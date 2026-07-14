#!/usr/bin/env python3
"""Inject all sector OHLC into market_raw_ohlc_2026-07-14.json

sz/sh sectors: from QQ API (fresh, _sector_raw/<code>_wx.json)
cs sectors: from westock cache (07-10) + today's QQ single-row appended
北证50: reuse index bj899050
"""
import json, os, datetime

DATA = os.path.dirname(os.path.abspath(__file__))
TODAY = "2026-07-14"
RAW = os.path.join(DATA, "market_raw_ohlc_%s.json" % TODAY)

# sz/sh 板块 -> QQ文件
SECTOR_QQ = [
    ("军工(航天装备/航海装备)", "sz399967_wx.json"),
    ("医疗服务", "sz399989_wx.json"),
    ("证券/大金融", "sz399437_wx.json"),
    ("食品饮料/大消费", "sh000815_wx.json"),
]

# cs板块 -> westock缓存 + 今日单点
CS_WITH_TODAY = [
    ("半导体", "csH30184_wx.json", 16496.67),
    ("CPO/通信设备", "cs931160_wx.json", 23568.96),
    ("港股创新药", "cs931787_wx.json", 1278.46),
    ("人工智能(应用端)", "cs931071_wx.json", 3172.28),
]

def parse_date(s):
    try:
        y, m, d = map(int, s.split("-"))
        return datetime.date(y, m, d)
    except: return None

def load_qq_wx(fname):
    """Load QQ API _wx.json format"""
    path = os.path.join(DATA, "_sector_raw", fname)
    with open(path, encoding="utf-8") as f:
        wx = json.load(f)
    nodes = wx.get("nodes", [])
    ohlc = []
    seen = set()
    for n in nodes:
        d = n["date"]
        if d > TODAY: continue
        if d in seen: continue
        seen.add(d)
        ohlc.append([d, n["open"], n["high"], n["low"], n["last"], round(n["amount"]/1e8, 2)])
    ohlc.sort(key=lambda x: x[0])
    return ohlc[-250:]

def load_cs_westock(fname, today_close):
    """Load westock cached data + append today's close from QQ"""
    path = os.path.join(DATA, "_sector_raw", fname)
    with open(path, encoding="utf-8") as f:
        wx = json.load(f)
    nodes = wx.get("nodes", [])
    ohlc = {}
    for n in nodes:
        d = n.get("date", "")
        if d > "2026-07-10": continue  # westock cache only up to 07-10
        if d in ohlc: continue
        ohlc[d] = [
            float(n.get("open", 0)),
            float(n.get("high", 0)),
            float(n.get("low", 0)),
            float(n.get("last", 0)),
            round(float(n.get("amount", 0))/1e8, 2),
        ]

    # Get the last cached close for today's estimate
    dates = sorted(ohlc.keys())
    last_close = ohlc[dates[-1]][3] if dates else 0

    # Append today's close from QQ (single-point: open=close=high=low=today_close)
    if TODAY not in ohlc:
        ohlc[TODAY] = [today_close, today_close, today_close, today_close, round(last_close * 0.01 * 0, 2)]

    sorted_dates = sorted(ohlc.keys())
    rows = [[d, ohlc[d][0], ohlc[d][1], ohlc[d][2], ohlc[d][3], ohlc[d][4]] for d in sorted_dates]
    return rows[-250:]

def main():
    with open(RAW, encoding="utf-8") as f:
        raw = json.load(f)

    sectors = []

    # 1. sz/sh sectors from QQ API
    for name, fname in SECTOR_QQ:
        ohlc = load_qq_wx(fname)
        if len(ohlc) >= 6:
            sectors.append({"name": name, "ohlc": ohlc})
            print("OK  %-26s %4d rows  %s..%s  last=%.2f" %
                  (name, len(ohlc), ohlc[0][0], ohlc[-1][0], ohlc[-1][4]))
        else:
            print("WARN %-26s only %d rows" % (name, len(ohlc)))

    # 2. cs sectors from westock cache + today's close
    for name, fname, tc in CS_WITH_TODAY:
        ohlc = load_cs_westock(fname, tc)
        if len(ohlc) >= 6:
            sectors.append({"name": name, "ohlc": ohlc})
            print("OK  %-26s %4d rows  %s..%s  last=%.2f [cs+QQ-today]" %
                  (name, len(ohlc), ohlc[0][0], ohlc[-1][0], ohlc[-1][4]))
        else:
            print("WARN %-26s only %d rows" % (name, len(ohlc)))

    # 3. 北证50: reuse index OHLC
    for idx in raw.get("indices", []):
        if idx.get("code") == "bj899050":
            ohlc = [list(r) for r in idx["ohlc"]]
            sectors.append({"name": "北证50", "ohlc": ohlc})
            print("OK  %-26s %4d rows (reuse index)" % ("北证50", len(ohlc)))
            break

    raw["sectors"] = sectors
    with open(RAW, "w", encoding="utf-8") as f:
        json.dump(raw, f, ensure_ascii=False, indent=1)
    print("\nINJECTED: %d sectors into %s" % (len(sectors), RAW))

if __name__ == "__main__":
    main()
