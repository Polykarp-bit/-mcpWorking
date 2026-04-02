import runpy
import sys

import pytest


def test_module_help_exits_zero_and_does_not_start_server(monkeypatch, capsys):
    # Ensure a fresh import of the package entrypoint
    monkeypatch.delitem(sys.modules, "neo4j_mcp_server.__main__", raising=False)

    # Running with --help should exit before calling main()
    monkeypatch.setattr(sys, "argv", ["neo4j_mcp_server", "--help"])
    with pytest.raises(SystemExit) as exc:
        runpy.run_module("neo4j_mcp_server", run_name="__main__")
    assert exc.value.code == 0

    out = capsys.readouterr().out
    assert "usage:" in out
    assert "neo4j_mcp_server" in out


def test_module_parses_transport_and_calls_main(monkeypatch):
    import neo4j_mcp_server.server as server

    # Ensure a fresh import of the package entrypoint so it binds our patched main()
    monkeypatch.delitem(sys.modules, "neo4j_mcp_server.__main__", raising=False)

    called = {}

    def fake_main(*, transport="stdio"):
        called["transport"] = transport

    monkeypatch.setattr(server, "main", fake_main, raising=True)
    monkeypatch.setattr(sys, "argv", ["neo4j_mcp_server", "--transport", "stdio"])

    runpy.run_module("neo4j_mcp_server", run_name="__main__")
    assert called["transport"] == "stdio"

