# -*- coding: utf-8 -*-
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
