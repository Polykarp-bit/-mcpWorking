# Neo4j MCP Server für arc42 Dokumentation

Dieser MCP-Server ermöglicht es, Dokumentation aus einer Neo4j-Datenbank zu durchsuchen, zu lesen und zu bearbeiten, mit Fokus auf arc42 Architektur-Dokumentation.

## Installation

**Wichtig (macOS / Homebrew-Python):**  
`pip install` direkt ins System-Python wird oft durch **PEP 668** blockiert.  
Deshalb ist der **Standard** wieder eine **Projekt-`.venv`** — zuverlässig für **Cursor** und **Claude Desktop**.

```bash
cd /pfad/zu/mcpWorking
chmod +x setup.sh
./setup.sh
```

Das legt `.venv` an und führt `pip install -e .` darin aus.

**Optional – nur System-Python (kann unter Homebrew fehlschlagen):**

```bash
./setup.sh --system
```

**Ohne setup.sh manuell:**

```bash
cd /pfad/zu/mcpWorking
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Umgebungsvariablen (Neo4j + Arc42-Projekt)

| Variable | Bedeutung |
|----------|-----------|
| `NEO4J_URI` | z. B. `bolt://localhost:7687` |
| `NEO4J_USER` | z. B. `neo4j` |
| `NEO4J_PASSWORD` | Neo4j-Passwort |
| `ARC42_PARENT_NAME` | **Name** des `Arc42`-Knotens in Neo4j (für `read_arc42_chapter`, Ressourcen `arc42://chapter/...`) |

```bash
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="dein_passwort"
export ARC42_PARENT_NAME="MCP Server arc42doc"
```

## Cursor & Claude Desktop (MCP)

1. `./setup.sh` ausführen (`.venv` anlegen).
2. Vorlage kopieren:
   - **Claude:** `claude_desktop_config.example.json` →  
     `~/Library/Application Support/Claude/claude_desktop_config.json` (einbinden/mergen)
   - **Cursor:** `cursor-mcp-config.example.json` in die MCP-Einstellungen übernehmen
3. **`command`** auf den **absoluten** Pfad setzen:  
   `/…/mcpWorking/.venv/bin/python`
4. **`NEO4J_*`** und **`ARC42_PARENT_NAME`** eintragen.
5. **Cursor / Claude vollständig neu starten.**

Alternative Startmethode (gleiches Repo, nutzt `.venv` falls vorhanden):

```json
"command": "/ABSOLUTER/PFAD/ZU/mcpWorking/scripts/run_arc42_mcp.sh",
"args": []
```

(`run_arc42_mcp.sh` ist ausführbar; setzt bei Bedarf `PYTHONPATH=src`.)

Details: **`INSTALLATION.md`**

## Verfügbare Tools

- **search_docs**, **list_titles**, **read_arc42_chapter**, viele CRUD-Tools pro arc42-Kapitel, **list_projects**, **rename_project**, …

## Manueller Start

```bash
cd /pfad/zu/mcpWorking
source .venv/bin/activate
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="dein_passwort"
export ARC42_PARENT_NAME="dein_projektname"

python -m neo4j_mcp_server
```

## MCP Inspector

```bash
npx @modelcontextprotocol/inspector \
  "$(pwd)/.venv/bin/python" \
  -m neo4j_mcp_server
```

(Vorher `NEO4J_*` und ggf. `ARC42_PARENT_NAME` in der Shell setzen.)
