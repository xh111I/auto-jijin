#!/usr/bin/env python3
"""
Fetch sz/sh sector OHLC via QQ finance public API.
QQ row: [date, open, close, high, low, volume, {}, pct, amount_wan, '', '']
Output nodes: {date, open, high, low, last, volume, amount}
amount: QQ gives amount_wan -> *10000 to yuan
"""
import json, os, ssl, urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
TODAY = "2026-07-13"
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

SECTORS = {
    "sz399389": "通信设备",
    "sz399437": "证券",
    "sz399998": "煤炭",
    "sz399967": "军工",
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
        raise ValueError("no data node for %s" % code)
    rows = node.get("day") or node.get("qfqday") or []
    if not rows:
        raise ValueError("empty day list for %s" % code)
    return rows

def rows_to_nodes(rows):
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
        amt = float(r[8]) * 10000 if len(r) > 8 else 0  # amount_wan -> yuan
        nodes.append({"date": date, "open": o, "last": c, "high": h, "low": lo, "volume": vol, "amount": amt})
    nodes.sort(key=lambda n: n["date"])
    return nodes

def main():
    for code, name in SECTORS.items():
        try:
            rows = fetch(code)
            nodes = rows_to_nodes(rows)
            if len(nodes) < 6:
                print("WARN %s: only %d rows" % (code, len(nodes)))
                continue
            path = os.path.join(BASE, "_sector_raw", "%s.json" % code)
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"code": code, "name": name, "nodes": nodes}, f, ensure_ascii=False, indent=1)
            print("OK   %-10s %-8s rows=%d  %s..%s  close=%.2f" %
                  (code, name, len(nodes), nodes[0]["date"], nodes[-1]["date"], nodes[-1]["last"]))
        except Exception as e:
            print("ERR  %s %s: %s" % (code, name, e))

if __name__ == "__main__":
    main()
