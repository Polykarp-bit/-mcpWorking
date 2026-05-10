from __future__ import annotations

import logging
import os
import re
import sys
import time
from typing import Any, Dict, List, Tuple

from mcp.server.fastmcp import FastMCP
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, SessionExpired

# ---------------------------------------------------------------------------
# Logging (Semantisches Interaktions-Logging)
# ---------------------------------------------------------------------------
# MCP nutzt stdio für das Protokoll — Logs immer nach stderr (nicht stdout).
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stderr,
    force=True,
)
logger = logging.getLogger("mcp.arc42")

# ---------------------------------------------------------------------------
# MCP Server Instanz
# ---------------------------------------------------------------------------
mcp = FastMCP("arc42doc MCP Server")


# ---------------------------------------------------------------------------
# Konfiguration über Umgebungsvariablen (Environment Variables)
# ---------------------------------------------------------------------------
def _env(name: str, default: str) -> str:
    """Liest eine Umgebungsvariable aus und gibt `default` zurück, wenn sie nicht gesetzt oder leer ist."""
    val = os.getenv(name)
    return val if val is not None and val != "" else default


NEO4J_URI = _env("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = _env("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = _env("NEO4J_PASSWORD", "yourPassword")


# ---------------------------------------------------------------------------
# Neo4j Service – Data Access Layer (Protokoll/Logik-Trennung)
# ---------------------------------------------------------------------------
_MAX_RECONNECT_ATTEMPTS = 3
_RECONNECT_DELAY_S = 1.0

_driver = None


def _get_driver():
    """Holt oder erstellt den Neo4j-Treiber mit Auto-Reconnect."""
    global _driver
    if _driver is None:
        logger.info("Creating new Neo4j driver → %s", NEO4J_URI)
        _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    # Verbindung überprüfen; bei Fehler neu verbinden
    for attempt in range(1, _MAX_RECONNECT_ATTEMPTS + 1):
        try:
            _driver.verify_connectivity()
            return _driver
        except (ServiceUnavailable, SessionExpired, OSError) as exc:
            logger.warning(
                "Neo4j connectivity check failed (attempt %d/%d): %s",
                attempt,
                _MAX_RECONNECT_ATTEMPTS,
                exc,
            )
            if attempt < _MAX_RECONNECT_ATTEMPTS:
                time.sleep(_RECONNECT_DELAY_S)
                _driver = GraphDatabase.driver(
                    NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD)
                )
            else:
                raise
    return _driver


def _run_read(cypher: str, **params) -> list:
    """Führt eine Lese-Query (Read) aus und gibt eine Liste von Einträgen zurück (Auto-Reconnect)."""
    driver = _get_driver()
    with driver.session() as session:
        result = session.run(cypher, **params)
        return list(result)


def _run_write(cypher: str, **params) -> list:
    """Führt eine Schreib-Query (Write) innerhalb einer Transaktion aus (transaktionale Writes)."""
    driver = _get_driver()
    with driver.session() as session:

        def _tx(tx):
            result = tx.run(cypher, **params)
            return list(result)

        return session.execute_write(_tx)


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Eingabevalidierung (Semantische Validierung von Tool-Aufrufen)
# ---------------------------------------------------------------------------
_MAX_INPUT_LEN = 10000


def _validate_required(value: str, field_name: str) -> str:
    """Prüft, ob ein erforderliches String-Feld nicht leer ist."""
    v = str(value).strip() if value else ""
    if not v:
        raise ValueError(f"Parameter '{field_name}' darf nicht leer sein.")
    if len(v) > _MAX_INPUT_LEN:
        raise ValueError(
            f"Parameter '{field_name}' ist zu lang ({len(v)} Zeichen, max {_MAX_INPUT_LEN})."
        )
    return v


# ---------------------------------------------------------------------------
# Inhaltsbereinigung (Token-Effizienz)
# ---------------------------------------------------------------------------
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _clean_content(text: str) -> str:
    """Entfernt HTML-Tags und übermäßige Leerzeichen, um Tokens zu sparen."""
    if not text:
        return ""
    text = _HTML_TAG_RE.sub("", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Hilfsfunktionen (Helpers)
# ---------------------------------------------------------------------------
def _safe_str(x: Any, fallback: str = "") -> str:
    """Konvertiert einen beliebigen Wert sicher zu einem String; liefert `fallback`, wenn der Wert `None`/leer ist oder die Konvertierung fehlschlägt."""
    if x is None:
        return fallback
    try:
        s = str(x)
        return s if s != "" else fallback
    except Exception:
        return fallback


def _extract_title_and_content(
    node_data: Dict[str, Any], labels: List[str]
) -> Tuple[str, str]:
    """Extrahiert Titel und Inhalt (Content) aus einem Node basierend auf seinen Labels und Properties."""
    title = ""
    content = ""

    for prop in [
        "title",
        "name",
        "begriff",
        "roleOrName",
        "konvention",
        "randbedingung",
        "aufgabe",
        "anforderung",
        "qualitaetsziel",
    ]:
        if prop in node_data and node_data[prop]:
            title = str(node_data[prop])
            break

    for prop in [
        "content",
        "text",
        "beschreibung",
        "erlaeuterung",
        "hintergrund",
        "strategy",
        "loesung",
        "aufgabe",
    ]:
        if prop in node_data and node_data[prop]:
            content = str(node_data[prop])
            break

    if "TextEingabe" in labels:
        if "content" in node_data:
            content = str(node_data["content"])
            if "type" in node_data and node_data["type"] == "TITLE":
                title = content
                content = ""

    if "Konzept" in labels:
        if "name" in node_data:
            title = str(node_data["name"])
        if "text" in node_data:
            content = str(node_data["text"])

    if not title:
        title = labels[0] if labels else "Untitled"

    return title, _clean_content(content)


def _format_doc(title: str, content: str, node_type: str = "") -> str:
    """Formatiert einen Dokumentationsknoten als Markdown-Block (`##`-Überschrift mit optionalem `[node_type]`-Präfix); ersetzt fehlenden Inhalt durch einen Platzhalter."""
    title = title.strip() or "Untitled"
    content = content.strip()
    if not content:
        content = "_(no content)_"

    type_prefix = f"[{node_type}] " if node_type else ""
    return f"## {type_prefix}{title}\n\n{content}\n"


def _format_error(action: str, err: Exception) -> str:
    """Gibt eine strukturierte Fehlermeldung zurück, die das LLM interpretieren kann."""
    logger.error("Action '%s' failed: %s – %s", action, type(err).__name__, err)
    return (
        "## Error\n\n"
        f"**Action:** {action}\n\n"
        f"**Cause:** `{type(err).__name__}`\n\n"
        f"**Message:** {str(err)}\n"
    )

