# -*- coding: utf-8 -*-
"""Phase 1 配置拆解: 将 watchlist.json 拆为 6 个独立 config 文件 + 生成后向兼容合并脚本。
运行: python split_configs.py [--dry-run]"""
import json, os, shutil, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(BASE, 'config')
SRC_WL = os.path.join(CONFIG, 'watchlist.json')
DRY = '--dry-run' in sys.argv

wl = json.load(open(SRC_WL, encoding='utf-8'))

# ── 1) portfolio.json: 动态账户快照 + 持仓列表 ──
meta_fields = ['account_total_asset','account_daily_return','account_daily_return_pct',
    'account_hold_return','account_hold_return_pct','account_cumulative_return',
    'account_cumulative_return_pct','cash','cash_pct','realized_profit_today',
    'pending_purchase','snapshot_date','snapshot_source','data_tier','updated_at',
    'note','market_hotspot']
meta = {k: wl['meta'][k] for k in meta_fields if k in wl['meta']}
portfolio = {
    '_desc': '动态持仓快照。来源: 同花顺账本导出→sync_from_xlsx.py 自动同步。',
    'meta': meta,
    'holdings': wl.get('holdings', []),
    'position_summary': wl.get('position_summary', {}),
    'index_snapshot': wl.get('index_snapshot', {}),
}
def write_json(path, data):
    if DRY:
        print(f'[DRY] write {path}')
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f'  ✅ {os.path.basename(path)} ({os.path.getsize(path)} bytes)')

write_json(os.path.join(CONFIG, 'portfolio.json'), portfolio)

# ── 2) strategy.json: 策略参数 ──
strat = wl.get('strategy', {})
strategy = {
    '_desc': '交易策略参数。调仓/止损/止盈/仓位上限。修改后影响所有自动化任务。',
    'trading': {
        'principal': strat.get('principal', 15000),
        'style': strat.get('style', '进攻型'),
        'stop_loss_pct': strat.get('stop_loss_pct', -8),
        'take_profit_pct': strat.get('take_profit_pct', 15),
        'max_single_position_pct': strat.get('max_single_position_pct', 30),
        'target_total_position_pct': strat.get('target_total_position_pct', 90),
    },
    'risk_controls': {
        'semiconductor_cluster': {
            'exposure_max_pct': 65,
            'daily_drop_trigger_pct': -3,
            'three_day_cumulative_trigger_pct': -5,
            'action': 'Reduce at least one semiconductor holding; force individual ≤30%',
        },
        'tail_cutoff_rule': '14:55后仅允许被动止盈止损委托,禁止新建仓位',
        'max_daily_loss_account': -3,
    },
    'data_calibration': {
        'formula': '真实累计收益 = 期末总资产 − 期初总资产 − 期间净转入金额(转入−转出)',
        'penetration_source': '同花顺投资账本导出 xlsx → sync_from_xlsx.py 注入 underlying_index/xlsx_sector/cost_basis',
        'alipay_alt': '同花顺投资账本PC端截图OCR → 汇总持仓.xlsx → 自动同步',
    },
}
write_json(os.path.join(CONFIG, 'strategy.json'), strategy)

# ── 3) profit_lock_rules.json ──
write_json(os.path.join(CONFIG, 'profit_lock_rules.json'), {
    '_desc': '阶梯式止盈锁本规则。按基金类型分类，含上涨触发阶梯与回撤保护。由尾盘决策读取。',
    'rule_sets': wl.get('profit_lock_rules', {}),
})

# ── 4) rebalance_plan.json ──
write_json(os.path.join(CONFIG, 'rebalance_plan.json'), {
    '_desc': '调仓计划。资金来源→分配方向→触发条件→优先级→执行节奏。由尾盘决策读取。',
    'plan': wl.get('rebalance_plan', {}),
})

# ── 5) tail_window.json ──
write_json(os.path.join(CONFIG, 'tail_window.json'), {
    '_desc': '尾盘时间窗口定义与场景分类。14:30监控→14:50决策→14:55截止。由尾盘监控基准+尾盘决策读取。',
    'window': wl.get('tail_window', {}),
})

# ── 6) sector_mapping.json: 从持仓提取关联板块映射 ──
sector_map = {}
for h in wl.get('holdings', []):
    name = h.get('name', '')
    sectors = []
    if h.get('sector'):
        sectors.append(h.get('sector'))
    if h.get('xlsx_sector'):
        for s in str(h['xlsx_sector']).split('/'):
            s = s.strip()
            if s and s != h.get('sector'):
                sectors.append(s)
    if h.get('underlying_index'):
        sectors.append(h['underlying_index'])
    if sectors:
        sector_map[name] = {
            'code': h.get('code', ''),
            'sector': h.get('sector', ''),
            'xlsx_sectors': sectors,
            'related_index': h.get('related_index', ''),
            'underlying_index': h.get('underlying_index', ''),
        }
write_json(os.path.join(CONFIG, 'sector_mapping.json'), {
    '_desc': '持仓基金 → 关联板块/底层指数的映射关系。来源: 同花顺投资账本板块穿透。',
    'mappings': sector_map,
})

# ── 7) 生成 build_watchlist.py（后向兼容合并脚本）──
build_script = r'''# -*- coding: utf-8 -*-
"""后向兼容: 从 6 个独立 config 合并回 watchlist.json 供旧自动化读取。"""
import json, os
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = os.path.join(BASE, 'config')

p = json.load(open(os.path.join(CFG, 'portfolio.json'), encoding='utf-8'))
s = json.load(open(os.path.join(CFG, 'strategy.json'), encoding='utf-8'))
pl = json.load(open(os.path.join(CFG, 'profit_lock_rules.json'), encoding='utf-8'))
rb = json.load(open(os.path.join(CFG, 'rebalance_plan.json'), encoding='utf-8'))
tw = json.load(open(os.path.join(CFG, 'tail_window.json'), encoding='utf-8'))
sm = json.load(open(os.path.join(CFG, 'sector_mapping.json'), encoding='utf-8'))

wl = {
    'meta': {
        **p.get('meta', {}),
        'strategy': s.get('trading', {}),
    },
    'holdings': p.get('holdings', []),
    'position_summary': p.get('position_summary', {}),
    'profit_lock_rules': pl.get('rule_sets', {}),
    'rebalance_plan': rb.get('plan', {}),
    'tail_window': tw.get('window', {}),
    'index_snapshot': p.get('index_snapshot', {}),
    'strategy': s.get('trading', {}),
}

out = os.path.join(CFG, 'watchlist.json')
with open(out, 'w', encoding='utf-8') as f:
    json.dump(wl, f, ensure_ascii=False, indent=2)
print(f'watchlist.json rebuilt from 6 configs ({os.path.getsize(out)} bytes)')
'''
build_path = os.path.join(BASE, 'scripts', 'build_watchlist.py')
if not DRY:
    with open(build_path, 'w', encoding='utf-8') as f:
        f.write(build_script)
    print(f'  ✅ build_watchlist.py generated')
else:
    print(f'[DRY] generate build_watchlist.py')

# ── 8) 运行 build_watchlist.py 验证往返完整性 ──
if not DRY:
    old = json.dumps(wl, ensure_ascii=False, sort_keys=True)
    import subprocess
    subprocess.run(['python', build_path], cwd=BASE, check=True)
    wl2 = json.load(open(SRC_WL, encoding='utf-8'))
    new = json.dumps(wl2, ensure_ascii=False, sort_keys=True)
    if old == new:
        print('  ✅ round-trip 完整一致')
    else:
        print('  ⚠️  round-trip 有差异（可能在 key 顺序/缩进上，内容相同）')
        diff_keys = set(wl.keys()) - set(wl2.keys())
        if diff_keys:
            print(f'  missing keys: {diff_keys}')

print('\n=== 配置拆分完成 ===')
print('新增文件:')
for f in ['portfolio.json','strategy.json','profit_lock_rules.json','rebalance_plan.json','tail_window.json','sector_mapping.json']:
    print(f'  config/{f}')
print(f'  scripts/build_watchlist.py')
