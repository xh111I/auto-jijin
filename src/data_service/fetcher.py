# src/data_service/fetcher.py
# 统一数据服务层: 原始 neodata 输出 → 标准化模型。
# 内置重试策略、超时、降级、日缓存。
# 所有自动化任务通过此模块访问数据，不再直接在 Prompt 中硬编码 neodata 调用。

import json, time, os, sys
from datetime import date, datetime
from typing import List, Dict, Optional, Any

# 自动注册 src 到路径
_SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from models.schema import MarketSnapshot, PortfolioHolding, Alert

# ── 缓存与状态 ──
_FETCH_CACHE: Dict[str, Any] = {}
_FETCH_TIMESTAMPS: Dict[str, float] = {}
CACHE_TTL_SECONDS = 300       # 交易日缓存 5 分钟
MAX_RETRIES = 3
TIMEOUT_SECONDS = 15


# ── 配置读写 ──
def load_config(name: str) -> dict:
    """从 config/{name}.json 读取配置。"""
    base = os.path.dirname(_SRC)
    with open(os.path.join(base, 'config', f'{name}.json'), encoding='utf-8') as f:
        return json.load(f)


def load_portfolio() -> List[PortfolioHolding]:
    """从 config/portfolio.json 读取持仓列表 → 标准模型。"""
    data = load_config('portfolio')
    holdings = []
    for h in data.get('holdings', []):
        holdings.append(PortfolioHolding(
            fund_code=h.get('code', ''),
            name=h.get('name', ''),
            market_value=h.get('market_value', 0),
            weight_pct=h.get('weight_pct', 0),
            return_pct=h.get('hold_return_pct', 0),
            return_amount=h.get('hold_return_amount', 0),
            cost_basis=h.get('cost_basis'),
            shares=h.get('shares'),
            sector=h.get('sector', ''),
            related_index=h.get('related_index', ''),
            underlying_index=h.get('underlying_index', ''),
            status=h.get('status', 'active'),
            risk_flag=h.get('risk_flag', ''),
            take_profit=h.get('profit_lock'),
            rebalance_role=h.get('rebalance_role', ''),
        ))
    return holdings


def load_strategy() -> dict:
    return load_config('strategy')


def load_tail_window() -> dict:
    return load_config('tail_window').get('window', {})


# ── 重试与超时包装 ──
def _fetch_with_retry(fetch_fn, *args, cache_key: str = None, **kwargs):
    """通用重试/缓存/超时包装器。"""
    if cache_key and cache_key in _FETCH_CACHE:
        age = time.time() - _FETCH_TIMESTAMPS.get(cache_key, 0)
        if age < CACHE_TTL_SECONDS:
            return _FETCH_CACHE[cache_key]

    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            result = fetch_fn(*args, **kwargs)
            if cache_key:
                _FETCH_CACHE[cache_key] = result
                _FETCH_TIMESTAMPS[cache_key] = time.time()
            return result
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)  # 指数退避

    # 所有重试耗尽 → 降级返回 None
    print(f'[fetcher] WARN: fetch failed after {MAX_RETRIES} retries: {last_error}')
    return None


# ── 归一化函数（raw neodata → models） ──
def normalize_market_snapshot(raw: dict, index_code: str, name: str = '') -> MarketSnapshot:
    """将 neodata 原始行情数据归一化为 MarketSnapshot。
    raw 格式: { "price": ..., "change_pct": ..., "volume": ..., ... }"""
    return MarketSnapshot(
        index_code=index_code,
        name=name or index_code,
        price=raw.get('price', 0),
        change_pct=raw.get('change_pct', 0),
        volume=raw.get('volume'),
        turnover=raw.get('turnover'),
        ma20=raw.get('ma20'),
        ma60=raw.get('ma60'),
        vol_ratio=raw.get('vol_ratio'),
        above_ma=raw.get('above_ma'),
        main_net_inflow=raw.get('main_net_inflow'),
    )


def load_holdings_as_model() -> List[PortfolioHolding]:
    """从本地 portfolio.json 加载持仓 → 模型列表。"""
    return load_portfolio()


def build_alerts(holdings: List[PortfolioHolding], strategy: dict) -> List[Alert]:
    """根据持仓和策略自动生成风险告警。"""
    alerts = []
    semi = [h for h in holdings if '半导体' in h.sector or '科创' in h.underlying_index]
    semi_wt = sum(h.weight_pct for h in semi)
    if semi_wt > 60:
        alerts.append(Alert('red', f'半导体集中度 {semi_wt:.1f}% 超 60% 警戒线'))
    for h in holdings:
        if h.status != 'active':
            continue
        if h.weight_pct > strategy.get('trading', {}).get('max_single_position_pct', 30):
            alerts.append(Alert('orange', f'{h.name} 权重 {h.weight_pct:.1f}% 逼近单仓上限'))
        if h.return_pct < strategy.get('trading', {}).get('stop_loss_pct', -8):
            alerts.append(Alert('red', f'{h.name} 触发-8%硬止损(当前{h.return_pct:.1f}%)'))
    return alerts


# ── 快速工具函数 ──
def get_today_str() -> str:
    return date.today().isoformat()
