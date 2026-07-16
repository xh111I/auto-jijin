#!/usr/bin/env python3
"""
Assemble market_raw_ohlc_<DATE>.json from:
  - indices: data/_raw_<CODE>.json (8 A-share indices via QQ API)
  - sectors: data/_sector_raw/*.json (QQ sz/sh + westock cs + bj899050 reuse)

OHLC row: [date, open, high, low, close, vol_yi]
vol_yi: 亿元 (QQ: amount_wan/1e4; westock: amount/1e8; index _raw: amount/1e8)
"""
import json, os, datetime, glob

BASE = os.path.dirname(os.path.abspath(__file__))
DATE = "2026-07-16"
TODAY = datetime.date(2026, 7, 16)

# Index code -> name (from QQ API _raw files)
INDEX_NAMES = {
    "sh000001": "上证",
    "sz399001": "深证",
    "sz399006": "创业板",
    "sh000016": "上证50",
    "sh000300": "沪深300",
    "sh000905": "中证500",
    "sh000688": "科创50",
    "bj899050": "北证50",
}

# Sector files: (filename, sector_name, is_wx_format)
# is_wx_format=True: nodes use {date,open,high,low,last,volume,amount} (amount in yuan)
# is_wx_format=False: QQ format, nodes also use {date,open,high,low,last,volume,amount} 
#   but we need to build from QQ row format saved in files
SECTOR_SOURCES = [
    ("_sector_raw/csH30184_wx.json", "半导体", True),
    ("_sector_raw/cs931160_wx.json", "CPO/通信设备", True),
    ("_sector_raw/cs931787_wx.json", "港股创新药", True),
    ("_sector_raw/cs931071_wx.json", "人工智能(应用端)", True),
    ("_sector_raw/sz399389.json", "通信设备", False),
    ("_sector_raw/sz399437.json", "证券", False),
    ("_sector_raw/sz399998.json", "煤炭", False),
    ("_sector_raw/sz399967.json", "军工", False),
]


def parse_date(s):
    try:
        return datetime.date(*map(int, s.split("-")))
    except:
        return None


def sanitize(nodes, date_field="date"):
    """Reject future dates, dedupe by date, sort ascending."""
    seen = set()
    clean = []
    for n in nodes:
        dt = parse_date(n.get(date_field, ""))
        if dt is None:
            continue
        if dt > TODAY:
            continue
        if n[date_field] in seen:
            continue
        seen.add(n[date_field])
        clean.append(n)
    clean.sort(key=lambda n: n[date_field])
    return clean


def load_index_nodes(code):
    """Load QQ API _raw_<CODE>.json nodes (already in westock format)."""
    path = os.path.join(BASE, "_raw_%s.json" % code)
    with open(path, "r", encoding="utf-8") as f:
        rec = json.load(f)
    nodes = rec.get("nodes", [])
    return sanitize(nodes)


def index_to_ohlc(nodes):
    """Convert westock-format nodes to [date, open, high, low, close, vol_yi].
    Nodes: {date, open, high, low, last, volume, amount}
    amount in yuan -> vol_yi = amount / 1e8
    """
    return [
        [n["date"], n["open"], n["high"], n["low"], n["last"], round(n["amount"] / 1e8, 2)]
        for n in nodes
    ]


def load_sector_nodes(path, is_wx):
    """Load sector nodes from _sector_raw/<file>.
    is_wx=True: westock format {date, open, high, low, last, volume, amount} (amount in yuan)
    is_wx=False: same format (QQ nodes saved by fetch_sector_qq.py)
    """
    full_path = os.path.join(BASE, path)
    if not os.path.exists(full_path):
        print("WARN: sector file not found: %s" % full_path, file=__import__('sys').stderr)
        return None
    with open(full_path, "r") as f:
        rec = json.load(f)
    nodes = rec.get("nodes", [])
    return sanitize(nodes)


def sector_to_ohlc(nodes, is_wx):
    """Convert sector nodes to [date, open, high, low, close, vol_yi].
    Westock: amount in yuan -> /1e8
    QQ (saved by fetch_sector_qq): amount in yuan (already *10000) -> /1e8
    """
    return [
        [n["date"], n["open"], n["high"], n["low"], n["last"], round(n["amount"] / 1e8, 2)]
        for n in nodes
    ]


def main():
    out = {"date": DATE, "indices": [], "sectors": []}

    # --- Indices ---
    for code in INDEX_NAMES:
        nodes = load_index_nodes(code)
        if len(nodes) < 6:
            print("WARN %s: only %d nodes" % (code, len(nodes)))
            continue
        ohlc = index_to_ohlc(nodes)
        out["indices"].append({"code": code, "name": INDEX_NAMES[code], "ohlc": ohlc})
        print("  IDX %-10s %-6s rows=%d  %s..%s  close=%.2f" %
              (code, INDEX_NAMES[code], len(ohlc), ohlc[0][0], ohlc[-1][0], ohlc[-1][4]))

    # --- Sectors ---
    for path, sec_name, is_wx in SECTOR_SOURCES:
        nodes = load_sector_nodes(path, is_wx)
        if nodes is None or len(nodes) < 6:
            print("WARN sector %s (%s): insufficient nodes" % (sec_name, path))
            continue
        ohlc = sector_to_ohlc(nodes, is_wx)
        out["sectors"].append({"name": sec_name, "ohlc": ohlc})
        print("  SEC %-22s rows=%d  %s..%s  close=%.2f" %
              (sec_name, len(ohlc), ohlc[0][0], ohlc[-1][0], ohlc[-1][4]))

    # --- 北证50: reuse from index ---
    for idx in out["indices"]:
        if idx.get("code") == "bj899050":
            ohlc = [list(r) for r in idx["ohlc"]]
            out["sectors"].append({"name": "北证50", "ohlc": ohlc})
            print("  SEC %-22s (reuse) rows=%d" % ("北证50", len(ohlc)))
            break

    dst = os.path.join(BASE, "market_raw_ohlc_%s.json" % DATE)
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("\nWrote %s" % dst)
    print("  indices=%d  sectors=%d" % (len(out["indices"]), len(out["sectors"])))


if __name__ == "__main__":
    main()
