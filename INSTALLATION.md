# Installation für Cursor & Claude Desktop

## Schritt 1: `.venv` anlegen und Paket installieren

Unter **macOS mit Homebrew-Python** schlägt `pip install -e .` ins System oft fehl (**PEP 668**).  
Deshalb: **`./setup.sh`** ohne Optionen (legt `.venv` an).

```bash
cd /pfad/zu/mcpWorking
./setup.sh
```

Nur wenn du weißt, was du tust: `./setup.sh --system` (System-Python).

## Schritt 2: Umgebungsvariablen in der MCP-Config

In **Cursor** oder **Claude Desktop** müssen mindestens gesetzt sein:

| Variable | Beispiel |
|----------|----------|
| `NEO4J_URI` | `bolt://localhost:7687` |
| `NEO4J_USER` | `neo4j` |
| `NEO4J_PASSWORD` | dein Neo4j-Passwort |
| `ARC42_PARENT_NAME` | exakter Name des Arc42-Projektknotens in Neo4j |

`ARC42_PARENT_NAME` wird u. a. für MCP-Ressourcen `arc42://chapter/…` und konsistente Kapitel-Lesezugriffe benötigt.

## Schritt 3: `command` in der MCP-Konfiguration

**Empfohlen:** absoluter Pfad zum Python in der Projekt-venv:

```
/pfad/zu/mcpWorking/.venv/bin/python
```

**Args:**

```json
["-m", "neo4j_mcp_server"]
```

Vorlagen:

- `cursor-mcp-config.example.json`
- `claude_desktop_config.example.json` (Mac: `~/Library/Application Support/Claude/claude_desktop_config.json`)

**Alternative:** `scripts/run_arc42_mcp.sh` als `command` (keine `args` nötig), gleiches Repo.

## Schritt 4: Client neu starten

Cursor bzw. Claude **vollständig beenden** und neu öffnen.

## Troubleshooting

### `ModuleNotFoundError: neo4j_mcp_server`

- `./setup.sh` ausgeführt?
- In der MCP-Config derselbe Interpreter wie nach Setup: **`.venv/bin/python`**?

### `externally-managed-environment` (pip)

- Nicht `./setup.sh --system` auf Homebrew-Python verwenden; normales **`./setup.sh`** nutzt `.venv`.

### Server startet, Tools scheitern an Neo4j

- Neo4j läuft? URI/Port/User/Passwort korrekt?

### Ressource `arc42://chapter/...` meldet Fehler zu `ARC42_PARENT_NAME`

- Variable in der MCP-`env` setzen (siehe oben).
