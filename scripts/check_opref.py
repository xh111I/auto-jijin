import json
d = json.load(open('data/market_tech_2026-07-14.json', 'r', encoding='utf-8'))
for k, v in list(d.get('by_code', {}).items())[:4]:
    print(f"{k}: {v.get('op_ref', '')[:200]}")
    print()
