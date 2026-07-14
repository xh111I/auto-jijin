"""Debug tech_calc tendency scoring."""
import json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath('.')), "data"))
sys.path.insert(0, "data")
from tech_calc import build_tech, load_raw

raw, date = load_raw("2026-07-14")
for rec in raw.get("indices", []):
    code = rec.get("code", "")
    name = rec.get("name", "")
    ohlc = rec.get("ohlc", [])
    if len(ohlc) < 6:
        continue
    closes = [r[4] for r in ohlc]
    highs = [r[2] for r in ohlc]
    lows = [r[1] for r in ohlc]
    vols = [r[5] for r in ohlc]

    from tech_calc import calc_ma, macd_state, kdj_state, pct
    mas, ma_info = calc_ma(ohlc)
    macd = macd_state(closes)
    kdj = kdj_state(highs, lows, closes)
    c = closes[-1]
    chg5 = pct(c, closes[-6])
    chg20 = pct(c, closes[-21])
    y = ma_info["year"]

    score = 0
    reasons = []
    ma_pat = ma_info.get("ma_pattern", "")
    yr_slope = y.get("slope", "")
    yr_status = y.get("status", "")
    if "多头" in ma_pat: score += 2; reasons.append("MA多头+2")
    if "空头" in ma_pat: score -= 2; reasons.append("MA空头-2")
    if "年线上方" in yr_status: score += 1; reasons.append("年线上方+1")
    if "年线下方" in yr_status: score -= 1; reasons.append("年线下方-1")
    if "向上" in yr_slope: score += 0.5; reasons.append("年线向上+0.5")
    if "向下" in yr_slope: score -= 0.5; reasons.append("年线向下-0.5")
    if macd == "金叉": score += 1; reasons.append("MACD金叉+1")
    if macd == "死叉": score -= 1; reasons.append("MACD死叉-1")
    if chg5 is not None and chg5 > 2: score += 1; reasons.append(f"chg5={chg5}+1")
    if chg5 is not None and chg5 < -2: score -= 1; reasons.append(f"chg5={chg5}-1")
    if chg20 is not None and chg20 > 5: score += 0.5; reasons.append(f"chg20={chg20}+0.5")
    if chg20 is not None and chg20 < -5: score -= 0.5; reasons.append(f"chg20={chg20}-0.5")
    if kdj == "超卖": score += 0.5; reasons.append("KDJ超卖+0.5")
    if kdj == "超买": score -= 0.5; reasons.append("KDJ超买-0.5")

    td = "偏多" if score >= 2 else ("偏空" if score <= -2 else "中性")
    print(f"{code} {name:8s} score={score:+.1f} td={td}")
    print(f"  ma_pat={ma_pat} yr={yr_status}/{yr_slope} macd={macd} kdj={kdj} chg5={chg5} chg20={chg20}")
    print(f"  reasons: {', '.join(reasons)}")
    print()
