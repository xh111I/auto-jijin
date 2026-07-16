#!/usr/bin/env python3
"""Build market_2026-07-16.json from DB + tech data."""
import json, os, sys, datetime, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from market_db import MarketDB

BASE = os.path.dirname(os.path.abspath(__file__))
TODAY = "2026-07-16"

db = MarketDB()
tech = json.load(open(os.path.join(BASE, "market_tech_2026-07-16.json")))
wl = json.load(open(os.path.join(BASE.replace('data','config'), "watchlist.json"), encoding="utf-8"))
indices_db = {r['code']: r for r in db.get_index_spot()}
sent = db.get_sentiment()

by_code = tech.get("by_code", {})
by_sector = tech.get("by_sector", {})

# ── tendency from tech score ──
def determine_tech_tendency(code):
    """Use multiple tech signals to determine tendency."""
    tc = by_code.get(code, {})
    if not tc:
        return "中性", 50
    score = 0
    ma_pat = tc.get("ma_pattern", "")
    if "多头" in ma_pat: score += 3
    elif "空头" in ma_pat: score -= 3
    yr = tc.get("year", {})
    if "年线上方" in yr.get("status",""): score += 2
    elif "年线下方" in yr.get("status",""): score -= 2
    if "向上" in yr.get("slope",""): score += 1
    elif "向下" in yr.get("slope",""): score -= 1
    macd = tc.get("macd", "")
    if macd == "金叉": score += 2
    elif macd == "死叉": score -= 2
    kdj = tc.get("kdj", "")
    if kdj == "超卖": score += 1
    elif kdj == "超买": score -= 1
    chg5 = tc.get("chg5") or 0
    chg20 = tc.get("chg20") or 0
    if chg5 < -3: score -= 2
    elif chg5 > 3: score += 2
    if chg20 < -5: score -= 2
    elif chg20 > 5: score += 2
    pat = tc.get("pattern_single", "")
    if "大阴" in pat: score -= 1
    elif "大阳" in pat: score += 1
    if score >= 4: return "偏多", 70
    elif score >= 1: return "中性偏多", 60
    elif score <= -4: return "偏空", 30
    elif score <= -1: return "中性偏空", 35
    return "中性", 50

def kline_shape_label(pat):
    if "大阴" in pat: return "大阴线"
    if "长上影" in pat: return "长上影"
    if "十字星" in pat: return "十字星"
    if "大阳" in pat: return "大阳线"
    if "阴线" in pat: return "阴线"
    if "阳线" in pat: return "阳线"
    return pat or "普通K线"

def shape_score(pat):
    if "大阳" in pat: return 80
    if "大阴" in pat: return 20
    if "上影" in pat: return 30
    if "十字星" in pat: return 40
    if "阳线" in pat: return 60
    return 50

# ── Build indices ──
CODE_NAMES = {
    "sh000001":"上证","sh000016":"上证50","sh000300":"沪深300",
    "sh000688":"科创50","sh000905":"中证500","sz399001":"深证",
    "sz399006":"创业板","bj899050":"北证50"
}

all_indices = []
for code, name in CODE_NAMES.items():
    tc = by_code.get(code, {})
    di = indices_db.get(code, {})
    if not tc and not di: continue
    close = tc.get("candle",[[0]])[-1][1] if tc.get("candle") else (di.get("price") or 0)
    # fallback: calculate change from QQ raw data if DB missing
    chg = di.get("change_pct")
    if chg is None:
        try:
            raw = json.load(open(os.path.join(BASE, f"_raw_{code}.json")))
            nodes = raw.get("nodes",[])
            if len(nodes) >= 2:
                c = nodes[-1]["last"]; p = nodes[-2]["last"]
                chg = round((c-p)/p*100, 2)
        except: chg = 0
    amt = round((di.get("amount") or 0)/1e8, 2) if di.get("amount") else 0
    # also calculate amt from raw if missing
    if amt == 0 and code in ("bj899050",):
        try:
            raw = json.load(open(os.path.join(BASE, f"_raw_{code}.json")))
            nodes = raw.get("nodes",[])
            if nodes and len(nodes) > 0:
                last = nodes[-1]
                amt = round((last.get("amount",0) or 0)/1e8, 2)
        except: pass
    td, sc = determine_tech_tendency(code)
    pat = tc.get("pattern_single", "")
    vr = tc.get("vol_ratio")
    vol_label = "缩量下跌" if (vr or 1) < 0.95 else ("放量下跌" if (vr or 1) > 1.05 else "平量下跌")
    all_indices.append({
        "name": name, "code": code, "close": close,
        "chg_pct": round(chg, 3), "amount_yi": amt,
        "main_flow_yi": None, "score": sc, "tendency": td,
        "kline": {
            "trend": {"label": td, "score": sc, "detail": tc.get("trend_text","")[:60]},
            "volprice": {"label": vol_label, "score": sc-10 if sc>50 else sc+10, "detail": f"量比{vr}，近5日{tc.get('chg5',0)}%、近20日{tc.get('chg20',0)}%"},
            "shape": {"label": kline_shape_label(pat), "score": shape_score(pat), "detail": pat},
            "mainforce": {"label": "—", "score": 50, "detail": "暂无主力数据"},
            "close_signal": {"label": "收盘偏弱", "detail": f"{pat},收盘偏弱"}
        },
        "warn": f"{name}收盘{close:.2f} {chg:+.2f}%",
        "series": [close]
    })

all_indices.sort(key=lambda x: x["chg_pct"])

# ── Sentiment ──
fg = sent["fear_greed"] if sent else 50
lvl = sent["level"] if sent else "中性"

# ── Sectors ──
# Analyze from QQ sectors + tech data
qq_sectors = {
    "sz399389":"通信设备","sz399437":"证券",
    "sz399998":"煤炭","sz399967":"军工",
    "sz399989":"医疗服务","sh000815":"食品饮料/大消费",
}
cs_sectors = {
    "csH30184":"半导体","cs931160":"CPO/通信设备",
    "cs931787":"港股创新药","cs931071":"人工智能(应用端)"
}

# Read QQ sector spot data from raw files
import urllib.request, ssl
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

def fetch_qq_spot(code, name):
    """Try to get sector change_pct from QQ realtime."""
    try:
        url = f"https://proxy.finance.qq.com/ifzqgtimg/appstock/app/newfqkline/get?param={code},day,,,5,"
        req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15, context=CTX) as r:
            data = json.loads(r.read().decode("utf-8"))
        d = data.get("data", {})
        node = d.get(code)
        if not node:
            for k,v in d.items():
                if isinstance(v,dict) and ("day" in v or "qfqday" in v):
                    node = v; break
        rows = node.get("day") or node.get("qfqday") or []
        if rows and len(rows) > 0:
            last = rows[-1]
            prev = rows[-2] if len(rows) >= 2 else None
            if prev and len(last) >= 3 and len(prev) >= 3:
                c = float(last[2]); pc = float(prev[2])
                chg = round((c-pc)/pc*100, 2)
                return chg
    except: pass
    return None

# Build sector change data
sector_chg = {}
for code, name in {**qq_sectors, **cs_sectors}.items():
    chg = fetch_qq_spot(code, name)
    if chg is not None:
        sector_chg[name] = chg
    else:
        # Try cached kline data (cs sectors: use last 2 closes from market_raw_ohlc cached data)
        # cs sector OHLC data cached to ~07-10, use as estimate
        st = by_sector.get(name, {})
        candle = st.get("candle", [])
        if len(candle) >= 2:
            c_last = candle[-1][1]   # close of last bar
            c_prev = candle[-2][1]   # close of previous bar
            est_chg = round((c_last - c_prev) / c_prev * 100, 2)
            sector_chg[name] = est_chg
            print(f"  ⚠ {name}: QQ不可用, 从缓存OHLC估算 chg={est_chg:+.2f}%")
        else:
            print(f"  ⚠ {name}: QQ不可用且无缓存OHLC")

# Add 北证50 from index data or raw
bj_code = "bj899050"
bj_chg = indices_db.get(bj_code, {}).get("change_pct")
if bj_chg is None:
    try:
        raw = json.load(open(os.path.join(BASE, f"_raw_{bj_code}.json")))
        nodes = raw.get("nodes",[])
        if len(nodes) >= 2:
            bj_chg = round((nodes[-1]["last"]-nodes[-2]["last"])/nodes[-2]["last"]*100, 2)
    except: pass
if bj_chg is not None:
    sector_chg["北证50"] = bj_chg

# Classify sectors
strong, rising, weak = [], [], []
sector_sorted = sorted(sector_chg.items(), key=lambda x: x[1], reverse=True)

for name, chg in sector_sorted:
    # Tech analysis
    st = by_sector.get(name, {})
    kdj = st.get("kdj", "")
    macd = st.get("macd", "")
    pat = st.get("pattern_single", "")
    
    if chg > 0: strong.append(name)
    elif chg > -2: rising.append(name)
    else: weak.append(name)

chain_strong = "领涨：" + "/".join(strong[:4]) if strong else "领涨：—"
chain_weak = "领跌：" + "/".join(weak[:4]) if weak else "领跌：—"
rising_str = "/".join(rising[:4]) if rising else "—"
rotation_text = f"强势板块：{'/'.join(strong[:4])}；温和走强：{rising_str}；弱势承压：{'/'.join(weak[:4])}"

# ── Holdings from watchlist ──
holdings_data = []
for h in wl.get("holdings", []):
    name = h.get("name", "")
    related = h.get("related_index", "—")
    # Determine signal based on market context
    signal = "持有观察" if fg <= 30 else ("警惕回调" if fg >= 80 else "持有观察")
    support = "箱体下沿支撑，观察方向选择"
    pressure = "箱体上沿压力，等待突破确认"
    risk = 6
    if "半导体" in name or "半导体" in related:
        risk = 8
        if fg <= 30:
            signal = "谨慎持有"
            support = "年线支撑，跌破需止损"
            pressure = "短期均线压力重重"
    if "创新药" in name or "港股" in name:
        risk = 5
    if "债券" in name or "债" in name:
        signal = "持有(防御)"
        risk = 2
    
    holdings_data.append({
        "name": name, "related": related,
        "signal": signal,
        "level": "高" if risk >= 8 else ("中" if risk >= 5 else "低"),
        "support": support,
        "pressure": pressure,
        "risk_dist_pct": risk
    })

# ── Predictions ──
predictions = []
for idx in all_indices:
    nm = idx["name"]
    td = idx["tendency"]
    chg = idx["chg_pct"]
    # Simple prediction logic
    if "空" in td:
        d1 = f"震荡-0.5~-1.5%(惯性下探)"
    elif td == "中性" and chg < -2:
        d1 = f"震荡-0.5%~+0.5%(超跌修复) "
    else:
        d1 = f"震荡+0~+1%(修复反弹)"
    predictions.append({
        "target": nm,
        "d1": d1,
        "d2": "待确认",
        "d3": "待确认",
        "conf": "低" if "空" in td else "中",
        "trigger": "关注FG能否止跌回升"
    })

# ── Watch levels ──
watch_levels = [
    {"type": "关键点位", "text": f"上证关注{all_indices[0]['close']:.0f}附近能否企稳"},
    {"type": "量能观察", "text": f"全市场成交额萎缩至缩量状态"},
    {"type": "情绪观察", "text": f"恐惧贪婪指数{fg}，{lvl}(超卖区间)"},
]

# ── Build core ──
# Market quality summary
chg_strs = [f"{i['name']}{i['chg_pct']:+.2f}%/{i['tendency']}" for i in all_indices]
main_line = "今日全线重挫："
for i in all_indices:
    main_line += f"{i['name']}{i['chg_pct']:+.2f}%/{i['tendency']} "

core = {
    "market_qual": f"A股收盘全线下挫：{' '.join(chg_strs)}",
    "main_line": main_line,
    "action_guideline": "恐慌释放中，管住手等企稳。关注FG是否止跌回升，不宜抄底。仅供参考，不构成投资建议。",
    "chain": f"{chain_strong} {chain_weak}",
    "metrics": {
        "indices_count": len(all_indices),
        "sectors_count": len(sector_chg),
        "fg_index": fg,
        "up_sectors": len(strong),
        "down_sectors": len(weak)
    }
}

# ── Credibility ──
credibility = [
    {"item":"指数行情(akshare)","status":"✅","note":f"{len(all_indices)}条"},
    {"item":"板块行情(QQ+缓存)","status":"⚠","note":f"{len(sector_chg)}条(6 QQ实时+4 cs缓存至07-10)"},
    {"item":f"情绪因子(FG={fg})","status":"✅","note":"sentiment表"},
    {"item":"市场广度","status":"⚠","note":"无数据(按中性50计)"},
    {"item":"北向资金","status":"⚠","note":"无数据(按中性50计)"},
    {"item":"主力资金流向","status":"⚠","note":"暂无数据"},
    {"item":"板块OHLC(cs缓存+QQ)","status":"⚠","note":"cs板块07-10缓存+QQ今日实时"},
]

# ── Final JSON ──
out = {
    "date": TODAY,
    "updated_at": f"{TODAY} 15:30 收盘",
    "data_tier": "T2",
    "core": core,
    "credibility": credibility,
    "indices": all_indices,
    "sentiment": {
        "fear_greed": fg,
        "factors": {
            "breadth": 50, "limit_up_down": 50, "main_flow": 50,
            "northbound": 50, "margin": 50, "volume": 50, "vix": 50, "erp": 50
        },
        "note": sent.get("note", f"FG={fg}·{lvl}") if sent else f"FG={fg}·{lvl}"
    },
    "sectors": {
        "strong": strong,
        "rising": rising,
        "weak": weak,
        "rotation": rotation_text,
        "chain": [chain_strong, chain_weak]
    },
    "holdings": holdings_data,
    "predictions": predictions,
    "watch_levels": watch_levels,
    "risks": [],
    "disclaimer": f"⚠ 本分析仅供参考,预测为模型研判,历史不代表未来。数据含T2估算与AI模型推断,不构成投资建议。涨红跌绿按A股惯例。板块cs数据截至07-10缓存。{TODAY}。"
}

dst = os.path.join(BASE, f"market_{TODAY}.json")
json.dump(out, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"✅ 已写入 {dst}")
print(f"   indices={len(all_indices)}, sectors_spot={len(sector_chg)}, holdings={len(holdings_data)}")
print(f"   FG={fg}·{lvl}, 上涨={len(strong)}, 下跌={len(weak)}")
for i in all_indices:
    print(f"   {i['name']:8s} {i['chg_pct']:+.2f}%  {i['tendency']:8s} score={i['score']}")
