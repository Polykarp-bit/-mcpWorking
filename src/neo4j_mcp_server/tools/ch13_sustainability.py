from __future__ import annotations

from ..core import logger, mcp, _format_error, _run_write
from .common import require_confirm, validate_required


# --- Chapter 13: Nachhaltigkeit ---


@mcp.tool()
def add_sustainability_goal(goal: str, motivation: str, priority: str, saving: str, *, parent_name: str) -> str:
    """Add a Sustainability Goal (Kap. 13) to arc42 documentation."""
    try:
        goal = validate_required(goal, "goal")
        motivation = validate_required(motivation, "motivation")
        priority = validate_required(priority, "priority")
        saving = validate_required(saving, "saving")
    except ValueError as e:
        return _format_error("add_sustainability_goal", e)

    # Keep schema compatible with `read_arc42_chapter` mapping (Nachhaltigkeitsziele/greengoal/prio/saving).
    cypher = (
        "MERGE (d:Arc42 {name: $parent_name}) "
        "CREATE (n:Nachhaltigkeitsziele { "
        "   greengoal: $goal, "
        "   motivation: $motivation, "
        "   prio: $priority, "
        "   saving: $saving "
        "}) "
        "MERGE (d)-[:hasNachhaltigkeitsziele]->(n) "
        "RETURN n"
    )
    logger.info("Tool add_sustainability_goal: '%s'", goal)
    try:
        _run_write(
            cypher,
            goal=goal,
            motivation=motivation,
            priority=priority,
            saving=saving,
            parent_name=parent_name,
        )
        return f"## Success\n\nAdded Sustainability Goal: **{goal}**\n"
    except Exception as e:
        return _format_error("add_sustainability_goal", e)


@mcp.tool()
def delete_sustainability_goal(goal: str, *, parent_name: str) -> str:
    """Delete a Sustainability Goal (Kap. 13) by goal title. Lösche niemals etwas, ohne nochmal nachzufragen!"""
    try:
        goal = validate_required(goal, "goal")
    except ValueError as e:
        return _format_error("delete_sustainability_goal", e)

    cypher = (
        "MATCH (d:Arc42 {name: $parent_name})-[:hasNachhaltigkeitsziele]->(n:Nachhaltigkeitsziele {greengoal: $goal}) "
        "DETACH DELETE n "
        "RETURN count(n) as c"
    )
    try:
        res = _run_write(cypher, goal=goal, parent_name=parent_name)
        deleted = res[0]["c"]
        if deleted > 0:
            return f"## Success\n\nDeleted Sustainability Goal: **{goal}**\n"
        return "## Warning\n\nNo matching sustainability goal found.\n"
    except Exception as e:
        return _format_error("delete_sustainability_goal", e)


@mcp.tool()
def update_sustainability_goal(
    old_goal: str,
    new_goal: str = "",
    new_motivation: str = "",
    new_priority: str = "",
    new_saving: str = "",
    *,
    parent_name: str,
) -> str:
    """Update an existing Sustainability Goal (Kap. 13)."""
    try:
        old_goal = validate_required(old_goal, "old_goal")
    except ValueError as e:
        return _format_error("update_sustainability_goal", e)

    set_clauses = []
    if new_goal:
        set_clauses.append("n.greengoal = $new_goal")
    if new_motivation:
        set_clauses.append("n.motivation = $new_motivation")
    if new_priority:
        set_clauses.append("n.prio = $new_priority")
    if new_saving:
        set_clauses.append("n.saving = $new_saving")
    if not set_clauses:
        return "## Error\n\nMindestens ein neues Feld muss angegeben werden.\n"

    cypher = (
        "MATCH (d:Arc42 {name: $parent_name})-[:hasNachhaltigkeitsziele]->(n:Nachhaltigkeitsziele {greengoal: $old_goal}) "
        f"SET {', '.join(set_clauses)} "
        "RETURN n"
    )
    try:
        records = _run_write(
            cypher,
            old_goal=old_goal,
            new_goal=new_goal,
            new_motivation=new_motivation,
            new_priority=new_priority,
            new_saving=new_saving,
            parent_name=parent_name,
        )
        if not records:
            return f"## Not Found\n\nSustainability Goal '{old_goal}' not found.\n"
        return f"## Success\n\nUpdated Sustainability Goal: **{old_goal}**\n"
    except Exception as e:
        return _format_error("update_sustainability_goal", e)

