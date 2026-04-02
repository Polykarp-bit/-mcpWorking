from __future__ import annotations

from ..core import logger, mcp, _format_error, _run_write
from .common import require_confirm, validate_required


# --- Chapter 1: Einführung und Ziele ---


@mcp.tool()
def add_requirement(task: str, *, parent_name: str) -> str:
    """Add a Requirement (Aufgabenstellung) to Chapter 1 – Einführung und Ziele."""
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
def delete_requirement(task: str, *, parent_name: str, confirm: bool = False) -> str:
    """Delete an existing Requirement (Aufgabenstellung) by exact text."""
    guard = require_confirm(confirm, "delete_requirement")
    if guard:
        return guard
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
    """Update an existing Requirement (Aufgabenstellung) in Chapter 1."""
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
    """Add a Quality Goal (Qualitätsziel) for Chapter 1."""
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
def delete_quality_goal(goal: str, *, parent_name: str, confirm: bool = False) -> str:
    """Delete an existing Quality Goal (Qualitätsziel) by its title."""
    guard = require_confirm(confirm, "delete_quality_goal")
    if guard:
        return guard
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
    """Update an existing Quality Goal (Qualitätsziel) in Chapter 1."""
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
def add_stakeholder(role_or_name: str, contact: str = "", expectation: str = "", *, parent_name: str) -> str:
    """Add a Stakeholder for Chapter 1."""
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
def delete_stakeholder(role_or_name: str, *, parent_name: str, confirm: bool = False) -> str:
    """Delete an existing Stakeholder by role/name."""
    guard = require_confirm(confirm, "delete_stakeholder")
    if guard:
        return guard
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
    """Update an existing Stakeholder in Chapter 1."""
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

