from __future__ import annotations

from ..core import logger, mcp, _format_error, _run_write
from .common import require_confirm, validate_required


# --- Chapter 4: Lösungsstrategie ---


@mcp.tool()
def add_solution_strategy(strategy: str, *, parent_name: str) -> str:
    """Fügt eine Lösungsstrategie für Kapitel 4 hinzu."""
    try:
        strategy = validate_required(strategy, "strategy")
    except ValueError as e:
        return _format_error("add_solution_strategy", e)
    cypher = (
        "MERGE (d:Arc42 {name: $parent_name}) "
        "CREATE (n:LoesungsStrategie {strategy: $strategy}) "
        "MERGE (d)-[:hatLoesung]->(n) "
        "RETURN n"
    )
    logger.info("Tool add_solution_strategy aufgerufen")
    try:
        _run_write(cypher, strategy=strategy, parent_name=parent_name)
        return "## Success\n\nAdded Solution Strategy.\n"
    except Exception as e:
        return _format_error("add_solution_strategy", e)


@mcp.tool()
def delete_solution_strategy(*, parent_name: str) -> str:
    """Löscht die Lösungsstrategie für Kapitel 4. Lösche niemals etwas, ohne nochmal nachzufragen!"""
    cypher = (
        "MATCH (d:Arc42 {name: $parent_name})-[:hatLoesung]->(n:LoesungsStrategie) "
        "DETACH DELETE n "
        "RETURN count(n) as c"
    )
    try:
        res = _run_write(cypher, parent_name=parent_name)
        deleted = res[0]["c"]
        if deleted > 0:
            return "## Success\n\nDeleted Solution Strategy entries.\n"
        return "## Warning\n\nNo Solution Strategy entries found.\n"
    except Exception as e:
        return _format_error("delete_solution_strategy", e)


@mcp.tool()
def update_solution_strategy(old_strategy: str, new_strategy: str, *, parent_name: str) -> str:
    """Update a specific Solution Strategy entry."""
    try:
        old_strategy = validate_required(old_strategy, "old_strategy")
        new_strategy = validate_required(new_strategy, "new_strategy")
    except ValueError as e:
        return _format_error("update_solution_strategy", e)

    cypher = (
        "MATCH (d:Arc42 {name: $parent_name})-[:hatLoesung]->(n:LoesungsStrategie {strategy: $old_strategy}) "
        "SET n.strategy = $new_strategy "
        "RETURN n"
    )
    try:
        records = _run_write(
            cypher,
            old_strategy=old_strategy,
            new_strategy=new_strategy,
            parent_name=parent_name,
        )
        if not records:
            return f"## Not Found\n\nSolution Strategy '{old_strategy}' not found.\n"
        return f"## Success\n\nUpdated Solution Strategy: **{old_strategy}**\n"
    except Exception as e:
        return _format_error("update_solution_strategy", e)


# --- Chapter 4: Project Meetings ---


@mcp.tool()
def add_project_meeting(parent_name: str, name: str, frequency: int, repetition: str, meeting_type: str) -> str:
    """Fügt einen Projektmeeting-Eintrag (Kapitel 4) hinzu (z.B. Kick-off, Reviews)."""
    try:
        parent_name = validate_required(parent_name, "parent_name")
        name = validate_required(name, "name")
        repetition = validate_required(repetition, "repetition")
        meeting_type = validate_required(meeting_type, "meeting_type")
    except ValueError as e:
        return _format_error("add_project_meeting", e)

    cypher = (
        "MERGE (d:Arc42 {name: $parent_name}) "
        "CREATE (m:Meeting {name: $name, frequency: $frequency, repetition: $repetition, type: $meeting_type}) "
        "MERGE (d)-[:hasMeeting]->(m) "
        "RETURN m"
    )
    try:
        _run_write(
            cypher,
            parent_name=parent_name,
            name=name,
            frequency=frequency,
            repetition=repetition,
            meeting_type=meeting_type,
        )
        return f"## Success\n\nAdded Project Meeting: **{name}**\n"
    except Exception as e:
        return _format_error("add_project_meeting", e)


@mcp.tool()
def delete_project_meeting(parent_name: str, name: str) -> str:
    """Löscht einen Projektmeeting-Eintrag (Kapitel 4). Lösche niemals etwas, ohne nochmal nachzufragen!"""
    try:
        parent_name = validate_required(parent_name, "parent_name")
        name = validate_required(name, "name")
    except ValueError as e:
        return _format_error("delete_project_meeting", e)

    cypher = (
        "MATCH (d:Arc42 {name: $parent_name})-[r:hasMeeting]->(m:Meeting {name: $name}) "
        "DETACH DELETE m "
        "RETURN count(m) as c"
    )
    try:
        res = _run_write(cypher, name=name, parent_name=parent_name)
        deleted = res[0]["c"]
        if deleted > 0:
            return f"## Success\n\nDeleted Project Meeting: **{name}**\n"
        return f"## Warning\n\nNo matching meeting '{name}' found.\n"
    except Exception as e:
        return _format_error("delete_project_meeting", e)


@mcp.tool()
def update_project_meeting(
    parent_name: str,
    old_name: str,
    new_name: str = "",
    new_frequency: int | None = None,
    new_repetition: str = "",
    new_meeting_type: str = "",
) -> str:
    """Update a specific Project Meeting (Chapter 4 – Solution Strategy)."""
    try:
        parent_name = validate_required(parent_name, "parent_name")
        old_name = validate_required(old_name, "old_name")
    except ValueError as e:
        return _format_error("update_project_meeting", e)

    set_clauses = []
    if new_name:
        set_clauses.append("m.name = $new_name")
    if new_frequency is not None:
        set_clauses.append("m.frequency = $new_frequency")
    if new_repetition:
        set_clauses.append("m.repetition = $new_repetition")
    if new_meeting_type:
        set_clauses.append("m.type = $new_meeting_type")
    if not set_clauses:
        return "## Error\n\nMindestens ein neues Feld muss angegeben werden.\n"

    cypher = (
        "MATCH (d:Arc42 {name: $parent_name})-[:hasMeeting]->(m:Meeting {name: $old_name}) "
        f"SET {', '.join(set_clauses)} "
        "RETURN m"
    )
    try:
        records = _run_write(
            cypher,
            parent_name=parent_name,
            old_name=old_name,
            new_name=new_name,
            new_frequency=new_frequency,
            new_repetition=new_repetition,
            new_meeting_type=new_meeting_type,
        )
        if not records:
            return f"## Not Found\n\nMeeting '{old_name}' not found.\n"
        return f"## Success\n\nUpdated Project Meeting: **{old_name}**\n"
    except Exception as e:
        return _format_error("update_project_meeting", e)

