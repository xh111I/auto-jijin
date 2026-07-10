# src/models/schema.py
# 统一数据契约（Schema）。
# 所有自动化任务输出的结构化数据必须符合此模型。
# 来自 DeepSeek 优化报告 §3.2。

from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from typing import List, Optional, Dict, Any


@dataclass
class MarketSnapshot:
    """大盘/板块/个股快照"""
    index_code: str
    name: str
    price: float
    change_pct: float
    volume: Optional[float] = None
    turnover: Optional[float] = None
    ma20: Optional[float] = None
    ma60: Optional[float] = None
    vol_ratio: Optional[float] = None          # 量比
    above_ma: Optional[bool] = None            # 是否站上分时均线
    main_net_inflow: Optional[float] = None    # 主力净流入(万元)


@dataclass
class PortfolioHolding:
    """持仓基金"""
    fund_code: str
    name: str
    market_value: float
    weight_pct: float
    return_pct: float
    return_amount: float
    cost_basis: Optional[float] = None
    shares: Optional[float] = None
    sector: str = ''
    related_index: str = ''
    underlying_index: str = ''
    status: str = 'active'                      # active | converting | pending_confirm | cleared
    risk_flag: str = ''
    stop_loss_pct: float = -8.0
    take_profit: Optional[Dict[str, Any]] = None  # 阶梯止盈参数(从 profit_lock_rules 匹配)
    rebalance_role: str = ''                      # 在调仓框架中的角色


@dataclass
class DecisionSignal:
    """操作信号"""
    fund_name: str
    fund_code: str
    action: str                              # buy | sell | hold | reduce | wait
    confidence: str                          # high | medium | low
    reason: str
    target_weight: Optional[float] = None    # 目标仓位%
    entry_price: Optional[float] = None
    stop_price: Optional[float] = None
    scenario: str = ''                       # 触发场景标签


@dataclass
class Alert:
    """风险告警"""
    level: str                               # red | orange | yellow
    text: str


@dataclass
class ReportData:
    """统一报告数据（所有任务产出的标准格式）"""
    date: str                                # YYYY-MM-DD
    version: str = '1.0'
    report_type: str = ''                    # morning | midday | tail | market | alert
    updated_at: str = ''                     # ISO datetime
    data_tier: str = 'T2'
    market: Dict[str, MarketSnapshot] = field(default_factory=dict)
    holdings: List[PortfolioHolding] = field(default_factory=list)
    signals: List[DecisionSignal] = field(default_factory=list)
    alerts: List[Alert] = field(default_factory=list)
    sentiment: Dict[str, Any] = field(default_factory=dict)
    predictions: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """序列化为标准 JSON（供生成器渲染）"""
        result = {}
        for k, v in asdict(self).items():
            result[k] = v
        return result
