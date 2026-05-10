from __future__ import annotations

from ..core import logger, mcp, _format_error, _run_write
from .common import validate_required


# --- Chapter 12: Glossar ---


@mcp.tool()
def add_glossary_term(term: str, description: str, *, parent_name: str) -> str:
    """Fügt einen Eintrag zum Glossar (Chapter 12) hinzu."""
    try:
        term = validate_required(term, "term")
        description = validate_required(description, "description")
    except ValueError as e:
        return _format_error("add_glossary_term", e)

    cypher = (
        "MERGE (d:Arc42 {name: $parent_name}) "
        "CREATE (n:Glossar {begriff: $term, beschreibung: $description}) "
        "MERGE (d)-[:hasGlossar]->(n) "
        "RETURN n"
    )
    logger.info("Tool add_glossary_term: '%s'", term)
    try:
        _run_write(cypher, term=term, description=description, parent_name=parent_name)
        return f"## Success\n\nAdded Glossar: **{term}**\n"
    except Exception as e:
        return _format_error("add_glossary_term", e)


@mcp.tool()
def update_glossary_term(
    old_term: str,
    new_term: str = "",
    new_description: str = "",
    *,
    parent_name: str,
) -> str:
    """Aktualisiert einen existierenden Glossar-Eintrag in Kapitel 12."""
    try:
        old_term = validate_required(old_term, "old_term")
    except ValueError as e:
        return _format_error("update_glossary_term", e)

    logger.info("Tool update_glossary_term: '%s'", old_term)
    set_clauses = []
    if new_term:
        set_clauses.append("n.begriff = $new_term")
    if new_description:
        set_clauses.append("n.beschreibung = $new_description")

    if not set_clauses:
        return "## Error\n\nMindestens ein neues Feld muss angegeben werden.\n"

    cypher = (
        "MATCH (d:Arc42 {name: $parent_name})-[:hasGlossar]->(n:Glossar {begriff: $old_term}) "
        f"SET {', '.join(set_clauses)} "
        "RETURN n"
    )
    try:
        records = _run_write(
            cypher,
            old_term=old_term,
            new_term=new_term,
            new_description=new_description,
            parent_name=parent_name,
        )
        if not records:
            return f"## Not Found\n\nGlossar term '{old_term}' not found.\n"
        return f"## Success\n\nUpdated Glossar: **{old_term}**\n"
    except Exception as e:
        return _format_error("update_glossary_term", e)


@mcp.tool()
def delete_glossary_term(term: str, *, parent_name: str) -> str:
    """Löscht einen Glossar-Eintrag anhand seines Begriffs. Lösche niemals etwas, ohne nochmal nachzufragen!"""
    try:
        term = validate_required(term, "term")
    except ValueError as e:
        return _format_error("delete_glossary_term", e)

    cypher = (
        "MATCH (d:Arc42 {name: $parent_name})-[:hasGlossar]->(n:Glossar {begriff: $term}) "
        "DETACH DELETE n "
        "RETURN count(n) as c"
    )
    try:
        res = _run_write(cypher, term=term, parent_name=parent_name)
        deleted = res[0]["c"]
        if deleted > 0:
            return f"## Success\n\nDeleted Glossar: **{term}**\n"
        return "## Warning\n\nNo matching glossary term found.\n"
    except Exception as e:
        return _format_error("delete_glossary_term", e)

