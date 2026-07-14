"""Check raw OHLC structure for cs sectors."""
import json

with open("data/market_raw_ohlc_2026-07-14.json", "r", encoding="utf-8") as f:
    raw = json.load(f)

print("Type of sectors:", type(raw.get("sectors")))
sectors = raw.get("sectors")
if isinstance(sectors, list):
    print(f"Sectors is list[{len(sectors)}]")
    for s in sectors:
        code = s.get("code", "")
        name = s.get("name", "")
        ohlc = s.get("ohlc", [])
        if ohlc and len(ohlc) > 0:
            last = ohlc[-1]
            print(f"  {name:20s} {code:15s} ohlc[{len(ohlc)}] last={last}")
elif isinstance(sectors, dict):
    print(f"Sectors is dict, keys: {list(sectors.keys())[:5]}")
    for name, sd in sectors.items():
        code = sd.get("code", "")
        ohlc = sd.get("ohlc", [])
        if ohlc:
            last = ohlc[-1]
            print(f"  {name:20s} {code:15s} ohlc[{len(ohlc)}] last={last}")
