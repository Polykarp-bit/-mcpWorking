"""
Einmalig ausführen um alle arc42-Diagramme via Kroki API zu generieren.
Ausführen mit: python3 generate_diagrams.py
"""
import base64
import os
import urllib.error
import urllib.request
import zlib

def mermaid_to_png(code: str, output_path: str):
    compressed = zlib.compress(code.encode("utf-8"), 9)
    encoded = base64.urlsafe_b64encode(compressed).decode("ascii")
    url = f"https://kroki.io/mermaid/png/{encoded}"
    req = urllib.request.Request(url, headers={"User-Agent": "arc42doc-mcp/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    with open(output_path, "wb") as f:
        f.write(data)
    print(f"✅  {os.path.basename(output_path)} ({len(data):,} bytes)")

OUT = os.path.dirname(os.path.abspath(__file__))

# ── Kapitel 5: Bausteinsicht ────────────────────────────────────────────────
bausteinsicht = """graph TD
    subgraph IL["Interface Layer (Schnittstellenschicht)"]
        MCP["MCP Server Instance\\n(FastMCP, Stdio/SSE)"]
        REG["Tool & Resource Registry\\n(Router, JSON-RPC Validator)"]
    end
    subgraph AC["Application Core (Anwendungskern)"]
        DS["Documentation Service\\n(Controller / Orchestrator)"]
        CF["Content Formatter\\n(Graph → Markdown / JSON)"]
        SV["Schema Validator\\n(Pydantic, Typensicherheit)"]
    end
    subgraph INF["Infrastructure Layer (Infrastrukturschicht)"]
        NEO["Neo4j Database Client\\n(Cypher Queries, Bolt)"]
        GIT["Git Repository Client\\n(GitHub / GitLab API)"]
    end
    MCP --> REG
    REG --> DS
    DS --> CF
    DS --> SV
    DS --> NEO
    DS --> GIT
    style IL fill:#dbeafe,stroke:#3b82f6
    style AC fill:#dcfce7,stroke:#22c55e
    style INF fill:#fee2e2,stroke:#dc2626"""

# ── Kapitel 6: Laufzeitsicht ────────────────────────────────────────────────
laufzeitsicht = """sequenceDiagram
    actor Dev as Entwickler
    participant LLM as LLM (Claude)
    participant Host as MCP Host
    participant MCP as arc42 MCP Server
    participant Neo4j as Neo4j DB
    participant Git as Git MCP Server

    Dev->>LLM: Was hängt von Komponente X ab?
    LLM->>Host: Tool-Anforderung erkannt
    Host->>+MCP: call_tool(get_dependencies)
    MCP->>+Neo4j: Cypher Query (Bolt)
    Neo4j-->>-MCP: Graph Result
    MCP-->>-Host: JSON Response
    Host->>LLM: Kontext bereitgestellt

    Note over Host,Git: Phase 2 – Quellcode (Out of Scope)
    Host->>+Git: call_tool(get_file)
    Git-->>-Host: Source Code

    LLM->>Dev: Präzise Antwort (Ground Truth)"""

# ── Kapitel 7: Verteilungssicht ─────────────────────────────────────────────
verteilungssicht = """graph LR
    subgraph CW["Client Workstation"]
        CD["Claude Desktop\\n(MCP Host)"]
    end

    subgraph SR["Server Runtime"]
        PY["Python MCP Server\\n(Stdio Transport)"]
    end

    subgraph DB["Datenhaltung (On-Premise)"]
        NEO[("Neo4j\\nBolt :7687")]
        ARC["arc42doc\\n(Java / Vaadin)"]
    end

    subgraph EXT["Externe Cloud-Dienste"]
        LLM["LLM Provider\\n(Anthropic / OpenAI)"]
        GIT["Git Provider\\n(GitHub / GitLab)"]
    end

    CD -- "Stdio / MCP\\n(JSON-RPC 2.0)" --> PY
    PY -- "Bolt TCP 7687" --> NEO
    ARC -- "Bolt TCP 7687" --> NEO
    CD -- "HTTPS" --> LLM
    PY -- "HTTPS REST" --> GIT

    style CW fill:#dbeafe,stroke:#3b82f6
    style SR fill:#dcfce7,stroke:#22c55e
    style DB fill:#fef9c3,stroke:#eab308
    style EXT fill:#fce7f3,stroke:#ec4899"""

print("Generiere Diagramme via Kroki API...")
mermaid_to_png(bausteinsicht,   os.path.join(OUT, "bausteinsicht.png"))
mermaid_to_png(laufzeitsicht,   os.path.join(OUT, "laufzeitsicht.png"))
mermaid_to_png(verteilungssicht, os.path.join(OUT, "verteilungssicht.png"))
print("\nFertig! Alle 3 Diagramme gespeichert.")
