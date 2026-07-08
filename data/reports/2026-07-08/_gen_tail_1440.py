# -*- coding: utf-8 -*-
import os, json, datetime

OUT_DIR = r"C:/Users/LEGION/Nutstore/1/daily-report/data/reports/2026-07-08"
os.makedirs(OUT_DIR, exist_ok=True)

start_t = "2026-07-08 14:35:35"
gen_t  = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
end_t  = gen_t

DATE = "2026-07-08"
HHMM = datetime.datetime.now().strftime("%H%M")

# ---- 实时行情(通达信 T2, 14:40 快照) ----
market = {"sh": -0.15, "cyb": -1.13}
idx_live = {
    "半导体(881319)": "+0.63%",
    "通信设备(881338)": "+0.36%",
    "中证煤炭(399998)": "+1.14%",
    "港股创新药(513120)": "-3.70%",
    "中证主要消费(000932)": "-0.53%",
    "纳斯达克100(513110)": "+1.26%",
}

# ---- 恐惧贪婪指数(8因子加权) ----
factors = [
    ("市场广度", "涨跌家数比≈0.64", 38),
    ("涨跌停家数", "数据缺失→中性", 50),
    ("主力资金净流入", "成长净流出/半导体微正", 42),
    ("北向资金净买入", "数据缺失→中性[⚠待验证]", 50),
    ("融资余额变化", "数据缺失→中性[⚠待验证]", 50),
    ("量能亢奋度", "创业板LB0.82/半导体LB0.98", 50),
    ("VIX恐慌指数", "隔夜美存储暴跌推升", 32),
    ("股债风险溢价ERP", "数据缺失→中性[⚠待验证]", 50),
]
wts = [0.15,0.10,0.15,0.12,0.08,0.10,0.15,0.15]
fg = round(sum(f[2]*w for f,w in zip(factors,wts)),1)
fg_level = "中性" if 40<=fg<=60 else ("恐惧" if fg<40 else "贪婪")
sentiment_action = "中性，按技术/基本面逻辑决策，情绪不额外干预（未达极端区）"

# ---- 板块日K量化(五维: 趋势40/量价30/形态15/主力15) ----
sectors = [
    ("半导体材料设备", "偏多", 66, "偏多(收盘MA20上/AI-CPO趋势)", "价微涨量近均(LB0.98)健康", "探底回升(低点2073→2160)", "洗盘偏多/温和净流", "站上短期均线"),
    ("通信设备/CPO", "偏多", 67, "偏多(CPO突破趋势)", "价涨量平(LB0.907)", "高位略上影但主题强", "抢筹(光模块量产)", "突破平台"),
    ("香港创新药", "偏空", 27, "偏空(下行/破MA)", "价跌量能放大", "下跌中继", "出货/减仓", "跌破均线"),
    ("中证煤炭", "偏多", 64, "偏多(午后反弹)", "价涨量增(反弹)", "探底回升(早-2.74%→+1.14%)", "回补", "收复均线"),
    ("中证主要消费", "中性", 50, "偏空转中性", "价跌量缩(LB0.72)", "无明确信号", "中性", "均线纠缠"),
]

# ---- 逐基金决策 ----
# (name, sector, weight, yret, idx, idx_chg, bias, action, stop, price_act, note)
funds = [
 ("东方人工智能主题混合C","半导体材料设备/AI",36.62,"+1.64%","半导体","+0.63%","偏多","HOLD","-8%","持有不加仓(单仓超限)","板块偏多企稳；单仓36.62%超30%上限，禁止加仓；建议择机降至≤30%"),
 ("东方阿尔法科技优选混合C","半导体/科技优选",21.80,"+0.87%","半导体","+0.63%","偏多","HOLD","-8%","持有","板块偏多；未超限；总仓限禁买"),
 ("广发港股创新药ETF联接(QDII)C","香港创新药",16.19,"-2.56%","香港创新药","-3.70%","偏空","HOLD(观察/风控)","-8%","持有观察，临近-8%预警","板块偏空(多空倾向27)；关联指数-3.7%承压；未触-8%硬止损"),
 ("永赢先锋半导体智选混合C","半导体/存储芯片",12.51,"-3.84%","半导体存储","承压(美存储暴跌)","分化","HOLD(风控优先)","-8%","持有，紧盯-8%","半导体broad偏多但存储子板块受美光-9%/闪迪-14%独立冲击，yret-3.84%逼近止损"),
 ("富国中证煤炭指数C","中证煤炭",7.30,"+1.29%","中证煤炭","+1.14%","偏多","SELL/转换在途","—","煤炭→鹏华丰诚债247.77份进行中","主动降风险，尾盘不追加"),
 ("嘉实中证主要消费ETF发起联接C","中证主要消费",3.60,"0.00%(新仓)","中证主要消费","-0.53%","中性","HOLD","-8%","持有观察","新建仓；总仓限禁买"),
 ("财通集成电路产业股票C","集成电路/PCB",0.72,"0.00%","PCB","-0.51%","中性","HOLD","-8%","持有","微小仓"),
 ("财通成长优选混合C","成长优选",0.72,"0.00%","成长风格","—","中性","HOLD","-8%","持有","微小仓"),
 ("天弘中证全指通信设备指数C","通信设备/CPO",0.07,"0.00%","通信设备","+0.36%","偏多","HOLD","-8%","持有","CPO主题偏多"),
 ("广发纳斯达克100ETF联接","纳斯达克100",0.43,"+0.53%","纳斯达克100","+1.26%","偏多","HOLD","-8%","持有","QDII隔夜美股上行"),
 ("国泰半导体制造精选混合C","半导体制造",0.00,"—","半导体制造","—","—","已清仓","—","无操作","已清仓"),
]

risk_flags = [
 ("🔴 总仓≈100% 超 90% 上限","需降至≤90%（约减1400元）；尾盘禁止净买入"),
 ("🔴 东方人工智能 单仓36.62% 超 30% 上限","择机减至≤30%（约减900元）"),
 ("🟡 永赢半导体 持有-3.84%+美存储暴跌","逼近-8%硬止损，重点盯盘"),
 ("🟡 港股创新药 持有-2.56%+板块偏空(-3.7%)","逼近-8%硬止损，重点盯盘"),
 ("🟡 创业板指 -1.13%","成长风格承压，但非大盘跳水(上证-0.15%)"),
]

buy_block = "总仓≈100% > 90%上限；且东方人工智能单仓36.62% > 30%上限 → 尾盘禁止净买入（除非先减仓腾额度，但无减仓触发）。大盘(上证-0.15%)未触发'跳水>0.5%'禁令；账户日亏-16.85元(≈-0.12%)未触发'-3%'禁令。"

# ====== build HTML ======
def esc(s): return str(s)

factor_rows = "".join(
    f"<tr><td>{n}</td><td><small>{raw}</small></td><td>{v}</td><td class='{'up' if v>=50 else 'dn'}'>{v}</td><td>{round(v*w,1)}</td></tr>"
    for (n,raw,v),w in zip(factors,wts))

sector_rows = "".join(
    f"<tr><td><b>{name}</b></td><td class='{'up' if bias>=65 else ('dn' if bias<=34 else '')}'><b>{bias}</b></td>"
    f"<td>{trend}</td><td>{vp}</td><td>{pat}</td><td>{mf}</td><td>{close}</td>"
    f"<td class='{'up' if lean=='偏多' else ('dn' if lean=='偏空' else '')}'><b>{lean}</b></td></tr>"
    for (name,lean,bias,trend,vp,pat,mf,close) in sectors)

fund_rows = "".join(
    f"<tr><td><b>{name}</b><br><small>{sec}</small></td><td>{w}%</td><td class='{'up' if yret.startswith('+') else ('dn' if yret.startswith('-') else '')}'>{yret}</td>"
    f"<td><small>{idx} {ichg}</small></td><td class='{'up' if bias=='偏多' else ('dn' if bias=='偏空' else '')}'>{bias}</td>"
    f"<td class='{'ok' if act.startswith('HOLD') else 'alert'}'><b>{act}</b></td><td class='{'dn' if sl!='—' else ''}'>{sl}</td>"
    f"<td><small>{pa}</small></td><td><small>{note}</small></td></tr>"
    for (name,sec,w,yret,idx,ichg,bias,act,sl,pa,note) in funds)

risk_rows = "".join(f"<tr><td>{r[0]}</td><td><small>{r[1]}</small></td></tr>" for r in risk_flags)
idx_rows = "".join(f"<tr><td>{k}</td><td class='{'up' if v.strip().startswith('+') else 'dn'}'>{v}</td></tr>" for k,v in idx_live.items())

html = f'''<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>尾盘决策基线 2026-07-08 14:40</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;background:#0f1216;color:#e8eaed;padding:14px;line-height:1.5}}
.card{{background:#1a1f26;border-radius:14px;padding:16px;margin-bottom:12px;box-shadow:0 2px 10px rgba(0,0,0,.3)}}
.h{{font-size:20px;font-weight:700;color:#ffd24a;margin-bottom:4px}}
.sub{{font-size:12px;color:#9aa0a6;margin-bottom:10px}}
.tag{{display:inline-block;background:#3a2a12;color:#ffb84a;border:1px solid #6b4a18;border-radius:8px;padding:3px 10px;font-size:13px;font-weight:700;margin-bottom:8px}}
.tline{{font-size:12px;color:#9aa0a6;border-top:1px solid #2a3038;padding-top:8px;margin-top:8px}}
.tline b{{color:#cfd3d8}}
table{{width:100%;border-collapse:collapse;font-size:13px;margin-top:6px}}
th,td{{padding:7px 6px;text-align:left;border-bottom:1px solid #2a3038;vertical-align:top}}
th{{color:#9aa0a6;font-weight:600;font-size:11px}}
.alert{{color:#ff5d5d;font-weight:700}}
.ok{{color:#46d18a;font-weight:700}}
.up{{color:#ff5d5d;font-weight:700}}
.dn{{color:#46d18a;font-weight:700}}
.act{{background:#221a10;border-left:4px solid #ffb84a;padding:10px 12px;border-radius:8px;font-size:13px;margin-top:6px}}
.note{{font-size:11px;color:#7d848c;margin-top:8px}}
.disc{{font-size:11px;color:#ff9d6b;margin-top:10px;border-top:1px dashed #5a3a1a;padding-top:8px}}
.small{{font-size:12px;color:#9aa0a6}}
.fgnum{{font-size:30px;font-weight:800;color:#ffd24a}}
</style></head>
<body>
<div class="card">
  <div class="h">📊 尾盘决策（基线 / 首轮）</div>
  <div class="sub">2026-07-08 周三 · 尾盘盯盘 14:35–15:00 · 生成于 14:40</div>
  <span class="tag">指令基调：HOLD 为主 · 禁止买入 · 煤炭降风险转换在途</span>
  <div class="tline">
    ① 开始时间：<b>{start_t}</b><br>
    ② 生成时间：<b>{gen_t}</b><br>
    ③ 结束时间：<b>{end_t}</b>
  </div>
  <div class="note">本决策为今日尾盘盯盘首轮基线（无上一轮可对比）。后续每2分钟一轮，决策变动时立即推送变动报告；约14:58出收盘定稿。</div>
</div>

<div class="card">
  <div class="h" style="font-size:16px;color:#ffd24a">全局纪律与买入禁令</div>
  <div class="act">{buy_block}</div>
</div>

<div class="card">
  <div class="h" style="font-size:16px;color:#ffd24a">实时关联指数（通达信 T2 · 14:40）</div>
  <table>
    <tr><th>指数/板块</th><th>实时涨跌</th></tr>
    {idx_rows}
    <tr><td>上证指数 / 创业板指</td><td>上证 <span class="dn">-0.15%</span> / 创业板 <span class="dn">-1.13%</span></td></tr>
  </table>
  <div class="note">大盘未跳水(上证-0.15%&lt;0.5%)；创业板-1.13%显示成长承压。数据 Tier：通达信实时行情(T2)，板块以对应指数/行业板近似关联指数，含跟踪误差。</div>
</div>

<div class="card">
  <div class="h" style="font-size:16px;color:#ffd24a">情绪因子 · 恐惧贪婪指数</div>
  <p class="small">综合指数 = <span class="fgnum">{fg}</span> / 100 &nbsp;|&nbsp; 分级：<b>{fg_level}</b></p>
  <p class="small">尾盘情绪指令：{sentiment_action}</p>
  <table style="margin-top:8px">
    <tr><th>因子</th><th>原始值</th><th>评分</th><th>加权贡献</th></tr>
    {factor_rows}
  </table>
  <div class="note">缺失因子(北向/融资/ERP)按中性50计入并标注[⚠待验证]，权重不变。情绪不覆盖-8%硬止损。</div>
</div>

<div class="card">
  <div class="h" style="font-size:16px;color:#ffd24a">板块日K量化（五维 · 多空倾向）</div>
  <table>
    <tr><th>板块</th><th>多空倾向</th><th>趋势定位</th><th>量价关系</th><th>形态信号</th><th>主力行为</th><th>收盘价暗号</th><th>判定</th></tr>
    {sector_rows}
  </table>
  <div class="note">加权=趋势40%+量价30%+形态15%+主力15%；≥65偏多 / 35-64中性 / ≤34偏空。形态与主力行为为AI模型研判(⚠模型研判)。</div>
</div>

<div class="card">
  <div class="h" style="font-size:16px;color:#ffd24a">逐基金决策（指令 / 价位 / 硬止损 / 情绪 / 板块）</div>
  <table>
    <tr><th>基金(板块)</th><th>仓位</th><th>持有收益</th><th>关联指数</th><th>板块</th><th>指令</th><th>硬止损</th><th>价位动作</th><th>逻辑</th></tr>
    {fund_rows}
  </table>
  <div class="note">硬止损-8%全程有效，不因子情绪覆盖。总仓超限→本轮回合无新买入指令。</div>
</div>

<div class="card">
  <div class="h" style="font-size:16px;color:#ffd24a">风控预警</div>
  <table>
    <tr><th>预警</th><th>说明</th></tr>
    {risk_rows}
  </table>
</div>

<div class="disc">⚠️ 本分析仅供参考，不构成投资建议。市场有风险，投资需谨慎。行情为 T2 实时快照(通达信)，含跟踪误差与延迟；基金以官方净值为准。情绪/板块形态含模型研判(⚠)。</div>
</body></html>'''

report_path = os.path.join(OUT_DIR, f"尾盘决策基线_2026{HHMM[:2]}{HHMM[2:]}.html".replace("2026","2026"))
# simpler explicit name:
report_path = os.path.join(OUT_DIR, f"尾盘决策基线_20260708_{HHMM}.html")
with open(report_path, "w", encoding="utf-8") as f:
    f.write(html)

# ====== last-decision.json (供下一轮对比) ======
decisions = {}
for (name,sec,w,yret,idx,ichg,bias,act,sl,pa,note) in funds:
    decisions[name] = {"action": act, "stop_loss": sl, "price_action": pa, "note": note, "sector_bias": bias, "yret": yret}

last = {
    "date": DATE,
    "gen_time": gen_t,
    "is_baseline": True,
    "fear_greed_index": fg,
    "sentiment_level": fg_level,
    "sentiment_action": sentiment_action,
    "market": market,
    "global": {
        "total_position_pct": 100,
        "total_position_limit": 90,
        "single_max_pct": 36.62,
        "single_limit": 30,
        "buy_allowed": False,
        "reason": "总仓≈100%超90%上限；东方人工智能单仓36.62%超30%上限"
    },
    "decisions": decisions,
    "risk_flags": [r[0] for r in risk_flags],
}
with open(os.path.join(OUT_DIR, "last-decision.json"), "w", encoding="utf-8") as f:
    json.dump(last, f, ensure_ascii=False, indent=2)

print("FG =", fg, fg_level)
print("report:", report_path, "| bytes:", os.path.getsize(report_path))
print("last-decision.json written")
