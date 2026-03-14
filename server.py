from __future__ import annotations

import base64
import logging
import os
import re
import time
import urllib.error
import urllib.request
import zlib
from typing import Any, Dict, List, Tuple

from mcp.server.fastmcp import FastMCP
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, SessionExpired

# ---------------------------------------------------------------------------
# Logging (QA-MA-02, QA-MA-04 – Semantic Interaction Logging)
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("mcp.arc42")

# ---------------------------------------------------------------------------
# MCP Server Instance
# ---------------------------------------------------------------------------
mcp = FastMCP("arc42doc MCP Server")


# ---------------------------------------------------------------------------
# Configuration via Environment Variables (QA-PO-02)
# ---------------------------------------------------------------------------
def _env(name: str, default: str) -> str:
    val = os.getenv(name)
    return val if val is not None and val != "" else default


NEO4J_URI = _env("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = _env("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = _env("NEO4J_PASSWORD", "yourPassword")

# ---------------------------------------------------------------------------
# Neo4j Service – Data Access Layer (QA-MA-01 Protocol/Logic Separation)
# ---------------------------------------------------------------------------
_MAX_RECONNECT_ATTEMPTS = 3
_RECONNECT_DELAY_S = 1.0

_driver = None


def _get_driver():
    """Get or create Neo4j driver with auto-reconnect (QA-RE-02)."""
    global _driver
    if _driver is None:
        logger.info("Creating new Neo4j driver → %s", NEO4J_URI)
        _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    # Verify connectivity; reconnect on failure
    for attempt in range(1, _MAX_RECONNECT_ATTEMPTS + 1):
        try:
            _driver.verify_connectivity()
            return _driver
        except (ServiceUnavailable, SessionExpired, OSError) as exc:
            logger.warning(
                "Neo4j connectivity check failed (attempt %d/%d): %s",
                attempt, _MAX_RECONNECT_ATTEMPTS, exc,
            )
            if attempt < _MAX_RECONNECT_ATTEMPTS:
                time.sleep(_RECONNECT_DELAY_S)
                _driver = GraphDatabase.driver(
                    NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD)
                )
            else:
                raise
    return _driver


def _run_read(cypher: str, **params) -> list:
    """Execute a read query and return list of records (QA-RE-02 auto-reconnect)."""
    driver = _get_driver()
    with driver.session() as session:
        result = session.run(cypher, **params)
        return list(result)


def _run_write(cypher: str, **params) -> list:
    """Execute a write query inside a transaction (QA-RE-03 transactional writes)."""
    driver = _get_driver()
    with driver.session() as session:
        def _tx(tx):
            result = tx.run(cypher, **params)
            return list(result)
        return session.execute_write(_tx)


# ---------------------------------------------------------------------------
# Input Validation (QA-SE-04 – Semantic Validation of Tool Calls)
# ---------------------------------------------------------------------------
_MAX_INPUT_LEN = 10000


def _validate_required(value: str, field_name: str) -> str:
    """Validate that a required string field is not empty."""
    v = str(value).strip() if value else ""
    if not v:
        raise ValueError(f"Parameter '{field_name}' darf nicht leer sein.")
    if len(v) > _MAX_INPUT_LEN:
        raise ValueError(
            f"Parameter '{field_name}' ist zu lang ({len(v)} Zeichen, max {_MAX_INPUT_LEN})."
        )
    return v


# ---------------------------------------------------------------------------
# Content Cleaning (QA-PE-02 – Token Efficiency)
# ---------------------------------------------------------------------------
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _clean_content(text: str) -> str:
    """Remove HTML tags and excessive whitespace to save tokens."""
    if not text:
        return ""
    text = _HTML_TAG_RE.sub("", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _safe_str(x: Any, fallback: str = "") -> str:
    if x is None:
        return fallback
    try:
        s = str(x)
        return s if s != "" else fallback
    except Exception:
        return fallback


def _extract_title_and_content(node_data: Dict[str, Any], labels: List[str]) -> Tuple[str, str]:
    """Extract title and content from node based on its labels and properties."""
    title = ""
    content = ""

    for prop in ["title", "name", "begriff", "roleOrName", "konvention", "randbedingung", "aufgabe", "anforderung", "qualitaetsziel"]:
        if prop in node_data and node_data[prop]:
            title = str(node_data[prop])
            break

    for prop in ["content", "text", "beschreibung", "erlaeuterung", "hintergrund", "strategy", "loesung", "aufgabe"]:
        if prop in node_data and node_data[prop]:
            content = str(node_data[prop])
            break

    if "TextEingabe" in labels:
        if "content" in node_data:
            content = str(node_data["content"])
            if "type" in node_data and node_data["type"] == "TITLE":
                title = content
                content = ""

    if "Konzept" in labels:
        if "name" in node_data:
            title = str(node_data["name"])
        if "text" in node_data:
            content = str(node_data["text"])

    if not title:
        title = labels[0] if labels else "Untitled"

    return title, _clean_content(content)


def _format_doc(title: str, content: str, node_type: str = "") -> str:
    title = title.strip() or "Untitled"
    content = content.strip()
    if not content:
        content = "_(no content)_"

    type_prefix = f"[{node_type}] " if node_type else ""
    return f"## {type_prefix}{title}\n\n{content}\n"


def _format_error(action: str, err: Exception) -> str:
    """Return a structured error message the LLM can interpret (QA-RE-01)."""
    logger.error("Action '%s' failed: %s – %s", action, type(err).__name__, err)
    return (
        "## Error\n\n"
        f"**Action:** {action}\n\n"
        f"**Cause:** `{type(err).__name__}`\n\n"
        f"**Message:** {str(err)}\n"
    )


@mcp.tool()
def search_docs(query: str) -> str:
    """Search across all arc42 documentation nodes (case-insensitive).

    Searches titles, descriptions, content and all text properties.
    Returns up to 50 matching results in Markdown format.

    Args:
        query: Search term (e.g. 'Bausteinsicht', 'Sicherheit').
    """
    q = _safe_str(query).strip()
    if not q:
        return "## Search Results\n\nProvide a non-empty `query`.\n"

    logger.info("LLM sucht Dokumentation: '%s'", q)

    cypher = (
        "MATCH (n) "
        "WHERE ("
        "  (n.content IS NOT NULL AND toLower(n.content) CONTAINS toLower($search_term)) OR "
        "  (n.text IS NOT NULL AND toLower(n.text) CONTAINS toLower($search_term)) OR "
        "  (n.beschreibung IS NOT NULL AND toLower(n.beschreibung) CONTAINS toLower($search_term)) OR "
        "  (n.erlaeuterung IS NOT NULL AND toLower(n.erlaeuterung) CONTAINS toLower($search_term)) OR "
        "  (n.hintergrund IS NOT NULL AND toLower(n.hintergrund) CONTAINS toLower($search_term)) OR "
        "  (n.title IS NOT NULL AND toLower(n.title) CONTAINS toLower($search_term)) OR "
        "  (n.name IS NOT NULL AND toLower(n.name) CONTAINS toLower($search_term)) OR "
        "  (n.begriff IS NOT NULL AND toLower(n.begriff) CONTAINS toLower($search_term)) OR "
        "  (n.aufgabe IS NOT NULL AND toLower(n.aufgabe) CONTAINS toLower($search_term)) OR "
        "  (n.anforderung IS NOT NULL AND toLower(n.anforderung) CONTAINS toLower($search_term)) OR "
        "  (n.strategy IS NOT NULL AND toLower(n.strategy) CONTAINS toLower($search_term)) OR "
        "  (n.loesung IS NOT NULL AND toLower(n.loesung) CONTAINS toLower($search_term))"
        ") "
        "RETURN n, labels(n) AS labels "
        "LIMIT 50"
    )

    try:
        records = _run_read(cypher, search_term=q)
        rows: List[Dict[str, Any]] = []
        for record in records:
            node = record["n"]
            labels = record["labels"]
            node_data = dict(node.items())
            title, content = _extract_title_and_content(node_data, labels)
            rows.append({
                "title": title,
                "content": content,
                "node_type": labels[0] if labels else "Unknown"
            })

        if not rows:
            return f"## Search Results\n\nNo matches for `{q}`.\n"

        parts = [
            f"## Search Results\n\nQuery: `{q}`\n\nMatches: **{len(rows)}**\n"
        ]
        for row in rows:
            title = _safe_str(row.get("title"), "Untitled")
            content = _safe_str(row.get("content"), "")
            node_type = _safe_str(row.get("node_type"), "")
            parts.append(_format_doc(title, content, node_type))
        return "\n".join(parts).strip() + "\n"

    except Exception as e:
        return _format_error("search_docs", e)


@mcp.tool()
def list_titles() -> str:
    """List all node titles from the arc42 documentation (sorted alphabetically).

    Returns a Markdown list of all unique titles/names found in the database.
    Useful to get an overview of available documentation content.
    """
    logger.info("LLM fordert Titelliste an")
    cypher = (
        "MATCH (n) "
        "RETURN n, labels(n) AS labels "
        "LIMIT 1000"
    )

    try:
        records = _run_read(cypher)
        titles_set = set()
        for record in records:
            node = record["n"]
            labels = record["labels"]
            node_data = dict(node.items())
            title, _ = _extract_title_and_content(node_data, labels)
            if title and title != "Untitled":
                titles_set.add(title)

        titles = sorted(list(titles_set), key=str.lower)

        if not titles:
            return "## Titles\n\nNo titles found.\n"

        lines = "\n".join(f"- {t}" for t in titles)
        return f"## Titles\n\nCount: **{len(titles)}**\n\n{lines}\n"

    except Exception as e:
        return _format_error("list_titles", e)



@mcp.tool()
def add_documentation(title: str, content: str, doc_type: str = "Konzept") -> str:
    """Add a cross-cutting concept (Querschnittliches Konzept, Chapter 8) to the arc42 documentation.

    Args:
        title: Name of the concept (e.g. 'Persistenz', 'Fehlerbehandlung', 'Logging').
        content: Detailed description of the concept.
        doc_type: Type – 'Konzept' (default) links to arc42, 'Documentation' for generic docs.
    """
    try:
        title = _validate_required(title, "title")
        content = _validate_required(content, "content")
    except ValueError as e:
        return _format_error("add_documentation", e)

    logger.info("Tool add_documentation aufgerufen: title='%s'", title)
    parent_arc42 = "Neo4j MCP Server"

    if doc_type == "Konzept" or doc_type == "Documentation":
        cypher = (
            "MERGE (parent:Arc42 {name: $parent_name}) "
            "MERGE (n:Konzept {name: $title}) "
            "SET n.text = $content, "
            "    n.conceptCategories = ['Documentation'], "
            "    n.updated_at = datetime() "
            "MERGE (parent)-[:hatKonzept]->(n) "
            "RETURN n"
        )
    else:
        cypher = (
            "MERGE (n:Documentation {title: $title}) "
            "SET n.content = $content, "
            "    n.type = $doc_type "
            "RETURN n"
        )

    try:
        _run_write(cypher, title=title, content=content, doc_type=doc_type, parent_name=parent_arc42)
        return f"## Success\n\nAdded/Updated documentation: **{title}** linked to **{parent_arc42}**\n"
    except Exception as e:
        return _format_error("add_documentation", e)


# --- Chapter 1: Einführung und Ziele ---

@mcp.tool()
def add_requirement(task: str, parent_name: str = "Neo4j MCP Server") -> str:
    """Add a Requirement (Aufgabenstellung) to Chapter 1 – Einführung und Ziele.

    Args:
        task: Description of the requirement (e.g. 'System muss 1000 Nutzer unterstützen').
        parent_name: Name of the parent arc42 project.
    """
    try:
        task = _validate_required(task, "task")
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
def add_quality_goal(goal: str, motivation: str, criteria: str = "Funktionalität", parent_name: str = "Neo4j MCP Server") -> str:
    """Add a Quality Goal (Qualitätsziel) for Chapter 1.
    Args:
        goal: The name/title of the goal.
        motivation: Specific motivation or description.
        criteria: Comma-separated list of linking criteria (e.g. "Funktionalität,Sicherheit").
                  Standard values: Funktionalität, Effizienz, Kompatibilität, Benutzbarkeit, Zuverlässigkeit, Sicherheit, Wartbarkeit, Portabilität, Nachhaltigkeit.
    """
    try:
        goal = _validate_required(goal, "goal")
        motivation = _validate_required(motivation, "motivation")
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
        return f"## Success\n\nAdded Quality Goal: **{goal}** linked to criteria **{criteria}**\nMotivation: {motivation}\n"
    except Exception as e:
        return _format_error("add_quality_goal", e)

@mcp.tool()
def add_stakeholder(role_or_name: str, contact: str = "", expectation: str = "", parent_name: str = "Neo4j MCP Server") -> str:
    """Add a Stakeholder for Chapter 1.
    Args:
        role_or_name: The name or role of the stakeholder (e.g. 'Software Architect').
        contact: Contact info (email, etc.).
        expectation: What they expect from the system.
    """
    try:
        role_or_name = _validate_required(role_or_name, "role_or_name")
    except ValueError as e:
        return _format_error("add_stakeholder", e)

    # Note: DAO uses relationship :hasStakeholder and property roleOrName
    cypher = (
        "MERGE (d:Arc42 {name: $parent_name}) "
        "CREATE (n:Stakeholder {roleOrName: $role_org_name, contact: $contact, expectation: $expectation}) "
        "MERGE (d)-[:hasStakeholder]->(n) "
        "RETURN n"
    )
    logger.info("Tool add_stakeholder: '%s'", role_or_name)
    try:
        _run_write(cypher, role_org_name=role_or_name, contact=contact, expectation=expectation, parent_name=parent_name)
        return f"## Success\n\nAdded Stakeholder: **{role_or_name}**\n"
    except Exception as e:
        return _format_error("add_stakeholder", e)


# --- Chapter 2: Randbedingungen ---

@mcp.tool()
def add_technical_constraint(constraint: str, background: str, parent_name: str = "Neo4j MCP Server") -> str:
    """Add a Technical Constraint (Technische Randbedingung) for Chapter 2."""
    try:
        constraint = _validate_required(constraint, "constraint")
        background = _validate_required(background, "background")
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
def add_organizational_constraint(constraint: str, background: str, parent_name: str = "Neo4j MCP Server") -> str:
    """Add an Organizational Constraint (Organisatorische Randbedingung) for Chapter 2."""
    try:
        constraint = _validate_required(constraint, "constraint")
        background = _validate_required(background, "background")
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
def add_ecological_constraint(constraint: str, background: str, parent_name: str = "Neo4j MCP Server") -> str:
    """Add an Ecological Constraint (Ökologische Randbedingung) for Chapter 2."""
    try:
        constraint = _validate_required(constraint, "constraint")
        background = _validate_required(background, "background")
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
def add_convention(convention: str, explanation: str, parent_name: str = "Neo4j MCP Server") -> str:
    """Add a Convention (Konvention) for Chapter 2."""
    try:
        convention = _validate_required(convention, "convention")
        explanation = _validate_required(explanation, "explanation")
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


# --- Chapter 3: Kontextabgrenzung ---

@mcp.tool()
def add_business_context(partner: str, input_data: str, output_data: str, description: str, risks: str, parent_name: str = "Neo4j MCP Server") -> str:
    """Add Business Context (Fachlicher Kontext) for Chapter 3."""
    try:
        partner = _validate_required(partner, "partner")
        description = _validate_required(description, "description")
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
        _run_write(cypher, partner=partner, input=input_data, output=output_data, description=description, risks=risks, parent_name=parent_name)
        return f"## Success\n\nAdded Business Context with Partner: **{partner}**\n"
    except Exception as e:
        return _format_error("add_business_context", e)

@mcp.tool()
def add_technical_context(description: str, parent_name: str = "Neo4j MCP Server") -> str:
    """Add Technical Context (Technischer Kontext) for Chapter 3."""
    try:
        description = _validate_required(description, "description")
    except ValueError as e:
        return _format_error("add_technical_context", e)
    # Note: TechnischKontext uses :kontext relationship and specific labeling
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
        return f"## Success\n\nAdded Technical Context.\n"
    except Exception as e:
        return _format_error("add_technical_context", e)

@mcp.tool()
def add_interface(name: str, documentation: str, calls: int = 0, emissions: float = 0.0, parent_name: str = "Neo4j MCP Server") -> str:
    """Add an Interface (Schnittstelle) for Chapter 3/Technical Context.
    Args:
        name: Name of the interface (e.g. 'MCP Stdio', 'Neo4j Bolt').
        documentation: Description/Documentation of the interface.
        calls: Calls per month (integer).
        emissions: CO2 emissions per call in grams (float).
    """
    try:
        name = _validate_required(name, "name")
        documentation = _validate_required(documentation, "documentation")
    except ValueError as e:
        return _format_error("add_interface", e)

    # Note: InterfaceDAO uses :hasInterface relationship and props: name, documentation, calls, emissions
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
        _run_write(cypher, name=name, documentation=documentation, calls=calls, emissions=emissions, parent_name=parent_name)
        return f"## Success\n\nAdded Interface: **{name}**\n"
    except Exception as e:
        return _format_error("add_interface", e)



# --- Chapter 4: Lösungsstrategie ---

@mcp.tool()
def add_solution_strategy(strategy: str, parent_name: str = "Neo4j MCP Server") -> str:
    """Add a Solution Strategy (Lösungsstrategie) for Chapter 4."""
    try:
        strategy = _validate_required(strategy, "strategy")
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
        return f"## Success\n\nAdded Solution Strategy.\n"
    except Exception as e:
        return _format_error("add_solution_strategy", e)


# --- Chapter 5: Bausteinsicht ---

@mcp.tool()
def add_building_block_view(description: str, image_file_path: str = "", parent_name: str = "Neo4j MCP Server") -> str:
    """Add a Building Block View (Bausteinsicht) for Chapter 5. 
    Overwrites existing view.
    Args:
        description: Text description.
        image_file_path: Absolute path to a PNG/JPG file to upload as the diagram.
    """
    try:
        description = _validate_required(description, "description")
    except ValueError as e:
        return _format_error("add_building_block_view", e)

    image_bytes = b""
    mime_type = ""
    image_name = ""
    
    if image_file_path:
        try:
            import os
            if os.path.exists(image_file_path):
                with open(image_file_path, "rb") as f:
                    image_bytes = f.read()
                image_name = os.path.basename(image_file_path)
                # Simple mime type guess
                if image_name.lower().endswith(".png"):
                    mime_type = "image/png"
                elif image_name.lower().endswith(".jpg") or image_name.lower().endswith(".jpeg"):
                    mime_type = "image/jpeg"
                else:
                    mime_type = "application/octet-stream"
        except Exception as e:
            return f"Error reading image file: {e}"

    # 1. Detach/Delete existing to enforce singleton for Java App
    # 2. Create new
    cypher = (
        "MERGE (d:Arc42 {name: $parent_name}) "
        "WITH d "
        "OPTIONAL MATCH (d)-[:bausteinsicht]->(old:Image:Baustein) "
        "DETACH DELETE old "
        "WITH d "
        "CREATE (n:Image:Baustein { "
        "   description: $description, "
        "   bildName: $image_name, "
        "   bildMimeType: $mime_type, "
        "   bildPath: $image_bytes, "
        "   uxfName: '', "
        "   uxfMimeType: '', "
        "   uxfPath: $empty_bytes "
        "}) "
        "MERGE (d)-[:bausteinsicht]->(n) "
        "RETURN n"
    )
    logger.info("Tool add_building_block_view: image='%s'", image_name)
    try:
        _run_write(cypher, 
                    description=description, 
                    parent_name=parent_name, 
                    image_name=image_name,
                    mime_type=mime_type,
                    image_bytes=image_bytes,
                    empty_bytes=b"")
        return f"## Success\n\nAdded Building Block View (Image: {image_name})\n"
    except Exception as e:
        return _format_error("add_building_block_view", e)


@mcp.tool()
def update_building_block_view_description(
    new_description: str,
    parent_name: str = "Neo4j MCP Server",
) -> str:
    """Update only the textual description of the Building Block View (Chapter 5).

    This tool does not touch the stored image data and can be used by the LLM
    to iteratively improve the description without re-uploading diagrams.
    """
    try:
        new_description = _validate_required(new_description, "new_description")
    except ValueError as e:
        return _format_error("update_building_block_view_description", e)

    logger.info("Tool update_building_block_view_description aufgerufen")
    cypher = (
        "MATCH (d:Arc42 {name: $parent_name})-[:bausteinsicht]->(n:Image:Baustein) "
        "SET n.description = $new_description "
        "RETURN n"
    )
    try:
        records = _run_write(
            cypher,
            parent_name=parent_name,
            new_description=new_description,
        )
        if not records:
            return (
                "## Not Found\n\n"
                "Keine bestehende Bausteinsicht gefunden. "
                "Bitte zuerst ein Diagramm mit add_building_block_view oder "
                "generate_mermaid_diagram anlegen.\n"
            )
        return "## Success\n\nUpdated Building Block View description.\n"
    except Exception as e:
        return _format_error("update_building_block_view_description", e)


# --- Chapter 6: Laufzeitsicht ---

@mcp.tool()
def add_runtime_view(description: str, image_file_path: str = "", parent_name: str = "Neo4j MCP Server") -> str:
    """Add a Runtime View (Laufzeitsicht) for Chapter 6."""
    try:
        description = _validate_required(description, "description")
    except ValueError as e:
        return _format_error("add_runtime_view", e)
    image_bytes = b""
    mime_type = ""
    image_name = ""
    
    if image_file_path:
        try:
            import os
            if os.path.exists(image_file_path):
                with open(image_file_path, "rb") as f:
                    image_bytes = f.read()
                image_name = os.path.basename(image_file_path)
                if image_name.lower().endswith(".png"):
                    mime_type = "image/png"
                elif image_name.lower().endswith(".jpg") or image_name.lower().endswith(".jpeg"):
                    mime_type = "image/jpeg"
                else:
                    mime_type = "application/octet-stream"
        except Exception as e:
            return f"Error reading image file: {e}"

    cypher = (
        "MERGE (d:Arc42 {name: $parent_name}) "
        "WITH d "
        "OPTIONAL MATCH (d)-[:laufzeitsicht]->(old:Image:Laufzeit) "
        "DETACH DELETE old "
        "CREATE (n:Image:Laufzeit { "
        "   description: $description, "
        "   bildName: $image_name, "
        "   bildMimeType: $mime_type, "
        "   bildPath: $image_bytes, "
        "   uxfName: '', "
        "   uxfMimeType: '', "
        "   uxfPath: $empty_bytes "
        "}) "
        "MERGE (d)-[:laufzeitsicht]->(n) "
        "RETURN n"
    )
    logger.info("Tool add_runtime_view: image='%s'", image_name)
    try:
        _run_write(cypher, 
                    description=description, 
                    parent_name=parent_name, 
                    image_name=image_name,
                    mime_type=mime_type,
                    image_bytes=image_bytes,
                    empty_bytes=b"")
        return f"## Success\n\nAdded Runtime View (Image: {image_name})\n"
    except Exception as e:
        return _format_error("add_runtime_view", e)


# --- Chapter 7: Verteilungssicht ---

@mcp.tool()
def add_deployment_view(description: str, image_file_path: str = "", parent_name: str = "Neo4j MCP Server") -> str:
    """Add a Deployment View (Verteilungssicht) for Chapter 7."""
    try:
        description = _validate_required(description, "description")
    except ValueError as e:
        return _format_error("add_deployment_view", e)
    image_bytes = b""
    mime_type = ""
    image_name = ""
    
    if image_file_path:
        try:
            import os
            if os.path.exists(image_file_path):
                with open(image_file_path, "rb") as f:
                    image_bytes = f.read()
                image_name = os.path.basename(image_file_path)
                if image_name.lower().endswith(".png"):
                    mime_type = "image/png"
                elif image_name.lower().endswith(".jpg") or image_name.lower().endswith(".jpeg"):
                    mime_type = "image/jpeg"
                else:
                    mime_type = "application/octet-stream"
        except Exception as e:
            return f"Error reading image file: {e}"

    cypher = (
        "MERGE (d:Arc42 {name: $parent_name}) "
        "WITH d "
        "OPTIONAL MATCH (d)-[:verteilungssicht]->(old:Image:Verteilung) "
        "DETACH DELETE old "
        "CREATE (n:Image:Verteilung { "
        "   description: $description, "
        "   bildName: $image_name, "
        "   bildMimeType: $mime_type, "
        "   bildPath: $image_bytes, "
        "   uxfName: '', "
        "   uxfMimeType: '', "
        "   uxfPath: $empty_bytes "
        "}) "
        "MERGE (d)-[:verteilungssicht]->(n) "
        "RETURN n"
    )
    logger.info("Tool add_deployment_view: image='%s'", image_name)
    try:
        _run_write(cypher, 
                    description=description, 
                    parent_name=parent_name, 
                    image_name=image_name,
                    mime_type=mime_type,
                    image_bytes=image_bytes,
                    empty_bytes=b"")
        return f"## Success\n\nAdded Deployment View (Image: {image_name})\n"
    except Exception as e:
        return _format_error("add_deployment_view", e)


# --- Chapter 9: Entwurfsentscheidungen ---

@mcp.tool()
def add_design_decision(decision: str, consequence: str, reasoning: str, importance: str, parent_name: str = "Neo4j MCP Server") -> str:
    """Add a Design Decision (Entwurfsentscheidung) for Chapter 9."""
    try:
        decision = _validate_required(decision, "decision")
        consequence = _validate_required(consequence, "consequence")
        reasoning = _validate_required(reasoning, "reasoning")
        importance = _validate_required(importance, "importance")
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
        _run_write(cypher, decision=decision, consequence=consequence, reasoning=reasoning, importance=importance, parent_name=parent_name)
        return f"## Success\n\nAdded Design Decision: **{decision}**\n"
    except Exception as e:
        return _format_error("add_design_decision", e)


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
    parent_name: str = "Neo4j MCP Server",
) -> str:
    """Add a Quality Scenario (Qualitätsszenario) for Chapter 10.

    Args:
        scenario: Description of the quality scenario.
        stimulus: The triggering event/stimulus.
        reaction: How the system reacts.
        response: Measurable response/target value (Zielwert).
        priority: Priority level e.g. 'hoch', 'mittel', 'niedrig'.
        risk: Risk if scenario is not met.
        qz_name: Name of the Qualitaetsziel to link to (e.g. 'Zeitverhalten – Antwortlatenz unter 2 Sekunden').
        parent_name: Name of the arc42 project node in Neo4j.
    """
    try:
        scenario = _validate_required(scenario, "scenario")
        stimulus = _validate_required(stimulus, "stimulus")
        reaction = _validate_required(reaction, "reaction")
        response = _validate_required(response, "response")
        priority = _validate_required(priority, "priority")
        risk = _validate_required(risk, "risk")
    except ValueError as e:
        return _format_error("add_quality_scenario", e)

    # Create the scenario node with arc42doc-compatible property names
    # Property names verified from QualityScenarioDAO.java source code:
    # qualitaetsscenario, stimulus, reaction, response, priority, risk
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
    # Link to Qualitaetsziel and its Qualitaetskriterium (arc42doc display structure)
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
    logger.info("Tool add_quality_scenario: '%s', qz='%s'", scenario[:80], qz_name)
    try:
        _run_write(
            cypher_create,
            scenario=scenario, stimulus=stimulus, reaction=reaction,
            response=response, priority=priority, risk=risk,
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
    parent_name: str = "Neo4j MCP Server",
) -> str:
    """Update an existing Quality Scenario (Qualitätsszenario) in Chapter 10.

    Args:
        old_scenario: Current scenario text to find.
        new_scenario: New scenario description.
        new_stimulus: New stimulus text.
        new_reaction: New reaction text.
        new_response: New response/target value.
        new_priority: New priority.
        new_risk: New risk description.
        new_qz_name: Optional new Qualitaetsziel name to (re)link to.
        parent_name: Name of the arc42 project.
    """
    try:
        old_scenario = _validate_required(old_scenario, "old_scenario")
    except ValueError as e:
        return _format_error("update_quality_scenario", e)

    logger.info("Tool update_quality_scenario: '%s'", old_scenario[:80])
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
            parent_name=parent_name,
            old_scenario=old_scenario,
            new_scenario=new_scenario,
            new_stimulus=new_stimulus,
            new_reaction=new_reaction,
            new_response=new_response,
            new_priority=new_priority,
            new_risk=new_risk,
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
            # Use the potentially updated scenario text as lookup target
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


# --- Chapter 11: Risiken ---

@mcp.tool()
def add_risk(description: str, impact: str, probability: str, status: str, parent_name: str = "Neo4j MCP Server") -> str:
    """Add a Risk (Risiko) for Chapter 11.
    Args:
        description: The risk description (anforderung).
        impact: Impact (schadenshoehe) - e.g. 'hoch', 'mittel', 'gering'.
        probability: Probability (eintrittswahrscheinlichkeit) - e.g. 'hoch', 'mittel'.
        status: e.g. 'identifiziert', 'behandelt'.
    """
    try:
        description = _validate_required(description, "description")
        impact = _validate_required(impact, "impact")
        probability = _validate_required(probability, "probability")
        status = _validate_required(status, "status")
    except ValueError as e:
        return _format_error("add_risk", e)

    # Fix: DAO uses :hasRisiko connection and different property names
    cypher = (
        "MERGE (d:Arc42 {name: $parent_name}) "
        "CREATE (n:Risiko { "
        "   anforderung: $description, "
        "   wirkung: $impact, "
        "   eintrittswahrscheinlichkeit: $probability, "
        "   schadenshoehe: $impact, " 
        "   status: $status, "
        "   erfasser: 'MCP-Agent', "
        "   zuletztAktu: toString(datetime()) "
        "}) "
        "MERGE (d)-[:hasRisiko]->(n) "
        "RETURN n"
    )
    logger.info("Tool add_risk: '%s'", description[:80])
    try:
        _run_write(cypher, description=description, impact=impact, probability=probability, status=status, parent_name=parent_name)
        return f"## Success\n\nAdded Risk: **{description}**\n"
    except Exception as e:
        return _format_error("add_risk", e)


# --- Chapter 12: Glossar ---

@mcp.tool()
def add_glossary_term(term: str, description: str, parent_name: str = "Neo4j MCP Server") -> str:
    """Add a Glossary Term (Glossar) for Chapter 12."""
    try:
        term = _validate_required(term, "term")
        description = _validate_required(description, "description")
    except ValueError as e:
        return _format_error("add_glossary_term", e)
    cypher = (
        "MERGE (d:Arc42 {name: $parent_name}) "
        "CREATE (n:Glossar {begriff: $term, beschreibung: $description}) "
        "MERGE (d)-[:hasGlossar]->(n) "
        "RETURN n"
    )
    logger.info("Tool add_glossary_term: '%s'", term)
    try:
        _run_write(cypher, term=term, description=description, parent_name=parent_name)
        return f"## Success\n\nAdded Glossary Term: **{term}**\n"
    except Exception as e:
        return _format_error("add_glossary_term", e)


# --- Chapter 13: Nachhaltigkeit ---

@mcp.tool()
def add_sustainability_goal(goal: str, motivation: str, priority: str, saving: str, parent_name: str = "Neo4j MCP Server") -> str:
    """Add a Sustainability Goal (Nachhaltigkeitsziel) for Chapter 13."""
    try:
        goal = _validate_required(goal, "goal")
        motivation = _validate_required(motivation, "motivation")
        priority = _validate_required(priority, "priority")
        saving = _validate_required(saving, "saving")
    except ValueError as e:
        return _format_error("add_sustainability_goal", e)
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
        _run_write(cypher, goal=goal, motivation=motivation, priority=priority, saving=saving, parent_name=parent_name)
        return f"## Success\n\nAdded Sustainability Goal: **{goal}**\n"
    except Exception as e:
        return _format_error("add_sustainability_goal", e)


@mcp.tool()
def read_arc42_chapter(chapter: str, parent_name: str = "Neo4j MCP Server") -> str:
    """Read the content of a specific arc42 chapter (1-13).

    Returns all nodes belonging to the specified chapter in Markdown format.
    Each chapter corresponds to a standard arc42 section:
      1=Einführung/Ziele, 2=Randbedingungen, 3=Kontextabgrenzung,
      4=Lösungsstrategie, 5=Bausteinsicht, 6=Laufzeitsicht,
      7=Verteilungssicht, 8=Querschnittliche Konzepte,
      9=Entwurfsentscheidungen, 10=Qualitätsszenarien,
      11=Risiken, 12=Glossar, 13=Nachhaltigkeit.

    Args:
        chapter: Chapter number as string ('1' through '13').
        parent_name: Name of the arc42 project.
    """
    logger.info("LLM fordert arc42-Kapitel %s an", chapter)

    chapter_map = {
        "1": [
            ("Aufgabenstellung", "hasRequirement", "aufgabe"),
            ("Qualitaetsziel", "hasQualityGoal", "qualitaetsziel"),
            ("Stakeholder", "hasStakeholder", "roleOrName")
        ],
        "2": [
            ("TechnischeRandbedingung", "hatTechnischRandbedingung", "randbedingung"),
            ("OrganisatorischRandbedingung", "hatOrganisatorischRandbedingung", "randbedingung"),
            ("OekologischeRandbedingung", "hatOekologischeRandbedingung", "randbedingung"),
            ("Konvention", "hatKonvention", "konvention")
        ],
        "3": [
            ("FachlicherKontext", "hasFachlicherKontext", "partner"),
            ("Kontext:TechnischhKontext", "kontext", "tkontext")
        ],
        "4": [("LoesungsStrategie", "hatLoesung", "strategy")],
        "5": [("Image:Baustein", "bausteinsicht", "description")],
        "6": [("Image:Laufzeit", "laufzeitsicht", "description")],
        "7": [("Image:Verteilung", "verteilungssicht", "description")],
        "8": [("Konzept", "hatKonzept", "name")],
        "9": [("Entwurfsentscheidung", "hasEntwurfsentscheidung", "entscheidung")],
        "10": [("Qualitaetsscenario", "hasQualityScenario", "qualitaetsscenario")],
        "11": [("Risiko", "hasRisiko", "anforderung")],
        "12": [("Glossar", "hasGlossar", "begriff")],
        "13": [("Nachhaltigkeitsziele", "hasNachhaltigkeitsziele", "greengoal")]
    }

    if chapter not in chapter_map:
        return f"Unknown chapter: {chapter}. Please specify 1-13."

    chapter_names = {
        "1": "Einführung und Ziele", "2": "Randbedingungen",
        "3": "Kontextabgrenzung", "4": "Lösungsstrategie",
        "5": "Bausteinsicht", "6": "Laufzeitsicht",
        "7": "Verteilungssicht", "8": "Querschnittliche Konzepte",
        "9": "Entwurfsentscheidungen", "10": "Qualitätsszenarien",
        "11": "Risiken und technische Schulden", "12": "Glossar",
        "13": "Nachhaltigkeit",
    }
    output = [f"# Kapitel {chapter}: {chapter_names.get(chapter, '')}\n"]

    try:
        driver = _get_driver()
        with driver.session() as session:
            for label, rel, main_prop in chapter_map[chapter]:
                cypher = (
                    "MATCH (d:Arc42 {{name: $parent_name}})-[:{rel}]->(n:{label}) "
                    "RETURN n"
                ).format(rel=rel, label=label)

                result = session.run(cypher, parent_name=parent_name)

                output.append(f"## {label}")
                found = False
                for record in result:
                    found = True
                    node = record["n"]
                    props = dict(node.items())

                    main_val = _clean_content(str(props.get(main_prop, "N/A")))
                    output.append(f"- **{main_val}**")

                    for k, v in props.items():
                        if k != main_prop and not isinstance(v, (bytes, bytearray)):
                            output.append(f"  - {k}: {_clean_content(str(v))}")
                    output.append("")

                if not found:
                    output.append("_(keine Einträge)_\n")

        return "\n".join(output)
    except Exception as e:
        return _format_error("read_arc42_chapter", e)


# =========================================================================
# MCP RESOURCES (Epic 1 – Read-Access)
# =========================================================================

@mcp.resource("arc42://chapter/{chapter_number}")
def get_chapter_resource(chapter_number: str) -> str:
    """Read a specific arc42 chapter (1-13) as an MCP Resource.

    URI pattern: arc42://chapter/1  through  arc42://chapter/13
    """
    logger.info("Resource arc42://chapter/%s abgerufen", chapter_number)
    return read_arc42_chapter(chapter_number)


@mcp.resource("arc42://overview")
def get_overview_resource() -> str:
    """High-level overview of the arc42 project – lists all chapters with a summary."""
    logger.info("Resource arc42://overview abgerufen")
    parts = ["# arc42 Projektübersicht\n"]
    chapter_names = {
        "1": "Einführung und Ziele", "2": "Randbedingungen",
        "3": "Kontextabgrenzung", "4": "Lösungsstrategie",
        "5": "Bausteinsicht", "6": "Laufzeitsicht",
        "7": "Verteilungssicht", "8": "Querschnittliche Konzepte",
        "9": "Entwurfsentscheidungen", "10": "Qualitätsszenarien",
        "11": "Risiken und technische Schulden", "12": "Glossar",
        "13": "Nachhaltigkeit",
    }
    for num, name in chapter_names.items():
        parts.append(f"- **Kapitel {num}**: {name} → `arc42://chapter/{num}`")
    return "\n".join(parts) + "\n"


# =========================================================================
# MCP PROMPTS (Pre-defined Templates for LLM Interaction)
# =========================================================================

@mcp.prompt()
def explain_architecture() -> str:
    """Erkläre die Architektur anhand der arc42-Dokumentation.

    Dieses Prompt-Template instruiert das LLM, die Bausteinsicht,
    Laufzeitsicht und Verteilungssicht zusammenzufassen.
    """
    return (
        "Bitte analysiere die arc42-Dokumentation dieses Projekts. "
        "Lies dazu Kapitel 5 (Bausteinsicht), Kapitel 6 (Laufzeitsicht) "
        "und Kapitel 7 (Verteilungssicht) und erstelle eine verständliche "
        "Zusammenfassung der Systemarchitektur. Erkläre die wichtigsten "
        "Komponenten, ihre Beziehungen und die zugrunde liegenden "
        "Entwurfsentscheidungen (Kapitel 9)."
    )


@mcp.prompt()
def consistency_check() -> str:
    """Prüfe die Konsistenz der arc42-Dokumentation.

    Instruiert das LLM, Widersprüche zwischen verschiedenen
    Kapiteln oder zwischen Diagrammen und Text zu finden.
    """
    return (
        "Führe eine Konsistenzprüfung der arc42-Dokumentation durch. "
        "Vergleiche dazu: 1) Stimmen Bausteinsicht (Kap. 5) und "
        "Lösungsstrategie (Kap. 4) überein? 2) Werden alle Stakeholder "
        "(Kap. 1) durch die Schnittstellen (Kap. 3) bedient? "
        "3) Sind die Risiken (Kap. 11) durch Qualitätsszenarien (Kap. 10) "
        "abgedeckt? Liste alle gefundenen Inkonsistenzen auf."
    )


@mcp.prompt()
def project_summary() -> str:
    """Erstelle eine kompakte Projektzusammenfassung.

    Das LLM erstellt ein Executive Summary basierend auf allen
    verfügbaren arc42-Kapiteln.
    """
    return (
        "Erstelle eine kompakte Projektzusammenfassung (maximal 500 Wörter) "
        "basierend auf der arc42-Dokumentation. Berücksichtige: "
        "Aufgabenstellung und Ziele (Kap. 1), Lösungsstrategie (Kap. 4), "
        "die wichtigsten Architekturentscheidungen (Kap. 9) und "
        "bekannte Risiken (Kap. 11). Schreibe für ein technisches Publikum."
    )


@mcp.prompt()
def dependency_analysis() -> str:
    """Analysiere Abhängigkeiten in der Architektur.

    Instruiert das LLM, die Bausteinsicht auf Abhängigkeitsketten
    und potenzielle Kopplungen zu untersuchen.
    """
    return (
        "Analysiere die Abhängigkeiten in der Bausteinsicht (Kap. 5). "
        "Identifiziere: 1) Welche Komponenten voneinander abhängen, "
        "2) Ob es zirkuläre Abhängigkeiten gibt, "
        "3) Welche Schnittstellen (Kap. 3) zwischen den Komponenten "
        "verwendet werden, 4) Potenzielle Single Points of Failure. "
        "Schlage ggf. Verbesserungen vor."
    )


@mcp.prompt()
def review_changes() -> str:
    """Reviewe die aktuellen Architekturentscheidungen.

    Instruiert das LLM, die Entwurfsentscheidungen kritisch zu prüfen.
    """
    return (
        "Reviewe die aktuellen Entwurfsentscheidungen (Kap. 9) und "
        "Qualitätsszenarien (Kap. 10). Prüfe für jede Entscheidung: "
        "1) Ist die Begründung nachvollziehbar? "
        "2) Sind die Konsequenzen vollständig beschrieben? "
        "3) Stimmen die Entscheidungen mit den Qualitätszielen (Kap. 1) "
        "überein? Gib konkretes Feedback."
    )


@mcp.prompt()
def generate_test_cases(parent_name: str = "Neo4j MCP Server") -> str:
    """Generiere strukturierte Testfälle aus der Architekturdokumentation.

    Liest Kapitel 1 (Anforderungen), 6 (Laufzeitsicht), 10 (Qualitätsszenarien)
    und 11 (Risiken) und leitet daraus vollständige Testfälle im Gherkin-Format ab.

    Args:
        parent_name: Name des arc42-Projekts in Neo4j.
    """
    ch1  = read_arc42_chapter("1",  parent_name)
    ch6  = read_arc42_chapter("6",  parent_name)
    ch10 = read_arc42_chapter("10", parent_name)
    ch11 = read_arc42_chapter("11", parent_name)

    return (
        "Du bist ein erfahrener Software-Tester. Auf Basis der folgenden "
        "Architekturdokumentation leitest du strukturierte Testfälle ab.\n\n"
        "## Eingabe-Dokumentation\n\n"
        "### Kapitel 1 – Anforderungen\n"
        f"{ch1}\n\n"
        "### Kapitel 6 – Laufzeitsicht\n"
        f"{ch6}\n\n"
        "### Kapitel 10 – Qualitätsszenarien\n"
        f"{ch10}\n\n"
        "### Kapitel 11 – Risiken\n"
        f"{ch11}\n\n"
        "## Aufgabe\n\n"
        "Leite aus den obigen Kapiteln vollständige Testfälle ab. Halte dabei "
        "folgende Struktur ein:\n\n"
        "**Testfall-Typen:**\n"
        "- Aus Kapitel 10 (Qualitätsszenarien): Akzeptanztests im Gherkin-Format "
        "(Given / When / Then), ein Testfall pro Szenario.\n"
        "- Aus Kapitel 1 (Anforderungen): Funktionale Happy-Path-Tests, die prüfen, "
        "ob jede Anforderung erfüllt ist.\n"
        "- Aus Kapitel 6 (Laufzeitsicht): Integrationstests für die beschriebenen "
        "Komponenteninteraktionen und Sequenzabläufe.\n"
        "- Aus Kapitel 11 (Risiken): Negativtests und Edge-Cases, die den "
        "beschriebenen Schadensfall provozieren und die Systemreaktion prüfen.\n\n"
        "**Ausgabeformat pro Testfall:**\n"
        "| Feld | Inhalt |\n"
        "|------|--------|\n"
        "| TC-ID | Eindeutige ID, z. B. TC-QS-01, TC-REQ-01, TC-RT-01, TC-RI-01 |\n"
        "| Typ | Akzeptanztest / Funktionaler Test / Integrationstest / Negativtest |\n"
        "| Quelle | Verweis auf das Kapitel und das Quell-Element (z. B. QS-03) |\n"
        "| Vorbedingung (Given) | Systemzustand vor dem Test |\n"
        "| Aktion (When) | Auslösende Aktion oder Tool-Aufruf |\n"
        "| Erwartetes Ergebnis (Then) | Messbares, konkretes Ergebnis |\n"
        "| Priorität | hoch / mittel / niedrig |\n\n"
        "Erstelle für jedes Qualitätsszenario, jede Anforderung, jeden "
        "Laufzeitpfad und jeden Risikoeintrag mindestens einen Testfall. "
        "Sortiere die Ausgabe nach Typ."
    )


# =========================================================================
# UPDATE TOOLS (Epic 2 – Write-Access / Modify Existing Data)
# =========================================================================

@mcp.tool()
def update_requirement(old_task: str, new_task: str, parent_name: str = "Neo4j MCP Server") -> str:
    """Update an existing Requirement (Aufgabenstellung) in Chapter 1.

    Finds the requirement by its current text and replaces it.

    Args:
        old_task: Current text of the requirement to update.
        new_task: New text for the requirement.
        parent_name: Name of the arc42 project.
    """
    try:
        old_task = _validate_required(old_task, "old_task")
        new_task = _validate_required(new_task, "new_task")
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
def update_stakeholder(old_name: str, new_name: str = "", new_contact: str = "", new_expectation: str = "", parent_name: str = "Neo4j MCP Server") -> str:
    """Update an existing Stakeholder in Chapter 1.

    Finds the stakeholder by role/name and updates the specified fields.
    Only non-empty fields will be updated.

    Args:
        old_name: Current roleOrName of the stakeholder to find.
        new_name: New name/role (leave empty to keep current).
        new_contact: New contact info (leave empty to keep current).
        new_expectation: New expectation (leave empty to keep current).
        parent_name: Name of the arc42 project.
    """
    try:
        old_name = _validate_required(old_name, "old_name")
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
        records = _run_write(cypher, old_name=old_name, new_name=new_name, new_contact=new_contact, new_expectation=new_expectation, parent_name=parent_name)
        if not records:
            return f"## Not Found\n\nStakeholder '{old_name}' not found.\n"
        return f"## Success\n\nUpdated Stakeholder: **{old_name}**\n"
    except Exception as e:
        return _format_error("update_stakeholder", e)


@mcp.tool()
def update_quality_goal(old_goal: str, new_goal: str = "", new_motivation: str = "", parent_name: str = "Neo4j MCP Server") -> str:
    """Update an existing Quality Goal (Qualitätsziel) in Chapter 1.

    Args:
        old_goal: Current name of the quality goal to find.
        new_goal: New name (leave empty to keep current).
        new_motivation: New motivation text (leave empty to keep current).
        parent_name: Name of the arc42 project.
    """
    try:
        old_goal = _validate_required(old_goal, "old_goal")
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
        records = _run_write(cypher, old_goal=old_goal, new_goal=new_goal, new_motivation=new_motivation, parent_name=parent_name)
        if not records:
            return f"## Not Found\n\nQuality Goal '{old_goal}' not found.\n"
        return f"## Success\n\nUpdated Quality Goal: **{old_goal}**\n"
    except Exception as e:
        return _format_error("update_quality_goal", e)


@mcp.tool()
def update_documentation(title: str, new_content: str, parent_name: str = "Neo4j MCP Server") -> str:
    """Update the text content of an existing Konzept (Chapter 8).

    Args:
        title: Name of the existing concept to update.
        new_content: New text content for the concept.
        parent_name: Name of the arc42 project.
    """
    try:
        title = _validate_required(title, "title")
        new_content = _validate_required(new_content, "new_content")
    except ValueError as e:
        return _format_error("update_documentation", e)

    logger.info("Tool update_documentation: '%s'", title)
    cypher = (
        "MATCH (d:Arc42 {name: $parent_name})-[:hatKonzept]->(n:Konzept {name: $title}) "
        "SET n.text = $new_content, n.updated_at = datetime() "
        "RETURN n"
    )
    try:
        records = _run_write(cypher, title=title, new_content=new_content, parent_name=parent_name)
        if not records:
            return f"## Not Found\n\nKonzept '{title}' not found.\n"
        return f"## Success\n\nUpdated Konzept: **{title}**\n"
    except Exception as e:
        return _format_error("update_documentation", e)


@mcp.tool()
def update_design_decision(old_decision: str, new_decision: str = "", new_consequence: str = "", new_reasoning: str = "", parent_name: str = "Neo4j MCP Server") -> str:
    """Update an existing Design Decision (Entwurfsentscheidung) in Chapter 9.

    Args:
        old_decision: Current decision text to find.
        new_decision: New decision text (leave empty to keep current).
        new_consequence: New consequence (leave empty to keep current).
        new_reasoning: New reasoning (leave empty to keep current).
        parent_name: Name of the arc42 project.
    """
    try:
        old_decision = _validate_required(old_decision, "old_decision")
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
        records = _run_write(cypher, old_decision=old_decision, new_decision=new_decision, new_consequence=new_consequence, new_reasoning=new_reasoning, parent_name=parent_name)
        if not records:
            return f"## Not Found\n\nDesign Decision '{old_decision}' not found.\n"
        return f"## Success\n\nUpdated Design Decision: **{old_decision}**\n"
    except Exception as e:
        return _format_error("update_design_decision", e)


@mcp.tool()
def update_risk(old_description: str, new_description: str = "", new_impact: str = "", new_probability: str = "", new_status: str = "", parent_name: str = "Neo4j MCP Server") -> str:
    """Update an existing Risk (Risiko) in Chapter 11.

    Args:
        old_description: Current risk description (anforderung) to find.
        new_description: New description (leave empty to keep current).
        new_impact: New impact / Schadenshöhe (leave empty to keep current).
        new_probability: New probability (leave empty to keep current).
        new_status: New status (leave empty to keep current).
        parent_name: Name of the arc42 project.
    """
    try:
        old_description = _validate_required(old_description, "old_description")
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
        records = _run_write(cypher, old_description=old_description, new_description=new_description, new_impact=new_impact, new_probability=new_probability, new_status=new_status, parent_name=parent_name)
        if not records:
            return f"## Not Found\n\nRisk '{old_description}' not found.\n"
        return f"## Success\n\nUpdated Risk: **{old_description}**\n"
    except Exception as e:
        return _format_error("update_risk", e)


@mcp.tool()
def update_glossary_term(old_term: str, new_term: str = "", new_description: str = "", parent_name: str = "Neo4j MCP Server") -> str:
    """Update an existing Glossary Term (Glossar) in Chapter 12.

    Args:
        old_term: Current term to find.
        new_term: New term text (leave empty to keep current).
        new_description: New description (leave empty to keep current).
        parent_name: Name of the arc42 project.
    """
    try:
        old_term = _validate_required(old_term, "old_term")
    except ValueError as e:
        return _format_error("update_glossary_term", e)

    logger.info("Tool update_glossary_term: '%s'", old_term)
    set_clauses = []
    if new_term:
        set_clauses.append("n.begriff = $new_term")
    if new_description:
        set_clauses.append("n.beschreibung = $new_description")

    if not set_clauses:
        return "## Error\n\nMindestens ein neues Feld muss angegeben werden.\n"

    cypher = (
        "MATCH (d:Arc42 {name: $parent_name})-[:hasGlossar]->(n:Glossar {begriff: $old_term}) "
        f"SET {', '.join(set_clauses)} "
        "RETURN n"
    )
    try:
        records = _run_write(cypher, old_term=old_term, new_term=new_term, new_description=new_description, parent_name=parent_name)
        if not records:
            return f"## Not Found\n\nGlossar term '{old_term}' not found.\n"
        return f"## Success\n\nUpdated Glossar: **{old_term}**\n"
    except Exception as e:
        return _format_error("update_glossary_term", e)


# =========================================================================
# Diagram Tool (Epic 3 – Binary Data Access)
# =========================================================================

@mcp.tool()
def get_diagram(chapter: str, parent_name: str = "Neo4j MCP Server") -> str:
    """Retrieve the description and metadata of a diagram (Bausteinsicht/Laufzeitsicht/Verteilungssicht).

    Returns the text description associated with the diagram.
    The binary image data is stored in the database and served via the arc42doc Java app.

    Args:
        chapter: '5' for Bausteinsicht, '6' for Laufzeitsicht, '7' for Verteilungssicht.
        parent_name: Name of the arc42 project.
    """
    diagram_map = {
        "5": ("Image:Baustein", "bausteinsicht", "Bausteinsicht"),
        "6": ("Image:Laufzeit", "laufzeitsicht", "Laufzeitsicht"),
        "7": ("Image:Verteilung", "verteilungssicht", "Verteilungssicht"),
    }

    if chapter not in diagram_map:
        return "## Error\n\nBitte Kapitel 5, 6 oder 7 angeben.\n"

    label, rel, name = diagram_map[chapter]
    logger.info("Tool get_diagram: Kapitel %s (%s)", chapter, name)

    cypher = (
        "MATCH (d:Arc42 {{name: $parent_name}})-[:{rel}]->(n:{label}) "
        "RETURN n.description AS description, n.bildName AS bildName, n.bildMimeType AS mimeType"
    ).format(rel=rel, label=label)

    try:
        records = _run_read(cypher, parent_name=parent_name)
        if not records:
            return f"## {name}\n\n_(kein Diagramm vorhanden)_\n"

        r = records[0]
        desc = _clean_content(str(r.get("description", "")))
        bild_name = r.get("bildName", "")
        mime_type = r.get("mimeType", "")

        parts = [f"## {name} (Kapitel {chapter})\n"]
        if desc:
            parts.append(f"**Beschreibung:** {desc}\n")
        if bild_name:
            parts.append(f"**Bilddatei:** {bild_name} ({mime_type})\n")
        else:
            parts.append("_(kein Bild hochgeladen)_\n")
        return "\n".join(parts)
    except Exception as e:
        return _format_error("get_diagram", e)


# =========================================================================
# Mermaid Diagram Generation via Kroki API (QA-FL-01 – No local install needed)
# =========================================================================

_KROKI_BASE_URL = "https://kroki.io"
_KROKI_TIMEOUT_S = 30


def _mermaid_to_png_bytes(mermaid_code: str) -> bytes:
    """Send Mermaid code to Kroki API and return raw PNG bytes.

    Kroki encodes diagrams as: base64(zlib_compress(utf8_code))
    No API key needed. Free public service.
    """
    compressed = zlib.compress(mermaid_code.encode("utf-8"), 9)
    encoded = base64.urlsafe_b64encode(compressed).decode("ascii")
    url = f"{_KROKI_BASE_URL}/mermaid/png/{encoded}"
    logger.info("Kroki API request: %s…", url[:80])
    req = urllib.request.Request(url, headers={"User-Agent": "arc42doc-mcp-server/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=_KROKI_TIMEOUT_S) as resp:
            png_bytes = resp.read()
            logger.info("Kroki API response: %d bytes (PNG)", len(png_bytes))
            return png_bytes
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Kroki API HTTP-Fehler {e.code}: {e.reason}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Kroki API nicht erreichbar: {e.reason}") from e


@mcp.tool()
def generate_mermaid_diagram(
    chapter: str,
    mermaid_code: str,
    description: str,
    parent_name: str = "Neo4j MCP Server",
) -> str:
    """Generate a Mermaid diagram via Kroki API and save the PNG to Neo4j.

    Calls the free kroki.io API with Mermaid code, receives a PNG image,
    and stores it in the arc42 view node in Neo4j.

    Args:
        chapter: '5' for Bausteinsicht, '6' for Laufzeitsicht, '7' for Verteilungssicht.
        mermaid_code: Valid Mermaid diagram source code.
        description: Text description stored alongside the image in Neo4j.
        parent_name: Name of the arc42 project node in Neo4j.
    """
    chapter_map = {
        "5": {
            "label_old": "Image:Baustein",
            "rel_delete": "bausteinsicht",
            "label_new": "Image:Baustein",
            "rel_create": "bausteinsicht",
            "name": "Bausteinsicht",
            "file_name": "bausteinsicht.png",
        },
        "6": {
            "label_old": "Image:Laufzeit",
            "rel_delete": "laufzeitsicht",
            "label_new": "Image:Laufzeit",
            "rel_create": "laufzeitsicht",
            "name": "Laufzeitsicht",
            "file_name": "laufzeitsicht.png",
        },
        "7": {
            "label_old": "Image:Verteilung",
            "rel_delete": "verteilungssicht",
            "label_new": "Image:Verteilung",
            "rel_create": "verteilungssicht",
            "name": "Verteilungssicht",
            "file_name": "verteilungssicht.png",
        },
    }

    if chapter not in chapter_map:
        return "## Error\n\nBitte Kapitel 5, 6 oder 7 angeben.\n"

    try:
        mermaid_code = _validate_required(mermaid_code, "mermaid_code")
        description = _validate_required(description, "description")
    except ValueError as e:
        return _format_error("generate_mermaid_diagram", e)

    cfg = chapter_map[chapter]
    logger.info(
        "Tool generate_mermaid_diagram: Kapitel %s (%s), parent='%s'",
        chapter, cfg["name"], parent_name,
    )

    # 1. Mermaid → PNG via Kroki API
    try:
        png_bytes = _mermaid_to_png_bytes(mermaid_code)
    except RuntimeError as e:
        return f"## Error\n\n**Kroki API fehlgeschlagen:** {e}\n\nBitte Internetverbindung prüfen oder Mermaid-Code auf Syntax-Fehler kontrollieren.\n"

    # 2. PNG direkt in Neo4j speichern (identisches Schema wie add_*_view)
    cypher = (
        "MERGE (d:Arc42 {{name: $parent_name}}) "
        "WITH d "
        "OPTIONAL MATCH (d)-[:{rel_delete}]->(old:{label_old}) "
        "DETACH DELETE old "
        "WITH d "
        "CREATE (n:{label_new} {{ "
        "   description: $description, "
        "   bildName: $file_name, "
        "   bildMimeType: 'image/png', "
        "   bildPath: $png_bytes, "
        "   uxfName: '', "
        "   uxfMimeType: '', "
        "   uxfPath: $empty_bytes "
        "}}) "
        "MERGE (d)-[:{rel_create}]->(n) "
        "RETURN n"
    ).format(
        rel_delete=cfg["rel_delete"],
        label_old=cfg["label_old"],
        label_new=cfg["label_new"],
        rel_create=cfg["rel_create"],
    )

    try:
        _run_write(
            cypher,
            parent_name=parent_name,
            description=description,
            file_name=cfg["file_name"],
            png_bytes=png_bytes,
            empty_bytes=b"",
        )
        return (
            f"## Success\n\n"
            f"Diagramm **{cfg['name']}** (Kapitel {chapter}) generiert und in Neo4j gespeichert.\n\n"
            f"- **Dateiname:** {cfg['file_name']}\n"
            f"- **Größe:** {len(png_bytes):,} Bytes\n"
            f"- **Beschreibung:** {description}\n"
        )
    except Exception as e:
        return _format_error("generate_mermaid_diagram", e)


# =========================================================================
# Intelligent Analysis Tools (Explain Node, Consistency Checks)
# =========================================================================

@mcp.tool()
def explain_node(title: str, parent_name: str = "Neo4j MCP Server") -> str:
    """Erkläre einen spezifischen Dokumentations-Knoten inkl. Kontext.

    Finds a single node by its human-readable title (e.g. Stakeholder-Name,
    Risiko-ID, Qualitätsziel) and returns:
      - a compact summary (type, main properties)
      - all directly related neighbours with relationship types
    """
    try:
        title = _validate_required(title, "title")
    except ValueError as e:
        return _format_error("explain_node", e)

    logger.info("Tool explain_node: '%s'", title)

    cypher = (
        "MATCH (d:Arc42 {name: $parent_name})-[]-(n) "
        "WHERE "
        "  n.title = $title OR "
        "  n.name = $title OR "
        "  n.begriff = $title OR "
        "  n.roleOrName = $title OR "
        "  n.konvention = $title OR "
        "  n.randbedingung = $title OR "
        "  n.anforderung = $title OR "
        "  n.qualitaetsscenario = $title OR "
        "  n.qualitaetsziel = $title "
        "WITH DISTINCT n "
        "LIMIT 1 "
        "OPTIONAL MATCH (n)-[r]-(m) "
        "RETURN n, labels(n) AS labels, "
        "       collect({rel: type(r), other: m, otherLabels: labels(m)}) AS edges"
    )

    try:
        records = _run_read(cypher, parent_name=parent_name, title=title)
        if not records:
            return f"## Not Found\n\nKein Knoten mit Titel '{title}' gefunden.\n"

        rec = records[0]
        node = rec["n"]
        labels = rec["labels"]
        node_data = dict(node.items())
        main_title, content = _extract_title_and_content(node_data, labels)

        lines: List[str] = []
        lines.append(f"## Knoten-Erklärung: {main_title}\n")
        lines.append("### Typ und Eigenschaften\n")
        lines.append(f"- **Labels:** {', '.join(labels)}")
        for k, v in node_data.items():
            if isinstance(v, (bytes, bytearray)):
                continue
            if k in ("bildPath", "uxfPath"):
                continue
            lines.append(f"- **{k}**: {_clean_content(str(v))}")

        if content:
            lines.append("\n### Hauptinhalt\n")
            lines.append(content)

        edges = rec.get("edges") or []
        if edges:
            lines.append("\n### Direkte Beziehungen\n")
            for edge in edges:
                rel = edge.get("rel")
                other = edge.get("other")
                other_labels = edge.get("otherLabels") or []
                if other is None or rel is None:
                    continue
                other_data = dict(other.items())
                other_title, _ = _extract_title_and_content(other_data, other_labels)
                lines.append(
                    f"- `-{rel}-` → **{other_title}** "
                    f"({', '.join(other_labels) if other_labels else 'Unknown'})"
                )
        else:
            lines.append("\n### Direkte Beziehungen\n")
            lines.append("_(keine direkten Nachbarn gefunden)_")

        return "\n".join(lines) + "\n"
    except Exception as e:
        return _format_error("explain_node", e)


@mcp.tool()
def check_consistency_report(parent_name: str = "Neo4j MCP Server") -> str:
    """Führt einfache, aber konkrete Konsistenzchecks über mehrere Kapitel aus.

    Aktuell implementierte Prüfungen:
      1. Risiken ohne abdeckendes Qualitätsszenario (Text-Referenz RI-XX).
      2. Qualitätsszenarien, die auf nicht existierende Risiken verweisen.
      3. Qualitätsszenarien ohne Verknüpfung zu einem Qualitätsziel.
    """
    logger.info("Tool check_consistency_report aufgerufen")

    try:
        # 1) Alle Risiken laden
        risks_records = _run_read(
            "MATCH (d:Arc42 {name: $parent_name})-[:hasRisiko]->(r:Risiko) "
            "RETURN r.anforderung AS anforderung",
            parent_name=parent_name,
        )
        risk_ids: List[str] = []
        for r in risks_records:
            desc = _safe_str(r.get("anforderung"), "")
            # Risikokürzel extrahieren, z.B. "RI-01" am Anfang
            m = re.match(r"(RI-\d+)", desc)
            if m:
                risk_ids.append(m.group(1))

        # 2) Alle Qualitätsszenarien laden
        qs_records = _run_read(
            "MATCH (d:Arc42 {name: $parent_name})-[:hasQualityScenario]->(q:Qualitaetsscenario) "
            "RETURN q.qualitaetsscenario AS name, q.risk AS risk_text",
            parent_name=parent_name,
        )

        # Mapping: Risiko-ID -> von QS abgedeckt?
        covered_risks: Dict[str, bool] = {rid: False for rid in risk_ids}
        # QS mit Referenzen auf nicht existierende Risiken
        inconsistent_qs: List[str] = []

        risk_id_pattern = re.compile(r"(RI-\d+)")
        for rec in qs_records:
            qs_name = _safe_str(rec.get("name"), "")
            risk_text = _safe_str(rec.get("risk_text"), "")
            refs = set(risk_id_pattern.findall(risk_text))
            if not refs:
                continue
            for rid in refs:
                if rid in covered_risks:
                    covered_risks[rid] = True
                else:
                    inconsistent_qs.append(
                        f"- Qualitätsszenario **{qs_name}** verweist auf unbekanntes Risiko `{rid}`."
                    )

        # 3) QS ohne Verknüpfung zu Qualitaetsziel
        qs_no_qz = _run_read(
            "MATCH (d:Arc42 {name: $parent_name})-[:hasQualityScenario]->(q:Qualitaetsscenario) "
            "WHERE NOT (q)-[:konkretisiert]->(:Qualitaetsziel) "
            "RETURN q.qualitaetsscenario AS name",
            parent_name=parent_name,
        )

        lines: List[str] = []
        lines.append("# Konsistenzbericht\n")

        # Abschnitt 1: Risiken ohne abdeckendes QS
        lines.append("## 1. Risiken ohne abdeckendes Qualitätsszenario\n")
        uncovered = [rid for rid, cov in covered_risks.items() if not cov]
        if not uncovered:
            lines.append("Alle dokumentierten Risiken werden in mindestens einem Qualitätsszenario referenziert.\n")
        else:
            lines.append(
                "Die folgenden Risiko-IDs werden in keinem Qualitätsszenario-Text erwähnt "
                "(Feld `risk` der Qualitaetsscenario-Knoten):\n"
            )
            for rid in sorted(uncovered):
                lines.append(f"- `{rid}`")
            lines.append("")

        # Abschnitt 2: QS mit Referenz auf nicht existierende Risiken
        lines.append("## 2. Qualitätsszenarien mit ungültigen Risiko-Referenzen\n")
        if not inconsistent_qs:
            lines.append("Keine Verweise auf nicht existierende Risiken gefunden.\n")
        else:
            lines.extend(inconsistent_qs)
            lines.append("")

        # Abschnitt 3: QS ohne Verknüpfung zu Qualitaetsziel
        lines.append("## 3. Qualitätsszenarien ohne verknüpftes Qualitätsziel\n")
        if not qs_no_qz:
            lines.append(
                "Alle Qualitätsszenarien sind über die Beziehung `:konkretisiert` mit einem Qualitaetsziel verknüpft.\n"
            )
        else:
            lines.append(
                "Die folgenden Qualitätsszenarien haben keine `:konkretisiert`-Beziehung "
                "zu einem Qualitaetsziel-Knoten:\n"
            )
            for rec in qs_no_qz:
                lines.append(f"- **{_safe_str(rec.get('name'), '')}**")
            lines.append("")

        return "\n".join(lines)
    except Exception as e:
        return _format_error("check_consistency_report", e)


# =========================================================================
# Entry Point
# =========================================================================
if __name__ == "__main__":
    logger.info("arc42doc MCP Server wird gestartet …")
    mcp.run()

