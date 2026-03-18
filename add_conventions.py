import os
import sys
import asyncio

os.environ["NEO4J_URI"] = "bolt://localhost:7687"
os.environ["NEO4J_USER"] = "neo4j"
os.environ["NEO4J_PASSWORD"] = "stones-principal-roars"
sys.path.append("src")

from neo4j_mcp_server.server import add_convention

async def main():
    conventions = [
        {
            "convention": "Sprache",
            "explanation": "Code, Variablen und technische Kommentare werden in Englisch verfasst. Die Projektdokumentation (arc42) erfolgt auf Deutsch, um den Anforderungen der Nutzer/Stakeholder zu entsprechen."
        },
        {
            "convention": "Architektur und Frameworks",
            "explanation": "Für die Implementierung neuer Features und Tools ist zwingend das offizielle Model Context Protocol (MCP) Python SDK zu verwenden (via FastMCP). Direkte API-Schnittstellen ohne MCP-Kapselung sind zu vermeiden."
        },
        {
            "convention": "Coding Guidelines (Python)",
            "explanation": "Der Python-Code folgt dem PEP-8 Standard. Type Hints (typing) sind für alle Parameter und Rückgabewerte von Methoden und MCP-Tools verpflichtend, um Typensicherheit für das LLM zu gewährleisten."
        },
        {
            "convention": "Fehlerbehandlung",
            "explanation": "Exceptions in MCP-Tools dürfen den Server nicht zum Absturz bringen. Jeder Fehler muss abgefangen und mittels der internen `_format_error`-Funktion als gut lesbares Markdown an den Client zurückgegeben werden."
        }
    ]

    for c in conventions:
        print(f"Füge Konvention hinzu: {c['convention']}")
        try:
            if asyncio.iscoroutinefunction(add_convention):
                res = await add_convention(c["convention"], c["explanation"])
            else:
                res = add_convention(c["convention"], c["explanation"])
            print(" ->", res.strip().split("\n")[0]) # Print "## Success"
        except Exception as e:
            print(" -> Error:", e)

if __name__ == "__main__":
    asyncio.run(main())
