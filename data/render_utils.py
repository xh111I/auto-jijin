# -*- coding: utf-8 -*-
"""
render_utils.py  —  报告生成器共享工具库（v2 · 方法论适配版）

功能：
  1. 统一工具函数（esc/tip/num/pcls/pbold/chg_cell/chg_span等）
  2. 规则引擎配置（RULES 常量字典，集中管理所有格式化阈值与触发条件）
  3. 自动计算公式（风险评分、止损空间、仓位校验）
  4. 缺失值标准化
  5. 预警阈值触发

使用方法：
  from render_utils import esc, tip, chg_cell, chg_span, bar, ...

色板与信号体系（与所有 make_*_html.py 统一）：
  涨跌幅 → 红涨绿跌（A股惯例）
  信号等级 → 多=绿系 / 空=红系（与涨跌价独立轴）
  强度标签 → 强=红 / 中=橙 / 弱=灰
  操作标签 → 持有=绿 / 减仓=红 / 警惕=橙 / 观望=蓝
  风险标签 → 高=红 / 中=橙 / 低=黄
"""

import re
import json
import datetime
from typing import Optional, Union

# ============================================================
#  一、统一色板 & 规则引擎配置（方法论 · 三、样式与预警层）
#  所有阈值在此修改，所有生成器自动生效
# ============================================================
RULES = {
    # ── 涨跌幅格式化 ──
    "chg_bold_thr": 2.0,         # ±2% 加粗（个股/板块）
    "chg_market_bold_thr": 3.0,  # 大盘研判用 ±3% 加粗（更宽松）
    "chg_highlight_thr": 5.0,    # ±5% 追加红色高亮

    # ── 仓位预警阈值 ──
    "pos_warn_yellow": 25,       # 仓位≥25% 标橙提示
    "pos_warn_red": 29,          # 仓位≥29% 标红 + 追加「逼近30%上限」
    "pos_max_single": 30,        # 单仓硬上限

    # ── 板块/指数预警 ──
    "sector_drop_alert": 3.0,    # 板块单日跌≥3% → 红色强风险标识
    "pre_close_reverse": 0.5,    # 盘前与隔夜反向≥0.5% → "盘前转向"标签
    "semic_concentration": 60,   # 半导体集中度≥60% → 极高集中度风险

    # ── 风险评分权重（方法论 · 四、逻辑计算层） ──
    "risk_weight": {
        "sentiment": 0.30,       # 情绪面 30%
        "technical": 0.25,       # 技术面 25%
        "event": 0.20,           # 风险事件 20%
        "capital": 0.15,         # 资金面 15%
        "news": 0.10,            # 新闻面 10%
    },

    # ── 止损阈值 ──
    "stop_loss_pct": -8.0,       # -8% 强制止损
    "risk_dist_high": 70,        # 距止损进度≥70% → 高风险
    "risk_dist_mid": 40,         # 距止损进度≥40% → 中风险

    # ── 情绪指标阈值 ──
    "fear_greed": {
        "extreme_fear": 20,      # 0-20 极度恐惧
        "fear": 40,              # 20-40 恐惧
        "neutral_low": 40,       # 40-60 中性
        "neutral_high": 60,
        "greed": 80,             # 60-80 贪婪
        # 80-100 极度贪婪
    },

    # ── 总仓位约束 ──
    "total_pos_max": 90,         # 总仓位≤90%

    # ── 缺失值标准文本 ──
    "missing_val": "—",          # 缺失值标准显示
    "missing_note": "(盘后更新)", # 缺失值注释
    "missing_api": "数据源未返回",  # API 缺失时的标注
    "missing_pending": "待验证",  # T2 级数据标注
}


# ============================================================
#  二、基础工具函数（方法论 · 二、内容结构层 · 组件化拼装）
# ============================================================

def esc(s) -> str:
    """HTML 转义（XSS 防护）。"""
    if s is None:
        return ""
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def tip(s: str) -> str:
    """把 [[术语|解释]] 转为带悬停提示的 span。先转义 HTML 再替换。"""
    s = esc(s)
    def repl(m):
        term = m.group(1)
        exp = m.group(2).replace('"', "&quot;")
        return '<span class="tip" data-tip="%s">%s</span>' % (exp, term)
    return re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", repl, s)


def num(v) -> Optional[float]:
    """安全转浮点，None/异常 → None。"""
    if v is None:
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


# ── 缺失值标准化（方法论 · 一、数据源层） ──

def missing_val(key: str = "default") -> str:
    """根据场景返回标准化缺失值文本。
    
    用例: 普通表格 → "—"，净值待更新 → "— (盘后更新)"，API失败 → "数据源未返回"
    """
    table = {
        "default": RULES["missing_val"],
        "nav": f"{RULES['missing_val']} ({RULES['missing_note']})",
        "api": RULES["missing_api"],
        "pending": RULES["missing_pending"],
    }
    return table.get(key, table["default"])


def r2(val, suffix: str = "") -> str:
    """千分位+2位小数。用于价格/金额/市值等非涨跌幅数值。
    例: 13873.99 → "13,873.99"，None → "—"
    """
    v = num(val)
    if v is None:
        return missing_val()
    # 千分位
    s = f"{v:,.2f}{suffix}"
    return s


# ── 涨跌幅格式化（方法论 · 三、样式与预警层） ──

def pcls(v) -> str:
    """值→CSS类: up/down/neu（红涨绿跌）。"""
    v = num(v)
    if v is None:
        return "neu"
    if v > 0.05:
        return "up"
    if v < -0.05:
        return "down"
    return "neu"


def pbold(v, thr: Optional[float] = None) -> bool:
    """是否加粗（绝对值≥阈值）。默认走 RULES['chg_bold_thr']=2.0%。
    大盘研判可传 thr=3.0 使用更宽松阈值。"""
    if thr is None:
        thr = RULES["chg_bold_thr"]
    v = num(v)
    return v is not None and abs(v) >= thr


def phighlight(v, thr: Optional[float] = None) -> bool:
    """是否红色高亮（绝对值≥阈值）。默认 RULES['chg_highlight_thr']=5.0%"""
    if thr is None:
        thr = RULES["chg_highlight_thr"]
    v = num(v)
    return v is not None and abs(v) >= thr


def chg_cell(v, thr: Optional[float] = None, suffix: str = "%") -> str:
    """涨跌幅表格单元格：红涨绿跌，自动加粗/高亮。"""
    v = num(v)
    if v is None:
        return f'<td class="neu">{missing_val("nav")}</td>'
    cls = pcls(v)
    b = " b" if pbold(v, thr) else ""
    hl = " hl" if phighlight(v) else ""
    sign = "+" if v > 0 else ""
    return '<td class="%s%s%s">%s%.2f%s</td>' % (cls, b, hl, sign, v, suffix)


def chg_span(v, thr: Optional[float] = None, suffix: str = "%") -> str:
    """涨跌幅行内 span（非单元格）。"""
    v = num(v)
    if v is None:
        return f'<span class="neu">{missing_val()}</span>'
    cls = pcls(v)
    b = " b" if pbold(v, thr) else ""
    sign = "+" if v > 0 else ""
    return '<span class="%s%s">%s%.2f%s</span>' % (cls, b, sign, v, suffix)


def bar(score, cls: str) -> str:
    """进度条 HTML（score: 0-100, cls: CSS 类）。"""
    s = num(score) or 0
    s = max(0, min(100, int(round(s))))
    return '<div class="bar"><i class="%s" style="width:%d%%"></i></div>' % (cls, s)


# ============================================================
#  三、信号等级映射（方法论 · 二、内容结构层 · 统一信号体系）
# ============================================================

SIGNAL_MAP = {
    "强多": "lv-strong-up",
    "偏多": "lv-up",
    "中性偏多": "lv-neu-up",
    "中性偏空": "lv-neu-down",
    "偏空": "lv-down",
    "强空": "lv-strong-down",
}

def level_info(score, label=None):
    """分数→多空等级 (css类, 等级中文)。"""
    if label and label in SIGNAL_MAP:
        return SIGNAL_MAP[label], label
    s = num(score) or 0
    if s >= 80:
        return "lv-strong-up", "强多"
    if s >= 60:
        return "lv-up", "偏多"
    if s >= 50:
        return "lv-neu-up", "中性偏多"
    if s >= 40:
        return "lv-neu-down", "中性偏空"
    if s >= 20:
        return "lv-down", "偏空"
    return "lv-strong-down", "强空"


def str_tag(s):
    """强度标签 强/中/弱 → (css, 文本)。"""
    m = {"强": "s-strong", "中": "s-mid", "弱": "s-weak"}
    return m.get(s, "s-weak"), s


def act_tag(a):
    """操作标签 持有/减仓/警惕/观望 → (css, 文本)。"""
    m = {"持有": "a-hold", "减仓": "a-reduce", "警惕": "a-warn", "观望": "a-watch"}
    return m.get(a, "a-watch"), a


def risk_cls(r):
    """风险标签 高/中/低 → (css, 文本)。"""
    m = {"高": "rk-high", "中": "rk-mid", "低": "rk-low"}
    return m.get(r, "rk-mid"), r


# ============================================================
#  四、仓位与收益单元格（早报/午盘/尾盘共用）
# ============================================================

def wt_cell(v):
    """仓位占比单元格，超阈值标橙。"""
    v = num(v)
    if v is None:
        return f'<td class="neu">{missing_val()}</td>'
    if v >= RULES["pos_warn_red"]:
        # ≥29% 标红 + 警告
        return ('<td class="r" style="font-weight:700;font-size:15px;'
                'background:rgba(245,86,77,.12);padding:2px 6px;border-radius:4px">'
                '%.1f%%<span class="sc" style="color:#ff6b61;font-size:10px;margin-left:4px">⚠逼近上限</span></td>' % v)
    if v >= RULES["pos_warn_yellow"]:
        # ≥25% 标橙
        return ('<td class="r" style="font-weight:600;color:#d9a441">%.1f%%</td>' % v)
    return '<td class="r">%.1f%%</td>' % v


def ret_cell(v):
    """持有收益单元格，红涨绿跌。"""
    v = num(v)
    if v is None:
        return f'<td class="neu">{missing_val()}</td>'
    cls = pcls(v)
    sign = "+" if v > 0 else ""
    return '<td class="r %s">%s%.2f%%</td>' % (cls, sign, v)


# ============================================================
#  五、逻辑计算引擎（方法论 · 四、逻辑计算层）
# ============================================================

def calc_risk_score(components: dict) -> dict:
    """风险综合评分自动计算。
    
    输入: {
        "sentiment": 0-100,    # 情绪面得分
        "technical": 0-100,    # 技术面得分
        "event": 0-100,        # 风险事件得分（越高=事件越负面）
        "capital": 0-100,      # 资金面得分
        "news": 0-100,         # 新闻面得分
    }
    输出: {
        "score": 0-100,        # 综合风险评分（0=低风险, 100=高风险）
        "details": {...},      # 各维度加权详情
        "level": "低风险|中风险|偏高|高",
    }
    """
    w = RULES["risk_weight"]
    details = {}
    weighted_sum = 0.0
    
    for key, weight in w.items():
        raw = num(components.get(key)) or 50
        # 情绪面取反：高情绪分→低风险，低情绪分→高风险
        if key == "sentiment":
            raw = 100 - raw
        scored = raw * weight
        details[key] = {
            "raw": raw,
            "weight": weight,
            "scored": round(scored, 1),
        }
        weighted_sum += scored
    
    score = round(weighted_sum, 1)
    
    if score <= 35:
        level = "低风险"
    elif score <= 55:
        level = "中等风险"
    elif score <= 75:
        level = "偏高"
    else:
        level = "高风险"
    
    return {
        "score": score,
        "details": details,
        "level": level,
    }


def calc_stop_loss_dist(hold_return_pct: float, stop_loss_pct: float = None) -> dict:
    """计算距止损的精确剩余空间。
    
    参数:
        hold_return_pct: 当前持有收益率%（如 +7.07）
        stop_loss_pct: 止损线%（如 -8.0），默认取 RULES
        
    返回:
        {"remaining_pct": float,    # 剩余下跌空间%（正数=还有空间）
         "progress_pct": float,     # 已消耗的止损进度%（0-100）
         "level": "高|中|低",       # 风险等级
         "level_cls": "rk-high|rk-mid|rk-low",
         "color": "#ff6b61|#d9a441|#e8c33a"}
    """
    if stop_loss_pct is None:
        stop_loss_pct = RULES["stop_loss_pct"]
    
    hr = num(hold_return_pct)
    sl = num(stop_loss_pct)
    
    if hr is None or sl is None or sl >= 0:
        return {
            "remaining_pct": None,
            "progress_pct": 0,
            "level": "—", "level_cls": "", "color": "#3a4250",
        }
    
    # 从当前收益到止损线的跌幅
    remaining = hr - sl  # 如 7.07% - (-8%) = 15.07%
    # 已消耗的止损进度
    total_range = abs(sl)  # 如 8%
    consumed = max(0, total_range - remaining)  # 已消耗部分
    if total_range > 0:
        progress = min(100, round(consumed / total_range * 100))
    else:
        progress = 0
    
    # 等级判定
    if progress >= RULES["risk_dist_high"]:
        level, level_cls, color = "高", "rk-high", "#ff6b61"
    elif progress >= RULES["risk_dist_mid"]:
        level, level_cls, color = "中", "rk-mid", "#d9a441"
    else:
        level, level_cls, color = "低", "rk-low", "#e8c33a"
    
    return {
        "remaining_pct": round(remaining, 2),
        "progress_pct": progress,
        "level": level,
        "level_cls": level_cls,
        "color": color,
    }


def calc_semic_concentration(holdings: list) -> dict:
    """计算半导体赛道集中度风险。
    
    输入: [{"name": "基金名", "weight_pct": 36.62, "sector": "半导体材料设备/AI"}, ...]
    输出: {"total_pct": float, "alert": bool, "over_thr": bool}
    """
    total = 0.0
    semic_keywords = ["半导体", "芯片", "AI", "人工智能", "集成电路", "通信设备", "CPO"]
    for h in holdings:
        sector = (h.get("sector") or "") + (h.get("name") or "")
        if any(kw in sector for kw in semic_keywords):
            total += num(h.get("weight_pct")) or 0
    total = round(total, 1)
    return {
        "total_pct": total,
        "over_thr60": total >= RULES["semic_concentration"],
    }


# ============================================================
#  六、预警条件触发（方法论 · 三、样式与预警层 · 规则引擎）
# ============================================================

def check_alerts(holdings: list, index_data: dict = None) -> list:
    """批量检查所有预警条件，返回触发列表。
    
    返回值: [{"level": "red|orange|yellow", "text": str, "target": str|None}, ...]
    """
    alerts = []
    
    # 1. 单基金仓位≥29% → 橙色预警 + 逼近30%上限
    for h in (holdings or []):
        wp = num(h.get("weight_pct"))
        if wp is not None and wp >= RULES["pos_warn_red"]:
            alerts.append({
                "level": "orange",
                "text": "%s仓位%.1f%% 逼近30%%上限" % (h.get("name", ""), wp),
                "target": h.get("name"),
            })
    
    # 2. 半导体集中度≥60% → 红色预警
    semic = calc_semic_concentration(holdings or [])
    if semic["over_thr60"]:
        alerts.append({
            "level": "red",
            "text": "半导体赛道集中度%.1f%% 极高集中度风险" % semic["total_pct"],
            "target": "半导体板块",
        })
    
    # 3. 板块单日跌幅≥3% → 红色预警（需传入 index_data）
    if index_data:
        for idx_name, idx_info in index_data.items():
            chg = num(idx_info.get("chg")) if isinstance(idx_info, dict) else None
            if chg is not None and chg <= -RULES["sector_drop_alert"]:
                alerts.append({
                    "level": "red",
                    "text": "%s单日跌%.2f%%，触发强风险" % (idx_name, chg),
                    "target": idx_name,
                })
    
    return alerts


# ============================================================
#  七、日期工具
# ============================================================

def yesterdate(d: str) -> str:
    """返回日期的昨日 ISO 格式。"""
    dt = datetime.date.fromisoformat(d)
    return (dt - datetime.timedelta(days=1)).isoformat()


def risk_dist_html(rd_val) -> str:
    """距止损进度HTML（含进度条 + 文本标签），
    替换原 `risk_dist()` 函数的单值返回。
    """
    rd = num(rd_val)
    if rd is None:
        return f'<td class="neu">{missing_val()}</td>'
    rd = int(round(max(0, min(100, rd))))
    if rd >= RULES["risk_dist_high"]:
        cls, col = "rk-high", "#ff6b61"
    elif rd >= RULES["risk_dist_mid"]:
        cls, col = "rk-mid", "#d9a441"
    else:
        cls, col = "rk-low", "#e8c33a"
    bar_html = '<div class="bar" style="display:inline-block;width:60px;vertical-align:middle;margin-right:4px"><i style="width:%d%%;background:%s"></i></div>' % (rd, col)
    txt = '<span class="%s">%d%%</span>' % (cls, rd)
    return '<td>%s %s</td>' % (bar_html, txt)
