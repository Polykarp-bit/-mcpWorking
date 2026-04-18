from __future__ import annotations

from ..core import logger, mcp, _format_error, _run_write
from .common import require_confirm, validate_required


# --- Chapter 11: Risiken ---


@mcp.tool()
def add_risk(description: str, impact: str, probability: str, status: str, *, parent_name: str) -> str:
    """Fügt ein Risiko (Risk) für Kapitel 11 hinzu."""
    try:
        description = validate_required(description, "description")
        impact = validate_required(impact, "impact")
        probability = validate_required(probability, "probability")
        status = validate_required(status, "status")
    except ValueError as e:
        return _format_error("add_risk", e)

    cypher = (
        "MERGE (d:Arc42 {name: $parent_name}) "
        "CREATE (n:Risiko { "
        "   anforderung: $description, "
        "   schadenshoehe: $impact, "
        "   wirkung: $impact, "
        "   eintrittswahrscheinlichkeit: $probability, "
        "   status: $status, "
        "   zuletztAktu: toString(datetime()) "
        "}) "
        "MERGE (d)-[:hasRisiko]->(n) "
        "RETURN n"
    )
    logger.info("Tool add_risk: '%s'", description[:80])
    try:
        _run_write(
            cypher,
            description=description,
            impact=impact,
            probability=probability,
            status=status,
            parent_name=parent_name,
        )
        return f"## Success\n\nAdded Risk: **{description}**\n"
    except Exception as e:
        return _format_error("add_risk", e)


@mcp.tool()
def update_risk(
    old_description: str,
    new_description: str = "",
    new_impact: str = "",
    new_probability: str = "",
    new_status: str = "",
    *,
    parent_name: str,
) -> str:
    """Aktualisiert ein Risiko in Kapitel 11."""
    try:
        old_description = validate_required(old_description, "old_description")
    except ValueError as e:
        return _format_error("update_risk", e)

    logger.info("Tool update_risk: '%s'", old_description[:60])
    set_clauses = []
    if new_description:
        set_clauses.append("n.anforderung = $new_description")
    if new_impact:
        set_clauses.append("n.schadenshoehe = $new_impact")
        set_clauses.append("n.wirkung = $new_impact")
    if new_probability:
        set_clauses.append("n.eintrittswahrscheinlichkeit = $new_probability")
    if new_status:
        set_clauses.append("n.status = $new_status")
    set_clauses.append("n.zuletztAktu = toString(datetime())")

    cypher = (
        "MATCH (d:Arc42 {name: $parent_name})-[:hasRisiko]->(n:Risiko {anforderung: $old_description}) "
        f"SET {', '.join(set_clauses)} "
        "RETURN n"
    )
    try:
        records = _run_write(
            cypher,
            old_description=old_description,
            new_description=new_description,
            new_impact=new_impact,
            new_probability=new_probability,
            new_status=new_status,
            parent_name=parent_name,
        )
        if not records:
            return f"## Not Found\n\nRisk '{old_description}' not found.\n"
        return f"## Success\n\nUpdated Risk: **{old_description}**\n"
    except Exception as e:
        return _format_error("update_risk", e)


@mcp.tool()
def delete_risk(description: str, *, parent_name: str) -> str:
    """Löscht ein Risiko anhand seiner Beschreibung. Lösche niemals etwas, ohne nochmal nachzufragen!"""
    try:
        description = validate_required(description, "description")
    except ValueError as e:
        return _format_error("delete_risk", e)

    cypher = (
        "MATCH (d:Arc42 {name: $parent_name})-[:hasRisiko]->(n:Risiko {anforderung: $description}) "
        "DETACH DELETE n "
        "RETURN count(n) as c"
    )
    try:
        res = _run_write(cypher, description=description, parent_name=parent_name)
        deleted = res[0]["c"]
        if deleted > 0:
            return f"## Success\n\nDeleted Risk: **{description}**\n"
        return "## Warning\n\nNo matching risk found.\n"
    except Exception as e:
        return _format_error("delete_risk", e)


@mcp.tool()
def add_swot(parent_name: str, strength: str = "", weakness: str = "", opportunity: str = "", threat: str = "") -> str:
    """Add one or more SWOT entries for Chapter 11 (stored as TextEingabe nodes)."""

    def _add_single(entry_type: str, content: str):
        cypher = (
            "MATCH (d:Arc42 {name: $parent_name}) "
            "CREATE (n:TextEingabe {type: $type, content: $content}) "
            "MERGE (d)-[:hasTextEingabe]->(n) "
            "RETURN n"
        )
        _run_write(cypher, type=entry_type, content=content.strip(), parent_name=parent_name)

    added = []
    try:
        parent_name = validate_required(parent_name, "parent_name")
    except ValueError as e:
        return _format_error("add_swot", e)

    try:
        if strength:
            _add_single("STRENGTH", strength)
            added.append(f"- **STRENGTH**: {strength.strip()}")
        if weakness:
            _add_single("WEAKNESS", weakness)
            added.append(f"- **WEAKNESS**: {weakness.strip()}")
        if opportunity:
            _add_single("OPPORTUNITY", opportunity)
            added.append(f"- **OPPORTUNITY**: {opportunity.strip()}")
        if threat:
            _add_single("THREAT", threat)
            added.append(f"- **THREAT**: {threat.strip()}")

        if not added:
            return "## Warning\n\nKeine SWOT-Eintraege uebergeben.\n"

        return "## Success\n\nAdded SWOT Entries:\n" + "\n".join(added) + "\n"
    except Exception as e:
        return _format_error("add_swot", e)


@mcp.tool()
def update_swot_entry(
    parent_name: str,
    entry_type: str,
    old_content: str,
    new_content: str,
) -> str:
    """Update a specific SWOT entry by type and old content."""
    try:
        parent_name = validate_required(parent_name, "parent_name")
        entry_type = validate_required(entry_type, "entry_type")
        old_content = validate_required(old_content, "old_content")
        new_content = validate_required(new_content, "new_content")
    except ValueError as e:
        return _format_error("update_swot_entry", e)

    cypher = (
        "MATCH (d:Arc42 {name: $parent_name})-[:hasTextEingabe]->(n:TextEingabe {type: $type, content: $old_content}) "
        "SET n.content = $new_content "
        "RETURN n"
    )
    try:
        records = _run_write(
            cypher,
            parent_name=parent_name,
            type=entry_type,
            old_content=old_content,
            new_content=new_content,
        )
        if not records:
            return "## Not Found\n\nNo matching SWOT entry found.\n"
        return f"## Success\n\nUpdated SWOT Entry ({entry_type}).\n"
    except Exception as e:
        return _format_error("update_swot_entry", e)


@mcp.tool()
def delete_swot_entry(parent_name: str, entry_type: str, content: str) -> str:
    """Delete a specific SWOT entry. Lösche niemals etwas, ohne nochmal nachzufragen!"""
    try:
        parent_name = validate_required(parent_name, "parent_name")
        entry_type = validate_required(entry_type, "entry_type")
        content = validate_required(content, "content")
    except ValueError as e:
        return _format_error("delete_swot_entry", e)

    cypher = (
        "MATCH (d:Arc42 {name: $parent_name})-[r:hasTextEingabe]->(n:TextEingabe {type: $type, content: $content}) "
        "DETACH DELETE n "
        "RETURN count(n) as c"
    )
    try:
        res = _run_write(cypher, type=entry_type, content=content, parent_name=parent_name)
        deleted = res[0]["c"]
        if deleted > 0:
            return f"## Success\n\nDeleted SWOT Entry ({entry_type}): **{content[:50]}**\n"
        return "## Warning\n\nNo matching SWOT entry found.\n"
    except Exception as e:
        return _format_error("delete_swot_entry", e)

