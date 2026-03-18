import asyncio
import os
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

async def run():
    env = os.environ.copy()
    env["NEO4J_URI"] = "bolt://localhost:7687"
    env["NEO4J_USER"] = "neo4j"
    env["NEO4J_PASSWORD"] = env.get("NEO4J_PASSWORD", "yourPassword")
    env["PYTHONPATH"] = os.path.abspath("src")
    python_exec = os.path.abspath(".venv/bin/python")
    params = StdioServerParameters(command=python_exec, args=["-m", "neo4j_mcp_server"], env=env)
    
    print("Connecting to MCP Server to test deletion tools...")
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            print("1. Testing delete_convention...")
            res1 = await session.call_tool("delete_convention", arguments={
                "convention": "MCP Client Test",
                "parent_name": "MCP Server arc42doc"
            })
            print(res1.content[0].text)

            print("\n2. Testing delete_project_meeting...")
            res2 = await session.call_tool("delete_project_meeting", arguments={
                "name": "Daily Sync MCP Team",
                "parent_name": "MCP arc42doc"
            })
            print(res2.content[0].text)

            print("\n3. Testing delete_swot_entry...")
            res3 = await session.call_tool("delete_swot_entry", arguments={
                "entry_type": "STRENGTH",
                "content": "Modularer Aufbau durch MCP; direkte Neo4j-Integration ohne komplexe REST-APIs.",
                "parent_name": "MCP arc42doc"
            })
            print(res3.content[0].text)

if __name__ == "__main__":
    asyncio.run(run())
