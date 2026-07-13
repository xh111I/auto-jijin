#!/usr/bin/env python3
"""Parse the westock batch kline result and save per-index _raw_<CODE>.json files."""
import json, os, sys

DATA = os.path.dirname(os.path.abspath(__file__))
RESULT_FILE = sys.argv[1] if len(sys.argv) > 1 else None

if not RESULT_FILE:
    # Read from stdin instead
    raw = sys.stdin.read()
else:
    with open(RESULT_FILE, "r", encoding="utf-8") as f:
        raw = f.read()
start = raw.index('{"ok"')
data = json.loads(raw[start:])

if not data.get("ok"):
    print("API returned error:", data)
    sys.exit(1)

records = data["data"]["data"]
for rec in records:
    symbol = rec["symbol"]
    nodes = rec["data"]["nodes"]
    # Deduplicate by date, sort ascending
    seen = set()
    clean = []
    for n in nodes:
        d = n.get("date","")
        if d and d not in seen:
            seen.add(d)
            clean.append(n)
    clean.sort(key=lambda n: n.get("date",""))
    # Truncate to latest 250
    if len(clean) > 250:
        clean = clean[-250:]
    
    out = {"code": symbol, "nodes": clean}
    out_path = os.path.join(DATA, f"_raw_{symbol}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"Saved {symbol}: {len(clean)} rows -> _raw_{symbol}.json")

print("Done. Files saved to", DATA)
