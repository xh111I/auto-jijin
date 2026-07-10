# -*- coding: utf-8 -*-
import json, glob, os, re
base = os.path.dirname(os.path.abspath(__file__))
files = sorted(glob.glob(os.path.join(base, "q_*.txt")))
for f in files:
    name = os.path.basename(f)
    print("\n==== %s ====" % name)
    try:
        d = json.load(open(f, encoding="utf-8"))
    except Exception as e:
        print("FAIL", e); continue
    data = d.get("data", {})
    api = data.get("apiData", {})
    for block in api.get("apiRecall", []) or []:
        c = block.get("content", "")
        # table format (commodities/fx)
        if "| :---:" in c:
            # find header row
            rows = [r for r in c.splitlines() if r.startswith("|") and "最新价格" not in r and ":---:" not in r and "市场类型" not in r]
            # header is the one with 期货名称
            for r in rows:
                cells = [x.strip() for x in r.strip("|").split("|")]
                if len(cells) > 14 and cells[1] and cells[1] not in ("期货名称",):
                    fn = cells[1]; price = cells[3]; chg = cells[14] if len(cells)>14 else ""
                    print("  [表] %s 价=%s 涨跌%%=%s" % (fn, price, chg))
            continue
        # text format: split by company blocks
        # find all "名称(代码:XXX)在"
        parts = re.split(r'(?=[^\n]*(?:\(代码:|\(证券代码:))', c)
        # simpler: iterate lines, capture per stock
        # Use regex to find each stock header and its 最新价格/当日涨跌幅
        # block-level: each entity starts with a name line
        ents = re.findall(r'([^（）\n]*?)\(代码:[^)]*\)在[^\n]*?\n数据更新时间:([^\n;]*);最新价格:([\d,]+\.?\d*)[^\n]*?;当日涨跌幅:(-?[\d.]+)%', c)
        for nm, ts, px, ch in ents:
            print("  [股] %s 时间=%s 价=%s 涨跌%%=%s" % (nm.strip(), ts.strip(), px, ch))
        # fx style table already handled; fallback for index-only
        idx = re.findall(r'([^\n]*指数)[为:].*?([\d,]+\.?\d*)点[^\n]*?涨跌幅为(-?[\d.]+)%', c)
        for nm, px, ch in idx:
            print("  [指] %s 点=%s 涨跌%%=%s" % (nm.strip(), px, ch))
