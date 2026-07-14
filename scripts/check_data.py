"""Quick inspection of market.json sectors/holdings and cs OHLC."""
import json

with open("data/market_2026-07-14.json", "r", encoding="utf-8") as f:
    d = json.load(f)

sec = d.get("sectors", {})
print("=== SECTORS ===")
for k, v in sec.items():
    if isinstance(v, list):
        print(f"  {k}: list[{len(v)}] first3={v[:3]}")
    elif isinstance(v, str):
        print(f"  {k}: str len={len(v)} val={v[:200]}")
    else:
        print(f"  {k}: {v}")

print()
print("=== HOLDINGS ===")
for hi in d.get("holdings", []):
    print(f"  {hi['name']:10s} sup={str(hi.get('support',''))[:40]} pres={str(hi.get('pressure',''))[:40]} risk={hi.get('risk_dist_pct','')}")

with open("data/market_raw_ohlc_2026-07-14.json", "r", encoding="utf-8") as f:
    raw = json.load(f)

print()
print("=== CS SECTOR OHLC last 3 ===")
for sn, sd in raw.get("sectors", {}).items():
    if sd.get("code", "").startswith("cs"):
        for row in sd.get("ohlc", [])[-3:]:
            print(f"  {sn:20s} {row}")
