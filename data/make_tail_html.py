# -*- coding: utf-8 -*-
"""
make_tail_html.py  —  尾盘决策（收盘前操作预案）报告生成器
读取 data/tail_<DATE>.json（由尾盘自动化 agent 在 neodata/westock 分析后落盘的结构化数据），
渲染为优化版 尾盘决策-<DATE>.html。

定位：尾盘终极决策 —— 用户尾盘前 10 分钟浏览，10 秒锁定操作。
优化点（对应需求 P0/P1/P2/P3）：
  P0  ① 顶部常驻悬浮「尾盘终极指令条」（sticky）：左侧核心结论 / 中间唯一主动操作(橙高亮) /
        右侧风控底线(红) / 时间戳 + 极简导航(持仓/板块/止损 + 当日早报/午盘跳转)
       ② 首屏「核心指标速览」4 大字卡（上证 / 创业板 / 领涨板块 / 板块主力净流入）
       ③ 模块优先级重排：指令条→核心速览→持仓明细[日K+主力]→板块量化→硬止损→情绪→逻辑[折叠]→来源[折叠]
  P0  持仓卡片升级——日K图+主力研判+操作指令三位一体。每持仓独立横向卡片，按仓位降序，
        重仓默认展开小仓折叠。左 1/3 迷你日K(ECharts candlestick, MA5/MA20, 红涨绿跌,
        标注当前价/支撑压力, 当日K高亮; 降级：缺失换文字版)；右 2/3 三栏(主力行为研判 /
        五维技术评分 / 操作指令区[大字指令+硬止损线+持有收益+缓冲空间+超限红标])
  P1  板块日K量化信号横向条形图(分数进度条+多空标签+主力净流入, 持仓强关联高亮, 点击展开详解)
        硬止损监控红色进度条卡片(当前亏损/-8%比例, 逼近标「盯盘」, 底部"当前无标的触发强制卖出")
        情绪指数结论前置("F&G X·中性"+核心背离提示, 8 分项折叠)
  P2  单文件模板化(数据封装单 JSON 变量注入); 模块化数据接口 5 字段
        (instruction/position/sector/risk/sentiment 独立渲染, 单缺失不阻塞)
  P3  风险高亮预警边框; 极简悬浮导航; 全链路跳转(当日早报/午盘); 移动端纵向+横向滚动; 打印

视觉与信号体系：与早报/午报/晚报/大盘研判完全统一
  —— 同一套深色配色板 + 同一套 涨红跌绿 + 同一套 [[术语|解释]] 悬停。
"""
import json
import os
import sys
import glob
import re
import datetime

from render_utils import (
    esc, tip, num, pcls, pbold, chg_span, bar, level_info,
    calc_risk_score, calc_stop_loss_dist, calc_semic_concentration,
    check_alerts, r2, missing_val, yesterdate, RULES,
)

BASE = os.path.dirname(os.path.abspath(__file__))
REPORTS = os.path.join(BASE, "reports")
CRED_TIER = "T2"

def miss(v):
    """缺失值标准化（render_utils 补充：尾盘版用 ⚠ 数据源未返回）。"""
    if v is None:
        return '<span class="mut">⚠ 数据源未返回</span>'
    s = str(v).strip()
    if s in ("未连接", "N/A", "数据源未返回", "—", ""):
        return '<span class="mut">⚠ %s</span>' % s
    return esc(s)
# ---------- 尾盘专用信号标签 ----------
def op_cls(instruction, overweight=False):
    """操作指令 → css 类。HOLD绿 / 减仓·卖出·转换红 / 盯盘·观察橙。"""
    s = (instruction or "").upper()
    if "SELL" in s or "减仓" in s or "转换" in s:
        return "op-sell"
    if "盯盘" in s or "观察" in s or "WATCH" in s:
        return "op-watch"
    if "HOLD" in s:
        return "op-hold"
    return "op-watch"
def mf_cls(q):
    """主力定性 → css 类。抢筹/拉升绿 / 出货红 / 观望·洗盘灰。"""
    s = (q or "")
    if "抢筹" in s or "拉升" in s:
        return "mf-up"
    if "出货" in s:
        return "mf-down"
    return "mf-neu"
def tech_cls(level):
    s = (level or "")
    if "偏多" in s:
        return "up"
    if "偏空" in s:
        return "down"
    return "neu"
def core_cls(c):
    """指令条核心结论 → css。hold绿 / sell红 / watch橙。"""
    s = (c or "").lower()
    if "hold" in s or "持有" in s or "禁止" in s:
        return "core-hold"
    if "sell" in s or "卖出" in s or "减仓" in s:
        return "core-sell"
    return "core-watch"

# ---------- 各模块渲染 ----------
def render_cmd_bar(instruction, date):
    """P0 顶部常驻悬浮指令条 + 极简导航。"""
    if not instruction:
        instruction = {}
    cc = instruction.get("core_conclusion", "—")
    cc_cls = core_cls(instruction.get("core_conclusion_cls") or cc)
    active = instruction.get("active_action") or "（无主动操作）"
    risk = instruction.get("risk_floor") or "单基 -8% 硬止损"
    ts = instruction.get("timestamp_label") or ("数据截至 " + date)
    disc = instruction.get("discipline_note")
    disc_html = ('<div class="cmd-disc">%s</div>' % tip(disc)) if disc else ""
    nav = ('<nav class="cmd-nav">'
            '<a href="#hold">📦 持仓</a><a href="#sector">📊 板块</a><a href="#stop">🔻 止损</a>'
            '<a href="#twin">🕒 窗口</a><a href="#pl">🔒 止盈</a><a href="#rb">🔄 调仓</a>'
            '<span class="nav-sep">|</span>'
            '<a href="早间全球分析-%s.html">🌅 早报</a>'
            '<a href="午盘收盘-%s.html">📊 午盘</a>'
            '<a href="../../index.html">📱 收件箱</a></nav>') % (date, date)
    return f'''
<div class="cmdbar {cc_cls}">
  <div class="cmd-main">
    <div class="cmd-core"><span class="dot"></span>{esc(cc)}</div>
    <div class="cmd-active">⚡ 唯一主动操作：{esc(active)}</div>
    <div class="cmd-risk">🔴 {esc(risk)}</div>
  </div>
  <div class="cmd-meta">
    <span class="ts">🕒 {esc(ts)}</span>
    {nav}
  </div>
  {disc_html}
</div>'''

def render_core_kpis(kpis):
    """P0 首屏核心指标速览 4 大字卡。"""
    if not kpis:
        return ""
    cards = ""
    for k in kpis:
        cls = k.get("cls", "neu")
        tag = k.get("tag")
        tag_html = ('<span class="kpi-tag">%s</span>' % esc(tag)) if tag else ""
        sub = k.get("sub")
        sub_html = ('<div class="kpi-sub">%s</div>' % esc(sub)) if sub else ""
        cards += ('<div class="kpi"><div class="kpi-l">%s%s</div>'
                  '<div class="kpi-v %s">%s</div>%s</div>') % (
            esc(k.get("label", "")), tag_html, cls, esc(k.get("value", "")), sub_html)
    return f'''
<section id="core" class="card">
  <h2>📈 核心指标速览 <span class="badge">收盘前 10 秒定操作</span></h2>
  <div class="kpi-row">{cards}</div>
  <div class="legend">涨跌配色 <b class="up">红=涨</b>/<b class="down">绿=跌</b>（A股惯例）· 尾盘决策以实时快照为准，收盘后以官方净值复核</div>
</section>'''

def render_holdings(holdings):
    """P0 持仓明细卡片：日K + 主力研判 + 操作指令 三位一体。"""
    if not holdings:
        return ""
    hs = sorted(holdings, key=lambda h: -(num(h.get("weight_pct")) or 0))
    cards = ""
    for i, h in enumerate(hs):
        name = tip(h.get("name", ""))
        sector = esc(h.get("sector") or "—")
        w = num(h.get("weight_pct"))
        w_html = ("%.2f%%" % w) if w is not None else miss(None)
        ret = num(h.get("hold_return_pct"))
        ret_html = chg_span(ret) if ret is not None else miss(None)
        instr = h.get("instruction") or "HOLD"
        ocls = op_cls(instr, h.get("overweight"))
        ow = h.get("overweight")
        ow_badge = '<span class="ow-badge">⚠ 单仓超限</span>' if ow else ""
        # 左 1/3 日K + 月K
        k = h.get("kline")
        if k and k.get("ohlc") and len(k.get("ohlc")):
            kline_html = ('<div style="height:140px"><canvas id="kline_%d"></canvas></div>'
                          '<div style="height:100px;margin-top:6px"><canvas id="kmonth_%d"></canvas></div>') % (i, i)
        else:
            kt = h.get("kline_text") or "⚠ 日K数据未返回"
            kline_html = '<div class="kline-text">%s</div>' % esc(kt)
        # 右 2/3 三栏
        mf = h.get("main_force") or {}
        mf_net = mf.get("net_inflow")
        mf_net_html = ("%s亿" % esc(mf_net)) if mf_net is not None else miss(None)
        mf_big = mf.get("big_order_pct")
        mf_big_html = ("%s%%" % esc(mf_big)) if mf_big is not None else miss(None)
        mf_q = mf.get("qualitative") or "—"
        mf_qcls = mf_cls(mf_q)
        mf_hint = tip(mf.get("hint") or "")
        ts = h.get("tech_score") or {}
        comp = ts.get("composite")
        comp_html = ("%s" % esc(comp)) if comp is not None else miss(None)
        tlevel = ts.get("level") or "—"
        tlevel_cls = tech_cls(tlevel)
        # 操作指令区
        stop = num(h.get("stop_loss_pct"))
        stop_html = ("%s%%" % stop) if stop is not None else "—"
        rel_idx = h.get("related_index")
        rel_chg = num(h.get("related_index_chg"))
        rel_html = ("%s %s" % (esc(rel_idx), chg_span(rel_chg))) if rel_idx else miss(None)
        # 缓冲空间：持有收益 - 止损线
        buf_html = miss(None)
        warn_buf = False
        if ret is not None and stop is not None:
            buf = ret - stop
            buf_html = "距 -8%% 还有 <b>%.2f%%</b>" % buf
            if buf < 3:
                warn_buf = True
                buf_html = '<span class="buf-warn">⚠ 逼近止损 · 距 -8%% 仅 <b>%.2f%%</b></span>' % buf
        logic = tip(h.get("logic") or "")
        cards += f'''
<details class="hcard {'open' if ((w or 0) >= 10 or ow) else ''}" {'open' if ((w or 0) >= 10 or ow) else ''}>
  <summary class="hsum">
    <span class="hname">{name}</span>
    <span class="hsector">{sector}</span>
    <span class="hweight">仓 {w_html}</span>
    <span class="hret">{ret_html}</span>
    <span class="op-tag {ocls}">{esc(instr)}</span>
    {ow_badge}
  </summary>
  <div class="hbody">
    <div class="hkline">{kline_html}</div>
    <div class="hright">
      <div class="hcol">
        <div class="hcol-h">主力行为研判</div>
        <div class="kv"><span>净流入</span><span class="{'up' if (mf_net or 0)>0 else 'down'}">{mf_net_html}</span></div>
        <div class="kv"><span>超大单占比</span><span>{mf_big_html}</span></div>
        <div class="kv"><span>定性</span><span class="mf {mf_qcls}">{esc(mf_q)}</span></div>
        <div class="hcol-note">{mf_hint}</div>
      </div>
      <div class="hcol">
        <div class="hcol-h">五维技术评分</div>
        <div class="tech-comp"><span class="{tlevel_cls}">{comp_html}</span><span class="tech-lvl {tlevel_cls}">{esc(tlevel)}</span></div>
        <div class="kv"><span>趋势</span><span>{esc(ts.get('trend') or '—')}</span></div>
        <div class="kv"><span>量价</span><span>{esc(ts.get('vol_price') or '—')}</span></div>
        <div class="kv"><span>形态</span><span>{esc(ts.get('shape') or '—')}</span></div>
      </div>
      <div class="hcol">
        <div class="hcol-h">操作指令区</div>
        <div class="op-big {ocls}">{esc(instr)}</div>
        <div class="kv"><span>硬止损</span><span class="down">{stop_html}</span></div>
        <div class="kv"><span>持有收益</span><span>{ret_html}</span></div>
        <div class="kv"><span>缓冲</span><span>{buf_html}</span></div>
        <div class="kv"><span>关联指数</span><span>{rel_html}</span></div>
        <div class="hcol-note {('warn' if warn_buf else '')}">{logic}</div>
      </div>
    </div>
  </div>
</details>'''
    return f'''
<section id="hold" class="card">
  <h2>📦 持仓明细 · 日K+主力+指令 <span class="badge">按仓位降序 · 重仓展开</span></h2>
  <div class="hcards">{cards}</div>
</section>'''

def render_sector(sector):
    """P1 板块日K量化信号横向条形图 + 可展开详解。"""
    if not sector:
        return ""
    bars = sector.get("bars") or []
    rows = ""
    for b in bars:
        score = num(b.get("score")) or 0
        ten = b.get("tendency") or "—"
        ten_cls = tech_cls(ten)
        linked = b.get("linked")
        flow = num(b.get("net_inflow"))
        flow_html = ("%s亿" % chg_span(flow)) if flow is not None else miss(None)
        tag = b.get("tag")
        tag_html = ('<span class="sbar-tag">%s</span>' % esc(tag)) if tag else ""
        cls = "sbar-row" + (" linked" if linked else "")
        rows += ('<div class="%s"><div class="sbar-name">%s%s</div>'
                 '<div class="sbar-track"><div class="sbar-fill %s" style="width:%.0f%%"></div>'
                 '<span class="sbar-score">%s</span></div>'
                 '<div class="sbar-ten %s">%s</div>'
                 '<div class="sbar-flow">%s</div></div>') % (
            cls, esc(b.get("name", "")), tag_html, ten_cls, score, esc(score),
            ten_cls, esc(ten), flow_html)
    detail = sector.get("detail")
    bottom = sector.get("bottom_signals")
    top = sector.get("top_signals")
    close = sector.get("close_special")
    extra = ""
    if detail or bottom or top or close:
        extra = ('<div class="sbar-extra">%s%s%s%s</div>') % (
            ("<div><b>主力行为详解</b>：%s</div>" % tip(detail)) if detail else "",
            ("<div class='up'>🟢 止跌信号：%s</div>" % esc(bottom)) if bottom else "",
            ("<div class='down'>🔴 见顶信号：%s</div>" % esc(top)) if top else "",
            ("<div>⚡ 收盘暗号：%s</div>" % esc(close)) if close else "")
    return f'''
<section id="sector" class="card">
  <h2>📊 板块日K量化信号 <span class="badge">五维 · 持仓强关联高亮</span></h2>
  <div class="sbars">{rows}</div>
  {extra}
  <div class="legend">评分 = 趋势40%+量价30%+形态15%+主力15%；≥65偏多 / 35-64中性 / ≤34偏空。进度条长度=多空评分。</div>
</section>'''

def render_risk_stop(risk):
    """P1 硬止损风险监控红色进度条 + 底部铁律。"""
    if not risk:
        return ""
    hs = risk.get("hard_stop") or {}
    items = hs.get("items") or []
    rows = ""
    for it in items:
        name = esc(it.get("name", ""))
        cur = num(it.get("cur_loss_pct"))
        stop = num(it.get("stop_loss_pct")) or -8
        ratio = 0
        if cur is not None and stop:
            ratio = min(100, abs(cur) / abs(stop) * 100)
        cur_html = ("%s%%" % cur) if cur is not None else miss(None)
        warn = it.get("warn")
        warn_label = it.get("warn_label") or "盯盘"
        warn_badge = ('<span class="stop-warn">%s</span>' % esc(warn_label)) if warn else ""
        cls = "stop-fill warn" if warn else "stop-fill"
        rows += ('<div class="stop-row"><div class="stop-name">%s</div>'
                 '<div class="stop-track"><div class="%s" style="width:%.1f%%"></div></div>'
                 '<div class="stop-pct">%s</div>%s</div>') % (
            name, cls, ratio, cur_html, warn_badge)
    floor = hs.get("floor_text") or "当前无标的触发强制卖出"
    alerts = risk.get("alerts") or []
    alert_html = ""
    if alerts:
        a = ""
        for al in alerts:
            lvl = al.get("level", "orange")
            a += ('<div class="alert-item %s"><b>%s</b> — %s</div>') % (
                lvl, esc(al.get("text", "")), esc(al.get("detail", "")))
        alert_html = '<div class="alerts">%s</div>' % a
    return f'''
<section id="stop" class="card">
  <h2>🔻 硬止损风险监控 <span class="badge">当前亏损 / -8% 进度</span></h2>
  <div class="stops">{rows}</div>
  <div class="stop-floor">🛡️ {esc(floor)}</div>
  {alert_html}
</section>'''

def render_sentiment(sent):
    """P1 情绪指数结论前置 + 8 分项折叠。"""
    if not sent:
        return ""
    idx = sent.get("index")
    idx_html = ("%s" % esc(idx)) if idx is not None else "—"
    level = sent.get("level") or "中性"
    lvl_cls = tech_cls(level)
    div = sent.get("divergence")
    div_html = ('<div class="fg-div">⚡ 核心背离：%s</div>' % tip(div)) if div else ""
    action = sent.get("action")
    action_html = ('<div class="fg-action">尾盘情绪指令：%s</div>' % esc(action)) if action else ""
    factors = sent.get("factors") or []
    frows = ""
    for f in factors:
        score = num(f.get("score"))
        sc_cls = pcls(score - 50) if score is not None else "neu"
        frows += ('<tr><td>%s</td><td class="mut">%s</td>'
                  '<td class="%s">%s</td><td class="mut">%s</td><td class="mut">%s</td></tr>') % (
            esc(f.get("name", "")), esc(f.get("raw", "")),
            sc_cls, esc(score if score is not None else "—"),
            esc(f.get("weight", "")), esc(f.get("src", "")))
    return f'''
<section id="sent" class="card">
  <h2>🌡️ 市场情绪 · 结论前置 <span class="badge">恐惧贪婪指数</span></h2>
  <div class="fg-big">F&amp;G <b>{idx_html}</b> / 100 · <span class="{lvl_cls}">{esc(level)}</span></div>
  {div_html}
  {action_html}
  <details class="fg-detail">
    <summary>📋 8 因子分项（点击展开）</summary>
    <table><tr><th>因子</th><th>原始值</th><th>评分</th><th>加权</th><th>来源</th></tr>{frows}</table>
  </details>
  <div class="note">情绪信号不覆盖 -8% 硬止损铁律，仅影响加仓/止盈的弹性决策。</div>
</section>'''

def render_logic(logic):
    """P2 操作逻辑引擎（默认折叠）。"""
    if not logic:
        return ""
    def block(title, key, cls):
        v = logic.get(key)
        if not v:
            return ""
        return '<div class="lg-block %s"><div class="lg-h">%s</div><pre class="lg-pre">%s</pre></div>' % (
            cls, esc(title), esc(v))
    rows = logic.get("action_rows")
    rows_html = ""
    if rows:
        r = ""
        for ar in rows:
            r += ('<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>') % (
                esc(ar.get("fund", "")), esc(ar.get("cmd", "")), esc(ar.get("price", "")),
                esc(ar.get("adj", "")), esc(ar.get("emo", "")), esc(ar.get("logic", "")))
        rows_html = ('<table class="lg-tbl"><tr><th>基金</th><th>最终指令</th><th>价位参考</th>'
                     '<th>仓位调整</th><th>情绪校准</th><th>逻辑</th></tr>%s</table>') % r
    body = (block("尾盘买入（需同时满足）", "tail_buy", "lg-buy")
            + block("尾盘卖出（满足任一）", "tail_sell", "lg-sell")
            + block("尾盘不加仓（禁止买入）", "tail_noadd", "lg-noadd")
            + block("情绪面校准规则", "emotion", "lg-emo")
            + rows_html)
    if not body:
        return ""
    return f'''
<details id="logic" class="card">
  <summary>🤖 操作决策逻辑引擎 <span class="badge">默认折叠</span></summary>
  {body}
</details>'''

def render_sources(src, disclaimer):
    """P2 数据源与免责（默认折叠）。"""
    if not src and not disclaimer:
        return ""
    items = ""
    for it in (src or {}).get("items", []):
        items += '<div class="kv"><span>%s</span><span class="src-note">%s</span></div>' % (
            tip(it.get("item", "")), tip(it.get("note", "")))
    disc = ('<div class="note warn">%s</div>' % tip(disclaimer)) if disclaimer else ""
    return f'''
<details id="src" class="card">
  <summary>📎 数据来源与免责 <span class="badge">默认折叠</span></summary>
  <div class="src-box">{items}</div>
  {disc}
</details>'''

# ---------- 策略配置（止盈锁本 / 调仓 / 尾盘窗口）从 watchlist.json 读取 ----------
def load_wl():
    """读取持仓策略配置（止盈线/调仓框架/尾盘窗口为静态策略，以 watchlist.json 为准）。"""
    p = os.path.normpath(os.path.join(BASE, "..", "config", "watchlist.json"))
    if not os.path.exists(p):
        return None
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return None

def render_tail_window(wl, data):
    """尾盘时间窗口与监控框架 + 今日场景高亮（今日场景来自 tail JSON instruction.tail_scenario）。"""
    if not wl:
        return ""
    tw = wl.get("tail_window")
    if not tw:
        return ""
    today_sc = ((data or {}).get("instruction") or {}).get("tail_scenario")
    phases = [
        ("① 实时监控期", tw.get("monitor_phase", "")),
        ("② 决策执行期", tw.get("decision_phase", "")),
        ("③ 截止铁律", tw.get("cutoff", "")),
    ]
    ph = ""
    for t, d in phases:
        ph += '<div class="tw-phase"><b>%s</b><span>%s</span></div>' % (esc(t), tip(d))
    mon = tw.get("monitoring") or {}
    mon_html = ""
    for k, v in mon.items():
        items = " / ".join(esc(x) for x in v)
        mon_html += '<div class="tw-mon"><b>%s：</b>%s</div>' % (esc(k), items)
    scs = tw.get("scenarios") or []
    sc_html = ""
    for s in scs:
        name = s.get("name", "")
        is_on = bool(today_sc) and (name in today_sc or today_sc in name)
        cls = " tw-sc-on" if is_on else ""
        sc_html += ('<div class="tw-sc%s"><div class="tw-sc-name">%s</div>'
                    '<div class="tw-sc-cond">判定：%s</div>'
                    '<div class="tw-sc-act">动作：%s</div></div>') % (
            cls, esc(name), esc(s.get("cond", "")), tip(s.get("action", "")))
    today_html = ('<div class="tw-today">🎯 今日尾盘场景：<b>%s</b></div>' % esc(today_sc)) if today_sc else ""
    return f'''
<section id="twin" class="card">
  <h2>🕒 尾盘时间窗口与监控框架 <span class="badge">14:30监控→14:55决策→截止</span></h2>
  {today_html}
  <div class="tw-phases">{ph}</div>
  <div class="tw-mon-box">{mon_html}</div>
  <div class="tw-sc-title">尾盘场景分类（命中今日高亮）</div>
  <div class="tw-scs">{sc_html}</div>
</section>'''

def _pl_entry(k, v):
    if isinstance(v, dict):
        trig = v.get("trigger_pct", v.get("from_peak_pct", "—"))
        act = v.get("action", "—")
        return "<b>%s</b>：%s → %s" % (esc(k), esc(trig), esc(act))
    return "<b>%s</b>：%s" % (esc(k), esc(v))

def render_profit_lock(wl):
    """阶梯止盈锁本参数表：逐持仓展开上涨触发阶梯 + 回撤保护 + 本金安全线。"""
    if not wl:
        return ""
    hs = wl.get("holdings") or []
    rows = ""
    for h in hs:
        pl = h.get("profit_lock")
        if not pl:
            continue
        name = tip(h.get("name", ""))
        typ = esc(pl.get("type", "—"))
        parts = []
        for k, v in pl.items():
            if k == "type":
                continue
            parts.append(_pl_entry(k, v))
        body = "".join('<li>%s</li>' % p for p in parts) or "<li>—</li>"
        rows += ('<div class="pl-row"><div class="pl-name">%s</div>'
                  '<div class="pl-type">%s</div><ul class="pl-list">%s</ul></div>') % (name, typ, body)
    if not rows:
        return ""
    rules = wl.get("profit_lock_rules") or {}
    rule_html = ""
    if rules:
        r = ""
        for typ, rv in rules.items():
            if isinstance(rv, dict):
                lines = " · ".join("%s：%s" % (esc(kk), esc(vv)) for kk, vv in rv.items())
                r += "<div><b>%s</b>：%s</div>" % (esc(typ), lines)
            else:
                r += "<div><b>%s</b>：%s</div>" % (esc(typ), esc(rv))
        rule_html = ('<details class="pl-rules"><summary>📋 阶梯止盈通用规则（点击展开）</summary>%s</details>') % r
    return f'''
<section id="pl" class="card">
  <h2>🔒 阶梯止盈锁本参数表 <span class="badge">按持仓 · 分批收回本金</span></h2>
  <div class="pl-rows">{rows}</div>
  {rule_html}
</section>'''

def render_rebalance(wl):
    """调仓清单：资金源 + 分配比例 + 触发条件 + 优先级 + 节奏。"""
    if not wl:
        return ""
    rb = wl.get("rebalance_plan")
    if not rb:
        return ""
    src = " / ".join(esc(s) for s in (rb.get("sources") or []))
    alloc = rb.get("allocation") or []
    bars = ""
    for a in alloc:
        pct = num(a.get("pct_of_proceeds")) or 0
        bars += ('<div class="rb-bar"><div class="rb-name">%s <span class="rb-pct">%s%%</span></div>'
                  '<div class="rb-track"><div class="rb-fill" style="width:%.0f%%"></div></div>'
                  '<div class="rb-target">%s · <span class="rb-role">%s</span></div></div>') % (
            esc(a.get("direction", "")), pct, pct, esc(a.get("target", "")), esc(a.get("role", "")))
    trigs = " / ".join(esc(t) for t in (rb.get("triggers") or []))
    pr = "".join('<li>%s</li>' % esc(x) for x in (rb.get("priority_reduce") or []))
    pa = "".join('<li>%s</li>' % esc(x) for x in (rb.get("priority_add") or []))
    pace = esc(rb.get("pace", ""))
    return f'''
<section id="rb" class="card">
  <h2>🔄 调仓清单 <span class="badge">资金源 · 分配 · 触发 · 节奏</span></h2>
  <div class="rb-src">💰 资金来源：{src or '—'}</div>
  <div class="rb-bars">{bars}</div>
  <div class="rb-trig">⚡ 调仓触发条件：{trigs or '—'}</div>
  <div class="rb-prio">
    <div class="rb-prio-col"><b class="down">优先减</b><ul>{pr or '<li>—</li>'}</ul></div>
    <div class="rb-prio-col"><b class="up">优先加</b><ul>{pa or '<li>—</li>'}</ul></div>
  </div>
  <div class="rb-pace">🐢 执行节奏：{pace or '—'}</div>
</section>'''

def render_plan_html(wl, date):
    """独立交付物：调仓止盈计划（止盈线表 + 调仓清单 + 尾盘窗口），深色统一板。"""
    body = (render_tail_window(wl, {"instruction": {}}) +
            render_profit_lock(wl) +
            render_rebalance(wl))
    intro = ('<section class="card"><div class="note">本计划由 watchlist.json 策略配置驱动，含每只基金阶梯止盈线、回撤保护、'
              '本金安全线，以及「防御对冲40% / 低位轮动35% / 机动现金25%」三元调仓框架。'
              '上方尾盘窗口卡的场景定义供日常尾盘决策报告填充当日实际场景。</div></section>')
    head = (HEAD.replace("__DATE__", esc(date))
             .replace("__UPD__", esc(date + " 策略快照"))
             .replace("__TIER__", "策略")
             .replace("<title>尾盘决策 __DATE__</title>", "<title>调仓止盈计划 __DATE__</title>")
             .replace('<h1>🎯 尾盘决策</h1>',
                      '<h1>🔒 调仓止盈计划</h1>')
             .replace('<div class="sub">数据截止 __DATE__ 尾盘 · 更新 __UPD__ · 数据源 __TIER__（neodata/westock）· 收盘前操作预案 · 仅供参考不构成投资建议</div>',
                      '<div class="sub">基于当前持仓策略配置 · 生成 __DATE__ · 阶梯止盈锁本 + 三元调仓框架 · 仅供参考不构成投资建议</div>'))
    return head + intro + body + SCRIPT.replace("__DATA__", "{}")

# ============================================================
# v2 新渲染函数：3秒决策 + 10秒执行 + 次日预案
# ============================================================

def render_mandatory_ops(data):
    """方向2: 操作三级分类 - 必执行/条件触发/持有不动"""
    inst = data.get("instruction") or {}
    pos = data.get("position") or {}
    holdings = (pos.get("holdings") or [])
    
    mandatory = []   # 必执行
    conditional = [] # 条件触发
    hold = []        # 持有不动
    
    for h in holdings:
        instr = (h.get("instruction") or "").upper()
        name = h.get("name", "")
        wp = num(h.get("weight_pct"))
        if "减仓" in instr or "SELL" in instr or "卖出" in instr:
            mandatory.append((name, instr, wp))
        elif "观察" in instr or "WATCH" in instr or "盯盘" in instr:
            conditional.append((name, instr, wp))
        else:
            hold.append((name, instr, wp))
    
    # 隐藏仓位<5%的次要标的（方向1.3）
    hold_core = [h for h in hold if (h[2] or 0) >= 5]
    hold_minor = [h for h in hold if (h[2] or 0) < 5]
    
    def _list(items):
        return "".join(f'<li><b>{esc(n)}</b> ({w:.1f}%) — {esc(i)}</li>' for n, i, w in items if w is not None)
    
    minor_html = ""
    if hold_minor:
        names = "、".join(esc(n) for n, _, w in hold_minor if w is not None)
        minor_html = f'<details style="margin-top:4px"><summary style="font-size:12px;color:var(--mut)">仓位≤5%观察仓({len(hold_minor)}只): {names}</summary></details>'
    
    return f'''
<section id="ops" class="card">
  <h3 style="margin:0 0 8px 0">操作指令（三级分类）</h3>
  {"<div style='border-left:3px solid var(--up);padding:6px 12px;margin-bottom:8px;background:rgba(245,86,77,.08)'><div style='font-weight:700;color:var(--up);font-size:13px'>🔴 必执行操作</div><ol style='margin:4px 0 0 0;padding-left:18px'>" + _list(mandatory) + "</ol></div>" if mandatory else ""}
  {"<div style='border-left:3px solid var(--neu);padding:6px 12px;margin-bottom:8px;background:rgba(217,164,65,.08)'><div style='font-weight:700;color:var(--neu);font-size:13px'>🟡 条件触发操作</div><ol style='margin:4px 0 0 0;padding-left:18px'>" + _list(conditional) + "</ol></div>" if conditional else ""}
  {"<div style='border-left:3px solid var(--down);padding:6px 12px;background:rgba(38,194,129,.08)'><div style='font-weight:700;color:var(--down);font-size:13px'>🟢 持有不动</div><ol style='margin:4px 0 0 0;padding-left:18px'>" + _list(hold_core) + "</ol>" + minor_html + "</div>" if hold_core else ""}
</section>'''

def render_logic_rules(data):
    """方向2.4: 操作底层决策逻辑 — 预设规则 + 博主实战分析体系"""
    inst = data.get("instruction") or {}
    risk = data.get("risk") or {}
    sector = data.get("sector") or {}
    sent = data.get("sentiment") or {}
    pos = data.get("position") or {}
    rr = inst.get("risk_rules", [])
    
    # ── 原有4条风控规则 ──
    rules = [
        ("硬止损纪律", "单基累计亏损达-8%强制减仓50%，避免极端行情亏损失控，保留操作本金"),
        ("集中度风控", "半导体赛道跌幅超3%触发集群减仓，降低赛道波动对账户净值的冲击"),
        ("锁本保护机制", "已提前赎回部分仓位收回本金，剩余仓位为利润安全垫，回撤在阈值内不操作"),
        ("分散对冲原则", "创新药、债券、纳指与科技赛道低相关，保留作为对冲底仓，平滑整体波动"),
    ]
    
    hard = risk.get("hard_stop") or {}
    triggered = []
    for item in (hard.get("items") or []):
        cur = num(item.get("cur_loss_pct"))
        sl = num(item.get("stop_loss_pct"))
        if cur is not None and sl is not None and cur <= sl:
            triggered.append(f"⚠ {item.get('name','')}已触发-8%硬止损")
    
    rows = ""
    for title, desc in rules:
        flag = ""
        if triggered and title == "硬止损纪律":
            flag = '<span style="color:var(--up);font-weight:700;margin-left:8px">🔴 ' + " · ".join(esc(t) for t in triggered) + '</span>'
        rows += f'<tr><td style="width:120px;font-weight:600;vertical-align:top;padding:4px 8px 4px 0">{title}</td><td style="padding:4px 0">{desc}{flag}</td></tr>'
    
    for r in rr:
        rows += f'<tr><td style="width:120px;font-weight:600;vertical-align:top;padding:4px 8px 4px 0;color:var(--up)">⚠ 铁律</td><td style="padding:4px 0;color:var(--up)">{esc(r)}</td></tr>'
    
    # ── 博主实战分析体系（基于当日数据自动判定） ──
    bars = sector.get("bars") or []
    mb = sector.get("market_breadth") or {}
    sent_note = sent.get("note", "")
    fg = num(sent.get("fear_greed_index"))
    holdings = (pos.get("holdings") or [])
    
    blogger_items = []
    
    # 1. 量能定性（量能第一性原理§1.1）— 从 market_breadth 和 emotional note 推断
    breadth_note = mb.get("note", "")
    # 成交量可参考 breadth_note 中的描述（无精确数字则用文本定性）
    has_tianliang = "天量" in breadth_note or "万亿" in breadth_note
    has_suoliang = "缩量" in breadth_note or "地量" in breadth_note
    
    if has_tianliang:
        blogger_items.append(("量能定性", "量能维持高位，资金未离场（§1.1量能第一性原理），调整=结构性轮动，非系统性风险。"))
    elif has_suoliang:
        blogger_items.append(("量能定性", "量能持续萎缩，需警惕资金系统性离场风险（§1.1）。"))
    else:
        # 从 breadth_note 提取定性信息
        blogger_items.append(("量能定性", f"市场广度：{esc(breadth_note[:80])}"))
    
    # 2. 盘面定性（盘面标准化四步法§2.1 + 两类下跌§2.2）
    up_stocks = num(mb.get("total_up"))
    down_stocks = num(mb.get("total_down"))
    if up_stocks is not None and down_stocks is not None:
        total = up_stocks + down_stocks
        ratio = up_stocks / total if total > 0 else 0.5
        if ratio > 0.6:
            breadth_note_quant = f"涨{up_stocks:.0f}家 vs 跌{down_stocks:.0f}家，多数上涨"
            scene_type = "结构性上涨"
        elif ratio < 0.4:
            breadth_note_quant = f"涨{up_stocks:.0f}家 vs 跌{down_stocks:.0f}家，多数下跌"
            scene_type = "结构性轮动下跌" if has_tianliang else "系统性风险下跌"
        else:
            breadth_note_quant = f"涨{up_stocks:.0f}家 vs 跌{down_stocks:.0f}家，涨跌互现"
            scene_type = "正常分化"
        scene_action = "调结构不杀跌（§2.2）" if "结构性" in scene_type else "按规则执行"
        blogger_items.append(("盘面定性", f"{breadth_note_quant}\n归因：{scene_type} → {scene_action}"))
    else:
        # 有文本描述就用文本
        if breadth_note:
            blogger_items.append(("盘面定性", esc(breadth_note[:100])))
    # 3. 赛道三层归因（§3.1 外围→交易→逻辑证伪）
    # 外围冲击层
    outer_kw = ["原油", "美股", "美元", "外围", "地缘", "冲突", "通胀", "加息", "纳指", "KOSPI", "熔断", "存储"]
    has_outer = any(kw in sent_note for kw in outer_kw)
    outer_detail = ""
    if has_outer:
        outer_detail = "外围事件触发短期情绪冲击。\n性质：不改变产业内部逻辑（§3.1外围冲击层）。" if "熔断" in sent_note or "暴跌" in sent_note else "外围有扰动，但非主导因素。"
    
    # 交易兑现层
    has_trade = "兑现" in sent_note or "还债" in sent_note or "获利" in sent_note or "抽血" in sent_note or "切换" in sent_note
    trade_detail = ""
    if has_trade:
        trade_detail = '短期涨幅过大→获利盘集中出逃。\n性质：技术性回调即「还债」，正常交易行为（§3.1交易兑现层）。'
    
    # 逻辑证伪层
    has_falsify = "证伪" in sent_note or "不及预期" in sent_note or "逻辑破坏" in sent_note or "基本面恶化" in sent_note
    
    # 综合归因输出
    attribution_lines = []
    if has_outer:
        attribution_lines.append(f"🌐 外围冲击：{outer_detail}")
    if has_trade:
        attribution_lines.append(f"💹 交易兑现：{trade_detail}")
    if has_falsify:
        attribution_lines.append(f"❌ 逻辑证伪：产业逻辑受损，需果断离场（§3.1逻辑证伪层）")
    else:
        attribution_lines.append(f"✅ 逻辑验证：产业核心逻辑未破，调整=技术性（§1.3分离原则）")
    if not has_outer and not has_trade:
        attribution_lines = ["✅ 三层归因：外围无冲击+交易未兑现+产业逻辑未破，当前波动属正常市场行为（§3.1）"]
    
    for line in attribution_lines:
        blogger_items.append(("赛道归因", line))
    
    # 4. 标的分层操作（§4.1）— 根据 instruction 自动归类
    for h in holdings:
        name = h.get("name", "")
        wp = num(h.get("weight_pct"))
        instr = h.get("instruction", "")
        logic_txt = h.get("logic", "")
        if wp is None:
            continue
        
        logic_trim = logic_txt[:60] if "减仓" in instr or "止损" in instr or "持有" in instr else ""
        
        if "止损" in instr or "赎回" in instr:
            blogger_items.append((f"标的分层·{name[:8]}", f"触发止损指令\n属性：核心业绩仓（仓位{wp:.1f}%）\n规则：硬止损触发→强制减仓，保留操作本金（§4.1核心业绩仓规则：急跌不盲目杀跌，但-8%硬止损必须执行）"))
        elif "减仓" in instr:
            blogger_items.append((f"标的分层·{name[:8]}", f"集中度减仓指令\n属性：核心业绩仓（仓位{wp:.1f}%）\n规则：赛道跌幅>3%触发集群减仓（§4.1核心业绩仓），但仍保留部分仓位等企稳"))
        elif "持有不动" in instr or "不做操作" in instr or "保留" in instr:
            layer = "核心业绩仓" if wp >= 10 else ("防御底仓" if "债券" in name or "纳斯达克" in name else "迷你观察仓")
            rule = "(§4.1)" if wp >= 10 else "破位清仓不恋战"
            blogger_items.append((f"标的分层·{name[:8]}", f"{layer}（仓位{wp:.1f}%）\n{logic_trim or '持有观察'}\n规则：{rule}"))
        elif "清仓" in instr:
            blogger_items.append((f"标的分层·{name[:8]}", f"迷你观察仓（仓位{wp:.1f}%）\n{logic_trim}\n规则：破位立刻清仓，亏损可控（§4.1迷你观察仓）"))
    
    # 渲染博主分析板块
    blogger_html = ""
    for tag, text in blogger_items[:12]:  # 最多12条
        blogger_html += f'<tr><td style="width:120px;font-weight:600;vertical-align:top;padding:4px 8px 4px 0;font-size:12px;color:var(--acc)">{esc(tag)}</td><td style="padding:4px 0;font-size:12px;white-space:pre-line">{esc(text)}</td></tr>'
    
    return f'''
<section id="logic" class="card">
  <h3>操作底层决策逻辑</h3>
  <p style="font-size:12px;color:var(--mut);margin:0 0 8px 0">所有操作基于预设规则自动触发，非主观判断</p>
  <table style="width:100%;border-collapse:collapse;font-size:13px">
    {rows}
  </table>
  {f'''
  <details style="margin-top:8px">
    <summary style="font-size:13px;font-weight:600;cursor:pointer;color:var(--acc)">📖 博主实战分析体系（当日盘面自动判定）</summary>
    <p style="font-size:11px;color:var(--mut);margin:4px 0 8px 0">基于「量能为锚、业绩分层、轮动识别、纪律优先」框架（data/blogger-protocol.md）</p>
    <table style="width:100%;border-collapse:collapse;font-size:13px">{blogger_html}</table>
  </details>''' if blogger_html else ""}
</section>'''


def render_decision_header(instr):
    """首屏决策核心区 — 3栏卡片：今日场景 / 唯一主动操作 / 风控红线"""
    if not instr:
        return ""
    scene = instr.get("tail_scenario") or "—"
    scene_detail = instr.get("scene_detail") or ""
    active = instr.get("active_action") or "（无主动操作）"
    active_detail = instr.get("active_detail") or ""
    risks = instr.get("risk_rules") or []
    risk_items = "".join('<li>🚫 %s</li>' % esc(r) for r in risks[:3])
    scene_cls = "green" if "偏多" in scene else ("red" if "减仓" in active or "跳水" in scene else "orange")
    return f'''
<section id="dechead" class="decision-header">
  <div class="panel-box de-scene">
    <div class="de-label">今日场景</div>
    <div class="de-scene-tag {scene_cls}">{tip(scene)}</div>
    <div class="de-detail">{tip(scene_detail)}</div>
  </div>
  <div class="panel-box de-action">
    <div class="de-label">唯一主动操作</div>
    <div class="de-action-main">{tip(active)}</div>
    <div class="de-detail">{tip(active_detail)}</div>
  </div>
  <div class="panel-box de-risk">
    <div class="de-label">核心风控红线</div>
    <ul>{risk_items}</ul>
  </div>
</section>'''

def render_index_scroll(kpis):
    """核心指数速览 — 横向滚动标签"""
    if not kpis:
        return ""
    items = ""
    for k in kpis:
        name = esc(k.get("label", ""))
        val = esc(k.get("value", ""))
        cls = k.get("cls", "neu")
        items += '<div class="ix-item"><div class="ix-name">%s</div><div class="ix-val %s">%s</div></div>' % (name, cls, val)
    return f'''
<section id="indices" class="card">
  <div class="ix-head"><h2>📈 核心指数速览</h2><span class="badge">尾盘收盘前 10 秒定操作</span></div>
  <div class="ix-scroll">{items}</div>
</section>'''

def render_holdings_table(hs):
    """持仓操作总表 — 极简 4 列，点击展开详情"""
    if not hs:
        return ""
    rows = ""
    hs_sorted = sorted(hs, key=lambda h: -(num(h.get("weight_pct")) or 0))
    idx = 0
    for h in hs_sorted:
        name = tip(h.get("name", ""))
        w = num(h.get("weight_pct"))
        w_html = ("%.2f%%" % w) if w is not None else "—"
        ret = num(h.get("hold_return_pct"))
        ret_cls = pcls(ret) if ret is not None else "neu"
        ret_html = ("%+.2f%%" % ret) if ret is not None else "—"
        instr = h.get("instruction") or "HOLD"
        ocls = op_cls(instr)
        ow = h.get("overweight")
        detail = h.get("logic") or ""
        if w and w >= 2.0:
            # 主基金：点击行展开详情
            # 收集详情数据
            ts = h.get("tech_score") or {}
            comp = ts.get("composite")
            tlevel = ts.get("level") or "—"
            comp_html = ("%s <span class='%s'>%s</span>" % (esc(comp), tech_cls(tlevel), esc(tlevel))) if comp else "—"
            mf = h.get("main_force") or {}
            mf_q = mf.get("qualitative") or "—"
            mf_qcls = mf_cls(mf_q)
            mf_net = mf.get("net_inflow")
            mf_net_html = ("%s亿" % esc(mf_net)) if mf_net is not None else "—"
            stop = num(h.get("stop_loss_pct"))
            buf_html = "—"
            if ret is not None and stop is not None:
                buf = ret - stop
                buf_html = "距 -8%% 还有 <b>%.2f%%</b>" % buf
                if buf < 3:
                    buf_html = '<span style="color:var(--neu);font-weight:700">⚠ 距止损仅 <b>%.2f%%</b></span>' % buf
            logic = tip(detail)
            rows += ('<tr class="ht-main" onclick="toggleHtDetail(%d)" data-idx="%d">'
                     '<td class="ht-name">%s</td>'
                     '<td class="ht-w%s">%s</td>'
                     '<td class="ht-ret %s">%s</td>'
                     '<td><span class="op-tag %s">%s</span><span class="ht-expand">▼</span></td></tr>'
                     '<tr class="ht-detail" id="htd_%d" style="display:none">'
                     '<td colspan="4"><div class="htd-grid">'
                     '<div class="htd-col"><div class="htd-h">五维评分</div><div class="htd-v">%s</div></div>'
                     '<div class="htd-col"><div class="htd-h">主力研判</div><div class="htd-v">%s · %s</div></div>'
                     '<div class="htd-col"><div class="htd-h">距止损</div><div class="htd-v">%s</div></div>'
                     '</div><div class="htd-logic">%s</div></td></tr>') % (
                idx, idx, name, (" ow" if ow else ""), w_html, ret_cls, ret_html,
                ocls, tip(instr), idx,
                comp_html, esc(mf_q), mf_net_html, buf_html, logic)
            idx += 1
        else:
            rows += '<tr class="ht-minor"><td colspan="4" class="ht-minor-td">%s · %.2f%% · %s</td></tr>' % (name, w, instr)
    return f'''
<section id="holdings" class="card">
  <h2>📋 今日持仓操作指令 <span class="badge">点击展开详情</span></h2>
  <table class="ht">
    <thead><tr><th>基金名称</th><th>仓位</th><th>持有收益</th><th>今日指令</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</section>'''


# ---------- 静态 HEAD（深色配色板，与早报/午报/晚报/大盘研判统一） ----------
HEAD = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>尾盘决策 __DATE__</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
<style>
:root{--up:#f5564d;--down:#26c281;--neu:#d9a441;--acc:#4aa8ff;--bg:#0e1117;--bg2:#161b24;--card:#1c232e;--line:#2a3340;--tx:#e6edf3;--mut:#8b98a9}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--tx);font:14px/1.6 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif;padding:12px;max-width:1080px;margin:0 auto}
.up{color:var(--up)} .down{color:var(--down)} .neu{color:var(--neu)} .acc{color:var(--acc)} .mut{color:var(--mut)}
.b{font-weight:700}
h1{font-size:19px;margin-bottom:2px} .sub{color:var(--mut);font-size:12px;margin-bottom:10px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px;margin:12px 0;box-shadow:0 1px 2px rgba(0,0,0,.25)}
.card h2{font-size:16px;margin-bottom:10px;display:flex;align-items:center;gap:6px;border-bottom:1px solid var(--line);padding-bottom:8px}
.badge{font-size:11px;padding:1px 7px;border-radius:6px;background:var(--bg2);color:var(--mut);border:1px solid var(--line);font-weight:400}
.legend{color:var(--mut);font-size:11px;margin-top:8px;line-height:1.6;border-top:1px dashed var(--line);padding-top:8px}
.note{color:var(--mut);font-size:11.5px;margin-top:8px;line-height:1.5}
.note.warn{background:rgba(217,164,65,.10);border:1px solid rgba(217,164,65,.3);border-radius:8px;padding:8px 10px;color:#d9a441}
/* 尾盘窗口 */
.tw-today{font-size:13px;background:rgba(74,168,255,.1);border:1px solid rgba(74,168,255,.35);border-radius:8px;padding:7px 10px;margin-bottom:8px}
.tw-phases{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0}
.tw-phase{flex:1;min-width:200px;background:var(--bg2);border:1px solid var(--line);border-radius:9px;padding:8px 10px}
.tw-phase b{display:block;color:var(--acc);font-size:12px;margin-bottom:3px}
.tw-phase span{font-size:11.5px;color:var(--mut);line-height:1.5}
.tw-mon-box{display:flex;flex-direction:column;gap:3px;margin:6px 0;font-size:12px}
.tw-mon b{color:var(--tx)}
.tw-sc-title{font-size:12px;color:var(--mut);margin:8px 0 5px}
.tw-scs{display:flex;gap:8px;flex-wrap:wrap}
.tw-sc{flex:1;min-width:200px;background:var(--bg2);border:1px solid var(--line);border-radius:9px;padding:8px 10px}
.tw-sc-on{border-color:var(--acc);background:rgba(74,168,255,.1);box-shadow:0 0 0 1px var(--acc)}
.tw-sc-name{font-weight:800;font-size:13px;margin-bottom:3px}
.tw-sc-cond,.tw-sc-act{font-size:11px;color:var(--mut);line-height:1.5;margin:2px 0}
.tw-sc-act{color:#aab4c0}
/* 止盈锁本 */
.pl-rows{display:flex;flex-direction:column;gap:8px}
.pl-row{background:var(--bg2);border:1px solid var(--line);border-radius:9px;padding:9px 11px}
.pl-name{font-weight:800;font-size:13px}
.pl-type{font-size:11px;color:var(--neu);margin:2px 0 5px}
.pl-list{margin:0;padding-left:16px;font-size:11.5px;line-height:1.6}
.pl-list b{color:var(--acc)}
.pl-list li{margin:2px 0}
.pl-rules{margin-top:8px;font-size:11.5px}
.pl-rules summary{cursor:pointer;color:var(--mut)}
.pl-rules>div{margin:3px 0;line-height:1.5}
/* 调仓 */
.rb-src{font-size:12.5px;margin-bottom:8px;color:#aab4c0}
.rb-bars{display:flex;flex-direction:column;gap:7px}
.rb-bar{background:var(--bg2);border:1px solid var(--line);border-radius:9px;padding:8px 10px}
.rb-name{font-size:12.5px;font-weight:700}
.rb-pct{color:var(--acc);font-weight:800;margin-left:4px}
.rb-track{height:8px;background:rgba(0,0,0,.3);border-radius:5px;overflow:hidden;margin:5px 0}
.rb-fill{height:100%;background:linear-gradient(90deg,var(--acc),#6ab0ff);border-radius:5px}
.rb-target{font-size:11px;color:var(--mut)}
.rb-role{color:#aab4c0}
.rb-trig{font-size:12px;margin:8px 0;color:#aab4c0}
.rb-prio{display:flex;gap:12px;margin:6px 0}
.rb-prio-col{flex:1;font-size:11.5px}
.rb-prio-col ul{margin:4px 0;padding-left:16px;line-height:1.5}
.rb-pace{font-size:12px;color:var(--neu);background:rgba(217,164,65,.08);border-radius:8px;padding:7px 10px;margin-top:6px}
/* 悬浮指令条 */
.cmdbar{position:sticky;top:0;z-index:40;background:linear-gradient(135deg,#141d28,#0e141d);border:1px solid #2b4a6a;border-radius:12px;padding:10px 12px;margin-bottom:12px;box-shadow:0 4px 18px rgba(0,0,0,.5)}
.cmdbar.core-sell{border-color:#6a2b2b}
.cmdbar.core-watch{border-color:#6a5a2b}
.cmd-main{display:flex;gap:14px;flex-wrap:wrap;align-items:center}
.cmd-core{font-size:15px;font-weight:800;display:flex;align-items:center;gap:6px;color:var(--down)}
.cmdbar.core-sell .cmd-core{color:var(--up)} .cmdbar.core-watch .cmd-core{color:var(--neu)}
.cmd-core .dot{width:9px;height:9px;border-radius:50%;background:currentColor;box-shadow:0 0 8px currentColor}
.cmd-active{font-size:13px;font-weight:700;color:#0e1117;background:linear-gradient(135deg,#f5b942,#e09a2e);padding:3px 10px;border-radius:8px}
.cmd-risk{font-size:13px;font-weight:700;color:var(--up)}
.cmd-meta{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:8px;border-top:1px dashed var(--line);padding-top:7px}
.cmd-meta .ts{font-size:11px;color:var(--mut)}
.cmd-nav{margin-left:auto;display:flex;gap:4px;flex-wrap:wrap}
.cmd-nav a{color:var(--mut);text-decoration:none;padding:2px 7px;border-radius:6px;font-size:11.5px}
.cmd-nav a:hover{background:var(--bg2);color:var(--tx)}
.cmd-nav .nav-sep{color:var(--mut);padding:2px 2px}
.cmd-disc{margin-top:7px;font-size:11px;color:var(--mut);background:rgba(74,168,255,.06);border-left:3px solid var(--acc);border-radius:6px;padding:5px 9px}
/* 核心速览 4 大字卡 */
.kpi-row{display:flex;gap:10px;flex-wrap:wrap}
.kpi{flex:1;min-width:160px;background:var(--bg2);border:1px solid var(--line);border-radius:10px;padding:12px;text-align:center}
.kpi-l{font-size:12px;color:var(--mut);margin-bottom:4px}
.kpi-tag{font-size:10px;background:rgba(245,86,77,.18);color:var(--up);border-radius:5px;padding:0 5px;margin-left:4px;font-weight:700}
.kpi-v{font-size:23px;font-weight:800}
.kpi-sub{font-size:10.5px;color:var(--mut);margin-top:3px}
/* 持仓卡片 */
.hcards{display:flex;flex-direction:column;gap:10px}
.hcard{background:var(--bg2);border:1px solid var(--line);border-radius:11px;overflow:hidden}
.hcard[open]{box-shadow:0 2px 10px rgba(0,0,0,.3)}
.hsum{list-style:none;cursor:pointer;display:flex;gap:10px;align-items:center;padding:11px 13px;flex-wrap:wrap}
.hsum::-webkit-details-marker{display:none}
.hname{font-weight:800;font-size:14px}
.hsector{font-size:11px;color:var(--mut)}
.hweight{font-size:12.5px;color:var(--acc);font-weight:700;margin-left:auto}
.hret{font-size:13px;font-weight:700}
.op-tag{font-size:11px;padding:2px 9px;border-radius:7px;font-weight:800}
.op-tag.op-hold{background:rgba(38,194,129,.16);color:#26c281}
.op-tag.op-sell{background:rgba(245,86,77,.16);color:#f5564d}
.op-tag.op-watch{background:rgba(217,164,65,.18);color:#d9a441}
.ow-badge{font-size:10px;font-weight:800;background:rgba(245,86,77,.22);color:#f5564d;border-radius:5px;padding:1px 6px}
.hbody{display:flex;gap:12px;padding:12px 13px;border-top:1px solid var(--line);align-items:stretch}
.hkline{flex:0 0 33%;min-width:200px}
.hkline canvas{width:100%;height:190px;background:rgba(0,0,0,.18);border-radius:8px}
.kline-text{width:100%;min-height:170px;display:flex;align-items:center;justify-content:center;text-align:center;color:var(--mut);font-size:12px;background:rgba(0,0,0,.18);border-radius:8px;padding:10px}
.hright{flex:1;display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;min-width:0}
.hcol{background:var(--card);border:1px solid var(--line);border-radius:9px;padding:9px 10px}
.hcol-h{font-size:12px;font-weight:700;color:var(--acc);margin-bottom:6px;border-bottom:1px solid var(--line);padding-bottom:4px}
.kv{display:flex;justify-content:space-between;gap:8px;font-size:11.5px;padding:3px 0;border-bottom:1px dashed rgba(42,51,64,.6)}
.kv:last-child{border-bottom:none}
.hcol-note{font-size:11px;color:#aab4c0;margin-top:6px;line-height:1.5}
.hcol-note.warn{color:var(--neu)}
.mf{font-weight:700}.mf-up{color:var(--down)}.mf-down{color:var(--up)}.mf-neu{color:var(--mut)}
.tech-comp{display:flex;align-items:baseline;gap:8px;margin-bottom:4px}
.tech-comp span:first-child{font-size:26px;font-weight:800}
.tech-lvl{font-size:12px;font-weight:700}
.op-big{font-size:18px;font-weight:800;text-align:center;padding:4px 0;border-radius:7px;margin-bottom:6px}
.op-big.op-hold{background:rgba(38,194,129,.14);color:#26c281}
.op-big.op-sell{background:rgba(245,86,77,.14);color:#f5564d}
.op-big.op-watch{background:rgba(217,164,65,.14);color:#d9a441}
.buf-warn{color:var(--neu);font-weight:700}
/* 板块条形图 */
.sbars{display:flex;flex-direction:column;gap:7px}
.sbar-row{display:flex;align-items:center;gap:10px;padding:6px 8px;border-radius:8px;background:var(--bg2);border:1px solid transparent}
.sbar-row.linked{border-color:rgba(38,194,129,.5);background:rgba(38,194,129,.06)}
.sbar-name{flex:0 0 170px;font-size:12.5px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.sbar-tag{font-size:9.5px;background:rgba(245,86,77,.18);color:var(--up);border-radius:4px;padding:0 4px;margin-left:4px}
.sbar-track{flex:1;background:rgba(0,0,0,.3);border-radius:6px;height:16px;position:relative;overflow:hidden}
.sbar-fill{height:100%;border-radius:6px}
.sbar-fill.up{background:linear-gradient(90deg,rgba(38,194,129,.5),#26c281)}
.sbar-fill.down{background:linear-gradient(90deg,rgba(245,86,77,.5),#f5564d)}
.sbar-fill.neu{background:linear-gradient(90deg,rgba(217,164,65,.5),#d9a441)}
.sbar-score{position:absolute;right:6px;top:0;line-height:16px;font-size:10.5px;font-weight:700;color:#fff;text-shadow:0 1px 2px #000}
.sbar-ten{flex:0 0 48px;font-size:12px;font-weight:700;text-align:center}
.sbar-flow{flex:0 0 86px;font-size:12px;text-align:right;font-weight:600}
.sbar-extra{margin-top:8px;font-size:12px;line-height:1.6;background:rgba(0,0,0,.18);border-radius:8px;padding:8px 10px}
.sbar-extra div{margin:3px 0}
/* 硬止损 */
.stops{display:flex;flex-direction:column;gap:8px}
.stop-row{display:flex;align-items:center;gap:10px}
.stop-name{flex:0 0 150px;font-size:12.5px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.stop-track{flex:1;background:rgba(0,0,0,.3);border-radius:6px;height:18px;overflow:hidden}
.stop-fill{height:100%;background:linear-gradient(90deg,#7a2b2b,#f5564d);border-radius:6px}
.stop-fill.warn{background:linear-gradient(90deg,#a85a1a,#f5b942)}
.stop-pct{flex:0 0 64px;text-align:right;font-size:12.5px;font-weight:700}
.stop-warn{font-size:10px;font-weight:800;background:rgba(245,185,66,.22);color:#f5b942;border-radius:5px;padding:1px 6px;margin-left:6px}
.stop-floor{margin-top:10px;font-size:12.5px;font-weight:700;color:var(--down);background:rgba(38,194,129,.08);border:1px solid rgba(38,194,129,.3);border-radius:8px;padding:8px 11px}
.alerts{margin-top:8px;display:flex;flex-direction:column;gap:5px}
.alert-item{font-size:12px;padding:6px 9px;border-radius:7px}
.alert-item.red{background:rgba(245,86,77,.10);border-left:3px solid var(--up);color:#f0a9a4}
.alert-item.orange{background:rgba(245,185,66,.10);border-left:3px solid var(--neu);color:#e9cd8a}
/* 情绪 */
.fg-big{font-size:22px;font-weight:800;margin:6px 0}
.fg-big b{font-size:30px;color:var(--neu)}
.fg-div{font-size:12.5px;color:var(--acc);background:rgba(74,168,255,.08);border-radius:7px;padding:6px 9px;margin:6px 0}
.fg-action{font-size:12.5px;color:#aab4c0;margin-bottom:6px}
.fg-detail{margin-top:6px}
.fg-detail summary{cursor:pointer;font-size:12px;color:var(--mut)}
.fg-detail table{width:100%;border-collapse:collapse;margin-top:6px;font-size:11.5px}
.fg-detail th,.fg-detail td{padding:5px 6px;text-align:left;border-bottom:1px solid var(--line)}
.fg-detail th{color:var(--mut);font-weight:400}
/* 逻辑引擎 */
.lg-block{margin:8px 0;background:var(--bg2);border-radius:9px;padding:9px 11px}
.lg-buy{border-left:3px solid var(--down)} .lg-sell{border-left:3px solid var(--up)}
.lg-noadd{border-left:3px solid var(--neu)} .lg-emo{border-left:3px solid var(--acc)}
.lg-h{font-size:13px;font-weight:700;margin-bottom:4px}
.lg-pre{font-size:12px;white-space:pre-wrap;color:#cdd7e2;font-family:inherit;margin:0;line-height:1.55}
.lg-tbl{width:100%;border-collapse:collapse;margin-top:8px;font-size:11.5px}
.lg-tbl th,.lg-tbl td{padding:6px 6px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}
.lg-tbl th{color:var(--mut);font-weight:400}
/* 数据源 */
.src-box{font-size:12.5px;line-height:1.7;background:rgba(74,168,255,.05);border-radius:8px;padding:10px 12px}
details.card summary{cursor:pointer;font-size:16px;font-weight:700;display:flex;align-items:center;gap:6px;list-style:none}
details.card summary::-webkit-details-marker{display:none}
details.card[open] summary{margin-bottom:10px;border-bottom:1px solid var(--line);padding-bottom:8px}
/* 术语悬停 */
.tip{border-bottom:1px dotted var(--acc);cursor:help}
.tip:hover{position:relative}
.tip:hover::after{content:attr(data-tip);position:absolute;left:0;top:130%;z-index:50;background:#0b0f15;border:1px solid var(--line);color:var(--tx);font-size:11.5px;line-height:1.4;padding:6px 8px;border-radius:8px;width:260px;box-shadow:0 4px 14px rgba(0,0,0,.5);font-weight:400}
@media (max-width:680px){
  .hbody{flex-direction:column}.hkline{flex:1;min-width:0}.hkline canvas{height:160px}
  .hright{grid-template-columns:1fr}.sbar-name{flex-basis:120px}.stop-name{flex-basis:110px}
  .cmd-main{gap:8px}.cmd-nav{margin-left:0}
}
@media print{
  body{background:#fff;color:#111;max-width:100%}
  .cmdbar{position:static;box-shadow:none}.card{break-inside:avoid;box-shadow:none}
  .hcard{break-inside:avoid}.tip:hover::after{display:none}
  details.card:not([open]){display:block}details.card summary{margin-bottom:8px}
  *{color:#111!important;border-color:#ccc!important}
}
/* === v2 优化：决策三栏 + 指数滚动 + 简化持仓表 === */
html{scroll-padding-top:72px}
body{padding-top:4px}
.decision-header{display:grid;grid-template-columns:1fr 1.2fr 1fr;gap:10px;margin-bottom:12px}
.panel-box{padding:14px;border-radius:10px;background:var(--card);border:1px solid var(--line)}
.de-label{font-size:12px;color:var(--mut);margin-bottom:6px;font-weight:600;text-transform:uppercase;letter-spacing:.5px}
.de-scene-tag{display:inline-block;padding:4px 12px;border-radius:20px;font-weight:700;font-size:14px;margin-bottom:6px}
.de-scene-tag.red{background:rgba(245,86,77,.18);color:var(--up)}
.de-scene-tag.orange{background:rgba(217,164,65,.18);color:var(--neu)}
.de-scene-tag.green{background:rgba(38,194,129,.16);color:var(--down)}
.de-action-main{font-size:17px;font-weight:800;color:var(--neu);margin:4px 0;line-height:1.4}
.de-detail{font-size:12.5px;color:var(--mut);line-height:1.5;margin-top:2px}
.de-risk ul{list-style:none;padding:0;margin:4px 0 0;font-size:13px;line-height:1.8;color:var(--mut)}
.de-risk ul li:first-child{color:var(--up);font-weight:700}
.de-action{border-left:3px solid var(--neu)}
.de-scene{border-left:3px solid var(--up)}
.de-risk{border-left:3px solid #f5564d}
/* 指数横向滚动 */
.ix-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}
.ix-scroll{display:flex;gap:10px;overflow-x:auto;padding-bottom:4px;scrollbar-width:none}
.ix-scroll::-webkit-scrollbar{display:none}
.ix-item{flex-shrink:0;background:var(--bg2);padding:8px 14px;border-radius:8px;min-width:80px;text-align:center;border:1px solid var(--line)}
.ix-name{font-size:11.5px;color:var(--mut);margin-bottom:2px}
.ix-val{font-size:17px;font-weight:800}
/* 持仓简化表 */
.ht{width:100%;border-collapse:collapse;font-size:13.5px}
.ht th,.ht td{padding:8px 6px;text-align:left;border-bottom:1px solid var(--line)}
.ht th{color:var(--mut);font-weight:400;font-size:12px}
.ht-name{font-weight:600}
.ht-w{color:var(--acc);font-weight:700}
.ht-w.ow{color:var(--up);font-weight:800}
.ht-ret{font-weight:600}
.ht .op-tag{font-size:11px;padding:2px 10px;border-radius:12px;font-weight:700}
.ht-detail{font-size:11px;color:var(--mut);margin-top:2px;line-height:1.4}
.ht-minor td{font-size:12px;color:var(--mut);padding:4px 6px}
.ht-minor-td{opacity:.7}
/* 持仓表行展开详情 */
.ht-main{cursor:pointer}.ht-main:hover{background:rgba(74,168,255,.06)}
.ht-expand{margin-left:6px;font-size:10px;color:var(--mut);transition:transform .2s}
.ht-detail td{padding:10px 12px;background:var(--bg2);border-bottom:2px solid var(--line)}
.htd-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:8px}
.htd-col{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:8px 10px}
.htd-h{font-size:11px;color:var(--mut);margin-bottom:4px;font-weight:700}
.htd-v{font-size:12.5px;line-height:1.5}.htd-v b{color:var(--neu)}
.htd-logic{font-size:12px;color:#aab4c0;line-height:1.5;padding:8px 10px;background:rgba(0,0,0,.15);border-radius:8px}
/* 次日预案 */
.ol-body{padding:0 4px}
.ol-section{margin:8px 0}
.ol-section ul{margin:4px 0;padding-left:18px;font-size:12.5px;line-height:1.6;color:#cdd7e2}
.ol-section li{margin:3px 0}
@media (max-width:680px){
  .decision-header{grid-template-columns:1fr}
  .ix-item{min-width:64px;padding:6px 10px}.ix-val{font-size:15px}
  .ht{font-size:12px}.ht th,.ht td{padding:5px 4px}
}
</style>
</head>
<body>
<h1>🎯 尾盘决策</h1>
<div class="sub">数据截止 __DATE__ 尾盘 · 更新 __UPD__ · 数据源 __TIER__（neodata/westock）· 收盘前操作预案 · 仅供参考不构成投资建议</div>
"""

# ---------- 静态 SCRIPT（ECharts 日K，__DATA__ 注入） ----------
SCRIPT = """
<script>
const REPORT = __DATA__;
const DARK = {tx:'#e6edf3', mut:'#8b98a9', up:'#f5564d', down:'#26c281', acc:'#4aa8ff', neu:'#d9a441'};
function genMA(n, closes){
  var r=[];
  for(var i=0;i<closes.length;i++){
    if(i<n-1){ r.push('-'); continue; }
    var s=0; for(var j=0;j<n;j++){ s+=closes[i-j]; }
    r.push(+(s/n).toFixed(4));
  }
  return r;
}
function initKlines(){
  try{
    var hs = (REPORT.position && REPORT.position.holdings) || [];
    hs.forEach(function(h, idx){
      var k = h.kline;
      var canvas = document.getElementById('kline_'+idx);
      if(!canvas) return;
      if(!k || !k.ohlc || !k.ohlc.length){
        canvas.parentNode.innerHTML = '<div class="kline-text">'+(h.kline_text||'⚠ 日K数据未返回')+'</div>';
        return;
      }
      var ohlc = k.ohlc, dates = k.dates || [];
      var closes = ohlc.map(function(d){ return d[1]; });
      var ma5 = genMA(5, closes), ma20 = genMA(20, closes);
      var marklines = [];
      if(k.current_price!=null) marklines.push({yAxis:k.current_price, name:'当前'});
      if(k.support!=null) marklines.push({yAxis:k.support, name:'支撑'});
      if(k.pressure!=null) marklines.push({yAxis:k.pressure, name:'压力'});
      var last = dates.length-1;
      var chart = echarts.init(canvas, null, {renderer:'canvas'});
      chart.setOption({
        backgroundColor:'transparent',
        grid:{left:4,right:10,top:8,bottom:16,containLabel:true},
        xAxis:{type:'category',data:dates,axisLabel:{show:false},axisLine:{lineStyle:{color:'#2a3340'}},axisTick:{show:false}},
        yAxis:{scale:true,axisLabel:{color:DARK.mut,fontSize:9},splitLine:{lineStyle:{color:'#1c232e'}},axisLine:{show:false}},
        tooltip:{trigger:'axis',axisPointer:{type:'cross'},backgroundColor:'#0b0f15',borderColor:'#2a3340',textStyle:{color:'#e6edf3',fontSize:10}},
        series:[
          {type:'candlestick',data:ohlc,
           itemStyle:{color:DARK.up,color0:DARK.down,borderColor:DARK.up,borderColor0:DARK.down},
           markLine:{silent:true,symbol:'none',lineStyle:{type:'dashed',color:DARK.acc},label:{color:DARK.tx,fontSize:9},data:marklines},
           markPoint:{symbol:'pin',symbolSize:30,itemStyle:{color:DARK.acc},data:[{coord:[last, closes[last]], value:'今'}]}},
          {type:'line',data:ma5,smooth:true,showSymbol:false,lineStyle:{color:DARK.acc,width:1},name:'MA5'},
          {type:'line',data:ma20,smooth:true,showSymbol:false,lineStyle:{color:DARK.neu,width:1},name:'MA20'}
        ]
      });
      
      // 月K（从日K聚合）
      var mCanvas = document.getElementById('kmonth_'+idx);
      if(mCanvas && ohlc.length > 0){
        var months = {}, mdates = [];
        dates.forEach(function(d, i){
          var m = d.substring(0,7);
          var c = ohlc[i];
          if(!months[m]){ months[m] = {open:c[0],close:c[1],low:c[2],high:c[3]}; mdates.push(m); }
          else{ months[m].close = c[1]; months[m].low = Math.min(months[m].low, c[2]); months[m].high = Math.max(months[m].high, c[3]); }
        });
        mdates = mdates.slice(-12);
        var mData = mdates.map(function(m){ return [months[m].open, months[m].close, months[m].low, months[m].high]; });
        var mChart = echarts.init(mCanvas, null, {renderer:'canvas'});
        mChart.setOption({
          backgroundColor:'transparent',
          grid:{left:4,right:10,top:8,bottom:16,containLabel:true},
          xAxis:{type:'category',data:mdates,axisLabel:{color:DARK.mut,fontSize:8},axisLine:{lineStyle:{color:'#2a3340'}},axisTick:{show:false}},
          yAxis:{scale:true,axisLabel:{color:DARK.mut,fontSize:8},splitLine:{lineStyle:{color:'#1c232e'}},axisLine:{show:false}},
          tooltip:{trigger:'axis',axisPointer:{type:'cross'},backgroundColor:'#0b0f15',borderColor:'#2a3340',textStyle:{color:'#e6edf3',fontSize:10}},
          series:[{type:'candlestick',data:mData,
            itemStyle:{color:DARK.up,color0:DARK.down,borderColor:DARK.up,borderColor0:DARK.down}}]
        });
      }
    });
  }catch(e){ console.error('kline error', e); }
}
window.addEventListener('load', initKlines);
// 持仓表行展开
function toggleHtDetail(idx){
  var row=document.getElementById('htd_'+idx);
  var trigger=document.querySelector('.ht-main[data-idx="'+idx+'"] .ht-expand');
  if(!row||!trigger)return;
  var vis=row.style.display;
  row.style.display=vis==='none'?'':'none';
  trigger.textContent=vis==='none'?'▲':'▼';
  trigger.style.color=vis==='none'?'var(--acc)':'var(--mut)';
}
</script>
</body>
</html>
"""

def load_data(date):
    p = os.path.join(BASE, "tail_%s.json" % date)
    if not os.path.exists(p):
        fs = sorted(glob.glob(os.path.join(BASE, "tail_*.json")))
        if not fs:
            raise SystemExit("找不到 tail_%s.json，也没有任何 tail_*.json" % date)
        p = fs[-1]
        date = os.path.basename(p)[5:-5]
    return json.load(open(p, encoding="utf-8")), date


# ================================================================
#  方法论模块1: 精简速览组件（首屏30秒决策）
# ================================================================
def render_lite_summary(data):
    """方法论方向1+4: 精简推送组件，首屏仅保留定调+必做操作+风控红线三类。
    
    模板结构（适配消息推送，30秒决策）:
    【日期 尾盘决策】
    ▌当日场景：...
    ▌必做操作：1. ... 2. ...
    ▌风控红线：...
    ▌次日预判：...，重点关注...
    """
    inst = data.get("instruction") or {}
    risk = data.get("risk") or {}
    sent = data.get("sentiment") or {}
    pos = data.get("position") or {}
    date = data.get("meta", {}).get("date", data.get("generated_at", "")[:10])
    
    # 当日场景定性
    scenario = esc(inst.get("tail_scenario", ""))
    scene_detail = esc(inst.get("scene_detail", ""))
    
    # 必做操作: 从active_action提取，最多2条
    active_action = esc(inst.get("active_action", ""))
    active_detail = esc(inst.get("active_detail", ""))
    
    # 从持有基金中检查是否触发止损
    holdings = (pos.get("holdings") or [])[:10]
    mandatory_ops = []
    for h in holdings:
        inst_text = esc(h.get("instruction", ""))
        hname = esc(h.get("name", ""))
        if "减仓" in inst_text or "卖出" in inst_text or "SELL" in inst_text:
            mandatory_ops.append((hname, inst_text))
    
    ops_html = ""
    if active_action:
        ops_html += f'<li><strong>{active_action}</strong> · {active_detail}</li>'
    for name, txt in mandatory_ops[:2]:
        if name not in (active_action or ""):
            ops_html += f'<li><strong>{name}</strong>：{txt}</li>'
    if not ops_html:
        ops_html = '<li>无必执行操作（全部持有观察）</li>'
    
    # 风控红线 (最多3条，从risk_rules和硬止损中提取)
    risk_rules = inst.get("risk_rules", [])
    risk_list = list(risk_rules)[:3]
    # 追加硬止损红线
    hard = risk.get("hard_stop") or {}
    for item in (hard.get("items") or []):
        cur = num(item.get("cur_loss_pct"))
        sl = num(item.get("stop_loss_pct"))
        if cur is not None and sl is not None and cur <= sl:
            risk_list.append(f"-8%硬止损已触发: {item.get('name','')}")
    risk_html = " · ".join(esc(r) for r in risk_list) if risk_list else "无"
    
    # 次日预判
    nd = inst.get("next_day") or {}
    watch_points = nd.get("watch_points") or []
    plans = nd.get("plans") or []
    # 从plans提取基准判断
    baseline = ""
    for p in plans[:2]:
        baseline += p + "；"
    baseline = esc(baseline[:120])
    focus = esc(watch_points[0]) if watch_points else ""
    
    # 情绪速览
    fg = num(sent.get("fear_greed_index"))
    fg_str = f"F&G {int(round(fg))} · {esc(sent.get('level',''))}" if fg is not None else ""
    
    # 报告链接（收件箱）
    link = f"../../reports/{date}/尾盘决策-{date}.html"
    
    return f'''
<section id="lite" class="card lite-summary" style="background:var(--card);border-left:3px solid var(--acc);padding:12px 16px;margin-bottom:12px">
  <div style="font-weight:700;font-size:13px;color:var(--acc);margin-bottom:6px">【{esc(date)} 尾盘决策】</div>
  <table style="width:100%;border-collapse:collapse;font-size:13px">
    <tr><td style="width:72px;vertical-align:top;color:var(--mut);padding:3px 8px 3px 0">▌当日场景</td><td style="padding:3px 0">{scenario} · {scene_detail} {fg_str}</td></tr>
    <tr><td style="vertical-align:top;color:var(--mut);padding:3px 8px 3px 0">▌必做操作</td><td style="padding:3px 0"><ol style="margin:0;padding-left:18px">{ops_html}</ol></td></tr>
    <tr><td style="vertical-align:top;color:var(--mut);padding:3px 8px 3px 0">▌风控红线</td><td style="padding:3px 0;color:var(--up)">{risk_html}</td></tr>
    <tr><td style="vertical-align:top;color:var(--mut);padding:3px 8px 3px 0">▌次日预判</td><td style="padding:3px 0">{baseline}</td></tr>
    <tr><td style="vertical-align:top;color:var(--mut);padding:3px 8px 3px 0">▌重点观察</td><td style="padding:3px 0">{focus}</td></tr>
  </table>
  <div style="margin-top:6px;font-size:11px;color:var(--mut)">
    完整报告: <a href="{link}" target="_blank" style="color:var(--acc)">{link}</a>
  </div>
</section>'''


# ================================================================
#  方法论模块3: 多维度涨跌归因（事实→传导→影响）
# ================================================================
def render_attribution(data):
    """
    方向3: 结构化涨跌归因 — 固定5维度 × 三段式(事实→传导→影响)
    下跌赛道 vs 抗跌赛道分开，无数据不展示。
    """
    sent = data.get("sentiment") or {}
    sector = data.get("sector") or {}
    bars = sector.get("bars") or []
    risk = data.get("risk") or {}
    pos = data.get("position") or {}
    holdings = pos.get("holdings") or []
    
    sent_note = sent.get("note", "")
    fg = num(sent.get("fear_greed_index"))
    
    # 判断主要下跌维度
    dims = []
    
    # 1. 外围事件
    outer_kw = ["原油", "美股", "美元", "外围", "地缘", "冲突", "通胀", "加息", "纳指", "KOSPI"]
    outer_triggered = any(kw in sent_note for kw in outer_kw)
    if outer_triggered:
        dims.append(("外围事件", f"隔夜{esc(sent_note[:60])}" if sent_note else "外围市场波动", "传导至A股风险偏好", "对科技/创新药持仓形成估值压制"))
    
    # 2. 资金面
    total_net = 0
    outflow_names = []
    inflow_names = []
    for b in bars:
        nf = num(b.get("net_inflow"))
        if nf is not None:
            total_net += nf
            if nf < -10:
                outflow_names.append(b.get("name",""))
            elif nf > 10:
                inflow_names.append(b.get("name",""))
    if outflow_names:
        dims.append(("资金面", f"主力净流出{abs(total_net):.0f}亿，{esc('、'.join(outflow_names[:3]))}出逃", "资金集体避险，踩踏式卖出", "半导体/科技持仓遭抽血"))
    if inflow_names:
        dims.append(("资金面", f"主力流入{esc('、'.join(inflow_names[:2]))}", "资金寻找抗跌品种", "债券/创新药等防御仓受益"))
    
    # 3. 情绪面
    if fg is not None:
        fg_label = sent.get("level", "")
        if fg <= 40:
            dims.append(("情绪面", f"恐惧贪婪指数{int(round(fg))} · {esc(fg_label)}", "恐慌情绪蔓延，非理性抛售", "极端情绪下不宜追杀，等待企稳"))
        elif fg >= 60:
            dims.append(("情绪面", f"恐惧贪婪指数{int(round(fg))} · {esc(fg_label)}", "市场偏热，需防情绪反转", "获利了结压力增大"))
    
    # 4. 技术面
    for b in bars[:2]:
        score = num(b.get("score"))
        name = b.get("name", "")
        if score is not None and score <= 40:
            _, label = level_info(score)
            dims.append(("技术面", f"{esc(name)} 技术评分{score} · {label}", "破位触发技术派止损盘", f"{esc(name)}持仓承压，需等企稳信号"))
    
    # 5. 基本面
    hard = risk.get("hard_stop") or {}
    for item in (hard.get("items") or [])[:1]:
        cur = num(item.get("cur_loss_pct"))
        sl = num(item.get("stop_loss_pct"))
        if cur is not None:
            dims.append(("基本面", f"当前亏损{cur:.2f}%", "基本面疲弱+触发风控阈值", "需执行硬止损纪律"))
    
    if not dims:
        return ""
    
    table_rows = ""
    for dim, fact, chain, impact in dims:
        table_rows += f'<tr><td style="font-weight:600;min-width:70px">{dim}</td><td>{esc(fact)}</td><td>{esc(chain)}</td><td>{esc(impact)}</td></tr>'
    
    # 抗跌赛道支撑逻辑
    defensives = []
    for b in bars:
        score = num(b.get("score"))
        name = b.get("name", "")
        nf = num(b.get("net_inflow"))
        if score is not None and score >= 50:
            defensives.append((name, score, nf))
    def_html = ""
    for name, score, nf in defensives[:3]:
        nf_str = f"资金净流入{nf:.0f}亿" if nf and nf > 0 else ""
        def_html += f'<li>{esc(name)} 技术评分{score} · {nf_str}</li>'
    
    return f'''
<section id="attr" class="card">
  <h3>当日涨跌多维度归因</h3>
  <table style="width:100%;border-collapse:collapse;font-size:13px">
    <thead><tr><th style="text-align:left;padding:6px 8px;background:var(--bg2)">分析维度</th><th style="text-align:left;padding:6px 8px;background:var(--bg2)">事实数据</th><th style="text-align:left;padding:6px 8px;background:var(--bg2)">传导逻辑</th><th style="text-align:left;padding:6px 8px;background:var(--bg2)">对持仓影响</th></tr></thead>
    <tbody>{table_rows}</tbody>
  </table>
  {f'<div style="margin-top:8px"><h4 style="margin:0 0 4px 0;font-size:13px">🟢 抗跌赛道支撑逻辑</h4><ul style="margin:0;padding-left:18px;font-size:12px">{def_html}</ul></div>' if def_html else ""}
</section>'''


# ================================================================
#  方法论模块4: 明日三分情景预判
# ================================================================
def render_outlook(data):
    """方向4: 情景预判表格 — 三情景×量化判定×对应操作 + 核心观察指标"""
    inst = data.get("instruction") or {}
    nd = inst.get("next_day") or {}
    
    watch_points = nd.get("watch_points") or []
    plans = nd.get("plans") or []
    
    # 基准判断
    baseline = ""
    for p in plans:
        if "缩量企稳" not in p and "放量下跌" not in p and "超跌反弹" not in p:
            baseline = p
            break
    if not baseline and plans:
        baseline = plans[0]
    
    # 三情景表格
    scenario_rows = ""
    scenarios = [("缩量企稳", "🟢"), ("放量下跌", "🔴"), ("超跌反弹", "🟡")]
    for sname, icon in scenarios:
        matched = [p for p in plans if sname in p]
        # 从plans中拆出判定条件和操作
        text = matched[0] if matched else ""
        # 尝试拆分为判定条件+操作（如果包含"则"或"，"）
        condition, action = text, ""
        for sep in ["，对应操作", ", 对应操作", "，则", ", 则"]:
            if sep in text:
                parts = text.split(sep, 1)
                condition = parts[0].strip()
                action = parts[1].strip() if len(parts) > 1 else ""
                break
        scenario_rows += f'<tr><td><b>{icon} {sname}</b></td><td>{esc(condition[:100])}</td><td>{esc(action[:80])}</td></tr>'
    if not scenario_rows:
        scenario_rows = '<tr><td colspan="3" style="text-align:center;color:var(--mut)">当日数据未提供情景判定</td></tr>'
    
    # 核心观察指标
    watch_html = ""
    for wp in watch_points[:5]:
        watch_html += f'<li>{esc(wp)}</li>'
    
    return f'''
<section id="outlook" class="card">
  <h3>次日行情预判与情景预案</h3>
  <p style="font-size:12px;color:var(--mut);margin:0 0 8px 0">不做绝对涨跌预测，给出各情景下的量化判定与对应操作</p>
  <div style="border-left:3px solid var(--acc);padding:6px 12px;margin-bottom:8px;font-size:13px">
    <b>基准判断</b>：{esc(baseline[:120]) if baseline else "等待数据"}
  </div>
  <table style="width:100%;border-collapse:collapse;font-size:13px">
    <thead><tr><th style="text-align:left;padding:6px 8px;background:var(--bg2);width:120px">情景类型</th><th style="text-align:left;padding:6px 8px;background:var(--bg2)">量化判定标准</th><th style="text-align:left;padding:6px 8px;background:var(--bg2)">对应操作动作</th></tr></thead>
    <tbody>{scenario_rows}</tbody>
  </table>
  {f'<div style="margin-top:8px"><h4 style="margin:0 0 4px 0;font-size:13px">🔍 次日核心观察指标</h4><ul style="margin:0;padding-left:18px;font-size:12px">{watch_html}</ul></div>' if watch_html else ""}
</section>'''


# ================================================================
#  方法论模块5: 因子回测输出表（读 factor_backtest.py 产物）
# ================================================================
def render_factor_backtest(data, date):
    """方向5: 因子回测追踪 — 前日决策回测 + 因子权重表 + 权重调整说明"""
    import os
    flog = os.path.join(BASE, "factor_log.json")
    wf = os.path.join(BASE, "factor_weights.json")
    
    log_records = []
    if os.path.exists(flog):
        try:
            log = json.load(open(flog, encoding="utf-8"))
            log_records = log.get("records", [])
        except Exception:
            pass
    
    current_weights = {}
    if os.path.exists(wf):
        try:
            current_weights = json.load(open(wf, encoding="utf-8"))
        except Exception:
            pass
    
    if not log_records and not current_weights:
        return ""
    
    # 前日决策回测
    backtest_html = ""
    if len(log_records) >= 2:
        prev = log_records[-2]
        curr = log_records[-1]
        prev_score = num(prev.get("combined_score"))
        curr_score = num(curr.get("combined_score"))
        # 如果两日综合分方向一致，视为符合预期
        if prev_score is not None and curr_score is not None:
            if abs(curr_score - prev_score) <= 5:
                accuracy = "符合预期（综合分波动≤5）"
            elif (curr_score > prev_score and prev_score < 50) or (curr_score < prev_score and prev_score >= 50):
                accuracy = "方向正确（综合分向预期方向变化）"
            else:
                accuracy = "方向偏差（综合分反向变化）"
        else:
            accuracy = "数据不足"
        
        backtest_html = f'''
    <div style="margin-bottom:12px">
      <h4 style="margin:0 0 6px 0;font-size:13px">（一）前一日决策回测</h4>
      <table style="width:100%;border-collapse:collapse;font-size:12px">
        <tr><td style="padding:3px 8px 3px 0;width:110px;color:var(--mut)">预判准确率</td><td style="padding:3px 0">{accuracy}</td></tr>
        <tr><td style="padding:3px 8px 3px 0;color:var(--mut)">综合分变化</td><td style="padding:3px 0">{prev_score if prev_score is not None else "—"} → {curr_score if curr_score is not None else "—"}</td></tr>
        <tr><td style="padding:3px 8px 3px 0;color:var(--mut)">规则有效性</td><td style="padding:3px 0">硬止损/集中度风控规则持续运行中（需更多交易日验证）</td></tr>
      </table>
    </div>'''
    
    # 因子权重表
    recent = [r for r in log_records if r.get("date") <= date][-10:]
    if recent:
        rows = ""
        for r in recent:
            rd = r.get("date", "")
            factors = r.get("factors", {})
            weights = r.get("weights", {})
            ics = r.get("ic", {})
            cells = f'<td>{rd}</td>'
            for fn in ["外围", "资金", "技术", "情绪", "基本面"]:
                fv = num(factors.get(fn))
                wv = num(weights.get(fn))
                icv = num(ics.get(fn)) if isinstance(ics, dict) else None
                fcell = f'{fv:.1f}' if fv is not None else '-'
                wcell = f'{wv*100:.0f}%' if wv is not None else '-'
                iccell = f'{icv:.3f}' if icv is not None else '-'
                cells += f'<td style="text-align:right;padding:2px 6px">{fcell}</td><td style="text-align:right;padding:2px 6px">{wcell}</td><td style="text-align:right;padding:2px 6px;font-size:11px">{iccell}</td>'
            rows += '<tr>' + cells + '</tr>'
        
        # 权重调整说明
        if current_weights:
            # 与基准权重对比
            adj_notes = []
            base_wt = {"外围": 0.20, "资金": 0.25, "技术": 0.25, "情绪": 0.15, "基本面": 0.15}
            for fn in ["外围", "资金", "技术", "情绪", "基本面"]:
                cur = current_weights.get(fn)
                base = base_wt.get(fn)
                if cur is not None and base is not None:
                    diff = (cur - base) * 100
                    if abs(diff) >= 3:
                        direction = "上调" if diff > 0 else "下调"
                        adj_notes.append(f"{fn}因子{direction}{abs(diff):.0f}%")
            adj_txt = "；".join(adj_notes) if adj_notes else "权重与基准一致，暂无调整"
        
        return f'''
<section id="factor" class="card">
  <h3>每日回测与因子迭代</h3>
  {backtest_html}
  <div>
    <h4 style="margin:0 0 6px 0;font-size:13px">（二）当前因子权重表</h4>
    <div style="overflow-x:auto">
    <table style="width:100%;border-collapse:collapse;font-size:12px">
      <thead><tr style="background:var(--bg2)"><th style="padding:4px 6px;text-align:left">日期</th>
        <th colspan="3" style="padding:4px 6px;text-align:center">外围</th><th colspan="3" style="padding:4px 6px;text-align:center">资金</th>
        <th colspan="3" style="padding:4px 6px;text-align:center">技术</th><th colspan="3" style="padding:4px 6px;text-align:center">情绪</th>
        <th colspan="3" style="padding:4px 6px;text-align:center">基本面</th></tr>
      <tr style="background:var(--bg2)"><th style="padding:2px 6px"></th>
        <th style="padding:2px 6px">分</th><th style="padding:2px 6px">权</th><th style="padding:2px 6px;font-size:10px">IC</th>
        <th style="padding:2px 6px">分</th><th style="padding:2px 6px">权</th><th style="padding:2px 6px;font-size:10px">IC</th>
        <th style="padding:2px 6px">分</th><th style="padding:2px 6px">权</th><th style="padding:2px 6px;font-size:10px">IC</th>
        <th style="padding:2px 6px">分</th><th style="padding:2px 6px">权</th><th style="padding:2px 6px;font-size:10px">IC</th>
        <th style="padding:2px 6px">分</th><th style="padding:2px 6px">权</th><th style="padding:2px 6px;font-size:10px">IC</th>
      </tr></thead>
      <tbody>{rows}</tbody>
    </table>
    </div>
  </div>
  <div style="margin-top:8px;font-size:12px;color:var(--mut);border-top:1px solid var(--line);padding-top:8px">
    <b>（三）本期权重调整说明</b>：{esc(adj_txt)}<br>
    <span style="font-size:11px">ICIR前2因子+5%/后2-5%，归一化到[5%,50%]。数据来自 factor_log.json / factor_weights.json</span>
  </div>
</section>'''
    return ""


def main():
    args = sys.argv[1:]
    if "--plan" in args:
        # 已弃用: 调仓止盈计划已合并到尾盘决策主报告
        # 原 --plan 独立交付物不再生成, 所有内容统一在 尾盘决策-<DATE>.html 中
        rest = [a for a in args if a != "--plan"]
        date = rest[0] if rest else datetime.date.today().isoformat()
        print(f"[deprecated] --plan 模式已取消。改为生成合并版尾盘决策报告。")
        args = rest  # fall through to normal mode
    if args:
        date = args[0]
    else:
        fs = sorted(glob.glob(os.path.join(BASE, "tail_*.json")))
        if not fs:
            raise SystemExit("用法: make_tail_html.py <YYYY-MM-DD> [--plan]")
        date = os.path.basename(fs[-1])[5:-5]
    data, date = load_data(date)

    global CRED_TIER
    CRED_TIER = data.get("data_tier") or "T2"
    updated = data.get("updated_at") or (date + " 14:20")
    prev = yesterdate(date)
    wl = load_wl()

    body = (
            # ── 模块1: 精简速览（首屏必看） ──
            render_lite_summary(data) +
            # ── 模块1续: 核心决策速览 ──
            render_decision_header(data.get("instruction")) +
            # ── 模块1续: 必执行操作+条件触发+持有不动 三级分类 ──
            render_mandatory_ops(data) +
            # ── 模块1续: 指数速览+持仓表（二级优先） ──
            render_index_scroll((data.get("position") or {}).get("index_kpis")) +
            render_holdings_table((data.get("position") or {}).get("holdings")) +
            # ── 模块2: 操作底层决策逻辑 ──
            render_logic_rules(data) +
            # ── 模块3: 涨跌多维度归因 ──
            render_attribution(data) +
            render_sector(data.get("sector")) +
            # ── 模块4: 次日行情预判与情景预案 ──
            render_outlook(data) +
            # ── 模块5: 每日回测与因子迭代 ──
            render_factor_backtest(data, date) +
            # ── 底部折叠区: 详细数据 ──
            render_risk_stop(data.get("risk")) +
            render_sentiment(data.get("sentiment")) +
            render_tail_window(wl, data) +
            render_profit_lock(wl) +
            render_rebalance(wl) +
            render_sources(data.get("sources"), data.get("disclaimer"))
        )

    head = (HEAD.replace("__DATE__", esc(date))
             .replace("__UPD__", esc(updated))
             .replace("__TIER__", esc(CRED_TIER)))
    script = SCRIPT.replace("__DATA__", json.dumps(data, ensure_ascii=False))

    out_dir = os.path.join(REPORTS, date)
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "尾盘决策-%s.html" % date)
    open(out, "w", encoding="utf-8").write(head + body + script)
    print("saved", out, "size", os.path.getsize(out))

if __name__ == "__main__":
    main()
