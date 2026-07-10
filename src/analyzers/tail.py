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


# ---- 涨因/跌因归因 (新增) ----

@dataclass
class RiseCause:
    cause_type: str      # "预期点燃"|"政策落地"|"技术反弹"|"资金轮动"
    label: str
    confidence: str      # 高/中/低
    evidence: list       # 证据链
    implication: str     # 对持仓的含义


def diagnose_rise_cause(market_data: dict, news: list, flow_data: dict) -> RiseCause:
    """诊断上涨原因: 是预期驱动还是实质利好?
    market_data: {指数: {chg_pct, vol_ratio, up_down_ratio(涨跌比)}}
    news: [{title, content, impact}]
    flow_data: {main_net_inflow(主力净流入), northbound_inflow(北向), sector_inflow_top5}
    返回: RiseCause
    """
    evidence = []
    chg = market_data.get("沪深300", {}).get("chg_pct", 0)
    vol_ratio = market_data.get("沪深300", {}).get("vol_ratio", 1)
    up_down = market_data.get("全市场", {}).get("up_down_ratio", 1)
    main_inflow = flow_data.get("main_net_inflow", 0)
    nb_inflow = flow_data.get("northbound_inflow", 0)
    
    has_policy = any("公告" in str(n) or "印发" in str(n) or "发布" in str(n) or "落地" in str(n) for n in news)
    has_rumor = any("传闻" in str(n) or "预期" in str(n) or "或将" in str(n) or "可能" in str(n) for n in news)
    prior_drop = market_data.get("连跌", {}).get("days", 0)
    
    # 政策落地: 大额北向+普涨+正式公告
    if has_policy and nb_inflow > 50 and up_down > 3:
        evidence = [f"北向净流入{nb_inflow:.0f}亿", f"涨跌比{up_down:.1f}:1普涨", "有正式政策文件"]
        return RiseCause("政策落地", "实质利好,关注持续性", "高", evidence,
                        "若利好覆盖半导体/AI, 持仓可持有甚至加仓;若利好在其他板块, 则为间接利好")
    
    # 预期点燃: 有传闻/预期但无正式文件
    if has_rumor or (chg > 1 and 1.2 <= vol_ratio <= 2.5 and up_down < 3):
        evidence = ["量比1.2-2.5(预期驱动特征)", f"涨跌比{up_down:.1f}:1(非普涨)",
                   f"北向试探性流入{nb_inflow:.0f}亿" if nb_inflow > 0 else "北向观望"]
        return RiseCause("预期点燃", "情绪驱动,次日需验证是否兑现", "中", evidence,
                        "不建议尾盘追高;若为持仓板块,可持有观察;若非持仓板块,等待正式落地再介入")
    
    # 技术性反弹: 无催化+前几日连跌+缩量
    if prior_drop >= 3 and vol_ratio < 0.8 and main_inflow < 100:
        evidence = [f"连跌{prior_drop}日后反弹", f"量比{vol_ratio:.1f}(缩量)", "无基本面催化"]
        return RiseCause("技术反弹", "超跌反弹,非趋势反转", "中", evidence,
                        "反弹不追;若持仓中深套, 趁反弹减仓降成本;若空仓, 等放量确认再进")
    
    # 资金轮动流入
    evidence = ["主力净流入但非板块自身利好", "可能为其他板块资金溢出"]
    return RiseCause("资金轮动", "被动轮动,谨慎追高", "低", evidence,
                    "被动流入持续性通常差;观察2-3日确认资金是否沉淀再决定")


@dataclass 
class FallCause:
    cause_type: str
    label: str
    confidence: str
    evidence: list
    implication: str


def diagnose_fall_cause(market_data: dict, news: list, flow_data: dict,
                         safe_haven_flow: float = 0) -> FallCause:
    """诊断下跌原因及资金去向。
    safe_haven_flow: 债市/货基/逆回购当日净流入(亿元), >50表示明显避险
    """
    evidence = []
    chg = market_data.get("沪深300", {}).get("chg_pct", 0)
    vol_ratio = market_data.get("沪深300", {}).get("vol_ratio", 1)
    up_down = market_data.get("全市场", {}).get("up_down_ratio", 1)
    main_outflow = abs(flow_data.get("main_net_inflow", 0)) if flow_data.get("main_net_inflow", 0) < 0 else 0
    nb_outflow = abs(flow_data.get("northbound_inflow", 0)) if flow_data.get("northbound_inflow", 0) < 0 else 0
    vix = market_data.get("VIX", 20)
    
    has_shock = any("突发" in str(n) or "暴跌" in str(n) or "地缘" in str(n) or "制裁" in str(n) for n in news)
    
    # 系统性避险: 全市场普跌+债市大额流入+VIX飙升+北向全出
    if chg < -2 and safe_haven_flow > 50 and vix > 28 and up_down < 0.5:
        evidence = [f"VIX={vix:.0f}(恐慌区间)", f"债市/货基流入{safe_haven_flow:.0f}亿",
                   f"涨跌比{up_down:.1f}:1(普跌)", f"北向净流出{nb_outflow:.0f}亿"]
        return FallCause("系统性避险", "系统性risk-off,立即降仓", "高", evidence,
                        "全面降仓至≤5成;半导体集中度极高是致命风险;债基防御仓位不动")
    
    # 政策/外围冲击
    if has_shock and vol_ratio > 2:
        evidence = [f"量比{vol_ratio:.1f}(恐慌放量)", "有突发利空事件"]
        return FallCause("政策/外围冲击", "外部冲击,关注晚间是否缓和", "高", evidence,
                        "不恐慌性清仓;观察晚间海外/政策面变化;若持有现金可次日低吸")
    
    # 获利了结: 前涨+缩量跌+主力流出但不恐慌
    prior_rise = flow_data.get("prior_5d_rise_pct", 0)
    if prior_rise > 10 and vol_ratio < 1 and vix < 25:
        evidence = [f"前5日涨幅{prior_rise:.1f}%", f"量比{vol_ratio:.1f}(缩量)", f"VIX={vix:.0f}(正常)"]
        return FallCause("获利了结", "健康回调,非趋势破坏", "中", evidence,
                        "正常调整;高盈利仓按阶梯止盈规则操作;刚回本/浅套仓继续持有")
    
    # 板块轮动流出
    sector_inflow = flow_data.get("sector_inflow_top5", [])
    sector_outflow = flow_data.get("sector_outflow_top5", [])
    has_rotation = (len(sector_inflow) > 0 and len(sector_outflow) > 0 and
                    sector_inflow[0].get("amount", 0) > 10)
    if has_rotation:
        inflow_names = [s.get("name","") for s in sector_inflow[:2]]
        outflow_names = [s.get("name","") for s in sector_outflow[:2]]
        evidence = [f"资金从{','.join(outflow_names)}→{','.join(inflow_names)}"]
        return FallCause("板块轮动流出", "资金切换,跟踪流向再定", "中", evidence,
                        f"持仓若在流出方→适度减仓;若在流入方→持有。关注{','.join(inflow_names)}持续性")
    
    evidence = [f"跌幅{chg:.1f}%", f"量比{vol_ratio:.1f}"]
    return FallCause("技术调整", "正常波动,无明确利空", "低", evidence, "维持原策略,无需恐慌操作")


@dataclass
class FundFlowTrack:
    direction: str      # "板块轮动"|"回收现金"|"北向离场"|"新资金入场"|"存量博弈"
    detail: str
    inflow_sectors: list
    outflow_sectors: list
    safe_haven_signal: bool   # 是否触发避险信号
    position_impact: str      # 对持仓的具体传导


def track_fund_flow(flow_data: dict, holdings_sectors: list,
                     safe_haven_flow: float = 0,
                     total_turnover_change_pct: float = 0) -> FundFlowTrack:
    """追踪资金流向: 流出资金去哪了? 流入资金从哪来? 对持仓的影响?
    flow_data: {main_total(全市场主力净额), northbound_total, 
                inflow_top5: [{name,amount,chg}], outflow_top5: [{name,amount,chg}]}
    holdings_sectors: 持仓覆盖板块名称列表
    """
    inflow = flow_data.get("inflow_top5", [])
    outflow = flow_data.get("outflow_top5", [])
    nb_total = flow_data.get("northbound_total", 0)
    
    # 判定资金去向
    if safe_haven_flow > 50 and nb_total < -30:
        direction = "回收现金+北向离场"
        detail = f"避险资产流入{safe_haven_flow:.0f}亿,北向净流出{abs(nb_total):.0f}亿——资金回收现金,风险偏好骤降"
        safe_haven_signal = True
    elif nb_total < -20:
        direction = "北向离场"
        detail = f"北向净流出{abs(nb_total):.0f}亿,内资承接力度待观察"
        safe_haven_signal = safe_haven_flow > 30
    elif len(inflow) >= 2 and len(outflow) >= 2:
        direction = "板块轮动"
        in_names = [s.get("name","") for s in inflow[:3]]
        out_names = [s.get("name","") for s in outflow[:3]]
        detail = f"资金从{','.join(out_names)}流出→{','.join(in_names)}流入,存量博弈格局"
        safe_haven_signal = False
    elif total_turnover_change_pct > 20:
        direction = "新资金入场"
        detail = f"全市场成交额放量{total_turnover_change_pct:.0f}%,增量资金入场信号"
        safe_haven_signal = False
    else:
        direction = "存量博弈"
        detail = "成交额持平,资金在各板块间腾挪,无明确方向"
        safe_haven_signal = safe_haven_flow > 30
    
    # 对持仓的传导
    inflow_names = {s.get("name","") for s in inflow}
    outflow_names = {s.get("name","") for s in outflow}
    held_in_inflow = holdings_sectors & inflow_names
    held_in_outflow = holdings_sectors & outflow_names
    
    if held_in_outflow and not held_in_inflow:
        position_impact = f"⚠️ 持仓板块({','.join(held_in_outflow)})为资金净流出方,无对应流入板块承接——建议减仓"
    elif held_in_outflow and held_in_inflow:
        position_impact = f"持仓板块分化: {','.join(held_in_outflow)}净流出 vs {','.join(held_in_inflow)}净流入——板块内调仓,非全面撤退"
    elif held_in_inflow:
        position_impact = f"✅ 持仓板块({','.join(held_in_inflow)})为资金净流入方,顺势持有"
    else:
        position_impact = "持仓板块非今日资金主战场,持仓不受直接影响"
    
    return FundFlowTrack(direction, detail,
                        [s.get("name","") for s in inflow],
                        [s.get("name","") for s in outflow],
                        safe_haven_signal, position_impact)
