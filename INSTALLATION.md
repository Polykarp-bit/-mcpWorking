# Installation für Cursor

## Schritt 1: Abhängigkeiten installieren

Dieses Projekt nutzt eine moderne Python Package-Struktur.

```bash
cd /Users/tobiasniederpruem/dev/projects/mcpWorking
./setup.sh
```

Alternativ manuell:
```bash
cd /Users/tobiasniederpruem/dev/projects/mcpWorking
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Schritt 2: Cursor MCP-Konfiguration hinzufügen

### Option A: Über Cursor UI (Empfohlen)

1. Öffne Cursor
2. Gehe zu **Settings** (⌘,)
3. Suche nach **"MCP"** oder **"Model Context Protocol"**
4. Klicke auf **"Add MCP Server"** oder **"Configure MCP Servers"**
5. Füge folgende Konfiguration hinzu:

```json
{
  "command": "/Users/tobiasniederpruem/dev/projects/mcpWorking/.venv/bin/python",
  "args": [
    "-m",
    "neo4j_mcp_server"
  ],
  "env": {
    "NEO4J_URI": "bolt://localhost:7687",
    "NEO4J_USER": "neo4j",
    "NEO4J_PASSWORD": "DEIN_NEO4J_PASSWORT"
  }
}
```

### Option B: Über Konfigurationsdatei

1. Öffne die Cursor MCP-Konfigurationsdatei:
   - Normalerweise unter: `~/Library/Application Support/Cursor/User/globalStorage/mcp.json`
   - Oder in den Cursor-Einstellungen unter MCP Servers

2. Füge den Inhalt aus `cursor-mcp-config.json` zu deiner bestehenden Konfiguration hinzu.

3. **WICHTIG**: Ersetze das Passwort durch dein tatsächliches Neo4j-Passwort.

## Schritt 3: Cursor neu starten

Nach dem Hinzufügen der Konfiguration:
1. **Cursor komplett schließen** (nicht nur das Fenster)
2. Cursor neu starten
3. Der MCP-Server sollte automatisch verbunden werden

## Schritt 4: Verwendung

Nach dem Neustart kannst du die Docs abfragen:

- **`search_docs(query)`**: Durchsucht alle Dokumentations-Knoten
- **`list_titles()`**: Listet alle Titel auf
- ...und weitere Methoden zur Dokumentationsgenerierung.

## Troubleshooting

### Server startet nicht

1. Prüfe, ob Neo4j läuft auf `bolt://localhost:7687`.

2. Teste den Server manuell im Terminal:
   ```bash
   cd /Users/tobiasniederpruem/dev/projects/mcpWorking
   source .venv/bin/activate
   export NEO4J_URI="bolt://localhost:7687"
   export NEO4J_USER="neo4j"
   export NEO4J_PASSWORD="yourPassword"
   python -m neo4j_mcp_server
   ```
   Wenn der Server ohne Absturz hochfährt, ist die Konfiguration korrekt.

### Passwort ändern

Wenn du das Neo4j-Passwort ändern musst, aktualisiere es in der Cursor MCP-Konfiguration unter `env`.
