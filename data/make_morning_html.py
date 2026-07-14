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

# ── 共享工具库（方法论适配版） ──
from render_utils import (
    esc, tip, num, level_info, pcls, pbold, chg_cell, chg_span, bar,
    str_tag, act_tag, risk_cls, wt_cell, ret_cell,
    calc_risk_score, calc_stop_loss_dist, calc_semic_concentration,
    check_alerts, r2, missing_val, risk_dist_html, yesterdate, RULES,
)

BASE = os.path.dirname(os.path.abspath(__file__))
REPORTS = os.path.join(BASE, "reports")
CRED_TIER = "T1"

# ---------- 各模块渲染 ----------
def render_core(core, sentiment):
    if not core:
        return ""
    # === 紧急警示条（浮动在导航下方） ===
    emerg = core.get("emergency")
    emerg_html = ""
    if emerg:
        ecls = "emergency-banner" + (" orange" if emerg.get("level") == "orange" else "")
        e_icon = emerg.get("icon", "🔴")
        e_text = tip(emerg.get("text", ""))
        emerg_html = f'''<div class="{ecls}"><span class="eb-icon">{e_icon}</span><span>{e_text}</span><span class="eb-close" onclick="this.parentElement.remove()">✕</span></div>'''
    # === 风险加权综合评分（方法论 · 四：数据缺失时自动计算） ===
    rs = core.get("risk_score")
    rs_html = ""
    if rs is not None:
        rs = num(rs) or 50
        if rs <= 35:
            r_cls, r_color, r_label = "r-low", "#26c281", "低风险"
        elif rs <= 55:
            r_cls, r_color, r_label = "r-mid", "#d9a441", "中等风险"
        elif rs <= 75:
            r_cls, r_color, r_label = "r-high", "#f5564d", "偏高风险"
        else:
            r_cls, r_color, r_label = "r-high", "#ff6b61", "高风险"
        rs_desc = tip(core.get("risk_score_note", ""))
        rs_html = f'''<div class="risk-score-block {r_cls}">
          <div class="risk-score"><div class="rs-num" style="color:{r_color}">{int(round(rs))}</div><div class="rs-label">{r_label}</div></div>
          <div class="rs-desc">{rs_desc}</div></div>'''
    # === 今日一句话指令 ===
    today_inst = core.get("today_instruction")
    inst_html = ""
    if today_inst:
        inst_html = f'<div class="today-instruction">🎯 {tip(today_inst)}</div>'
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
    # 情绪迷你折线（10日时序，替代原仪表盘）
    sent_trend_html = ('<div class="gauge-mini"><div id="sentTrend" style="width:300px;height:120px"></div>'
                       '<div class="gauge-cap">半导体情绪 近10日趋势</div></div>')
    return f'''
{emerg_html}
<section id="core" class="core-card">
  <div class="core-head">🌅 盘前核心定调 <span class="badge">开盘前30秒决策</span></div>
  {rs_html}
  {inst_html}
  <div class="mood-bars">
    {bars}
    {sent_trend_html}
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
    # 分组条形图（每个组一张图表，避免37个标的全堆一起）
    bar_charts = ""
    bar_data_js = []  # 收集各组数据供JS渲染
    for gi, g in enumerate(groups):
        gname = esc(g.get("group", ""))
        grows = g.get("rows") or []
        if not grows:
            continue
        rows_html += '<tr class="grp"><td colspan="5">%s</td></tr>' % gname
        g_names = []; g_vals = []
        for r in grows:
            chg = num(r.get("chg"))
            g_names.append(r.get("name"))
            g_vals.append(chg or 0)
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
        bh = max(120, 30 + len(grows) * 24)
        bar_charts += ('<div style="margin-bottom:8px"><div style="font-size:12px;color:var(--acc);padding:4px 0">%s</div>'
                       '<div class="chart-wrap" style="height:%dpx"><canvas id="chgBar_%d"></canvas></div></div>') % (gname, bh, gi)
        bar_data_js.append({"group": gname, "names": g_names, "vals": g_vals})
    note = ('<div class="note">📌 涨跌配色：<b class="up">红=涨</b>/<b class="down">绿=跌</b>；±2%加粗；重点行已高亮。</div>')
    # 关键标的分时趋势图
    trend_html = '<div style="margin-top:10px"><div style="font-size:12px;color:var(--mut);margin-bottom:6px">📈 关键标的近10日走势</div><div class="trend-mini" id="trendBar">' \
                 '<div class="trend-item"><div class="trend-title">中证半导</div><canvas id="trend_0"></canvas></div>' \
                 '<div class="trend-item"><div class="trend-title">人工智能</div><canvas id="trend_1"></canvas></div>' \
                 '<div class="trend-item"><div class="trend-title">半导体ETF</div><canvas id="trend_2"></canvas></div>' \
                 '</div></div>'
    return f'''
<section id="global" class="card">
  <h2>① 全球股市 / 大宗 / 汇率 涨跌 <span class="badge">{len(flat)} 标的</span></h2>
  {bar_charts}
  {trend_html}
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
    red_boxes = ""; other_boxes = ""
    for c in conflicts:
        lv = c.get("level") or "orange"
        cls = {"red": "cf-red", "orange": "cf-orange", "yellow": "cf-yellow"}.get(lv, "cf-orange")
        icon = {"red": "🔴", "orange": "🟠", "yellow": "🟡"}.get(lv, "🟠")
        fact = tip(c.get("body", ""))
        chain = tip(c.get("chain", ""))
        impact = tip(c.get("impact", ""))
        chain_html = ('<div class="cf-chain"><b>传导链：</b>%s</div>' % chain) if chain else ""
        impact_html = ('<div class="cf-impact"><b>持仓影响：</b>%s</div>' % impact) if impact else ""
        box = '''
<div class="cf-box %s">
  <div class="cf-title">%s %s</div>
  <div class="cf-body">%s</div>
  %s
  %s
</div>''' % (cls, icon, tip(c.get("title", "")), fact, chain_html, impact_html)
        if lv == "red":
            red_boxes += box
        else:
            other_boxes += box
    # 🔴 红级直接展开；🟠🟡 折叠（summary 显示标题）
    fold_html = ""
    if other_boxes:
        fold_html = '<details><summary>🟠🟡 次级风险事件 <span class="sc">%d 条 · 点击展开</span></summary>%s</details>' % (
            sum(1 for c in conflicts if c.get("level") != "red"), other_boxes)
    return f'''
<section id="conflict" class="card">
  <h2>② 风险事件结构化 <span class="badge">事件等级→事实→传导→影响</span></h2>
  {red_boxes}
  {fold_html}
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
        # 方法论 · 四：精确计算止损剩余空间（替代原"高/中/低"模糊描述）
        sl = calc_stop_loss_dist(h.get("ret"))
        sl_progress = sl["progress_pct"]
        sl_color = sl["color"]
        sl_cls = sl["level_cls"]
        sl_txt = "%d%%" % sl_progress if sl["remaining_pct"] is not None else missing_val()
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
            sl_progress, sl_color, sl_cls, sl_txt)
    cons_html = ('<div class="constraint-bar">⚠️ 今日核心约束：%s</div>' % tip(constraint)) if constraint else ""
    # 持仓迷你趋势图
    mini_trends = '<div style="margin-top:8px"><div style="font-size:12px;color:var(--mut);margin-bottom:4px">📈 持仓关联指数近10日走势</div><div class="trend-mini" id="holdTrendBar">' \
                  '<div class="trend-item"><div class="trend-title">中证半导(东方AI/阿尔法/永赢)</div><canvas id="htrend_0"></canvas></div>' \
                  '<div class="trend-item"><div class="trend-title">人工智能(东方AI)</div><canvas id="htrend_1"></canvas></div>' \
                  '<div class="trend-item"><div class="trend-title">港股创新药(港药)</div><canvas id="htrend_2"></canvas></div>' \
                  '</div></div>'
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
  {mini_trends}
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
        idx = esc(t.get("index", ""))
        # 生成安全的 canvas id（用于 kline 图表）
        cid = re.sub(r'[^a-zA-Z0-9]', '_', t.get("index", "idx"))
        # kline 数据（日K OHLC，可选）
        kline = t.get("kline")
        has_kline = kline and kline.get("dates") and kline.get("ohlc")
        kline_html = ""
        if has_kline:
            kline_html = ('<div style="margin:6px 0;font-size:12px;color:var(--mut)">'
                          '📈 日K线（近60日）· 📊 月K线（近12月）<span class="sc"> 展开可见</span></div>'
                          '<div class="chart-wrap" style="height:220px;margin:4px 0;">'
                          '<canvas id="kx_%s"></canvas></div>'
                          '<div class="chart-wrap" style="height:180px;margin:4px 0;">'
                          '<canvas id="km_%s"></canvas></div>') % (cid, cid)
        else:
            kline_html = ('<div style="margin:6px 0;font-size:12.5px;color:#8b98a9;'
                          'background:rgba(255,255,255,.03);padding:8px 12px;border-radius:6px;">'
                          '💡 日K/月K线图：需 agent 在 tech[].kline 字段提供 {dates, ohlc} 数据</div>')
        blocks += '''
<details>
  <summary>%s <span class="sc">收盘 %s · 单日 %s</span></summary>
  %s
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
            kline_html,
            esc(t.get("ma20", "—")), esc(t.get("ma60", "—")),
            tip(t.get("interpret", "")),
            tip(t.get("macd", "—")), tip(t.get("kdj", "—")))
    return f'''
<section id="tech" class="card">
  <h2>⑥ 持仓关联指数技术面 <span class="badge">日K·月K·MA20/MA60 · neodata</span></h2>
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
  <details>
  <summary>展开数据来源 <span class="sc">neodata {esc(CRED_TIER)} · 点击查看</span></summary>
  <div class="src-box">{rows}</div>
  </details>
  {disc}
</section>'''

# ============================================================
# 新板块渲染：头条速览 / 重点事件解读 / 中国动态 / 今日前瞻 / 风险提示
# ============================================================

def render_headlines(headlines):
    """1. 头条速览 — 首屏 1 行 3 条，每条 ≤50 字"""
    if not headlines:
        return ""
    items = ""
    for h in headlines[:3]:
        title = tip(h.get("title", ""))
        impact = tip(h.get("impact", ""))
        items += '<div class="hl-item"><span class="hl-title">%s</span><span class="hl-impact">%s</span></div>' % (title, impact)
    return '''
<section id="headlines" class="card hl-card">
  <div class="hl-grid">
    %s
  </div>
</section>''' % items

def render_key_events(key_events):
    """3. 重点事件解读 — 3~5 条，每条(类别→事件概述→关键细节→影响解读)"""
    if not key_events:
        return ""
    items = ""
    for e in key_events:
        cat = esc(e.get("category", "宏观"))
        summary = tip(e.get("event", ""))
        detail = tip(e.get("details", ""))
        impact = tip(e.get("impact", ""))
        items += '''
<div class="ke-item">
  <div class="ke-cat">%s</div>
  <div class="ke-summary"><b>事件：</b>%s</div>
  <details class="ke-detail">
    <summary>关键细节 &amp; 影响解读 <span class="sc">点击展开</span></summary>
    <div class="ke-body"><b>关键细节：</b>%s</div>
    <div class="ke-impact"><b>影响解读：</b>%s</div>
  </details>
</div>''' % (cat, summary, detail, impact)
    return '''
<section id="keyevents" class="card">
  <h2>③ 重点事件解读 <span class="badge">事件→细节→影响</span></h2>
  %s
</section>''' % items

def render_china(china):
    """4. 中国相关动态 — 单独板块"""
    if not china:
        return ""
    items = ""
    for c in china:
        title = tip(c.get("title", ""))
        detail = tip(c.get("detail", ""))
        impact = tip(c.get("impact", ""))
        items += '<div class="cn-item"><div class="cn-title">%s</div><div class="cn-detail">%s</div><div class="cn-imp">影响：%s</div></div>' % (title, detail, impact)
    return '''
<section id="china" class="card">
  <h2>④ 中国相关动态 <span class="badge">中概·政策·中国资产</span></h2>
  %s
</section>''' % items

def render_outlook(outlook):
    """5. 今日前瞻 — 时间+事件+预期"""
    if not outlook:
        return ""
    items = ""
    for o in outlook:
        t = esc(o.get("time", ""))
        ev = tip(o.get("event", ""))
        exp = tip(o.get("expectation", ""))
        items += '<div class="ol-item"><span class="ol-time">%s</span><span class="ol-ev">%s</span><span class="ol-exp">%s</span></div>' % (t, ev, exp)
    return '''
<section id="outlook" class="card">
  <h2>⑤ 今日前瞻 <span class="badge">数据发布·财经事件</span></h2>
  <div class="ol-list">%s</div>
</section>''' % items

def render_risk_tips(risks):
    """6. 风险提示 — 底部 1~2 条"""
    if not risks:
        return ""
    items = ""
    for r in risks:
        risk_text = tip(r.get("risk", ""))
        assess = tip(r.get("assessment", ""))
        items += '<div class="rt-item"><span class="rt-icon">⚠️</span><span class="rt-text">%s</span><span class="rt-assess">%s</span></div>' % (risk_text, assess)
    return '''
<section id="risktips" class="card rt-card">
  <h2>⑥ 风险提示 <span class="badge">客观审慎</span></h2>
  %s
</section>''' % items

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
html{scroll-padding-top:64px}
body{background:var(--bg);color:var(--tx);font:14px/1.6 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif;padding:12px;max-width:1080px;margin:0 auto;padding-top:56px}
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
/* 信号等级（多空语义） */
.lv-strong-up{background:rgba(38,194,129,.30);color:#2ee07a;--lc:#2ee07a}
.lv-up{background:rgba(38,194,129,.16);color:#26c281;--lc:#26c281}
.lv-neu-up{background:rgba(38,194,129,.08);color:#7fd1a8;--lc:#7fd1a8}
.lv-neu-down{background:rgba(245,86,77,.08);color:#e08a85;--lc:#e08a85}
.lv-down{background:rgba(245,86,77,.16);color:#f5564d;--lc:#f5564d}
.lv-strong-down{background:rgba(245,86,77,.30);color:#ff6b61;--lc:#ff6b61}
/* 强度/操作/风险 标签 */
.str{display:inline-block;font-size:11px;font-weight:700;padding:1px 7px;border-radius:6px;margin-right:4px}
.s-strong{background:#f5564d;color:#fff} .s-mid{background:#d9a441;color:#1a1205} .s-weak{background:#5b6675;color:#e6edf3}
.tag.a-hold{background:rgba(38,194,129,.16);color:#26c281}
.tag.a-reduce{background:rgba(245,86,77,.16);color:#f5564d}
.tag.a-warn{background:rgba(217,164,65,.16);color:#d9a441}
.tag.a-watch{background:rgba(74,168,255,.16);color:#4aa8ff}
.rk-high{color:#ff6b61;font-weight:700} .rk-mid{color:#d9a441;font-weight:600} .rk-low{color:#e8c33a}
td .wt-over{font-weight:700;font-size:15px;background:rgba(245,86,77,.08);padding:2px 6px;border-radius:4px}
td.up,td.down{font-size:14px}
/* ========== 1. 头条速览 ========== */
.hl-card{background:linear-gradient(135deg,#1b2a3a,#15202e);border-color:#2b4a6a;padding:10px 12px}
.hl-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}
.hl-item{background:rgba(0,0,0,.25);border-radius:8px;padding:8px 10px;border-left:3px solid var(--acc)}
.hl-title{display:block;font-weight:700;font-size:14px;color:#e6edf3;margin-bottom:2px;line-height:1.3}
.hl-impact{display:block;font-size:12px;color:var(--mut);line-height:1.4}
/* ========== 3. 重点事件解读 ========== */
.ke-item{margin-bottom:12px;padding:10px 12px;background:var(--bg2);border-radius:10px}
.ke-cat{display:inline-block;font-size:11px;padding:1px 7px;border-radius:6px;background:rgba(74,168,255,.16);color:var(--acc);margin-bottom:6px;font-weight:600}
.ke-summary{font-size:13px;line-height:1.6;margin-bottom:6px}
.ke-detail summary{font-size:12.5px;color:var(--acc);cursor:pointer;padding:4px 0}
.ke-body,.ke-impact{font-size:12.5px;color:#cdd7e2;line-height:1.65;padding:6px 0}
.ke-body b,.ke-impact b{color:var(--mut);font-weight:400}
/* ========== 4. 中国相关动态 ========== */
.cn-item{background:var(--bg2);border-radius:10px;padding:10px 12px;margin-bottom:8px;border-left:3px solid var(--acc)}
.cn-title{font-weight:700;font-size:13.5px;margin-bottom:3px}
.cn-detail{font-size:12.5px;color:#cdd7e2;line-height:1.5}
.cn-imp{font-size:12px;color:var(--mut);margin-top:4px}
/* ========== 5. 今日前瞻 ========== */
.ol-list{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:8px}
.ol-item{background:var(--bg2);border-radius:10px;padding:10px 12px;display:flex;flex-direction:column;gap:3px}
.ol-time{font-size:12px;color:var(--acc);font-weight:700}
.ol-ev{font-size:13px;line-height:1.5}
.ol-exp{font-size:12px;color:var(--mut)}
/* ========== 6. 风险提示 ========== */
.rt-card{border-left:3px solid var(--up)}
.rt-item{display:flex;align-items:flex-start;gap:10px;padding:8px 0;border-bottom:1px solid var(--line)}
.rt-item:last-child{border-bottom:none}
.rt-icon{flex-shrink:0;font-size:16px;margin-top:1px}
.rt-text{flex:1;font-size:13px;line-height:1.5}
.rt-assess{flex:0 0 auto;font-size:12px;color:var(--mut);padding:2px 8px;background:rgba(217,164,65,.12);border-radius:6px}
/* === 固定悬浮目录 === */
.topnav{position:fixed;top:0;left:0;right:0;z-index:50;background:rgba(14,17,23,.96);backdrop-filter:blur(8px);border-bottom:1px solid var(--line);padding:6px 12px;display:flex;gap:4px;flex-wrap:wrap;align-items:center;font-size:12px;min-height:44px;max-width:1080px;margin:0 auto;left:50%;transform:translateX(-50%)}
.topnav a{color:var(--mut);text-decoration:none;padding:3px 8px;border-radius:6px;transition:all .15s}
.topnav a:hover{background:var(--bg2);color:var(--tx)}
.topnav a.active{background:var(--acc);color:#fff;font-weight:600}
.nav-actions{margin-left:auto;display:flex;gap:4px}
.nav-actions button{background:var(--bg2);border:1px solid var(--line);color:var(--mut);padding:3px 8px;border-radius:6px;cursor:pointer;font-size:11px;white-space:nowrap}
.nav-actions button:hover{background:var(--card);color:var(--tx)}
/* === 紧急警示 === */
.emergency-banner{position:sticky;top:56px;z-index:40;background:linear-gradient(90deg,#7f1d1d,#991b1b);color:#fecaca;padding:10px 16px;border-radius:10px;margin-bottom:12px;display:flex;align-items:center;gap:10px;font-size:13.5px;font-weight:700;box-shadow:0 2px 12px rgba(127,29,29,.5);animation:pulse 2s infinite}
.emergency-banner.orange{background:linear-gradient(90deg,#78350f,#92400e)}
.emergency-banner .eb-icon{font-size:20px;flex-shrink:0}
.emergency-banner .eb-close{flex-shrink:0;margin-left:auto;cursor:pointer;color:#fca5a5;font-size:16px;font-weight:400;padding:2px 8px;border-radius:4px}
.emergency-banner .eb-close:hover{background:rgba(255,255,255,.15);color:#fff}
@keyframes pulse{0%,100%{opacity:1} 50%{opacity:.85}}
/* === 风险评分大字块 === */
.risk-score-block{display:flex;align-items:center;gap:16px;margin-bottom:14px;padding:14px;border-radius:10px}
.risk-score-block.r-low{background:rgba(38,194,129,.12);border:1px solid rgba(38,194,129,.3)}
.risk-score-block.r-mid{background:rgba(217,164,65,.12);border:1px solid rgba(217,164,65,.3)}
.risk-score-block.r-high{background:rgba(245,86,77,.12);border:1px solid rgba(245,86,77,.3)}
.risk-score{text-align:center;min-width:80px}
.risk-score .rs-num{font-size:42px;font-weight:800;line-height:1}
.risk-score .rs-label{font-size:12px;color:var(--mut);margin-top:2px}
.risk-score-block .rs-desc{flex:1;font-size:13.5px;line-height:1.7;color:#cdd7e2}
.today-instruction{background:rgba(74,168,255,.08);border:1px solid rgba(74,168,255,.25);border-radius:8px;padding:10px 14px;margin-bottom:10px;font-size:14px;font-weight:700;color:#93c5fd}
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
.chart-wrap{margin:8px 0;background:rgba(0,0,0,.15);border-radius:10px;padding:6px;height:260px}
.chart-wrap.sm{height:200px}.chart-wrap.lg{height:450px}.chart-wrap.trend{height:240px}
.trend-mini{display:flex;gap:8px;flex-wrap:wrap;margin:6px 0}
.trend-item{flex:1;min-width:280px;background:rgba(0,0,0,.12);border-radius:8px;padding:4px;height:220px}
.trend-title{font-size:11px;color:var(--mut);padding:4px 8px;text-align:center}
.trend-item canvas{width:100%;height:190px}
.constraint-bar{background:rgba(245,86,77,.12);border-left:4px solid #f5564d;border-radius:8px;padding:10px 12px;margin-top:10px;font-size:12.5px;color:#ffb0a8}
details{border-top:1px solid var(--line);padding:8px 0}
summary{cursor:pointer;font-weight:600;font-size:13.5px;display:flex;justify-content:space-between;align-items:center}
summary .sc{font-size:12px;color:var(--mut)}
.tech-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px 14px;margin-top:6px}
.tech-fold{display:grid;grid-template-columns:1fr 1fr;gap:6px 14px;margin-top:6px;padding-top:6px;border-top:1px dashed var(--line)}
.dim{display:flex;gap:8px;font-size:12px}
.dim b{color:var(--mut);font-weight:400;flex:0 0 48px}
.tech-interp{font-size:12.5px;color:#cdd7e2;margin-top:6px;line-height:1.6}
.timeline{position:relative;padding-left:14px;margin-top:6px;border-left:2px solid var(--line)}
.tl-item{position:relative;padding:7px 0}
.tl-item::before{content:"";position:absolute;left:-19px;top:12px;width:9px;height:9px;border-radius:50%;background:var(--acc);border:2px solid var(--bg)}
.tl-time{font-size:12px;color:var(--acc);font-weight:700}
.tl-event{font-size:13px;color:var(--tx);margin:2px 0}
.tl-impact{font-size:12px;color:var(--mut);line-height:1.5}
.src-box{font-size:12.5px;line-height:1.7;background:rgba(74,168,255,.05);border-radius:8px;padding:10px 12px}
.kv{display:flex;justify-content:space-between;gap:8px;padding:4px 0;border-bottom:1px solid var(--line)}
.kv .ok{color:#26c281} .kv .warn{color:var(--neu)} .kv .q{color:var(--mut)}
.tip{border-bottom:1px dotted var(--acc);cursor:help}
.tip:hover{position:relative}
.tip:hover::after{content:attr(data-tip);position:absolute;left:0;top:130%;z-index:50;background:#0b0f15;border:1px solid var(--line);color:var(--tx);font-size:11.5px;line-height:1.4;padding:6px 8px;border-radius:8px;width:260px;box-shadow:0 4px 14px rgba(0,0,0,.5);font-weight:400}
/* 涨跌色说明（表格顶部固定） */
.color-legend{font-size:11px;color:var(--mut);padding:4px 0;margin-bottom:6px;display:flex;gap:10px;flex-wrap:wrap}
.color-legend span{display:inline-flex;align-items:center;gap:4px}
@media (max-width:680px){
  .two-col{grid-template-columns:1fr}
  .topnav{font-size:10px;padding:4px 6px}
  .hl-grid{grid-template-columns:1fr}
  .ol-list{grid-template-columns:1fr}
  .tech-grid,.tech-fold{grid-template-columns:1fr}
}
@media print{
  body{background:#fff;color:#111;max-width:100%;padding-top:0}
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
    // ① 全球涨跌幅分组条形图（每组独立图表，防止堆叠）
    if(document.getElementById('chgBar_0')){
      const groups = (REPORT.global||[]);
      const gColors = ['#4aa8ff','#26c281','#d9a441','#a78bfa','#f472b6','#22d3ee','#fb923c','#94a3b8'];
      groups.forEach((g, gi)=>{
        const canvas = document.getElementById('chgBar_'+gi);
        if(!canvas) return;
        const rows = g.rows||[];
        if(!rows.length) return;
        const names = rows.map(r=>r.name);
        const vals = rows.map(r=>r.chg||0);
        const c = echarts.init(canvas, null, {renderer:'canvas'});
        c.setOption({
          backgroundColor:'transparent',
          grid:{left:155,right:50,top:4,bottom:4},
          tooltip:{trigger:'axis',axisPointer:{type:'shadow'},
            formatter:function(p){const d=p[0];return d.name+'<br/>涨跌: '+d.value.toFixed(2)+'%';}},
          xAxis:{type:'value',axisLabel:{color:DARK.mut,formatter:'{value}%'},splitLine:{lineStyle:{color:'#222b36'}}},
          yAxis:{type:'category',data:names.slice().reverse(),
            axisLabel:{color:DARK.tx,fontSize:10.5,width:150,overflow:'none',interval:0},
            axisLine:{lineStyle:{color:'#2a3340'}},axisTick:{show:false}},
          series:[{type:'bar',data:vals.slice().reverse().map(v=>({value:v,
            itemStyle:{color:v>0?DARK.up:(v<0?DARK.down:DARK.neu)}})),
            barCategoryGap:'30%',
            label:{show:true,position:'right',color:DARK.tx,fontSize:10,distance:5,formatter:'{c}%'}}]
        });
      });
    }
    // ①b 关键标的分时走势（从 tech[].kline 提取近10日收盘价折线）
    if(document.getElementById('trendBar')){
      const techArr = (REPORT.tech||[]);
      let trendIdx = 0;
      techArr.forEach(t=>{
        if(!t.kline || !t.kline.dates || t.kline.dates.length===0) return;
        const el = document.getElementById('trend_'+trendIdx);
        if(!el) return;
        const closes = t.kline.ohlc.map(d=>d[1]);
        const dates = t.kline.dates;
        if(closes.length < 2) return;
        const ct = echarts.init(el, null, {renderer:'canvas'});
        ct.setOption({
          backgroundColor:'transparent',
          grid:{left:36,right:8,top:8,bottom:18},
          tooltip:{trigger:'axis',formatter:'{b}<br/>收盘: {c}'},
          xAxis:{type:'category',data:dates.slice(-10),axisLabel:{color:DARK.mut,fontSize:8,rotate:30},axisLine:{lineStyle:{color:'#2a3340'}}},
          yAxis:{type:'value',scale:true,axisLabel:{color:DARK.mut,fontSize:8},splitLine:{lineStyle:{color:'#222b36'}}},
          series:[{type:'line',data:closes.slice(-10),smooth:true,symbol:'circle',symbolSize:4,
            lineStyle:{color:DARK.acc,width:1.5},itemStyle:{color:DARK.acc},
            areaStyle:{color:{type:'linear',x:0,y:0,x2:0,y2:1,
              colorStops:[{offset:0,color:'rgba(74,168,255,.2)'},{offset:1,color:'rgba(74,168,255,.01)'}]}}}]
        });
        trendIdx++;
      });
    }
    // 持仓关联指数趋势图（htrend_0/1/2）
    if(document.getElementById('htrend_0')){
      const techArr2 = (REPORT.tech||[]);
      // 匹配：中证半导、人工智能、恒生科技/港股创新药
      const hTargets = ['中证半导','931865','人工智能','931071','恒生科技','港股','创新药'];
      const hMatched = [null,null,null]; // [中证半导, 人工智能, 恒生科技]
      techArr2.forEach(t=>{
        const idx = t.index||'';
        if(!t.kline || !t.kline.dates || t.kline.dates.length===0) return;
        if(idx.includes('中证半导')||idx.includes('931865')) hMatched[0] = t;
        if(idx.includes('人工智能')||idx.includes('931071')) hMatched[1] = t;
        if(idx.includes('恒生科技')||idx.includes('创新药')) hMatched[2] = t;
      });
      hMatched.forEach((t,i)=>{
        const el = document.getElementById('htrend_'+i);
        if(!el || !t) return;
        const closes = t.kline.ohlc.map(d=>d[1]);
        const ct = echarts.init(el, null, {renderer:'canvas'});
        ct.setOption({
          backgroundColor:'transparent',
          grid:{left:36,right:8,top:4,bottom:16},
          tooltip:{trigger:'axis'},
          xAxis:{type:'category',data:(t.kline.dates||[]).slice(-10),axisLabel:{color:DARK.mut,fontSize:8,rotate:30},axisLine:{lineStyle:{color:'#2a3340'}}},
          yAxis:{type:'value',scale:true,axisLabel:{color:DARK.mut,fontSize:8},splitLine:{lineStyle:{color:'#222b36'}}},
          series:[{type:'line',data:closes.slice(-10),smooth:true,symbol:'circle',symbolSize:4,
            lineStyle:{color:DARK.acc,width:1.5},itemStyle:{color:DARK.acc},
            areaStyle:{color:{type:'linear',x:0,y:0,x2:0,y2:1,colorStops:[{offset:0,color:'rgba(74,168,255,.25)'},{offset:1,color:'rgba(74,168,255,.01)'}]}}}]
        });
      });
    }
    if(document.getElementById('trendBar')){
      const techArr = (REPORT.tech||[]);
      let trendIdx = 0;
      techArr.forEach(t=>{
        if(!t.kline || !t.kline.dates || t.kline.dates.length===0) return;
        const el = document.getElementById('trend_'+trendIdx);
        if(!el) return;
        const closes = t.kline.ohlc.map(d=>d[1]);
        const dates = t.kline.dates;
        if(closes.length < 2) return;
        const ct = echarts.init(el, null, {renderer:'canvas'});
        ct.setOption({
          backgroundColor:'transparent',
          grid:{left:36,right:8,top:8,bottom:18},
          tooltip:{trigger:'axis',formatter:'{b}<br/>收盘: {c}'},
          xAxis:{type:'category',data:dates.slice(-10),axisLabel:{color:DARK.mut,fontSize:8,rotate:30},axisLine:{lineStyle:{color:'#2a3340'}}},
          yAxis:{type:'value',scale:true,axisLabel:{color:DARK.mut,fontSize:8},splitLine:{lineStyle:{color:'#222b36'}}},
          series:[{type:'line',data:closes.slice(-10),smooth:true,symbol:'circle',symbolSize:4,
            lineStyle:{color:DARK.acc,width:1.5},itemStyle:{color:DARK.acc},
            areaStyle:{color:{type:'linear',x:0,y:0,x2:0,y2:1,
              colorStops:[{offset:0,color:'rgba(74,168,255,.2)'},{offset:1,color:'rgba(74,168,255,.01)'}]}}}]
        });
        trendIdx++;
      });
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
    // ③ 情绪趋势折线图（近10日，替代原仪表盘）
    if(document.getElementById('sentTrend')){
      const st = (REPORT.sentiment||{}).semiconductor_trend;
      const trend_dates = (st||{}).dates || [];
      const trend_vals = (st||{}).values || [];
      const current = (REPORT.sentiment||{}).semiconductor;
      if(trend_dates.length){
        const ct = echarts.init(document.getElementById('sentTrend'), null, {renderer:'canvas'});
        ct.setOption({
          backgroundColor:'transparent',
          grid:{left:40,right:16,top:10,bottom:20},
          tooltip:{trigger:'axis',formatter:'{b}<br/>情绪分: {c}'},
          xAxis:{type:'category',data:trend_dates,axisLabel:{color:DARK.mut,fontSize:9},axisLine:{lineStyle:{color:'#2a3340'}}},
          yAxis:{type:'value',min:0,max:100,axisLabel:{color:DARK.mut,fontSize:9},splitLine:{lineStyle:{color:'#222b36'}}},
          series:[{type:'line',data:trend_vals,smooth:true,
            lineStyle:{color:DARK.acc,width:2},itemStyle:{color:DARK.acc},
            areaStyle:{color:{type:'linear',x:0,y:0,x2:0,y2:1,
              colorStops:[{offset:0,color:'rgba(74,168,255,.3)'},{offset:1,color:'rgba(74,168,255,.02)'}]}},
            markLine:{silent:true,symbol:'none',
              data:[{yAxis:20,label:{formatter:'恐惧 20',color:DARK.down,fontSize:9},lineStyle:{color:DARK.down,type:'dashed'}},
                    {yAxis:80,label:{formatter:'贪婪 80',color:DARK.up,fontSize:9},lineStyle:{color:DARK.up,type:'dashed'}}]}
          }]
        });
        // 底部5日Δ标签
        if(trend_vals.length>=5){
          const d5 = trend_vals[trend_vals.length-1] - trend_vals[trend_vals.length-5];
          const el = document.querySelector('.gauge-cap');
          if(el){ el.innerHTML = '半导体情绪 近10日趋势 · 5日Δ=<span style="color:'+(d5<0?DARK.down:DARK.up)+';font-weight:700">'+(d5>0?'+':'')+d5.toFixed(0)+'</span>'+(d5<-10?'⚠️ 加速恐慌':(d5>10?' 🔥 情绪过热':'')); }
        }
      }
    }
    // ④ 日K线 + 月K线（技术面，每个持仓关联指数）
    if(REPORT.tech && REPORT.tech.length){
      REPORT.tech.forEach(t => {
        const kline = t.kline;
        if(!kline || !kline.dates || !kline.ohlc || !kline.dates.length) return;
        const cid = (t.index||"").replace(/[^a-zA-Z0-9]/g, '_');
        const dates = kline.dates;
        const ohlc = kline.ohlc;
        
        // 日K（最近60日）+ MA20/MA60 overlay
        const dEl = document.getElementById('kx_'+cid);
        if(dEl){
          const dDates = dates.slice(-60);
          const dOhlc = ohlc.slice(-60);
          const ma20 = (kline.ma20||[]).slice(-60);
          const ma60 = (kline.ma60||[]).slice(-60);
          const c = echarts.init(dEl, null, {renderer:'canvas'});
          const series = [{type:'candlestick',name:'日K',data:dOhlc,
            itemStyle:{color:DARK.up,color0:DARK.down,borderColor:DARK.up,borderColor0:DARK.down}}];
          if(ma20.length) series.push({type:'line',name:'MA20',data:ma20,smooth:false,
            lineStyle:{color:'#d9a441',width:1},symbol:'none'});
          if(ma60.length) series.push({type:'line',name:'MA60',data:ma60,smooth:false,
            lineStyle:{color:'#4aa8ff',width:1},symbol:'none'});
          c.setOption({
            backgroundColor:'transparent',
            grid:{left:48,right:16,top:10,bottom:24},
            tooltip:{trigger:'axis',axisPointer:{type:'cross'},
              formatter:function(p){const d=p[0];if(!d)return'';const o=d.data;return d.name+'<br/>开:'+o[0]+' 收:'+o[1]+'<br/>低:'+o[2]+' 高:'+o[3];}},
            legend:{show:true,top:0,textStyle:{color:DARK.mut,fontSize:9}},
            xAxis:{type:'category',data:dDates,axisLabel:{color:DARK.mut,fontSize:8},axisLine:{lineStyle:{color:'#2a3340'}}},
            yAxis:{type:'value',scale:true,axisLabel:{color:DARK.mut,fontSize:9},splitLine:{lineStyle:{color:'#222b36'}}},
            series:series
          });
        }
        
        // 月K聚合（从全部日K数据按月份分组）
        const months={};
        dates.forEach((d,i)=>{
          const m=d.substring(0,7);
          const c=ohlc[i];
          if(!months[m]){months[m]={open:c[0],close:c[1],low:c[2],high:c[3]};}
          else{months[m].close=c[1];months[m].low=Math.min(months[m].low,c[2]);months[m].high=Math.max(months[m].high,c[3]);}
        });
        const mKeys=Object.keys(months).sort();
        const mDates=mKeys.slice(-12);
        const mData=mDates.map(m=>[months[m].open,months[m].close,months[m].low,months[m].high]);
        
        const mEl = document.getElementById('km_'+cid);
        if(mEl){
          const c = echarts.init(mEl, null, {renderer:'canvas'});
          c.setOption({
            backgroundColor:'transparent',
            grid:{left:48,right:16,top:10,bottom:24},
            tooltip:{trigger:'axis',axisPointer:{type:'cross'},
              formatter:function(p){const d=p[0];if(!d)return'';const o=d.data;return d.name+'<br/>开:'+o[0].toFixed(2)+' 收:'+o[1].toFixed(2)+'<br/>低:'+o[2].toFixed(2)+' 高:'+o[3].toFixed(2);}},
            xAxis:{type:'category',data:mDates,axisLabel:{color:DARK.mut,fontSize:8},axisLine:{lineStyle:{color:'#2a3340'}}},
            yAxis:{type:'value',scale:true,axisLabel:{color:DARK.mut,fontSize:9},splitLine:{lineStyle:{color:'#222b36'}}},
            series:[{type:'candlestick',name:'月K',data:mData,
              itemStyle:{color:DARK.up,color0:DARK.down,borderColor:DARK.up,borderColor0:DARK.down}}]
          });
        }
      });
    }
  }catch(e){ console.error('chart error', e); }
}
window.addEventListener('load', initCharts);
// 导航滚动高亮（Intersection Observer）
try{
  const navLinks = document.querySelectorAll('#topnav a[href^="#"]');
  const sections = Array.from(navLinks).map(a=>document.getElementById(a.getAttribute('href').slice(1))).filter(Boolean);
  const io = new IntersectionObserver(entries=>{
    let activeId = '';
    entries.forEach(e=>{if(e.isIntersecting)activeId=e.target.id;});
    if(activeId) navLinks.forEach(a=>{a.classList.toggle('active',a.getAttribute('href')==='#'+activeId);});
  },{rootMargin:'-80px 0px -60% 0px'});
  sections.forEach(s=>io.observe(s));
}catch(e){console.error('nav scroll err',e);}
// 打印页面
document.querySelectorAll('.nav-actions button').forEach(b=>{
  b.addEventListener('click',()=>window.print());
});
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

    # ========== 方法论 · 四：逻辑计算层 ==========
    # 1. 半导体集中度自动计算
    semic = calc_semic_concentration(data.get("holdings") or [])
    if semic["over_thr60"]:
        # 追加到 holdings_constraint 或 top_risk
        sc_warn = "⚠️ 半导体赛道集中度%.1f%%（≥60%），极高集中度风险" % semic["total_pct"]
        core = data.get("core") or {}
        old_top = core.get("top_risk", "")
        if sc_warn not in old_top:
            core["top_risk"] = (old_top + " · " + sc_warn) if old_top else sc_warn

    # 2. 风险评分自动兜底（agent 未提供时自动计算）
    core = data.get("core") or {}
    if core.get("risk_score") is None:
        # 用情绪面和已有数据估算
        sent = data.get("sentiment") or {}
        sem_score = num(sent.get("semiconductor"))
        if sem_score is not None:
            computed = calc_risk_score({
                "sentiment": sem_score,
                "technical": 50,   # 默认中性
                "event": 50,
                "capital": 50,
                "news": 50,
            })
            core["risk_score"] = computed["score"]
            core["risk_score_note"] = "自动估算（情绪%.0f+默认值）" % sem_score

    # 3. 自动预警检查
    alerts = check_alerts(data.get("holdings") or [])
    alert_banners = ""
    for a in alerts:
        lvl = a["level"]
        icon = {"red": "🔴", "orange": "🟠"}.get(lvl, "🟡")
        cls = "emergency-banner" + (" orange" if lvl == "orange" else "")
        alert_banners += '<div class="%s"><span class="eb-icon">%s</span><span>%s</span></div>' % (cls, icon, esc(a["text"]))
    # 把预警横幅注入到报告最顶部
    alert_section = f'<section id="alerts">{alert_banners}</section>' if alert_banners else ""
    # ========== 方法论结束 ==========

    # 是否有头条速览/今日前瞻/风险提示等新板块
    has_headlines = bool(data.get("headlines"))
    has_keyevents = bool(data.get("key_events"))
    has_china = bool(data.get("china_dynamics"))
    has_outlook = bool(data.get("today_outlook"))
    has_risk = bool(data.get("risk_warnings"))

    # 动态导航：根据数据有无决定是否显示
    nav_links = []
    def nav_a(href, label, always=True):
        if always or (not always and data.get(href.replace("#",""))):
            nav_links.append('<a href="%s">%s</a>' % (href, label))
    nav_a("#headlines","速览", has_headlines)
    nav_a("#core","定调")
    nav_a("#global","全球")
    nav_a("#keyevents","事件", has_keyevents)
    nav_a("#conflict","风险")
    nav_a("#bullbear","多空")
    nav_a("#hold","持仓")
    nav_a("#china","中国", has_china)
    nav_a("#outlook","前瞻", has_outlook)
    nav_a("#tech","技术")
    nav_a("#risktips","提示", has_risk)
    nav_a("#cred","来源")

    nav = ('<nav class="topnav" id="topnav">%s'
            '<span class="nav-actions">'
            '<a href="早间全球分析-%s.html" title="昨日报告">←昨日</a>'
            '<a href="../../index.html" title="收件箱">🏠</a>'
            '<button onclick="window.print()" title="导出 PDF">🖨️ PDF</button>'
            '</span></nav>') % (' '.join(nav_links), prev)

    body = (alert_section +
            render_headlines(data.get("headlines")) +
            render_core(data.get("core"), data.get("sentiment")) +
            render_global(data.get("global")) +
            render_key_events(data.get("key_events")) +
            render_conflicts(data.get("conflicts")) +
            render_bullbear(data.get("bulls"), data.get("bears")) +
            render_holdings(data.get("holdings"), data.get("holdings_constraint")) +
            render_earnings(data.get("earnings")) +
            render_china(data.get("china_dynamics")) +
            render_outlook(data.get("today_outlook")) +
            render_tech(data.get("tech")) +
            render_events(data.get("events")) +
            render_risk_tips(data.get("risk_warnings")) +
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
