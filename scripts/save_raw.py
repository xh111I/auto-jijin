#!/usr/bin/env python3
"""Process and save MCP kline data to raw files."""
import json, sys, os

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')

if __name__ == "__main__":
    raw = json.loads(sys.stdin.readline())
    code = raw.get("code", "")
    payload = raw.get("data", {}).get("nodes", [])
    
    # Deduplicate by date, sort ascending, keep last 250
    seen = set()
    clean = []
    for n in payload:
        d = n.get("date","")
        if d and d not in seen:
            seen.add(d)
            clean.append(n)
    clean.sort(key=lambda n: n.get("date",""))
    if len(clean) > 250:
        clean = clean[-250:]
    
    path = os.path.join(DATA, f"_raw_{code}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"code": code, "nodes": clean}, f, ensure_ascii=False, indent=1)
    
    print(f"{code}: {len(clean)} rows -> {path}")
