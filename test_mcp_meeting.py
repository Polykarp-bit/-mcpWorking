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
            
            print("Rufe das Tool 'add_project_meeting' über MCP auf...")
            result = await session.call_tool(
                "add_project_meeting",
                arguments={
                    "name": "Daily Sync MCP Team",
                    "frequency": 1,
                    "repetition": "Täglich",
                    "meeting_type": "Statusmeeting",
                    "parent_name": "MCP arc42doc"
                }
            )
            print("\n----- ERGEBNIS VOM MCP SERVER -----")
            for content in result.content:
                if content.type == "text":
                    print(content.text)

if __name__ == "__main__":
    asyncio.run(run())
