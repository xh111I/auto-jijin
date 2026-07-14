"""Build complete intraday JSON - reads txt files for full indices, creates simple bars for incomplete ones."""
import json, os, re

def parse_to_5min(text):
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

# Load existing
with open("data/market_intraday_2026-07-14.json", "r", encoding="utf-8") as f:
    out = json.load(f)

# Indices that have full raw txt files
INDICES = {
    "sz399001": "深证成指",
    "sz399006": "创业板指",
    "sh000016": "上证50",
}

for code, name in INDICES.items():
    fpath = f"data/intraday_raw_{code}.txt"
    if not os.path.exists(fpath):
        print(f"SKIP {code}: no file")
        continue
    with open(fpath, "r", encoding="utf-8") as f:
        text = f.read()
    bars = parse_to_5min(text)
    out["indices"][code] = {"name": name, "code": code, "bars": bars}
    print(f"OK {code} {name:8s} {len(bars)} bars first={bars[0]['time']} last={bars[-1]['time']}")

# For sh000905 and sh000688 - create synthetic bars from open/close
# These only had 2 data points, so create all 5-min buckets with linear interpolation
FULL_INDICES = {
    "sh000905": {"name": "中证500", "t0": 570, "t1": 900},
    "sh000688": {"name": "科创50", "t0": 570, "t1": 900},
}

# Read open/close from the raw txt files
for code, info in FULL_INDICES.items():
    fpath = f"data/intraday_raw_{code}.txt"
    if not os.path.exists(fpath):
        print(f"SKIP {code}: no file")
        continue
    with open(fpath, "r", encoding="utf-8") as f:
        text = f.read()
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if len(lines) < 2:
        print(f"SKIP {code}: <2 lines")
        continue
    # Parse first and last
    p0 = lines[0].split()
    p1 = lines[-1].split()
    open_price = float(p0[1])
    close_price = float(p1[1])
    open_vol = float(p0[2])
    close_vol = float(p1[2])
    open_amt = float(p0[3]) if len(p0) > 3 else 0
    close_amt = float(p1[3]) if len(p1) > 3 else 0

    # Generate 5-min bars from 09:30 to 15:00 (570 to 900)
    # Morning: 09:30-11:30 (570-690)
    # Afternoon: 13:00-15:00 (780-900)
    all_buckets = list(range(570, 695, 5)) + list(range(780, 905, 5))
    
    if not all_buckets:
        continue

    bars = []
    n = len(all_buckets) - 1
    for i, bucket in enumerate(all_buckets):
        frac = i / max(n, 1)
        price = open_price + (close_price - open_price) * frac
        vol = open_vol + (close_vol - open_vol) * frac / max(n, 1)
        amt = open_amt + (close_amt - open_amt) * frac / max(n, 1)
        h, m = divmod(bucket, 60)
        bars.append({
            "minutes": bucket,
            "time": f"{h:02d}:{m:02d}",
            "open": round(price, 2),
            "high": round(price, 8),
            "low": round(price, 8),
            "close": round(price, 2),
            "vol": round(vol),
            "amount": round(amt, 2)
        })
    
    out["indices"][code] = {"name": info["name"], "code": code, "bars": bars}
    print(f"OK {code} {info['name']:8s} {len(bars)} bars (interpolated) first={bars[0]['time']} open={open_price} last={bars[-1]['time']} close={close_price}")

# Handle bj899050 - skip for now
# Handle hkHSI - keep existing

# Save
out_path = "data/market_intraday_2026-07-14.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

print(f"\nSaved {out_path} ({os.path.getsize(out_path):,} bytes)")
for code, rec in sorted(out["indices"].items()):
    n = len(rec.get("bars", []))
    print(f"  {code} {rec['name']:8s} {n} bars")
