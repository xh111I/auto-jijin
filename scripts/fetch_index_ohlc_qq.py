#!/usr/bin/env python3
"""Fetch 9 A-share indices 250-day OHLC via QQ public API, save to _raw_<CODE>.json"""
import json, os, ssl, sys, urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
TODAY = "2026-07-14"

# Index codes (8 A-share + 北证50 handled via QQ)
CODES = {
    "sh000001": "上证",
    "sz399001": "深证",
    "sz399006": "创业板",
    "sh000016": "上证50",
    "sh000300": "沪深300",
    "sh000905": "中证500",
    "sh000688": "科创50",
    "bj899050": "北证50",
}

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

def fetch_qq(code):
    url = "https://proxy.finance.qq.com/ifzqgtimg/appstock/app/newfqkline/get?param=%s,day,,,250," % code
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
        data = json.loads(r.read().decode("utf-8"))
    d = data.get("data", {})
    node = d.get(code)
    if not node:
        for k, v in d.items():
            if isinstance(v, dict) and ("day" in v or "qfqday" in v):
                node = v
                break
    if not node:
        raise ValueError("no data node for %s" % code)
    rows = node.get("day") or node.get("qfqday") or []
    if not rows:
        raise ValueError("empty day list for %s" % code)
    return rows

def to_nodes(rows):
    """Convert QQ rows [date, open, close, high, low, volume, {}, pct, amount_wan] to westock-compatible nodes"""
    out = []
    seen = set()
    for r in rows:
        date = r[0]
        if date > TODAY:
            continue
        if date in seen:
            continue
        seen.add(date)
        out.append({
            "date": date,
            "open": float(r[1]),
            "close": float(r[2]),
            "high": float(r[3]),
            "low": float(r[4]),
            "last": float(r[2]),
            "volume": float(r[5]) if len(r) > 5 else 0,
            "amount": float(r[8]) * 1e4 if len(r) > 8 else 0,  # 万元→元
        })
    out.sort(key=lambda n: n["date"])
    return out[-250:]

def main():
    for code, name in CODES.items():
        try:
            rows = fetch_qq(code)
            nodes = to_nodes(rows)
            path = os.path.join(DATA, "_raw_%s.json" % code)
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"code": code, "nodes": nodes}, f, ensure_ascii=False, indent=1)
            print("OK  %-8s %-6s %4d rows  %s..%s  last=%.2f" %
                  (code, name, len(nodes), nodes[0]["date"], nodes[-1]["date"], nodes[-1]["last"]))
        except Exception as e:
            print("ERR %-8s %-6s %s" % (code, name, e), file=sys.stderr)

if __name__ == "__main__":
    main()
