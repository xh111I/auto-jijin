# -*- coding: utf-8 -*-
"""
make_midday_html.py  —  午盘收盘分析（中场决策快报）报告生成器
读取 data/midday_<DATE>.json（由午盘自动化 agent 在 westock/neodata 分析后落盘的结构化数据），
渲染为优化版 午盘收盘-<DATE>.html。

定位：中场决策快报 —— 用户午休快速浏览，验证早盘判断、明确下午操作。
优化点（对应需求 P0/P1/P2）：
  P0  ① 首屏「午盘核心速览」卡（1句市场定性 + 3核心数据大字卡: 领涨/领跌/主力流入Top1 + 1句下午操作总纲）
       ② 模块顺序按决策优先级重排：核心速览→板块-基金对齐表→主力资金流向→下午走势预判→尾盘操作前瞻→数据校验与来源(默认折叠)
       ③ 统一全页信号体系：涨跌红涨绿跌±2%加粗；操作标签 持有/减仓观察/待确认/观望 绿/红/灰/浅灰；置信度 高/中/低 三级标签
  P0  板块↔基金对齐表深度优化：列精简(基金名称|关联ETF午盘涨跌|申万行业涨跌|操作信号)；
        基金估算/偏离度合并底部统一备注；成因列精简为关键词标签；
        重点行视觉分层(半导体浅绿高亮标"核心持仓"/富国煤炭浅红/QDII名称后加"QDII·T+1"小标签)；缺失值标准化灰字⚠
        预测模块从文字列表改三栏卡片矩阵(上涨/下跌/震荡 绿/红/灰；每卡基金名+置信度标签+1句理由；顶部小字"模型已下调震荡权重")
  P1  资金流模块可视化(极简横向条形图: 左主力净流入TOP3/右净流出TOP3 + 底部1句结论)
        尾盘前瞻提炼为赛道要点(【半导体系~71%】【煤炭】【QDII类】【其他小仓】【风控底线】)
        消除信息冗余(原"今日信号"整合进对齐表操作信号列)
  P1  顶部迷你悬浮导航(对齐表/资金/预判/尾盘 4锚点)；折叠机制(数据校验/来源/免责默认折叠)；术语悬停(申万行业/偏离度/T+1净值滞后)
  P2  时间标识强化("数据截止 2026-07-09 11:30 A股午盘")；命中率规范化(移至预测模块底部+"累计验证4/20")；
        全链路跳转入口(顶部加当日早间报告/前一日晚间复盘)；移动端适配(表格横向滚动)；打印样式(自动展开折叠)

视觉与信号体系：与早报(make_morning_html.py)、晚报(make_html.py)、大盘研判(make_market_html.py) 完全统一
  —— 同一套深色配色板 + 同一套 chg_cell 涨跌映射 + 同一套 [[术语|解释]] 悬停。
"""
import json
import os
import sys
import glob
import re
import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
REPORTS = os.path.join(BASE, "reports")
CRED_TIER = "T2"

# ---------- 工具函数（与 make_morning_html.py 保持一致） ----------
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
    """涨跌幅单元格：红涨绿跌，±thr% 加粗。None → 灰字⚠ 数据源未返回。"""
    v = num(v)
    if v is None:
        return '<td class="mut">⚠ 数据源未返回</td>'
    cls = pcls(v)
    b = " b" if pbold(v, thr) else ""
    sign = "+" if v > 0 else ""
    return '<td class="%s%s">%s%.2f%s</td>' % (cls, b, sign, v, suffix)
def chg_span(v, thr=2.0, suffix="%"):
    v = num(v)
    if v is None:
        return '<span class="mut">⚠ 未返回</span>'
    cls = pcls(v)
    b = " b" if pbold(v, thr) else ""
    sign = "+" if v > 0 else ""
    return '<span class="%s%s">%s%.2f%s</span>' % (cls, b, sign, v, suffix)
def chg_inline(v, thr=2.0, suffix="%"):
    """涨跌幅行内 span（用于对齐表单元格内，不生成 <td>）。None → 灰字⚠。"""
    v = num(v)
    if v is None:
        return '<span class="mut">⚠ 数据源未返回</span>'
    cls = pcls(v)
    b = " b" if pbold(v, thr) else ""
    sign = "+" if v > 0 else ""
    return '<span class="%s%s">%s%.2f%s</span>' % (cls, b, sign, v, suffix)
# ---------- 午盘专用信号标签 ----------
def op_tag(a):
    """操作标签 持有/减仓观察/待确认/观望 → (css, 文本)。绿/红/灰/浅灰。"""
    m = {"持有": "o-hold", "减仓观察": "o-reduce", "待确认": "o-pending", "观望": "o-watch"}
    return m.get(a, "o-watch"), a
def conf_tag(c):
    """置信度 高/中/低 → (css, 文本)。绿/橙/灰。"""
    m = {"高": "conf-high", "中": "conf-mid", "低": "conf-low"}
    return m.get(c, "conf-low"), c
def miss(v):
    """缺失值标准化：未连接 / N/A / 数据源未返回 / None → 灰字⚠。"""
    if v is None:
        return '<span class="mut">⚠ 数据源未返回</span>'
    s = str(v).strip()
    if s in ("未连接", "N/A", "数据源未返回", "—", ""):
        return '<span class="mut">⚠ %s</span>' % s
    return esc(s)
def yesterdate(d):
    dt = datetime.date.fromisoformat(d)
    return (dt - datetime.timedelta(days=1)).isoformat()

# ---------- 各模块渲染 ----------
def render_core(core):
    if not core:
        return ""
    kpis = ""
    for k in (core.get("kpis") or []):
        kpis += ('<div class="kpi"><div class="kpi-v %s">%s</div>'
                  '<div class="kpi-l">%s</div></div>') % (
            k.get("cls", "neu"), esc(k.get("value", "")), esc(k.get("label", "")))
    one = tip(core.get("one_liner", ""))
    guide = tip(core.get("action_guide", ""))
    return f'''
<section id="core" class="core-card">
  <div class="core-head">📊 午盘核心速览 <span class="badge">中场决策快报</span></div>
  <div class="core-line"><span class="cl-k">市场定性</span><span class="cl-v">{one}</span></div>
  <div class="kpi-row">{kpis}</div>
  <div class="rule-box">🎯 下午操作总纲：{guide}</div>
  <div class="legend">涨跌配色 <b class="up">红=涨</b>/<b class="down">绿=跌</b>（A股惯例）· ±2% 加粗 · 操作标签 🟢持有/🔴减仓观察/⚪待确认/⚫观望 · 置信度 🟢高/🟠中/⚪低</div>
</section>'''

def render_alignment(rows, note):
    if not rows:
        return ""
    body = ""
    for r in rows:
        name = tip(r.get("name", ""))
        qdii = (' <span class="qdii tip" data-tip="QDII 基金净值滞后一个交易日(T+1)确认，午盘所见为前一交易日美股/港股表现">QDII·T+1</span>') if r.get("qdii") else ""
        # 重点行分层
        rc = r.get("row_class")
        hl = ""
        badge = ""
        if rc == "core":
            hl = " hl-core"
            badge = ' <span class="core-badge">核心持仓</span>'
        elif rc == "reduce":
            hl = " hl-reduce"
        # 关联ETF午盘列：ETF名(小字) + 涨跌色（内联 span，不生成 td）
        etf_name = esc(r.get("etf") or "—")
        etf_cell = ('<div class="cell-sub">%s</div>%s') % (etf_name, chg_inline(r.get("etf_chg")))
        # 申万行业列：行业名 + 涨跌色（缺失标准化）
        sw_name = r.get("sw_sector")
        if not sw_name:
            sw_cell = '<div class="cell-sub mut">⚠ 数据源未返回</div>'
        else:
            sw_cell = ('<div class="cell-sub">%s</div>%s') % (esc(sw_name), chg_inline(r.get("sw_chg")))
        # 成因 → 关键词标签
        ctags = r.get("cause_tags") or []
        ctag_html = '<div class="ctags">%s</div>' % "".join(
            '<span class="ctag">%s</span>' % tip(t) for t in ctags)
        # 操作信号标签
        ocls, otxt = op_tag(r.get("op_signal"))
        op = '<span class="tag %s">%s</span>' % (ocls, esc(otxt))
        body += ('<tr class="%s"><td class="lname">%s%s%s</td>'
                  '<td>%s</td><td>%s</td><td>%s%s</td></tr>') % (
            hl, name, qdii, badge, etf_cell, sw_cell, op, ctag_html)
    note_html = ('<div class="note">%s</div>' % tip(note)) if note else ""
    return f'''
<section id="align" class="card">
  <h2>① 板块↔基金对齐表 <span class="badge">交叉验证 · 核心</span></h2>
  <div class="tbl-scroll">
  <table>
    <tr><th>基金名称</th><th>关联ETF午盘</th><th>申万行业</th><th>操作信号 / 成因</th></tr>
    {body}
  </table>
  </div>
  {note_html}
</section>'''

def render_flow(cap):
    if not cap:
        return ""
    note = tip(cap.get("conclusion", ""))
    illu = cap.get("illustrative")
    illu_html = ('<div class="note warn">%s</div>' % tip(illu)) if illu else ""
    return f'''
<section id="flow" class="card">
  <h2>② 主力资金流向 <span class="badge">westock zljlr</span></h2>
  <div class="flow-wrap">
    <div class="flow-col"><div class="flow-cap up">⬆ 净流入 TOP3</div><div class="chart-wrap sm"><canvas id="flowIn"></canvas></div></div>
    <div class="flow-col"><div class="flow-cap down">⬇ 净流出 TOP3</div><div class="chart-wrap sm"><canvas id="flowOut"></canvas></div></div>
  </div>
  <div class="note">%s</div>
  %s
</section>''' % (note, illu_html)

def render_predict(pred):
    if not pred:
        return ""
    note = tip(pred.get("note", ""))
    def col(items, kind):
        cls = {"up": "pc-up", "down": "pc-down", "flat": "pc-flat"}[kind]
        arrow = {"up": "↑ 涨", "down": "↓ 跌", "flat": "→ 震荡"}[kind]
        if not items:
            return '<div class="pcard %s"><div class="pc-head">%s</div><div class="note">无</div></div>' % (cls, arrow)
        cards = ""
        for it in items:
            ccls, ctxt = conf_tag(it.get("conf"))
            cards += ('<div class="pc-item"><div class="pc-top">'
                      '<span class="pc-name">%s</span>'
                      '<span class="conf %s">置信·%s</span></div>'
                      '<div class="pc-reason">%s</div></div>') % (
                tip(it.get("name", "")), ccls, ctxt, tip(it.get("reason", "")))
        return '<div class="pcard %s"><div class="pc-head">%s</div>%s</div>' % (cls, arrow, cards)
    hit = pred.get("hit_rate")
    hit_html = ('<div class="hit-rate">📈 命中率：%s（本批预测加权后计入统计）</div>' % esc(hit)) if hit else ""
    return f'''
<section id="predict" class="card">
  <h2>③ 下午走势预判 <span class="badge">三栏卡片矩阵</span></h2>
  <div class="pgrid">%s%s%s</div>
  <div class="warnbox">⚠️ %s</div>
  %s
</section>''' % (
        col(pred.get("up"), "up"), col(pred.get("down"), "down"),
        col(pred.get("flat"), "flat"), note, hit_html)

def render_tail(tail):
    if not tail:
        return ""
    tracks = tail.get("tracks") or []
    items = ""
    for t in tracks:
        items += ('<div class="tl-track"><span class="tl-tag">%s</span>'
                  '<span class="tl-body">%s</span></div>') % (
            esc(t.get("title", "")), tip(t.get("body", "")))
    return f'''
<section id="tail" class="card">
  <h2>④ 尾盘操作前瞻 <span class="badge">赛道要点</span></h2>
  <div class="tracks">{items}</div>
</section>'''

def render_validation(val):
    if not val:
        return ""
    checks = val.get("checks") or []
    rows = ""
    for c in checks:
        st = c.get("status", "ok")
        if st == "ok":
            icon, cls = "✅", "ok"
        elif st == "warn":
            icon, cls = "⚠️", "warn"
        else:
            icon, cls = "❓", "q"
        rows += '<li class="%s">%s <b>%s</b> — %s</li>' % (
            cls, icon, tip(c.get("item", "")), tip(c.get("note", "")))
    warnbox = ""
    if val.get("warnbox"):
        warnbox = '<div class="warnbox">%s</div>' % tip(val.get("warnbox"))
    return f'''
<details id="valid" class="card">
  <summary>⑤ 数据校验与来源说明 <span class="badge">默认折叠</span></summary>
  <ul class="check">{rows}</ul>
  {warnbox}
</details>'''

def render_sources(src, disclaimer):
    if not src and not disclaimer:
        return ""
    items = ""
    for it in (src or {}).get("items", []):
        items += '<div class="kv"><span>%s</span><span class="src-note">%s</span></div>' % (
            tip(it.get("item", "")), tip(it.get("note", "")))
    disc = ('<div class="note warn">%s</div>' % tip(disclaimer)) if disclaimer else ""
    return f'''
<details id="src" class="card">
  <summary>⑥ 数据来源与免责 <span class="badge">默认折叠</span></summary>
  <div class="src-box">{items}</div>
  {disc}
</details>'''

# ---------- 静态 HEAD（深色配色板，与早报/晚报/大盘研判统一） ----------
HEAD = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>午盘收盘分析 __DATE__</title>
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
.tbl-scroll{max-height:520px;overflow:auto}
th,td{padding:8px 6px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--mut);font-weight:400;font-size:11.5px;position:sticky;top:0;background:var(--card);z-index:2}
tbody tr:nth-child(even){background:rgba(255,255,255,.025)}
.lname{font-weight:700}
.cell-sub{font-size:10.5px;color:var(--mut);margin-bottom:2px}
.tag{font-size:11px;padding:1px 7px;border-radius:6px;font-weight:700}
/* 操作标签：持有绿 / 减仓观察红 / 待确认灰 / 观望浅灰 */
.tag.o-hold{background:rgba(38,194,129,.16);color:#26c281}
.tag.o-reduce{background:rgba(245,86,77,.16);color:#f5564d}
.tag.o-pending{background:#3a4250;color:#aab4c0;font-weight:600}
.tag.o-watch{background:#2a3340;color:#8b98a9;font-weight:600}
/* 重点行分层 */
tr.hl-core{background:rgba(38,194,129,.08)}
tr.hl-core td:first-child{box-shadow:inset 3px 0 0 #26c281}
tr.hl-reduce{background:rgba(245,86,77,.07)}
tr.hl-reduce td:first-child{box-shadow:inset 3px 0 0 #f5564d}
.core-badge{font-size:10px;font-weight:800;background:rgba(38,194,129,.22);color:#26c281;border-radius:5px;padding:1px 5px;margin-left:4px}
.qdii{font-size:10px;background:rgba(217,164,65,.18);color:#d9a441;border-radius:6px;padding:1px 5px;margin-left:4px;font-weight:700}
.ctags{margin-top:5px;display:flex;flex-wrap:wrap;gap:4px}
.ctag{font-size:10.5px;background:var(--bg2);color:#aab4c0;border-radius:5px;padding:1px 6px}
.note{color:var(--mut);font-size:11.5px;margin-top:8px;line-height:1.5}
.note.warn{background:rgba(217,164,65,.10);border:1px solid rgba(217,164,65,.3);border-radius:8px;padding:8px 10px;color:#d9a441}
.legend{color:var(--mut);font-size:11px;margin-top:8px;line-height:1.6;border-top:1px dashed var(--line);padding-top:8px}
/* 核心速览卡 */
.core-card{background:linear-gradient(135deg,#16202c,#111a24);border:1px solid #2b4a6a;border-radius:14px;padding:16px;margin-bottom:12px}
.core-head{font-size:17px;font-weight:700;margin-bottom:10px;display:flex;align-items:center;gap:6px}
.core-line{display:flex;gap:10px;padding:8px 0;font-size:13.5px;align-items:baseline;border-bottom:1px solid var(--line)}
.cl-k{flex:0 0 70px;color:var(--acc);font-weight:600;font-size:12.5px}
.cl-v{flex:1;color:var(--tx);line-height:1.7}
.kpi-row{display:flex;gap:10px;flex-wrap:wrap;margin:12px 0}
.kpi{flex:1;min-width:150px;background:var(--bg2);border:1px solid var(--line);border-radius:10px;padding:12px;text-align:center}
.kpi-v{font-size:21px;font-weight:800}
.kpi-l{font-size:11.5px;color:var(--mut);margin-top:4px}
.rule-box{background:rgba(74,168,255,.10);border-left:4px solid #4aa8ff;border-radius:8px;padding:10px 12px;margin-top:10px;font-size:13px;color:#bcd9f5}
/* 资金流 */
.flow-wrap{display:flex;gap:14px}
.flow-col{flex:1;min-width:0}
.flow-cap{font-size:13px;font-weight:700;margin-bottom:6px}
.chart-wrap{margin:8px 0;background:rgba(0,0,0,.15);border-radius:10px;padding:6px;height:240px}
.chart-wrap.sm{height:220px}
/* 预测三栏卡片 */
.pgrid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px}
.pcard{border:1px solid var(--line);border-radius:11px;padding:10px;background:var(--bg2)}
.pc-up{border-top:3px solid var(--up)}
.pc-down{border-top:3px solid var(--down)}
.pc-flat{border-top:3px solid var(--neu)}
.pc-head{font-size:14px;font-weight:800;margin-bottom:8px}
.pc-item{border-top:1px solid var(--line);padding:7px 0;font-size:12px}
.pc-item:first-child{border-top:none}
.pc-top{display:flex;justify-content:space-between;align-items:center;gap:6px;margin-bottom:3px}
.pc-name{font-weight:700;font-size:12.5px}
.conf{font-size:10px;font-weight:700;border-radius:6px;padding:1px 6px;white-space:nowrap}
.conf-high{background:rgba(38,194,129,.22);color:#26c281}
.conf-mid{background:rgba(217,164,65,.22);color:#d9a441}
.conf-low{background:rgba(139,152,169,.22);color:#8b98a9}
.pc-reason{font-size:11.5px;color:#aab4c0;line-height:1.55}
.warnbox{background:rgba(217,164,65,.10);border:1px solid rgba(217,164,65,.3);border-radius:8px;padding:8px 11px;font-size:11.5px;color:#d9a441;margin-top:10px}
.hit-rate{font-size:12px;color:var(--acc);margin-top:10px;font-weight:600}
/* 尾盘赛道要点 */
.tracks{display:flex;flex-direction:column;gap:8px}
.tl-track{display:flex;gap:10px;align-items:flex-start;font-size:13px;line-height:1.6;padding:8px 10px;background:var(--bg2);border-radius:9px;border-left:3px solid var(--acc)}
.tl-tag{flex:0 0 auto;font-weight:800;font-size:12px;color:var(--acc);min-width:118px}
.tl-body{flex:1;color:#cdd7e2}
/* 数据校验 / 来源（折叠） */
details.card summary{cursor:pointer;font-size:16px;font-weight:700;display:flex;align-items:center;gap:6px;list-style:none}
details.card summary::-webkit-details-marker{display:none}
details.card[open] summary{margin-bottom:10px;border-bottom:1px solid var(--line);padding-bottom:8px}
.check{list-style:none;font-size:12.5px;line-height:1.6}
.check li{margin:6px 0;padding-left:22px;position:relative}
.check li.ok:before{content:"✓";position:absolute;left:0;color:#26c281;font-weight:800}
.check li.warn:before{content:"!";position:absolute;left:0;color:#d9a441;font-weight:800}
.check li.q:before{content:"?";position:absolute;left:0;color:var(--mut);font-weight:800}
.check li b{color:var(--tx)}
.src-box{font-size:12.5px;line-height:1.7;background:rgba(74,168,255,.05);border-radius:8px;padding:10px 12px}
.kv{display:flex;justify-content:space-between;gap:10px;padding:5px 0;border-bottom:1px solid var(--line);font-size:12px}
.kv .src-note{color:var(--mut);text-align:right;flex:1}
/* 顶部导航 */
.topnav{position:sticky;top:0;z-index:30;background:rgba(14,17,23,.95);backdrop-filter:blur(6px);border:1px solid var(--line);border-radius:10px;padding:6px 8px;margin-bottom:12px;display:flex;gap:4px;flex-wrap:wrap;align-items:center;font-size:12px}
.topnav a{color:var(--mut);text-decoration:none;padding:3px 7px;border-radius:6px}
.topnav a:hover{background:var(--bg2);color:var(--tx)}
.nav-hist{margin-left:auto;display:flex;gap:4px}
/* 术语悬停 */
.tip{border-bottom:1px dotted var(--acc);cursor:help}
.tip:hover{position:relative}
.tip:hover::after{content:attr(data-tip);position:absolute;left:0;top:130%;z-index:50;background:#0b0f15;border:1px solid var(--line);color:var(--tx);font-size:11.5px;line-height:1.4;padding:6px 8px;border-radius:8px;width:260px;box-shadow:0 4px 14px rgba(0,0,0,.5);font-weight:400}
@media (max-width:680px){.flow-wrap{grid-template-columns:1fr}.pgrid{grid-template-columns:1fr}.topnav{font-size:11px}.tl-tag{min-width:90px}}
@media print{
  body{background:#fff;color:#111;max-width:100%}
  .topnav{display:none}.card{break-inside:avoid;box-shadow:none}
  .chart-wrap{height:200px}.tip:hover::after{display:none}
  details.card:not([open]){display:block}
  details.card summary{margin-bottom:8px}
  *{color:#111!important;border-color:#ccc!important}
}
</style>
</head>
<body>
<h1>📊 午盘收盘分析</h1>
<div class="sub">数据截止 __DATE__ 11:30 A股午盘 · 更新 __UPD__ · 数据源 __TIER__（westock/neodata）· 中场决策快报 · 仅供参考不构成投资建议</div>
"""

# ---------- 静态 SCRIPT（ECharts，__DATA__ 注入） ----------
SCRIPT = """
<script>
const REPORT = __DATA__;
const DARK = {tx:'#e6edf3', mut:'#8b98a9', up:'#f5564d', down:'#26c281', acc:'#4aa8ff', neu:'#d9a441'};
function barOpt(title, pairs, color){
  const names = pairs.map(p=>p.name);
  const vals = pairs.map(p=>p.value);
  return {
    backgroundColor:'transparent',
    grid:{left:8,right:46,top:8,bottom:8,containLabel:true},
    tooltip:{trigger:'axis',axisPointer:{type:'shadow'},formatter:'{b}: {c}亿'},
    xAxis:{type:'value',axisLabel:{color:DARK.mut,fontSize:10,formatter:'{value}'},splitLine:{lineStyle:{color:'#222b36'}},axisLine:{show:false}},
    yAxis:{type:'category',data:names.slice().reverse(),axisLabel:{color:DARK.tx,fontSize:11},axisLine:{lineStyle:{color:'#2a3340'}},axisTick:{show:false}},
    series:[{type:'bar',data:vals.slice().reverse(),itemStyle:{color:color,borderRadius:[0,4,4,0]},
      label:{show:true,position:'right',color:DARK.tx,fontSize:10,formatter:'{c}亿'}}]
  };
}
function initCharts(){
  try{
    if(document.getElementById('flowIn')){
      const cap = (REPORT.capital_flow||{});
      const ins = cap.in_top3||[];
      if(ins.length){
        const c = echarts.init(document.getElementById('flowIn'), null, {renderer:'canvas'});
        c.setOption(barOpt('in', ins, DARK.up));
      }
    }
    if(document.getElementById('flowOut')){
      const cap = (REPORT.capital_flow||{});
      const outs = cap.out_top3||[];
      if(outs.length){
        const c = echarts.init(document.getElementById('flowOut'), null, {renderer:'canvas'});
        c.setOption(barOpt('out', outs, DARK.down));
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
    p = os.path.join(BASE, "midday_%s.json" % date)
    if not os.path.exists(p):
        fs = sorted(glob.glob(os.path.join(BASE, "midday_*.json")))
        if not fs:
            raise SystemExit("找不到 midday_%s.json，也没有任何 midday_*.json" % date)
        p = fs[-1]
        date = os.path.basename(p)[7:-5]
    return json.load(open(p, encoding="utf-8")), date

def main():
    if len(sys.argv) > 1:
        date = sys.argv[1]
    else:
        fs = sorted(glob.glob(os.path.join(BASE, "midday_*.json")))
        if not fs:
            raise SystemExit("用法: make_midday_html.py <YYYY-MM-DD>")
        date = os.path.basename(fs[-1])[7:-5]
    data, date = load_data(date)

    global CRED_TIER
    CRED_TIER = data.get("data_tier") or "T2"
    updated = data.get("updated_at") or (date + " 11:30")
    prev = yesterdate(date)

    nav = ('<nav class="topnav"><a href="#align">对齐表</a>'
            '<a href="#flow">资金</a><a href="#predict">预判</a>'
            '<a href="#tail">尾盘</a>'
            '<span class="nav-hist"><a href="早间全球分析-%s.html">🌅当日早间</a>'
            '<a href="../%s/晚间复盘-%s.html">🌙前日晚间</a>'
            '<a href="../../index.html">📱收件箱</a></span></nav>') % (date, prev, prev)

    body = (render_core(data.get("core")) +
            render_alignment(data.get("alignment"), data.get("align_note")) +
            render_flow(data.get("capital_flow")) +
            render_predict(data.get("predict")) +
            render_tail(data.get("tail")) +
            render_validation(data.get("validation")) +
            render_sources(data.get("sources"), data.get("disclaimer")))

    head = (HEAD.replace("__DATE__", esc(date))
             .replace("__UPD__", esc(updated))
             .replace("__TIER__", esc(CRED_TIER)))
    script = SCRIPT.replace("__DATA__", json.dumps(data, ensure_ascii=False))

    out_dir = os.path.join(REPORTS, date)
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "午盘收盘-%s.html" % date)
    open(out, "w", encoding="utf-8").write(head + nav + body + script)
    print("saved", out, "size", os.path.getsize(out))

if __name__ == "__main__":
    main()
