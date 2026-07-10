#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把 4 个中证板块(westock 已拉取、落盘 _sector_raw/<code>_wx.json)的 250 日 OHLC
追加进 market_raw_ohlc 的 sectors 数组(其余 5 个 sz/sh 板块 + 北证50 已由
inject_sector_ohlc.py 注入，保留不动)。

_wx.json 节点: {date, open, high, low, last(=close), volume, amount, exchange}
amount 单位为 元 -> vol_yi(亿) = amount / 1e8
OHLC 行(与既有 indices/sectors 一致): [date, open, high, low, close, vol_yi]
"""
import json
import os

BASE = "C:/Users/LEGION/Nutstore/1/daily-report/data"
RAW = os.path.join(BASE, "market_raw_ohlc_2026-07-10.json")
TODAY = "2026-07-10"

# 报告板块名(EXACT) -> _wx.json 文件名
CS_FILES = [
    ("半导体", "csH30184_wx.json"),
    ("CPO/通信设备", "cs931160_wx.json"),
    ("港股创新药", "cs931787_wx.json"),
    ("人工智能(应用端)", "cs931071_wx.json"),
]


def to_ohlc(nodes):
    out = []
    seen = set()
    for n in nodes:
        d = n["date"]
        if d > TODAY:
            continue
        if d in seen:
            continue
        seen.add(d)
        o = float(n["open"])
        h = float(n["high"])
        lo = float(n["low"])
        c = float(n["last"])
        amt = float(n.get("amount") or 0)
        out.append([d, o, h, lo, c, round(amt / 1e8, 2)])
    out.sort(key=lambda x: x[0])
    return out


def main():
    with open(RAW, encoding="utf-8") as f:
        raw = json.load(f)

    existing = raw.get("sectors") or []
    exist_names = {s["name"] for s in existing}
    print("现有 sectors (%d): %s" % (len(existing), sorted(exist_names)))

    added = 0
    for name, fname in CS_FILES:
        if name in exist_names:
            print("SKIP %s (已在 sectors 中)" % name)
            continue
        path = os.path.join(BASE, "_sector_raw", fname)
        with open(path, encoding="utf-8") as f:
            wx = json.load(f)
        ohlc = to_ohlc(wx.get("nodes", []))
        if len(ohlc) < 6:
            print("WARN %s: 仅 %d 行" % (name, len(ohlc)))
            continue
        existing.append({"name": name, "ohlc": ohlc})
        added += 1
        print("ADD  %-22s %4d rows %s..%s last_close=%.2f" %
              (name, len(ohlc), ohlc[0][0], ohlc[-1][0], ohlc[-1][4]))

    raw["sectors"] = existing
    with open(RAW, "w", encoding="utf-8") as f:
        json.dump(raw, f, ensure_ascii=False, indent=1)
    print("DONE: sectors=%d (+%d)" % (len(existing), added))


if __name__ == "__main__":
    main()
