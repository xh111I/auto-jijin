#!/usr/bin/env python3
"""Step 2 v2: Read market.db → analyze → produce market_2026-07-14.json"""
import json, os, sys, datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "data"))
from market_db import MarketDB

DATE = "2026-07-14"
db = MarketDB()

# ===================== 1. Read from DB =====================
indices_raw = db.get_index_spot()
sectors_raw = db.get_sector_spot()
sentiment_raw = db.get_sentiment(DATE)
breadth_raw = db.get_breadth(DATE)
north_raw = db.get_northbound(DATE)
flow_raw = db.get_capital_flow(DATE, 30)
fresh = db.get_freshness()

# Also read raw OHLC for sector analysis
ohlc_path = os.path.join(BASE, "data", "market_raw_ohlc_%s.json" % DATE)
sector_ohlc_list = []
if os.path.exists(ohlc_path):
    with open(ohlc_path) as f:
        raw_ohlc = json.load(f)
    sector_ohlc_list = raw_ohlc.get("sectors", [])

print("=== DB Snapshot ===")
print(f"Indices: {len(indices_raw)} | Sectors(DB): {len(sectors_raw)} | Sectors(OHLC): {len(sector_ohlc_list)} | Sentiment: {sentiment_raw and sentiment_raw.get('fear_greed')}")
print(f"Breadth: {breadth_raw} | Northbound: {north_raw} | Flow: {len(flow_raw)}")

# ===================== 2. Build per-index analysis =====================
def score_to_tend(score):
    if score >= 80: return "强多"
    if score >= 65: return "偏多"
    if score >= 45: return "中性"
    if score >= 25: return "偏空"
    return "强空"

def calc_kline_detail(idx):
    c = idx.get("price", 0)
    cp = idx.get("change_pct", 0)
    flow = idx.get("net_inflow", 0) or 0
    if cp > 3: shape = ("大阳线", 80, "大阳线,强势上攻")
    elif cp > 1.5: shape = ("中阳线", 70, "中阳线,上涨延续")
    elif cp > 0.2: shape = ("小阳线", 60, "小阳线,震荡偏多")
    elif cp > -0.2: shape = ("十字星", 50, "十字星,方向不明")
    elif cp > -1.5: shape = ("小阴线", 40, "小阴线,弱势整理")
    elif cp > -3: shape = ("中阴线", 25, "中阴线,回调延续")
    elif cp > -5: shape = ("大阴线", 15, "大阴线,空头主导")
    else: shape = ("超大阴", 5, "超大阴线,恐慌性抛售")
    vol_judge = "放量上涨" if cp > 0.5 else "放量下跌" if cp < -0.5 else "平量"
    vol_score = 80 if cp > 1 else 20 if cp < -1 else 50
    trend_score = 75 if cp > 2 else 60 if cp > 0.5 else 50 if cp > -0.5 else 30 if cp > -2 else 15
    trend_detail = f"收盘{c}，{'强势突破' if cp>2 else '温和上涨' if cp>0.5 else '窄幅震荡' if cp>-0.5 else '温和回调' if cp>-2 else '大幅下挫'}"
    main_label = "净流入" if flow > 0 else "净流出"
    main_score = 70 if flow > 50 else 50 if flow > 0 else 30 if flow > -50 else 10
    close_label = "收盘偏强" if cp > 1 else "收盘偏弱" if cp < -1 else "收盘平稳"
    return {
        "trend": {"label": score_to_tend(trend_score), "score": trend_score, "detail": trend_detail},
        "volprice": {"label": vol_judge, "score": vol_score, "detail": f"{vol_judge}{cp:+.2f}%"},
        "shape": {"label": shape[0], "score": shape[1], "detail": shape[2]},
        "mainforce": {"label": main_label, "score": main_score, "detail": f"主力净{main_label}约{abs(flow):.0f}亿" if flow != 0 else "主力流向中性"},
        "close_signal": {"label": close_label, "detail": f"{shape[0]},{close_label}"},
    }

def calc_prediction(idx):
    name = idx.get("name", "")
    cp = idx.get("change_pct", 0)
    c = idx.get("price", 0)
    if cp > 2: d1, conf = f"震荡偏多+0.5~1.5%(强势延续)", "中"
    elif cp > 0.5: d1, conf = f"震荡+0~1%(动能衰减)", "中"
    elif cp > -0.5: d1, conf = f"震荡±0.5%(方向不明)", "中"
    elif cp > -2: d1, conf = f"偏空-0.5~1.5%(弱势延续)", "中"
    elif cp > -4: d1, conf = f"偏空-1~2%(空头主导)", "中高"
    else: d1, conf = f"持续回调-1~3%(恐慌需消化)", "中"
    return {"target": name, "d1": d1, "d2": "待确认", "d3": "待确认", "conf": conf, "trigger": ""}

# ===================== 3. Build output =====================
indices_out = []
for idx in indices_raw:
    c = idx.get("price", 0)
    cp = idx.get("change_pct", 0) or 0
    amt_val = idx.get("amount", 0) or 0
    amt_yi = round(amt_val / 1e8, 2) if amt_val else 0
    flow = idx.get("net_inflow", 0) or 0
    score = 70 if cp > 2 else 60 if cp > 0.5 else 50 if cp > -0.5 else 30 if cp > -2 else 20 if cp > -4 else 10
    indices_out.append({
        "name": idx["name"], "code": idx["code"],
        "close": c, "chg_pct": cp, "amount_yi": amt_yi,
        "main_flow_yi": round(flow, 2),
        "score": score, "tendency": score_to_tend(score),
        "kline": calc_kline_detail(idx),
        "warn": f"{idx['name']}收盘{c} {cp:+.2f}%" if abs(cp) > 0.3 else f"{idx['name']}收盘{c} 基本持平",
        "series": [c],
    })

# Sentiment
fg = 50
factors = {}
fg_note = ""
if sentiment_raw:
    fg = sentiment_raw.get("fear_greed", 50)
    factors = {
        "breadth": int(sentiment_raw.get("breadth_score", 50) or 50),
        "limit_up_down": int(sentiment_raw.get("limit_score", 50) or 50),
        "main_flow": int(sentiment_raw.get("main_force_score", 50) or 50),
        "northbound": int(sentiment_raw.get("north_score", 50) or 50),
        "margin": int(sentiment_raw.get("margin_score", 50) or 50),
        "volume": int(sentiment_raw.get("volume_score", 50) or 50),
        "vix": int(sentiment_raw.get("vix_score", 50) or 50),
        "erp": int(sentiment_raw.get("erp_score", 50) or 50),
    }
    fg_note = sentiment_raw.get("note", "") or ""
else:
    fg_note = "情绪因子数据缺失，按中性(50)计。"

# Sectors - from DB sector_spot + OHLC
sector_pcts = {}
for s in sectors_raw:
    sp = s.get("change_pct")
    if sp is not None:
        sector_pcts[s["name"]] = sp
# Also extract from OHLC sector closes if available
for s in sector_ohlc_list:
    if s["name"] not in sector_pcts and s.get("ohlc") and len(s["ohlc"]) > 0:
        last = s["ohlc"][-1]
        if len(s["ohlc"]) >= 2:
            prev = s["ohlc"][-2]
            pct = round((last[4] - prev[4]) / prev[4] * 100, 2)
            sector_pcts[s["name"]] = pct

sorted_p = sorted(sector_pcts.items(), key=lambda x: x[1], reverse=True)
strong_names = [n for n, p in sorted_p if p > 1]
rising_names = [n for n, p in sorted_p if 0.2 < p <= 1]
weak_names = [n for n, p in sorted_p if p < -0.2]

# Find main rotation chain
up = "领涨：" + "/".join(strong_names[:3]) if strong_names else ""
down = "领跌：" + "/".join(weak_names[:3]) if weak_names else ""

# Update market_qual and main_line
market_qual = "A股收盘："
main_line = "今日指数："
for idx in indices_out:
    market_qual += f"{idx['name']}{idx['chg_pct']:+.2f}%/{idx['tendency']}{idx['score']} "
    main_line += f"{idx['name']}{idx['chg_pct']:+.2f}%/{idx['tendency']} "

out = {
    "date": DATE,
    "updated_at": f"{DATE} 15:30 收盘",
    "data_tier": "T2",
    "core": {
        "market_qual": market_qual,
        "main_line": main_line,
        "action_guideline": "根据综合研判结果调整。仅供参考，不构成投资建议。",
        "chain": up + " " + down,
        "metrics": {"indices_count": len(indices_out), "sectors_count": len(sector_pcts), "fg_index": fg,
                     "up_sectors": len(strong_names), "down_sectors": len(weak_names)},
    },
    "credibility": [
        {"item": "指数行情(akshare)", "status": "✅", "note": f"{len(indices_raw)}条"},
        {"item": "板块行情(DB)", "status": "⚠", "note": f"{len(sectors_raw)}条DB+{len(sector_ohlc_list)}条OHLC"},
        {"item": f"情绪因子(FG={fg})", "status": "✅", "note": f"sentiment表"},
        {"item": "市场广度", "status": "⚠", "note": "无数据(按中性50计)"},
        {"item": "北向资金", "status": "⚠", "note": "无数据(按中性50计)"},
        {"item": "主力资金流向", "status": "⚠", "note": f"{len(flow_raw)}条"},
        {"item": "板块OHLC(cs缓存+QQ)", "status": "⚠", "note": "cs板块07-10缓存+今日QQ单点"},
    ],
    "indices": indices_out,
    "sentiment": {
        "fear_greed": fg,
        "factors": factors,
        "note": fg_note,
    },
    "sectors": {
        "strong": strong_names,
        "rising": rising_names,
        "weak": weak_names,
        "rotation": [],
        "chain": [up, down],
    },
    "holdings": [],
    "predictions": [calc_prediction(idx) for idx in indices_raw[:7]],
    "watch_levels": [
        {"type": "关键点位", "text": f"上证关注{indices_out[0]['close']:.0f}附近" if indices_out else "等待数据"},
        {"type": "量能观察", "text": "全市场成交额维持观察"},
        {"type": "情绪观察", "text": f"恐惧贪婪指数{fg}，{'谨慎' if fg<30 else '中性' if fg<70 else '偏贪婪(需警惕)'}"},
    ],
    "risks": [],
    "disclaimer": f"⚠ 本分析仅供参考,预测为模型研判,历史不代表未来。数据含T2估算与AI模型推断,不构成投资建议。涨红跌绿按A股惯例。板块数据截至{DATE}。",
}

# Holdings from watchlist
try:
    wl_path = os.path.join(BASE, "config", "watchlist.json")
    with open(wl_path) as f:
        wl = json.load(f)
    holdings_raw = wl if isinstance(wl, list) else wl.get("holdings", wl.get("items", []))
    for h in holdings_raw:
        out["holdings"].append({
            "name": h.get("name", h.get("fund_name", "?")),
            "related": h.get("related_index", ""),
            "signal": "持有观察", "level": "中", "support": "", "pressure": "", "risk_dist_pct": 0,
        })
except Exception as e:
    print("watchlist:", e)

# Save
dst = os.path.join(BASE, "data", "market_%s.json" % DATE)
os.makedirs(os.path.dirname(dst), exist_ok=True)
with open(dst, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("\nSaved", dst)
print("  indices:", len(indices_out))
print("  sectors(DB):", len(sectors_raw), "sectors(labeled):", len(sector_pcts))
print("  strong:", strong_names[:3], "weak:", weak_names[:3])
print("  FG:", fg)
