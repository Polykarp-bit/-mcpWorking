from __future__ import annotations

import argparse
import sys

from neo4j_mcp_server.server import main

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="neo4j_mcp_server")
    parser.add_argument(
        "--transport",
        default="stdio",
        choices=["stdio"],
        help="MCP transport to use (default: stdio).",
    )
    args = parser.parse_args(sys.argv[1:])
    main(transport=args.transport)
