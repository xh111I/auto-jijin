#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
场内穿透计算器（确定性，非 LLM 估算）
=====================================
根据基金「持仓/ETF 成份股」+ 各成份股当日涨跌幅，自己算出基金理论涨幅，
再与真实净值(NAV)比对，输出归因与偏差。

输入 JSON（由自动化 LLM 从 westock 取数后组装，本脚本只做确定性计算）：
{
  "as_of": "2026-07-08",
  "funds": [
    {
      "name": "半导体ETF国联安",
      "code": "sh512480",
      "type": "etf",                       # etf=交易所基金(用 westock etf holdings); offsite=场外股基(用缓存 holdings)
      "actual_return_pct": 0.22,          # ETF=westock quote change%; 场外=watchlist yesterday_return_pct(OCR 真值)
      "holdings": [ {"code":"sh688256","name":"寒武纪","weight":7.84}, ... ],
      "quotes": { "sh688256": 1.84, "sh603986": -2.71, ... }   # 成份股当日 change_percent
    }
  ]
}

输出：penetrate_output.json + 打印 Markdown 表。
"""
import json
import sys
import os


def penetrate_fund(f: dict) -> dict:
    holdings = f.get("holdings") or []
    quotes = f.get("quotes") or {}
    rows = []
    sum_w = 0.0
    sum_wp = 0.0
    missing = []
    for it in holdings:
        w = float(it.get("weight") or 0.0)
        code = it.get("code")
        pct = quotes.get(code)
        if pct is None:
            missing.append(code)
            continue
        pct = float(pct)
        sum_w += w
        sum_wp += w * pct
        rows.append({
            "code": code,
            "name": it.get("name"),
            "weight": w,
            "pct": pct,
            "contrib_pct": w * pct / 100.0,   # 对基金净值的贡献(百分点)
        })
    # 已知成份加权日均涨 → 假设未知部分(现金/其它持仓)同幅运动
    est = (sum_wp / sum_w) if sum_w else 0.0
    actual = float(f.get("actual_return_pct") or 0.0)
    dev = actual - est
    return {
        "name": f.get("name"),
        "code": f.get("code"),
        "type": f.get("type"),
        "known_weight_pct": round(sum_w, 2),
        "est_return_pct": round(est, 3),
        "actual_return_pct": round(actual, 3),
        "deviation_pct": round(dev, 3),
        "within_0_5": abs(dev) <= 0.5,
        "unattributed_weight_pct": round(100.0 - sum_w, 2),
        "missing_quotes": missing,
        "top_contrib": sorted(rows, key=lambda r: -abs(r["contrib_pct"]))[:5],
    }


def main():
    inp = sys.argv[1] if len(sys.argv) > 1 else None
    if inp and os.path.exists(inp):
        data = json.load(open(inp, encoding="utf-8"))
    else:
        data = json.load(sys.stdin)

    out = {
        "as_of": data.get("as_of"),
        "funds": [penetrate_fund(f) for f in data.get("funds", [])],
    }

    print(f"# 场内穿透结果（as_of={data.get('as_of')}）\n")
    print("| 基金 | 类型 | 已知权重% | 估算涨幅% | 实际涨幅% | 偏差% | ±0.5? | 未归因% |")
    print("|---|---|---|---|---|---|---|---|")
    for r in out["funds"]:
        flag = "OK" if r["within_0_5"] else "WARN"
        print(
            f"| {r['name']} | {r['type']} | {r['known_weight_pct']} "
            f"| {r['est_return_pct']} | {r['actual_return_pct']} "
            f"| {r['deviation_pct']} | {flag} | {r['unattributed_weight_pct']} |"
        )

    out_path = "penetrate_output.json"
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)
    print(f"\n-> 已写 {out_path}")


if __name__ == "__main__":
    main()
