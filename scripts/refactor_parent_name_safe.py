import re

def main():
    path = "src/neo4j_mcp_server/server.py"
    with open(path, "r") as f:
        text = f.read()
        
    # Replace `, parent_name: str = "..."` with `, *, parent_name: str`
    text = re.sub(r',\s*parent_name\s*:\s*str\s*=\s*"[^"]*"', r', *, parent_name: str', text)
    
    # Replace `(parent_name: str = "...")` with `(parent_name: str)`
    text = re.sub(r'\(\s*parent_name\s*:\s*str\s*=\s*"[^"]*"', r'(parent_name: str', text)
    
    with open(path, "w") as f:
        f.write(text)
        
    print("Signatures updated successfully!")

if __name__ == "__main__":
    main()
