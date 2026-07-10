# src/orchestrator/runner.py
# 编排层 · 任务运行器。
# 统一执行步骤：加载配置 → 依赖检查 → 调用数据/分析 → 渲染 → 发布 → 审计日志。
# 所有任务 Prompt 精简为仅描述目标+数据需求，复用此运行器。
import json, os, sys, time, subprocess, traceback
from datetime import datetime
from pathlib import Path
from typing import Optional

_SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from data_service.fetcher import load_config, get_today_str
from .dag import check_dependency, TASK_DAG

# 项目根
ROOT = os.path.dirname(_SRC)
DATA = os.path.join(ROOT, 'data')
REPORTS = os.path.join(DATA, 'reports')
LOG_FILE = os.path.join(ROOT, 'logs', 'task_audit.log')


# ── 审计日志 ──
def audit_log(task_name: str, status: str, detail: str = '', duration_ms: float = 0):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    line = f'[{datetime.now().isoformat()}] {task_name} | {status} | {duration_ms:.0f}ms'
    if detail:
        line += f' | {detail[:200]}'
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(line + '\n')


# ── 依赖检查 ──
def check_prerequisite(file_path: str, max_age_minutes: int = 15) -> bool:
    """检查前置文件是否存在且未过期。"""
    if not os.path.exists(file_path):
        return False
    age_sec = time.time() - os.path.getmtime(file_path)
    return age_sec < max_age_minutes * 60


def check_tail_baseline(today: str) -> bool:
    """尾盘基准快照是否就绪（14:30 产出）。"""
    return check_prerequisite(os.path.join(DATA, f'tail_baseline_{today}.json'), 15)


# ── 任务统一入口 ──
def run_task(task_name: str, analyze_fn, data_requirements: dict = None,
             template_name: str = None, publish: bool = True) -> str:
    """
    任务统一运行器。
    - task_name: 任务名（用于日志、输出目录）
    - analyze_fn: 分析函数，接收 (today_date_str) → 返回 ReportData
    - template_name: 渲染模板名（morning|midday|tail|market|alert）
    - publish: 是否执行 git publish
    """
    started = time.time()

    try:
        today = get_today_str()

        # 1. DAG依赖检查
        ready, missing, detail = check_dependency(task_name, today)
        if not ready:
            audit_log(task_name, 'SKIP_DEP', detail)
            print(f'[runner] SKIP: dependency not ready → {detail}')
            return f'SKIPPED: {detail}'

        # 2. 执行分析
        print(f'[runner] {task_name}: analyzing...')
        report_data = analyze_fn(today) if analyze_fn else None

        # 3. 写结构化 JSON（如果有标准化输出）
        if report_data:
            out_dir = os.path.join(REPORTS, today)
            os.makedirs(out_dir, exist_ok=True)
            json_name = f'{task_name}_{today}.json'
            json_path = os.path.join(out_dir, json_name)
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(report_data.to_dict() if hasattr(report_data, 'to_dict') else report_data,
                          f, ensure_ascii=False, indent=2)
            print(f'[runner] JSON saved: {json_path} ({os.path.getsize(json_path)} bytes)')

        # 4. 渲染 HTML（统一渲染层）
        if template_name:
            from render.render import render as render_html
            render_html(template_name, today)

        # 5. 重建索引 & 发布(带重试)
        if publish:
            for script in ['rebuild_index.sh', 'publish.sh']:
                sp = os.path.join(ROOT, script)
                if not os.path.exists(sp):
                    continue
                for attempt in range(3):
                    r = subprocess.run(['bash', sp], cwd=ROOT, capture_output=True, text=True)
                    if r.returncode == 0 or 'Everything up-to-date' in r.stdout:
                        break
                    if attempt < 2:
                        print(f'[runner] {script} retry {attempt+1}/3...')
                        time.sleep(2 ** attempt)
                    else:
                        audit_log(task_name, 'PUB_FAIL', f'{script} failed after 3 retries')

        elapsed = (time.time() - started) * 1000
        audit_log(task_name, 'OK', f'template={template_name}', elapsed)
        return 'OK'

    except Exception as e:
        elapsed = (time.time() - started) * 1000
        detail = f'{e.__class__.__name__}: {e}'
        audit_log(task_name, 'FAIL', detail, elapsed)
        traceback.print_exc()
        return f'FAIL: {detail}'


# ── 快速辅助 ──
def bare_completion(task_name: str, message: str = 'done', publish: bool = False):
    """最简完成记录（无分析，仅日志+发布）。"""
    started = time.time()
    print(f'[runner] {task_name}: {message}')
    if publish:
        for script in ['rebuild_index.sh', 'publish.sh']:
            sp = os.path.join(ROOT, script)
            if os.path.exists(sp):
                subprocess.run(['bash', sp], cwd=ROOT, check=False)
    elapsed = (time.time() - started) * 1000
    audit_log(task_name, 'OK' if message else 'DONE', message, elapsed)
