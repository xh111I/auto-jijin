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


# ── 规则引擎校验 ──
def validate_decision(decision_data: dict, strategy: dict = None) -> list:
    """
    DeepSeek V4 Flash 输出落盘前的规则引擎强制校验。
    修正突破硬约束的数值，返回修正记录列表供埋点统计。
    :param decision_data: 模型输出的完整JSON字典
    :param strategy: strategy.json 加载的硬约束配置；None时自动加载
    :return: corrections 修正记录列表
    """
    if strategy is None:
        try:
            _SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if _SRC not in sys.path:
                sys.path.insert(0, _SRC)
            from data_service.fetcher import load_strategy
            strategy = load_strategy()
        except Exception:
            strategy = {}

    trading = strategy.get('trading', {})
    single_limit = trading.get('max_single_position_pct', 30)
    total_limit = trading.get('target_total_position_pct', 90)
    stop_loss_limit = trading.get('stop_loss_pct', -8)
    take_profit_limit = trading.get('take_profit_pct', 15)

    corrections = []
    position_adjust = decision_data.get('position_adjust', [])
    total_target_pct = 0

    # 1. 单仓上限校验
    for item in position_adjust:
        pct = item.get('target_position_pct', 0)
        if pct > single_limit:
            corrections.append({
                'field': 'target_position_pct',
                'symbol': item.get('symbol', ''),
                'original': pct,
                'corrected': single_limit,
                'reason': f'单仓突破上限{single_limit}%'
            })
            item['target_position_pct'] = single_limit
        total_target_pct += item.get('target_position_pct', 0)

    # 2. 总仓上限校验（超标则等比例压缩）
    if total_target_pct > total_limit:
        corrections.append({
            'field': 'total_position_pct',
            'original': round(total_target_pct, 2),
            'corrected': total_limit,
            'reason': f'总仓突破上限{total_limit}%'
        })
        ratio = total_limit / total_target_pct
        for item in position_adjust:
            item['target_position_pct'] = round(item['target_position_pct'] * ratio, 2)

    # 3. 止损阈值校验
    stop_loss_pct = decision_data.get('stop_loss_pct', 0)
    if stop_loss_pct > stop_loss_limit and stop_loss_pct != 0:
        corrections.append({
            'field': 'stop_loss_pct',
            'original': stop_loss_pct,
            'corrected': stop_loss_limit,
            'reason': f'止损阈值宽松于硬约束{stop_loss_limit}%'
        })
        decision_data['stop_loss_pct'] = stop_loss_limit

    # 4. 止盈阈值校验
    take_profit_pct = decision_data.get('take_profit_pct', 0)
    if 0 < take_profit_pct < take_profit_limit:
        corrections.append({
            'field': 'take_profit_pct',
            'original': take_profit_pct,
            'corrected': take_profit_limit,
            'reason': f'止盈阈值宽松于硬约束{take_profit_limit}%'
        })
        decision_data['take_profit_pct'] = take_profit_limit

    # 修正记录写入埋点
    decision_data['_telemetry'] = decision_data.get('_telemetry', {})
    decision_data['_telemetry']['rule_corrections'] = corrections
    decision_data['_telemetry']['validate_ts'] = datetime.now().isoformat()

    if corrections:
        print(f'[validate] {len(corrections)} correction(s) applied')

    return corrections
