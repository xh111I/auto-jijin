# src/analyzers/market.py
# 大盘·板块·日K研判引擎：指数五维分析 + 板块排序 + 次日预测。
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

# ---- 日K五维研判 ----
@dataclass
class KlineDiagnosis:
    index_code: str
    name: str
    trend: str          # 趋势判定
    volume_signal: str  # 量价信号
    pattern: str        # K线形态
    main_force: str     # 主力意图
    close_signal: str   # 收盘暗号
    bias: str           # "偏多"|"偏空"|"中性"
    score: int          # 0-10

def analyze_kline(index_code: str, name: str, data: dict) -> KlineDiagnosis:
    """对单个指数做五维日K研判。
    data: {price, change_pct, volume, turnover, ma20, ma60,
           open, high, low, close, main_net_inflow}
    """
    price = data.get("price", 0)
    chg = data.get("change_pct", 0)
    ma20 = data.get("ma20", price)
    ma60 = data.get("ma60", price)
    inflow = data.get("main_net_inflow") or 0
    
    # 1. 趋势
    above_ma20 = price > ma20 if ma20 else None
    above_ma60 = price > ma60 if ma60 else None
    if above_ma20 and above_ma60 and ma20 > ma60:
        trend = "多头排列(MA20>MA60,价站双线)"
    elif not above_ma20 and not above_ma60 and ma20 < ma60:
        trend = "空头排列"
    else:
        trend = "震荡整理"
    
    # 2. 量价
    vol = data.get("volume", 0)
    vol_avg = data.get("vol_5avg") or vol
    vol_ratio = vol / vol_avg if vol_avg > 0 else 1
    if chg > 0 and vol_ratio > 1.5:
        volume_signal = "放量上涨(增量资金入场)"
    elif chg < -1 and vol_ratio > 2:
        volume_signal = "放量下跌(恐慌抛售)"
    elif abs(chg) < 0.5 and vol_ratio < 0.6:
        volume_signal = "缩量窄幅(方向选择前兆)"
    else:
        volume_signal = "量价正常"
    
    # 3. K线形态
    o, h, l, c = data.get("open", price), data.get("high", price), data.get("low", price), data.get("close", price)
    body = abs(c - o)
    upper = h - max(c, o)
    lower = min(c, o) - l
    if body > 0 and lower > body * 2 and upper < body * 0.5:
        pattern = "锤子线(下影>实体2倍,可能见底)"
    elif body > 0 and upper > body * 2 and lower < body * 0.5:
        pattern = "射击之星(上影>实体2倍,可能见顶)"
    elif chg > 1.5 and c >= h * 0.998:
        pattern = "光头阳线(强势)"
    elif chg < -1.5 and c <= l * 1.002:
        pattern = "光脚阴线(弱势)"
    else:
        pattern = "普通K线"
    
    # 4. 主力意图
    if inflow > 0:
        if chg > 0:
            main_force = "主动流入(拉升特征)"
        else:
            main_force = "逆势流入(护盘/吸筹)"
    elif inflow < 0:
        if chg < 0:
            main_force = "主动流出(出货特征)"
        else:
            main_force = "逆势流出(拉高出货)"
    else:
        main_force = "主力观望"
    
    # 5. 收盘信号
    if chg > 0 and c > o and c > (h + l) / 2:
        close_signal = "多头强势收盘"
    elif chg < 0 and c < o and c < (h + l) / 2:
        close_signal = "空头主导收盘"
    else:
        close_signal = "中性收盘"
    
    # 综合评分
    score = 5
    if "多头" in trend: score += 2
    elif "空头" in trend: score -= 2
    if "上涨" in volume_signal: score += 1
    elif "下跌" in volume_signal: score -= 2
    if "见底" in pattern or "阳线" in pattern: score += 1
    elif "见顶" in pattern or "阴线" in pattern: score -= 1
    if "流入" in main_force and "逆势" not in main_force: score += 1
    elif "流出" in main_force and "逆势" not in main_force: score -= 1
    score = max(0, min(10, score))
    
    bias = "偏多" if score > 6 else ("偏空" if score < 4 else "中性")
    
    return KlineDiagnosis(
        index_code=index_code, name=name, trend=trend, volume_signal=volume_signal,
        pattern=pattern, main_force=main_force, close_signal=close_signal, bias=bias, score=score
    )

# ---- 板块强弱排序 ----
def rank_sectors(sector_data: List[dict]) -> List[dict]:
    """按综合强度排序板块。
    sector_data: [{name, chg_pct, main_net_inflow, turnover_ratio}]
    返回: 按 score 降序排列
    """
    for s in sector_data:
        chg = s.get("chg_pct", 0)
        inflow = (s.get("main_net_inflow") or 0) / 1e8
        turnover = s.get("turnover_ratio", 0)
        s["score"] = round(chg * 2 + (inflow * 0.5 if inflow > 0 else inflow) + turnover * 0.3, 1)
    return sorted(sector_data, key=lambda x: x.get("score", 0), reverse=True)

# ---- 次日预测 ----
@dataclass
class NextDayPrediction:
    index_code: str
    direction: str   # "上涨"|"下跌"|"震荡"
    confidence: str  # "高"|"中"|"低"
    trigger: str     # 关键触发条件

def predict_next_day(diag: KlineDiagnosis, data: dict) -> NextDayPrediction:
    """基于今日日K+历史倾向预测次日方向。"""
    score = diag.score
    chg = data.get("change_pct", 0)
    
    if score >= 7:
        direction, confidence = "上涨", "高" if chg > 0 else "中"
        trigger = f"延续今日强势(T={diag.trend})"
    elif score <= 3:
        direction, confidence = "下跌", "高" if chg < 0 else "中"
        trigger = f"延续弱势({diag.volume_signal})"
    else:
        direction = "震荡" if abs(chg) < 0.5 else ("偏多震荡" if chg > 0 else "偏空震荡")
        confidence = "低"
        trigger = f"方向选择中,关注{diag.pattern}"
    
    return NextDayPrediction(diag.index_code, direction, confidence, trigger)
