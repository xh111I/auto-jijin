"""Rebuild intraday JSON with full 1min data for all 9 indices."""
import json, os, re

def parse_min(text):
    lines = [l for l in text.split("\n") if l.strip()]
    parsed = []
    for l in lines:
        parts = l.split()
        if len(parts) < 4: continue
        t = parts[0]
        if not re.match(r"^\d{4}$", t): continue
        price = float(parts[1])
        vol = float(parts[2])
        amt = float(parts[3]) if len(parts) > 3 else 0
        h, m = int(t[:2]), int(t[2:])
        parsed.append((h * 60 + m, price, price, price, price, vol, amt))
    if not parsed: return []
    bars = []
    cur = None
    for tm, p, _, _, _, v, a in parsed:
        bucket = (tm // 5) * 5
        if cur is None or cur["minutes"] != bucket:
            if cur: bars.append(cur)
            cur = {"minutes": bucket, "open": p, "high": p, "low": p, "close": p, "vol": v, "amount": a}
        else:
            cur["high"] = max(cur["high"], p)
            cur["low"] = min(cur["low"], p)
            cur["close"] = p
            cur["vol"] += v
            cur["amount"] += a
    if cur: bars.append(cur)
    for b in bars:
        h, m = divmod(b["minutes"], 60)
        b["time"] = "%02d:%02d" % (h, m)
    return bars

# Load from existing intraday file (sh000001 + sh000300 already complete)
with open("data/market_intraday_2026-07-14.json", "r", encoding="utf-8") as f:
    existing = json.load(f)

# Inline data for the 5 newly pulled indices (full 1min)
SZ_399001 = """0930 14532.36 5575524 9604416325.47
1500 14924.87 674840592 1432171610040.82"""

SZ_399006 = """0930 3729.61 1014130 3320606711.23
1500 3851.14 196146517 653269514605.69"""

SH_000016 = """0930 2909.93 446245 1723370164.00
1500 2955.55 66998208 260712822999.00"""

SH_000905 = """0930 8135.05 1304063 3080365231.40
1500 8275.94 215841090 562942515965.90"""

SH_000688 = """0930 1994.44 65093 993170249.00
1500 2009.73 16013950 202059847034.00"""

# Note: These are just placeholders; actual data from API is in the response
# We need the actual full data from the API responses.
# For now, let's read from the raw API responses which are in the tool call results.

# Actually, let me embed the actual full data directly from the API calls.
# This is a big dataset but necessary for proper charts.

DATA = {
    "sh000001": existing["indices"]["sh000001"],
    "sh000300": existing["indices"]["sh000300"],
    "sz399001": {"name": "深证成指", "code": "sz399001"},
    "sz399006": {"name": "创业板指", "code": "sz399006"},
    "sh000016": {"name": "上证50", "code": "sh000016"},
    "sh000905": {"name": "中证500", "code": "sh000905"},
    "sh000688": {"name": "科创50", "code": "sh000688"},
    "hkHSI": existing["indices"].get("hkHSI", {"name": "恒生指数", "code": "hkHSI"}),
}

# Copy existing parsed bars for sh000001 and sh000300
out = {"date": "2026-07-14", "indices": {}}
out["indices"]["sh000001"] = DATA["sh000001"]
out["indices"]["sh000300"] = DATA["sh000300"]
if DATA["hkHSI"].get("bars"):
    out["indices"]["hkHSI"] = DATA["hkHSI"]

# For the other indices, we need full data embedded.
# Let me write a helper that reads from a separate file.

print("sh000001:", len(out["indices"]["sh000001"]["bars"]), "bars")
print("sh000300:", len(out["indices"]["sh000300"]["bars"]), "bars")
print("hkHSI:", len(out["indices"].get("hkHSI", {}).get("bars", [])), "bars")

# Report on what's still missing
for code in ["sz399001","sz399006","sh000016","sh000905","sh000688"]:
    print(f"{code}: NEED FULL DATA EMBEDDING")

import os
out_path = "data/market_intraday_2026-07-14.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("Partial save done, size", os.path.getsize(out_path))
print("Need to embed full 1min data for 5 indices.")
