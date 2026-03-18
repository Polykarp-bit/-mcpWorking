import os
import sys

os.environ["NEO4J_URI"] = "bolt://localhost:7687"
os.environ["NEO4J_USER"] = "neo4j"
os.environ["NEO4J_PASSWORD"] = os.environ.get("NEO4J_PASSWORD", "yourPassword")
sys.path.append("src")
from neo4j_mcp_server.server import _run_write

res = _run_write("MATCH (d:Arc42) RETURN d.name as n, id(d) as id, d.title as title")
print("Arc42 Nodes:")
for r in res:
    name = r["n"]
    node_id = r["id"]
    title = r["title"]
    print(f" - name: {name}, title: {title} (ID: {node_id})")

    # Get SWOT for this node
    swot_res = _run_write(
        "MATCH (d:Arc42)-[:hasTextEingabe]->(t:TextEingabe) "
        "WHERE id(d) = $id "
        "RETURN t.type as type, t.content as content",
        id=node_id,
    )
    for s in swot_res:
        t = s["type"]
        c = s["content"]
        print(f"   -> {t}: {c}")
