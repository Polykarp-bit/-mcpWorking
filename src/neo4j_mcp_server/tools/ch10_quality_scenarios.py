from __future__ import annotations

from ..core import logger, mcp, _format_error, _run_write
from .common import require_confirm, validate_required


# --- Chapter 10: Qualitätsszenarien ---


@mcp.tool()
def add_quality_scenario(
    scenario: str,
    stimulus: str,
    reaction: str,
    response: str,
    priority: str,
    risk: str,
    qz_name: str = "",
    *,
    parent_name: str,
) -> str:
    """Fügt ein Qualitätsszenario für Kapitel 10 hinzu."""
    try:
        scenario = validate_required(scenario, "scenario")
        stimulus = validate_required(stimulus, "stimulus")
        reaction = validate_required(reaction, "reaction")
        response = validate_required(response, "response")
        priority = validate_required(priority, "priority")
        risk = validate_required(risk, "risk")
    except ValueError as e:
        return _format_error("add_quality_scenario", e)

    cypher_create = (
        "MERGE (d:Arc42 {name: $parent_name}) "
        "CREATE (n:Qualitaetsscenario { "
        "   qualitaetsscenario: $scenario, "
        "   stimulus: $stimulus, "
        "   reaction: $reaction, "
        "   response: $response, "
        "   priority: $priority, "
        "   risk: $risk "
        "}) "
        "MERGE (d)-[:hasQualityScenario]->(n) "
        "RETURN n"
    )
    cypher_link = (
        "MATCH (n:Qualitaetsscenario {qualitaetsscenario: $scenario}) "
        "MATCH (qz:Qualitaetsziel) WHERE qz.qualitaetsziel = $qz_name "
        "MERGE (n)-[:konkretisiert]->(qz) "
        "WITH n, qz "
        "OPTIONAL MATCH (qz)--(qk:Qualitaetskriterium) "
        "FOREACH (k IN CASE WHEN qk IS NOT NULL THEN [qk] ELSE [] END | "
        "   MERGE (n)-[:hasQualityCriteria]->(k)) "
        "RETURN n"
    )

    logger.info("Tool add_quality_scenario: '%s'", scenario[:80])
    try:
        _run_write(
            cypher_create,
            scenario=scenario,
            stimulus=stimulus,
            reaction=reaction,
            response=response,
            priority=priority,
            risk=risk,
            parent_name=parent_name,
        )
        if qz_name:
            _run_write(cypher_link, scenario=scenario, qz_name=qz_name)
        return f"## Success\n\nAdded Quality Scenario: **{scenario}**\n"
    except Exception as e:
        return _format_error("add_quality_scenario", e)


@mcp.tool()
def update_quality_scenario(
    old_scenario: str,
    new_scenario: str = "",
    new_stimulus: str = "",
    new_reaction: str = "",
    new_response: str = "",
    new_priority: str = "",
    new_risk: str = "",
    new_qz_name: str = "",
    *,
    parent_name: str,
) -> str:
    """Aktualisiert ein vorhandenes Qualitätsszenario in Kapitel 10."""
    try:
        old_scenario = validate_required(old_scenario, "old_scenario")
    except ValueError as e:
        return _format_error("update_quality_scenario", e)

    set_clauses = []
    if new_scenario:
        set_clauses.append("n.qualitaetsscenario = $new_scenario")
    if new_stimulus:
        set_clauses.append("n.stimulus = $new_stimulus")
    if new_reaction:
        set_clauses.append("n.reaction = $new_reaction")
    if new_response:
        set_clauses.append("n.response = $new_response")
    if new_priority:
        set_clauses.append("n.priority = $new_priority")
    if new_risk:
        set_clauses.append("n.risk = $new_risk")

    if not set_clauses and not new_qz_name:
        return "## Error\n\nMindestens ein neues Feld oder ein neues Qualitaetsziel muss angegeben werden.\n"

    cypher_update = (
        "MATCH (d:Arc42 {name: $parent_name})-[:hasQualityScenario]->(n:Qualitaetsscenario {qualitaetsscenario: $old_scenario}) "
        f"SET {', '.join(set_clauses) if set_clauses else 'n = n'} "
        "RETURN n"
    )
    try:
        records = _run_write(
            cypher_update,
            old_scenario=old_scenario,
            new_scenario=new_scenario,
            new_stimulus=new_stimulus,
            new_reaction=new_reaction,
            new_response=new_response,
            new_priority=new_priority,
            new_risk=new_risk,
            parent_name=parent_name,
        )
        if not records:
            return f"## Not Found\n\nQuality Scenario '{old_scenario}' not found.\n"
        if new_qz_name:
            cypher_relink = (
                "MATCH (d:Arc42 {name: $parent_name})-[:hasQualityScenario]->(n:Qualitaetsscenario {qualitaetsscenario: $target_scenario}) "
                "OPTIONAL MATCH (n)-[old_rel:konkretisiert]->(:Qualitaetsziel) "
                "DELETE old_rel "
                "WITH n "
                "MATCH (qz:Qualitaetsziel {qualitaetsziel: $new_qz_name}) "
                "MERGE (n)-[:konkretisiert]->(qz) "
                "WITH n, qz "
                "OPTIONAL MATCH (qz)--(qk:Qualitaetskriterium) "
                "FOREACH (k IN CASE WHEN qk IS NOT NULL THEN [qk] ELSE [] END | "
                "   MERGE (n)-[:hasQualityCriteria]->(k)) "
                "RETURN n"
            )
            target_scenario = new_scenario or old_scenario
            _run_write(
                cypher_relink,
                parent_name=parent_name,
                target_scenario=target_scenario,
                new_qz_name=new_qz_name,
            )
        return f"## Success\n\nUpdated Quality Scenario: **{old_scenario}**\n"
    except Exception as e:
        return _format_error("update_quality_scenario", e)


@mcp.tool()
def delete_quality_scenario(scenario: str, *, parent_name: str) -> str:
    """Löscht ein Qualitätsszenario anhand seines Titels. Lösche niemals etwas, ohne nochmal nachzufragen!"""
    try:
        scenario = validate_required(scenario, "scenario")
    except ValueError as e:
        return _format_error("delete_quality_scenario", e)

    cypher = (
        "MATCH (d:Arc42 {name: $parent_name})-[:hasQualityScenario]->(n:Qualitaetsscenario {qualitaetsscenario: $scenario}) "
        "DETACH DELETE n "
        "RETURN count(n) as c"
    )
    try:
        res = _run_write(cypher, scenario=scenario, parent_name=parent_name)
        deleted = res[0]["c"]
        if deleted > 0:
            return f"## Success\n\nDeleted Quality Scenario: **{scenario}**\n"
        return "## Warning\n\nNo matching quality scenario found.\n"
    except Exception as e:
        return _format_error("delete_quality_scenario", e)

