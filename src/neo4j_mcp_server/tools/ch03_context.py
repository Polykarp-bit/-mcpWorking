from __future__ import annotations

from ..core import logger, mcp, _format_error, _run_write
from .common import require_confirm, validate_required


# --- Chapter 3: Kontextabgrenzung ---


@mcp.tool()
def add_business_context(
    partner: str,
    input_data: str,
    output_data: str,
    description: str,
    risks: str,
    *,
    parent_name: str,
) -> str:
    """Add Business Context (Fachlicher Kontext) for Chapter 3."""
    try:
        partner = validate_required(partner, "partner")
        description = validate_required(description, "description")
    except ValueError as e:
        return _format_error("add_business_context", e)
    cypher = (
        "MERGE (d:Arc42 {name: $parent_name}) "
        "WITH d "
        "OPTIONAL MATCH (d)-[:hasFachlicherKontext]->(old:FachlicherKontext) "
        "DETACH DELETE old "
        "WITH d "
        "CREATE (n:FachlicherKontext { "
        "   partner: $partner, "
        "   input: $input, "
        "   output: $output, "
        "   beschreibung: $description, "
        "   risiken: $risks "
        "}) "
        "MERGE (d)-[:hasFachlicherKontext]->(n) "
        "RETURN n"
    )
    logger.info("Tool add_business_context: partner='%s'", partner)
    try:
        _run_write(
            cypher,
            partner=partner,
            input=input_data,
            output=output_data,
            description=description,
            risks=risks,
            parent_name=parent_name,
        )
        return f"## Success\n\nAdded Business Context with Partner: **{partner}**\n"
    except Exception as e:
        return _format_error("add_business_context", e)


@mcp.tool()
def delete_business_context(*, parent_name: str) -> str:
    """Delete the current Business Context (Fachlicher Kontext) singleton for Chapter 3. Lösche niemals etwas, ohne nochmal nachzufragen!"""
    cypher = (
        "MATCH (d:Arc42 {name: $parent_name})-[:hasFachlicherKontext]->(n:FachlicherKontext) "
        "DETACH DELETE n "
        "RETURN count(n) as c"
    )
    try:
        res = _run_write(cypher, parent_name=parent_name)
        deleted = res[0]["c"]
        if deleted > 0:
            return "## Success\n\nDeleted Business Context.\n"
        return "## Warning\n\nNo Business Context found.\n"
    except Exception as e:
        return _format_error("delete_business_context", e)


@mcp.tool()
def update_business_context(
    partner: str = "",
    input_data: str = "",
    output_data: str = "",
    description: str = "",
    risks: str = "",
    *,
    parent_name: str,
) -> str:
    """Update the current Business Context singleton."""
    set_clauses = []
    if partner:
        set_clauses.append("n.partner = $partner")
    if input_data:
        set_clauses.append("n.input = $input_data")
    if output_data:
        set_clauses.append("n.output = $output_data")
    if description:
        set_clauses.append("n.beschreibung = $description")
    if risks:
        set_clauses.append("n.risiken = $risks")
    if not set_clauses:
        return "## Error\n\nMindestens ein neues Feld muss angegeben werden.\n"

    cypher = (
        "MATCH (d:Arc42 {name: $parent_name})-[:hasFachlicherKontext]->(n:FachlicherKontext) "
        f"SET {', '.join(set_clauses)} "
        "RETURN n"
    )
    try:
        records = _run_write(
            cypher,
            partner=partner,
            input_data=input_data,
            output_data=output_data,
            description=description,
            risks=risks,
            parent_name=parent_name,
        )
        if not records:
            return "## Not Found\n\nNo Business Context found.\n"
        return "## Success\n\nUpdated Business Context.\n"
    except Exception as e:
        return _format_error("update_business_context", e)


@mcp.tool()
def add_technical_context(description: str, *, parent_name: str) -> str:
    """Add Technical Context (Technischer Kontext) for Chapter 3."""
    try:
        description = validate_required(description, "description")
    except ValueError as e:
        return _format_error("add_technical_context", e)
    cypher = (
        "MERGE (d:Arc42 {name: $parent_name}) "
        "WITH d "
        "OPTIONAL MATCH (d)-[:kontext]->(old:Kontext:TechnischhKontext) "
        "DETACH DELETE old "
        "WITH d "
        "CREATE (n:Kontext:TechnischhKontext {tkontext: $description}) "
        "MERGE (d)-[:kontext]->(n) "
        "RETURN n"
    )
    logger.info("Tool add_technical_context aufgerufen")
    try:
        _run_write(cypher, description=description, parent_name=parent_name)
        return "## Success\n\nAdded Technical Context.\n"
    except Exception as e:
        return _format_error("add_technical_context", e)


@mcp.tool()
def delete_technical_context(*, parent_name: str) -> str:
    """Delete the current Technical Context singleton for Chapter 3. Lösche niemals etwas, ohne nochmal nachzufragen!"""
    cypher = (
        "MATCH (d:Arc42 {name: $parent_name})-[:kontext]->(n:Kontext:TechnischhKontext) "
        "DETACH DELETE n "
        "RETURN count(n) as c"
    )
    try:
        res = _run_write(cypher, parent_name=parent_name)
        deleted = res[0]["c"]
        if deleted > 0:
            return "## Success\n\nDeleted Technical Context.\n"
        return "## Warning\n\nNo Technical Context found.\n"
    except Exception as e:
        return _format_error("delete_technical_context", e)


@mcp.tool()
def update_technical_context(new_description: str, *, parent_name: str) -> str:
    """Update the Technical Context singleton description."""
    try:
        new_description = validate_required(new_description, "new_description")
    except ValueError as e:
        return _format_error("update_technical_context", e)

    cypher = (
        "MATCH (d:Arc42 {name: $parent_name})-[:kontext]->(n:Kontext:TechnischhKontext) "
        "SET n.tkontext = $new_description "
        "RETURN n"
    )
    try:
        records = _run_write(cypher, new_description=new_description, parent_name=parent_name)
        if not records:
            return "## Not Found\n\nNo Technical Context found.\n"
        return "## Success\n\nUpdated Technical Context.\n"
    except Exception as e:
        return _format_error("update_technical_context", e)


@mcp.tool()
def add_interface(
    name: str,
    documentation: str,
    calls: int = 0,
    emissions: float = 0.0,
    *,
    parent_name: str,
) -> str:
    """Add an Interface (Schnittstelle) for Chapter 3/Technical Context."""
    try:
        name = validate_required(name, "name")
        documentation = validate_required(documentation, "documentation")
    except ValueError as e:
        return _format_error("add_interface", e)

    cypher = (
        "MERGE (d:Arc42 {name: $parent_name}) "
        "CREATE (n:Interface { "
        "   name: $name, "
        "   documentation: $documentation, "
        "   calls: $calls, "
        "   emissions: $emissions "
        "}) "
        "MERGE (d)-[:hasInterface]->(n) "
        "RETURN n"
    )
    logger.info("Tool add_interface: '%s'", name)
    try:
        _run_write(
            cypher,
            name=name,
            documentation=documentation,
            calls=calls,
            emissions=emissions,
            parent_name=parent_name,
        )
        return f"## Success\n\nAdded Interface: **{name}**\n"
    except Exception as e:
        return _format_error("add_interface", e)


@mcp.tool()
def delete_interface(name: str, *, parent_name: str) -> str:
    """Delete an Interface (Schnittstelle) by name. Lösche niemals etwas, ohne nochmal nachzufragen!"""
    try:
        name = validate_required(name, "name")
    except ValueError as e:
        return _format_error("delete_interface", e)

    cypher = (
        "MATCH (d:Arc42 {name: $parent_name})-[:hasInterface]->(n:Interface {name: $name}) "
        "DETACH DELETE n "
        "RETURN count(n) as c"
    )
    try:
        res = _run_write(cypher, name=name, parent_name=parent_name)
        deleted = res[0]["c"]
        if deleted > 0:
            return f"## Success\n\nDeleted Interface: **{name}**\n"
        return f"## Warning\n\nNo matching interface '{name}' found.\n"
    except Exception as e:
        return _format_error("delete_interface", e)


@mcp.tool()
def update_interface(
    old_name: str,
    new_name: str = "",
    new_documentation: str = "",
    new_calls: int | None = None,
    new_emissions: float | None = None,
    *,
    parent_name: str,
) -> str:
    """Update an Interface (Schnittstelle) by name."""
    try:
        old_name = validate_required(old_name, "old_name")
    except ValueError as e:
        return _format_error("update_interface", e)

    set_clauses = []
    if new_name:
        set_clauses.append("n.name = $new_name")
    if new_documentation:
        set_clauses.append("n.documentation = $new_documentation")
    if new_calls is not None:
        set_clauses.append("n.calls = $new_calls")
    if new_emissions is not None:
        set_clauses.append("n.emissions = $new_emissions")
    if not set_clauses:
        return "## Error\n\nMindestens ein neues Feld muss angegeben werden.\n"

    cypher = (
        "MATCH (d:Arc42 {name: $parent_name})-[:hasInterface]->(n:Interface {name: $old_name}) "
        f"SET {', '.join(set_clauses)} "
        "RETURN n"
    )
    try:
        records = _run_write(
            cypher,
            old_name=old_name,
            new_name=new_name,
            new_documentation=new_documentation,
            new_calls=new_calls,
            new_emissions=new_emissions,
            parent_name=parent_name,
        )
        if not records:
            return f"## Not Found\n\nInterface '{old_name}' not found.\n"
        return f"## Success\n\nUpdated Interface: **{old_name}**\n"
    except Exception as e:
        return _format_error("update_interface", e)

