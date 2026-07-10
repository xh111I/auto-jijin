#!/usr/bin/env python3
"""Update watchlist.json from 2026-07-10 14:37 腾讯自选股截图 OCR 数据"""
import json

CONFIG_PATH = r"C:\Users\LEGION\Nutstore\1\daily-report\config\watchlist.json"

with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    d = json.load(f)

# === 新持仓数据（2026-07-10 14:37 截图） ===
new_data = [
    ("东方人工智能主题混合C",              4767.32,  314.44,   571.70,  13.63),
    ("东方阿尔法科技优选混合C",             3358.57,  189.51,   358.57,  11.93),
    ("永赢先锋半导体智选混合C",            1856.32, -22.85,   -17.54,  -0.94),
    ("鹏华丰诚债券C",                     1262.55,  -0.42,    -0.39,  -0.04),
    ("广发港股创新药ETF联接(QDII)C",       1390.95,  -2.09,   -54.26,  -3.75),
    ("财通集成电路产业股票C",               192.91,   5.00,     4.98,   2.65),
    ("财通成长优选混合C",                   192.85,   4.91,     4.92,   2.62),
    ("广发纳斯达克100ETF联接(QDII)C",        89.05,  -0.18,    -1.95,  -1.35),
    ("天弘中证全指通信设备指数C",             10.59,   0.59,     0.59,   5.91),
    ("富国中证煤炭指数C",                    4.85,  -9.17,     0.00,   0.00),
    ("嘉实中证主要消费ETF发起联接C",          3.30,  -4.68,     0.00,   0.00),
]

total_mv = sum(row[1] for row in new_data)
daily_ret = sum(row[2] for row in new_data)
total_hr = sum(row[3] for row in new_data)

# Preserve old metadata fields
old_h_map = {h['name']: h for h in d.get('holdings', [])}

new_holdings = []
for name, mv, pnl, hr_amt, hr_pct in new_data:
    old = old_h_map.get(name, {})
    w = round(mv / total_mv * 100, 1)

    entry = {
        'name': name,
        'market_value': mv,
        'yesterday_pnl': pnl,
        'hold_return_amount': hr_amt,
        'hold_return_pct': hr_pct,
        'weight_pct': w,
        'status': old.get('status', 'active'),
        'sector': old.get('sector'),
        'related_index': old.get('related_index'),
        'risk_flag': old.get('risk_flag'),
    }
    entry = {k: v for k, v in entry.items() if v is not None}
    new_holdings.append(entry)

# Sort by weight desc
new_holdings.sort(key=lambda x: x['weight_pct'], reverse=True)

# --- Update meta ---
d['meta']['account_total_asset'] = round(total_mv, 2)
d['meta']['account_daily_return'] = round(daily_ret, 2)
base = total_mv - daily_ret
d['meta']['account_daily_return_pct'] = round(daily_ret / base * 100, 2) if base > 0 else 0
d['meta']['account_hold_return'] = round(total_hr, 2)
hr_base = total_mv - total_hr
d['meta']['account_hold_return_pct'] = round(total_hr / hr_base * 100, 2) if hr_base > 0 else 0
d['meta']['snapshot_date'] = '2026-07-10T14:37'
d['meta']['snapshot_source'] = 'OCR校准(腾讯自选股持仓截图14:37盘中版) @ 2026-07-10'
d['meta']['updated_at'] = '2026-07-10T14:38:00+08:00'

semi_exp = 36.31 + 25.58 + 14.14 + 1.47 + 0.08  # 东方AI+东财+永赢+财通集成+天弘
note_parts = [
    f"14:38更新（腾讯自选股14:37截图盘中版）。总资产{total_mv:.2f}，日赚+{daily_ret:.2f}(+{daily_ret/base*100:.2f}%)，持有收益+{total_hr:.2f}(+{total_hr/hr_base*100:.2f}%)。",
    "今日重大调仓：",
    "①永赢半导大幅加仓~971(885→1856, 权重6.7%→14.1%, 翻倍!)",
    "②煤炭几乎清仓(502→5, 权重3.8%→≈0%)",
    "③消费几乎清仓(497→3, 权重3.8%→≈0%)",
    "④港药继续减仓~176(1567→1391, 权重11.9%→10.6%)",
    "⑤财通两只加仓各~88(105→193各)",
    "⑥东方AI微增20(4747→4767)。",
    f"半导体集中度暴升至{semi_exp:.1f}%(东方AI36.3+东财25.6+永赢14.1+财通集成1.5)，进攻性极强。",
    "永赢半导从-15.9%回撤至-0.94%(翻倍加仓摊薄成本)。",
    "【OCR校准2026-07-10 盘中】单图14:37确认。"
]
d['meta']['note'] = ''.join(note_parts)

d['holdings'] = new_holdings

# --- Update position_summary ---
d['position_summary'] = {
    'active_funds_count': 11,
    'dormant_funds_count': 0,
    'cleared_funds_count': 1,
    'total_active_market_value': round(total_mv, 2),
    'top3_concentration_pct': round(36.31 + 25.58 + 14.14, 1),
    'semiconductor_exposure_pct': round(semi_exp, 2),
    'hk_innovation_drug_pct': 10.60,
    'coal_defense_pct': 0.04,
    'bond_safety_pct': 9.62,
    'us_nasdaq_pct': 0.68,
    'consumption_pct': 0.03,
    'newly_confirmed_funds': [],
    'key_moves_20260710':
        '①永赢半导翻倍+971(权重6.7→14.1%,成本摊薄-15.9%→-0.94%) '
        '②煤炭清仓99%(502→5) ③消费清仓99%(497→3) '
        '④港药继续减-176(11.9%→10.6%) '
        '⑤财通双基加仓各+88 ⑥半导体集中度77.6%',
    'risk_alerts': [
        f'半导体集中度{semi_exp:.1f}% 极度集中，单一板块风险敞口大',
        '东方AI单仓36.3%超30%上限',
        '永赢半导虽回撤至-0.94%，但翻倍后绝对敞口增至1856',
        '港药持续亏损-3.75%'
    ]
}

with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
    json.dump(d, f, ensure_ascii=False, indent=2)

print(f"OK - watchlist.json updated")
print(f"  Total asset:  {total_mv:.2f}")
print(f"  Daily return: {daily_ret:+.2f} ({daily_ret/base*100:+.2f}%)")
print(f"  Hold return:  {total_hr:+.2f} ({total_hr/hr_base*100:+.2f}%)")
print(f"  Semi exposure:{semi_exp:.1f}%")
