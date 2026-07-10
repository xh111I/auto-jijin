#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
补齐 market_raw_ohlc 的 sectors 数组（板块 250 日 OHLC），解决模块⑦「板块日K」的
「（未提供近 250 日 OHLC，暂略去日K）」占位问题。

数据源：腾讯公开行情接口 newfqkline（不复权，含成交额）。
行格式（腾讯 day 数组）：[date, open, close, high, low, volume, {}, pct, amount_wan, '', '']
其中 amount 以「万元」计，故 vol_yi(亿) = amount_wan / 1e4。

目标 OHLC 行（与 market_raw_ohlc 既有 indices 一致）：[date, open, high, low, close, vol_yi]
"""
import json
import ssl
import sys
import urllib.request

RAW = "C:/Users/LEGION/Nutstore/1/daily-report/data/market_raw_ohlc_2026-07-10.json"
TODAY = "2026-07-10"

# 报告板块名（EXACT，须与 market_2026-07-10.json 一致） -> 腾讯/westock 代码
SECTOR_CODES = [
    ("半导体", "csH30184"),
    ("CPO/通信设备", "cs931160"),
    ("军工(航天装备/航海装备)", "sz399967"),
    ("医疗服务", "sz399989"),
    ("港股创新药", "cs931787"),
    ("食品饮料/大消费", "sh000815"),
    ("人工智能(应用端)", "cs931071"),
    ("证券/大金融", "sz399437"),
]
# 北证50 复用既有指数 OHLC（bj899050），无需重新拉取
BEIJING50_NAME = "北证50"
BEIJING50_CODE = "bj899050"

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


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


def to_ohlc(rows):
    out = []
    seen = set()
    for r in rows:
        date = r[0]
        if date > TODAY:           # 剔除未来日期
            continue
        if date in seen:           # 去重
            continue
        seen.add(date)
        o = float(r[1])
        c = float(r[2])
        h = float(r[3])
        lo = float(r[4])
        amt_wan = float(r[8])
        vol_yi = round(amt_wan / 1e4, 2)
        out.append([date, o, h, lo, c, vol_yi])
    out.sort(key=lambda x: x[0])   # 升序
    return out


def main():
    with open(RAW, encoding="utf-8") as f:
        raw = json.load(f)

    sectors = []
    for name, code in SECTOR_CODES:
        try:
            rows = fetch(code)
            ohlc = to_ohlc(rows)
            if len(ohlc) < 6:
                print("WARN %s (%s): only %d rows" % (name, code, len(ohlc)), file=sys.stderr)
                continue
            sectors.append({"name": name, "ohlc": ohlc, "code": code})
            print("OK   %-26s (%s): %4d rows  %s..%s  last_close=%.2f" %
                  (name, code, len(ohlc), ohlc[0][0], ohlc[-1][0], ohlc[-1][4]))
        except Exception as e:
            print("ERR  %s (%s): %s" % (name, code, e), file=sys.stderr)

    # 北证50：复用指数 OHLC
    for idx in raw.get("indices", []):
        if idx.get("code") == BEIJING50_CODE:
            ohlc = [list(r) for r in idx["ohlc"]]
            sectors.append({"name": BEIJING50_NAME, "ohlc": ohlc, "code": BEIJING50_CODE})
            print("OK   %-26s (reuse %s): %4d rows  %s..%s" %
                  (BEIJING50_NAME, BEIJING50_CODE, len(ohlc), ohlc[0][0], ohlc[-1][0]))
            break

    raw["sectors"] = [{"name": s["name"], "ohlc": s["ohlc"]} for s in sectors]
    with open(RAW, "w", encoding="utf-8") as f:
        json.dump(raw, f, ensure_ascii=False, indent=1)
    print("INJECTED sectors: %d" % len(raw["sectors"]))


if __name__ == "__main__":
    main()
