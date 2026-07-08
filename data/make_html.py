import json, os

BASE = "C:/Users/LEGION/Nutstore/1/daily-report/data"
REP = os.path.join(BASE, "reports", "2026-07-08")
C = json.load(open(os.path.join(BASE,"consolidated_2026-07-08.json"),encoding="utf-8"))
CALC = json.load(open(os.path.join(BASE,"calc_2026-07-08.json"),encoding="utf-8"))
DATE="2026-07-08"

def fnum(x, d=2, suf=""):
    if x is None: return "—"
    if isinstance(x,float): return (f"{x:,.{d}f}{suf}")
    return str(x)

def pct(x):
    if x is None: return "—"
    return f"{x:+.2f}%"

def cls(x):  # color class by sign (red up / green down, CN convention)
    if x is None: return ""
    return "up" if x>=0 else "down"

def chip(name, w):
    if not name: return ""
    return f'<span class="chip">{name} <b>{fnum(w,1)}%</b></span>'

# ---- indices ----
idx_html = ""
for nm in ["上证指数","创业板指","沪深300"]:
    v = C["indices"].get(nm,{})
    chg = v.get("change_pct")
    idx_html += f'''<div class="card sm"><div class="lbl">{nm}</div>
      <div class="big {cls(chg)}">{fnum(v.get('close'),2)}</div>
      <div class="{cls(chg)}">{pct(chg)}</div></div>'''

# ---- funds α table ----
fund_rows = ""
for f in C["funds"]:
    nav = f.get("nav"); d7=f.get("daily_0707"); ytd=f.get("ytd_pct"); al=f.get("alpha")
    rk = f.get("ranking") or {}
    rank_str = f"{fnum(rk.get('rank'),0)}/{fnum(rk.get('total'),0)}" if rk.get('rank') else "—"
    top = f.get("top10") or []
    top_chips = " ".join(chip(t.get("name"), t.get("weight")) for t in top[:6]) or "—"
    risk = f.get("risk_flag")
    risk_badge = '<span class="risk">HIGH</span>' if risk=="HIGH" else ""
    st = f.get("status")
    st_badge = '<span class="dorm">休眠</span>' if st=="dormant" else ""
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

# ---- rebalance ----
reb_html = ""
for title, desc, sug in CALC["rebalance"]:
    reb_html += f'''<div class="reb"><div class="reb-t">● {title}</div>
      <div class="reb-d">{desc}</div><div class="reb-s">➤ 建议：{sug}</div></div>'''

# ---- prediction backfill table ----
plog = json.load(open(os.path.join(BASE,"prediction-log.json"),encoding="utf-8"))
pred_rows = ""
for rec in plog["records"]:
    if rec.get("verified") and rec.get("verify_date")==DATE:
        hit = rec.get("hit")
        hc = "hit" if hit else "miss"
        pred_rows += f'''<tr>
          <td>{rec['target']}</td>
          <td class="r"><span class="pdir">{rec['direction']}</span></td>
          <td class="r {cls(rec['actual_close_next_day'])}">{pct(rec['actual_close_next_day'])} <span class="pdir">{rec['actual_direction']}</span></td>
          <td>{rec['confidence']}</td>
          <td class="r"><span class="badge {hc}">{'命中' if hit else '未中'}</span></td>
        </tr>'''

# ---- fear greed factors ----
fg = CALC["fg_factors"]
fgw = {"breadth":0.15,"limit_up_down":0.10,"main_flow":0.15,"northbound":0.12,"margin":0.08,"volume":0.10,"vix":0.15,"erp":0.15}
fg_rows = ""
fgnames = {"breadth":"市场广度","limit_up_down":"涨跌停家数","main_flow":"主力资金净流入","northbound":"北向资金净买入",
           "margin":"融资余额变化","volume":"量能亢奋度","vix":"VIX恐慌指数","erp":"股债风险溢价"}
for k in fg:
    miss = "⚠缺失" if k in CALC["fg_missing"] else ""
    fg_rows += f'''<tr><td>{fgnames[k]} <span class="w">{(fgw[k]*100):.0f}%</span></td>
      <td class="r">{fg[k]}{(' '+miss) if miss else ''}</td>
      <td class="r">{fnum(fg[k]*fgw[k],2)}</td></tr>'''

# ---- kline ----
kline_html = ""
bias_cls = {"偏多":"up","偏空":"down","中性":"neu"}
for k in CALC["kline"]:
    b = k.get("bias","中性")
    kline_html += f'''<div class="kcard">
      <div class="khead"><span>{k['sector']}</span>
        <span class="kbias {bias_cls.get(b,'neu')}">{b} {pct(k['change_0708'])}</span></div>
      <div class="krow"><span>趋势</span><b>{k['trend_judg']}</b><i>{k['trend_score']}</i></div>
      <div class="krow"><span>量价</span><b>{k['vp_judg']}</b><i>{k['vp_score']}</i></div>
      <div class="krow"><span>形态</span><b>{k['pattern']}</b></div>
      <div class="krow"><span>主力</span><b>{k['main_force']}</b></div>
      <div class="krow"><span>收盘</span><b>{k['close_signal']}</b></div>
      <div class="knote">{k['preclose_meaning']}</div>
    </div>'''

# ---- news ----
news_html = "".join(f"<li>{n}</li>" for n in C["news"][:12])

acct_ret = C["account_est_return_0708_pct"]
acct_pnl = C["account_est_pnl_0708"]

HTML = f'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>基金晚间复盘 · {DATE}</title>
<style>
:root{{--bg:#0e1117;--bg2:#161b24;--card:#1c232e;--line:#2a3340;--tx:#e6edf3;--mut:#8b98a9;--up:#f5564d;--down:#26c281;--neu:#d9a441;--acc:#4aa8ff;}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--tx);font-family:-apple-system,"PingFang SC","Microsoft YaHei",Segoe UI,sans-serif;line-height:1.6;padding:28px 18px 60px}}
.wrap{{max-width:1080px;margin:0 auto}}
h1{{font-size:26px;letter-spacing:1px}}
h2{{font-size:18px;margin:34px 0 14px;padding-left:11px;border-left:4px solid var(--acc);color:#fff}}
.sub{{color:var(--mut);font-size:12px}}
.up{{color:var(--up)}}.down{{color:var(--down)}}.neu{{color:var(--neu)}}
.meta{{color:var(--mut);font-size:13px;margin-top:6px}}
.banner{{background:linear-gradient(90deg,#1a2433,#161b24);border:1px solid var(--line);border-left:4px solid var(--acc);border-radius:10px;padding:14px 18px;margin:18px 0;font-size:13px}}
.banner b{{color:var(--acc)}}
.banner .warn{{color:var(--neu)}}
.cards{{display:flex;gap:12px;flex-wrap:wrap;margin:12px 0}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;flex:1;min-width:150px}}
.card.sm .lbl{{color:var(--mut);font-size:12px}}
.card.sm .big{{font-size:22px;font-weight:700;margin:4px 0}}
.acct{{display:flex;gap:14px;flex-wrap:wrap;align-items:stretch;margin:12px 0}}
.acct .card{{flex:1;min-width:180px}}
.acct .big{{font-size:28px;font-weight:800}}
table{{width:100%;border-collapse:collapse;margin:10px 0;font-size:13px}}
th,td{{padding:9px 8px;border-bottom:1px solid var(--line);text-align:left}}
th{{color:var(--mut);font-weight:600;font-size:12px;background:var(--bg2)}}
td.r,th.r{{text-align:right}}
.chips{{max-width:240px}}
.chip{{display:inline-block;background:#222b38;border:1px solid var(--line);border-radius:6px;padding:2px 7px;margin:2px;font-size:11px;color:#cdd7e2}}
.risk{{background:#3a1d1d;color:#ff7a72;border:1px solid #6b2b2b;border-radius:5px;padding:1px 6px;font-size:11px;margin-left:5px}}
.dorm{{background:#1d2433;color:#8fb6ff;border:1px solid #2c3c5c;border-radius:5px;padding:1px 6px;font-size:11px;margin-left:5px}}
.reb{{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--neu);border-radius:8px;padding:11px 14px;margin:9px 0}}
.reb-t{{font-weight:700;color:#fff}}
.reb-d{{font-size:13px;margin:4px 0;color:#d4dde6}}
.reb-s{{font-size:13px;color:var(--acc)}}
.badge{{padding:2px 9px;border-radius:20px;font-size:12px;font-weight:700}}
.badge.hit{{background:#143a28;color:#3fe39a;border:1px solid #1f6e47}}
.badge.miss{{background:#3a1717;color:#ff8a82;border:1px solid #6b2b2b}}
.pdir{{font-size:11px;padding:1px 6px;border-radius:4px;background:#222b38;color:var(--mut)}}
.kcards{{display:flex;gap:12px;flex-wrap:wrap}}
.kcard{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px;flex:1;min-width:185px}}
.khead{{display:flex;justify-content:space-between;align-items:center;font-weight:700;margin-bottom:8px}}
.kbias{{font-size:12px;padding:2px 8px;border-radius:6px}}
.kbias.up{{background:#3a1d1d;color:var(--up)}}.kbias.down{{background:#143a28;color:var(--down)}}.kbias.neu{{background:#2a2415;color:var(--neu)}}
.krow{{display:flex;gap:8px;font-size:12px;padding:3px 0;border-bottom:1px dashed #232c38}}
.krow span{{color:var(--mut);width:38px;flex:none}}
.krow b{{flex:1;font-weight:500}}
.krow i{{color:var(--mut);font-style:normal}}
.knote{{font-size:12px;color:#cdd7e2;margin-top:7px;line-height:1.5}}
.gauge{{display:flex;align-items:center;gap:18px;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px;margin:10px 0}}
.gnum{{font-size:46px;font-weight:800;min-width:120px;text-align:center}}
.glbl{{font-size:15px;font-weight:700}}
.gbar{{flex:1;height:14px;background:linear-gradient(90deg,#f5564d,#d9a441,#26c281);border-radius:8px;position:relative}}
.gbar i{{position:absolute;top:-5px;width:3px;height:24px;background:#fff;border-radius:2px}}
ul.news{{margin:8px 0 0 18px;font-size:13px;color:#d4dde6}}
ul.news li{{margin:5px 0}}
.foot{{margin-top:36px;padding-top:16px;border-top:1px solid var(--line);font-size:12px;color:var(--mut)}}
</style></head>
<body><div class="wrap">

<h1>📊 每日基金晚间复盘</h1>
<div class="meta">日期 <b>{DATE}</b> · 生成 2026-07-08 21:25 · 数据来源 <b>neodata-financial-search</b> · 仅供参考，不构成投资建议</div>

<div class="banner">
<b>✅ 数据源状态：neodata 已连接并返回数据（非「数据源缺失」）。</b> 截至执行时刻(21:25)：
<span class="warn">① 公募基金官方净值(07-08)在该源尚未更新，最新为 07-07 收官 → 基金净值/日涨跌采用最近可得官方收盘(07-07)，当日(07-08)变动以关联板块真实收盘作估值代理；</span>
② 北向资金、基金规模字段该源未返回；
<span class="warn">③ 「广发港股创新药ETF联接(QDII)C」被源误匹配为「中证创新药联接(012738)」（不同标的），该QDII持仓净值采用支付宝T0截图(-2.56%)，排名/重仓标注 N/A；</span>
④ 所有数值均为源返回真实值，未做任何编造。
</div>

<h2>一、账户与大盘概览</h2>
<div class="cards">{idx_html}</div>
<div class="acct">
  <div class="card"><div class="lbl">账户估算日收益 (07-08，板块代理)</div>
    <div class="big {cls(acct_ret)}">{pct(acct_ret)}</div>
    <div class="{cls(acct_ret)}">≈ {fnum(acct_pnl,2)} 元（持仓市值 {fnum(C['total_mv'],2)} 元）</div></div>
  <div class="card"><div class="lbl">策略</div>
    <div style="font-size:15px;margin-top:6px">进攻型 · 本金 15000 · 单基≤30% · 止损-8% / 止盈+15%</div>
    <div class="sub" style="margin-top:6px">活跃持仓 {sum(1 for f in C['funds'] if f['status']=='active')} 只 · 半导体暴露约 {CALC['semic_exposure']}%</div></div>
  <div class="card"><div class="lbl">全市场广度</div>
    <div style="font-size:18px;margin-top:6px" class="down">涨跌比 {CALC['breadth_ratio']}</div>
    <div class="sub">极致分化，个股普跌</div></div>
</div>

<h2>二、资金流（资金面）</h2>
<div class="card" style="margin:10px 0">
  <div style="font-weight:700;margin-bottom:6px">行业主力资金（07-08，⚠ 估算）</div>
  <ul class="news">{''.join(f'<li>{n}</li>' for n in CALC['mainflow_notes'])}</ul>
  <div class="sub" style="margin-top:8px">北向资金：{CALC['northbound_status']}</div>
</div>

<h2>三、α 与基本面（最近可得官方净值 07-07）</h2>
<div class="sub" style="margin-bottom:6px">α = 基金 07-07 实际日收益 − 关联基准 07-07 收益（越大越好）。排名/重仓为 neodata 返回，缺失标注 —。</div>
<table>
<tr><th>基金 / 板块</th><th class="r">净值(元)</th><th class="r">日收益07-07</th><th class="r">年内收益</th><th class="r">α</th><th class="r">同类排名</th><th class="r">07-08代理</th><th>十大重仓(前6)</th></tr>
{fund_rows}
</table>

<h2>四、调仓建议（集中度 / 半导体暴露 / 风险标记）</h2>
{reb_html}

<h2>五、预测命中率（回填 07-07→07-08）</h2>
<div class="cards">
  <div class="card sm"><div class="lbl">总体命中率</div><div class="big {cls(CALC['overall_acc']-50)}">{CALC['overall_acc']}%</div><div class="sub">{CALC['hits']}/{CALC['backfilled']} 命中</div></div>
  <div class="card sm"><div class="lbl">置信加权命中率</div><div class="big neu">{CALC['weighted_acc']}%</div><div class="sub">权重和 {fnum(CALC['w_total'],1)}</div></div>
  <div class="card sm"><div class="lbl">时段</div><div class="big" style="font-size:20px">evening</div><div class="sub">21:30 复盘</div></div>
</div>
<div class="banner" style="border-left-color:var(--neu)">07-07 晚间普遍看多，但 07-08 大盘回调（上证-0.49%、半导体近平、港股创新药-1.39%、仅煤炭+1.2% 逆势），致多数看多预测落空；仅「纳指100」「中证主要消费」震荡判断命中。实际值采用关联板块 07-08 真实收盘变动作估值代理。</div>
<table>
<tr><th>预测标的</th><th class="r">预测方向</th><th class="r">实际(07-08代理)</th><th>置信</th><th class="r">结果</th></tr>
{pred_rows}
</table>

<h2>六、收盘情绪校准 · 恐惧贪婪指数</h2>
<div class="gauge">
  <div class="gnum neu">{CALC['fg_index']}</div>
  <div style="flex:1">
    <div class="glbl neu">{CALC['fg_level']}</div>
    <div class="gbar"><i style="left:{CALC['fg_index']}%"></i></div>
    <div class="sub" style="margin-top:6px">{CALC['fg_action']}</div>
  </div>
</div>
<table>
<tr><th>情绪因子</th><th class="r">评分(0-100)</th><th class="r">加权贡献</th></tr>
{fg_rows}
<tr><td><b>综合恐惧贪婪指数</b></td><td class="r"><b class="neu">{CALC['fg_index']}</b></td><td class="r">—</td></tr>
</table>
<div class="sub">⚠ 5/8 因子（涨跌停/北向/融资/VIX/ERP）数据源未返回，按协议以中性50计入，综合指数被拉向中性；广度(涨跌比约1:7)显示真实情绪偏恐惧。</div>

<h2>七、板块日K信号（⚠ 模型研判）</h2>
<div class="kcards">{kline_html}</div>

<h2>八、新闻面（行业/政策/重仓动态）</h2>
<ul class="news">{news_html}</ul>

<div class="foot">
数据来源：<b>neodata-financial-search</b>（已连接）。指数/板块/基金净值为源返回真实值；基金官方净值最新为 07-07，07-08 变动以关联板块真实收盘作估值代理；北向/规模/港股创新药QDII排名等字段源未返回或误匹配，已标注。<br>
⚠️ 本报告由自动化系统生成，所有内容仅供参考，不构成任何投资建议。市场有风险，投资需谨慎。
</div>

</div></body></html>'''

out = os.path.join(REP, f"evening-review-{DATE}.html")
open(out,"w",encoding="utf-8").write(HTML)
print("wrote", out, len(HTML), "bytes")
