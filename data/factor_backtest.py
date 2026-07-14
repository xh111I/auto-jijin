# -*- coding: utf-8 -*-
"""
factor_backtest.py  —  因子回测引擎（方法论 · 模块5：量化闭环）

功能：
  1. 每日因子数据入库（外围/资金/技术/情绪/基本面 5维得分）
  2. IC（信息系数）/ ICIR（信息比）自动计算
  3. 因子权重动态迭代（ICIR前2+5%/后2-5%）
  4. 操作效果统计（止损/减仓后3日超额收益）
  5. 月度全量回测 + 失效因子检测

用法：
  python factor_backtest.py                  # 自动用今日数据入库+计算IC+更新权重
  python factor_backtest.py 2026-07-13      # 指定日期回测

数据存储：
  - data/factor_log.json — 时序因子日志（永久保留）
  - data/factor_weights.json — 当前因子权重配置
"""

import json
import os
import sys
import datetime
import statistics
from typing import Optional

BASE = os.path.dirname(os.path.abspath(__file__))
FACTOR_LOG = os.path.join(BASE, "factor_log.json")
WEIGHTS_FILE = os.path.join(BASE, "factor_weights.json")

# ── 因子列表（5维） ──
FACTOR_NAMES = ["外围", "资金", "技术", "情绪", "基本面"]

# ── 基础权重（方法论文档预设） ──
BASE_WEIGHTS = {"外围": 0.20, "资金": 0.25, "技术": 0.25, "情绪": 0.15, "基本面": 0.15}


# ================================================================
#  工具函数
# ================================================================

def _load_json(path, default):
    try:
        return json.load(open(path, encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def num(v) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


# ================================================================
#  1. 从尾盘JSON提取当日因子数据
# ================================================================

def extract_factors(date: str) -> dict:
    """从 tail_<DATE>.json 提取5维因子得分。
    
    返回: {"外围": 0-100, "资金": 0-100, ... , "date": "YYYY-MM-DD"}
    """
    tail_file = os.path.join(BASE, f"tail_{date}.json")
    if not os.path.exists(tail_file):
        print(f"[factor] tail_{date}.json 不存在，跳过")
        return None
    
    data = json.load(open(tail_file, encoding="utf-8"))
    sentiment = data.get("sentiment") or {}
    sector = data.get("sector") or {}
    risk = data.get("risk") or {}
    
    # 1. 情绪因子（0-100, 直接来自fear_greed_index）
    fg = num(sentiment.get("fear_greed_index"))
    emotion_score = fg if fg is not None else 50
    
    # 2. 资金因子（从板块主力净流入折算）
    bars = sector.get("bars") or []
    net_inflows = [num(b.get("net_inflow")) for b in bars if num(b.get("net_inflow")) is not None]
    if net_inflows:
        avg_net = sum(net_inflows) / len(net_inflows)
        # 净流入>0=高资金分, 净流出<0=低资金分
        capital_score = max(0, min(100, 50 + avg_net / 5))
    else:
        capital_score = 50
    
    # 3. 技术因子（从板块技术评分加权平均）
    scores = [num(b.get("score")) for b in bars if num(b.get("score")) is not None]
    tech_score = statistics.mean(scores) if scores else 50
    
    # 4. 外围因子（从情绪note/当日全球数据估算）
    sent_note = sentiment.get("note", "")
    # 简单启发式：如果note提到利空关键词则降分
    bearish_kw = ["跌", "挫", "利空", "风险", "恐慌", "通胀", "加息", "冲突", "暴跌", "跳水"]
    bullish_kw = ["涨", "升", "利好", "反弹", "企稳", "突破", "放量", "抢筹"]
    bearish_count = sum(1 for kw in bearish_kw if kw in sent_note)
    bullish_count = sum(1 for kw in bullish_kw if kw in sent_note)
    external_score = max(20, min(80, 50 + (bullish_count - bearish_count) * 10))
    
    # 5. 基本面因子（从硬止损数据+半导体集中度估算）
    hard_stop = risk.get("hard_stop") or {}
    items = hard_stop.get("items") or []
    stop_distances = []
    for item in items:
        cur = num(item.get("cur_loss_pct"))
        sl = num(item.get("stop_loss_pct"))
        if cur is not None and sl is not None and sl < 0:
            stop_distances.append(abs(cur - sl))
    if stop_distances:
        avg_dist = sum(stop_distances) / len(stop_distances)
        # 距离止损越大=基本面分越高
        fundamental_score = max(20, min(100, 50 + avg_dist * 3))
    else:
        fundamental_score = 60  # 无止损标的=偏乐观
    
    return {
        "date": date,
        "factors": {
            "外围": round(external_score, 1),
            "资金": round(capital_score, 1),
            "技术": round(tech_score, 1),
            "情绪": round(emotion_score, 1),
            "基本面": round(fundamental_score, 1),
        },
        "semic_concentration": num(risk.get("concentration", {}).get("weight_pct")),
        "generated_at": data.get("generated_at", ""),
    }


# ================================================================
#  2. 计算IC（信息系数）+ ICIR（信息比）
# ================================================================

def _pearson_r(x, y):
    """皮尔逊相关系数（手动实现，避免numpy依赖）。"""
    n = len(x)
    if n < 3 or len(y) < 3:
        return 0.0
    mx = sum(x) / n
    my = sum(y) / n
    num = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    dx = sum((xi - mx) ** 2 for xi in x) ** 0.5
    dy = sum((yi - my) ** 2 for yi in y) ** 0.5
    if dx == 0 or dy == 0:
        return 0.0
    return num / (dx * dy)


def calc_ic(factor_log: list, window: int = 20) -> dict:
    """计算各因子IC（当日因子分 vs 次日板块收益）和ICIR。
    
    由于我们没有精确的次日收益数据，使用加权综合评分的变化作为代理。
    返回: {"外围": {"ic": 0.1, "icir": 0.5}, ...}
    """
    if len(factor_log) < 3:
        return {fn: {"ic": 0.0, "icir": 0.0} for fn in FACTOR_NAMES}
    
    # 取最近window条
    recents = factor_log[-window:]
    
    result = {}
    for fn in FACTOR_NAMES:
        factor_values = []
        next_returns = []
        for i in range(len(recents) - 1):
            cur_fv = num(recents[i].get("factors", {}).get(fn))
            # 用所有因子均值变化作为收益代理
            cur_total = num(recents[i].get("combined_score"))
            next_total = num(recents[i + 1].get("combined_score"))
            if cur_fv is not None and cur_total is not None and next_total is not None:
                factor_values.append(cur_fv)
                next_returns.append(next_total - cur_total)
        
        if len(factor_values) >= 5:
            ic = _pearson_r(factor_values, next_returns)
            # ICIR = mean(IC_series) / std(IC_series)
            # 用滚动窗口内的IC稳定性近似
            ics = []
            slice_len = min(10, len(factor_values))
            for j in range(len(factor_values) - slice_len + 1):
                try:
                    ic_slice = _pearson_r(
                        factor_values[j:j+slice_len],
                        next_returns[j:j+slice_len]
                    )
                    ics.append(ic_slice)
                except Exception:
                    pass
            icir = statistics.mean(ics) / (statistics.stdev(ics) + 0.001) if len(ics) >= 3 else 0.0
            result[fn] = {"ic": round(ic, 4), "icir": round(icir, 3)}
        else:
            result[fn] = {"ic": 0.0, "icir": 0.0}
    
    return result


# ================================================================
#  3. 因子权重迭代
# ================================================================

def update_weights(current_ic: dict, weights: dict = None) -> dict:
    """ICIR驱动的权重动态更新。
    规则: ICIR前2因子+5%/后2因子-5%，其余不动。
    """
    if weights is None:
        weights = dict(BASE_WEIGHTS)
    
    if not current_ic:
        return weights
    
    # 按ICIR排序
    sorted_factors = sorted(
        FACTOR_NAMES,
        key=lambda fn: abs(num(current_ic.get(fn, {}).get("icir", 0)) or 0),
        reverse=True
    )
    
    if len(sorted_factors) >= 4:
        # 前2 +5%
        for fn in sorted_factors[:2]:
            weights[fn] = weights.get(fn, 0.2) + 0.05
        # 后2 -5%
        for fn in sorted_factors[-2:]:
            weights[fn] = weights.get(fn, 0.2) - 0.05
    
    # 归一化到[0.05, 0.50]区间
    for fn in FACTOR_NAMES:
        weights[fn] = max(0.05, min(0.50, weights[fn]))
    
    # 归一化总和=1
    total = sum(weights.values())
    for fn in FACTOR_NAMES:
        weights[fn] = round(weights[fn] / total, 4)
    
    return weights


# ================================================================
#  4. 操作效果统计
# ================================================================

def calc_operation_stats(factor_log: list, window: int = 20) -> dict:
    """统计减仓/止损操作后3日账户表现。
    
    TODO: 需要账户收益时序数据。当前返回占位值。
    """
    return {
        "stop_loss_3d_avg": 0,        # 止损后3日超额收益
        "reduce_3d_avg": 0,           # 减仓后3日超额收益
        "max_drawdown_improve": 0,    # 最大回撤改善
        "sample_count": 0,
    }


# ================================================================
#  5. 主流程
# ================================================================

def run_backtest(date: str = None):
    """完整回测流水线：入库→计算IC→更新权重。"""
    if date is None:
        date = datetime.date.today().isoformat()
    
    print(f"[factor] === 因子回测流水线 {date} ===")
    
    # 1. 因子数据入库
    factors = extract_factors(date)
    if factors is None:
        print(f"[factor] ⚠ 无数据可入库")
        return None
    
    log = _load_json(FACTOR_LOG, {"records": []})
    # 去重：同一日期不重复追加
    existing_dates = {r.get("date") for r in log["records"]}
    if date not in existing_dates:
        log["records"].append(factors)
        _save_json(FACTOR_LOG, log)
        print(f"[factor] ✅ 因子数据入库: {date} ({len(log['records'])}条)")
    else:
        # 更新已有记录
        for i, r in enumerate(log["records"]):
            if r.get("date") == date:
                log["records"][i] = factors
                break
        _save_json(FACTOR_LOG, log)
        print(f"[factor] 🔄 因子数据更新: {date}")
    
    # 2. 计算综合得分
    weights = _load_json(WEIGHTS_FILE, dict(BASE_WEIGHTS))
    f = factors["factors"]
    factors["combined_score"] = round(
        sum(num(f.get(fn, 50)) * num(weights.get(fn, 0.2)) or 0 for fn in FACTOR_NAMES),
        1
    )
    factors["weights"] = dict(weights)
    _save_json(FACTOR_LOG, log)
    
    # 3. 计算IC/ICIR
    ic = calc_ic(log["records"])
    factors["ic"] = ic
    # 回写IC到日志
    for i, r in enumerate(log["records"]):
        if r.get("date") == date:
            log["records"][i]["ic"] = ic
            break
    _save_json(FACTOR_LOG, log)
    
    print(f"[factor] IC: { {fn: ic[fn]['ic'] for fn in FACTOR_NAMES} }")
    print(f"[factor] ICIR: { {fn: ic[fn]['icir'] for fn in FACTOR_NAMES} }")
    
    # 4. 权重迭代
    new_weights = update_weights(ic, dict(weights))
    _save_json(WEIGHTS_FILE, new_weights)
    print(f"[factor] 权重更新: { {fn: f'{w*100:.0f}%' for fn, w in new_weights.items()} }")
    
    # 5. 操作效果统计（占位）
    stats = calc_operation_stats(log["records"])
    factors["operation_stats"] = stats
    _save_json(FACTOR_LOG, log)
    
    # 6. 保存最新权重到记录
    for i, r in enumerate(log["records"]):
        if r.get("date") == date:
            log["records"][i]["weights"] = new_weights
            break
    _save_json(FACTOR_LOG, log)
    
    print(f"[factor] ✅ 回测完成")
    return factors


if __name__ == "__main__":
    date = sys.argv[1] if len(sys.argv) > 1 else None
    run_backtest(date)
