import subprocess
import shutil
import re
import os
import re

NEW_TOOLS = """

# --- Neu hinzugefuegte Tools (Dynamische Projekte) ---

@mcp.tool()
def list_projects() -> str:
    \"\"\"List all available Arc42 projects in the database.
    Use this to see which projects exist before calling other tools.
    \"\"\"
    cypher = "MATCH (d:Arc42) RETURN id(d) as id, d.name as name"
    try:
        res = _run_write(cypher)
        if not res:
            return "## Projects\\n\\nKeine Projekte gefunden.\\n"
        output = "## Available Projects\\n\\n"
        for r in res:
            output += f"- **{r.get('name', 'Unnamed')}** (ID: {r.get('id')})\\n"
        return output
    except Exception as e:
        return _format_error("list_projects", e)

@mcp.tool()
def rename_project(old_name: str, new_name: str) -> str:
    \"\"\"Rename a root project (Arc42 node) in the database.\"\"\"
    try:
        old_name = _validate_required(old_name, "old_name")
        new_name = _validate_required(new_name, "new_name")
    except ValueError as e:
        return _format_error("rename_project", e)
    
    cypher = (
        "MATCH (n:Arc42 {name: $old_name}) "
        "SET n.name = $new_name "
        "RETURN n"
    )
    try:
        records = _run_write(cypher, old_name=old_name, new_name=new_name)
        if not records:
            return f"## Not Found\\n\\nKein Projekt mit Namen '{old_name}' gefunden.\\n"
        return f"## Success\\n\\nProjekt '{old_name}' wurde erfolgreich in '{new_name}' umbenannt.\\n"
    except Exception as e:
        return _format_error("rename_project", e)

@mcp.tool()
def add_project_meeting(parent_name: str, name: str, frequency: int, repetition: str, meeting_type: str) -> str:
    \"\"\"Add a Project Meeting (Meeting) for Chapter 4 - Projektorganisation.\"\"\"
    try:
        name = _validate_required(name, "name")
        repetition = _validate_required(repetition, "repetition")
        meeting_type = _validate_required(meeting_type, "meeting_type")
        if not isinstance(frequency, int):
            try:
                frequency = int(frequency)
            except ValueError:
                return "## Error\\n\\nParameter 'frequency' muss ein Integer sein.\\n"
    except ValueError as e:
        return _format_error("add_project_meeting", e)

    cypher = (
        "MERGE (d:Arc42 {name: $parent_name}) "
        "CREATE (m:Meeting {name: $name, frequency: $frequency, repetition: $repetition, type: $type}) "
        "MERGE (d)-[:hasMeeting]->(m) "
        "RETURN m"
    )
    try:
        _run_write(cypher, name=name, frequency=frequency, repetition=repetition, type=meeting_type, parent_name=parent_name)
        return f"## Success\\n\\nAdded Project Meeting: **{name}**\\nFrequency: {frequency} {repetition}\\nType: {meeting_type}\\n"
    except Exception as e:
        return _format_error("add_project_meeting", e)

@mcp.tool()
def add_swot(parent_name: str, strength: str = "", weakness: str = "", opportunity: str = "", threat: str = "") -> str:
    \"\"\"Add SWOT Analysis entries (Strengths, Weaknesses, Opportunities, Threats) for Chapter 11.\"\"\"
    added = []
    
    def _add_single(entry_type, content):
        if not content.strip():
            return
        cypher = (
            "MERGE (d:Arc42 {name: $parent_name}) "
            "CREATE (n:TextEingabe {type: $type, content: $content}) "
            "MERGE (d)-[:hasTextEingabe]->(n) "
            "RETURN n"
        )
        _run_write(cypher, type=entry_type, content=content.strip(), parent_name=parent_name)
        added.append(f"- **{entry_type}**: {content.strip()}")

    try:
        if strength: _add_single("STRENGTH", strength)
        if weakness: _add_single("WEAKNESS", weakness)
        if opportunity: _add_single("OPPORTUNITY", opportunity)
        if threat: _add_single("THREAT", threat)
        
        if not added:
            return "## Warning\\n\\nKeine SWOT-Eintraege uebergeben.\\n"
            
        return "## Success\\n\\nAdded SWOT Entries:\\n" + "\\n".join(added) + "\\n"
    except Exception as e:
        return _format_error("add_swot", e)

@mcp.tool()
def delete_convention(parent_name: str, convention: str) -> str:
    \"\"\"Delete a Convention (Konvention).\"\"\"
    try:
        convention = _validate_required(convention, "convention")
    except ValueError as e:
        return _format_error("delete_convention", e)

    cypher = (
        "MATCH (d:Arc42 {name: $parent_name})-[r:hatKonvention]->(n:Konvention {konvention: $convention}) "
        "DELETE r, n "
        "RETURN count(n) as c"
    )
    try:
        res = _run_write(cypher, convention=convention, parent_name=parent_name)
        deleted = res[0]["c"] if getattr(res, "records", None) else res[0]["c"]
        if deleted > 0:
            return f"## Success\\n\\nDeleted Convention: **{convention}**\\n"
        return f"## Warning\\n\\nNo matching convention '{convention}' found.\\n"
    except Exception as e:
        return _format_error("delete_convention", e)

@mcp.tool()
def delete_project_meeting(parent_name: str, name: str) -> str:
    \"\"\"Delete a specific Project Meeting for Chapter 4.\"\"\"
    try:
        name = _validate_required(name, "name")
    except ValueError as e:
        return _format_error("delete_project_meeting", e)

    cypher = (
        "MATCH (d:Arc42 {name: $parent_name})-[r:hasMeeting]->(m:Meeting {name: $name}) "
        "DELETE r, m "
        "RETURN count(m) as c"
    )
    try:
        res = _run_write(cypher, name=name, parent_name=parent_name)
        deleted = res[0]["c"] if getattr(res, "records", None) else res[0]["c"]
        if deleted > 0:
            return f"## Success\\n\\nDeleted Project Meeting: **{name}**\\n"
        return f"## Warning\\n\\nNo matching meeting '{name}' found.\\n"
    except Exception as e:
        return _format_error("delete_project_meeting", e)

@mcp.tool()
def delete_swot_entry(parent_name: str, entry_type: str, content: str) -> str:
    \"\"\"Delete a specific SWOT entry for Chapter 11.\"\"\"
    try:
        entry_type = _validate_required(entry_type, "entry_type")
        content = _validate_required(content, "content")
    except ValueError as e:
        return _format_error("delete_swot_entry", e)

    cypher = (
        "MATCH (d:Arc42 {name: $parent_name})-[r:hasTextEingabe]->(n:TextEingabe {type: $type, content: $content}) "
        "DELETE r, n "
        "RETURN count(n) as c"
    )
    try:
        res = _run_write(cypher, type=entry_type, content=content, parent_name=parent_name)
        deleted = res[0]["c"] if getattr(res, "records", None) else res[0]["c"]
        if deleted > 0:
            return f"## Success\\n\\nDeleted SWOT Entry ({entry_type}): **{content[:50]}**\\n"
        return f"## Warning\\n\\nNo matching SWOT entry found.\\n"
    except Exception as e:
        return _format_error("delete_swot_entry", e)
"""

def main():
    print("1. Restoring server.py from git history...")
    subprocess.run(["git", "checkout", "HEAD", "--", "server.py"], check=True)
    
    with open("server.py", "r") as f:
        text = f.read()

    print("2. Replacing default parent_name...")
    # Safe replacement: `, parent_name: str = "Neo4j MCP Server"` to `, *, parent_name: str`
    text = re.sub(r',\s*parent_name\s*:\s*str\s*=\s*"[^"]*"', r', *, parent_name: str', text)
    # Safe replacement: `(parent_name: str = "Neo4j MCP Server")` to `(parent_name: str)`
    text = re.sub(r'\(\s*parent_name\s*:\s*str\s*=\s*"[^"]*"', r'(parent_name: str', text)

    print("3. Appending new dynamic project tools...")
    text += NEW_TOOLS

    with open("src/neo4j_mcp_server/server.py", "w") as f:
        f.write(text)

    # Optional: wir räumen das temporär per git wiederhergestellte server.py in Root weg,
    # da es ja in src/neo4j_mcp_server/server.py gehört.
    if os.path.exists("server.py"):
        os.remove("server.py")

    print("Erfolgreich abgeschlossen!")

if __name__ == "__main__":
    main()
