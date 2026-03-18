import os
import sys
import asyncio

os.environ["NEO4J_URI"] = "bolt://localhost:7687"
os.environ["NEO4J_USER"] = "neo4j"
os.environ["NEO4J_PASSWORD"] = "stones-principal-roars"
sys.path.append("src")

from neo4j_mcp_server.server import rename_project, _run_write

async def main():
    try:
        # First, query all projects to see what we have
        print("Vorherige Projekte:")
        res_before = _run_write("MATCH (n:Arc42) RETURN n.name as name")
        if getattr(res_before, "records", None):
            for r in res_before.records:
                print(" -", r.get("name"))
        elif isinstance(res_before, list):
            for r in res_before:
                print(" -", r.get("name"))

        # We want to rename "Neo4j MCP Server" -> "MCP Server arc42doc" (the original TODO item)
        # But wait, there is ALREADY an "MCP Server arc42doc" (ID 112).
        # We also need to rename "MCP Server arc42doc" to "MCP arc42doc"
        
        # Let's do: 
        # 1. Rename 'MCP Server arc42doc' -> 'MCP arc42doc'
        if asyncio.iscoroutinefunction(rename_project):
            res1 = await rename_project("MCP Server arc42doc", "MCP arc42doc")
        else:
            res1 = rename_project("MCP Server arc42doc", "MCP arc42doc")
        print("Result 1:", res1)
        
        # 2. Rename 'Neo4j MCP Server' -> 'MCP Server arc42doc'
        if asyncio.iscoroutinefunction(rename_project):
            res2 = await rename_project("Neo4j MCP Server", "MCP Server arc42doc")
        else:
            res2 = rename_project("Neo4j MCP Server", "MCP Server arc42doc")
        print("Result 2:", res2)

    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    asyncio.run(main())
