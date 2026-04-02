import pytest


def test_env_uses_default_when_missing(monkeypatch):
    from neo4j_mcp_server import core

    monkeypatch.delenv("SOME_VAR", raising=False)
    assert core._env("SOME_VAR", "default") == "default"


def test_env_uses_default_when_empty(monkeypatch):
    from neo4j_mcp_server import core

    monkeypatch.setenv("SOME_VAR", "")
    assert core._env("SOME_VAR", "default") == "default"


def test_env_uses_value_when_set(monkeypatch):
    from neo4j_mcp_server import core

    monkeypatch.setenv("SOME_VAR", "value")
    assert core._env("SOME_VAR", "default") == "value"


def test_clean_content_handles_empty_and_strips():
    from neo4j_mcp_server import core

    assert core._clean_content("") == ""
    assert core._clean_content(None) == ""
    assert core._clean_content("  hi  ") == "hi"


def test_clean_content_removes_html_and_collapses_newlines():
    from neo4j_mcp_server import core

    raw = "<p>Hello</p>\n\n\n\nWorld"
    assert core._clean_content(raw) == "Hello\n\nWorld"


def test_safe_str_fallback_on_none():
    from neo4j_mcp_server import core

    assert core._safe_str(None, fallback="x") == "x"


def test_safe_str_fallback_on_str_error():
    from neo4j_mcp_server import core

    class BadStr:
        def __str__(self):
            raise RuntimeError("boom")

    assert core._safe_str(BadStr(), fallback="fallback") == "fallback"


def test_extract_title_and_content_fallbacks_and_cleaning():
    from neo4j_mcp_server import core

    title, content = core._extract_title_and_content(
        {"foo": "bar", "content": "<b>x</b>\n\n\n\ny"}, labels=["Documentation"]
    )
    assert title == "Documentation"
    assert content == "x\n\ny"


def test_extract_title_and_content_text_eingabe_title_type():
    from neo4j_mcp_server import core

    node_data = {"content": "Kapitel 1", "type": "TITLE"}
    title, content = core._extract_title_and_content(node_data, labels=["TextEingabe"])
    assert title == "Kapitel 1"
    assert content == ""


def test_format_doc_inserts_no_content_placeholder():
    from neo4j_mcp_server import core

    out = core._format_doc("Title", "", node_type="")
    assert out.startswith("## Title")
    assert "_(no content)_" in out


def test_format_doc_prefixes_node_type():
    from neo4j_mcp_server import core

    out = core._format_doc("Title", "Body", node_type="Konzept")
    assert out.startswith("## [Konzept] Title")


def test_format_error_contains_action_type_and_message():
    from neo4j_mcp_server import core

    err = ValueError("nope")
    out = core._format_error("do_thing", err)
    assert "## Error" in out
    assert "**Action:** do_thing" in out
    assert "`ValueError`" in out
    assert "nope" in out

