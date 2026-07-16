#!/usr/bin/env python3
"""
Fetch 250-day OHLC for all indices (via QQ finance public API for sz/sh/bj codes)
and save to _raw_<CODE>.json files.
For cs中证 codes, use MCP (separate script).

QQ finance API: https://proxy.finance.qq.com/ifzqgtimg/appstock/app/newfqkline/get?param=<CODE>,day,,,250,
"""
import json, os, ssl, sys, urllib.request, datetime

BASE = os.path.dirname(os.path.abspath(__file__))
TODAY = "2026-07-16"
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

# Index code -> name mapping
INDICES = {
    "sh000001": "上证",
    "sz399001": "深证",
    "sz399006": "创业板",
    "sh000016": "上证50",
    "sh000300": "沪深300",
    "sh000905": "中证500",
    "sh000688": "科创50",
    "bj899050": "北证50",
}

def fetch(code):
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
        raise ValueError("no data node for %s: %s" % (code, list(d.keys())[:3]))
    rows = node.get("day") or node.get("qfqday") or []
    if not rows:
        raise ValueError("empty day list for %s" % code)
    return rows

def qq_to_nodes(rows):
    """Convert QQ finance rows to standalone node format matching westock:
    each node: {date, open, high, low, last, volume, amount}
    QQ row: [date, open, close, high, low, volume, {}, pct, amount_wan, '', '']
    """
    nodes = []
    seen = set()
    for r in rows:
        date = r[0]
        if date > TODAY:
            continue
        if date in seen:
            continue
        seen.add(date)
        o = float(r[1])
        c = float(r[2])
        h = float(r[3])
        lo = float(r[4])
        vol = int(float(r[5])) if len(r) > 5 else 0
        amt = float(r[8]) * 10000 if len(r) > 8 else 0  # amount_wan to yuan
        nodes.append({
            "date": date,
            "open": o,
            "last": c,
            "high": h,
            "low": lo,
            "volume": vol,
            "amount": amt,
        })
    nodes.sort(key=lambda n: n["date"])
    return nodes

def save_raw(code, nodes):
    path = os.path.join(BASE, "_raw_%s.json" % code)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"code": code, "nodes": nodes}, f, ensure_ascii=False, indent=1)
    print("OK   %-10s %s  %4d rows  %s..%s  last_close=%.2f" %
          (code, name_map.get(code, ""), len(nodes), nodes[0]["date"], nodes[-1]["date"], nodes[-1]["last"]))

name_map = INDICES

def main():
    for code in INDICES:
        try:
            rows = fetch(code)
            nodes = qq_to_nodes(rows)
            if len(nodes) < 6:
                print("WARN %s: only %d nodes" % (code, len(nodes)))
                continue
            save_raw(code, nodes)
        except Exception as e:
            print("ERR  %s: %s" % (code, e))

if __name__ == "__main__":
    main()
