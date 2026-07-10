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

BASE = os.path.dirname(os.path.abspath(__file__))
REPORTS = os.path.join(BASE, "reports")
CRED_TIER = "T2"

# ---------- 工具函数（与 make_midday_html.py 保持一致） ----------
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
def chg_span(v, thr=2.0, suffix="%"):
    """行内涨跌幅 span（红涨绿跌，±thr% 加粗）。None → 灰字⚠。"""
    v = num(v)
    if v is None:
        return '<span class="mut">⚠ 数据源未返回</span>'
    cls = pcls(v)
    b = " b" if pbold(v, thr) else ""
    sign = "+" if v > 0 else ""
    return '<span class="%s%s">%s%.2f%s</span>' % (cls, b, sign, v, suffix)
def miss(v):
    """缺失值标准化：未连接 / N/A / 数据源未返回 / None → 灰字⚠。"""
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
def yesterdate(d):
    dt = datetime.date.fromisoformat(d)
    return (dt - datetime.timedelta(days=1)).isoformat()

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
        # 左 1/3 日K
        k = h.get("kline")
        if k and k.get("ohlc") and len(k.get("ohlc")):
            kline_html = '<canvas id="kline_%d"></canvas>' % i
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
    });
  }catch(e){ console.error('kline error', e); }
}
window.addEventListener('load', initKlines);
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

    body = (render_cmd_bar(data.get("instruction"), date) +
            render_tail_window(wl, data) +
            render_core_kpis((data.get("position") or {}).get("index_kpis")) +
            render_holdings((data.get("position") or {}).get("holdings")) +
            render_sector(data.get("sector")) +
            render_risk_stop(data.get("risk")) +
            render_profit_lock(wl) +
            render_rebalance(wl) +
            render_sentiment(data.get("sentiment")) +
            render_logic(data.get("logic")) +
            render_sources(data.get("sources"), data.get("disclaimer")))

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
