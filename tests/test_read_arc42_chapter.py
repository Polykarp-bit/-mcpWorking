"""Tests für das zentrale Lesetool ``read_arc42_chapter``.

Verifiziert das ``chapter_map``-Pattern (Kap. 5.3.1) am Beispiel von
Kapitel 1 sowie den Fehlerpfad bei Verbindungsproblemen (QA-RE-01).
"""

from __future__ import annotations

from unittest.mock import MagicMock


def _fake_record(props):
    """Bildet einen Neo4j-Record nach (``record["n"]`` mit ``items()``)."""
    node = MagicMock()
    node.items.return_value = list(props.items())
    return {"n": node}


def _fake_driver(record_lists):
    """Mock-Driver, der pro session.run() die nächste Liste zurückgibt
    und alle Aufrufe in ``driver.calls`` sammelt."""
    driver = MagicMock()
    driver.calls = []
    session = MagicMock()
    session.__enter__.return_value = session
    session.__exit__.return_value = False
    iter_records = iter(record_lists)

    def fake_run(cypher, **params):
        driver.calls.append({"cypher": cypher, "params": params})
        return iter(next(iter_records, []))

    session.run.side_effect = fake_run
    driver.session.return_value = session
    return driver


def test_read_arc42_chapter_kapitel_1_baut_die_drei_kapitel_queries(monkeypatch):
    """Kapitel 1 erzeugt laut chapter_map drei Queries (Aufgabenstellung,
    Qualitätsziel, Stakeholder) und liefert die Inhalte als Markdown."""
    from neo4j_mcp_server import server

    driver = _fake_driver([
        [_fake_record({"aufgabe": "Buchausleihe ermöglichen"})],
        [_fake_record({"qualitaetsziel": "Antwortzeit < 2s"})],
        [_fake_record({"roleOrName": "Bibliothekar"})],
    ])
    monkeypatch.setattr(server, "_get_driver", lambda: driver)

    out = server.read_arc42_chapter("1", parent_name="SmartLibrary")

    assert out.startswith("# Kapitel 1: Einführung und Ziele")
    assert len(driver.calls) == 3
    cyphers = " | ".join(c["cypher"] for c in driver.calls)
    assert "hasRequirement" in cyphers
    assert "hasQualityGoal" in cyphers
    assert "hasStakeholder" in cyphers
    assert "Buchausleihe ermöglichen" in out
    assert "Bibliothekar" in out


def test_read_arc42_chapter_db_fehler_wird_strukturiert_gemeldet(monkeypatch):
    """Bei einer Driver-Exception greift _format_error und liefert eine
    strukturierte Markdown-Fehlermeldung (QA-RE-01 Fehlertoleranz)."""
    from neo4j_mcp_server import server

    def boom():
        raise RuntimeError("connection refused")

    monkeypatch.setattr(server, "_get_driver", boom)

    out = server.read_arc42_chapter("1", parent_name="SmartLibrary")
    assert "## Error" in out
    assert "RuntimeError" in out
    assert "connection refused" in out
