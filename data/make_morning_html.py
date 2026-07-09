# -*- coding: utf-8 -*-
"""
make_morning_html.py  —  早间全球分析（盘前推送）报告生成器
读取 data/early-morning_<DATE>.json（由自动化 agent 在 neodata 分析后落盘的结构化数据），
渲染为优化版 早间全球分析-<DATE>.html。

优化点（对应需求 P0/P1/P2）：
  P0  ① 首屏「盘前核心定调」总览卡（情绪进度条 + 一句话结论 + 操作铁律红框 + 最高风险橙条）
       ② 模块顺序重排：定调→全球涨跌→风险事件→利好利空→持仓指引→公司财报→技术面→事件日历→免责
       ③ 统一信号等级体系（强度:强/中/弱；操作:持有/减仓/警惕/观望；风险:高红/中橙/低黄）
  P0  全球涨跌表分组(美股/欧股/亚太/大宗/汇率) + 重点行高亮 + 涨跌标准化(红涨绿跌±2%加粗) + 信号标签化 + 置信度图标
       持仓操作表强化(仓位占比列/持有收益红绿 + 距止损进度条/建议动作标签/底部红色约束条)
       利好利空左右分栏卡片列表
  P1  风险事件结构化(事件等级→事实→传导链→持仓影响)；技术面精简(MACD/KDJ折叠)；今日事件时间线
       交互可视化：全球涨跌幅条形图(ECharts) / 仓位环形图(ECharts) / 情绪仪表盘(ECharts)
       顶部固定导航 / 折叠 / 术语悬停
  P2  时间标注统一 / 缺失数据标准化 / 响应式 / 历史报告入口 / 打印样式

视觉与信号体系：与收盘报告(make_html.py)、大盘研判(make_market_html.py) 完全统一
  —— 同一套深色配色板 + 同一套 level_info 信号映射 + 同一套 [[术语|解释]] 悬停。

色彩规则：
  涨跌幅  → 红涨绿跌（A股惯例，守 color board --up/--down）
  信号等级 → 多=绿系 / 空=红系（与涨跌价独立轴，页面有图例）
  强度标签 → 强=红 / 中=橙 / 弱=灰（事件强度，与涨跌价/多空无关，页面有图例）
  操作标签 → 持有=绿 / 减仓=红 / 警惕=橙 / 观望=蓝
  风险标签 → 高=红 / 中=橙 / 低=黄
"""
import json
import os
import sys
import glob
import re
import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
REPORTS = os.path.join(BASE, "reports")
CRED_TIER = "T1"

# ---------- 工具函数（与 make_market_html.py 保持一致） ----------
def esc(s):
    if s is None:
        return ""
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))

def tip(s):
    """把 [[术语|解释]] 转为带悬停提示的 span。先转义 HTML 再替换。"""
    s = esc(s)
    def repl(m):
        term = m.group(1)
        exp = m.group(2).replace('"', "&quot;")
        return '<span class="tip" data-tip="%s">%s</span>' % (exp, term)
    return re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", repl, s)

def num(v):
    if v is None:
        return None
    try:
        return float(v)
    except Exception:
        return None

def level_info(score, label=None):
    """分数→(css类, 等级中文)。label 优先（与用户等级表一致）。"""
    m = {"强多": "lv-strong-up", "偏多": "lv-up", "中性偏多": "lv-neu-up",
          "中性偏空": "lv-neu-down", "偏空": "lv-down", "强空": "lv-strong-down"}
    if label and label in m:
        return m[label], label
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

def pcls(v):
    v = num(v)
    if v is None:
        return "neu"
    if v > 0.05:
        return "up"
    if v < -0.05:
        return "down"
    return "neu"

def pbold(v, thr=2.0):
    v = num(v)
    return v is not None and abs(v) >= thr

def chg_cell(v, thr=2.0, suffix="%"):
    """涨跌幅单元格：红涨绿跌，±thr% 加粗。"""
    v = num(v)
    if v is None:
        return '<td class="neu">—</td>'
    cls = pcls(v)
    b = " b" if pbold(v, thr) else ""
    sign = "+" if v > 0 else ""
    return '<td class="%s%s">%s%.2f%s</td>' % (cls, b, sign, v, suffix)

def chg_span(v, thr=2.0, suffix="%"):
    """涨跌幅行内 span（非单元格，用于折叠 summary 等）。"""
    v = num(v)
    if v is None:
        return '<span class="neu">—</span>'
    cls = pcls(v)
    b = " b" if pbold(v, thr) else ""
    sign = "+" if v > 0 else ""
    return '<span class="%s%s">%s%.2f%s</span>' % (cls, b, sign, v, suffix)

def bar(score, cls):
    s = num(score) or 0
    s = max(0, min(100, int(round(s))))
    return '<div class="bar"><i class="%s" style="width:%d%%"></i></div>' % (cls, s)

def yesterdate(d):
    dt = datetime.date.fromisoformat(d)
    return (dt - datetime.timedelta(days=1)).isoformat()

# ---------- 早报专用信号标签 ----------
def str_tag(s):
    """强度标签 强/中/弱 → (css, 文本)。强=红, 中=橙, 弱=灰（事件强度，非多空）。"""
    m = {"强": "s-strong", "中": "s-mid", "弱": "s-weak"}
    return m.get(s, "s-weak"), s

def act_tag(a):
    """操作标签 持有/减仓/警惕/观望 → (css, 文本)。"""
    m = {"持有": "a-hold", "减仓": "a-reduce", "警惕": "a-warn", "观望": "a-watch"}
    return m.get(a, "a-watch"), a

def risk_cls(r):
    """风险标签 高/中/低 → (css, 文本)。高=红, 中=橙, 低=黄。"""
    m = {"高": "rk-high", "中": "rk-mid", "低": "rk-low"}
    return m.get(r, "rk-mid"), r

def wt_cell(v):
    v = num(v)
    if v is None:
        return '<td class="neu">—</td>'
    over = " over" if v > 30 else ""
    return '<td class="r%s">%.1f%%</td>' % (over, v)

def ret_cell(v):
    v = num(v)
    if v is None:
        return '<td class="neu">—</td>'
    cls = pcls(v)
    sign = "+" if v > 0 else ""
    return '<td class="r %s">%s%.2f%%</td>' % (cls, sign, v)

def risk_dist(rd):
    """距 -8% 止损进度：rd 越大=越接近止损=风险越高。
    阈值：≥70 高(红) / 40–70 中(橙) / <40 低(黄)，与收盘报告风险语义对齐。
    返回 (文本, 文本css, 进度条色, 数值)。"""
    rd = num(rd)
    if rd is None:
        return "—", "", "#3a4250", 0
    rd = int(round(max(0, min(100, rd))))
    if rd >= 70:
        cls, col = "rk-high", "#ff6b61"
    elif rd >= 40:
        cls, col = "rk-mid", "#d9a441"
    else:
        cls, col = "rk-low", "#e8c33a"
    return "%d%%" % rd, cls, col, rd

# ---------- 各模块渲染 ----------
def render_core(core, sentiment):
    if not core:
        return ""
    # 情绪进度条
    bars = ""
    for mb in (core.get("mood_bars") or []):
        score = num(mb.get("score")) or 0
        if (score or 0) >= 60:
            cls = "lv-up"
        elif (score or 0) >= 40:
            cls = "lv-neu-up"
        else:
            cls = "lv-down"
        bars += ('<div class="mood-row"><span class="m-k">%s</span>'
                 '<div class="mood-bar"><i class="%s" style="width:%d%%"></i></div>'
                 '<span class="m-v %s">%s %s</span></div>') % (
            esc(mb.get("k", "")), cls, int(round(score)), cls,
            esc(mb.get("score", "")), esc(mb.get("label", "")))
    one = tip(core.get("one_liner", ""))
    rule = tip(core.get("action_rules", ""))
    top = tip(core.get("top_risk", ""))
    # 情绪仪表盘（半导体情绪，次级）
    semi = (sentiment or {}).get("semiconductor") or {}
    semi_score = num(semi.get("score"))
    semi_html = ""
    if semi_score is not None:
        semi_html = ('<div class="gauge-mini"><div id="sentGauge" style="width:200px;height:120px"></div>'
                     '<div class="gauge-cap">半导体情绪 <b class="lv-down">%s</b> · %s</div></div>') % (
            esc(semi.get("score", "")), esc(semi.get("label", "")))
    return f'''
<section id="core" class="core-card">
  <div class="core-head">🌅 盘前核心定调 <span class="badge">开盘前30秒决策</span></div>
  <div class="mood-bars">
    {bars}
    {semi_html}
  </div>
  <div class="core-line"><span class="cl-k">一句话结论</span><span class="cl-v">{one}</span></div>
  <div class="rule-box">🔴 操作铁律：{rule}</div>
  <div class="risk-bar">🟠 最高风险：{top}</div>
  <div class="legend">涨跌配色 <b class="up">红=涨</b>/<b class="down">绿=跌</b>（A股惯例）· 强度标签 🔴强/🟠中/⚪弱（事件强度，与涨跌价无关）· 信号等级 <b class="lv-up">绿=偏多</b>/<b class="lv-down">红=偏空</b>（多空语义，独立轴）</div>
</section>'''

def render_global(groups):
    if not groups:
        return ""
    rows_html = ""
    flat = []
    for g in groups:
        gname = esc(g.get("group", ""))
        grows = g.get("rows") or []
        if not grows:
            continue
        rows_html += '<tr class="grp"><td colspan="5">%s</td></tr>' % gname
        for r in grows:
            chg = num(r.get("chg"))
            flat.append({"name": r.get("name"), "chg": chg})
            tier = r.get("tier") or "T1"
            tcls = "tag-t1" if tier == "T1" else "tag-t2"
            signal = tip(r.get("signal", ""))
            key = r.get("key")
            warn = r.get("warn")
            hl = " hl-row" if (key or warn) else ""
            keybadge = ' <span class="tag-warn">关键</span>' if key else ""
            warnbadge = (' <span class="tag-warn">%s</span>' % esc(warn)) if warn else ""
            src = '<span class="%s">%s</span>' % (tcls, esc(tier))
            rows_html += ('<tr class="%s"><td class="lname">%s</td><td>%s</td>%s<td>%s%s%s</td><td>%s</td></tr>') % (
                hl, tip(r.get("name", "")), esc(r.get("close", "—")),
                chg_cell(chg, 2.0),
                src, keybadge, warnbadge, signal)
    note = ('<div class="note">📌 涨跌配色遵循 A 股惯例：<b class="up">红=涨</b> / <b class="down">绿=跌</b>；'
            '±2% 加粗；重点行（关键标的/地缘相关）已高亮；置信度 T1=实时行情/T2=新闻交叉。</div>')
    return f'''
<section id="global" class="card">
  <h2>① 全球股市 / 大宗 / 汇率 涨跌 <span class="badge">{len(flat)} 标的</span></h2>
  <div class="chart-wrap"><canvas id="chgBar"></canvas></div>
  <div class="tbl-scroll">
  <table>
    <tr><th>市场 / 标的</th><th>收盘/最新</th><th>涨跌</th><th>来源/置信</th><th>信号</th></tr>
    {rows_html}
  </table>
  </div>
  {note}
</section>'''

def render_conflicts(conflicts):
    if not conflicts:
        return ""
    boxes = ""
    for c in conflicts:
        lv = c.get("level") or "orange"
        cls = {"red": "cf-red", "orange": "cf-orange", "yellow": "cf-yellow"}.get(lv, "cf-orange")
        icon = {"red": "🔴", "orange": "🟠", "yellow": "🟡"}.get(lv, "🟠")
        fact = tip(c.get("body", ""))
        chain = tip(c.get("chain", ""))
        impact = tip(c.get("impact", ""))
        chain_html = ('<div class="cf-chain"><b>传导链：</b>%s</div>' % chain) if chain else ""
        impact_html = ('<div class="cf-impact"><b>持仓影响：</b>%s</div>' % impact) if impact else ""
        boxes += '''
<div class="cf-box %s">
  <div class="cf-title">%s %s</div>
  <div class="cf-body">%s</div>
  %s
  %s
</div>''' % (cls, icon, tip(c.get("title", "")), fact, chain_html, impact_html)
    return f'''
<section id="conflict" class="card">
  <h2>② 风险事件结构化 <span class="badge">事件等级→事实→传导→影响</span></h2>
  {boxes}
</section>'''

def render_bullbear(bulls, bears):
    def cards(lst, kind):
        if not lst:
            return '<div class="note">无</div>'
        out = ""
        for it in lst:
            st_cls, st_txt = str_tag(it.get("strength"))
            target = tip(it.get("target", ""))
            impact = tip(it.get("impact", ""))
            out += ('<div class="bb-item"><span class="str %s">%s</span>'
                    '<div class="bb-txt">%s</div>'
                    '<div class="bb-meta">影响：%s%s</div></div>') % (
                st_cls, st_txt, tip(it.get("text", "")), target,
                (' · %s' % impact) if impact else "")
        return out
    return f'''
<section id="bullbear" class="card">
  <h2>③ 利好 / 利空清单 <span class="badge">逐条标注强度+标的</span></h2>
  <div class="two-col">
    <div class="bull-card">
      <h3 class="bb-h up">✅ 利好</h3>
      <div class="bb-list">{cards(bulls, "bull")}</div>
    </div>
    <div class="bear-card">
      <h3 class="bb-h down">⚠️ 利空</h3>
      <div class="bb-list">{cards(bears, "bear")}</div>
    </div>
  </div>
</section>'''

def render_holdings(hs, constraint):
    if not hs:
        return ""
    rows = ""
    pie = []
    for h in hs:
        act_cls, act_txt = act_tag(h.get("action_tag"))
        lvl_cls, lvl_txt = risk_cls(h.get("risk_level"))
        rd_txt, rd_css, rd_col, rd_val = risk_dist(h.get("risk_dist"))
        pie.append({"name": h.get("name"), "value": num(h.get("weight_pct")) or 0})
        rows += ('<tr>'
                 '<td class="lname">%s</td>'
                 '%s'
                 '%s'
                 '<td><span class="tag %s">%s</span></td>'
                 '<td class="r">%s</td>'
                 '<td class="r %s">%s</td>'
                 '<td><div class="bar"><i style="width:%d%%;background:%s"></i></div><span class="%s">%s</span></td>'
                 '</tr>') % (
            tip(h.get("name", "")),
            wt_cell(h.get("weight_pct")),
            ret_cell(h.get("ret")),
            act_cls, tip(act_txt),
            tip(h.get("signal", "")),
            lvl_cls, lvl_txt,
            rd_val, rd_col, rd_css, rd_txt)
    cons_html = ('<div class="constraint-bar">⚠️ 今日核心约束：%s</div>' % tip(constraint)) if constraint else ""
    return f'''
<section id="hold" class="card">
  <h2>④ 持仓盘前指引 <span class="badge">watchlist T0</span></h2>
  <div class="chart-wrap sm"><canvas id="posPie"></canvas></div>
  <div class="tbl-scroll">
  <table>
    <tr><th>基金</th><th>仓位占比</th><th>持有收益</th><th>盘前信号</th><th>建议动作</th><th>距-8%止损</th></tr>
    {rows}
  </table>
  </div>
  {cons_html}
</section>'''

def render_earnings(earnings):
    if not earnings:
        return ""
    rows = ""
    for e in earnings:
        rows += ('<tr><td class="lname">%s</td>'
                 '<td>%s</td>'
                 '<td>%s</td></tr>') % (
            tip(e.get("name", "")), tip(e.get("dynamic", "")), tip(e.get("impact", "")))
    return f'''
<section id="earn" class="card">
  <h2>⑤ 财报 / 关键公司要点</h2>
  <table>
    <tr><th>标的</th><th>最新动态</th><th>对持仓影响</th></tr>
    {rows}
  </table>
</section>'''

def render_tech(tech):
    if not tech:
        return ""
    blocks = ""
    for t in tech:
        blocks += '''
<details>
  <summary>%s <span class="sc">收盘 %s · 单日 %s</span></summary>
  <div class="tech-grid">
    <div class="dim"><b>MA20</b><span>%s</span></div>
    <div class="dim"><b>MA60</b><span>%s</span></div>
  </div>
  <div class="tech-interp">%s</div>
  <div class="tech-fold">
    <div class="dim"><b>MACD</b><span>%s</span></div>
    <div class="dim"><b>KDJ</b><span>%s</span></div>
  </div>
</details>''' % (
            tip(t.get("index", "")), esc(t.get("close", "—")),
            chg_span(t.get("chg"), 2.0),
            esc(t.get("ma20", "—")), esc(t.get("ma60", "—")),
            tip(t.get("interpret", "")),
            tip(t.get("macd", "—")), tip(t.get("kdj", "—")))
    return f'''
<section id="tech" class="card">
  <h2>⑥ 持仓关联指数技术面 <span class="badge">MA20/MA60 · neodata</span></h2>
  {blocks}
</section>'''

def render_events(events):
    if not events:
        return ""
    items = ""
    for e in events:
        items += ('<div class="tl-item"><span class="tl-time">%s</span>'
                  '<div class="tl-body"><div class="tl-event">%s</div>'
                  '<div class="tl-impact">%s</div></div></div>') % (
            esc(e.get("time", "")), tip(e.get("event", "")), tip(e.get("impact", "")))
    return f'''
<section id="event" class="card">
  <h2>⑦ 今日关键事件时间线</h2>
  <div class="timeline">{items}</div>
</section>'''

def render_cred(cred, disclaimer):
    if not cred and not disclaimer:
        return ""
    rows = ""
    for it in cred or []:
        st = it.get("status", "ok")
        if st == "ok":
            icon, cls = "✅", "ok"
        elif st == "warn":
            icon, cls = "⚠️", "warn"
        else:
            icon, cls = "❓", "q"
        rows += '<div class="kv"><span>%s</span><span class="%s">%s %s</span></div>' % (
            tip(it.get("item", "")), cls, icon, tip(it.get("note", "")))
    disc = ('<div class="note warn">%s</div>' % tip(disclaimer)) if disclaimer else ""
    return f'''
<section id="cred" class="card">
  <h2>⑧ 数据来源与可信度 <span class="badge">{esc(CRED_TIER)}</span></h2>
  <div class="src-box">{rows}</div>
  {disc}
</section>'''

# ---------- 静态 HEAD（含全部 CSS，深色配色板与收盘/大盘研判统一） ----------
HEAD = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>早间全球分析 __DATE__</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
<style>
:root{--up:#f5564d;--down:#26c281;--neu:#d9a441;--acc:#4aa8ff;--bg:#0e1117;--bg2:#161b24;--card:#1c232e;--line:#2a3340;--tx:#e6edf3;--mut:#8b98a9}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--tx);font:14px/1.6 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif;padding:12px;max-width:1080px;margin:0 auto}
.up{color:var(--up)} .down{color:var(--down)} .neu{color:var(--neu)} .acc{color:var(--acc)} .mut{color:var(--mut)}
.b{font-weight:700} .r{text-align:right}
h1{font-size:19px;margin-bottom:2px} .sub{color:var(--mut);font-size:12px;margin-bottom:10px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px;margin-bottom:12px;box-shadow:0 1px 2px rgba(0,0,0,.25)}
.card h2{font-size:16px;margin-bottom:10px;display:flex;align-items:center;gap:6px;border-bottom:1px solid var(--line);padding-bottom:8px}
.badge{font-size:11px;padding:1px 7px;border-radius:6px;background:var(--bg2);color:var(--mut);border:1px solid var(--line);font-weight:400}
table{width:100%;border-collapse:collapse;font-size:12.5px}
.tbl-scroll{max-height:460px;overflow:auto}
th,td{padding:7px 5px;text-align:right;border-bottom:1px solid var(--line)}
th{color:var(--mut);font-weight:400;font-size:11.5px;position:sticky;top:0;background:var(--card);z-index:2}
td:first-child,th:first-child{text-align:left}
tbody tr:nth-child(even){background:rgba(255,255,255,.025)}
tr.grp td{text-align:left;background:var(--bg2);color:var(--acc);font-weight:700;font-size:12px;padding:5px 5px}
tr.hl-row{background:rgba(74,168,255,.07)}
.lname{font-weight:600}
.tag{font-size:11px;padding:1px 6px;border-radius:5px;font-weight:600}
.tag-t1{background:rgba(38,194,129,.16);color:#26c281}
.tag-t2{background:rgba(217,164,65,.16);color:#d9a441}
.tag-warn{background:rgba(245,86,77,.16);color:#f5564d}
.bar{height:6px;border-radius:3px;background:var(--bg2);overflow:hidden;margin-top:3px;display:inline-block;width:64%;vertical-align:middle}
.bar i{display:block;height:100%;border-radius:3px;background:var(--lc)}
.note{color:var(--mut);font-size:11.5px;margin-top:8px;line-height:1.5}
.legend{color:var(--mut);font-size:11px;margin-top:8px;line-height:1.6;border-top:1px dashed var(--line);padding-top:8px}
/* 信号等级（多空语义，与 make_market 统一） */
.lv-strong-up{background:rgba(38,194,129,.30);color:#2ee07a;--lc:#2ee07a}
.lv-up{background:rgba(38,194,129,.16);color:#26c281;--lc:#26c281}
.lv-neu-up{background:rgba(38,194,129,.08);color:#7fd1a8;--lc:#7fd1a8}
.lv-neu-down{background:rgba(245,86,77,.08);color:#e08a85;--lc:#e08a85}
.lv-down{background:rgba(245,86,77,.16);color:#f5564d;--lc:#f5564d}
.lv-strong-down{background:rgba(245,86,77,.30);color:#ff6b61;--lc:#ff6b61}
.lv-up-text{color:#26c281} .lv-down-text{color:#f5564d}
/* 强度/操作/风险 标签 */
.str{display:inline-block;font-size:11px;font-weight:700;padding:1px 7px;border-radius:6px;margin-right:4px}
.s-strong{background:#f5564d;color:#fff} .s-mid{background:#d9a441;color:#1a1205} .s-weak{background:#5b6675;color:#e6edf3}
.tag.a-hold{background:rgba(38,194,129,.16);color:#26c281}
.tag.a-reduce{background:rgba(245,86,77,.16);color:#f5564d}
.tag.a-warn{background:rgba(217,164,65,.16);color:#d9a441}
.tag.a-watch{background:rgba(74,168,255,.16);color:#4aa8ff}
.rk-high{color:#ff6b61;font-weight:700} .rk-mid{color:#d9a441;font-weight:600} .rk-low{color:#e8c33a}
/* 盘前核心定调卡 */
.core-card{background:linear-gradient(135deg,#16202c,#111a24);border:1px solid #2b4a6a;border-radius:14px;padding:16px;margin-bottom:12px}
.core-head{font-size:17px;font-weight:700;margin-bottom:12px;display:flex;align-items:center;gap:6px}
.mood-bars{display:flex;flex-direction:column;gap:8px;margin-bottom:12px}
.mood-row{display:flex;align-items:center;gap:10px}
.mood-row .m-k{flex:0 0 110px;color:var(--acc);font-weight:600;font-size:12.5px}
.mood-bar{flex:1;height:10px;border-radius:5px;background:var(--bg2);overflow:hidden}
.mood-bar i{display:block;height:100%;border-radius:5px;background:var(--lc)}
.m-v{flex:0 0 auto;font-weight:700;font-size:13px;min-width:96px}
.gauge-mini{display:flex;align-items:center;gap:10px;margin-top:6px}
.gauge-cap{font-size:12px;color:var(--mut)}
.core-line{display:flex;gap:10px;padding:8px 0;font-size:13.5px;align-items:baseline;border-top:1px solid var(--line)}
.cl-k{flex:0 0 80px;color:var(--acc);font-weight:600;font-size:12.5px}
.cl-v{flex:1;color:var(--tx);line-height:1.7}
.rule-box{background:rgba(245,86,77,.12);border-left:4px solid #f5564d;border-radius:8px;padding:10px 12px;margin-top:10px;font-size:13px;color:#ffb0a8}
.risk-bar{background:rgba(217,164,65,.12);border-left:4px solid #d9a441;border-radius:8px;padding:10px 12px;margin-top:8px;font-size:13px;color:#f0d79a}
/* 风险事件结构化 */
.cf-box{border-radius:10px;padding:11px 13px;margin-top:10px}
.cf-red{border-left:4px solid #f5564d;background:rgba(245,86,77,.07)}
.cf-orange{border-left:4px solid #d9a441;background:rgba(217,164,65,.07)}
.cf-yellow{border-left:4px solid #e8c33a;background:rgba(232,195,58,.06)}
.cf-title{font-weight:700;font-size:13.5px;margin-bottom:6px}
.cf-body{font-size:13px;line-height:1.6;color:#d4dde6}
.cf-chain,.cf-impact{font-size:12.5px;line-height:1.6;margin-top:6px;color:#cdd7e2}
/* 利好利空分栏 */
.two-col{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.bull-card,.bear-card{background:var(--bg2);border-radius:10px;padding:12px}
.bb-h{font-size:14px;margin:0 0 8px;padding-bottom:6px;border-bottom:1px solid var(--line)}
.bb-list{display:flex;flex-direction:column;gap:9px}
.bb-item{font-size:12.5px;line-height:1.55}
.bb-txt{color:var(--tx)}
.bb-meta{color:var(--mut);font-size:11.5px;margin-top:2px}
/* 持仓环形图 */
.chart-wrap{margin:8px 0;background:rgba(0,0,0,.15);border-radius:10px;padding:6px;height:260px}
.chart-wrap.sm{height:200px}
/* 约束条 */
.constraint-bar{background:rgba(245,86,77,.12);border-left:4px solid #f5564d;border-radius:8px;padding:10px 12px;margin-top:10px;font-size:12.5px;color:#ffb0a8}
/* 技术面折叠 */
details{border-top:1px solid var(--line);padding:8px 0}
summary{cursor:pointer;font-weight:600;font-size:13.5px;display:flex;justify-content:space-between;align-items:center}
summary .sc{font-size:12px;color:var(--mut)}
.tech-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px 14px;margin-top:6px}
.tech-fold{display:grid;grid-template-columns:1fr 1fr;gap:6px 14px;margin-top:6px;padding-top:6px;border-top:1px dashed var(--line)}
.dim{display:flex;gap:8px;font-size:12px}
.dim b{color:var(--mut);font-weight:400;flex:0 0 48px}
.tech-interp{font-size:12.5px;color:#cdd7e2;margin-top:6px;line-height:1.6}
/* 事件时间线 */
.timeline{position:relative;padding-left:14px;margin-top:6px;border-left:2px solid var(--line)}
.tl-item{position:relative;padding:7px 0}
.tl-item::before{content:"";position:absolute;left:-19px;top:12px;width:9px;height:9px;border-radius:50%;background:var(--acc);border:2px solid var(--bg)}
.tl-time{font-size:12px;color:var(--acc);font-weight:700}
.tl-event{font-size:13px;color:var(--tx);margin:2px 0}
.tl-impact{font-size:12px;color:var(--mut);line-height:1.5}
/* 数据来源 */
.src-box{font-size:12.5px;line-height:1.7;background:rgba(74,168,255,.05);border-radius:8px;padding:10px 12px}
.kv{display:flex;justify-content:space-between;gap:8px;padding:4px 0;border-bottom:1px solid var(--line)}
.kv .ok{color:#26c281} .kv .warn{color:var(--neu)} .kv .q{color:var(--mut)}
.tip{border-bottom:1px dotted var(--acc);cursor:help}
.tip:hover{position:relative}
.tip:hover::after{content:attr(data-tip);position:absolute;left:0;top:130%;z-index:50;background:#0b0f15;border:1px solid var(--line);color:var(--tx);font-size:11.5px;line-height:1.4;padding:6px 8px;border-radius:8px;width:260px;box-shadow:0 4px 14px rgba(0,0,0,.5);font-weight:400}
/* 顶部导航 */
.topnav{position:sticky;top:0;z-index:30;background:rgba(14,17,23,.95);backdrop-filter:blur(6px);border:1px solid var(--line);border-radius:10px;padding:6px 8px;margin-bottom:12px;display:flex;gap:4px;flex-wrap:wrap;align-items:center;font-size:12px}
.topnav a{color:var(--mut);text-decoration:none;padding:3px 7px;border-radius:6px}
.topnav a:hover{background:var(--bg2);color:var(--tx)}
.nav-hist{margin-left:auto;display:flex;gap:4px}
@media (max-width:680px){.two-col{grid-template-columns:1fr}.topnav{font-size:11px}.tech-grid,.tech-fold{grid-template-columns:1fr}}
@media print{
  body{background:#fff;color:#111;max-width:100%}
  .topnav{display:none}.card{break-inside:avoid;box-shadow:none}
  .chart-wrap{height:200px}
  .tip:hover::after{display:none}
  *{color:#111!important;border-color:#ccc!important}
  .lv-strong-up,.lv-up,.lv-neu-up{background:#e8f7ee!important}
  .lv-neu-down,.lv-down,.lv-strong-down{background:#fdeceb!important}
}
</style>
</head>
<body>
<h1>🌍 早间全球分析</h1>
<div class="sub">__DATE__ · __UPD__（北京时间）· 数据源 neodata(__TIER__) · 盘前推送（A股未开盘）· 仅供参考不构成投资建议</div>
"""

# ---------- 静态 SCRIPT（ECharts，__DATA__ 注入） ----------
SCRIPT = """
<script>
const REPORT = __DATA__;
const DARK = {bg:'transparent', tx:'#e6edf3', mut:'#8b98a9', up:'#f5564d', down:'#26c281', acc:'#4aa8ff', neu:'#d9a441'};
function initCharts(){
  try{
    // ① 全球涨跌幅条形图
    if(document.getElementById('chgBar')){
      const groups = (REPORT.global||[]);
      let names=[], vals=[];
      groups.forEach(g=>{ (g.rows||[]).forEach(r=>{ names.push(r.name); vals.push(r.chg||0); }); });
      if(names.length){
        const c = echarts.init(document.getElementById('chgBar'), null, {renderer:'canvas'});
        c.setOption({
          backgroundColor:'transparent',
          grid:{left:96,right:46,top:10,bottom:10},
          tooltip:{trigger:'axis',axisPointer:{type:'shadow'},formatter:'{b}: {c}%'},
          xAxis:{type:'value',axisLabel:{color:DARK.mut,formatter:'{value}%'},splitLine:{lineStyle:{color:'#222b36'}}},
          yAxis:{type:'category',data:names.slice().reverse(),axisLabel:{color:DARK.tx,fontSize:11},axisLine:{lineStyle:{color:'#2a3340'}}},
          series:[{type:'bar',data:vals.slice().reverse().map(v=>({value:v,itemStyle:{color:v>0?DARK.up:(v<0?DARK.down:DARK.neu)}})),
            label:{show:true,position:'right',color:DARK.tx,fontSize:10,formatter:'{c}%'}}]
        });
      }
    }
    // ② 仓位环形图
    if(document.getElementById('posPie')){
      const hs = (REPORT.holdings||[]).filter(h=>h.weight_pct);
      if(hs.length){
        const c = echarts.init(document.getElementById('posPie'), null, {renderer:'canvas'});
        c.setOption({
          backgroundColor:'transparent',
          tooltip:{trigger:'item',formatter:'{b}: {c}% ({d}%)'},
          legend:{show:true,bottom:0,textStyle:{color:DARK.mut,fontSize:10},type:'scroll'},
          series:[{type:'pie',radius:['42%','70%'],center:['50%','46%'],
            data:hs.map(h=>({name:h.name,value:h.weight_pct})),
            label:{color:DARK.tx,fontSize:11,formatter:'{b}\\n{c}%'},
            itemStyle:{borderColor:'#0e1117',borderWidth:2},
            color:['#4aa8ff','#f5564d','#26c281','#d9a441','#a78bfa','#f472b6','#22d3ee','#fb923c','#94a3b8']
          }]
        });
      }
    }
    // ③ 情绪仪表盘（半导体情绪，次级）
    if(document.getElementById('sentGauge')){
      const s = (REPORT.sentiment||{}).semiconductor;
      if(s && s.score!==undefined && s.score!==null){
        const v = s.score;
        const c = echarts.init(document.getElementById('sentGauge'), null, {renderer:'canvas'});
        c.setOption({
          backgroundColor:'transparent',
          series:[{type:'gauge',min:0,max:100,radius:'92%',center:['50%','58%'],
            startAngle:210,endAngle:-30,
            progress:{show:false},
            axisLine:{lineStyle:{width:12,color:[[0.4,'#f5564d'],[0.6,'#d9a441'],[1,'#26c281']]}},
            pointer:{width:4,length:'60%',itemStyle:{color:'#e6edf3'}},
            axisTick:{show:false},splitLine:{length:10,lineStyle:{color:'#2a3340'}},
            axisLabel:{color:DARK.mut,fontSize:8,distance:12},
            detail:{valueAnimation:false,fontSize:20,color:'#e6edf3',offsetCenter:[0,'38%']},
            title:{show:false},
            data:[{value:v}]
          }]
        });
      }
    }
  }catch(e){ console.error('chart error', e); }
}
window.addEventListener('load', initCharts);
</script>
</body>
</html>
"""

def load_data(date):
    p = os.path.join(BASE, "early-morning_%s.json" % date)
    if not os.path.exists(p):
        fs = sorted(glob.glob(os.path.join(BASE, "early-morning_*.json")))
        if not fs:
            raise SystemExit("找不到 early-morning_%s.json，也没有任何 early-morning_*.json" % date)
        p = fs[-1]
        date = os.path.basename(p)[14:-5]
    return json.load(open(p, encoding="utf-8")), date

def main():
    if len(sys.argv) > 1:
        date = sys.argv[1]
    else:
        fs = sorted(glob.glob(os.path.join(BASE, "early-morning_*.json")))
        if not fs:
            raise SystemExit("用法: make_morning_html.py <YYYY-MM-DD>")
        date = os.path.basename(fs[-1])[14:-5]
    data, date = load_data(date)

    global CRED_TIER
    CRED_TIER = data.get("data_tier") or "T1"
    updated = data.get("updated_at") or (date + " 09:00")
    prev = yesterdate(date)

    nav = ('<nav class="topnav"><a href="#core">定调</a>'
            '<a href="#global">全球</a><a href="#conflict">风险</a>'
            '<a href="#bullbear">利好利空</a><a href="#hold">持仓</a>'
            '<a href="#earn">财报</a><a href="#tech">技术</a>'
            '<a href="#event">事件</a><a href="#cred">来源</a>'
            '<span class="nav-hist"><a href="早间全球分析-%s.html">←昨日</a>'
            '<a href="../../index.html">收件箱</a></span></nav>') % prev

    body = (render_core(data.get("core"), data.get("sentiment")) +
            render_global(data.get("global")) +
            render_conflicts(data.get("conflicts")) +
            render_bullbear(data.get("bulls"), data.get("bears")) +
            render_holdings(data.get("holdings"), data.get("holdings_constraint")) +
            render_earnings(data.get("earnings")) +
            render_tech(data.get("tech")) +
            render_events(data.get("events")) +
            render_cred(data.get("credibility"), data.get("disclaimer")))

    head = (HEAD.replace("__DATE__", esc(date))
            .replace("__UPD__", esc(updated))
            .replace("__TIER__", esc(CRED_TIER)))
    script = SCRIPT.replace("__DATA__", json.dumps(data, ensure_ascii=False))

    out_dir = os.path.join(REPORTS, date)
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "早间全球分析-%s.html" % date)
    open(out, "w", encoding="utf-8").write(head + nav + body + script)
    print("saved", out, "size", os.path.getsize(out))

if __name__ == "__main__":
    main()
