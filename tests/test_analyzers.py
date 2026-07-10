# tests/test_analyzers.py
# 引擎层单元测试(Phase 6): mock数据验证核心决策逻辑的纯函数。
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from analyzers.tail import classify_scenario, evaluate_profit_lock, generate_tail_signals
from analyzers.market import analyze_kline, rank_sectors, predict_next_day
from analyzers.midday import cross_validate_sectors, classify_main_force_phase, afternoon_preview
from analyzers.morning import assess_overseas_impact, generate_morning_guidance

# ─── tail.py ───
def test_classify_scenario_plunge():
    """放量跳水检测"""
    baseline = {'创业板指': {'chg_pct': -2, 'vol_ratio': 1.5, 'above_ma': False}}
    current = {'创业板指': {'chg_pct': -4, 'vol_ratio': 4, 'above_ma': False}}
    # 单指数: avg_chg=-2(<-1), avg_vol=4(>3), ma_ratio=0(<0.5) → plunge
    # Actually: avg_chg = -2, avg_vol = 4 → meets plunge criteria
    scenario, label = classify_scenario(baseline, current, ['创业板指'])
    assert scenario == 'plunge', f'Expected plunge, got {scenario}'

def test_classify_scenario_surge():
    """放量拉升检测"""
    baseline = {'沪深300': {'chg_pct': 0, 'vol_ratio': 1, 'above_ma': True}}
    current = {'沪深300': {'chg_pct': 1.5, 'vol_ratio': 1.5, 'above_ma': True}}
    scenario, _ = classify_scenario(baseline, current, ['沪深300'])
    assert scenario == 'surge', f'Expected surge, got {scenario}'

def test_classify_scenario_range():
    """缩量震荡检测"""
    baseline = {'科创50': {'chg_pct': 0, 'vol_ratio': 1, 'above_ma': False}}
    current = {'科创50': {'chg_pct': 0.2, 'vol_ratio': 0.6, 'above_ma': False}}
    scenario, _ = classify_scenario(baseline, current, ['科创50'])
    assert scenario == 'range', f'Expected range, got {scenario}'

def test_evaluate_profit_lock_hold():
    """正常持有(未触发任何止盈止损)"""
    h = {'name': 'test_fund', 'return_pct': 0.05, 'profit_lock': {'stages': []}, 'peak_return_pct': 0.05}
    action, reason, pct = evaluate_profit_lock(h, 5)
    assert action == 'hold'

def test_evaluate_profit_lock_stop():
    """硬止损触发(-8%)"""
    h = {'name': 'stop_fund', 'return_pct': -0.09, 'profit_lock': {}, 'peak_return_pct': -0.09}
    action, _, pct = evaluate_profit_lock(h, 1)
    assert action == 'sell_100'
    assert pct == 100

# ─── market.py ───
def test_analyze_kline_bullish():
    """多头排列+量价齐升"""
    data = {'price': 3500, 'change_pct': 1.5, 'volume': 1e10, 'vol_5avg': 5e9,
            'ma20': 3450, 'ma60': 3400, 'open': 3490, 'high': 3520, 'low': 3485,
            'close': 3510, 'main_net_inflow': 10000}
    d = analyze_kline('test', '测试指数', data)
    assert d.bias == '偏多'
    assert d.score >= 7

def test_analyze_kline_bearish():
    """空头排列+放量下跌"""
    data = {'price': 3000, 'change_pct': -2, 'volume': 2e10, 'vol_5avg': 5e9,
            'ma20': 3200, 'ma60': 3400, 'open': 3050, 'high': 3060, 'low': 2980,
            'close': 2990, 'main_net_inflow': -5000}
    d = analyze_kline('test', '测试指数', data)
    assert d.bias in ('偏空', '中性')

# ─── midday.py ───
def test_classify_main_force_lift():
    """拉升阶段判定"""
    data = {'chg_5d': 8, 'flow_5d': 2000, 'price_pos': 70}
    phase = classify_main_force_phase(data)
    assert '拉升' in phase

def test_classify_main_force_distribute():
    """出货阶段判定"""
    data = {'chg_5d': 10, 'flow_5d': -500, 'price_pos': 85}
    phase = classify_main_force_phase(data)
    assert '出货' in phase

# ─── morning.py ───
def test_assess_overseas_impact_neutral():
    """海外中性影响"""
    overseas = {'纳指': 0.5, '费城半导体': 0.3, '原油': -1, '美元指数': 0.2, 'VIX': 18}
    result = assess_overseas_impact(overseas, [])
    assert result['impact_score'] >= -2 and result['impact_score'] <= 2
    assert len(result['risk_events']) == 0

def test_assess_overseas_impact_bearish():
    """海外利空(纳指+SOX双杀+VIX飙升)"""
    overseas = {'纳指': -2, '费城半导体': -3, '原油': -4, '美元指数': 0.8, 'VIX': 35}
    result = assess_overseas_impact(overseas, [])
    assert result['impact_score'] < -2
    assert len(result['risk_events']) >= 2
