#!/usr/bin/env python3
# data/compare_ds_grayscale.py
# DeepSeek V4 Flash 灰度比对脚本。
# 遍历 data/ 与 ds_grayscale/ 同名 JSON，比对字段完整率与规则修正率。
# 用法: python3 data/compare_ds_grayscale.py [YYYY-MM-DD]

import json, os, sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, 'data')
DS_DIR = os.path.join(ROOT, 'data', 'ds_grayscale')
today = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()

REQUIRED_FIELDS = {
    'early-morning': ['core', 'sentiment', 'tech'],
    'tail': ['decision_level', 'core_instructions', 'position_adjust'],
    'market': ['market_summary', 'next_day_forecast']
}

results = []
total_fields_missing = 0
total_corrections = 0
total_tasks = 0

# 遍历 ds_grayscale 目录
if not os.path.exists(DS_DIR):
    print(f'[compare] ds_grayscale/ not found, skip')
    sys.exit(0)

for fname in sorted(os.listdir(DS_DIR)):
    if not fname.endswith('.json'):
        continue
    if today not in fname:
        continue

    ds_path = os.path.join(DS_DIR, fname)
    orig_path = None
    # 查找对应的原始文件（可能在 data/ 根目录或 reports/ 下）
    for root_dir in [DATA_DIR, os.path.join(DATA_DIR, 'reports', today)]:
        candidate = os.path.join(root_dir, fname)
        if os.path.exists(candidate):
            orig_path = candidate
            break

    # 加载 Flash 输出
    try:
        with open(ds_path, 'r', encoding='utf-8') as f:
            ds_data = json.load(f)
    except Exception as e:
        results.append({'file': fname, 'error': f'Flash JSON parse failed: {e}'})
        total_fields_missing += 1
        continue

    # 字段完整率
    task_type = fname.split('_')[0]
    required = REQUIRED_FIELDS.get(task_type, [])
    missing = [f for f in required if f not in ds_data]
    total_fields_missing += len(missing)
    total_tasks += 1

    # 规则修正率
    telemetry = ds_data.get('_telemetry', {})
    corrections = telemetry.get('rule_corrections', [])
    total_corrections += len(corrections)

    # 文件大小
    ds_size = os.path.getsize(ds_path)

    r = {
        'file': fname,
        'task_type': task_type,
        'ds_size_bytes': ds_size,
        'missing_fields': missing,
        'corrections': len(corrections),
    }
    if orig_path:
        r['orig_size_bytes'] = os.path.getsize(orig_path)
    if corrections:
        r['correction_details'] = corrections
    results.append(r)

# 汇总
print(f'\n===== DeepSeek V4 Flash 灰度比对 ({today}) =====')
for r in results:
    if 'error' in r:
        print(f'  ❌ {r["file"]}: {r["error"]}')
        continue
    status = '✅' if not r['missing_fields'] else '⚠️'
    corr_str = f' | 修正{r["corrections"]}次' if r['corrections'] else ''
    size_str = f' | {r["ds_size_bytes"]}B'
    if r.get('orig_size_bytes'):
        size_str += f' vs orig {r["orig_size_bytes"]}B'
    print(f'  {status} {r["file"]}: {r["task_type"]}{size_str}{corr_str}')
    if r['missing_fields']:
        print(f'     缺失字段: {r["missing_fields"]}')
    if r.get('correction_details'):
        for c in r['correction_details']:
            print(f'     ⚡ {c["reason"]}')

# 统计
field_rate = ((total_tasks * (len(REQUIRED_FIELDS.get('early-morning', []))) - total_fields_missing)
              / (total_tasks * len(REQUIRED_FIELDS.get('early-morning', []))) * 100) if total_tasks > 0 else 0
print(f'\n--- 统计 ---')
print(f'  任务数: {total_tasks}')
print(f'  字段缺失: {total_fields_missing}')
print(f'  规则修正: {total_corrections} 次')
print(f'  字段完整率: {field_rate:.0f}%')
print(f'  评估: {"✅ 可上线" if field_rate >= 98 and total_corrections <= 3 else "⚠️ 需观察" if field_rate >= 90 else "❌ 不达标"}')

# 落盘汇总
summary_path = os.path.join(DS_DIR, f'grayscale_summary_{today}.json')
with open(summary_path, 'w', encoding='utf-8') as f:
    json.dump({'date': today, 'results': results, 'field_completion_pct': round(field_rate, 1),
               'total_corrections': total_corrections, 'total_tasks': total_tasks},
              f, ensure_ascii=False, indent=2)
print(f'\n汇总已保存: {summary_path}')
