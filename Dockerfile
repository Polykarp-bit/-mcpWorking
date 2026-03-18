FROM python:3.12-slim-bookworm

WORKDIR /app

# Copy project files
COPY pyproject.toml .
COPY README.md .
COPY src/ /app/src/

# Install the package and its dependencies
RUN pip install --no-cache-dir .

# Export server entrypoint
ENTRYPOINT ["python", "-m", "neo4j_mcp_server"]
