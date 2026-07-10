# src/analyzers/midday.py
# 午盘分析引擎: 板块↔持仓交叉验证 + 主力阶段判定 + 下午预判。
from typing import List, Dict, Tuple

def cross_validate_sectors(holdings: list, sector_flow: dict, sector_perf: dict) -> list:
    """板块↔持仓交叉验证：流入板块 vs 持仓覆盖板块，标注偏差。
    sector_flow: {板块名: 主力净流入}
    sector_perf: {板块名: 涨跌幅%}
    返回: [{holding_name, sector, covered, flow, perf, confidence}]
    """
    results = []
    all_sectors = set(sector_flow.keys()) | set(sector_perf.keys())
    held_sectors = {h.get("sector", "") for h in holdings if h.get("sector")}
    
    for h in holdings:
        name = h.get("name", "")
        sector = h.get("sector", "")
        xlsx_sectors = str(h.get("xlsx_sector", "")).split("/")
        
        covered = sector in all_sectors
        flow = sector_flow.get(sector, 0)
        perf = sector_perf.get(sector, 0)
        
        # 偏差: 资金流入但不在持仓 → 可能错失
        deviation = ""
        top_inflow = sorted(sector_flow.items(), key=lambda x: x[1], reverse=True)[:3]
        top_sectors = {s for s, _ in top_inflow}
        if not (held_sectors & top_sectors):
            deviation = "持仓板块未进入资金流入前三"
        
        confidence = "高" if covered and flow > 0 and perf > 0 else ("中" if covered else "低")
        
        results.append({
            "fund": name, "sector": sector, "xlsx_sectors": xlsx_sectors,
            "covered": covered, "flow_wan": flow, "perf_pct": perf,
            "deviation": deviation, "confidence": confidence
        })
    return results


def classify_main_force_phase(sector_data: dict) -> str:
    """判定板块主力所处阶段。
    sector_data: {name, chg_5d(5日涨幅), flow_5d(5日净流入), price_pos(现价历史分位)}
    返回: "吸筹"|"洗盘"|"拉升"|"出货"
    """
    flow = sector_data.get("flow_5d", 0)
    chg = sector_data.get("chg_5d", 0)
    pos = sector_data.get("price_pos", 50)  # 历史分位 0-100
    
    if flow > 0 and chg < 0:
        return "吸筹(资金逆势流入+价格下跌)"
    elif flow > 0 and chg > 5:
        return "拉升(量价齐升)"
    elif flow < 0 and chg > 5:
        return "出货(价格涨但资金流出)"
    elif flow < 0 and chg < -3:
        return "观望/洗盘(缩量下跌)"
    elif abs(flow) < 0.1 * abs(chg) if chg != 0 else True:
        return "横盘整理(量能低迷)"
    return "震荡(方向不明)"


def afternoon_preview(indices: dict, sectors: list, sentiment: float) -> dict:
    """下午走势预判三栏矩阵。
    返回: {market_bias, key_sectors: [{name, direction, logic, confidence, trigger}]}
    """
    bias = 0
    for idx_data in indices.values():
        chg = idx_data.get("change_pct", 0)
        vol_ratio = idx_data.get("vol_ratio", 1)
        above_ma = idx_data.get("above_ma", True)
        bias += (1 if chg > 0 else -1) * (1.5 if vol_ratio > 1.2 else 1) * (1.2 if above_ma else 0.8)
    
    market_bias = "偏多" if bias > 1 else ("偏空" if bias < -1 else "中性")
    
    key_sectors = []
    for s in sectors[:5]:
        dir_s = "延续强势" if s.get("chg_pct", 0) > 0 else ("反弹" if s.get("flow_wan", 0) > 0 else "延续弱势")
        key_sectors.append({
            "name": s.get("name", ""),
            "direction": dir_s,
            "logic": f"主力{'流入' if s.get('flow_wan',0)>0 else '流出'}{abs(s.get('flow_wan',0)):.0f}万 涨{s.get('chg_pct',0):.1f}%",
            "confidence": "高" if abs(s.get("chg_pct", 0)) > 1 and abs(s.get("flow_wan", 0)) > 100 else "中",
            "trigger": f"量比{s.get('vol_ratio',1):.1f}"
        })
    
    return {"market_bias": market_bias, "sentiment": sentiment, "key_sectors": key_sectors}
