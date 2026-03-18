import re

def reorder_parent_name():
    path = "src/neo4j_mcp_server/server.py"
    with open(path, "r") as f:
        text = f.read()

    def repl(m):
        prefix = m.group(1)
        args = m.group(2).strip()
        if args.endswith(','):
            args = args[:-1].strip()
        
        # Build new signature
        if args:
            new_sig = f"{prefix}parent_name: str, {args}{m.group(3)}"
        else:
            new_sig = f"{prefix}parent_name: str{m.group(3)}"
            
        return new_sig

    # This regex looks for function definitions that end with -> str:
    # and have parent_name: str = "..." as the LAST argument.
    pattern = re.compile(
        r'(def\s+[a-zA-Z0-9_]+\()([\s\S]*?)(?:,\s*)?parent_name:\s*str\s*=\s*"[^"]*"\s*(\)\s*->\s*str:)',
        re.MULTILINE
    )

    new_text, count = pattern.subn(repl, text)
    
    with open(path, "w") as f:
        f.write(new_text)
        
    print(f"Successfully updated {count} tool signatures in {path}.")

if __name__ == "__main__":
    reorder_parent_name()
