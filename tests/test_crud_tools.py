"""Exemplarische Tests für je einen Add-, Update- und Delete-Pfad.

Die fachliche Logik der Tool-Funktionen liegt fast vollständig in den
Cypher-Statements; geprüft werden Validierung, Cypher-Bestandteile und
das Markdown-Antwortformat. Stellvertretend wurden Tools aus Kap. 1
(``add_requirement``) und Kap. 9 (``add_design_decision``,
``delete_design_decision``) gewählt — diese Operationen wurden auch in
der Probanden-Evaluation (Kap. 6.2) ausgeführt.

Der mit ``pytest.mark.xfail`` markierte Regressionstest am Ende
dokumentiert einen während der Test-Implementierung aufgedeckten Bug
in ``delete_diagram`` (Kap. 5.4.5 der MA).
"""

from __future__ import annotations

import pytest


def _capture(monkeypatch, module, return_value=None):
    """Ersetzt ``_run_write`` durch einen Capture-Mock und gibt die
    aufgezeichneten ``(cypher, kwargs)``-Tupel zurück."""
    calls: list[tuple[str, dict]] = []

    def fake(cypher, **kwargs):
        calls.append((cypher, kwargs))
        return return_value if return_value is not None else []

    monkeypatch.setattr(module, "_run_write", fake)
    return calls


# --- Add-Pfad: add_requirement (Kap. 1) -----------------------------------
def test_add_requirement_baut_korrekte_cypher(monkeypatch):
    from neo4j_mcp_server.tools import ch01_introduction as ch01

    calls = _capture(monkeypatch, ch01)
    out = ch01.add_requirement("Buchausleihe ermöglichen", parent_name="SmartLibrary")

    assert "## Success" in out
    assert "Buchausleihe ermöglichen" in out
    cypher, params = calls[0]
    assert "Aufgabenstellung" in cypher
    assert "hasRequirement" in cypher
    assert params["task"] == "Buchausleihe ermöglichen"
    assert params["parent_name"] == "SmartLibrary"


def test_add_requirement_lehnt_leeren_text_ab(monkeypatch):
    from neo4j_mcp_server.tools import ch01_introduction as ch01

    calls = _capture(monkeypatch, ch01)
    out = ch01.add_requirement("   ", parent_name="P")

    assert "## Error" in out
    assert calls == []  # kein DB-Aufruf, wenn Validierung fehlschlägt


# --- Add mit mehreren Pflichtfeldern: add_design_decision (Kap. 9) --------
def test_add_design_decision_setzt_alle_felder_in_cypher(monkeypatch):
    from neo4j_mcp_server.tools import ch09_decisions as ch09

    calls = _capture(monkeypatch, ch09)
    out = ch09.add_design_decision(
        decision="Einsatz von Flyway 9.2",
        consequence="Migrationen in CI/CD-Pipeline",
        reasoning="Bisher manuelle Migrationen → Schemafehler",
        importance="hoch",
        parent_name="SmartLibrary",
    )

    assert "## Success" in out
    cypher, params = calls[0]
    assert "Entwurfsentscheidung" in cypher
    assert "hasEntwurfsentscheidung" in cypher
    assert params["decision"] == "Einsatz von Flyway 9.2"
    assert params["importance"] == "hoch"


# --- Delete-Pfad und Human-in-the-Loop-Hinweis im Docstring (Kap. 5.3.4) --
def test_delete_design_decision_meldet_warnung_wenn_kein_treffer(monkeypatch):
    from neo4j_mcp_server.tools import ch09_decisions as ch09

    _capture(monkeypatch, ch09, return_value=[{"c": 0}])
    out = ch09.delete_design_decision("Existiert nicht", parent_name="P")
    assert "## Warning" in out


def test_delete_design_decision_docstring_warnt_vor_loeschung():
    """Human-in-the-Loop nach Kap. 5.3.4: Docstrings destruktiver Tools
    enthalten den Bestätigungs-Hinweis, den Claude liest und der dazu
    führt, dass das LLM eine Bestätigung anfordert."""
    from neo4j_mcp_server.tools import ch09_decisions as ch09

    assert "ohne nochmal nachzufragen" in (ch09.delete_design_decision.__doc__ or "")


# --- Regressionstest für aufgedeckten Bug in delete_diagram (xfail) --------
@pytest.mark.xfail(
    reason=(
        "Bekannter Bug: ch05_07_diagrams.delete_diagram baut die Cypher-"
        "Query mit str.format(rel=…, label=…) auf, der String enthält aber "
        "{name: $parent_name}. Python interpretiert {name} als Format-"
        "Variable und wirft KeyError. Fix: doppelte geschweifte Klammern "
        "{{name: $parent_name}} oder str.replace verwenden."
    ),
    raises=KeyError,
    strict=True,
)
def test_delete_diagram_kapitel_5_loest_bekannten_format_bug_aus(monkeypatch):
    from neo4j_mcp_server.tools import ch05_07_diagrams as ch507

    _capture(monkeypatch, ch507, return_value=[{"c": 1}])
    ch507.delete_diagram(chapter="5", parent_name="P")
