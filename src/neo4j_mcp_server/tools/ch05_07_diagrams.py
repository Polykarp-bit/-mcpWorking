from __future__ import annotations

import base64
import binascii

# `urllib.error`, `urllib.request` und `zlib` werden nur noch vom auskommentierten
# Kroki-Code (siehe unten) referenziert. Imports bleiben bestehen, damit der
# deaktivierte Block sofort wieder lauffähig wäre, falls er reaktiviert wird.
import urllib.error  # noqa: F401  (used by commented-out Kroki code)
import urllib.request  # noqa: F401  (used by commented-out Kroki code)
import zlib  # noqa: F401  (used by commented-out Kroki code)

from ..core import (
    logger,
    mcp,
    _clean_content,
    _format_error,
    _run_read,
    _run_write,
    _safe_str,
)
from .common import validate_required


# --- Chapter 5–7: Bausteinsicht / Laufzeitsicht / Verteilungssicht (Diagrams) ---


def _read_image_file(image_file_path: str) -> tuple[bytes, str, str]:
    """Liest Bild-Bytes und gibt (bytes, mime_type, file_name) zurück."""
    if not image_file_path:
        return b"", "", ""
    try:
        import os

        if not os.path.exists(image_file_path):
            return b"", "", ""
        with open(image_file_path, "rb") as f:
            image_bytes = f.read()
        image_name = os.path.basename(image_file_path)
        if image_name.lower().endswith(".png"):
            mime_type = "image/png"
        elif image_name.lower().endswith(".jpg") or image_name.lower().endswith(".jpeg"):
            mime_type = "image/jpeg"
        else:
            mime_type = "application/octet-stream"
        return image_bytes, mime_type, image_name
    except Exception:
        return b"", "", ""


@mcp.tool()
def add_building_block_view(description: str, image_file_path: str, *, parent_name: str) -> str:
    """Fügt eine Bausteinsicht (Building Block View) für Kapitel 5 hinzu. Überschreibt eine existierende Ansicht.

    WICHTIG: Es ist zwingend notwendig, ein Diagramm bereitzustellen, um eine
    Beschreibung anzulegen. Eine Beschreibung ohne zugehöriges Diagramm ist NICHT erlaubt.
    Gib daher entweder einen gültigen Pfad zu einer Bilddatei (PNG/JPG/JPEG) über
    `image_file_path` an, oder nutze stattdessen `generate_mermaid_diagram(chapter="5", ...)`,
    um Diagramm UND Beschreibung gemeinsam zu erzeugen.
    """
    import os

    try:
        description = validate_required(description, "description")
        image_file_path = validate_required(image_file_path, "image_file_path")
    except ValueError as e:
        return _format_error("add_building_block_view", e)

    if not os.path.exists(image_file_path):
        return (
            "## Error\n\n"
            "Ein Diagramm ist für die Bausteinsicht zwingend notwendig. "
            f"Die angegebene Datei wurde nicht gefunden: `{image_file_path}`. "
            "Bitte einen gültigen Pfad zu einer PNG/JPG/JPEG-Datei angeben oder "
            "`generate_mermaid_diagram(chapter='5', ...)` verwenden.\n"
        )

    image_bytes, mime_type, image_name = _read_image_file(image_file_path)
    if not image_bytes:
        return (
            "## Error\n\n"
            "Ein Diagramm ist für die Bausteinsicht zwingend notwendig. "
            f"Die Datei `{image_file_path}` konnte nicht als Bild gelesen werden "
            "(unterstützt: PNG, JPG, JPEG).\n"
        )

    cypher = (
        "MERGE (d:Arc42 {name: $parent_name}) "
        "WITH d "
        "OPTIONAL MATCH (d)-[:bausteinsicht]->(old:Image:Baustein) "
        "DETACH DELETE old "
        "WITH d "
        "CREATE (n:Image:Baustein { "
        "   description: $description, "
        "   bildName: $image_name, "
        "   bildMimeType: $mime_type, "
        "   bildPath: $image_bytes, "
        "   uxfName: '', "
        "   uxfMimeType: '', "
        "   uxfPath: $empty_bytes "
        "}) "
        "MERGE (d)-[:bausteinsicht]->(n) "
        "RETURN n"
    )
    logger.info("Tool add_building_block_view: image='%s'", image_name)
    try:
        _run_write(
            cypher,
            description=description,
            parent_name=parent_name,
            image_name=image_name,
            mime_type=mime_type,
            image_bytes=image_bytes,
            empty_bytes=b"",
        )
        return f"## Success\n\nAdded Building Block View (Image: {image_name})\n"
    except Exception as e:
        return _format_error("add_building_block_view", e)


@mcp.tool()
def update_building_block_view_description(new_description: str, *, parent_name: str) -> str:
    """Aktualisiert nur die textuelle Beschreibung der Bausteinsicht (Kapitel 5).

    WICHTIG: Es muss bereits eine Bausteinsicht mit Diagramm existieren. Eine
    Beschreibung ohne zugehöriges Diagramm ist NICHT erlaubt. Falls noch kein
    Diagramm vorhanden ist, zuerst `add_building_block_view` (mit Bild) oder
    `generate_mermaid_diagram(chapter='5', ...)` aufrufen.
    """
    try:
        new_description = validate_required(new_description, "new_description")
    except ValueError as e:
        return _format_error("update_building_block_view_description", e)

    logger.info("Tool update_building_block_view_description aufgerufen")
    cypher = (
        "MATCH (d:Arc42 {name: $parent_name})-[:bausteinsicht]->(n:Image:Baustein) "
        "SET n.description = $new_description "
        "RETURN n"
    )
    try:
        records = _run_write(cypher, parent_name=parent_name, new_description=new_description)
        if not records:
            return (
                "## Not Found\n\n"
                "Keine bestehende Bausteinsicht gefunden. "
                "Bitte zuerst ein Diagramm mit add_building_block_view oder "
                "generate_mermaid_diagram anlegen.\n"
            )
        return "## Success\n\nUpdated Building Block View description.\n"
    except Exception as e:
        return _format_error("update_building_block_view_description", e)


@mcp.tool()
def add_runtime_view(description: str, image_file_path: str, *, parent_name: str) -> str:
    """Fügt eine Laufzeitsicht (Runtime View) für Kapitel 6 hinzu. Überschreibt eine existierende Ansicht.

    WICHTIG: Es ist zwingend notwendig, ein Diagramm bereitzustellen, um eine
    Beschreibung anzulegen. Eine Beschreibung ohne zugehöriges Diagramm ist NICHT erlaubt.
    Gib daher entweder einen gültigen Pfad zu einer Bilddatei (PNG/JPG/JPEG) über
    `image_file_path` an, oder nutze stattdessen `generate_mermaid_diagram(chapter="6", ...)`,
    um Diagramm UND Beschreibung gemeinsam zu erzeugen.
    """
    import os

    try:
        description = validate_required(description, "description")
        image_file_path = validate_required(image_file_path, "image_file_path")
    except ValueError as e:
        return _format_error("add_runtime_view", e)

    if not os.path.exists(image_file_path):
        return (
            "## Error\n\n"
            "Ein Diagramm ist für die Laufzeitsicht zwingend notwendig. "
            f"Die angegebene Datei wurde nicht gefunden: `{image_file_path}`. "
            "Bitte einen gültigen Pfad zu einer PNG/JPG/JPEG-Datei angeben oder "
            "`generate_mermaid_diagram(chapter='6', ...)` verwenden.\n"
        )

    image_bytes, mime_type, image_name = _read_image_file(image_file_path)
    if not image_bytes:
        return (
            "## Error\n\n"
            "Ein Diagramm ist für die Laufzeitsicht zwingend notwendig. "
            f"Die Datei `{image_file_path}` konnte nicht als Bild gelesen werden "
            "(unterstützt: PNG, JPG, JPEG).\n"
        )

    cypher = (
        "MERGE (d:Arc42 {name: $parent_name}) "
        "WITH d "
        "OPTIONAL MATCH (d)-[:laufzeitsicht]->(old:Image:Laufzeit) "
        "DETACH DELETE old "
        "CREATE (n:Image:Laufzeit { "
        "   description: $description, "
        "   bildName: $image_name, "
        "   bildMimeType: $mime_type, "
        "   bildPath: $image_bytes, "
        "   uxfName: '', "
        "   uxfMimeType: '', "
        "   uxfPath: $empty_bytes "
        "}) "
        "MERGE (d)-[:laufzeitsicht]->(n) "
        "RETURN n"
    )
    logger.info("Tool add_runtime_view: image='%s'", image_name)
    try:
        _run_write(
            cypher,
            description=description,
            parent_name=parent_name,
            image_name=image_name,
            mime_type=mime_type,
            image_bytes=image_bytes,
            empty_bytes=b"",
        )
        return f"## Success\n\nAdded Runtime View (Image: {image_name})\n"
    except Exception as e:
        return _format_error("add_runtime_view", e)


@mcp.tool()
def update_runtime_view_description(new_description: str, *, parent_name: str) -> str:
    """Aktualisiert nur die textuelle Beschreibung der Laufzeitsicht (Kapitel 6).

    WICHTIG: Es muss bereits eine Laufzeitsicht mit Diagramm existieren. Eine
    Beschreibung ohne zugehöriges Diagramm ist NICHT erlaubt. Falls noch kein
    Diagramm vorhanden ist, zuerst `add_runtime_view` (mit Bild) oder
    `generate_mermaid_diagram(chapter='6', ...)` aufrufen.
    """
    try:
        new_description = validate_required(new_description, "new_description")
    except ValueError as e:
        return _format_error("update_runtime_view_description", e)

    cypher = (
        "MATCH (d:Arc42 {name: $parent_name})-[:laufzeitsicht]->(n:Image:Laufzeit) "
        "SET n.description = $new_description "
        "RETURN n"
    )
    try:
        records = _run_write(cypher, new_description=new_description, parent_name=parent_name)
        if not records:
            return "## Not Found\n\nKeine bestehende Laufzeitsicht gefunden.\n"
        return "## Success\n\nUpdated Runtime View description.\n"
    except Exception as e:
        return _format_error("update_runtime_view_description", e)


@mcp.tool()
def add_deployment_view(description: str, image_file_path: str, *, parent_name: str) -> str:
    """Fügt eine Verteilungssicht (Kapitel 7) hinzu. Überschreibt eine existierende Ansicht.

    WICHTIG: Es ist zwingend notwendig, ein Diagramm bereitzustellen, um eine
    Beschreibung anzulegen. Eine Beschreibung ohne zugehöriges Diagramm ist NICHT erlaubt.
    Gib daher entweder einen gültigen Pfad zu einer Bilddatei (PNG/JPG/JPEG) über
    `image_file_path` an, oder nutze stattdessen `generate_mermaid_diagram(chapter="7", ...)`,
    um Diagramm UND Beschreibung gemeinsam zu erzeugen.
    """
    import os

    try:
        description = validate_required(description, "description")
        image_file_path = validate_required(image_file_path, "image_file_path")
    except ValueError as e:
        return _format_error("add_deployment_view", e)

    if not os.path.exists(image_file_path):
        return (
            "## Error\n\n"
            "Ein Diagramm ist für die Verteilungssicht zwingend notwendig. "
            f"Die angegebene Datei wurde nicht gefunden: `{image_file_path}`. "
            "Bitte einen gültigen Pfad zu einer PNG/JPG/JPEG-Datei angeben oder "
            "`generate_mermaid_diagram(chapter='7', ...)` verwenden.\n"
        )

    image_bytes, mime_type, image_name = _read_image_file(image_file_path)
    if not image_bytes:
        return (
            "## Error\n\n"
            "Ein Diagramm ist für die Verteilungssicht zwingend notwendig. "
            f"Die Datei `{image_file_path}` konnte nicht als Bild gelesen werden "
            "(unterstützt: PNG, JPG, JPEG).\n"
        )

    cypher = (
        "MERGE (d:Arc42 {name: $parent_name}) "
        "WITH d "
        "OPTIONAL MATCH (d)-[:verteilungssicht]->(old:Image:Verteilung) "
        "DETACH DELETE old "
        "CREATE (n:Image:Verteilung { "
        "   description: $description, "
        "   bildName: $image_name, "
        "   bildMimeType: $mime_type, "
        "   bildPath: $image_bytes, "
        "   uxfName: '', "
        "   uxfMimeType: '', "
        "   uxfPath: $empty_bytes "
        "}) "
        "MERGE (d)-[:verteilungssicht]->(n) "
        "RETURN n"
    )
    logger.info("Tool add_deployment_view: image='%s'", image_name)
    try:
        _run_write(
            cypher,
            description=description,
            parent_name=parent_name,
            image_name=image_name,
            mime_type=mime_type,
            image_bytes=image_bytes,
            empty_bytes=b"",
        )
        return f"## Success\n\nAdded Deployment View (Image: {image_name})\n"
    except Exception as e:
        return _format_error("add_deployment_view", e)


@mcp.tool()
def update_deployment_view_description(new_description: str, *, parent_name: str) -> str:
    """Aktualisiert nur die textuelle Beschreibung der Verteilungssicht (Kapitel 7).

    WICHTIG: Es muss bereits eine Verteilungssicht mit Diagramm existieren. Eine
    Beschreibung ohne zugehöriges Diagramm ist NICHT erlaubt. Falls noch kein
    Diagramm vorhanden ist, zuerst `add_deployment_view` (mit Bild) oder
    `generate_mermaid_diagram(chapter='7', ...)` aufrufen.
    """
    try:
        new_description = validate_required(new_description, "new_description")
    except ValueError as e:
        return _format_error("update_deployment_view_description", e)

    cypher = (
        "MATCH (d:Arc42 {name: $parent_name})-[:verteilungssicht]->(n:Image:Verteilung) "
        "SET n.description = $new_description "
        "RETURN n"
    )
    try:
        records = _run_write(cypher, new_description=new_description, parent_name=parent_name)
        if not records:
            return "## Not Found\n\nKeine bestehende Verteilungssicht gefunden.\n"
        return "## Success\n\nUpdated Deployment View description.\n"
    except Exception as e:
        return _format_error("update_deployment_view_description", e)


@mcp.tool()
def delete_diagram(chapter: str, *, parent_name: str) -> str:
    """Löscht ein Architekturdiagramm nach Kapitel-Spezifikation. Lösche niemals etwas, ohne nochmal nachzufragen!"""

    chapter = _safe_str(chapter).strip()
    cfg = {
        "5": ("Image:Baustein", "bausteinsicht", "Bausteinsicht"),
        "6": ("Image:Laufzeit", "laufzeitsicht", "Laufzeitsicht"),
        "7": ("Image:Verteilung", "verteilungssicht", "Verteilungssicht"),
    }.get(chapter)
    if not cfg:
        return "## Error\n\nBitte Kapitel 5, 6 oder 7 angeben.\n"

    label, rel, name = cfg
    cypher = (
        "MATCH (d:Arc42 {name: $parent_name})-[:{rel}]->(n:{label}) "
        "DETACH DELETE n "
        "RETURN count(n) as c"
    ).format(rel=rel, label=label)
    try:
        res = _run_write(cypher, parent_name=parent_name)
        deleted = res[0]["c"]
        if deleted > 0:
            return f"## Success\n\nDeleted diagram: **{name}** (Kapitel {chapter}).\n"
        return f"## Warning\n\nNo diagram found for Kapitel {chapter}.\n"
    except Exception as e:
        return _format_error("delete_diagram", e)


@mcp.tool()
def get_diagram(chapter: str, *, parent_name: str) -> str:
    """Ruft die Beschreibung und Metadaten eines Diagramms ab (Bausteinsicht/Laufzeitsicht/Verteilungssicht)."""
    diagram_map = {
        "5": ("Image:Baustein", "bausteinsicht", "Bausteinsicht"),
        "6": ("Image:Laufzeit", "laufzeitsicht", "Laufzeitsicht"),
        "7": ("Image:Verteilung", "verteilungssicht", "Verteilungssicht"),
    }

    if chapter not in diagram_map:
        return "## Error\n\nBitte Kapitel 5, 6 oder 7 angeben.\n"

    label, rel, name = diagram_map[chapter]
    logger.info("Tool get_diagram: Kapitel %s (%s)", chapter, name)

    cypher = (
        "MATCH (d:Arc42 {{name: $parent_name}})-[:{rel}]->(n:{label}) "
        "RETURN n.description AS description, n.bildName AS bildName, n.bildMimeType AS mimeType"
    ).format(rel=rel, label=label)

    try:
        records = _run_read(cypher, parent_name=parent_name)
        if not records:
            return f"## {name}\n\n_(kein Diagramm vorhanden)_\n"

        r = records[0]
        desc = _clean_content(str(r.get("description", "")))
        bild_name = r.get("bildName", "")
        mime_type = r.get("mimeType", "")

        parts = [f"## {name} (Kapitel {chapter})\n"]
        if desc:
            parts.append(f"**Beschreibung:** {desc}\n")
        if bild_name:
            parts.append(f"**Bilddatei:** {bild_name} ({mime_type})\n")
        else:
            parts.append("_(kein Bild hochgeladen)_\n")
        return "\n".join(parts)
    except Exception as e:
        return _format_error("get_diagram", e)


# ---------------------------------------------------------------------------
# Konfiguration der Diagramm-Kapitel (Bausteinsicht / Laufzeitsicht /
# Verteilungssicht). Wird sowohl vom (auskommentierten) Kroki-basierten
# `generate_mermaid_diagram` als auch vom neuen `add_diagram_image` genutzt.
# ---------------------------------------------------------------------------
_DIAGRAM_CHAPTER_MAP = {
    "5": {
        "label_old": "Image:Baustein",
        "rel_delete": "bausteinsicht",
        "label_new": "Image:Baustein",
        "rel_create": "bausteinsicht",
        "name": "Bausteinsicht",
        "file_name": "bausteinsicht.png",
    },
    "6": {
        "label_old": "Image:Laufzeit",
        "rel_delete": "laufzeitsicht",
        "label_new": "Image:Laufzeit",
        "rel_create": "laufzeitsicht",
        "name": "Laufzeitsicht",
        "file_name": "laufzeitsicht.png",
    },
    "7": {
        "label_old": "Image:Verteilung",
        "rel_delete": "verteilungssicht",
        "label_new": "Image:Verteilung",
        "rel_create": "verteilungssicht",
        "name": "Verteilungssicht",
        "file_name": "verteilungssicht.png",
    },
}


# ---------------------------------------------------------------------------
# DEPRECATED: Kroki-basiertes Mermaid-Rendering
# ---------------------------------------------------------------------------
# Der folgende Block ruft die externe Kroki-API auf, um Mermaid-Code in ein
# PNG umzuwandeln. Wurde deaktiviert, weil die Kroki-API-Aufrufe wiederholt
# in Timeouts gelaufen sind. Stattdessen wird `add_diagram_image` verwendet,
# bei dem das LLM das fertig gerenderte Bild direkt als base64 mitliefert.
# Code bewusst auskommentiert (nicht gelöscht), damit er bei Bedarf wieder
# aktiviert werden kann.
# ---------------------------------------------------------------------------
# _KROKI_BASE_URL = "https://kroki.io"
# _KROKI_TIMEOUT_S = 30
#
#
# def _mermaid_to_png_bytes(mermaid_code: str) -> bytes:
#     """Sendet Mermaid-Code an die Kroki-API und gibt rohe PNG-Bytes zurück."""
#     compressed = zlib.compress(mermaid_code.encode("utf-8"), 9)
#     encoded = base64.urlsafe_b64encode(compressed).decode("ascii")
#     url = f"{_KROKI_BASE_URL}/mermaid/png/{encoded}"
#     logger.info("Kroki API request: %s…", url[:80])
#     req = urllib.request.Request(url, headers={"User-Agent": "arc42doc-mcp-server/1.0"})
#     try:
#         with urllib.request.urlopen(req, timeout=_KROKI_TIMEOUT_S) as resp:
#             png_bytes = resp.read()
#             logger.info("Kroki API response: %d bytes (PNG)", len(png_bytes))
#             return png_bytes
#     except urllib.error.HTTPError as e:
#         raise RuntimeError(f"Kroki API HTTP-Fehler {e.code}: {e.reason}") from e
#     except urllib.error.URLError as e:
#         raise RuntimeError(f"Kroki API nicht erreichbar: {e.reason}") from e
#
#
# @mcp.tool()
# def generate_mermaid_diagram(
#     chapter: str,
#     mermaid_code: str,
#     description: str,
#     *,
#     parent_name: str,
# ) -> str:
#     """Generiert ein Mermaid-Diagramm über die Kroki-API und speichert das PNG in Neo4j."""
#     if chapter not in _DIAGRAM_CHAPTER_MAP:
#         return "## Error\n\nBitte Kapitel 5, 6 oder 7 angeben.\n"
#
#     try:
#         mermaid_code = validate_required(mermaid_code, "mermaid_code")
#         description = validate_required(description, "description")
#     except ValueError as e:
#         return _format_error("generate_mermaid_diagram", e)
#
#     cfg = _DIAGRAM_CHAPTER_MAP[chapter]
#     logger.info(
#         "Tool generate_mermaid_diagram: Kapitel %s (%s), parent='%s'",
#         chapter,
#         cfg["name"],
#         parent_name,
#     )
#
#     try:
#         png_bytes = _mermaid_to_png_bytes(mermaid_code)
#     except RuntimeError as e:
#         return (
#             "## Error\n\n"
#             f"**Kroki API fehlgeschlagen:** {e}\n\n"
#             "Bitte Internetverbindung prüfen oder Mermaid-Code auf Syntax-Fehler kontrollieren.\n"
#         )
#
#     cypher = (
#         "MERGE (d:Arc42 {{name: $parent_name}}) "
#         "WITH d "
#         "OPTIONAL MATCH (d)-[:{rel_delete}]->(old:{label_old}) "
#         "DETACH DELETE old "
#         "WITH d "
#         "CREATE (n:{label_new} {{ "
#         "   description: $description, "
#         "   bildName: $file_name, "
#         "   bildMimeType: $mime_type, "
#         "   bildPath: $png_bytes, "
#         "   uxfName: '', "
#         "   uxfMimeType: '', "
#         "   uxfPath: $empty_bytes "
#         "}}) "
#         "MERGE (d)-[:{rel_create}]->(n) "
#         "RETURN n"
#     ).format(
#         rel_delete=cfg["rel_delete"],
#         label_old=cfg["label_old"],
#         label_new=cfg["label_new"],
#         rel_create=cfg["rel_create"],
#     )
#
#     try:
#         _run_write(
#             cypher,
#             parent_name=parent_name,
#             description=description,
#             file_name=cfg["file_name"],
#             mime_type="image/png",
#             png_bytes=png_bytes,
#             empty_bytes=b"",
#         )
#         return f"## Success\n\nMermaid-Diagramm gespeichert: **{cfg['name']}** (Kapitel {chapter}).\n"
#     except Exception as e:
#         return _format_error("generate_mermaid_diagram", e)


# ---------------------------------------------------------------------------
# Neue Variante: Diagrammbild kommt direkt vom LLM (kein externer Render-Call)
# ---------------------------------------------------------------------------
_SUPPORTED_IMAGE_FORMATS = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "svg": "image/svg+xml",
}


@mcp.tool()
def add_diagram_image(
    chapter: str,
    description: str,
    image_base64: str,
    *,
    parent_name: str,
    image_format: str = "png",
) -> str:
    """Speichert ein vom LLM bereitgestelltes Diagrammbild (base64-codiert) in Neo4j.

    Ersetzt das frühere `generate_mermaid_diagram`-Tool, das den Mermaid-Code
    extern bei Kroki rendern ließ. Stattdessen rendert das LLM (bzw. ein
    vorgelagertes Tool) das Diagramm selbst und übergibt das fertige Bild
    direkt als base64-String — ohne externen HTTP-Call.

    Args:
        chapter: "5" (Bausteinsicht), "6" (Laufzeitsicht) oder "7" (Verteilungssicht).
        description: Markdown-Beschreibung des Diagramms.
        image_base64: Base64-codierte Bild-Bytes. Optional mit Data-URI-Prefix
            ("data:image/png;base64,...") — der Prefix wird automatisch entfernt.
        parent_name: Name des arc42-Projekts in Neo4j.
        image_format: "png" (Default), "jpg"/"jpeg" oder "svg".
    """
    if chapter not in _DIAGRAM_CHAPTER_MAP:
        return "## Error\n\nBitte Kapitel 5, 6 oder 7 angeben.\n"

    fmt = (image_format or "png").lower().strip()
    if fmt not in _SUPPORTED_IMAGE_FORMATS:
        return (
            "## Error\n\n"
            f"Unbekanntes Bildformat `{image_format}`. "
            f"Erlaubt: {', '.join(sorted(_SUPPORTED_IMAGE_FORMATS))}.\n"
        )

    try:
        description = validate_required(description, "description")
        image_base64 = validate_required(image_base64, "image_base64")
    except ValueError as e:
        return _format_error("add_diagram_image", e)

    # Data-URI-Prefix (z. B. "data:image/png;base64,") entfernen, falls vorhanden.
    payload = image_base64.strip()
    if payload.startswith("data:") and "," in payload:
        payload = payload.split(",", 1)[1]

    try:
        image_bytes = base64.b64decode(payload, validate=True)
    except (ValueError, binascii.Error) as e:
        return (
            "## Error\n\n"
            f"`image_base64` konnte nicht dekodiert werden: {e}\n"
        )

    if not image_bytes:
        return "## Error\n\n`image_base64` ist nach dem Dekodieren leer.\n"

    cfg = _DIAGRAM_CHAPTER_MAP[chapter]
    mime_type = _SUPPORTED_IMAGE_FORMATS[fmt]
    # Dateinamen-Endung dem Format anpassen (z. B. bausteinsicht.svg statt .png)
    base_name = cfg["file_name"].rsplit(".", 1)[0]
    file_name = f"{base_name}.{fmt}"

    logger.info(
        "Tool add_diagram_image: Kapitel %s (%s), parent='%s', format=%s, size=%d bytes",
        chapter,
        cfg["name"],
        parent_name,
        fmt,
        len(image_bytes),
    )

    cypher = (
        "MERGE (d:Arc42 {{name: $parent_name}}) "
        "WITH d "
        "OPTIONAL MATCH (d)-[:{rel_delete}]->(old:{label_old}) "
        "DETACH DELETE old "
        "WITH d "
        "CREATE (n:{label_new} {{ "
        "   description: $description, "
        "   bildName: $file_name, "
        "   bildMimeType: $mime_type, "
        "   bildPath: $image_bytes, "
        "   uxfName: '', "
        "   uxfMimeType: '', "
        "   uxfPath: $empty_bytes "
        "}}) "
        "MERGE (d)-[:{rel_create}]->(n) "
        "RETURN n"
    ).format(
        rel_delete=cfg["rel_delete"],
        label_old=cfg["label_old"],
        label_new=cfg["label_new"],
        rel_create=cfg["rel_create"],
    )

    try:
        _run_write(
            cypher,
            parent_name=parent_name,
            description=description,
            file_name=file_name,
            mime_type=mime_type,
            image_bytes=image_bytes,
            empty_bytes=b"",
        )
        return (
            "## Success\n\n"
            f"Diagrammbild gespeichert: **{cfg['name']}** (Kapitel {chapter}, "
            f"Format `{fmt}`, {len(image_bytes)} Bytes).\n"
        )
    except Exception as e:
        return _format_error("add_diagram_image", e)

