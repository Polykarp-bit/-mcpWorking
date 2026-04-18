from __future__ import annotations

import os
from typing import Any, Dict, List

# Importiere Tool-Module, damit die Decorators die Tools beim Importieren registrieren.
# (Behalte dies weit oben, damit MCP-Hosts ein konsistentes Tool-Set sehen.)
from .tools import search as _tools_search  # noqa: F401
from .tools import ch01_introduction as _tools_ch01  # noqa: F401
from .tools import ch02_constraints as _tools_ch02  # noqa: F401
from .tools import ch03_context as _tools_ch03  # noqa: F401
from .tools import ch04_strategy as _tools_ch04  # noqa: F401
from .tools import ch05_07_diagrams as _tools_ch05_07  # noqa: F401
from .tools import ch08_concepts as _tools_ch08  # noqa: F401
from .tools import ch09_decisions as _tools_ch09  # noqa: F401
from .tools import ch10_quality_scenarios as _tools_ch10  # noqa: F401
from .tools import ch11_risks as _tools_ch11  # noqa: F401
from .tools import ch12_glossary as _tools_ch12  # noqa: F401
from .tools import ch13_sustainability as _tools_ch13  # noqa: F401
from .tools import analysis as _tools_analysis  # noqa: F401

from .core import (
    logger,
    mcp,
    _MAX_INPUT_LEN,
    _clean_content,
    _extract_title_and_content,
    _format_doc,
    _format_error,
    _get_driver,
    _run_read,
    _run_write,
    _safe_str,
)


def _validate_required(value: str, field_name: str) -> str:
    """Prüft, ob ein erforderliches String-Feld nicht leer ist.

    Hinweis: Bleibt in diesem Modul zwecks Abwärtskompatibilität mit Tests, die
    `_MAX_INPUT_LEN` an `neo4j_mcp_server.server` per Monkeypatch überschreiben.
    """
    v = str(value).strip() if value else ""
    if not v:
        raise ValueError(f"Parameter '{field_name}' darf nicht leer sein.")
    if len(v) > _MAX_INPUT_LEN:
        raise ValueError(
            f"Parameter '{field_name}' ist zu lang ({len(v)} Zeichen, max {_MAX_INPUT_LEN})."
        )
    return v


def _require_confirm(confirm: bool, action: str) -> str | None:
    """Guardrail für destruktive Operationen (Human-in-the-Loop).

    Gibt eine Markdown-Nachricht zurück, falls die Bestätigung fehlt, ansonsten None.
    """
    if confirm is True:
        return None
    return (
        "## Confirmation Required\n\n"
        f"Diese Aktion ist destruktiv (**{action}**). "
        "Setze `confirm=true`, um fortzufahren.\n"
    )

@mcp.tool()
def read_arc42_chapter(chapter: str, *, parent_name: str) -> str:
    """Liest den Inhalt eines bestimmten arc42-Kapitels (1-13) aus.

    Gibt alle Knoten zurück, die zu dem angegebenen Kapitel gehören, formatiert in Markdown.
    Jedes Kapitel entspricht einer Standard-arc42-Sektion:
      1=Einführung/Ziele, 2=Randbedingungen, 3=Kontextabgrenzung,
      4=Lösungsstrategie, 5=Bausteinsicht, 6=Laufzeitsicht,
      7=Verteilungssicht, 8=Querschnittliche Konzepte,
      9=Entwurfsentscheidungen, 10=Qualitätsszenarien,
      11=Risiken und SWOT, 12=Glossar, 13=Nachhaltigkeit.

    Args:
        chapter: Kapitelnummer als String ('1' bis '13').
        parent_name: Name des arc42-Projekts.
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
        "11": [
            ("Risiko", "hasRisiko", "anforderung"),
            ("TextEingabe", "hasTextEingabe", "content"),
        ],
        "12": [("Glossar", "hasGlossar", "begriff")],
        "13": [("Nachhaltigkeitsziele", "hasNachhaltigkeitsziele", "greengoal")]
    }

    if chapter not in chapter_map:
        return f"Unbekanntes Kapitel: {chapter}. Bitte 1-13 angeben."

    chapter_names = {
        "1": "Einführung und Ziele", "2": "Randbedingungen",
        "3": "Kontextabgrenzung", "4": "Lösungsstrategie",
        "5": "Bausteinsicht", "6": "Laufzeitsicht",
        "7": "Verteilungssicht", "8": "Querschnittliche Konzepte",
        "9": "Entwurfsentscheidungen", "10": "Qualitätsszenarien",
        "11": "Risiken und SWOT", "12": "Glossar",
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
                if chapter == "11" and label == "TextEingabe":
                    cypher = (
                        "MATCH (d:Arc42 {name: $parent_name})-[:hasTextEingabe]->(n:TextEingabe) "
                        "WHERE n.type IN ['STRENGTH', 'WEAKNESS', 'OPPORTUNITY', 'THREAT'] "
                        "RETURN n"
                    )

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
# MCP RESSOURCEN (Epic 1 – Read-Access)
# =========================================================================

@mcp.resource("arc42://chapter/{chapter_number}")
def get_chapter_resource(chapter_number: str) -> str:
    """Liest ein bestimmtes arc42-Kapitel (1-13) als eine MCP Resource.

    URI-Muster: arc42://chapter/1  bis  arc42://chapter/13

    Benötigt die Umgebungsvariable (Env) ``ARC42_PARENT_NAME`` (Arc42-Projektname in Neo4j), analog zu den MCP Tool-Aufrufen.
    """
    logger.info("Resource arc42://chapter/%s abgerufen", chapter_number)
    parent_name = os.environ.get("ARC42_PARENT_NAME", "").strip()
    if not parent_name:
        return (
            "## Error\n\n"
            "Für diese Resource muss die Umgebungsvariable **`ARC42_PARENT_NAME`** "
            "auf den Namen des Arc42-Projekts in Neo4j gesetzt sein "
            "(in der MCP-Server-`env`-Konfiguration von Cursor/Claude).\n"
        )
    return read_arc42_chapter(chapter_number, parent_name=parent_name)


@mcp.resource("arc42://overview")
def get_overview_resource() -> str:
    """High-Level-Übersicht des arc42-Projekts – listet alle Kapitel mit einer Zusammenfassung auf."""
    logger.info("Resource arc42://overview abgerufen")
    parts = ["# arc42 Projektübersicht\n"]
    chapter_names = {
        "1": "Einführung und Ziele", "2": "Randbedingungen",
        "3": "Kontextabgrenzung", "4": "Lösungsstrategie",
        "5": "Bausteinsicht", "6": "Laufzeitsicht",
        "7": "Verteilungssicht", "8": "Querschnittliche Konzepte",
        "9": "Entwurfsentscheidungen", "10": "Qualitätsszenarien",
        "11": "Risiken und SWOT", "12": "Glossar",
        "13": "Nachhaltigkeit",
    }
    for num, name in chapter_names.items():
        parts.append(f"- **Kapitel {num}**: {name} → `arc42://chapter/{num}`")
    return "\n".join(parts) + "\n"


# =========================================================================
# MCP PROMPTS (Vordefinierte Vorlagen für die LLM-Interaktion)
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
def generate_test_cases(parent_name: str) -> str:
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

# --- Neu hinzugefuegte Tools (Dynamische Projekte) ---

@mcp.tool()
def create_project(project_name: str) -> str:
    """Erstellt explizit einen neuen Arc42-Projektknoten (Node).
    
    Obwohl das Hinzufügen von Elementen (wie add_requirement) das Projekt implizit erstellt, falls es fehlt,
    erlaubt dieses Tool die explizite Erstellung eines leeren Projekt-Frameworks. Verwende dies beim Start eines neuen Projekts.
    """
    try:
        # Hinweis: server.py hat kein validate_required im lokalen Scope. Doch, über `_validate_required` in `.core`!
        project_name = _validate_required(project_name, "project_name")
    except ValueError as e:
        return _format_error("create_project", e)
        
    cypher = (
        "MERGE (d:Arc42 {name: $project_name}) "
        "RETURN d"
    )
    try:
        _run_write(cypher, project_name=project_name)
        return f"## Erfolgreich\n\nProjekt **{project_name}** wurde erstellt (oder existiert bereits).\n"
    except Exception as e:
        return _format_error("create_project", e)


@mcp.tool()
def list_projects() -> str:
    """Listet alle vorhandenen Arc42-Projekte in der Datenbank auf.
    Verwende dies, um zu sehen, welche Projekte existieren, bevor andere Tools aufgerufen werden.
    """
    cypher = "MATCH (d:Arc42) RETURN id(d) as id, d.name as name"
    try:
        res = _run_write(cypher)
        if not res:
            return "## Projects\n\nKeine Projekte gefunden.\n"
        output = "## Verfügbare Projekte\n\n"
        for r in res:
            output += f"- **{r.get('name', 'Unnamed')}** (ID: {r.get('id')})\n"
        return output
    except Exception as e:
        return _format_error("list_projects", e)

@mcp.tool()
def rename_project(old_name: str, new_name: str) -> str:
    """Benennt ein Root-Projekt (Arc42 Node) in der Datenbank um."""
    try:
        old_name = _validate_required(old_name, "old_name")
        new_name = _validate_required(new_name, "new_name")
    except ValueError as e:
        return _format_error("rename_project", e)
    
    cypher = (
        "MATCH (n:Arc42 {name: $old_name}) "
        "SET n.name = $new_name "
        "RETURN n"
    )
    try:
        records = _run_write(cypher, old_name=old_name, new_name=new_name)
        if not records:
            return f"## Not Found\n\nKein Projekt mit Namen '{old_name}' gefunden.\n"
        return f"## Success\n\nProjekt '{old_name}' wurde erfolgreich in '{new_name}' umbenannt.\n"
    except Exception as e:
        return _format_error("rename_project", e)

# =========================================================================
# Einstiegspunkt (Entry Point)
# =========================================================================
def main(transport: str = "stdio"):
    logger.info("arc42doc MCP Server wird gestartet …")
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
