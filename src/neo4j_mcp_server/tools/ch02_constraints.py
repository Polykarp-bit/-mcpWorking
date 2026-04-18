from __future__ import annotations

from ..core import logger, mcp, _format_error, _run_write
from .common import require_confirm, validate_required


# --- Chapter 2: Randbedingungen ---


@mcp.tool()
def add_technical_constraint(constraint: str, background: str, *, parent_name: str) -> str:
    """Add a Technical Constraint (Technische Randbedingung) for Chapter 2."""
    try:
        constraint = validate_required(constraint, "constraint")
        background = validate_required(background, "background")
    except ValueError as e:
        return _format_error("add_technical_constraint", e)
    cypher = (
        "MERGE (d:Arc42 {name: $parent_name}) "
        "CREATE (n:TechnischeRandbedingung {randbedingung: $constraint, hintergrund: $background}) "
        "MERGE (d)-[:hatTechnischRandbedingung]->(n) "
        "RETURN n"
    )
    logger.info("Tool add_technical_constraint: '%s'", constraint[:80])
    try:
        _run_write(cypher, constraint=constraint, background=background, parent_name=parent_name)
        return f"## Success\n\nAdded Technical Constraint: **{constraint}**\nBackground: {background}\n"
    except Exception as e:
        return _format_error("add_technical_constraint", e)


@mcp.tool()
def add_organizational_constraint(constraint: str, background: str, *, parent_name: str) -> str:
    """Add an Organizational Constraint (Organisatorische Randbedingung) for Chapter 2."""
    try:
        constraint = validate_required(constraint, "constraint")
        background = validate_required(background, "background")
    except ValueError as e:
        return _format_error("add_organizational_constraint", e)
    cypher = (
        "MERGE (d:Arc42 {name: $parent_name}) "
        "CREATE (n:OrganisatorischRandbedingung {randbedingung: $constraint, hintergrund: $background}) "
        "MERGE (d)-[:hatOrganisatorischRandbedingung]->(n) "
        "RETURN n"
    )
    logger.info("Tool add_organizational_constraint: '%s'", constraint[:80])
    try:
        _run_write(cypher, constraint=constraint, background=background, parent_name=parent_name)
        return f"## Success\n\nAdded Organizational Constraint: **{constraint}**\n"
    except Exception as e:
        return _format_error("add_organizational_constraint", e)


@mcp.tool()
def add_ecological_constraint(constraint: str, background: str, *, parent_name: str) -> str:
    """Add an Ecological Constraint (Ökologische Randbedingung) for Chapter 2."""
    try:
        constraint = validate_required(constraint, "constraint")
        background = validate_required(background, "background")
    except ValueError as e:
        return _format_error("add_ecological_constraint", e)
    cypher = (
        "MERGE (d:Arc42 {name: $parent_name}) "
        "CREATE (n:OekologischeRandbedingung {randbedingung: $constraint, hintergrund: $background}) "
        "MERGE (d)-[:hatOekologischeRandbedingung]->(n) "
        "RETURN n"
    )
    logger.info("Tool add_ecological_constraint: '%s'", constraint[:80])
    try:
        _run_write(cypher, constraint=constraint, background=background, parent_name=parent_name)
        return f"## Success\n\nAdded Ecological Constraint: **{constraint}**\n"
    except Exception as e:
        return _format_error("add_ecological_constraint", e)


@mcp.tool()
def delete_constraint(constraint: str, constraint_type: str, *, parent_name: str) -> str:
    """Delete a constraint from Chapter 2. Lösche niemals etwas, ohne nochmal nachzufragen!"""
    try:
        constraint = validate_required(constraint, "constraint")
        constraint_type = validate_required(constraint_type, "constraint_type").lower()
    except ValueError as e:
        return _format_error("delete_constraint", e)

    cfg = {
        "technical": ("TechnischeRandbedingung", "hatTechnischRandbedingung", "randbedingung"),
        "organizational": ("OrganisatorischRandbedingung", "hatOrganisatorischRandbedingung", "randbedingung"),
        "ecological": ("OekologischeRandbedingung", "hatOekologischeRandbedingung", "randbedingung"),
    }.get(constraint_type)
    if not cfg:
        return (
            "## Error\n\n"
            "Ungültiger `constraint_type`. Erlaubt: technical, organizational, ecological.\n"
        )

    label, rel, prop = cfg
    cypher = (
        f"MATCH (d:Arc42 {{name: $parent_name}})-[:{rel}]->(n:{label} {{{prop}: $constraint}}) "
        "DETACH DELETE n "
        "RETURN count(n) as c"
    )
    try:
        res = _run_write(cypher, constraint=constraint, parent_name=parent_name)
        deleted = res[0]["c"]
        if deleted > 0:
            return f"## Success\n\nDeleted Constraint ({constraint_type}): **{constraint}**\n"
        return "## Warning\n\nNo matching constraint found.\n"
    except Exception as e:
        return _format_error("delete_constraint", e)


@mcp.tool()
def update_constraint(
    old_constraint: str,
    constraint_type: str,
    new_constraint: str = "",
    new_background: str = "",
    *,
    parent_name: str,
) -> str:
    """Update a Chapter-2 constraint (technical/organizational/ecological)."""
    try:
        old_constraint = validate_required(old_constraint, "old_constraint")
        constraint_type = validate_required(constraint_type, "constraint_type").lower()
    except ValueError as e:
        return _format_error("update_constraint", e)

    cfg = {
        "technical": ("TechnischeRandbedingung", "hatTechnischRandbedingung"),
        "organizational": ("OrganisatorischRandbedingung", "hatOrganisatorischRandbedingung"),
        "ecological": ("OekologischeRandbedingung", "hatOekologischeRandbedingung"),
    }.get(constraint_type)
    if not cfg:
        return "## Error\n\nUngültiger `constraint_type`. Erlaubt: technical, organizational, ecological.\n"

    set_clauses = []
    if new_constraint:
        set_clauses.append("n.randbedingung = $new_constraint")
    if new_background:
        set_clauses.append("n.hintergrund = $new_background")
    if not set_clauses:
        return "## Error\n\nMindestens ein neues Feld muss angegeben werden.\n"

    label, rel = cfg
    cypher = (
        f"MATCH (d:Arc42 {{name: $parent_name}})-[:{rel}]->(n:{label} {{randbedingung: $old_constraint}}) "
        f"SET {', '.join(set_clauses)} "
        "RETURN n"
    )
    try:
        records = _run_write(
            cypher,
            old_constraint=old_constraint,
            new_constraint=new_constraint,
            new_background=new_background,
            parent_name=parent_name,
        )
        if not records:
            return f"## Not Found\n\nConstraint '{old_constraint}' not found.\n"
        return f"## Success\n\nUpdated Constraint: **{old_constraint}**\n"
    except Exception as e:
        return _format_error("update_constraint", e)


@mcp.tool()
def add_convention(convention: str, explanation: str, *, parent_name: str) -> str:
    """Add a Convention (Konvention) for Chapter 2."""
    try:
        convention = validate_required(convention, "convention")
        explanation = validate_required(explanation, "explanation")
    except ValueError as e:
        return _format_error("add_convention", e)
    cypher = (
        "MERGE (d:Arc42 {name: $parent_name}) "
        "CREATE (n:Konvention {konvention: $convention, erlaeuterung: $explanation}) "
        "MERGE (d)-[:hatKonvention]->(n) "
        "RETURN n"
    )
    logger.info("Tool add_convention: '%s'", convention[:80])
    try:
        _run_write(cypher, convention=convention, explanation=explanation, parent_name=parent_name)
        return f"## Success\n\nAdded Convention: **{convention}**\nExplanation: {explanation}\n"
    except Exception as e:
        return _format_error("add_convention", e)


@mcp.tool()
def update_convention(old_convention: str, new_convention: str = "", new_explanation: str = "", *, parent_name: str) -> str:
    """Update an existing Convention in Chapter 2."""
    try:
        old_convention = validate_required(old_convention, "old_convention")
    except ValueError as e:
        return _format_error("update_convention", e)

    set_clauses = []
    if new_convention:
        set_clauses.append("n.konvention = $new_convention")
    if new_explanation:
        set_clauses.append("n.erlaeuterung = $new_explanation")
    if not set_clauses:
        return "## Error\n\nMindestens ein neues Feld muss angegeben werden.\n"

    cypher = (
        "MATCH (d:Arc42 {name: $parent_name})-[:hatKonvention]->(n:Konvention {konvention: $old_convention}) "
        f"SET {', '.join(set_clauses)} "
        "RETURN n"
    )
    try:
        records = _run_write(
            cypher,
            old_convention=old_convention,
            new_convention=new_convention,
            new_explanation=new_explanation,
            parent_name=parent_name,
        )
        if not records:
            return f"## Not Found\n\nConvention '{old_convention}' not found.\n"
        return f"## Success\n\nUpdated Convention: **{old_convention}**\n"
    except Exception as e:
        return _format_error("update_convention", e)


@mcp.tool()
def delete_convention(parent_name: str, convention: str) -> str:
    """Delete a Convention (Konvention). Lösche niemals etwas, ohne nochmal nachzufragen!"""
    try:
        convention = validate_required(convention, "convention")
    except ValueError as e:
        return _format_error("delete_convention", e)

    cypher = (
        "MATCH (d:Arc42 {name: $parent_name})-[r:hatKonvention]->(n:Konvention {konvention: $convention}) "
        "DETACH DELETE n "
        "RETURN count(n) as c"
    )
    try:
        res = _run_write(cypher, convention=convention, parent_name=parent_name)
        deleted = res[0]["c"]
        if deleted > 0:
            return f"## Success\n\nDeleted Convention: **{convention}**\n"
        return f"## Warning\n\nNo matching convention '{convention}' found.\n"
    except Exception as e:
        return _format_error("delete_convention", e)

