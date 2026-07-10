# src/render/render.py
# 统一渲染层(Phase 4): 合并5个 make_*_html.py → 单一路由。
# 当前阶段为包装层(零风险): 根据 template_name 委托现有生成器。
# 后续可渐进迁移模板到 Jinja2, 改一处所有报告自动升级。
import os, sys, subprocess

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data')

# 模板→生成器映射
_RENDERERS = {
    'morning': 'make_morning_html.py',
    'midday':  'make_midday_html.py',
    'tail':    'make_tail_html.py',
    'market':  'make_market_html.py',
    'alert':   'make_html.py',       # 通用回顾式(晚间复盘)
}

def render(template: str, date_str: str) -> bool:
    """渲染指定模板的HTML报告。
    template: morning|midday|tail|market|alert
    date_str: YYYY-MM-DD"""
    if template not in _RENDERERS:
        print(f'[render] unknown template: {template}')
        return False
    script = os.path.join(DATA, _RENDERERS[template])
    if not os.path.exists(script):
        print(f'[render] generator not found: {script}')
        return False
    result = subprocess.run(['python', script, date_str], cwd=DATA, capture_output=True, text=True)
    if result.returncode == 0:
        print(f'[render] {template} done: {result.stdout.strip()[-80:]}')
        return True
    print(f'[render] {template} FAIL: {result.stderr[:200]}')
    return False

def list_templates() -> list:
    return list(_RENDERERS.keys())
