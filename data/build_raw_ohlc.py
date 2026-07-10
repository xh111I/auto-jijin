#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Assemble per-index 250-day K-line raw files into market_raw_ohlc_<DATE>.json.

Reads data/_raw_<CODE>.json (one per A-share index, produced from westock-mcp
full K-line history), sanitizes each node's date (reject dates > TODAY, dedupe
by date, sort ascending), transforms every node into an OHLC row
[date, open, high, low, close, vol_in_yi], appends the 恒生科技 single-point
fallback, and writes market_raw_ohlc_<DATE>.json with "sectors":[].
"""
import json
import os
import datetime

DATA = os.path.dirname(os.path.abspath(__file__))
DATE = "2026-07-10"
TODAY = datetime.date(2026, 7, 10)

NAME = {
    "sh000001": "上证",
    "sz399001": "深证",
    "sz399006": "创业板",
    "sh000016": "上证50",
    "sh000300": "沪深300",
    "sh000905": "中证500",
    "sh000688": "科创50",
    "bj899050": "北证50",
}


def parse_date(s):
    try:
        y, m, d = map(int, s.split("-"))
        return datetime.date(y, m, d)
    except Exception:
        return None


def sanitize(nodes):
    """Reject future dates, dedupe by date, sort ascending."""
    seen = set()
    clean = []
    for n in nodes:
        dt = parse_date(n.get("date", ""))
        if dt is None:
            continue
        if dt > TODAY:          # drop glitched future dates (e.g. 2026-09-09)
            continue
        if n["date"] in seen:   # dedupe
            continue
        seen.add(n["date"])
        clean.append(n)
    clean.sort(key=lambda n: n["date"])
    return clean


def main():
    out = {"date": DATE, "indices": [], "sectors": []}

    for code in NAME:
        path = os.path.join(DATA, "_raw_%s.json" % code)
        with open(path, "r", encoding="utf-8") as f:
            rec = json.load(f)
        nodes = rec.get("nodes", [])
        clean = sanitize(nodes)
        ohlc = [
            [
                n["date"],
                n["open"],
                n["high"],
                n["low"],
                n["last"],
                round(n["amount"] / 1e8, 2),
            ]
            for n in clean
        ]
        out["indices"].append({"code": code, "name": NAME[code], "ohlc": ohlc})

    # 恒生科技 (hstech) not covered by westock A-share K-line -> single-point fallback
    out["indices"].append(
        {
            "code": "hstech",
            "name": "恒生科技",
            "ohlc": [["2026-07-10", 4730.32, 4730.32, 4730.32, 4730.32, 0.0]],
        }
    )

    dst = os.path.join(DATA, "market_raw_ohlc_%s.json" % DATE)
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    print("Wrote", dst)
    for i in out["indices"]:
        print("  %-8s %-6s rows=%d" % (i["code"], i["name"], len(i["ohlc"])))


if __name__ == "__main__":
    main()
