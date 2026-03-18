import os
os.environ["NEO4J_URI"] = "bolt://localhost:7687"
os.environ["NEO4J_USER"] = "neo4j"
os.environ["NEO4J_PASSWORD"] = "stones-principal-roars"

import sys
sys.path.append('src')

from neo4j_mcp_server.server import add_convention

try:
    res = add_convention("Test Konvention", "Dies ist ein Test")
    print("Response:", repr(res))
except Exception as e:
    print("Error:", repr(e))
