#!/bin/bash
# Standard: Projekt-.venv (empfohlen — funktioniert mit Homebrew/Python PEP 668).
# Optional: ./setup.sh --system  versucht System-pip (scheitert oft unter macOS/Homebrew).

set -euo pipefail

echo "Neo4j MCP Server – Installation"
echo ""

if ! command -v python3 &> /dev/null; then
    echo "Fehler: python3 ist nicht installiert oder nicht im PATH."
    exit 1
fi

if [ "${1:-}" = "--system" ]; then
    echo "Modus: System-Python (ohne venv): $(command -v python3)"
    echo "Hinweis: Unter macOS/Homebrew schlägt das oft fehl (PEP 668). Bei Fehler: ./setup.sh ohne --system"
    python3 -m pip install --upgrade pip
    python3 -m pip install -e .
    echo ""
    echo "Fertig. MCP command: $(command -v python3)"
else
    echo "Modus: virtuelle Umgebung .venv (empfohlen für Cursor / Claude Desktop)"
    if [ ! -d ".venv" ]; then
        echo "Erstelle .venv …"
        python3 -m venv .venv
    fi
    # shellcheck source=/dev/null
    source .venv/bin/activate
    python -m pip install --upgrade pip
    python -m pip install -e .
    echo ""
    echo "Fertig."
    echo "  Server:  source .venv/bin/activate && export NEO4J_* && python -m neo4j_mcp_server"
    echo "  MCP command in Cursor/Claude: $(pwd)/.venv/bin/python"
    echo "  Oder Startskript: $(pwd)/scripts/run_arc42_mcp.sh"
fi
