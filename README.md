# Neo4j MCP Server für arc42 Dokumentation

Dieser MCP-Server ermöglicht es, Dokumentation aus einer Neo4j-Datenbank zu durchsuchen und zu lesen.

## Installation

1. **Abhängigkeiten installieren:**
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

   Oder manuell:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
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
3. **WICHTIG**: Ersetze das Passwort durch dein tatsächliches Neo4j-Passwort (`NEO4J_PASSWORD`), sonst verbindet der Server nicht.
4. Starte Cursor neu

Die Konfigurationsdatei befindet sich normalerweise unter:
- `~/Library/Application Support/Cursor/User/globalStorage/mcp.json` oder
- In den Cursor-Einstellungen unter MCP Servers

## Verfügbare Tools

- **search_docs(query)**: Durchsucht alle Dokumentations-Knoten nach dem angegebenen Query
- **list_titles()**: Listet alle Titel aus der Dokumentation auf
- **add_documentation(title, content, doc_type)**: Fügt einen neuen Dokumentations-Knoten hinzu (Standard doc_type: "Documentation")

## Verfügbare Resources

- **docs://{title}**: Ruft den Inhalt eines Dokumentations-Knotens direkt über den Titel ab (z.B. `docs://Installation`)

## Unterstützte Knoten-Typen

Der Server unterstützt folgende Knoten-Typen aus dem arc42doc-Projekt:

- **TextEingabe**: `content` (kann TITLE sein)
- **Glossar**: `begriff` (Titel), `beschreibung` (Content)
- **Konzept**: `name` (Titel), `text` (Content)
- **SecurityAdvisory**: `title`, `content`
- **Risiko**: `anforderung` (Titel)
- **Stakeholder**: `roleOrName` (Titel)
- **Konvention**: `konvention` (Titel), `erlaeuterung` (Content)
- **TechnischeRandbedingung**: `randbedingung` (Titel), `hintergrund` (Content)
- **Aufgabenstellung**: `aufgabe` (Content)
- **LoesungsStrategie**: `strategy` (Content)
- Und weitere...

## Manueller Start

```bash
cd /Users/tobiasniederpruem/neo4j-mcp-server
source .venv/bin/activate
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="dein_echtes_neo4j_passwort"

## Nutzung

### Option 1: MCP Inspector (Empfohlen zum Testen)

Der MCP Inspector ist ein browser-basiertes Tool, um den Server interaktiv zu testen.

```bash
npx @modelcontextprotocol/inspector \
  /Users/tobiasniederpruem/neo4j-mcp-server/.venv/bin/python \
  /Users/tobiasniederpruem/neo4j-mcp-server/server.py
```

### Option 2: Claude Desktop App

Füge folgende Konfiguration zu deiner `claude_desktop_config.json` hinzu (Mac: `~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "neo4j-mcp-server": {
      "command": "/Users/tobiasniederpruem/neo4j-mcp-server/.venv/bin/python",
      "args": [
        "/Users/tobiasniederpruem/neo4j-mcp-server/server.py"
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
Dann starte die Claude App neu. Ein Stecker-Symbol sollte erscheinen.
