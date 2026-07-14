#!/usr/bin/env python3
"""Fix main_flow_yi and rotation in market_2026-07-14.json"""
import json, os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DST = os.path.join(BASE, "data", "market_2026-07-14.json")

# 第一次成功获取的东财数据 (f169+f175, 单位: 元×10000 => 万元)
# 东财 f169=超大单 f175=大单, 总主力 = (f169+f175)/10000 (亿元)
MAINFLOW = {
    "sh000001": 35.37,   # 上证: 5334+348338=353672/10000=35.37
    "sh000016": 27.72,   # 上证50: 4236+272991=277227/10000=27.72
    "sh000300": 40.95,   # 沪深300: 10112+399392=409504/10000=40.95
    "sh000688": 10.02,   # 科创50: 1541+98650=100191/10000=10.02
    "sh000905": 61.12,   # 中证500: 13780+597380=611160/10000=61.12
    "sz399001": 110.53,  # 深证: 40202+1065115=1105317/10000=110.53
    "sz399006": 23.17,   # 创业板: 12762+218908=231670/10000=23.17
    "bj899050": 11.42,   # 北证50: 2534+111624=114158/10000=11.42
    # hstech 无数据
}

with open(DST, encoding="utf-8") as f:
    d = json.load(f)

# 1. Fix main_flow_yi
for idx in d["indices"]:
    code = idx.get("code", "")
    if code in MAINFLOW:
        idx["main_flow_yi"] = MAINFLOW[code]
        # Update kline mainforce
        mf = MAINFLOW[code]
        idx["kline"]["mainforce"]["detail"] = f"主力净流入约{mf:.0f}亿"
        idx["kline"]["mainforce"]["label"] = "净流入" if mf > 0 else "净流出"
        idx["kline"]["mainforce"]["score"] = 70 if mf > 50 else 50 if mf > 0 else 30
    else:
        idx["kline"]["mainforce"]["detail"] = "主力数据缺失"
        idx["kline"]["mainforce"]["label"] = "数据缺失"
        idx["kline"]["mainforce"]["score"] = 50

# 2. Fix rotation
strong = d["sectors"].get("strong", [])
rising = d["sectors"].get("rising", [])
weak = d["sectors"].get("weak", [])

rotation = ""
if strong:
    rotation += f"强势板块：{', '.join(strong)}"
if rising:
    rotation += f"；温和走强：{', '.join(rising)}"
if weak:
    rotation += f"；弱势承压：{', '.join(weak)}"
if not rotation:
    rotation = "板块表现分化，资金在强势与弱势板块间轮动，关注量能持续性。"

d["sectors"]["rotation"] = rotation

# 3. Update core
# Rebuild market_qual with main flow
parts = []
for idx in d["indices"]:
    mf = idx.get("main_flow_yi", 0)
    parts.append(f"{idx['name']}{idx['chg_pct']:+.2f}%/{idx['tendency']}(主力{'+' if mf>0 else ''}{mf:.0f}亿)")
d["core"]["market_qual"] = "A股收盘：" + " ".join(parts)

with open(DST, "w", encoding="utf-8") as f:
    json.dump(d, f, ensure_ascii=False, indent=1)

print("Fixed:")
print("  main_flow_yi:", {i["code"]: i["main_flow_yi"] for i in d["indices"]})
print("  rotation:", d["sectors"]["rotation"][:100])
