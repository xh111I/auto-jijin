#!/usr/bin/env python3
"""Save all fetched raw data to _raw_<CODE>.json files.
Each _raw file contains {"code":"...", "nodes":[...]}.
import json, os, sys

DATA = os.path.dirname(os.path.abspath(__file__))

def save_raw(code, nodes):
    path = os.path.join(DATA, "_raw_%s.json" % code)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"code": code, "nodes": nodes}, f, ensure_ascii=False, indent=1)
    print(f"Saved {code} ({len(nodes)} rows)")

if __name__ == "__main__":
    code = sys.argv[1]
    json_str = sys.stdin.read()
    nodes = json.loads(json_str)
    save_raw(code, nodes)
