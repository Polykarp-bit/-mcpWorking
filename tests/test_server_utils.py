import pytest


def test_validate_required_rejects_empty():
    from neo4j_mcp_server import server

    with pytest.raises(ValueError, match="darf nicht leer sein"):
        server._validate_required("", "title")

    with pytest.raises(ValueError, match="darf nicht leer sein"):
        server._validate_required("   ", "title")


def test_validate_required_rejects_too_long(monkeypatch):
    from neo4j_mcp_server import server

    monkeypatch.setattr(server, "_MAX_INPUT_LEN", 5)
    with pytest.raises(ValueError, match="ist zu lang"):
        server._validate_required("123456", "title")


def test_clean_content_removes_html_and_excess_newlines():
    from neo4j_mcp_server import server

    raw = "<p>Hello</p>\n\n\n\nWorld"
    assert server._clean_content(raw) == "Hello\n\nWorld"


def test_extract_title_and_content_prefers_known_props_and_cleans_content():
    from neo4j_mcp_server import server

    node_data = {
        "name": "Persistenz",
        "text": "<b>Neo4j</b>\n\n\nDetails",
    }
    title, content = server._extract_title_and_content(node_data, labels=["Konzept"])
    assert title == "Persistenz"
    assert content == "Neo4j\n\nDetails"


def test_extract_title_and_content_text_eingabe_title_type():
    from neo4j_mcp_server import server

    node_data = {"content": "Kapitel 1", "type": "TITLE"}
    title, content = server._extract_title_and_content(node_data, labels=["TextEingabe"])
    assert title == "Kapitel 1"
    assert content == ""

