import json
d = json.load(open('data/market_tech_2026-07-14.json', 'r', encoding='utf-8'))
for k, v in d.get('by_code', {}).items():
    print(f"{k} {v.get('name',''):8s}: {v.get('op_ref', '')}")
    print()
