from __future__ import annotations

from ..core import logger, mcp, _format_error, _run_write
from .common import validate_required


# --- Kapitel 1: Einführung und Ziele ---


@mcp.tool()
def add_requirement(task: str, *, parent_name: str) -> str:
    """Fügt eine Aufgabenstellung (Requirement) für Kapitel 1 – Einführung und Ziele hinzu."""
    try:
        task = validate_required(task, "task")
    except ValueError as e:
        return _format_error("add_requirement", e)

    logger.info("Tool add_requirement: '%s'", task[:80])
    cypher = (
        "MERGE (d:Arc42 {name: $parent_name}) "
        "CREATE (n:Aufgabenstellung {aufgabe: $task}) "
        "MERGE (d)-[:hasRequirement]->(n) "
        "RETURN n"
    )
    try:
        _run_write(cypher, task=task, parent_name=parent_name)
        return f"## Success\n\nAdded Requirement: {task}\n"
    except Exception as e:
        return _format_error("add_requirement", e)


@mcp.tool()
def delete_requirement(task: str, *, parent_name: str) -> str:
    """Löscht eine vorhandene Aufgabenstellung (Requirement) anhand des exakten Textes. Lösche niemals etwas, ohne nochmal nachzufragen!"""
    try:
        task = validate_required(task, "task")
    except ValueError as e:
        return _format_error("delete_requirement", e)

    cypher = (
        "MATCH (d:Arc42 {name: $parent_name})-[:hasRequirement]->(n:Aufgabenstellung {aufgabe: $task}) "
        "DETACH DELETE n "
        "RETURN count(n) as c"
    )
    try:
        res = _run_write(cypher, task=task, parent_name=parent_name)
        deleted = res[0]["c"]
        if deleted > 0:
            return f"## Success\n\nDeleted Requirement: **{task}**\n"
        return "## Warning\n\nNo matching requirement found.\n"
    except Exception as e:
        return _format_error("delete_requirement", e)


@mcp.tool()
def update_requirement(old_task: str, new_task: str, *, parent_name: str) -> str:
    """Aktualisiert eine vorhandene Aufgabenstellung (Requirement) in Kapitel 1."""
    try:
        old_task = validate_required(old_task, "old_task")
        new_task = validate_required(new_task, "new_task")
    except ValueError as e:
        return _format_error("update_requirement", e)

    logger.info("Tool update_requirement: '%s' → '%s'", old_task[:40], new_task[:40])
    cypher = (
        "MATCH (d:Arc42 {name: $parent_name})-[:hasRequirement]->(n:Aufgabenstellung {aufgabe: $old_task}) "
        "SET n.aufgabe = $new_task "
        "RETURN n"
    )
    try:
        records = _run_write(cypher, old_task=old_task, new_task=new_task, parent_name=parent_name)
        if not records:
            return f"## Not Found\n\nRequirement '{old_task}' not found.\n"
        return f"## Success\n\nUpdated Requirement: **{old_task}** → **{new_task}**\n"
    except Exception as e:
        return _format_error("update_requirement", e)


@mcp.tool()
def add_quality_goal(goal: str, motivation: str, criteria: str = "Funktionalität", *, parent_name: str) -> str:
    """Fügt ein Qualitätsziel (Quality Goal) für Kapitel 1 hinzu."""
    try:
        goal = validate_required(goal, "goal")
        motivation = validate_required(motivation, "motivation")
    except ValueError as e:
        return _format_error("add_quality_goal", e)

    cypher = (
        "MERGE (d:Arc42 {name: $parent_name}) "
        "MERGE (n:Qualitaetsziel {qualitaetsziel: $goal, motivation: $motivation}) "
        "MERGE (d)-[:hasQualityGoal]->(n) "
        "WITH n "
        "UNWIND split($criteria, ',') AS crit "
        "   MERGE (c:Qualitaetskriterium {qualitaetskriterium: trim(crit)}) "
        "   MERGE (n)-[:hasQualityCriteria]->(c) "
        "RETURN n"
    )
    logger.info("Tool add_quality_goal: '%s'", goal)
    try:
        _run_write(cypher, goal=goal, motivation=motivation, criteria=criteria, parent_name=parent_name)
        return (
            f"## Success\n\nAdded Quality Goal: **{goal}** linked to criteria **{criteria}**\n"
            f"Motivation: {motivation}\n"
        )
    except Exception as e:
        return _format_error("add_quality_goal", e)


@mcp.tool()
def delete_quality_goal(goal: str, *, parent_name: str) -> str:
    """Löscht ein vorhandenes Qualitätsziel (Quality Goal) anhand seines Titels. Lösche niemals etwas, ohne nochmal nachzufragen!"""
    try:
        goal = validate_required(goal, "goal")
    except ValueError as e:
        return _format_error("delete_quality_goal", e)

    cypher = (
        "MATCH (d:Arc42 {name: $parent_name})-[:hasQualityGoal]->(n:Qualitaetsziel {qualitaetsziel: $goal}) "
        "DETACH DELETE n "
        "RETURN count(n) as c"
    )
    try:
        res = _run_write(cypher, goal=goal, parent_name=parent_name)
        deleted = res[0]["c"]
        if deleted > 0:
            return f"## Success\n\nDeleted Quality Goal: **{goal}**\n"
        return f"## Warning\n\nNo matching quality goal '{goal}' found.\n"
    except Exception as e:
        return _format_error("delete_quality_goal", e)


@mcp.tool()
def update_quality_goal(old_goal: str, new_goal: str = "", new_motivation: str = "", *, parent_name: str) -> str:
    """Aktualisiert ein vorhandenes Qualitätsziel (Quality Goal) in Kapitel 1."""
    try:
        old_goal = validate_required(old_goal, "old_goal")
    except ValueError as e:
        return _format_error("update_quality_goal", e)

    logger.info("Tool update_quality_goal: '%s'", old_goal)
    set_clauses = []
    if new_goal:
        set_clauses.append("n.qualitaetsziel = $new_goal")
    if new_motivation:
        set_clauses.append("n.motivation = $new_motivation")

    if not set_clauses:
        return "## Error\n\nMindestens ein neues Feld muss angegeben werden.\n"

    cypher = (
        "MATCH (d:Arc42 {name: $parent_name})-[:hasQualityGoal]->(n:Qualitaetsziel {qualitaetsziel: $old_goal}) "
        f"SET {', '.join(set_clauses)} "
        "RETURN n"
    )
    try:
        records = _run_write(
            cypher,
            old_goal=old_goal,
            new_goal=new_goal,
            new_motivation=new_motivation,
            parent_name=parent_name,
        )
        if not records:
            return f"## Not Found\n\nQuality Goal '{old_goal}' not found.\n"
        return f"## Success\n\nUpdated Quality Goal: **{old_goal}**\n"
    except Exception as e:
        return _format_error("update_quality_goal", e)


@mcp.tool()
def add_sustainability_goal(
    goal: str,
    motivation: str,
    prioritaet: str = "",
    einsparung: str = "",
    *,
    parent_name: str,
) -> str:
    """Fügt ein Nachhaltigkeitsziel (Sustainability Goal) für Kapitel 1 – Einführung und Ziele hinzu."""
    try:
        goal = validate_required(goal, "goal")
        motivation = validate_required(motivation, "motivation")
    except ValueError as e:
        return _format_error("add_sustainability_goal", e)

    cypher = (
        "MERGE (d:Arc42 {name: $parent_name}) "
        "MERGE (n:Nachhaltigkeitsziele {greengoal: $goal}) "
        "SET n.motivation = $motivation, n.prio = $prioritaet, n.saving = $einsparung "
        "MERGE (d)-[:hasNachhaltigkeitsziele]->(n) "
        "RETURN n"
    )
    logger.info("Tool add_sustainability_goal: '%s'", goal)
    try:
        _run_write(
            cypher,
            goal=goal,
            motivation=motivation,
            prioritaet=prioritaet,
            einsparung=einsparung,
            parent_name=parent_name,
        )
        return (
            f"## Success\n\nAdded Sustainability Goal: **{goal}**\n"
            f"Motivation: {motivation}\n"
            f"Priorität: {prioritaet or '-'} | Einsparung: {einsparung or '-'}\n"
        )
    except Exception as e:
        return _format_error("add_sustainability_goal", e)


@mcp.tool()
def delete_sustainability_goal(goal: str, *, parent_name: str) -> str:
    """Löscht ein vorhandenes Nachhaltigkeitsziel (Sustainability Goal) anhand seines Titels. Lösche niemals etwas, ohne nochmal nachzufragen!"""
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
        return f"## Warning\n\nNo matching sustainability goal '{goal}' found.\n"
    except Exception as e:
        return _format_error("delete_sustainability_goal", e)


@mcp.tool()
def update_sustainability_goal(
    old_goal: str,
    new_goal: str = "",
    new_motivation: str = "",
    new_prioritaet: str = "",
    new_einsparung: str = "",
    *,
    parent_name: str,
) -> str:
    """Aktualisiert ein vorhandenes Nachhaltigkeitsziel (Sustainability Goal) in Kapitel 1."""
    try:
        old_goal = validate_required(old_goal, "old_goal")
    except ValueError as e:
        return _format_error("update_sustainability_goal", e)

    logger.info("Tool update_sustainability_goal: '%s'", old_goal)
    set_clauses = []
    if new_goal:
        set_clauses.append("n.greengoal = $new_goal")
    if new_motivation:
        set_clauses.append("n.motivation = $new_motivation")
    if new_prioritaet:
        set_clauses.append("n.prio = $new_prioritaet")
    if new_einsparung:
        set_clauses.append("n.saving = $new_einsparung")

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
            new_prioritaet=new_prioritaet,
            new_einsparung=new_einsparung,
            parent_name=parent_name,
        )
        if not records:
            return f"## Not Found\n\nSustainability Goal '{old_goal}' not found.\n"
        return f"## Success\n\nUpdated Sustainability Goal: **{old_goal}**\n"
    except Exception as e:
        return _format_error("update_sustainability_goal", e)


@mcp.tool()
def add_stakeholder(role_or_name: str, contact: str = "", expectation: str = "", *, parent_name: str) -> str:
    """Fügt einen Stakeholder für Kapitel 1 hinzu."""
    try:
        role_or_name = validate_required(role_or_name, "role_or_name")
    except ValueError as e:
        return _format_error("add_stakeholder", e)

    cypher = (
        "MERGE (d:Arc42 {name: $parent_name}) "
        "CREATE (n:Stakeholder {roleOrName: $role_org_name, contact: $contact, expectation: $expectation}) "
        "MERGE (d)-[:hasStakeholder]->(n) "
        "RETURN n"
    )
    logger.info("Tool add_stakeholder: '%s'", role_or_name)
    try:
        _run_write(
            cypher,
            role_org_name=role_or_name,
            contact=contact,
            expectation=expectation,
            parent_name=parent_name,
        )
        return f"## Success\n\nAdded Stakeholder: **{role_or_name}**\n"
    except Exception as e:
        return _format_error("add_stakeholder", e)


@mcp.tool()
def delete_stakeholder(role_or_name: str, *, parent_name: str) -> str:
    """Löscht einen vorhandenen Stakeholder anhand der Rolle/des Namens. Lösche niemals etwas, ohne nochmal nachzufragen!"""
    try:
        role_or_name = validate_required(role_or_name, "role_or_name")
    except ValueError as e:
        return _format_error("delete_stakeholder", e)

    cypher = (
        "MATCH (d:Arc42 {name: $parent_name})-[:hasStakeholder]->(n:Stakeholder {roleOrName: $role_or_name}) "
        "DETACH DELETE n "
        "RETURN count(n) as c"
    )
    try:
        res = _run_write(cypher, role_or_name=role_or_name, parent_name=parent_name)
        deleted = res[0]["c"]
        if deleted > 0:
            return f"## Success\n\nDeleted Stakeholder: **{role_or_name}**\n"
        return f"## Warning\n\nNo matching stakeholder '{role_or_name}' found.\n"
    except Exception as e:
        return _format_error("delete_stakeholder", e)


@mcp.tool()
def update_stakeholder(
    old_name: str,
    new_name: str = "",
    new_contact: str = "",
    new_expectation: str = "",
    *,
    parent_name: str,
) -> str:
    """Aktualisiert einen vorhandenen Stakeholder in Kapitel 1."""
    try:
        old_name = validate_required(old_name, "old_name")
    except ValueError as e:
        return _format_error("update_stakeholder", e)

    logger.info("Tool update_stakeholder: '%s'", old_name)
    set_clauses = []
    if new_name:
        set_clauses.append("n.roleOrName = $new_name")
    if new_contact:
        set_clauses.append("n.contact = $new_contact")
    if new_expectation:
        set_clauses.append("n.expectation = $new_expectation")

    if not set_clauses:
        return "## Error\n\nMindestens ein neues Feld muss angegeben werden.\n"

    cypher = (
        "MATCH (d:Arc42 {name: $parent_name})-[:hasStakeholder]->(n:Stakeholder {roleOrName: $old_name}) "
        f"SET {', '.join(set_clauses)} "
        "RETURN n"
    )
    try:
        records = _run_write(
            cypher,
            old_name=old_name,
            new_name=new_name,
            new_contact=new_contact,
            new_expectation=new_expectation,
            parent_name=parent_name,
        )
        if not records:
            return f"## Not Found\n\nStakeholder '{old_name}' not found.\n"
        return f"## Success\n\nUpdated Stakeholder: **{old_name}**\n"
    except Exception as e:
        return _format_error("update_stakeholder", e)

