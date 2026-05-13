from __future__ import annotations

from ..core import logger, mcp, _format_error, _run_write
from .common import validate_required


# --- Chapter 4: Lösungsstrategie ---


@mcp.tool()
def add_solution_strategy(
    strategy: str,
    qg_id: str = "null",
    n_id: str = "null",
    *,
    parent_name: str,
) -> str:
    """Fügt eine Lösungsstrategie für Kapitel 4 hinzu.

    Args:
        strategy: Beschreibungstext der Lösungsstrategie.
        qg_id: Optional. Referenz-ID eines verknüpften Qualitätsziels als Integer-String
            (z. B. "157"). Default "null" = nicht verknüpft (Sentinel-Wert wie im UI).
        n_id: Optional. Referenz-ID eines verknüpften Nachhaltigkeitsziels als
            Integer-String. Default "null" = nicht verknüpft.
        parent_name: Name des arc42-Projekts.
    """
    try:
        strategy = validate_required(strategy, "strategy")
    except ValueError as e:
        return _format_error("add_solution_strategy", e)
    cypher = (
        "MERGE (d:Arc42 {name: $parent_name}) "
        "CREATE (n:LoesungsStrategie {strategy: $strategy, qgId: $qg_id, nId: $n_id}) "
        "MERGE (d)-[:hatLoesung]->(n) "
        "RETURN n"
    )
    logger.info("Tool add_solution_strategy aufgerufen")
    try:
        _run_write(
            cypher,
            strategy=strategy,
            qg_id=qg_id,
            n_id=n_id,
            parent_name=parent_name,
        )
        return "## Success\n\nAdded Solution Strategy.\n"
    except Exception as e:
        return _format_error("add_solution_strategy", e)


@mcp.tool()
def delete_solution_strategy(strategy: str = "", *, parent_name: str) -> str:
    """Löscht eine Lösungsstrategie für Kapitel 4.

    Wird `strategy` angegeben, wird nur dieser eine Eintrag gelöscht.
    Ohne Angabe werden **alle** Lösungsstrategien des Projekts gelöscht.
    Lösche niemals etwas, ohne nochmal nachzufragen!
    """
    if strategy:
        cypher = (
            "MATCH (d:Arc42 {name: $parent_name})-[:hatLoesung]->(n:LoesungsStrategie {strategy: $strategy}) "
            "DETACH DELETE n "
            "RETURN count(n) as c"
        )
        params = {"parent_name": parent_name, "strategy": strategy}
    else:
        cypher = (
            "MATCH (d:Arc42 {name: $parent_name})-[:hatLoesung]->(n:LoesungsStrategie) "
            "DETACH DELETE n "
            "RETURN count(n) as c"
        )
        params = {"parent_name": parent_name}
    try:
        res = _run_write(cypher, **params)
        deleted = res[0]["c"]
        if deleted > 0:
            return f"## Success\n\nDeleted {deleted} Solution Strategy entry/entries.\n"
        return "## Warning\n\nNo Solution Strategy entries found.\n"
    except Exception as e:
        return _format_error("delete_solution_strategy", e)


@mcp.tool()
def update_solution_strategy(
    old_strategy: str,
    new_strategy: str = "",
    new_qg_id: str = "",
    new_n_id: str = "",
    *,
    parent_name: str,
) -> str:
    """Aktualisiert einen bestimmten Lösungsstrategie-Eintrag.

    Args:
        old_strategy: Aktueller Strategietext zur Identifikation des Knotens.
        new_strategy: Optional neuer Strategietext.
        new_qg_id: Optional neue Qualitätsziel-Referenz-ID ("null" für leer).
        new_n_id: Optional neue Nachhaltigkeitsziel-Referenz-ID ("null" für leer).
        parent_name: Name des arc42-Projekts.
    """
    try:
        old_strategy = validate_required(old_strategy, "old_strategy")
    except ValueError as e:
        return _format_error("update_solution_strategy", e)

    set_clauses = []
    if new_strategy:
        set_clauses.append("n.strategy = $new_strategy")
    if new_qg_id:
        set_clauses.append("n.qgId = $new_qg_id")
    if new_n_id:
        set_clauses.append("n.nId = $new_n_id")
    if not set_clauses:
        return "## Error\n\nMindestens ein neues Feld muss angegeben werden.\n"

    cypher = (
        "MATCH (d:Arc42 {name: $parent_name})-[:hatLoesung]->(n:LoesungsStrategie {strategy: $old_strategy}) "
        f"SET {', '.join(set_clauses)} "
        "RETURN n"
    )
    try:
        records = _run_write(
            cypher,
            old_strategy=old_strategy,
            new_strategy=new_strategy,
            new_qg_id=new_qg_id,
            new_n_id=new_n_id,
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
    """Aktualisiert ein bestimmtes Projektmeeting (Kapitel 4 – Lösungsstrategie)."""
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

