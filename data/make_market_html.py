# -*- coding: utf-8 -*-
"""
make_market_html.py  —  大盘·板块·日K研判 报告生成器
读取 data/market_<DATE>.json（由自动化 agent 在 neodata 分析后落盘的结构化数据），
渲染为优化版 market-index-<DATE>.html。

优化点（对应需求 P0/P1/P2）：
  P0  结论前置(今日核心研判卡) / 模块重排 / 统一信号等级体系(分数→等级→颜色) /
       表格视觉(色阶+进度条/涨红跌绿±3%加粗/表头固定/奇偶行) / 卡片化 /
       三级标题 / ⚠橙色背景条 / 标签化
  P1  情绪8因子雷达 / 指数涨跌幅横向柱 / 主力资金流向条 / 指数迷你走势 /
       顶部固定导航 / 折叠展开 / 悬停术语 / 持仓筛选 / 持仓联动升级(关键点位+风险距离) /
       次日观察点位 / 风险分级
  P2  可信度标识 / 响应式 / 打印样式 / 历史入口

色彩规则：
  涨跌幅  → 红涨绿跌（A股惯例，守 color board --up/--down）
  信号等级 → 多=绿系 / 空=红系（用户新等级表，与涨跌价独立轴，页面有图例）
  资金流向 → 正流入绿 / 负流出红（用户指定）
"""
import json
import os
import sys
import glob
import re
import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
REPORTS = os.path.join(BASE, "reports")
Cred_tier = "T2"


def load_data(date):
    p = os.path.join(BASE, "market_%s.json" % date)
    if not os.path.exists(p):
        fs = sorted(glob.glob(os.path.join(BASE, "market_*.json")))
        if not fs:
            raise SystemExit("找不到 market_%s.json，也没有任何 market_*.json" % date)
        p = fs[-1]
        date = os.path.basename(p)[7:-5]
    return json.load(open(p, encoding="utf-8")), date


def load_tech(date):
    """读取技术面增强产出的 market_tech_<DATE>.json，返回 (by_code, by_sector) 字典；缺失返回 (None, None)。"""
    p = os.path.join(BASE, "market_tech_%s.json" % date)
    if not os.path.exists(p):
        return None, None
    try:
        d = json.load(open(p, encoding="utf-8"))
        return d.get("by_code") or {}, d.get("by_sector") or {}
    except Exception:
        return None, None


# ---------- 工具函数 ----------
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


def pbold(v):
    v = num(v)
    return v is not None and abs(v) >= 3.0


def chg_cell(v, suffix="%"):
    v = num(v)
    if v is None:
        return '<td class="neu">—</td>'
    cls = pcls(v)
    b = " b" if pbold(v) else ""
    sign = "+" if v > 0 else ""
    return '<td class="%s%s">%s%.2f%s</td>' % (cls, b, sign, v, suffix)


def bar(score, cls):
    s = num(score) or 0
    s = max(0, min(100, int(round(s))))
    return '<div class="bar"><i class="%s" style="width:%d%%"></i></div>' % (cls, s)


def yesterdate(d):
    dt = datetime.date.fromisoformat(d)
    return (dt - datetime.timedelta(days=1)).isoformat()


def dim_name(d):
    return {"trend": "趋势", "volprice": "量价", "shape": "形态",
            "mainforce": "主力"}.get(d, d)


# ---------- 各模块渲染 ----------
def render_core(c):
    if not c:
        return ""
    m = c.get("metrics") or {}
    amt = num(m.get("amount_yi"))
    fg = num(m.get("fear_greed"))
    br = num(m.get("breadth_ratio"))
    br_txt = ("%.2f" % br) if br is not None else "—"
    amt_txt = ("%.0f 亿" % amt) if amt is not None else "—"
    fg_txt = ("%d" % fg) if fg is not None else "—"
    if (fg or 0) >= 60:
        fg_cls = "lv-up"
    elif (fg or 0) < 40:
        fg_cls = "lv-down"
    else:
        fg_cls = "lv-neu-up"
    return f'''
<section id="core" class="core-card">
  <div class="core-head">🎯 今日核心研判 <span class="badge">决策优先</span></div>
  <div class="core-line"><span class="cl-k">市场定性</span><span class="cl-v">{tip(c.get('market_qual', ''))}</span></div>
  <div class="core-line"><span class="cl-k">主线总结</span><span class="cl-v">{tip(c.get('main_line', ''))}</span></div>
  <div class="core-line"><span class="cl-k">操作总纲</span><span class="cl-v act">{tip(c.get('action_guideline', ''))}</span></div>
  <div class="metrics">
    <div class="metric"><div class="m-k">全市场成交额</div><div class="m-v">{amt_txt}</div></div>
    <div class="metric"><div class="m-k">恐惧贪婪指数</div><div class="m-v {fg_cls}">{fg_txt}</div></div>
    <div class="metric"><div class="m-k">涨跌家数比</div><div class="m-v">{br_txt}</div></div>
  </div>
</section>'''


def render_cred(cred):
    if not cred:
        return ""
    rows = ""
    for it in cred:
        st = it.get("status", "ok")
        if st == "ok":
            icon, cls = "✅", "ok"
        elif st == "warn":
            icon, cls = "⚠️", "warn"
        else:
            icon, cls = "❓", "q"
        rows += '<div class="kv"><span>%s</span><span class="%s">%s %s</span></div>' % (
            tip(it.get("item", "")), cls, icon, tip(it.get("note", "")))
    return f'''
<div class="card">
  <h2>① 数据可信度 <span class="badge">{esc(Cred_tier)}</span></h2>
  {rows}
</div>'''


def render_panorama(indices):
    if not indices:
        return ""
    rows = ""
    for ix in indices:
        cls, lbl = level_info(ix.get("score"), ix.get("tendency"))
        flow = num(ix.get("main_flow_yi"))
        if flow is not None:
            flow_txt = "+%.0f" % flow
            flow_cls = pcls(flow)
        else:
            flow_txt = "—"
            flow_cls = "neu"
        rows += ('<tr data-score="%d">'
                 '<td class="lname">%s</td>'
                 '<td>%s</td>'
                 '%s'
                 '<td>%s</td>'
                 '<td class="%s">%s</td>'
                 '<td><span class="tag %s">%s %s</span>%s</td>'
                 '</tr>') % (
            int(round(num(ix.get("score")) or 0)),
            tip(ix.get("name", "")),
            esc(ix.get("close", "—")),
            chg_cell(ix.get("chg_pct")),
            esc(ix.get("amount_yi", "—")),
            flow_cls, flow_txt,
            cls, lbl, esc(ix.get("score", "")),
            bar(ix.get("score"), cls))
    note = ('<div class="note">涨跌幅按 A股惯例 <b class="up">红涨</b>/<b class="down">绿跌</b>；'
            '信号等级 <b class="lv-up-text">绿=偏多</b>/<b class="lv-down-text">红=偏空</b>'
            '（情绪/多空语义，与涨跌价独立）。</div>')
    return f'''
<div class="card">
  <h2>② 大盘全景速览 <span class="badge">{len(indices)} 指数</span></h2>
  <div class="chart-wrap"><canvas id="chgBar"></canvas></div>
  <div class="tbl-scroll">
  <table>
    <tr><th>指数</th><th>收盘</th><th>涨%</th><th>额(亿)</th><th>主净(亿)</th><th>倾向 / 等级</th></tr>
    {rows}
  </table>
  </div>
  {note}
  <div class="chart-wrap"><canvas id="flowBar"></canvas></div>
</div>'''


def render_sentiment(s):
    if not s:
        return ""
    fg = num(s.get("fear_greed"))
    if (fg or 0) >= 60:
        fg_cls = "lv-up"
    elif (fg or 0) < 40:
        fg_cls = "lv-down"
    else:
        fg_cls = "lv-neu-up"
    f = s.get("factors") or {}
    order = [("breadth", "市场广度"), ("limit_up_down", "涨跌停家数"), ("main_flow", "主力净流入"),
             ("northbound", "北向资金"), ("margin", "融资余额"), ("volume", "量能亢奋度"),
             ("vix", "VIX恐慌"), ("erp", "股债ERP")]
    rows = ""
    for k, name in order:
        v = num(f.get(k))
        vtxt = ("%d" % v) if v is not None else "—"
        if (v or 0) >= 60:
            cls = "lv-up"
        elif (v or 0) < 40:
            cls = "lv-down"
        else:
            cls = "lv-neu-up"
        rows += '<div class="kv"><span>%s</span><span class="%s">%s</span></div>' % (name, cls, vtxt)
    fg_txt = ("%d" % fg) if fg is not None else "—"
    lvl = "贪婪" if (fg or 0) >= 60 else ("恐惧" if (fg or 0) < 40 else "中性")
    return f'''
<div class="card">
  <h2>③ 情绪与资金面 <span class="badge">恐惧贪婪 {fg_txt}</span></h2>
  <div class="chart-wrap"><canvas id="sentRadar"></canvas></div>
  <div class="kv"><span class="neu">综合恐惧贪婪指数</span><span class="{fg_cls}"><b>{fg_txt}</b> · {lvl}</span></div>
  <div class="bar"><i class="{fg_cls}" style="width:{int(round(fg or 0))}%"></i></div>
  {rows}
  <div class="note">{tip(s.get('note', ''))}</div>
</div>'''


def render_sectors(sec):
    if not sec:
        return ""
    def chips(lst, cls):
        if not lst:
            return '<span class="mut">—</span>'
        return " ".join('<span class="chip %s">%s</span>' % (cls, tip(x)) for x in lst)
    return f'''
<div class="card">
  <h2>④ 板块主线与传导</h2>
  <div class="row"><span class="acc">强势主线</span><span>{chips(sec.get('strong'), 'c-up')}</span></div>
  <div class="row"><span class="acc">联动走强</span><span>{chips(sec.get('rising'), 'c-up')}</span></div>
  <div class="row"><span class="warn">弱势 / 承压</span><span>{chips(sec.get('weak'), 'c-down')}</span></div>
  <div class="row"><span class="acc">轮动逻辑</span><span>{tip(sec.get('rotation', ''))}</span></div>
  <div class="note">{tip(sec.get('chain', ''))}</div>
</div>'''


def render_holdings(hs):
    if not hs:
        return ""
    rows = ""
    for h in hs:
        cls, lbl = level_info(None, h.get("level"))
        sup = h.get("support")
        pres = h.get("pressure")
        rd = num(h.get("risk_dist_pct"))
        if rd is not None:
            rd_txt = "%.0f%%" % rd
            if rd >= 80:
                rd_cls = "lv-strong-down"
            elif rd >= 60:
                rd_cls = "lv-down"
            elif rd >= 40:
                rd_cls = "lv-neu-up"
            else:
                rd_cls = "lv-up"
        else:
            rd_txt = "—"
            rd_cls = "neu"
        rows += ('<tr data-level="%s">'
                 '<td class="lname">%s</td>'
                 '<td>%s</td>'
                 '<td><span class="tag %s">%s</span></td>'
                 '<td>%s / %s</td>'
                 '<td class="%s">%s</td>'
                 '</tr>') % (
            esc(h.get("level", "中性")),
            tip(h.get("name", "")),
            tip(h.get("related", "")),
            cls, tip(h.get("signal", "")),
            esc(sup if sup is not None else "—"),
            esc(pres if pres is not None else "—"),
            rd_cls, rd_txt)
    return f'''
<div class="card">
  <h2>⑤ 持仓联动 <span class="badge">watchlist</span></h2>
  <div class="filter-bar">
    <button class="fbtn active" data-f="all">全部</button>
    <button class="fbtn" data-f="持有">持有</button>
    <button class="fbtn" data-f="警惕">警惕</button>
    <button class="fbtn" data-f="中性">中性</button>
  </div>
  <div class="tbl-scroll">
  <table>
    <tr><th>持仓</th><th>关联</th><th>信号</th><th>关键点位(支撑/压力)</th><th>距-8%止损</th></tr>
    {rows}
  </table>
  </div>
</div>'''


def render_predict(pds, watch_levels):
    if not pds:
        return ""
    def c(t):
        t = t or ""
        if "偏多" in t or "多" in t or "+" in t:
            return "up"
        if "偏空" in t or "空" in t or "-" in t:
            return "down"
        return "neu"
    rows = ""
    for p in pds:
        rows += ('<tr><td class="lname">%s</td>'
                 '<td class="%s">%s</td><td class="%s">%s</td><td class="%s">%s</td>'
                 '<td class="neu">%s</td></tr>') % (
            tip(p.get("target", "")), c(p.get("d1")), tip(p.get("d1", "")),
            c(p.get("d2")), tip(p.get("d2", "")), c(p.get("d3")), tip(p.get("d3", "")),
            esc(p.get("conf", "")))
    wl = ""
    if watch_levels:
        for w in watch_levels:
            cls = "up" if (w.get("type") or "").startswith("上行") else "down"
            wl += '<div class="row"><span class="%s">%s</span><span>%s</span></div>' % (
                cls, tip(w.get("type", "")), tip(w.get("text", "")))
    if not wl:
        wl = '<div class="note">（未提供观察位）</div>'
    return f'''
<div class="card">
  <h2>⑥ 次日走势预判 <span class="badge">模型研判</span></h2>
  <div class="tbl-scroll">
  <table>
    <tr><th>标的</th><th>次日</th><th>t+2</th><th>t+3</th><th>置信</th></tr>
    {rows}
  </table>
  </div>
  <h3 class="sub-h">🔭 明日关键观察位</h3>
  {wl}
</div>'''


def _render_kx_card(i, ix, t, cls, lbl, cid="candle"):
    """技术面增强版卡片：左 ECharts 日K蜡烛图(全周期均线含年线) + 右技术文案/支撑压力。
    cid 控制 canvas id 前缀（指数 candle / 板块 scandle），避免 ID 冲突。"""
    name = tip(ix.get("name", ""))
    score = esc(ix.get("score", ""))
    lines = [
        ("趋势判定", t.get("trend_text", "")),
        ("K线解读", t.get("kline_text", "")),
        ("价位研判", t.get("price_text", "")),
        ("操作参考", t.get("op_ref", "")),
    ]
    lx = ""
    for k, v in lines:
        if v:
            lx += '<div class="kx-line"><b>%s</b><span>%s</span></div>' % (k, tip(v))
    sr = ""
    for s in (t.get("support") or []):
        sr += ('<div class="sr-item sr-up"><span class="sr-p">%.2f</span>'
               '<span class="sr-t">%s</span><span class="sr-s s-%s">%s</span></div>') % (
            s["price"], s["type"], s["strength"], s["strength"])
    for r in (t.get("resistance") or []):
        sr += ('<div class="sr-item sr-down"><span class="sr-p">%.2f</span>'
               '<span class="sr-t">%s</span><span class="sr-s s-%s">%s</span></div>') % (
            r["price"], r["type"], r["strength"], r["strength"])
    sp = ""
    for tag in (t.get("special") or []):
        sp += '<span class="sp-tag">%s</span>' % tag
    badges = ('<span class="kv-badge">单K %s</span> <span class="kv-badge">3日 %s</span> '
              '<span class="kv-badge">MACD %s</span> <span class="kv-badge">KDJ %s</span> '
              '<span class="kv-badge">量比 %s</span> <span class="kv-badge">偏距5 %.2f%%</span>') % (
        t.get("pattern_single", "—"), t.get("pattern_3d", "—"),
        t.get("macd", "—"), t.get("kdj", "—"),
        ("%.2f" % t["vol_ratio"]) if t.get("vol_ratio") is not None else "—",
        t.get("bias5") or 0)
    warn = ('<div class="warn-box">⚠ %s</div>' % tip(ix.get("warn"))) if ix.get("warn") else ""
    return '''
<details>
  <summary>%s · %s <span class="sc">综合 %s</span></summary>
  <div class="kx-card">
    <div class="kx-left">
      <div style="font-size:11px;color:var(--mut);margin-bottom:4px">📈 日K（近250日）</div>
      <div class="chart-wrap sm"><canvas id="%s%d"></canvas></div>
      <div style="font-size:11px;color:var(--mut);margin:8px 0 4px">📊 月K（近12月）</div>
      <div class="chart-wrap" style="height:180px"><canvas id="m%s%d"></canvas></div>
      <div class="badges">%s</div>
      %s
    </div>
    <div class="kx-right">
      %s
      <div class="sr-title">支撑 / 压力（近→远 · 强/中/弱）</div>
      <div class="sr-list">%s</div>
    </div>
  </div>
 %s
</details>''' % (name, lbl, score, cid, i, cid, i, badges, sp, lx, sr, warn)


def render_kline(indices):
    if not indices:
        return ""
    blocks = ""
    for i, ix in enumerate(indices):
        cls, lbl = level_info(ix.get("score"), ix.get("tendency"))
        tech = ix.get("tech")
        if tech:
            blocks += _render_kx_card(i, ix, tech, cls, lbl)
            continue
        # 降级：原五维 + 迷你折线
        k = ix.get("kline") or {}
        dims = ""
        for dim in ["trend", "volprice", "shape", "mainforce"]:
            d = k.get(dim)
            if not d:
                continue
            dcls = level_info(d.get("score"), d.get("label"))[0]
            dims += '<div class="dim"><b>%s</b><span class="%s">%s</span><span>%s</span></div>' % (
                dim_name(dim), dcls, tip(d.get("label", "")), tip(d.get("detail", "")))
        cs = k.get("close_signal")
        if cs:
            dims += '<div class="dim"><b>收盘暗号</b><span>%s</span><span>%s</span></div>' % (
                tip(cs.get("label", "")), tip(cs.get("detail", "")))
        warn = ('<div class="warn-box">⚠ %s</div>' % tip(ix.get("warn"))) if ix.get("warn") else ""
        canvas = ('<div class="chart-wrap sm"><canvas id="mini%d"></canvas></div>' % i) if ix.get("series") \
            else '<div class="note">（未提供近 N 日收盘序列，略去迷你走势）</div>'
        blocks += '''
<details>
  <summary>%s · %s <span class="sc">综合 %s</span></summary>
  %s
  %s
  %s
</details>''' % (tip(ix.get("name", "")), lbl, esc(ix.get("score", "")),
         dims, warn, canvas)
    return f'''
<div class="card">
  <h2>⑦ 指数详细日 K 研判 <span class="badge">技术面增强</span></h2>
  {blocks}
</div>'''


def render_sector_kline(cards):
    """板块日K技术研判：每张卡左 ECharts 蜡烛图 + 右技术文案/支撑压力（复用 _render_kx_card）。"""
    if not cards:
        return ""
    blocks = ""
    for i, c in enumerate(cards):
        cat = c.get("category")
        if cat == "strong":
            cls, lbl = "lv-strong-up", "强多"
        elif cat == "rising":
            cls, lbl = "lv-up", "偏多"
        else:
            cls, lbl = "lv-down", "偏空"
        ix = {"name": c.get("name"), "score": "", "warn": None}
        t = c.get("tech")
        if t:
            blocks += _render_kx_card(i, ix, t, cls, lbl, cid="scandle")
            continue
        blocks += ('<details><summary>%s · %s</summary>'
                   '<div class="note">（未提供近 250 日 OHLC，暂略去日K）</div></details>') % (
            tip(c.get("name", "")), lbl)
    return f'''
<div class="card" id="skline">
  <h2>📊 板块日 K 技术研判 <span class="badge">技术面增强</span></h2>
  {blocks}
</div>'''


def render_risk(risks, disclaimer):
    if not risks and not disclaimer:
        return ""
    rows = ""
    for r in risks or []:
        lv = r.get("level") or "中"
        cls = {"高": "rk-high", "中": "rk-mid", "低": "rk-low"}.get(lv, "rk-mid")
        rows += '<div class="row"><span class="%s">%s</span><span>%s</span></div>' % (
            cls, lv, tip(r.get("text", "")))
    disc = ('<div class="note warn">%s</div>' % tip(disclaimer)) if disclaimer else ""
    return f'''
<div class="card">
  <h2>⑧ 风险提示与免责</h2>
  {rows}
  {disc}
</div>'''


# ---------- 静态 HEAD（含全部 CSS） ----------
HEAD = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>大盘·板块·日K研判 __DATE__</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
<style>
:root{--up:#f5564d;--down:#26c281;--neu:#d9a441;--acc:#4aa8ff;--bg:#0e1117;--bg2:#161b24;--card:#1c232e;--line:#2a3340;--tx:#e6edf3;--mut:#8b98a9}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--tx);font:14px/1.55 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif;padding:12px;max-width:720px;margin:0 auto}
.up{color:var(--up)} .down{color:var(--down)} .neu{color:var(--neu)} .acc{color:var(--acc)} .mut{color:var(--mut)}
.b{font-weight:700}
h1{font-size:18px;margin-bottom:2px} .sub{color:var(--mut);font-size:12px;margin-bottom:10px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px;margin-bottom:12px;box-shadow:0 1px 2px rgba(0,0,0,.25)}
.card h2{font-size:15px;margin-bottom:8px;display:flex;align-items:center;gap:6px;border-bottom:1px solid var(--line);padding-bottom:6px}
.sub-h{font-size:13.5px;margin:12px 0 6px;color:var(--acc)}
.badge{font-size:11px;padding:1px 6px;border-radius:6px;background:var(--bg2);color:var(--mut);border:1px solid var(--line)}
table{width:100%;border-collapse:collapse;font-size:12.5px}
.tbl-scroll{max-height:440px;overflow:auto}
th,td{padding:6px 4px;text-align:right;border-bottom:1px solid var(--line)}
th{color:var(--mut);font-weight:400;font-size:11.5px;position:sticky;top:0;background:var(--card);z-index:2}
td:first-child,th:first-child{text-align:left}
tbody tr:nth-child(even){background:rgba(255,255,255,.025)}
.lname{font-weight:600}
.tag{font-size:11px;padding:1px 6px;border-radius:5px;font-weight:600}
.lv-strong-up{background:rgba(38,194,129,.30);color:#2ee07a;--lc:#2ee07a}
.lv-up{background:rgba(38,194,129,.16);color:#26c281;--lc:#26c281}
.lv-neu-up{background:rgba(38,194,129,.08);color:#7fd1a8;--lc:#7fd1a8}
.lv-neu-down{background:rgba(245,86,77,.08);color:#e08a85;--lc:#e08a85}
.lv-down{background:rgba(245,86,77,.16);color:#f5564d;--lc:#f5564d}
.lv-strong-down{background:rgba(245,86,77,.30);color:#ff6b61;--lc:#ff6b61}
.lv-up-text{color:#26c281} .lv-down-text{color:#f5564d}
.bar{height:6px;border-radius:3px;background:var(--bg2);overflow:hidden;margin-top:3px}
.bar i{display:block;height:100%;border-radius:3px;background:var(--lc)}
.row{display:flex;justify-content:space-between;gap:8px;padding:5px 0;border-bottom:1px solid var(--line);font-size:13px}
.row:last-child{border:0} .row span:last-child{text-align:right}
.kv{display:flex;justify-content:space-between;font-size:13px;padding:4px 0}
.kv .ok{color:#26c281} .kv .warn{color:var(--neu)} .kv .q{color:var(--mut)}
.note{color:var(--mut);font-size:11.5px;margin-top:6px;line-height:1.5}
.warn{color:var(--neu)}
details{border-top:1px solid var(--line);padding:8px 0}
summary{cursor:pointer;font-weight:600;font-size:13.5px;display:flex;justify-content:space-between;align-items:center}
summary .sc{font-size:12px;color:var(--mut)}
.dim{display:grid;grid-template-columns:64px 1fr 1fr;gap:4px;font-size:12px;margin-top:6px}
.dim b{color:var(--mut);font-weight:400}
.core-card{background:linear-gradient(135deg,#1c2a3a,#16202c);border:1px solid #2b4a6a;border-radius:14px;padding:14px;margin-bottom:12px}
.core-head{font-size:16px;font-weight:700;margin-bottom:8px;display:flex;align-items:center;gap:6px}
.core-line{display:flex;gap:8px;padding:4px 0;font-size:13px;align-items:baseline}
.cl-k{flex:0 0 64px;color:var(--acc);font-weight:600;font-size:12px}
.cl-v{flex:1;color:var(--tx)}
.cl-v.act{color:#ffd479;font-weight:600}
.metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:10px}
.metric{background:rgba(255,255,255,.04);border:1px solid var(--line);border-radius:10px;padding:10px 6px;text-align:center}
.m-k{font-size:11px;color:var(--mut);margin-bottom:4px}
.m-v{font-size:19px;font-weight:700}
.chart-wrap{margin:8px 0;background:rgba(0,0,0,.15);border-radius:10px;padding:6px;height:240px}
.chart-wrap.sm{height:150px}
canvas{width:100%!important;height:100%!important}
.chip{display:inline-block;font-size:11.5px;padding:2px 8px;border-radius:20px;margin:2px 0}
.c-up{background:rgba(38,194,129,.16);color:#26c281} .c-down{background:rgba(245,86,77,.16);color:#f5564d}
.filter-bar{display:flex;gap:6px;margin-bottom:8px;flex-wrap:wrap}
.fbtn{background:var(--bg2);color:var(--mut);border:1px solid var(--line);border-radius:8px;padding:3px 10px;font-size:12px;cursor:pointer}
.fbtn.active{background:var(--acc);color:#08121e;border-color:var(--acc);font-weight:600}
.warn-box{background:rgba(217,164,65,.12);border-left:3px solid var(--neu);border-radius:6px;padding:6px 8px;margin-top:6px;font-size:12px;color:#e8c878}
.rk-high{color:#ff6b61;font-weight:700} .rk-mid{color:var(--neu);font-weight:600} .rk-low{color:var(--mut)}
.tip{border-bottom:1px dotted var(--acc);cursor:help}
.tip:hover{position:relative}
.tip:hover::after{content:attr(data-tip);position:absolute;left:0;top:130%;z-index:50;background:#0b0f15;border:1px solid var(--line);color:var(--tx);font-size:11.5px;line-height:1.4;padding:6px 8px;border-radius:8px;width:240px;box-shadow:0 4px 14px rgba(0,0,0,.5);font-weight:400}
.topnav{position:sticky;top:0;z-index:30;background:rgba(14,17,23,.95);backdrop-filter:blur(6px);border:1px solid var(--line);border-radius:10px;padding:6px 8px;margin-bottom:12px;display:flex;gap:4px;flex-wrap:wrap;align-items:center;font-size:12px}
.topnav a{color:var(--mut);text-decoration:none;padding:3px 7px;border-radius:6px}
.topnav a:hover{background:var(--bg2);color:var(--tx)}
.nav-hist{margin-left:auto;display:flex;gap:4px}
@media (max-width:560px){.metrics{grid-template-columns:1fr}.topnav{font-size:11px}.m-v{font-size:17px}}
@media print{
  body{background:#fff;color:#111;max-width:100%}
  .topnav{display:none}.card{break-inside:avoid;box-shadow:none}
  .chart-wrap{height:200px}
  details{display:block!important}
  .tip:hover::after{display:none}
  *{color:#111!important;border-color:#ccc!important}
  .lv-strong-up,.lv-up,.lv-neu-up{background:#e8f7ee!important}
  .lv-neu-down,.lv-down,.lv-strong-down{background:#fdeceb!important}
}
.kx-card{display:flex;gap:10px;margin-top:6px}
.kx-left{flex:0 0 38%;min-width:200px}
.kx-right{flex:1;min-width:0}
.kx-line{display:grid;grid-template-columns:64px 1fr;gap:6px;font-size:12px;margin-top:6px;align-items:baseline}
.kx-line b{color:var(--mut);font-weight:400}
.badges{margin-top:6px;font-size:11px;color:var(--mut);line-height:1.9}
.kv-badge{display:inline-block;background:var(--bg2);border:1px solid var(--line);border-radius:6px;padding:1px 6px;margin:2px 3px 2px 0;color:var(--tx);font-size:11px}
.sp-tag{display:inline-block;font-size:11px;padding:1px 7px;border-radius:20px;margin:3px 3px 0 0;background:rgba(217,164,65,.16);color:var(--neu);border:1px solid rgba(217,164,65,.4)}
.sr-title{font-size:11.5px;color:var(--mut);margin:10px 0 4px;border-top:1px dashed var(--line);padding-top:6px}
.sr-list{display:flex;flex-wrap:wrap;gap:4px}
.sr-item{display:flex;align-items:center;gap:5px;font-size:11.5px;padding:2px 8px;border-radius:7px;border:1px solid var(--line)}
.sr-up{background:rgba(38,194,129,.10);border-color:rgba(38,194,129,.35)}
.sr-down{background:rgba(245,86,77,.10);border-color:rgba(245,86,77,.35)}
.sr-p{font-weight:700}
.sr-up .sr-p{color:#26c281}.sr-down .sr-p{color:#f5564d}
.sr-t{color:var(--mut)}
.sr-s{font-size:10px;padding:0 5px;border-radius:5px}
.s-强{background:rgba(74,168,255,.18);color:#7cc4ff}
.s-中{background:rgba(139,152,169,.16);color:var(--mut)}
.s-弱{background:rgba(139,152,169,.08);color:#6b7686}
@media (max-width:560px){.kx-card{flex-direction:column}.kx-left{flex:none;width:100%}}
</style>
</head>
<body>
<h1>📡 大盘·板块·日K研判</h1>
<div class="sub">__DATE__ · __UPD__ · 数据源 neodata(__TIER__) · 方法论 四因子+板块五维+情绪8因子</div>
"""

# ---------- 静态 SCRIPT（ECharts，DATA 由 __DATA__ 注入） ----------
SCRIPT = """
<script>
const REPORT = __DATA__;
const DARK = {bg:'transparent', tx:'#e6edf3', mut:'#8b98a9', up:'#f5564d', down:'#26c281', acc:'#4aa8ff', neu:'#d9a441'};
function initCharts(){
  try{
    const idx = (REPORT.indices||[]);
    if(document.getElementById('chgBar') && idx.length){
      const c = echarts.init(document.getElementById('chgBar'), null, {renderer:'canvas'});
      const names = idx.map(x=>x.name).reverse();
      const vals = idx.map(x=>(x.chg_pct||0)).reverse();
      c.setOption({
        backgroundColor:'transparent',
        grid:{left:64,right:42,top:12,bottom:12},
        tooltip:{trigger:'axis',axisPointer:{type:'shadow'}},
        xAxis:{type:'value',axisLabel:{color:DARK.mut,formatter:'{value}%'},splitLine:{lineStyle:{color:'#222b36'}}},
        yAxis:{type:'category',data:names,axisLabel:{color:DARK.tx},axisLine:{lineStyle:{color:'#2a3340'}}},
        series:[{type:'bar',data:vals.map(v=>({value:v,itemStyle:{color:v>0?DARK.up:(v<0?DARK.down:DARK.neu)}})),
          label:{show:true,position:'right',color:DARK.tx,formatter:'{c}%'}}]
      });
    }
    if(document.getElementById('flowBar')){
      const fi = idx.filter(x=>x.main_flow_yi!==null && x.main_flow_yi!==undefined);
      if(fi.length){
        const c = echarts.init(document.getElementById('flowBar'), null, {renderer:'canvas'});
        const names = fi.map(x=>x.name).reverse();
        const vals = fi.map(x=>x.main_flow_yi).reverse();
        c.setOption({
          backgroundColor:'transparent',
          grid:{left:64,right:50,top:24,bottom:12},
          tooltip:{trigger:'axis',axisPointer:{type:'shadow'}},
          title:{text:'主力净流入(亿)',left:'center',top:0,textStyle:{color:DARK.mut,fontSize:12}},
          xAxis:{type:'value',axisLabel:{color:DARK.mut},splitLine:{lineStyle:{color:'#222b36'}}},
          yAxis:{type:'category',data:names,axisLabel:{color:DARK.tx},axisLine:{lineStyle:{color:'#2a3340'}}},
          series:[{type:'bar',data:vals.map(v=>({value:v,itemStyle:{color:v>=0?DARK.down:DARK.up}})),
            label:{show:true,position:'right',color:DARK.tx,formatter:'{c}'}}]
        });
      }
    }
    if(document.getElementById('sentRadar') && REPORT.sentiment){
      const f = REPORT.sentiment.factors||{};
      const keys = [['breadth','市场广度'],['limit_up_down','涨跌停'],['main_flow','主力净流入'],['northbound','北向资金'],['margin','融资余额'],['volume','量能亢奋'],['vix','VIX'],['erp','股债ERP']];
      const c = echarts.init(document.getElementById('sentRadar'), null, {renderer:'canvas'});
      c.setOption({
        backgroundColor:'transparent',
        tooltip:{},
        radar:{indicator:keys.map(k=>({name:k[1],max:100})),
          axisName:{color:DARK.tx,fontSize:11},splitLine:{lineStyle:{color:'#2a3340'}},
          splitArea:{areaStyle:{color:['rgba(74,168,255,.03)','rgba(74,168,255,.06)']}},
          axisLine:{lineStyle:{color:'#2a3340'}}},
        series:[{type:'radar',data:[{value:keys.map(k=>f[k[0]]||0),
          areaStyle:{color:'rgba(74,168,255,.25)'},lineStyle:{color:DARK.acc},itemStyle:{color:DARK.acc}}]}]
      });
    }
    idx.forEach((x,i)=>{
      if(x.tech) return;   // 技术面增强卡走蜡烛图，跳过迷你折线
      const el = document.getElementById('mini'+i);
      if(el && Array.isArray(x.series) && x.series.length){
        const c = echarts.init(el, null, {renderer:'canvas'});
        const s = x.series;
        const ma=(n)=>s.map((_,j)=> j>=n-1 ? +(s.slice(j-n+1,j+1).reduce((a,b)=>a+b,0)/n).toFixed(2) : null);
        c.setOption({
          backgroundColor:'transparent',
          grid:{left:46,right:12,top:14,bottom:18},
          tooltip:{trigger:'axis'},
          xAxis:{type:'category',data:s.map((_,j)=>j+1),axisLabel:{color:DARK.mut,fontSize:9},axisLine:{lineStyle:{color:'#2a3340'}}},
          yAxis:{type:'value',scale:true,axisLabel:{color:DARK.mut,fontSize:9},splitLine:{lineStyle:{color:'#1d2530'}}},
          series:[
            {type:'line',data:s,name:'收盘',showSymbol:false,lineStyle:{color:DARK.acc,width:1.5}},
            {type:'line',data:ma(5),name:'MA5',showSymbol:false,lineStyle:{color:DARK.up,width:1}},
            {type:'line',data:ma(20),name:'MA20',showSymbol:false,lineStyle:{color:DARK.down,width:1}}
          ]
        });
      }
    });
    // 技术面增强：日K蜡烛图（全周期均线，含年线）
    idx.forEach((x,i)=>{
      const el = document.getElementById('candle'+i);
      const t = x.tech;
      if(el && t && Array.isArray(t.candle) && t.candle.length){
        const c = echarts.init(el, null, {renderer:'canvas'});
        const dates = t.dates||[];
        const ma=(name)=> (t.ma && t.ma[name]) ? t.ma[name] : null;
        c.setOption({
          backgroundColor:'transparent',
          grid:{left:48,right:12,top:24,bottom:18},
          tooltip:{trigger:'axis'},
          legend:{data:['MA5','MA20','MA60','MA120','MA250(年)'],textStyle:{color:DARK.mut,fontSize:9},top:0,right:4,itemWidth:12,itemHeight:8},
          xAxis:{type:'category',data:dates,axisLabel:{color:DARK.mut,fontSize:9},axisLine:{lineStyle:{color:'#2a3340'}}},
          yAxis:{type:'value',scale:true,axisLabel:{color:DARK.mut,fontSize:9},splitLine:{lineStyle:{color:'#1d2530'}}},
          series:[
            {type:'candlestick',name:'日K',data:t.candle,
              itemStyle:{color:DARK.up,color0:DARK.down,borderColor:DARK.up,borderColor0:DARK.down}},
            {type:'line',data:ma('MA5'),name:'MA5',showSymbol:false,lineStyle:{color:'#e6c84',width:1}},
            {type:'line',data:ma('MA20'),name:'MA20',showSymbol:false,lineStyle:{color:'#b083f0',width:1}},
            {type:'line',data:ma('MA60'),name:'MA60',showSymbol:false,lineStyle:{color:'#26c281',width:1}},
            {type:'line',data:ma('MA120'),name:'MA120',showSymbol:false,lineStyle:{color:'#4aa8ff',width:1}},
            {type:'line',data:ma('MA250'),name:'MA250(年)',showSymbol:false,lineStyle:{color:'#8b98a9',width:1,type:'dashed'}}
          ]
        });
        // 月K聚合渲染
        const mEl = document.getElementById('mcandle'+i);
        if(mEl && Array.isArray(t.candle) && t.candle.length){
          const months={}, mds=[];
          (t.dates||[]).forEach((d,j)=>{
            const m=d.substring(0,7); const c=t.candle[j];
            if(!months[m]){months[m]={open:c[0],close:c[1],low:c[2],high:c[3]};mds.push(m);}
            else{months[m].close=c[1];months[m].low=Math.min(months[m].low,c[2]);months[m].high=Math.max(months[m].high,c[3]);}
          });
          const use=mds.slice(-12);
          const mData=use.map(m=>[months[m].open,months[m].close,months[m].low,months[m].high]);
          const mc=echarts.init(mEl,null,{renderer:'canvas'});
          mc.setOption({
            backgroundColor:'transparent',grid:{left:48,right:12,top:8,bottom:18},
            tooltip:{trigger:'axis'},xAxis:{type:'category',data:use,axisLabel:{color:DARK.mut,fontSize:9},axisLine:{lineStyle:{color:'#2a3340'}}},
            yAxis:{type:'value',scale:true,axisLabel:{color:DARK.mut,fontSize:9},splitLine:{lineStyle:{color:'#1d2530'}}},
            series:[{type:'candlestick',name:'月K',data:mData,
              itemStyle:{color:DARK.up,color0:DARK.down,borderColor:DARK.up,borderColor0:DARK.down}}]
          });
        }
      }
    });
    // 板块日K蜡烛图（全周期均线，含年线）
    const skx = (REPORT._sector_kx)||[];
    skx.forEach((x,i)=>{
      const el = document.getElementById('scandle'+i);
      const t = x.tech;
      if(el && t && Array.isArray(t.candle) && t.candle.length){
        const c = echarts.init(el, null, {renderer:'canvas'});
        const dates = t.dates||[];
        const ma=(name)=> (t.ma && t.ma[name]) ? t.ma[name] : null;
        c.setOption({
          backgroundColor:'transparent',
          grid:{left:48,right:12,top:24,bottom:18},
          tooltip:{trigger:'axis'},
          legend:{data:['MA5','MA20','MA60','MA120','MA250(年)'],textStyle:{color:DARK.mut,fontSize:9},top:0,right:4,itemWidth:12,itemHeight:8},
          xAxis:{type:'category',data:dates,axisLabel:{color:DARK.mut,fontSize:9},axisLine:{lineStyle:{color:'#2a3340'}}},
          yAxis:{type:'value',scale:true,axisLabel:{color:DARK.mut,fontSize:9},splitLine:{lineStyle:{color:'#1d2530'}}},
          series:[
            {type:'candlestick',name:'日K',data:t.candle,
              itemStyle:{color:DARK.up,color0:DARK.down,borderColor:DARK.up,borderColor0:DARK.down}},
            {type:'line',data:ma('MA5'),name:'MA5',showSymbol:false,lineStyle:{color:'#e6c84',width:1}},
            {type:'line',data:ma('MA20'),name:'MA20',showSymbol:false,lineStyle:{color:'#b083f0',width:1}},
            {type:'line',data:ma('MA60'),name:'MA60',showSymbol:false,lineStyle:{color:'#26c281',width:1}},
            {type:'line',data:ma('MA120'),name:'MA120',showSymbol:false,lineStyle:{color:'#4aa8ff',width:1}},
            {type:'line',data:ma('MA250'),name:'MA250(年)',showSymbol:false,lineStyle:{color:'#8b98a9',width:1,type:'dashed'}}
          ]
        });
        // 板块月K
        const mEl = document.getElementById('mscandle'+i);
        if(mEl && Array.isArray(t.candle) && t.candle.length){
          const months={}, mds=[];
          (t.dates||[]).forEach((d,j)=>{
            const m=d.substring(0,7); const c=t.candle[j];
            if(!months[m]){months[m]={open:c[0],close:c[1],low:c[2],high:c[3]};mds.push(m);}
            else{months[m].close=c[1];months[m].low=Math.min(months[m].low,c[2]);months[m].high=Math.max(months[m].high,c[3]);}
          });
          const use=mds.slice(-12);
          const mData=use.map(m=>[months[m].open,months[m].close,months[m].low,months[m].high]);
          const mc=echarts.init(mEl,null,{renderer:'canvas'});
          mc.setOption({
            backgroundColor:'transparent',grid:{left:48,right:12,top:8,bottom:18},
            tooltip:{trigger:'axis'},xAxis:{type:'category',data:use,axisLabel:{color:DARK.mut,fontSize:9},axisLine:{lineStyle:{color:'#2a3340'}}},
            yAxis:{type:'value',scale:true,axisLabel:{color:DARK.mut,fontSize:9},splitLine:{lineStyle:{color:'#1d2530'}}},
            series:[{type:'candlestick',name:'月K',data:mData,
              itemStyle:{color:DARK.up,color0:DARK.down,borderColor:DARK.up,borderColor0:DARK.down}}]
          });
        }
      }
    });
  }catch(e){ console.error('chart error', e); }
}
function initFilter(){
  const btns = document.querySelectorAll('.fbtn');
  btns.forEach(b=>{
    b.addEventListener('click',()=>{
      btns.forEach(x=>x.classList.remove('active'));
      b.classList.add('active');
      const f = b.getAttribute('data-f');
      document.querySelectorAll('#hold table tbody tr').forEach(tr=>{
        const lv = tr.getAttribute('data-level')||'';
        let show = true;
        if(f==='持有') show = /持有/.test(lv) || /偏多|强多/.test(lv);
        else if(f==='警惕') show = /警惕|偏空|强空/.test(lv);
        else if(f==='中性') show = /中性/.test(lv);
        tr.style.display = show?'':'none';
      });
    });
  });
}
window.addEventListener('load',()=>{ initCharts(); initFilter(); });
</script>
</body>
</html>
"""


def main():
    if len(sys.argv) > 1:
        date = sys.argv[1]
    else:
        fs = sorted(glob.glob(os.path.join(BASE, "market_*.json")))
        if not fs:
            raise SystemExit("用法: make_market_html.py <YYYY-MM-DD>")
        date = os.path.basename(fs[-1])[7:-5]
    data, date = load_data(date)

    # 合并技术面增强产出的 market_tech_<DATE>.json（指数 by_code + 板块 by_sector）
    by_code, by_sector = load_tech(date)
    if by_code:
        for ix in (data.get("indices") or []):
            t = by_code.get(ix.get("code")) or by_code.get(ix.get("name"))
            if t:
                ix["tech"] = t
    # 板块：取 strong/rising/weak 名称并集，挂技术面
    sec = data.get("sectors") or {}
    cat_map = {}
    for cat in ("strong", "rising", "weak"):
        for nm in (sec.get(cat) or []):
            cat_map.setdefault(nm, cat)
    sector_cards = []
    for nm, cat in cat_map.items():
        t = (by_sector or {}).get(nm)
        sector_cards.append({"name": nm, "category": cat, "tech": t})
    data["_sector_kx"] = sector_cards

    global Cred_tier
    Cred_tier = data.get("data_tier") or "T2"
    updated = data.get("updated_at") or (date + " 收盘")
    prev = yesterdate(date)

    nav = ('<nav class="topnav"><a href="#core">核心</a><a href="#cred">可信度</a>'
            '<a href="#pano">大盘</a><a href="#sent">情绪</a><a href="#sec">板块</a><a href="#skline">板块日K</a>'
            '<a href="#hold">持仓</a><a href="#pred">预判</a><a href="#kline">日K</a>'
            '<a href="#risk">风险</a>'
            '<span class="nav-hist"><a href="market-index-%s.html">←昨日</a>'
            '<a href="../../index.html">收件箱</a></span></nav>') % prev

    body = (render_core(data.get("core")) +
            render_cred(data.get("credibility")) +
            render_panorama(data.get("indices")) +
            render_sentiment(data.get("sentiment")) +
            render_sectors(data.get("sectors")) +
            render_sector_kline(sector_cards) +
            render_holdings(data.get("holdings")) +
            render_predict(data.get("predictions"), data.get("watch_levels")) +
            render_kline(data.get("indices")) +
            render_risk(data.get("risks"), data.get("disclaimer")))

    head = (HEAD.replace("__DATE__", esc(date))
            .replace("__UPD__", esc(updated))
            .replace("__TIER__", esc(Cred_tier)))
    script = SCRIPT.replace("__DATA__", json.dumps(data, ensure_ascii=False))

    out_dir = os.path.join(REPORTS, date)
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "market-index-%s.html" % date)
    open(out, "w", encoding="utf-8").write(head + nav + body + script)
    print("saved", out, "size", os.path.getsize(out))


if __name__ == "__main__":
    main()
