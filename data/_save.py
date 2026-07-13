#!/usr/bin/env python3
"""Save MCP raw data to _raw_ files."""
import json, os, sys

BASE = os.path.dirname(os.path.abspath(__file__))

def save(code, nodes):
    path = os.path.join(BASE, "_raw_%s.json" % code)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"code": code, "nodes": nodes}, f, ensure_ascii=False, indent=1)
    print("Saved %s (%d rows)" % (code, len(nodes)))

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "save":
        code = sys.argv[2]
        data = json.loads(sys.stdin.read())
        save(code, data)
    elif cmd == "batch":
        # Read from a JSON file mapping code->nodes
        with open(sys.argv[2], "r", encoding="utf-8") as f:
            items = json.load(f)
        for item in items:
            save(item["code"], item["nodes"])
    else:
        print("Usage: _save.py save <code>  OR  _save.py batch <file>")
