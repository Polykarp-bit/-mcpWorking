#!/usr/bin/env python3
"""
Bausteinsicht (rote PNG) in Neo4j schreiben.
Verwendet dieselbe Logik wie der MCP-Server add_building_block_view.
Voraussetzung: Neo4j läuft, NEO4J_URI/USER/PASSWORD gesetzt (z. B. .env oder export).
"""
import os
import sys

# Projektroot für Imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from neo4j import GraphDatabase

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "yourPassword")
PARENT_NAME = os.getenv("ARC42_PARENT_NAME", "Neo4j MCP Server")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
PNG_PATH = os.path.join(PROJECT_ROOT, "diagrams", "bausteinsicht.png")
DESCRIPTION = (
    "Bausteinsicht: Drei-Schichten-Architektur des arc42 MCP Servers – "
    "Interface Layer, Application Core und Infrastructure Layer."
)


def main():
    if not os.path.exists(PNG_PATH):
        print(f"Fehler: PNG nicht gefunden: {PNG_PATH}")
        print("Bitte zuerst: cd diagrams && python3 generate_diagrams.py")
        sys.exit(1)

    with open(PNG_PATH, "rb") as f:
        image_bytes = f.read()
    image_name = os.path.basename(PNG_PATH)
    mime_type = "image/png"

    driver = GraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USER, NEO4J_PASSWORD),
    )

    cypher = (
        "MERGE (d:Arc42 {name: $parent_name}) "
        "WITH d "
        "OPTIONAL MATCH (d)-[:bausteinsicht]->(old:Image:Baustein) "
        "DETACH DELETE old "
        "WITH d "
        "CREATE (n:Image:Baustein { "
        "   description: $description, "
        "   bildName: $image_name, "
        "   bildMimeType: $mime_type, "
        "   bildPath: $image_bytes, "
        "   uxfName: '', "
        "   uxfMimeType: '', "
        "   uxfPath: $empty_bytes "
        "}) "
        "MERGE (d)-[:bausteinsicht]->(n) "
        "RETURN n"
    )

    try:
        with driver.session() as session:
            session.run(
                cypher,
                parent_name=PARENT_NAME,
                description=DESCRIPTION,
                image_name=image_name,
                mime_type=mime_type,
                image_bytes=image_bytes,
                empty_bytes=b"",
            )
        print(f"OK: Bausteinsicht in Neo4j aktualisiert ({image_name}, {len(image_bytes):,} Bytes)")
        print("In arc42doc die Seite neu laden, dann erscheint die rote Version.")
    except Exception as e:
        print(f"Fehler: {e}")
        sys.exit(1)
    finally:
        driver.close()


if __name__ == "__main__":
    main()
