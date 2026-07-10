# src/analyzers/morning.py
# 早间全球分析引擎: 海外影响评估 + 持仓盘前指引风险评分。
from typing import List, Dict, Tuple

def assess_overseas_impact(overseas: dict, holdings: list) -> dict:
    """评估隔夜海外市场对A股持仓的传导影响。
    overseas: {美股纳指/标普/SOX/费半: chg_pct, 原油/铜/黄金: chg_pct, 美元指数: chg_pct}
    返回: {impact_score(-10~10), risk_events: [{level, fact, channel, impact}]}
    """
    score = 0
    events = []
    
    # 纳指 + SOX → 科技/AI/半导体
    nasdaq = overseas.get("纳指", 0)
    sox = overseas.get("费城半导体", 0)
    if nasdaq < -1 and sox < -2:
        events.append({"level": "red", "fact": f"纳指{nasdaq:.1f}%+SOX{sox:.1f}%双杀",
                       "channel": "AI/半导体情绪传导", "impact": "持仓半导体面临开盘承压"})
        score -= 3
    elif nasdaq > 1 or sox > 2:
        score += 2
    
    # 原油 → 成本端/通胀预期
    oil = overseas.get("原油", 0)
    if abs(oil) > 3:
        events.append({"level": "orange", "fact": f"原油波动{oil:.1f}%",
                       "channel": "通胀预期/成本端", "impact": "宏观不确定性增加"})
        score -= 1 if oil < -3 else 0
    
    # 美元+汇率
    dxy = overseas.get("美元指数", 0)
    if abs(dxy) > 0.5:
        events.append({"level": "yellow", "fact": f"美元指数变动{dxy:.2f}%",
                       "channel": "北向资金流向预期", "impact": "关注北向开盘动向"})
    
    # VIX恐慌指数
    vix = overseas.get("VIX", 20)
    if vix > 30:
        events.append({"level": "red", "fact": f"VIX={vix:.0f}恐慌区间",
                       "channel": "全球风险偏好骤降", "impact": "防御仓位(债基)价值上升"})
        score -= 2
    
    return {"impact_score": max(-10, min(10, score)), "risk_events": events}


def generate_morning_guidance(holdings: list, overseas_impact: dict,
                               strategy: dict) -> List[dict]:
    """为每持仓生成盘前指引。
    返回: [{name, attention_level(高/中/低), points: [关注点], action_hint}]
    """
    guidance = []
    stop_loss = strategy.get("stop_loss_pct", -8) / 100
    impact_score = overseas_impact.get("impact_score", 0)
    
    for h in holdings:
        name = h.get("name", "")
        sector = h.get("sector", "")
        ret = h.get("return_pct", 0)
        wt = h.get("weight_pct", 0)
        points = []
        level = "低"
        
        # 止损逼近
        distance_to_stop = ret - stop_loss
        if distance_to_stop < 0.02:
            points.append(f"⚠️ 距-8%硬止损仅{distance_to_stop*100:.1f}%")
            level = "高"
        
        # 海外传导
        if "半导体" in sector and impact_score < -1:
            points.append("隔夜SOX/纳指承压,开盘关注半导体板块低开幅度")
            level = "高"
        elif "医药" in sector and impact_score > 0:
            points.append("隔夜海外映射偏暖,关注创新药联动")
        
        # 权重超限
        max_wt = strategy.get("max_single_position_pct", 30)
        if wt > max_wt * 0.9:
            points.append(f"权重{wt:.1f}%逼近{max_wt}%上限,今日若冲高可减至≤{max_wt}%")
            level = "高"
        
        # 盈利锁本提示
        if ret > 0.10:
            points.append(f"收益{ret*100:.1f}%,注意阶梯止盈(从profit_lock_rules匹配)")
            level = max(level, "中")
        
        guidance.append({
            "name": name,
            "attention_level": level,
            "points": points or [f"{name}: 无特殊信号,维持原策略"],
            "action_hint": "持有观望" if level == "低" else ("关注" if level == "中" else "准备操作")
        })
    
    return guidance
