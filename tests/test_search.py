"""Tests für die Volltextsuche ``search_docs``.

``search_docs`` ist neben ``read_arc42_chapter`` das zweite zentrale
Lesetool und wurde in mehreren Probanden-Sitzungen der Evaluation
benutzt (Kap. 6.4).
"""

from __future__ import annotations

from unittest.mock import MagicMock


def _fake_record(props, labels):
    node = MagicMock()
    node.items.return_value = list(props.items())
    return {"n": node, "labels": labels}


def test_search_docs_uebergibt_query_und_liefert_treffer(monkeypatch):
    from neo4j_mcp_server.tools import search

    captured = {}

    def fake_run_read(cypher, **kwargs):
        captured["cypher"] = cypher
        captured["kwargs"] = kwargs
        return [_fake_record({"name": "Bausteinsicht", "text": "Modulare Struktur"},
                             labels=["Image", "Baustein"])]

    monkeypatch.setattr(search, "_run_read", fake_run_read)

    out = search.search_docs("Bausteinsicht")

    assert "Bausteinsicht" in out
    assert "Modulare Struktur" in out
    assert captured["kwargs"]["search_term"] == "Bausteinsicht"
    assert "toLower" in captured["cypher"]  # Case-Insensitive-Suche


def test_search_docs_lehnt_leere_query_ab(monkeypatch):
    from neo4j_mcp_server.tools import search

    calls = []
    monkeypatch.setattr(search, "_run_read", lambda c, **kw: calls.append(c) or [])

    out = search.search_docs("   ")
    assert "non-empty" in out
    assert calls == []  # keine DB-Anfrage bei leerer Query
