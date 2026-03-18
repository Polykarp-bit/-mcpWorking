import asyncio
import os
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

async def run():
    env = os.environ.copy()
    env["NEO4J_URI"] = "bolt://localhost:7687"
    env["NEO4J_USER"] = "neo4j"
    env["NEO4J_PASSWORD"] = "stones-principal-roars"
    env["PYTHONPATH"] = os.path.abspath("src")
    
    python_exec = os.path.abspath(".venv/bin/python")
    
    params = StdioServerParameters(
        command=python_exec,
        args=["-m", "neo4j_mcp_server"],
        env=env
    )
    
    print("Starte stdio MCP Client...")
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("Erfolgreich mit dem MCP Server verbunden!")
            
            print("Rufe das Tool 'add_swot' über MCP auf...")
            result = await session.call_tool(
                "add_swot",
                arguments={
                    "strength": "Modularer Aufbau durch MCP; direkte Neo4j-Integration ohne komplexe REST-APIs.",
                    "weakness": "Abhängigkeit vom lokalen Neo4j Service; fehlende Multi-User-Authentifizierung.",
                    "opportunity": "Erweiterung auf andere standardisierte Dokumentations-Frameworks neben arc42. Hohes Automatisierungspotenzial im CI/CD.",
                    "threat": "Kurzfristige Änderungen im noch jungen MCP-Protokollstandard von Anthropic.",
                    "parent_name": "MCP arc42doc"
                }
            )
            print("\n----- ERGEBNIS VOM MCP SERVER -----")
            for content in result.content:
                if content.type == "text":
                    print(content.text)

if __name__ == "__main__":
    asyncio.run(run())
