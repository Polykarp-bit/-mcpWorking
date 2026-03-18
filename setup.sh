#!/bin/bash

# Setup script for Neo4j MCP Server

echo "Setting up Neo4j MCP Server..."

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Install dependencies via setup
echo "Installing dependencies..."
pip install --upgrade pip
pip install -e .

echo ""
echo "Setup complete!"
echo ""
echo "To start the server manually, run:"
echo "  source .venv/bin/activate"
echo "  export NEO4J_URI='bolt://localhost:7687'"
echo "  export NEO4J_USER='neo4j'"
echo "  export NEO4J_PASSWORD='yourPassword'"
echo "  python -m neo4j_mcp_server"
echo ""
