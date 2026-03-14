# Installation für Cursor

## Schritt 1: Abhängigkeiten installieren

Die Abhängigkeiten sind bereits installiert! Falls du sie neu installieren musst:

```bash
cd /Users/tobiasniederpruem/neo4j-mcp-server
./setup.sh
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
  "command": "/Users/tobiasniederpruem/neo4j-mcp-server/.venv/bin/python",
  "args": [
    "/Users/tobiasniederpruem/neo4j-mcp-server/server.py"
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

2. Füge den Inhalt aus `cursor-mcp-config.json` zu deiner bestehenden Konfiguration hinzu

3. **WICHTIG**: Ersetze `DEIN_NEO4J_PASSWORT` durch dein tatsächliches Neo4j-Passwort – sonst verbindet der MCP-Server nicht mit der Datenbank.

## Schritt 3: Cursor neu starten

Nach dem Hinzufügen der Konfiguration:
1. **Cursor komplett schließen** (nicht nur das Fenster)
2. Cursor neu starten
3. Der MCP-Server sollte automatisch verbunden werden

## Schritt 4: Verwendung

Nach dem Neustart kannst du die folgenden Tools verwenden:

- **`search_docs(query)`**: Durchsucht alle Dokumentations-Knoten
- **`list_titles()`**: Listet alle Titel auf

## Troubleshooting

### Server startet nicht

1. Prüfe, ob Neo4j läuft:
   ```bash
   # Neo4j sollte auf bolt://localhost:7687 erreichbar sein
   ```

2. Prüfe die Logs in Cursor:
   - Öffne die Developer Tools (⌘⇧P → "Developer: Toggle Developer Tools")
   - Schaue nach Fehlern im Console-Tab

3. Teste den Server manuell:
   ```bash
   cd /Users/tobiasniederpruem/neo4j-mcp-server
   source .venv/bin/activate
   export NEO4J_URI="bolt://localhost:7687"
   export NEO4J_USER="neo4j"
   export NEO4J_PASSWORD="tobiasniederpruem"
   python server.py
   ```

### Passwort ändern

Wenn du das Neo4j-Passwort ändern musst, aktualisiere es in:
- Der Cursor MCP-Konfiguration (`NEO4J_PASSWORD`)
- Oder in den Umgebungsvariablen, wenn du den Server manuell startest
