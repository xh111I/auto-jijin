#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
组装 场内穿透 输入 JSON（由 LLM 从 westock 取数后调用）。
读 watchlist 的 stock_holdings + westock 当日 change_percent，组装 penetrate.py 输入。

本脚本内联 2026-07-07 的 westock 重仓股涨跌幅（真实数据），
仅供本次端到端验证；正式自动化中这些数字由 LLM 实时拉取注入。
"""
import json
import sys
import datetime

# 2026-07-07 westock 重仓股 change_percent（前缀代码）
QUOTES = {
    "sh600105": -2.0, "sh600183": -2.27, "sh600188": -3.24, "sh600348": -0.47,
    "sh600487": -4.39, "sh600498": -1.81, "sh600522": -1.58, "sh600985": -2.12,
    "sh601001": -4.07, "sh601088": -0.36, "sh601138": 0.3, "sh601225": -1.04,
    "sh601699": -1.72, "sh601898": -1.94, "sh603061": -2.92, "sh603986": -5.24,
    "sh688008": -5.76, "sh688012": 0.01, "sh688037": 3.03, "sh688072": 0.0,
    "sh688082": 6.3, "sh688120": 2.6, "sh688123": -1.14, "sh688147": 5.26,
    "sh688183": 1.06, "sh688195": -2.36, "sh688200": 4.48, "sh688233": 0.8,
    "sh688361": 3.97, "sh688409": 3.13, "sh688498": 4.58, "sh688525": -6.53,
    "sh688627": 1.16, "sh688630": -1.65, "sh688652": 6.27, "sh688766": -6.58,
    "sz000063": -1.35, "sz000723": -1.75, "sz000983": -4.35, "sz001309": -8.98,
    "sz002281": 6.05, "sz002371": 0.35, "sz002463": 0.69, "sz300136": -0.29,
    "sz300223": -8.62, "sz300308": 2.09, "sz300394": 2.99, "sz300475": -7.8,
    "sz300502": 0.63, "sz300567": 0.91, "sz301200": -1.83, "sz301308": -7.91,
    "sz301377": 0.59,
}

# 参与穿透的基金（跳过 纯债/已清仓/联接QDII/待确认）
#   note: pending_confirm 基金 NAV 未确认(=0)，仅展示估算，不参与 ±0.5 判定
TARGETS = {
    "东方人工智能主题混合C": "active",
    "东方阿尔法科技优选混合C": "active",
    "永赢先锋半导体智选混合C": "active",
    "富国中证煤炭指数C": "active",
    "财通集成电路产业股票C": "pending_confirm",
    "财通成长优选混合C": "pending_confirm",
    "天弘中证全指通信设备指数C": "pending_confirm",
}


def prefix(code: str) -> str:
    if code[0] == "6":
        return "sh" + code
    if code[0] in "03":
        return "sz" + code
    if code[0] in "84":
        return "bj" + code
    return code


def main():
    wl = json.load(open("config/watchlist.json", encoding="utf-8"))
    as_of = "2026-07-07"
    funds = []
    for f in wl["holdings"]:
        name = f["name"]
        if name not in TARGETS:
            continue
        sh = f.get("stock_holdings") or []
        if not sh:
            continue
        holdings = [{"code": prefix(x["code"]), "name": x["name"], "weight": x["weight"]} for x in sh]
        quotes = {prefix(x["code"]): QUOTES.get(prefix(x["code"])) for x in sh}
        quotes = {k: v for k, v in quotes.items() if v is not None}
        actual = f.get("yesterday_return_pct") or 0.0
        funds.append({
            "name": name,
            "code": f.get("full_name", name),
            "type": "offsite",
            "status": TARGETS[name],
            "actual_return_pct": round(float(actual), 3),
            "holdings": holdings,
            "quotes": quotes,
        })
    out = {"as_of": as_of, "funds": funds}
    json.dump(out, open("penetrate_input.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"-> 已写 penetrate_input.json ({len(funds)} 只基金, as_of={as_of})")
    for fd in funds:
        miss = [h["code"] for h in fd["holdings"] if h["code"] not in fd["quotes"]]
        print(f"   {fd['name']:20s} 持仓{len(fd['holdings'])} 命中quote{len(fd['quotes'])} 缺{len(miss)} {miss}")


if __name__ == "__main__":
    main()
