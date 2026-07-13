# -*- coding: utf-8 -*-
"""
make_html.py —— 基金晚间复盘 HTML 生成器（优化版 v2）

设计目标（对照优化框架）：
  1) 首屏核心摘要：3 句话结论 + 4 张 KPI 大数字卡（达标绿/预警橙/异常红）
  2) 异常/待跟进横幅：自动从数据派生
  3) 主体分层：概览 → 资金流 → α基本面 → 调仓(风险应对) → 命中率(问题归因) → 情绪 → 板块K → 新闻
  4) 底部行动闭环：明日待办 + 待跟进风险项（带优先级）
  5) 设计系统：三级标题、卡片留白、涨红跌绿（遵守 README 色板）、主色克制
  6) 交互：固定顶部导航锚点 + 回到顶部 + 折叠展开 + 响应式 + 打印样式
  7) 图表：恐惧贪婪仪表 + Chart.js α 横向柱（数值直接标注）+ 每张表配 1 句数据解读

用法：
  python make_html.py                 # 自动取最新 consolidated_*.json 日期
  python make_html.py 2026-07-09    # 指定日期

仅依赖标准库（json/os/sys/glob/datetime），无第三方依赖。
"""
import json, os, sys, glob, datetime

BASE = "C:/Users/LEGION/Nutstore/1/daily-report/data"

# ---------------- 日期解析 ----------------
def latest_date():
    fs = glob.glob(os.path.join(BASE, "consolidated_*.json"))
    ds = [os.path.basename(f).split("_")[-1].split(".")[0] for f in fs]
    return sorted(ds)[-1] if ds else None

DATE = sys.argv[1] if len(sys.argv) > 1 else (latest_date() or "2026-07-08")

def load(p, default):
    try:
        return json.load(open(os.path.join(BASE, p), encoding="utf-8"))
    except Exception:
        return default

C    = load(f"consolidated_{DATE}.json", {})
CALC = load(f"calc_{DATE}.json", {})
PLOG = load("prediction-log.json", {"records": []})

# ---------------- 工具函数 ----------------
def fnum(x, d=2, suf=""):
    if x is None: return "—"
    if isinstance(x, float): return f"{x:,.{d}f}{suf}"
    return str(x)

def pct(x):
    if x is None: return "—"
    return f"{x:+.2f}%"

def cls(x):  # 颜色类：涨红 / 跌绿 / 中性（CN 约定，遵守 README）
    if x is None: return ""
    return "up" if x >= 0 else "down"

def chip(name, w):
    if not name: return ""
    return f'<span class="chip">{name} <b>{fnum(w,1)}%</b></span>'

def status(val, good_ge, warn_lt):
    """返回 (css类, 文案)：达标绿 / 预警橙 / 异常红"""
    if val is None: return ("", "—")
    if val >= good_ge: return ("ok", "达标")
    if val >= warn_lt: return ("warn", "预警")
    return ("bad", "异常")

def semic_status(s):
    if s is None: return ("", "—")
    if s <= 60: return ("ok", "达标")
    if s <= 70: return ("warn", "预警")
    return ("bad", "异常")

# ---------------- 索引概览 ----------------
idx_html = ""
for nm in ["上证指数", "创业板指", "沪深300"]:
    v = C.get("indices", {}).get(nm, {})
    chg = v.get("change_pct")
    idx_html += f'''<div class="card sm"><div class="lbl">{nm}</div>
      <div class="big {cls(chg)}">{fnum(v.get('close'),2)}</div>
      <div class="{cls(chg)}">{pct(chg)}</div></div>'''

# ---------------- 基金 α 表 ----------------
fund_rows = ""
for f in C.get("funds", []):
    nav = f.get("nav"); d7 = f.get("daily_0707"); ytd = f.get("ytd_pct"); al = f.get("alpha")
    rk = f.get("ranking") or {}
    rank_str = f"{fnum(rk.get('rank'),0)}/{fnum(rk.get('total'),0)}" if rk.get('rank') else "—"
    top = f.get("top10") or []
    top_chips = " ".join(chip(t.get("name"), t.get("weight")) for t in top[:6]) or "—"
    risk = f.get("risk_flag")
    risk_badge = '<span class="risk">HIGH</span>' if risk == "HIGH" else ""
    st = f.get("status")
    st_badge = '<span class="dorm">休眠</span>' if st == "dormant" else ""
    fund_rows += f'''<tr>
      <td><b>{f['name']}</b><br><span class="sub">{f['sector']}</span> {risk_badge}{st_badge}</td>
      <td class="r">{fnum(nav,4)}</td>
      <td class="r {cls(d7)}">{pct(d7)}</td>
      <td class="r {cls(ytd)}">{pct(ytd)}</td>
      <td class="r {cls(al)}"><b>{pct(al)}</b></td>
      <td class="r">{rank_str}</td>
      <td class="r {cls(f.get('proxy_0708'))}">{pct(f.get('proxy_0708'))}</td>
      <td class="chips">{top_chips}</td>
    </tr>'''

# ---------------- 调仓建议 ----------------
reb_html = ""
priority_map = {"高集中度": "高", "半导体暴露过高": "高", "高风险管理": "高",
                "新建小仓观察": "低", "已排队的降风险操作": "低"}
for title, desc, sug in CALC.get("rebalance", []):
    pr = priority_map.get(title, "中")
    reb_html += f'''<div class="reb pr-{pr}">
      <div class="reb-t">● {title} <span class="pbadge p-{pr}">{pr}优先</span></div>
      <div class="reb-d">{desc}</div><div class="reb-s">➤ 建议：{sug}</div></div>'''

# ---------------- 预测命中率回填表 ----------------
pred_rows = ""
for rec in PLOG.get("records", []):
    if rec.get("verified") and rec.get("verify_date") == DATE:
        hit = rec.get("hit")
        hc = "hit" if hit else "miss"
        pred_rows += f'''<tr>
          <td>{rec['target']}</td>
          <td class="r"><span class="pdir">{rec['direction']}</span></td>
          <td class="r {cls(rec.get('actual_close_next_day'))}">{pct(rec.get('actual_close_next_day'))} <span class="pdir">{rec.get('actual_direction')}</span></td>
          <td>{rec.get('confidence')}</td>
          <td class="r"><span class="badge {hc}">{'命中' if hit else '未中'}</span></td>
        </tr>'''

# ---------------- 恐惧贪婪 8 因子 ----------------
fg = CALC.get("fg_factors", {})
fgw = {"breadth":0.15,"limit_up_down":0.10,"main_flow":0.15,"northbound":0.12,"margin":0.08,"volume":0.10,"vix":0.15,"erp":0.15}
fg_rows = ""
fgnames = {"breadth":"市场广度","limit_up_down":"涨跌停家数","main_flow":"主力资金净流入","northbound":"北向资金净买入",
           "margin":"融资余额变化","volume":"量能亢奋度","vix":"VIX恐慌指数","erp":"股债风险溢价"}
for k in fg:
    miss = "⚠缺失" if k in CALC.get("fg_missing", []) else ""
    fg_rows += f'''<tr><td>{fgnames[k]} <span class="w">{(fgw[k]*100):.0f}%</span></td>
      <td class="r">{fg[k]}{(' '+miss) if miss else ''}</td>
      <td class="r">{fnum(fg[k]*fgw[k],2)}</td></tr>'''

# ---------------- 板块日 K ----------------
kline_html = ""
bias_cls = {"偏多":"up","偏空":"down","中性":"neu"}
for k in CALC.get("kline", []):
    b = k.get("bias", "中性")
    kline_html += f'''<div class="kcard">
      <div class="khead"><span>{k['sector']}</span>
        <span class="kbias {bias_cls.get(b,'neu')}">{b} {pct(k.get('change_0708'))}</span></div>
      <div class="krow"><span>趋势</span><b>{k.get('trend_judg')}</b><i>{k.get('trend_score')}</i></div>
      <div class="krow"><span>量价</span><b>{k.get('vp_judg')}</b><i>{k.get('vp_score')}</i></div>
      <div class="krow"><span>形态</span><b>{k.get('pattern')}</b></div>
      <div class="krow"><span>主力</span><b>{k.get('main_force')}</b></div>
      <div class="krow"><span>收盘</span><b>{k.get('close_signal')}</b></div>
      <div class="knote">{k.get('preclose_meaning')}</div>
    </div>'''

news_html = "".join(f"<li>{n}</li>" for n in C.get("news", [])[:12])

# ---------------- 休市特刊 / 新增分析板块（仅当 calc 含对应字段时渲染，非交易日不影响原逻辑） ----------------
holiday = C.get("holiday") or CALC.get("holiday")
holiday_banner = ""
if holiday:
    holiday_banner = f'''<div class="holiday">📴 <b>休市特刊</b> · {CALC.get('holiday_note','2026-07-11 周六·A股休市，本复盘为周末特刊。')}</div>'''

# 1. 全天资金迁徙路线回顾
migration_html = ""
if CALC.get("migration"):
    m = CALC["migration"]
    seg_html = ""
    for s in m.get("segments", []):
        seg_html += f'''<div class="mig-seg">
          <div class="mig-phase">{s['phase']}</div>
          <div class="mig-flow">{s['flow']}</div>
          <div class="mig-detail">{s['detail']}</div>
          <div class="mig-net">资金：{s.get('net','—')}</div>
          <div class="mig-pos">持仓位置：{s.get('pos','—')}</div></div>'''
    migration_html = f'''<section class="sec" id="migration">
  <h2>🔥 一、全天资金迁徙路线回顾（核心） <span class="tg">▾</span></h2>
  <div class="sec-body">
  <div class="cap">数据基底：{m.get('base_date')}（2026-07-11 周六休市，无实盘，以下为最近交易日真实收盘回顾）。</div>
  <div class="mig-route">{seg_html}</div>
  <div class="keyword">全天关键词：<b>{m.get('keyword')}</b></div>
  <div class="mig-my"><b>你的持仓在迁徙路线中的位置：</b>{m.get('my_position')}</div>
  <div class="mig-verdict"><b>结论（跟减 or 扛）：</b>{m.get('verdict')}</div>
  </div></section>'''

# 2. 主线验证
theme_html = ""
if CALC.get("theme_validate"):
    t = CALC["theme_validate"]
    sub_html = ""
    for s in t.get("subscores", []):
        sub_html += f'''<div class="subscore"><span class="ss-dim">{s['dim']}</span>
        <span class="ss-bar"><i style="width:{s['score']/s['max']*100:.0f}%"></i></span>
        <span class="ss-num">{s['score']}/{s['max']}</span>
        <div class="ss-note">{s.get('note','')}</div></div>'''
    theme_html = f'''<section class="sec" id="theme">
  <h2>🎯 二、主线验证 · 商业航天 <span class="tg">▾</span></h2>
  <div class="sec-body">
  <div class="theme-grade">持续性得分：<b>{t.get('grade')}</b> <span class="sub">（涨停梯队+产业链覆盖+催化力度+资金沉淀）</span></div>
  <div class="subscores">{sub_html}</div>
  <div class="cap"><b>历史参照：</b>{t.get('history_ref')}</div>
  <div class="theme-outlook"><b>下周(07-13)展望：</b>{t.get('outlook')}</div>
  </div></section>'''

# 3. 持仓绩效 · 被抽血量化
holdperf_html = ""
if CALC.get("holdings_perf"):
    hp = CALC["holdings_perf"]
    rows = ""
    for r in hp.get("rows", []):
        rows += f'''<tr><td><b>{r['short']}</b><br><span class="sub">{r['sector']}</span></td>
          <td class="r {cls(r['day_ret'])}">{pct(r['day_ret'])}</td>
          <td class="r {cls(r['alpha'])}"><b>{pct(r['alpha'])}</b></td>
          <td class="r">{r['weight']}%</td>
          <td class="r {cls(r['contrib'])}">{pct(r['contrib'])}</td></tr>'''
    holdperf_html = f'''<section class="sec" id="holdperf">
  <h2>📊 三、持仓绩效 · 被抽血量化（基底 2026-07-10） <span class="tg">▾</span></h2>
  <div class="sec-body">
  <table><tr><th>基金/板块</th><th class="r">当日收益</th><th class="r">α(超额)</th><th class="r">权重</th><th class="r">对账户贡献</th></tr>
  {rows}</table>
  <div class="bleed"><b>半导体被抽血多少？</b> {hp.get('bleed')}</div>
  <div class="cap">{hp.get('note')}</div>
  </div></section>'''

# 4. 决策链路回溯
decision_html = ""
if CALC.get("decision_chain"):
    dc = CALC["decision_chain"]
    steps = ""
    for s in dc.get("steps", []):
        steps += f'''<div class="dec-step dec-{s['verdict']}">
          <div class="dec-phase">{s['phase']}</div>
          <div class="dec-act">{s['action']}</div>
          <div class="dec-verdict">判定：{s['verdict_label']}</div>
          <div class="dec-reason">{s['reason']}</div></div>'''
    decision_html = f'''<section class="sec" id="decision">
  <h2>🔍 四、早间→午盘→尾盘 决策链路回溯 <span class="tg">▾</span></h2>
  <div class="sec-body">{steps}
  <div class="dec-bias"><b>最大偏差归因：</b>{dc.get('bias')}</div>
  <div class="cap">{dc.get('lesson')}</div></div></section>'''

# 5. 次日预案（下个交易日）
nextday_html = ""
if CALC.get("next_day_plan"):
    nd = CALC["next_day_plan"]
    sc = nd.get("scenarios", {})
    kl = "".join(f"<li>{k}</li>" for k in nd.get("key_levels", []))
    ev = "".join(f"<li>{e}</li>" for e in nd.get("events", []))
    nextday_html = f'''<section class="sec" id="nextday">
  <h2>🗓 五、次日预案（下个交易日 {nd.get('next_trading_day')}） <span class="tg">▾</span></h2>
  <div class="sec-body">
  <div class="sub" style="margin-bottom:4px">关键价位 / 事件</div>
  <ul class="news">{kl}</ul>
  <div class="sub" style="margin:8px 0 2px">情景推演</div>
  <div class="scn scn-opt"><b>乐观：</b>{sc.get('optimistic')}</div>
  <div class="scn scn-base"><b>基准：</b>{sc.get('base')}</div>
  <div class="scn scn-pess"><b>悲观：</b>{sc.get('pessimistic')}</div>
  <div class="cap">事件面：{''.join(ev)}</div>
  </div></section>'''

# 命中率·待验证表（休市日无新增回填，展示滚至下交易日的预测）
pending_html = ""
if CALC.get("pending_list"):
    prow = ""
    for p in CALC["pending_list"]:
        prow += f'''<tr><td>{p['target']}</td><td class="r"><span class="pdir">{p['direction']}</span></td>
          <td>{p.get('confidence','')}</td><td class="r"><span class="badge pend">待07-13验证</span></td></tr>'''
    pending_html = f'''<div class="anomaly" style="background:#16242e;border-color:#244a5c;margin-top:12px">
    <b style="color:#7fc8ff">⏳ {CALC.get('pending_count',0)} 条预测待下个交易日(07-13)验证</b>
    <div class="sub">以下预测于 07-10 做出、verify_date=07-11，但 07-11 周六休市无实盘，将于 07-13(周一)收盘回填：</div>
    <table style="margin-top:8px"><tr><th>标的</th><th class="r">预测方向</th><th>置信</th><th class="r">状态</th></tr>{prow}</table></div>'''
hit_holiday_note = CALC.get("hit_holiday_note", "")

# ---------------- 首屏核心摘要（自动派生） ----------------
acct_ret = C.get("account_est_return_0708_pct")
acct_pnl = C.get("account_est_pnl_0708")
total_mv = C.get("total_mv")
overall  = CALC.get("overall_acc")
weighted = CALC.get("weighted_acc")
hits     = CALC.get("hits")
backfilled = CALC.get("backfilled")
fg_idx   = CALC.get("fg_index")
fg_level = CALC.get("fg_level")
semic    = CALC.get("semic_exposure")
top2     = CALC.get("top2_pct")

risks   = [f['name'] for f in C.get("funds", []) if f.get("risk_flag")]
missing = CALC.get("fg_missing", [])

kpi_acct  = (pct(acct_ret), cls(acct_ret), *status(acct_ret, 0, -5))
kpi_hit   = (f"{overall}%", "", *status(overall, 50, 30))
kpi_fg    = (f"{fg_idx}", "", "neu", fg_level)
kpi_semic = (f"{semic}%", "", *semic_status(semic))

kpi_cards = f'''
  <div class="kpi-card {kpi_acct[1]}"><div class="klbl">账户估算日收益</div>
    <div class="kbig {kpi_acct[1]}">{kpi_acct[0]}</div>
    <div class="kstat {kpi_acct[2]}">{kpi_acct[3]} · ≈{fnum(acct_pnl,0)}元</div></div>
  <div class="kpi-card"><div class="klbl">综合预测命中率</div>
    <div class="kbig">{kpi_hit[0]}</div>
    <div class="kstat {kpi_hit[2]}">{kpi_hit[3]} · {'%d/%d累计命中' % (CALC.get('cum_hits', hits), CALC.get('cum_verified', backfilled)) if holiday else '%d/%d命中' % (hits, backfilled)}</div></div>
  <div class="kpi-card"><div class="klbl">收盘恐惧贪婪</div>
    <div class="kbig neu">{kpi_fg[0]}</div>
    <div class="kstat neu">{kpi_fg[3]}</div></div>
  <div class="kpi-card {kpi_semic[1]}"><div class="klbl">半导体/科技暴露</div>
    <div class="kbig {kpi_semic[1]}">{kpi_semic[0]}</div>
    <div class="kstat {kpi_semic[2]}">{kpi_semic[3]} · 前二{top2}%</div></div>
'''

headline = (
    f"账户估算日收益 <b class='{cls(acct_ret)}'>{pct(acct_ret)}</b>（约 {fnum(acct_pnl,2)} 元）；"
    f"综合预测命中率 <b>{overall}%</b>（{hits}/{backfilled} 命中）；"
    f"收盘恐惧贪婪指数 <b>{fg_idx}</b>（{fg_level}）。"
)
headline2 = (
    f"核心问题：半导体/科技类暴露约 <b>{semic}%</b>、前二持仓合计 <b>{top2}%</b> 偏高集中；"
    f"多数看多预测因大盘回调落空。"
)
headline3 = (
    "核心动作：维持防御、严守单基 -8% 硬止损；将高集中度半导体仓位向债券/消费再平衡，"
    "待确认转换后于次日复盘更新结构。"
)

anomalies = []
if semic and semic > 60: anomalies.append(f"半导体暴露 {semic}% 超 60% 阈值")
if top2 and top2 > 50:  anomalies.append(f"前二持仓集中 {top2}%")
if risks: anomalies.append(f"高风险标记：{'，'.join(risks)}")
if missing: anomalies.append(f"{len(missing)}/{len(fg)} 情绪因子源未返回（按中性50计入，指数偏中性）")
anomaly_html = "".join(f"<li>⚠ {a}</li>" for a in anomalies) or "<li>暂无显著异常</li>"

# ==================== v2 首屏四栏核心卡 ====================
acct_label = f"{pct(acct_ret)}" if acct_ret is not None else "—"
acct_cls = cls(acct_ret) if acct_ret is not None else "neu"
card_ret = f'<div class="ev-card-num {acct_cls}">{acct_label}</div><div class="ev-desc">约 {fnum(acct_pnl,2)} 元（板块代理）</div>'

card_issue = f'<ul class="ev-list"><li>半导体暴露 {semic}% 超阈值</li><li>前二持仓集中度 {top2}%</li></ul>' if semic else "—"

weekend_cat = C.get("weekend_catalysts") or CALC.get("weekend_catalysts")
if weekend_cat:
    card_cat = "<ul class='ev-list'>"
    for wc in weekend_cat[:3]:
        card_cat += f"<li>{wc.get('event','')} — {wc.get('impact','')}</li>"
    card_cat += "</ul>"
else:
    card_cat = '<span class="mut">待周末扫描确认</span>'

ev_summary = f'''
<div class="ev-summary">
  <div class="ev-card"><div class="ev-label">当日账户收益</div>{card_ret}</div>
  <div class="ev-card"><div class="ev-label">核心问题</div>{card_issue}</div>
  <div class="ev-card"><div class="ev-label">周末催化影响</div>{card_cat}</div>
  <div class="ev-card ev-action"><div class="ev-label">下日总策略</div>
    <ul class="ev-act">
      <li class="down">🔴 反弹锁利降半导体集中度</li>
      <li class="up">🟢 新主线纳入观察名单</li>
      <li class="neu">⚪ 严守 -8% 硬止损</li>
    </ul>
  </div>
</div>'''

# ==================== 周末催化表格 ====================
catalyst_html = ""
if weekend_cat:
    cat_rows = ""
    for wc in weekend_cat:
        lvl = wc.get("level", "中")
        lvl_cls = {"高":"cat-high","中":"cat-mid","低":"cat-low"}.get(lvl, "cat-mid")
        cat_rows += f'<tr><td><b>{wc.get("event","")}</b></td><td>{wc.get("detail","")}</td><td>{wc.get("impact","")}</td><td><span class="cat-lvl {lvl_cls}">{lvl}</span></td></tr>'
    cat_conclusion = weekend_cat[0].get("conclusion") or ""
    catalyst_html = f'''
<section class="sec" id="catalyst">
  <h2>⑤ 周末全球催化更新 <span class="badge cat-badge">非实盘·周末新增</span> <span class="tg">▾</span></h2>
  <div class="sec-body">
  <div class="cap" style="margin-bottom:6px">以下为周末新产生的市场信息，非实盘行情，影响等级用于评估周一开盘情绪。</div>
  <table><tr><th>事件</th><th>核心内容</th><th>对持仓影响</th><th>影响等级</th></tr>{cat_rows}</table>
  {('<div class="cat-conclusion">📌 核心结论：'+cat_conclusion+'</div>') if cat_conclusion else ""}
  </div>
</section>'''

# ==================== 结构化决策链路 ====================
dc = CALC.get("decision_chain", {})
dec_html = ""
if dc:
    hits_items = dc.get("hits") or []
    misses_items = dc.get("misses") or []
    root_causes = dc.get("root_causes") or []
    improvements = dc.get("improvements") or []
    def blist(items, tag):
        if not items:
            return '<div class="mut">无</div>'
        return "".join(f'<li class="dec-item dec-{tag}">{i}</li>' for i in items)
    dec_html = f'''
<section class="sec" id="decision">
  <h2>④ 决策链路回溯 <span class="badge" style="background:rgba(74,168,255,.15);color:#4aa8ff">复盘迭代</span> <span class="tg">▾</span></h2>
  <div class="sec-body">
    <div class="dec-grid">
      <div class="dec-col dec-hit"><b class="dec-col-hl down">✅ 命中与应对得当</b><ul>{blist(hits_items, "hit")}</ul></div>
      <div class="dec-col dec-miss"><b class="dec-col-hl up">❌ 失误与偏差</b><ul>{blist(misses_items, "miss")}</ul></div>
      <div class="dec-col dec-root"><b class="dec-col-hl neu">🔍 根因分析</b><ul>{blist(root_causes, "root")}</ul></div>
      <div class="dec-col dec-impr"><b class="dec-col-hl acc">🛠️ 改进措施</b><ul>{blist(improvements, "impr")}</ul></div>
    </div>
    {f'<div class="dec-bias"><b>最大偏差归因：</b>{dc.get("bias","")}</div>' if dc.get("bias") else ""}
    {f'<div class="cap">{dc.get("lesson","")}</div>' if dc.get("lesson") else ""}
  </div>
</section>'''

# ==================== 结构化三情景预案 ====================
nd = CALC.get("next_day_plan", {})
nextday_html = ""
if nd:
    sc = nd.get("scenarios", {})
    kl = "".join(f"<li>{k}</li>" for k in nd.get("key_levels", []))
    # 三情景触发式
    trig_opt = sc.get("trigger_optimistic") or sc.get("optimistic","")
    trig_base = sc.get("trigger_base") or sc.get("base","")
    trig_pess = sc.get("trigger_pessimistic") or sc.get("pessimistic","")
    act_opt = sc.get("action_optimistic") or ""
    act_base = sc.get("action_base") or ""
    act_pess = sc.get("action_pessimistic") or ""
    nextday_html = f'''
<section class="sec" id="nextday">
  <h2>⑥ 下交易日（{nd.get("next_trading_day","周一")}）操作预案 <span class="tg">▾</span></h2>
  <div class="sec-body">
  <div class="sub" style="margin-bottom:6px">核心观察阈值：{" · ".join(kl) if kl else "—"}</div>
  <div class="scn-grid">
    <div class="scn scn-opt"><b>🟢 乐观</b><br><span class="scn-trig">触发：{trig_opt}</span><br><span class="scn-act">操作：{act_opt}</span></div>
    <div class="scn scn-base"><b>🟡 基准</b><br><span class="scn-trig">触发：{trig_base}</span><br><span class="scn-act">操作：{act_base}</span></div>
    <div class="scn scn-pess"><b>🔴 悲观</b><br><span class="scn-trig">触发：{trig_pess}</span><br><span class="scn-act">操作：{act_pess}</span></div>
  </div>
  </div>
</section>'''

# ---------------- 底部行动闭环 ----------------
action_items = ""
for title, desc, sug in CALC.get("rebalance", []):
    pr = priority_map.get(title, "中")
    action_items += f'''<div class="act pr-{pr}">
      <span class="pbadge p-{pr}">{pr}</span>
      <div><b>{title}</b><div class="act-d">{sug}</div>
      <div class="act-meta">责任人：策略自动化 · 跟进：次日复盘复核</div></div></div>'''

risk_items = ""
if risks:
    risk_items += f'<div class="ritem bad">高风险持仓标记（{", ".join(risks)}）— 需严守 -8% 硬止损，不扛单。</div>'
if semic and semic > 60:
    risk_items += f'<div class="ritem bad">行业集中风险：半导体/科技暴露 {semic}% 超阈值，需向债券/消费再平衡（目标≤60%）。</div>'
if top2 and top2 > 50:
    risk_items += f'<div class="ritem warn">集中度风险：前二持仓 {top2}%，单基东方人工智能主题超 30% 上限。</div>'
if missing:
    risk_items += f'<div class="ritem warn">数据缺口：{len(missing)}/{len(fg)} 情绪因子源未返回，综合情绪指数置信度下降。</div>'
risk_items = risk_items or '<div class="ritem ok">暂无待跟进高风险项。</div>'

# ---------------- 图表数据 ----------------
chart_alpha = [{"n": f.get("short") or f.get("name"), "a": f.get("alpha")}
               for f in C.get("funds", []) if isinstance(f.get("alpha"), (int, float))]
CHARTS = json.dumps({"alpha": chart_alpha}, ensure_ascii=False)

GEN_TIME = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
sh_chg = C.get("indices", {}).get("上证指数", {}).get("change_pct")

# ================= HTML 拼装 =================
# HEAD：纯字符串（CSS/JS 之外的静态部分），__DATE__ 占位稍后替换
HEAD = """<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>基金晚间复盘 · __DATE__</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
:root{--bg:#0e1117;--bg2:#161b24;--card:#1c232e;--line:#2a3340;--tx:#e6edf3;--mut:#8b98a9;--up:#f5564d;--down:#26c281;--neu:#d9a441;--acc:#4aa8ff;--ok:#26c281;--warn:#d9a441;--bad:#f5564d;}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--tx);font-family:-apple-system,"PingFang SC","Microsoft YaHei",Segoe UI,sans-serif;line-height:1.65;padding:0 0 60px}
.wrap{max-width:1080px;margin:0 auto;padding:0 18px}
.up{color:var(--up)}.down{color:var(--down)}.neu{color:var(--neu)}
.nav{position:sticky;top:0;z-index:50;background:rgba(14,17,23,.92);backdrop-filter:blur(8px);border-bottom:1px solid var(--line);display:flex;gap:4px;flex-wrap:wrap;padding:8px 14px;overflow-x:auto}
.nav a{color:var(--mut);text-decoration:none;font-size:12.5px;padding:5px 10px;border-radius:7px;white-space:nowrap}
.nav a:hover{color:var(--tx);background:var(--card)}
.nav .brand{color:var(--acc);font-weight:700;margin-right:6px}
h1{font-size:25px;letter-spacing:.5px;margin:22px 0 4px}
h2{font-size:18px;margin:30px 0 12px;padding-left:11px;border-left:4px solid var(--acc);color:#fff;cursor:pointer;user-select:none}
h2 .tg{float:right;color:var(--mut);font-size:14px;font-weight:400}
.sub{color:var(--mut);font-size:12px}
.meta{color:var(--mut);font-size:12.5px;margin-top:6px}
.sec-body{margin-top:6px}
.sec.collapsed .sec-body{display:none}
.summary{background:linear-gradient(135deg,#19222e,#161b24);border:1px solid var(--line);border-radius:14px;padding:20px 22px;margin:16px 0}
.summary h2{border:none;padding:0;margin:0 0 10px;cursor:default}
.hl{font-size:14.5px;line-height:1.8;margin:6px 0}
.hl b{color:#fff}
.kpi-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:16px 0}
.kpi-card{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--line);border-radius:10px;padding:13px 15px}
.kpi-card.up{border-left-color:var(--up)}.kpi-card.down{border-left-color:var(--down)}.kpi-card.neu{border-left-color:var(--neu)}
.klbl{color:var(--mut);font-size:12px}
.kbig{font-size:27px;font-weight:800;margin:3px 0}
.kstat{font-size:12px;color:var(--mut)}
.kstat.ok{color:var(--ok)}.kstat.warn{color:var(--warn)}.kstat.bad{color:var(--bad)}
.anomaly{background:#1d1414;border:1px solid #6b2b2b;border-radius:10px;padding:12px 16px;margin-top:12px}
.anomaly ul{margin:4px 0 0 18px;font-size:13px;color:#ffb4ae}
.cards{display:flex;gap:12px;flex-wrap:wrap;margin:12px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;flex:1;min-width:150px}
.card.sm .lbl{color:var(--mut);font-size:12px}
.card.sm .big{font-size:22px;font-weight:700;margin:4px 0}
.acct{display:flex;gap:14px;flex-wrap:wrap;align-items:stretch;margin:12px 0}
.acct .card{flex:1;min-width:180px}.acct .big{font-size:26px;font-weight:800}
table{width:100%;border-collapse:collapse;margin:10px 0;font-size:13px}
th,td{padding:9px 8px;border-bottom:1px solid var(--line);text-align:left}
th{color:var(--mut);font-weight:600;font-size:12px;background:var(--bg2)}
td.r,th.r{text-align:right}
.chips{max-width:240px}
.chip{display:inline-block;background:#222b38;border:1px solid var(--line);border-radius:6px;padding:2px 7px;margin:2px;font-size:11px;color:#cdd7e2}
.risk{background:#3a1d1d;color:#ff7a72;border:1px solid #6b2b2b;border-radius:5px;padding:1px 6px;font-size:11px;margin-left:5px}
.dorm{background:#1d2433;color:#8fb6ff;border:1px solid #2c3c5c;border-radius:5px;padding:1px 6px;font-size:11px;margin-left:5px}
.cap{font-size:12px;color:var(--mut);margin:6px 0 2px;padding-left:2px;border-left:2px solid var(--line)}
.reb{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--neu);border-radius:8px;padding:11px 14px;margin:9px 0}
.reb-t{font-weight:700;color:#fff}.reb-d{font-size:13px;margin:4px 0;color:#d4dde6}.reb-s{font-size:13px;color:var(--acc)}
.pbadge{font-size:11px;padding:1px 7px;border-radius:20px;margin-left:6px;font-weight:700}
.p-高{background:#3a1d1d;color:#ff7a72;border:1px solid #6b2b2b}
.p-中{background:#2a2415;color:var(--neu);border:1px solid #5c4a1d}
.p-低{background:#16242e;color:#7fc8ff;border:1px solid #244a5c}
.act{display:flex;gap:10px;background:var(--card);border:1px solid var(--line);border-radius:8px;padding:11px 14px;margin:8px 0;align-items:flex-start}
.act .pbadge{margin:2px 0 0}
.act-d{font-size:13px;color:#d4dde6;margin-top:3px}
.act-meta{font-size:11.5px;color:var(--mut);margin-top:4px}
.ritem{font-size:13px;padding:9px 13px;border-radius:8px;margin:7px 0;border:1px solid var(--line)}
.ritem.ok{background:#143026;color:#9ff0c4;border-color:#1f6e47}
.ritem.warn{background:#2a2415;color:#f0d79a;border-color:#5c4a1d}
.ritem.bad{background:#3a1717;color:#ffb0a8;border-color:#6b2b2b}
.badge{padding:2px 9px;border-radius:20px;font-size:12px;font-weight:700}
.badge.hit{background:#143a28;color:#3fe39a;border:1px solid #1f6e47}
.badge.miss{background:#3a1717;color:#ff8a82;border:1px solid #6b2b2b}
.pdir{font-size:11px;padding:1px 6px;border-radius:4px;background:#222b38;color:var(--mut)}
.kcards{display:flex;gap:12px;flex-wrap:wrap}
.kcard{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px;flex:1;min-width:185px}
.khead{display:flex;justify-content:space-between;align-items:center;font-weight:700;margin-bottom:8px}
.kbias{font-size:12px;padding:2px 8px;border-radius:6px}
.kbias.up{background:#3a1d1d;color:var(--up)}.kbias.down{background:#143a28;color:var(--down)}.kbias.neu{background:#2a2415;color:var(--neu)}
.krow{display:flex;gap:8px;font-size:12px;padding:3px 0;border-bottom:1px dashed #232c38}
.krow span{color:var(--mut);width:38px;flex:none}.krow b{flex:1;font-weight:500}.krow i{color:var(--mut);font-style:normal}
.knote{font-size:12px;color:#cdd7e2;margin-top:7px;line-height:1.5}
.gauge{display:flex;align-items:center;gap:18px;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px;margin:10px 0}
.gnum{font-size:46px;font-weight:800;min-width:120px;text-align:center}
.glbl{font-size:15px;font-weight:700}.gbar{flex:1;height:14px;background:linear-gradient(90deg,#f5564d,#d9a441,#26c281);border-radius:8px;position:relative}
.gbar i{position:absolute;top:-5px;width:3px;height:24px;background:#fff;border-radius:2px}
ul.news{margin:8px 0 0 18px;font-size:13px;color:#d4dde6}
ul.news li{margin:5px 0}
.foot{margin-top:36px;padding-top:16px;border-top:1px solid var(--line);font-size:12px;color:var(--mut)}
.totop{position:fixed;right:18px;bottom:20px;width:42px;height:42px;border-radius:50%;background:var(--acc);color:#06223f;border:none;font-size:20px;cursor:pointer;display:none;z-index:60;box-shadow:0 2px 8px rgba(0,0,0,.4)}
.totop.show{display:block}
.chart-box{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px;margin:10px 0;height:320px}
@media(max-width:680px){.kpi-grid{grid-template-columns:repeat(2,1fr)}.cards,.acct,.kcards{flex-direction:column}h1{font-size:21px}}
@media print{body{background:#fff;color:#000}.nav,.totop{display:none!important}.sec.collapsed .sec-body{display:block}.card,.reb,.kcard,.ritem,.act,.gauge,.chart-box{break-inside:avoid;border-color:#ccc}.up{color:#c0392b!important}.down{color:#1e7e44!important}.neu{color:#b8860b!important}h2{color:#000;border-left-color:#333}}
.holiday{background:#1a2230;border:1px solid #2c3c5c;border-left:4px solid #4aa8ff;border-radius:10px;padding:12px 16px;margin:14px 0;font-size:13.5px;color:#cfe2f5;line-height:1.7}
.holiday b{color:#7fc8ff}
.mig-route{display:flex;flex-direction:column;gap:10px;margin:10px 0}
.mig-seg{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:11px 14px;position:relative}
.mig-seg:before{content:"";position:absolute;left:18px;top:-10px;width:2px;height:10px;background:var(--line)}
.mig-phase{font-size:12px;color:var(--acc);font-weight:700}
.mig-flow{font-size:15px;font-weight:700;margin:3px 0;color:#fff}
.mig-detail{font-size:13px;color:#d4dde6;line-height:1.6}
.mig-net{font-size:12px;color:#cdd7e2;margin-top:4px}
.mig-pos{font-size:12px;color:var(--neu);margin-top:2px}
.keyword{background:#16242e;border:1px solid #244a5c;border-radius:8px;padding:9px 13px;margin:10px 0;font-size:13.5px}
.mig-my{font-size:13px;color:#d4dde6;margin:6px 0}
.mig-verdict{font-size:13px;color:#cfe2f5;margin-top:4px;padding:8px 12px;background:#143026;border:1px solid #1f6e47;border-radius:8px}
.theme-grade{font-size:15px;margin:8px 0;color:#fff}.theme-grade b{color:var(--neu);font-size:20px}
.subscores{margin:10px 0}
.subscore{margin:8px 0}
.ss-dim{display:inline-block;width:90px;font-weight:700;color:#fff;font-size:13px}
.ss-bar{display:inline-block;width:160px;height:10px;background:#222b38;border-radius:6px;vertical-align:middle;overflow:hidden}
.ss-bar i{display:block;height:100%;background:linear-gradient(90deg,#d9a441,#26c281)}
.ss-num{display:inline-block;width:54px;text-align:right;color:var(--neu);font-weight:700;font-size:12px}
.ss-note{font-size:12px;color:#cdd7e2;margin:2px 0 0 90px;line-height:1.5}
.theme-outlook{font-size:13.5px;color:#cfe2f5;margin-top:10px;padding:9px 13px;background:#16242e;border:1px solid #244a5c;border-radius:8px;line-height:1.65}
.bleed{font-size:13.5px;color:#ffb0a8;margin:10px 0;padding:10px 13px;background:#3a1717;border:1px solid #6b2b2b;border-radius:8px;line-height:1.7}
.dec-step{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--mut);border-radius:8px;padding:10px 14px;margin:9px 0}
.dec-step.dec-hit{border-left-color:var(--down)}
.dec-step.dec-miss{border-left-color:var(--up)}
.dec-phase{font-weight:700;color:var(--acc);font-size:13px}
.dec-act{font-size:13px;color:#d4dde6;margin:4px 0;line-height:1.6}
.dec-verdict{font-size:12.5px;color:var(--neu);font-weight:700}
.dec-reason{font-size:12px;color:#cdd7e2;line-height:1.5}
.dec-bias{font-size:13.5px;color:#ffb0a8;margin:10px 0;padding:10px 13px;background:#3a1717;border:1px solid #6b2b2b;border-radius:8px;line-height:1.7}
.scn{font-size:13px;padding:9px 13px;border-radius:8px;margin:7px 0;line-height:1.6}
.scn b{margin-right:4px}
.scn-opt{background:#143026;color:#9ff0c4;border:1px solid #1f6e47}
.scn-base{background:#2a2415;color:#f0d79a;border:1px solid #5c4a1d}
.scn-pess{background:#3a1717;color:#ffb0a8;border:1px solid #6b2b2b}
.badge.pend{background:#16242e;color:#7fc8ff;border:1px solid #244a5c}
.hit-note{font-size:12.5px;color:var(--mut);margin:6px 0}
/* v2 新样式：四栏结论卡 + 催化表格 + 结构化决策 + 三情景 + 待办表 */
.ev-summary{display:grid;grid-template-columns:1fr 1fr 1fr 1.2fr;gap:10px;margin:14px 0}
.ev-card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:13px 15px;border-left:4px solid var(--line)}
.ev-card.ev-action{border-left-color:var(--acc);background:rgba(74,168,255,.06)}
.ev-label{color:var(--mut);font-size:11.5px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px}
.ev-card-num{font-size:24px;font-weight:800;margin:2px 0}.ev-desc{font-size:11.5px;color:var(--mut)}
.ev-list{list-style:none;padding:0;margin:0;font-size:13px;line-height:1.7}.ev-act{list-style:none;padding:0;margin:0;font-size:13px;line-height:1.9}
.cat-badge{background:rgba(74,168,255,.12);color:#4aa8ff;font-size:10px;margin-left:4px}
.cat-lvl{font-size:11px;padding:1px 8px;border-radius:12px;font-weight:700}
.cat-high{background:rgba(245,86,77,.16);color:var(--up)}.cat-mid{background:rgba(217,164,65,.16);color:var(--neu)}.cat-low{background:rgba(139,152,169,.16);color:var(--mut)}
.cat-conclusion{font-size:13px;color:#cfe2f5;margin-top:10px;padding:9px 12px;background:rgba(74,168,255,.08);border:1px solid rgba(74,168,255,.25);border-radius:8px}
.dec-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:8px 0}
.dec-col{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px 12px}
.dec-col-hl{font-size:13px;display:block;margin-bottom:6px;border-bottom:1px solid var(--line);padding-bottom:4px}
.dec-col ul{list-style:none;padding:0;margin:0;font-size:12.5px;line-height:1.6}
.dec-item{padding:4px 0;border-bottom:1px dashed rgba(42,51,64,.5)}.dec-item:last-child{border:none}
.dec-item.hit{color:var(--down)}.dec-item.miss{color:var(--up)}.dec-item.root{color:var(--neu)}.dec-item.impr{color:#7fc8ff}
.scn-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin:8px 0}
.scn-trig{font-size:12px;color:#aab4c0;display:block;margin:4px 0}.scn-act{font-size:12.5px;color:#fff;display:block;margin:4px 0}
.todo-table-head{display:grid;grid-template-columns:72px 1fr 1.5fr;gap:8px;padding:6px 10px;color:var(--mut);font-size:12px;font-weight:700;background:var(--bg2);border-radius:8px;margin-bottom:4px}
.pr-高 .pbadge{background:#3a1d1d;color:#ff7a72}.pr-中 .pbadge{background:#2a2415;color:var(--neu)}.pr-低 .pbadge{background:#16242e;color:#7fc8ff}
@media(max-width:680px){.ev-summary{grid-template-columns:1fr 1fr}.dec-grid{grid-template-columns:1fr}.scn-grid{grid-template-columns:1fr}.kpi-grid{grid-template-columns:repeat(2,1fr)}.cards,.acct,.kcards{flex-direction:column}h1{font-size:21px}}
<body>
<nav class="nav"><span class="brand">📊 复盘</span>
<a href="#summary">摘要</a><a href="#overview">概览</a><a href="#flow">资金流</a><a href="#alpha">α基本面</a>
<a href="#rebalance">调仓</a><a href="#hit">命中率</a><a href="#sentiment">情绪</a><a href="#kline">板块K</a>
<a href="#news">新闻</a><a href="#action">行动闭环</a>
<a href="../../index.html" style="margin-left:auto">← 历史复盘</a></nav>
<div class="wrap">
"""

# BODY：f-string，仅含 HTML（不含 <script>），单花括号即占位符
BODY = f'''
<h1>📊 每日基金晚间复盘</h1>
<div class="meta">日期 <b>{DATE}</b> · 数据截止：最近交易日收盘 + 周末扫描 · 生成 {GEN_TIME} · 数据源 <b>neodata-financial-search</b> · 仅供参考，不构成投资建议</div>

{ev_summary}

<section class="sec" id="overview">
  <h2>① 当日行情与资金复盘 <span class="tg">▾</span></h2>
  <div class="sec-body">
  <div class="cards">{idx_html}</div>
  <div class="acct">
    <div class="card"><div class="lbl">账户估算日收益（板块代理）</div>
      <div class="big {cls(acct_ret)}">{pct(acct_ret)}</div>
      <div class="{cls(acct_ret)}">≈ {fnum(acct_pnl,2)} 元（持仓市值 {fnum(total_mv,2)} 元）</div></div>
    <div class="card"><div class="lbl">策略</div>
      <div style="font-size:15px;margin-top:6px">进攻型 · 本金 15000 · 单基≤30% · 止损-8% / 止盈+15%</div>
      <div class="sub" style="margin-top:6px">活跃持仓 {sum(1 for f in C.get('funds',[]) if f.get('status')=='active')} 只 · 半导体暴露约 {semic}%</div></div>
    <div class="card"><div class="lbl">全市场广度</div>
      <div style="font-size:18px;margin-top:6px" class="down">涨跌比 {CALC.get('breadth_ratio')}</div>
      <div class="sub">极致分化，个股普跌</div></div>
  </div>
  <div class="cap">解读：账户收益由关联板块真实收盘代理，大盘回调背景下整体小幅承压；广度显示个股普跌、情绪偏冷。</div>
  </div>
</section>

{migration_html}
{theme_html}
{holdperf_html}
{decision_html}

<section class="sec" id="flow">
  <h2>② 资金流（资金面） <span class="tg">▾</span></h2>
  <div class="sec-body">
  <div class="card" style="margin:10px 0">
    <div style="font-weight:700;margin-bottom:6px">行业主力资金</div>
    <ul class="news">{''.join(f'<li>{n}</li>' for n in CALC.get('mainflow_notes',[]))}</ul>
    <div class="sub" style="margin-top:8px">北向资金：{CALC.get('northbound_status')}</div>
  </div>
  <div class="cap">解读：电子(含半导体/存储)主力净流出、计算机/通信受捧，内部分化明显。</div>
  </div>
</section>

{catalyst_html}
{nextday_html}

<section class="sec" id="rebalance">
  <h2>⑦ 调仓与风控待办清单 <span class="tg">▾</span></h2>
  <div class="sec-body">
  <div class="sub" style="margin-bottom:6px">α = 基金实际日收益 − 关联基准收益（越大越好）。排名/重仓为 neodata 返回，缺失标注 —。</div>
  <table>
  <tr><th>基金 / 板块</th><th class="r">净值(元)</th><th class="r">日收益</th><th class="r">年内收益</th><th class="r">α</th><th class="r">同类排名</th><th class="r">板块代理</th><th>十大重仓(前6)</th></tr>
  {fund_rows}
  </table>
  <div class="cap">解读：α 为正代表跑赢基准；多数基金近日 α 承压，仅少数(如纳指100联接、财通成长)保持正 α。</div>
  <div class="chart-box"><canvas id="alphaChart"></canvas></div>
  <div class="cap">图表：各基金 α(相对基准, %)，正α红/负α绿，数值直接标注。</div>
  </div>
</section>

<section class="sec" id="rebalance">
  <h2>四、调仓建议（风险与应对） <span class="tg">▾</span></h2>
  <div class="sec-body">{reb_html}
  <div class="cap">解读：调仓主线为「降集中度 + 压半导体暴露 + 严守硬止损」，属防御型再平衡。</div>
  </div>
</section>

{nextday_html}

<section class="sec" id="hit">
  <h2>五、预测命中率（问题归因） <span class="tg">▾</span></h2>
  <div class="sec-body">
  <div class="cards">
    <div class="card sm"><div class="lbl">总体命中率</div><div class="big {cls((overall or 0)-50)}">{overall}%</div><div class="sub">{hits}/{backfilled} 命中</div></div>
    <div class="card sm"><div class="lbl">置信加权命中率</div><div class="big neu">{weighted}%</div><div class="sub">权重和 {fnum(CALC.get('w_total'),1)}</div></div>
    <div class="card sm"><div class="lbl">时段</div><div class="big" style="font-size:20px">evening</div><div class="sub">21:30 复盘</div></div>
  </div>
  <div class="anomaly" style="background:#1d1814;border-color:#5c4a1d"><b style="color:#f0d79a">📘 为何多数看多落空</b><ul><li>07-07 晚间普遍看多，但 {DATE} 大盘回调（上证{sh_chg}%、半导体近平、港股创新药-1.39%、仅煤炭+1.2% 逆势），致多数看多预测落空；仅震荡判断命中。</li></ul></div>
  <table>
  <tr><th>预测标的</th><th class="r">预测方向</th><th class="r">实际(板块代理)</th><th>置信</th><th class="r">结果</th></tr>
  {pred_rows}
  </table>
  {pending_html}
  <div class="hit-note">{hit_holiday_note}</div>
  <div class="cap">解读：命中率偏低主因是大盘系统性回调，非个基基本面恶化；情绪恐惧+高集中度下不宜加仓。</div>
  </div>
</section>

<section class="sec" id="sentiment">
  <h2>六、收盘情绪校准 · 恐惧贪婪指数 <span class="tg">▾</span></h2>
  <div class="sec-body">
  <div class="gauge">
    <div class="gnum neu">{fg_idx}</div>
    <div style="flex:1">
      <div class="glbl neu">{fg_level}</div>
      <div class="gbar"><i style="left:{fg_idx}%"></i></div>
      <div class="sub" style="margin-top:6px">{CALC.get('fg_action')}</div>
    </div>
  </div>
  <table>
  <tr><th>情绪因子</th><th class="r">评分(0-100)</th><th class="r">加权贡献</th></tr>
  {fg_rows}
  <tr><td><b>综合恐惧贪婪指数</b></td><td class="r"><b class="neu">{fg_idx}</b></td><td class="r">—</td></tr>
  </table>
  <div class="cap">解读：{len(missing)}/{len(fg)} 因子源未返回按中性计入，指数被拉向中性；真实广度显示情绪偏恐惧。</div>
  </div>
</section>

<section class="sec collapsed" id="kline">
  <h2>七、板块日K信号（模型研判） <span class="tg">▾</span></h2>
  <div class="sec-body">
  <div class="kcards">{kline_html}</div>
  <div class="cap">解读：板块多偏空/中性，仅煤炭逆势偏多；⚠ 形态与主力行为为模型推断，仅供参考。</div>
  </div>
</section>

<section class="sec collapsed" id="news">
  <h2>八、新闻面（行业/政策/重仓动态） <span class="tg">▾</span></h2>
  <div class="sec-body">
  <ul class="news">{news_html}</ul>
  <div class="cap">解读：半导体国产替代与港股创新药政策催化并存，但高估值与获利盘压制短期表现。</div>
  </div>
</section>

<section class="sec" id="action">
  <h2>🔚 底部行动闭环 <span class="tg">▾</span></h2>
  <div class="sec-body">
  <h3 style="font-size:15px;margin:6px 0 8px;color:#fff">① 明日待办（按优先级）</h3>
  {action_items}
  <h3 style="font-size:15px;margin:18px 0 8px;color:#fff">② 待跟进风险项</h3>
  {risk_items}
  </div>
</section>

<div class="foot">
数据来源：<b>neodata-financial-search</b>（已连接）。指数/板块/基金净值为源返回真实值；基金官方净值最新为最近可得，当日变动以关联板块真实收盘作估值代理；北向/规模/港股创新药QDII排名等字段源未返回或误匹配，已标注。<br>
⚠️ 本报告由自动化系统生成，所有内容仅供参考，不构成任何投资建议。市场有风险，投资需谨慎。
</div>
</div>
'''

# TAIL：纯字符串（含 <script>），普通字符串里 { } 可直接书写，无需转义
TAIL = """
<button class="totop" id="totop" onclick="window.scrollTo({top:0,behavior:'smooth'})">↑</button>
<script>
const CHARTS = __CHARTS__;
document.querySelectorAll('h2').forEach(function(h){
  h.addEventListener('click', function(){
    var s = h.closest('.sec'); if(!s) return;
    s.classList.toggle('collapsed');
    var t = h.querySelector('.tg'); if(t) t.textContent = s.classList.contains('collapsed') ? '▸' : '▾';
  });
});
var tb = document.getElementById('totop');
window.addEventListener('scroll', function(){ tb.classList.toggle('show', window.scrollY > 400); });
if (CHARTS.alpha && CHARTS.alpha.length) {
  var lbl = { id:'lbl', afterDatasetsDraw: function(c){
    var ctx = c.ctx; var m = c.getDatasetMeta(0);
    m.data.forEach(function(bar, i){
      var v = c.data.datasets[0].data[i];
      ctx.fillStyle = '#cdd7e2'; ctx.font = '11px sans-serif'; ctx.textAlign = 'center';
      ctx.fillText(v, bar.x, bar.y - 4);
    });
  }};
  new Chart(document.getElementById('alphaChart'), {
    type: 'bar',
    data: { labels: CHARTS.alpha.map(function(d){return d.n;}),
            datasets: [ { data: CHARTS.alpha.map(function(d){return d.a;}),
                         backgroundColor: CHARTS.alpha.map(function(d){return d.a>=0?'#f5564d':'#26c281';}),
                         borderRadius: 4 } ] },
    options: { indexAxis:'y', responsive:true, maintainAspectRatio:false,
      plugins: { legend: { display:false } },
      scales: { x: { grid:{color:'#2a3340'}, ticks:{color:'#8b98a9'} },
                y: { grid:{color:'#2a3340'}, ticks:{color:'#cdd7e2'} } } },
    plugins: [lbl]
  });
}
</script>
</body></html>
"""

HTML = HEAD.replace("__DATE__", DATE) + BODY + TAIL.replace("__CHARTS__", CHARTS)

out = os.path.join(BASE, "reports", DATE, f"evening-review-{DATE}.html")
os.makedirs(os.path.dirname(out), exist_ok=True)
open(out, "w", encoding="utf-8").write(HTML)
print("wrote", out, len(HTML), "bytes")
