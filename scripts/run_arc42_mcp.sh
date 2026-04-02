#!/usr/bin/env bash
# Startet den MCP-Server für Cursor / Claude Desktop.
# Nutzt .venv falls vorhanden (nach ./setup.sh), sonst python3 + PYTHONPATH=src.

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"

if [ -x "$ROOT/.venv/bin/python" ]; then
  exec "$ROOT/.venv/bin/python" -m neo4j_mcp_server "$@"
fi

if ! command -v python3 &> /dev/null; then
  echo "neo4j-mcp-server: python3 nicht gefunden. Bitte ./setup.sh ausführen." >&2
  exit 1
fi
exec python3 -m neo4j_mcp_server "$@"
