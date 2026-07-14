"""检查 market_2026-07-14.json 结构"""
import json
with open('data/market_2026-07-14.json') as f:
    d = json.load(f)
print('=== sectors keys ===')
for k in d['sectors']:
    print(f'  {k}: {len(d["sectors"][k])} items')
print()
print('=== sectors.strong ===')
for s in d['sectors'].get('strong', []):
    print(f'  {s}')
print('=== sectors.rising ===')
for s in d['sectors'].get('rising', []):
    print(f'  {s}')
print('=== sectors.weak ===')
for s in d['sectors'].get('weak', []):
    print(f'  {s}')
print()
print('=== rotation ===')
for r in d.get('rotation', []):
    print(f'  {r}')
print()
print('=== keys ===')
for k in d:
    if isinstance(d[k], dict):
        print(f'  {k}: {list(d[k].keys())[:8]}')
    else:
        print(f'  {k}: {type(d[k]).__name__}')
