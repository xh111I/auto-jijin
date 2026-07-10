# src/orchestrator/dag.py
# 任务依赖DAG(Phase 5): 定义任务执行顺序与前置校验。
# 所有任务跑前校验前置是否成功, 失败则重试/跳过/告警。
import os, time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, 'data')

# ── DAG 定义 ──
# {task_id: {depends_on: [task_id,...], check: fn()→bool, max_wait_sec}}
TASK_DAG = {
    '尾盘监控基准': {
        'depends_on': [],
        'output_file': lambda d: os.path.join(DATA, f'tail_baseline_{d}.json'),
        'description': '14:30大盘快照,无前置依赖'
    },
    '尾盘决策': {
        'depends_on': ['尾盘监控基准'],
        'output_file': lambda d: os.path.join(DATA, f'tail_{d}.json'),
        'max_wait_sec': 300,       # 等待监控基准最多5分钟
        'description': '14:45决策,依赖14:30基准快照'
    },
    '早间全球分析': {
        'depends_on': [],
        'output_file': lambda d: os.path.join(DATA, f'early-morning_{d}.json'),
        'description': '09:00独立,无前置依赖'
    },
    '午盘收盘分析': {
        'depends_on': ['早间全球分析'],
        'output_file': lambda d: os.path.join(DATA, f'midday_{d}.json'),
        'max_wait_sec': 0,         # 不等待(早间必已完成或跳过)
        'description': '11:30,依赖早间(软依赖,上午未出则跳过校验)'
    },
    '大盘·板块·日K研判': {
        'depends_on': [],
        'output_file': lambda d: os.path.join(DATA, f'market_{d}.json'),
        'description': '15:30独立,需收盘数据'
    },
    '基金晚间复盘': {
        'depends_on': ['早间全球分析', '午盘收盘分析', '尾盘决策', '大盘·板块·日K研判'],
        'output_file': None,       # 输出到 reports/ 不依赖单一JSON
        'max_wait_sec': 0,
        'description': '22:30全链路回溯,软依赖全部前置任务'
    },
    '盘中预警': {
        'depends_on': [],
        'output_file': None,
        'description': '每10分钟独立运行,无依赖'
    },
    'Git推送探活': {
        'depends_on': [],
        'output_file': None,
        'description': '每小时独立,无依赖'
    },
}

def check_dependency(task_name: str, today: str) -> tuple:
    """检查任务前置依赖是否就绪。
    返回: (ready: bool, missing: [dep_name], detail: str)
    """
    dag = TASK_DAG.get(task_name, {})
    deps = dag.get('depends_on', [])
    
    if not deps:
        return (True, [], '无前置依赖')
    
    missing = []
    for dep_name in deps:
        dep_dag = TASK_DAG.get(dep_name, {})
        output_fn = dep_dag.get('output_file')
        if output_fn:
            fpath = output_fn(today)
            if not os.path.exists(fpath):
                missing.append(f'{dep_name}(文件缺失: {os.path.basename(fpath)})')
                continue
            # 检查文件是否过期(超过2小时)
            if time.time() - os.path.getmtime(fpath) > 7200:
                missing.append(f'{dep_name}(文件过期>2h)')
    
    if missing:
        return (False, missing, '; '.join(missing))
    return (True, [], '全部前置就绪')


def list_all_deps() -> dict:
    """列出所有任务的依赖关系(审计/文档)。"""
    return {name: {'depends_on': d['depends_on'], 'desc': d['description']}
            for name, d in TASK_DAG.items()}
