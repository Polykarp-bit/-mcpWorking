from __future__ import annotations

from ..core import logger, mcp, _format_error, _run_write
from .common import require_confirm, validate_required


# --- Chapter 8: Querschnittliche Konzepte ---


@mcp.tool()
def add_documentation(title: str, content: str, doc_type: str = "Konzept") -> str:
    """Add a cross-cutting concept (Querschnittliches Konzept, Chapter 8) to the arc42 documentation."""
    try:
        title = validate_required(title, "title")
        content = validate_required(content, "content")
    except ValueError as e:
        return _format_error("add_documentation", e)

    logger.info("Tool add_documentation aufgerufen: title='%s'", title)
    parent_arc42 = "Neo4j MCP Server"

    if doc_type == "Konzept" or doc_type == "Documentation":
        cypher = (
            "MERGE (parent:Arc42 {name: $parent_name}) "
            "MERGE (n:Konzept {name: $title}) "
            "SET n.text = $content, "
            "    n.conceptCategories = ['Documentation'], "
            "    n.updated_at = datetime() "
            "MERGE (parent)-[:hatKonzept]->(n) "
            "RETURN n"
        )
    else:
        cypher = (
            "MERGE (n:Documentation {title: $title}) "
            "SET n.content = $content, "
            "    n.type = $doc_type "
            "RETURN n"
        )

    try:
        _run_write(cypher, title=title, content=content, doc_type=doc_type, parent_name=parent_arc42)
        return f"## Success\n\nAdded/Updated documentation: **{title}** linked to **{parent_arc42}**\n"
    except Exception as e:
        return _format_error("add_documentation", e)


@mcp.tool()
def update_documentation(title: str, new_content: str, *, parent_name: str) -> str:
    """Update the text content of an existing Konzept (Chapter 8)."""
    try:
        title = validate_required(title, "title")
        new_content = validate_required(new_content, "new_content")
    except ValueError as e:
        return _format_error("update_documentation", e)

    logger.info("Tool update_documentation: '%s'", title)
    cypher = (
        "MATCH (d:Arc42 {name: $parent_name})-[:hatKonzept]->(n:Konzept {name: $title}) "
        "SET n.text = $new_content, n.updated_at = datetime() "
        "RETURN n"
    )
    try:
        records = _run_write(cypher, title=title, new_content=new_content, parent_name=parent_name)
        if not records:
            return f"## Not Found\n\nKonzept '{title}' not found.\n"
        return f"## Success\n\nUpdated Konzept: **{title}**\n"
    except Exception as e:
        return _format_error("update_documentation", e)


@mcp.tool()
def delete_documentation(title: str, *, parent_name: str, confirm: bool = False) -> str:
    """Delete an existing Konzept (Chapter 8) by title."""
    guard = require_confirm(confirm, "delete_documentation")
    if guard:
        return guard
    try:
        title = validate_required(title, "title")
    except ValueError as e:
        return _format_error("delete_documentation", e)

    cypher = (
        "MATCH (d:Arc42 {name: $parent_name})-[:hatKonzept]->(n:Konzept {name: $title}) "
        "DETACH DELETE n "
        "RETURN count(n) as c"
    )
    try:
        res = _run_write(cypher, title=title, parent_name=parent_name)
        deleted = res[0]["c"]
        if deleted > 0:
            return f"## Success\n\nDeleted Konzept: **{title}**\n"
        return f"## Warning\n\nNo matching Konzept '{title}' found.\n"
    except Exception as e:
        return _format_error("delete_documentation", e)

