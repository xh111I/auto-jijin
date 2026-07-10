# src/analyzers/tail.py
# 尾盘决策引擎: 场景分类 + 止盈锁本评估 + 操作信号生成。
# 纯函数设计, 输入数据对象, 输出决策对象, 可直接单元测试。

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

# ---- 场景分类 ----

def classify_scenario(
    baseline: dict, current: dict, indices: list = None
) -> Tuple[str, str]:
    """根据14:30基准与14:45实时对比，分类尾盘场景。
    baseline/current 各含: {指数: {chg_pct, vol_ratio, above_ma}}
    返回: (scenario_key, scenario_label)
    """
    if not baseline or not current:
        return ("indeterminate", "缩量震荡(无基准数据,默认观望)")
    
    target = indices or ["创业板指", "科创50", "沪深300"]
    chg_delta = 0
    vol_avg = 0
    ma_ok = 0
    
    for idx in target:
        b = baseline.get(idx, {})
        c = current.get(idx, {})
        if b and c:
            chg_delta += c.get("chg_pct", 0) - b.get("chg_pct", 0)
            vol_avg += c.get("vol_ratio", 1)
            if c.get("above_ma"):
                ma_ok += 1
    
    n = len(target)
    avg_chg = chg_delta / n if n > 0 else 0
    avg_vol = vol_avg / n if n > 0 else 1
    ma_ratio = ma_ok / n if n > 0 else 0.5
    
    # 放量拉升: 尾盘涨幅>1%, 量比>1.2, 站上均线
    if avg_chg > 1.0 and avg_vol > 1.2 and ma_ratio > 0.5:
        return ("surge", "放量拉升 · 盈利持有不动,不追高加仓仅留底仓")
    
    # 放量跳水: 跌幅>1%, 量比>3, 跌破均线
    if avg_chg < -1.0 and avg_vol > 3.0 and ma_ratio < 0.5:
        return ("plunge", "放量跳水 · 高仓位/高盈利减仓1/3锁利,弱势止损降仓")
    
    # 缩量震荡: 高低点价差<1%, 量较日内萎缩50%
    # 简化: 涨幅幅度<0.5%且量比<0.8
    if abs(avg_chg) < 0.5 and avg_vol < 0.8:
        return ("range", "缩量震荡 · 维持原有仓位,等次日方向")
    
    # 板块分化
    return ("divergence", "板块分化 · 不盲目减仓,观察持续性次日再调仓")


# ---- 止盈锁本评估 ----

def evaluate_profit_lock(holding: dict, score: float) -> Tuple[str, str, Optional[float]]:
    """根据持仓收益+规则评估止盈/止损操作。
    holding: {name, return_pct, profit_lock: {stages[]: {trigger_pct, action_pct, action}}}
    返回: (action, reason, suggested_sell_pct)
    """
    name = holding.get("name", "")
    ret = holding.get("return_pct", 0)
    profit_lock = holding.get("profit_lock", {})
    
    # 硬止损: 跌破-8%
    if ret <= -0.08:
        return ("sell_100", f"{name} 触发-8%硬止损(当前{ret*100:.1f}%)", 100)
    
    # 阶梯止盈
    stages = profit_lock.get("stages", [])
    for stage in sorted(stages, key=lambda s: s.get("trigger_pct", 999)):
        trigger = stage.get("trigger_pct", 0)
        action_pct = stage.get("action_pct", 0)
        action = stage.get("action", "hold")
        if ret >= trigger / 100:  # trigger_pct 是百分比(如20=20%)
            return (action, f"{name} 触发{trigger}%阶梯止盈: {action}({action_pct}%)", action_pct)
    
    # 回撤保护
    high_water = holding.get("peak_return_pct") or ret
    drawdown = high_water - ret
    if drawdown > 0.05:  # 从高点回撤>5%
        return ("reduce_50", f"{name} 从高点回撤{drawdown*100:.1f}% >5%阈值, 减仓50%", 50)
    
    return ("hold", f"{name} 正常持有(收益{ret*100:.1f}%)", None)


# ---- 操作信号生成 ----

@dataclass
class TailSignal:
    fund_name: str
    action: str       # buy|sell|hold|reduce|wait
    target_weight: float
    reason: str
    urgency: str      # high|medium|low

def generate_tail_signals(holdings: list, scenario: str, strategy: dict) -> List[TailSignal]:
    """根据场景分类+持仓+策略生成每持仓操作信号。"""
    signals = []
    max_single = strategy.get("max_single_position_pct", 30)
    stop_loss = strategy.get("stop_loss_pct", -8) / 100
    
    for h in holdings:
        name = h.get("name", "")
        wt = h.get("weight_pct", 0)
        ret = h.get("return_pct", 0)
        status = h.get("status", "active")
        
        if status != "active":
            continue
        
        # 权重超限
        if wt > max_single:
            signals.append(TailSignal(name, "reduce", max_single, 
                f"权重{wt:.1f}% 超{max_single}%上限", "high"))
            continue
        
        # 止损
        if ret <= stop_loss:
            signals.append(TailSignal(name, "sell", 0,
                f"触发{stop_loss*100:.0f}%硬止损(当前{ret*100:.1f}%)", "high"))
            continue
        
        # 场景联动
        if scenario == "surge":
            if ret > 0.15:
                signals.append(TailSignal(name, "reduce", wt * 0.7,
                    f"放量拉升+高盈利{ret*100:.1f}%, 减30%锁利", "medium"))
            else:
                signals.append(TailSignal(name, "hold", wt,
                    "放量拉升·持有不动", "low"))
        elif scenario == "plunge":
            signals.append(TailSignal(name, "reduce", wt * 0.67,
                f"放量跳水, 减仓1/3规避次日低开", "high"))
        elif scenario == "range":
            signals.append(TailSignal(name, "hold", wt,
                "缩量震荡·维持原仓位", "low"))
        else:
            signals.append(TailSignal(name, "hold", wt,
                "板块分化·观察等待", "medium"))
    
    return signals
