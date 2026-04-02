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
# Logging (QA-MA-02, QA-MA-04 – Semantic Interaction Logging)
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
# MCP Server Instance
# ---------------------------------------------------------------------------
mcp = FastMCP("arc42doc MCP Server")


# ---------------------------------------------------------------------------
# Configuration via Environment Variables (QA-PO-02)
# ---------------------------------------------------------------------------
def _env(name: str, default: str) -> str:
    val = os.getenv(name)
    return val if val is not None and val != "" else default


NEO4J_URI = _env("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = _env("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = _env("NEO4J_PASSWORD", "yourPassword")


# ---------------------------------------------------------------------------
# Neo4j Service – Data Access Layer (QA-MA-01 Protocol/Logic Separation)
# ---------------------------------------------------------------------------
_MAX_RECONNECT_ATTEMPTS = 3
_RECONNECT_DELAY_S = 1.0

_driver = None


def _get_driver():
    """Get or create Neo4j driver with auto-reconnect (QA-RE-02)."""
    global _driver
    if _driver is None:
        logger.info("Creating new Neo4j driver → %s", NEO4J_URI)
        _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    # Verify connectivity; reconnect on failure
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
    """Execute a read query and return list of records (QA-RE-02 auto-reconnect)."""
    driver = _get_driver()
    with driver.session() as session:
        result = session.run(cypher, **params)
        return list(result)


def _run_write(cypher: str, **params) -> list:
    """Execute a write query inside a transaction (QA-RE-03 transactional writes)."""
    driver = _get_driver()
    with driver.session() as session:

        def _tx(tx):
            result = tx.run(cypher, **params)
            return list(result)

        return session.execute_write(_tx)


# ---------------------------------------------------------------------------
# Input Validation (QA-SE-04 – Semantic Validation of Tool Calls)
# ---------------------------------------------------------------------------
_MAX_INPUT_LEN = 10000


def _validate_required(value: str, field_name: str) -> str:
    """Validate that a required string field is not empty."""
    v = str(value).strip() if value else ""
    if not v:
        raise ValueError(f"Parameter '{field_name}' darf nicht leer sein.")
    if len(v) > _MAX_INPUT_LEN:
        raise ValueError(
            f"Parameter '{field_name}' ist zu lang ({len(v)} Zeichen, max {_MAX_INPUT_LEN})."
        )
    return v


# ---------------------------------------------------------------------------
# Content Cleaning (QA-PE-02 – Token Efficiency)
# ---------------------------------------------------------------------------
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _clean_content(text: str) -> str:
    """Remove HTML tags and excessive whitespace to save tokens."""
    if not text:
        return ""
    text = _HTML_TAG_RE.sub("", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _safe_str(x: Any, fallback: str = "") -> str:
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
    """Extract title and content from node based on its labels and properties."""
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
    title = title.strip() or "Untitled"
    content = content.strip()
    if not content:
        content = "_(no content)_"

    type_prefix = f"[{node_type}] " if node_type else ""
    return f"## {type_prefix}{title}\n\n{content}\n"


def _format_error(action: str, err: Exception) -> str:
    """Return a structured error message the LLM can interpret (QA-RE-01)."""
    logger.error("Action '%s' failed: %s – %s", action, type(err).__name__, err)
    return (
        "## Error\n\n"
        f"**Action:** {action}\n\n"
        f"**Cause:** `{type(err).__name__}`\n\n"
        f"**Message:** {str(err)}\n"
    )

