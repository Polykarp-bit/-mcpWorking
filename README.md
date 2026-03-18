# Neo4j MCP Server für arc42 Dokumentation

Dieser MCP-Server ermöglicht es, Dokumentation aus einer Neo4j-Datenbank zu durchsuchen, zu lesen und zu bearbeiten, mit Fokus auf arc42 Architektur-Dokumentation.

## Installation

1. **Abhängigkeiten installieren:**
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

   Oder manuell mit pip/uv:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e .
   ```

## Docker Container

Du kannst den Server auch via Docker betreiben:
```bash
docker build -t neo4j-mcp-server .
docker run --rm -it \
  -e NEO4J_URI="bolt://host.docker.internal:7687" \
  -e NEO4J_USER="neo4j" \
  -e NEO4J_PASSWORD="dein_echtes_neo4j_passwort" \
  neo4j-mcp-server
```

## Konfiguration

Setze die folgenden Umgebungsvariablen:

```bash
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="dein_echtes_neo4j_passwort"
```

## Cursor MCP Konfiguration

**Siehe `INSTALLATION.md` für detaillierte Anweisungen!**

Kurzfassung:
1. Öffne Cursor Settings → MCP Servers
2. Füge die Konfiguration aus `cursor-mcp-config.json` hinzu
3. **WICHTIG**: Ersetze das Passwort durch dein tatsächliches Neo4j-Passwort (`NEO4J_PASSWORD`).
4. Starte Cursor neu

## Verfügbare Tools

- **search_docs(query)**: Durchsucht alle Dokumentations-Knoten nach dem angegebenen Query
- **list_titles()**: Listet alle Titel aus der Dokumentation auf
- **add_documentation(title, content, doc_type)**: Fügt einen neuen Dokumentations-Knoten hinzu
- **Viele weitere tools**: Der Server ermöglicht auch das Hinzufügen von Bausteinsichten, Laufzeitsichten und Anforderungen etc.

## Manueller Start

Um den Server lokal für den Inspector zu starten:
```bash
cd /Users/tobiasniederpruem/dev/projects/mcpWorking
source .venv/bin/activate
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="dein_echtes_neo4j_passwort"

# Server starten
python -m neo4j_mcp_server
```

## MCP Inspector (Interaktives Testen)

Der MCP Inspector ist ein browser-basiertes Tool, um den Server interaktiv zu testen.

```bash
npx @modelcontextprotocol/inspector \
  /Users/tobiasniederpruem/dev/projects/mcpWorking/.venv/bin/python \
  -m neo4j_mcp_server
```

## Claude Desktop App Integration

Füge folgende Konfiguration zu deiner `claude_desktop_config.json` hinzu (Mac: `~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "neo4j-mcp-server": {
      "command": "/Users/tobiasniederpruem/dev/projects/mcpWorking/.venv/bin/python",
      "args": [
        "-m", "neo4j_mcp_server"
      ],
      "env": {
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "dein_echtes_neo4j_passwort"
      }
    }
  }
}
```
Überprüfe nach dem Neustart von Claude, ob das Stecker-Symbol aktiv ist.
