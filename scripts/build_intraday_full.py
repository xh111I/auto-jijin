"""Build complete intraday JSON from raw data files + existing JSON."""
import json, os, re, glob

def parse_to_5min(text):
    """Parse raw 1min text into 5-min aggregated bars."""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
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
        parsed.append((h * 60 + m, price, vol, amt))
    if not parsed: return []
    bars = []
    cur = None
    for tm, p, v, a in parsed:
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
        b["time"] = f"{h:02d}:{m:02d}"
    return bars

# Load existing intraday (has sh000001 + sh000300 complete)
with open("data/market_intraday_2026-07-14.json", "r", encoding="utf-8") as f:
    existing = json.load(f)

# Index definitions
INDICES = {
    "sz399001": "深证成指",
    "sz399006": "创业板指",
    "sh000016": "上证50",
    "sh000905": "中证500",
    "sh000688": "科创50",
}

# Read raw data files
for code in INDICES:
    fpath = f"data/intraday_raw_{code}.txt"
    if not os.path.exists(fpath):
        print(f"SKIP {code}: missing {fpath}")
        continue
    with open(fpath, "r", encoding="utf-8") as f:
        text = f.read()
    bars = parse_to_5min(text)
    if bars:
        existing["indices"][code] = {
            "name": INDICES[code],
            "code": code,
            "bars": bars
        }
        print(f"OK {code} {INDICES[code]:8s} {len(bars)} bars | first={bars[0]['time']} open={bars[0]['open']} | last={bars[-1]['time']} close={bars[-1]['close']}")
    else:
        print(f"FAIL {code}: no bars parsed")

# Save
out_path = "data/market_intraday_2026-07-14.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(existing, f, ensure_ascii=False, indent=1)

# Summary
total = existing["indices"]
print(f"\nSaved {out_path} ({os.path.getsize(out_path):,} bytes)")
for code, rec in total.items():
    n = len(rec.get("bars", []))
    print(f"  {code} {rec['name']:8s} {n} bars")
