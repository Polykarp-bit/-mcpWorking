from __future__ import annotations

import base64
import urllib.error
import urllib.request
import zlib

from ..core import (
    logger,
    mcp,
    _clean_content,
    _format_error,
    _run_read,
    _run_write,
    _safe_str,
)
from .common import require_confirm, validate_required


# --- Chapter 5–7: Bausteinsicht / Laufzeitsicht / Verteilungssicht (Diagrams) ---


def _read_image_file(image_file_path: str) -> tuple[bytes, str, str]:
    """Read image bytes and return (bytes, mime_type, file_name)."""
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
def add_building_block_view(description: str, image_file_path: str = "", *, parent_name: str) -> str:
    """Add a Building Block View (Bausteinsicht) for Chapter 5. Overwrites existing view."""
    try:
        description = validate_required(description, "description")
    except ValueError as e:
        return _format_error("add_building_block_view", e)

    image_bytes, mime_type, image_name = _read_image_file(image_file_path)
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
    """Update only the textual description of the Building Block View (Chapter 5)."""
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
def add_runtime_view(description: str, image_file_path: str = "", *, parent_name: str) -> str:
    """Add a Runtime View (Laufzeitsicht) for Chapter 6. Overwrites existing view."""
    try:
        description = validate_required(description, "description")
    except ValueError as e:
        return _format_error("add_runtime_view", e)

    image_bytes, mime_type, image_name = _read_image_file(image_file_path)
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
    """Aktualisiert nur die textuelle Beschreibung der Laufzeitsicht (Kapitel 6)."""
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
def add_deployment_view(description: str, image_file_path: str = "", *, parent_name: str) -> str:
    """Fügt eine Verteilungssicht (Kapitel 7) hinzu. Überschreibt eine existierende Ansicht."""
    try:
        description = validate_required(description, "description")
    except ValueError as e:
        return _format_error("add_deployment_view", e)

    image_bytes, mime_type, image_name = _read_image_file(image_file_path)
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
    """Aktualisiert nur die textuelle Beschreibung der Verteilungssicht (Kapitel 7)."""
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


_KROKI_BASE_URL = "https://kroki.io"
_KROKI_TIMEOUT_S = 30


def _mermaid_to_png_bytes(mermaid_code: str) -> bytes:
    """Send Mermaid code to Kroki API and return raw PNG bytes."""
    compressed = zlib.compress(mermaid_code.encode("utf-8"), 9)
    encoded = base64.urlsafe_b64encode(compressed).decode("ascii")
    url = f"{_KROKI_BASE_URL}/mermaid/png/{encoded}"
    logger.info("Kroki API request: %s…", url[:80])
    req = urllib.request.Request(url, headers={"User-Agent": "arc42doc-mcp-server/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=_KROKI_TIMEOUT_S) as resp:
            png_bytes = resp.read()
            logger.info("Kroki API response: %d bytes (PNG)", len(png_bytes))
            return png_bytes
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Kroki API HTTP-Fehler {e.code}: {e.reason}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Kroki API nicht erreichbar: {e.reason}") from e


@mcp.tool()
def generate_mermaid_diagram(
    chapter: str,
    mermaid_code: str,
    description: str,
    *,
    parent_name: str,
) -> str:
    """Generate a Mermaid diagram via Kroki API and save the PNG to Neo4j."""
    chapter_map = {
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

    if chapter not in chapter_map:
        return "## Error\n\nBitte Kapitel 5, 6 oder 7 angeben.\n"

    try:
        mermaid_code = validate_required(mermaid_code, "mermaid_code")
        description = validate_required(description, "description")
    except ValueError as e:
        return _format_error("generate_mermaid_diagram", e)

    cfg = chapter_map[chapter]
    logger.info(
        "Tool generate_mermaid_diagram: Kapitel %s (%s), parent='%s'",
        chapter,
        cfg["name"],
        parent_name,
    )

    try:
        png_bytes = _mermaid_to_png_bytes(mermaid_code)
    except RuntimeError as e:
        return (
            "## Error\n\n"
            f"**Kroki API fehlgeschlagen:** {e}\n\n"
            "Bitte Internetverbindung prüfen oder Mermaid-Code auf Syntax-Fehler kontrollieren.\n"
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
        "   bildPath: $png_bytes, "
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
            file_name=cfg["file_name"],
            mime_type="image/png",
            png_bytes=png_bytes,
            empty_bytes=b"",
        )
        return f"## Success\n\nMermaid-Diagramm gespeichert: **{cfg['name']}** (Kapitel {chapter}).\n"
    except Exception as e:
        return _format_error("generate_mermaid_diagram", e)

