#!/usr/bin/env python3
"""Save MCP fetch results to _raw_<CODE>.json files."""
import json, os, sys

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)))

def save_raw(code, nodes):
    path = os.path.join(DATA, "_raw_%s.json" % code)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"code": code, "nodes": nodes}, f, ensure_ascii=False, indent=1)
    print(f"Saved {code} ({len(nodes)} rows) -> {path}")

if __name__ == "__main__":
    code = sys.argv[1]
    nodes_file = sys.argv[2]
    with open(nodes_file, "r", encoding="utf-8") as f:
        nodes = json.load(f)
    save_raw(code, nodes)
