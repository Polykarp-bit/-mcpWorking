from __future__ import annotations

from ..core import logger, mcp, _format_error, _run_write
from .common import require_confirm, validate_required


# --- Chapter 9: Entwurfsentscheidungen ---


@mcp.tool()
def add_design_decision(decision: str, consequence: str, reasoning: str, importance: str, *, parent_name: str) -> str:
    """Fügt eine Entwurfsentscheidung (Design Decision) für Kapitel 9 hinzu."""
    try:
        decision = validate_required(decision, "decision")
        consequence = validate_required(consequence, "consequence")
        reasoning = validate_required(reasoning, "reasoning")
        importance = validate_required(importance, "importance")
    except ValueError as e:
        return _format_error("add_design_decision", e)
    cypher = (
        "MERGE (d:Arc42 {name: $parent_name}) "
        "CREATE (n:Entwurfsentscheidung { "
        "   entscheidung: $decision, "
        "   konsequenz: $consequence, "
        "   begruendung: $reasoning, "
        "   wichtigkeit: $importance "
        "}) "
        "MERGE (d)-[:hasEntwurfsentscheidung]->(n) "
        "RETURN n"
    )
    logger.info("Tool add_design_decision: '%s'", decision[:80])
    try:
        _run_write(
            cypher,
            decision=decision,
            consequence=consequence,
            reasoning=reasoning,
            importance=importance,
            parent_name=parent_name,
        )
        return f"## Success\n\nAdded Design Decision: **{decision}**\n"
    except Exception as e:
        return _format_error("add_design_decision", e)


@mcp.tool()
def update_design_decision(
    old_decision: str,
    new_decision: str = "",
    new_consequence: str = "",
    new_reasoning: str = "",
    *,
    parent_name: str,
) -> str:
    """Aktualisiert eine vorhandene Entwurfsentscheidung in Kapitel 9."""
    try:
        old_decision = validate_required(old_decision, "old_decision")
    except ValueError as e:
        return _format_error("update_design_decision", e)

    logger.info("Tool update_design_decision: '%s'", old_decision[:60])
    set_clauses = []
    if new_decision:
        set_clauses.append("n.entscheidung = $new_decision")
    if new_consequence:
        set_clauses.append("n.konsequenz = $new_consequence")
    if new_reasoning:
        set_clauses.append("n.begruendung = $new_reasoning")

    if not set_clauses:
        return "## Error\n\nMindestens ein neues Feld muss angegeben werden.\n"

    cypher = (
        "MATCH (d:Arc42 {name: $parent_name})-[:hasEntwurfsentscheidung]->(n:Entwurfsentscheidung {entscheidung: $old_decision}) "
        f"SET {', '.join(set_clauses)} "
        "RETURN n"
    )
    try:
        records = _run_write(
            cypher,
            old_decision=old_decision,
            new_decision=new_decision,
            new_consequence=new_consequence,
            new_reasoning=new_reasoning,
            parent_name=parent_name,
        )
        if not records:
            return f"## Not Found\n\nDesign Decision '{old_decision}' not found.\n"
        return f"## Success\n\nUpdated Design Decision: **{old_decision}**\n"
    except Exception as e:
        return _format_error("update_design_decision", e)


@mcp.tool()
def delete_design_decision(decision: str, *, parent_name: str) -> str:
    """Löscht eine Entwurfsentscheidung anhand ihres Textes. Lösche niemals etwas, ohne nochmal nachzufragen!"""
    try:
        decision = validate_required(decision, "decision")
    except ValueError as e:
        return _format_error("delete_design_decision", e)

    cypher = (
        "MATCH (d:Arc42 {name: $parent_name})-[:hasEntwurfsentscheidung]->(n:Entwurfsentscheidung {entscheidung: $decision}) "
        "DETACH DELETE n "
        "RETURN count(n) as c"
    )
    try:
        res = _run_write(cypher, decision=decision, parent_name=parent_name)
        deleted = res[0]["c"]
        if deleted > 0:
            return f"## Success\n\nDeleted Design Decision: **{decision}**\n"
        return "## Warning\n\nNo matching design decision found.\n"
    except Exception as e:
        return _format_error("delete_design_decision", e)

