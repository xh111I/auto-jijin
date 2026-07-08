#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
场内穿透 · 持仓清单拉取（option i：akshare 季度重仓缓存）
========================================================
为「场外股基 / QDII / 指数联接」拉取真实十大重仓股，写入 watchlist.json
的 holdings[i].stock_holdings 字段 + holdings_as_of（季度日期），季度更新一次即可。

数据源：akshare -> 东方财富 fund_portfolio_hold_em（已验证 eastmoney 本环境可达）。
只处理权益类（跳过 纯债 鹏华丰诚债）。

用法：
    python3 fetch_fund_holdings.py [watchlist.json 路径]

依赖：pip install akshare
"""
import json
import sys
import os
import datetime

# 纯债 / 无权益持仓的基金直接跳过
SKIP_SECTORS = {"固定收益/纯债安全垫", "纯债安全垫(无权益板块)"}

# 名称->akshare 代码 显式映射（watchlist 名称常与 akshare 简称差"发起/科技/LOF/(QDII)"等后缀，
# 自动模糊匹配易误命中，这里对小而固定的基金列表用精确映射最稳）。
NAME_OVERRIDE = {
    "东方人工智能主题混合C": "017811",
    "东方阿尔法科技优选混合C": "024424",   # akshare: 东方阿尔法科技优选混合发起C
    "广发港股创新药ETF联接(QDII)C": "019671",
    "永赢先锋半导体智选混合C": "025209",   # akshare: 永赢先锋半导体智选混合发起C
    "富国中证煤炭指数C": "013275",         # akshare: 富国中证煤炭指数(LOF)C
    "嘉实中证主要消费ETF发起联接C": "009180",
    "广发纳斯达克100ETF联接(QDII)C": "006479",  # akshare: 广发纳斯达克100ETF联接人民币(QDII)C
    "国泰半导体制造精选混合C": "025687",   # akshare: 国泰半导体制造精选混合发起C
    "财通集成电路产业股票C": "006503",
    "财通成长优选混合C": "021528",
    "天弘中证全指通信设备指数C": "020900",  # akshare: 天弘中证全指通信设备指数发起C
}


def fetch_top10(ak, code: str, year: str):
    """拉取单只基金十大重仓股（股票型）。返回 [{code,name,weight}]。"""
    try:
        df = ak.fund_portfolio_hold_em(symbol=code, date=year)
    except Exception as e:
        print(f"  WARN 拉取 {code} 失败: {e}")
        return [], ""
    if df is None or len(df) == 0:
        return [], ""
    name_col = "股票名称" if "股票名称" in df.columns else df.columns[1]
    code_col = "股票代码" if "股票代码" in df.columns else df.columns[0]
    w_col = "占净值比例" if "占净值比例" in df.columns else df.columns[-1]
    q_col = "季度" if "季度" in df.columns else None
    rows = []
    for _, r in df.iterrows():
        try:
            w = float(str(r[w_col]).replace("%", ""))
        except Exception:
            w = 0.0
        rows.append({
            "code": str(r[code_col]).strip(),
            "name": str(r[name_col]).strip(),
            "weight": round(w, 2),
            "quarter": str(r[q_col]).strip() if q_col else "",
        })
    q = rows[0]["quarter"] if rows else ""
    return rows[:10], q


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "config/watchlist.json"
    if not os.path.exists(path):
        print(f"ERROR: 找不到 {path}")
        sys.exit(1)

    try:
        import akshare as ak
    except Exception as e:
        print("ERROR: akshare 未安装或不可达:", e)
        print("       请先: pip install akshare")
        sys.exit(2)

    wl = json.load(open(path, encoding="utf-8"))
    today = datetime.date.today().strftime("%Y-%m-%d")
    year = str(datetime.date.today().year)

    funds = wl.get("holdings") or []
    updated = 0
    for f in funds:
        sector = f.get("sector") or ""
        if any(s in sector for s in SKIP_SECTORS):
            print(f"  SKIP {f.get('name')} (纯债，无权益持仓)")
            continue
        name = (f.get("name") or f.get("full_name") or "").strip()
        code = NAME_OVERRIDE.get(name)
        if not code:
            print(f"  SKIP {name} (未在 NAME_OVERRIDE 映射中找到代码)")
            continue
        print(f"  拉取 {name} ({code}) ...")
        top10, quarter = fetch_top10(ak, code, year)
        if top10:
            f["stock_holdings"] = top10
            f["holdings_as_of"] = quarter or today
            updated += 1
            print(f"    -> {len(top10)} 只重仓股, 合计权重 {round(sum(x['weight'] for x in top10),1)}% [{quarter}]")
        else:
            print(f"    -> 无重仓股数据(可能季报未披露)")

    if updated:
        json.dump(wl, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"\n-> 已更新 {updated} 只基金的 stock_holdings 到 {path}")
    else:
        print("\n-> 无更新")


if __name__ == "__main__":
    main()
