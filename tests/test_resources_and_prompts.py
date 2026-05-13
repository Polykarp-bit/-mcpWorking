"""Tests für eine MCP Resource und einen MCP Prompt.

* ``get_chapter_resource`` (URI ``arc42://chapter/{chapter_number}``)
  benötigt die Umgebungsvariable ``ARC42_PARENT_NAME`` und delegiert an
  ``read_arc42_chapter`` (Kap. 5.3.2).
* ``generate_test_cases`` lädt zur Laufzeit die Kapitel 1, 6, 10 und 11
  und baut daraus einen System-Prompt im Gherkin-Schema (Kap. 5.3.3).
"""

from __future__ import annotations


def test_get_chapter_resource_ohne_parent_name_meldet_fehler(monkeypatch):
    """Ohne gesetzte Umgebungsvariable darf die Resource keinen DB-Zugriff
    machen, sondern eine erklärende Fehlermeldung zurückgeben."""
    from neo4j_mcp_server import server

    monkeypatch.delenv("ARC42_PARENT_NAME", raising=False)
    out = server.get_chapter_resource("1")

    assert "## Error" in out
    assert "ARC42_PARENT_NAME" in out


def test_get_chapter_resource_delegiert_an_read_arc42_chapter(monkeypatch):
    """Bei gesetzter Env-Variable wird die Anfrage transparent an
    ``read_arc42_chapter`` weitergereicht — keine duplizierte Logik."""
    from neo4j_mcp_server import server

    monkeypatch.setenv("ARC42_PARENT_NAME", "SmartLibrary")
    captured = {}

    def fake_read(chapter, *, parent_name):
        captured["chapter"] = chapter
        captured["parent_name"] = parent_name
        return f"# Kapitel {chapter}"

    monkeypatch.setattr(server, "read_arc42_chapter", fake_read)
    out = server.get_chapter_resource("5")

    assert captured == {"chapter": "5", "parent_name": "SmartLibrary"}
    assert "Kapitel 5" in out


def test_generate_test_cases_laedt_kapitel_1_6_10_und_11(monkeypatch):
    """Laut Kap. 5.3.3 lädt der Prompt zur Laufzeit Kapitel 1, 6, 10 und 11
    aus Neo4j und fordert Gherkin-Format (Given/When/Then) als Ausgabe."""
    from neo4j_mcp_server import server

    geladen: list[str] = []

    def fake_read(chapter, parent_name):
        geladen.append(chapter)
        return f"# Kapitel {chapter} Inhalt"

    monkeypatch.setattr(server, "read_arc42_chapter", fake_read)
    prompt = server.generate_test_cases(parent_name="SmartLibrary")

    assert sorted(geladen) == ["1", "10", "11", "6"]
    assert "Gherkin" in prompt
    assert "Given" in prompt and "When" in prompt and "Then" in prompt
