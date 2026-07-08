# -*- coding: utf-8 -*-
import os, datetime

# 上证指数近30根日K收盘 (20260527 -> 20260708, 取自通达信 T2)
closes = [4093.729980,4098.640137,4068.570068,4057.739990,4075.100098,
          4083.969971,4057.780029,4027.739990,3959.340088,4010.030029,
          3993.229980,3987.010010,4031.510010,4096.470215,4091.889893,
          4108.080078,4090.479980,4163.100098,4106.250000,4110.810059,
          4120.279785,4027.260010,4073.899902,4094.399902,4112.450195,
          4028.899902,4043.639893,4041.239990,3990.239990,3991.193359]
ma20 = sum(closes[-20:]) / 20

sh_now = 3991.19          # 上证现价 (14:24)
sh_chg = 0.02             # 上证当日涨跌幅 %
support_3460 = 3460.0

below_ma20_pct = (ma20 - sh_now) / ma20 * 100
above_3460_pct = (sh_now - support_3460) / support_3460 * 100

# 板块代理 ETF 实时涨跌 (通达信 T2, 14:24)
proxies = [
    ("半导体ETF(512480)", "半导体材料设备/存储/制造", 1.80,  "东方人工智能/东方阿尔法/永赢半导体/国泰半导体"),
    ("煤炭ETF(515220)",   "中证煤炭",         1.06,  "富国中证煤炭"),
    ("通信ETF(515880)",   "通信设备",         0.53,  "天弘通信设备"),
    ("港股创新药ETF(513120)","香港创新药",    -0.18, "广发港股创新药"),
    ("消费ETF(159928)",   "中证主要消费",    -0.32, "嘉实主要消费"),
    ("纳指ETF(513100)",   "纳斯达克100",     -0.97, "广发纳斯达克100"),
]
max_up = max(p[2] for p in proxies)
max_dn = min(p[2] for p in proxies)

# 8因子快速估算恐惧贪婪指数
fg = (0.15*37 + 0.10*50 + 0.15*35 + 0.12*50 + 0.08*50 + 0.10*50 + 0.15*30 + 0.15*55)
fg = round(fg, 1)

start_t  = "2026-07-08 14:21:12"
gen_t    = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
end_t    = gen_t  # 任务完成时刻 ≈ 生成时刻

def row(name, trig, detail, css):
    return f'''<tr>
      <td>{name}</td>
      <td class="{css}">{"✅ 触发" if trig else "❌ 未触发"}</td>
      <td>{detail}</td>
    </tr>'''

rows = []
rows.append(row("减仓预警<br><small>上证破3460或20日线</small>", True,
    f"上证 <b>{sh_now}</b> &lt; MA20 <b>{ma20:.2f}</b>（下方 <b>{below_ma20_pct:.2f}%</b>，趋势性持续）；3460 相距 +{above_3460_pct:.1f}% 未破", "alert"))
rows.append(row("禁止买入预警<br><small>大盘跳水&gt;0.5%</small>", False,
    f"上证当日 <b>+{sh_chg}%</b>（微涨），非跳水", "ok"))
rows.append(row("止损预警<br><small>单基跌&gt;5%</small>", False,
    f"代理板块最大跌幅 <b>{max_dn:.2f}%</b>（纳指ETF），无基金跌超5%", "ok"))
rows.append(row("止盈预警<br><small>单基涨&gt;15%</small>", False,
    f"代理板块最大涨幅 <b>+{max_up:.2f}%</b>（半导体ETF），远低于15%", "ok"))

proxy_rows = "".join(
    f"<tr><td>{n}</td><td><small>{sec}</small></td><td class='{'up' if v>=0 else 'dn'}'>{v:+.2f}%</td><td><small>{fund}</small></td></tr>"
    for (n,sec,v,fund) in proxies)

html = f'''<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>盘中预警 2026-07-08 14:25</title>
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
th,td{{padding:8px 6px;text-align:left;border-bottom:1px solid #2a3038;vertical-align:top}}
th{{color:#9aa0a6;font-weight:600;font-size:12px}}
.alert{{color:#ff5d5d;font-weight:700}}
.ok{{color:#46d18a;font-weight:700}}
.up{{color:#ff5d5d;font-weight:700}}   /* 中国习惯：涨红 */
.dn{{color:#46d18a;font-weight:700}}   /* 中国习惯：跌绿 */
.act{{background:#221a10;border-left:4px solid #ffb84a;padding:10px 12px;border-radius:8px;font-size:13px;margin-top:6px}}
.act li{{margin:5px 0 5px 16px}}
.note{{font-size:11px;color:#7d848c;margin-top:8px}}
.disc{{font-size:11px;color:#ff9d6b;margin-top:10px;border-top:1px dashed #5a3a1a;padding-top:8px}}
.small{{font-size:12px;color:#9aa0a6}}
</style></head>
<body>
<div class="card">
  <div class="h">🛡️ 盘中预警</div>
  <div class="sub">2026-07-08 周二盘中风控监控 · 交易日 14:25</div>
  <span class="tag">⚠ 1 项触发：减仓预警（趋势性持续）</span>
  <div class="tline">
    ① 开始时间：<b>{start_t}</b><br>
    ② 生成时间：<b>{gen_t}</b><br>
    ③ 结束时间：<b>{end_t}</b>
  </div>
</div>

<div class="card">
  <div class="h" style="font-size:16px;color:#ffd24a">预警清单</div>
  <table>
    <tr><th>触发条件</th><th>状态</th><th>实时判定</th></tr>
    {''.join(rows)}
  </table>
  <div class="note">数据 Tier：上证/ETF 均取自通达信实时行情（T2），时间戳 2026-07-08 14:24。板块代理以对应 ETF 实时涨跌近似关联指数，含跟踪误差。</div>
</div>

<div class="card">
  <div class="h" style="font-size:16px;color:#ffd24a">单基金代理板块实时涨跌</div>
  <table>
    <tr><th>代理ETF</th><th>关联板块</th><th>实时</th><th>覆盖持仓</th></tr>
    {proxy_rows}
  </table>
  <div class="note">最大跌幅 {max_dn:.2f}%（纳指），最大涨幅 +{max_up:.2f}%（半导体）；均未触及 ±5%/±15% 阈值，故止损/止盈预警未触发。</div>
</div>

<div class="card">
  <div class="h" style="font-size:16px;color:#ffd24a">建议动作</div>
  <div class="act">
    <ul>
      <li><b>不追高、不恐慌减仓</b>：本次为趋势性破位（上证持续运行于 20 日线下方约 1.8%），非急跌跳水，硬止损线 -8% 未触及。</li>
      <li><b>维持进攻型仓位</b>：账户总仓 ≤ 90%、单基 ≤ 30% 的纪律不变；重仓半导体（合计约 58%）随板块反弹 +1.80%，未触发减仓点，继续持有观察。</li>
      <li><b>等待尾盘指令</b>：具体加减仓/调仓价位以 14:30 尾盘决策任务为准，本监控仅预警、不买卖。</li>
      <li><b>持续关注</b>：若上证进一步跌破 MA20 且放量，或单基金当日跌 &gt; 5%，将升级为更强制预警。</li>
    </ul>
  </div>
</div>

<div class="card">
  <div class="h" style="font-size:16px;color:#ffd24a">盘中情绪（8 因子快估）</div>
  <p class="small">恐惧贪婪指数 ≈ <b style="color:#ffd24a;font-size:18px">{fg}</b>（中性偏恐惧，区间 0-100）</p>
  <p class="small">未达极端区（≤20 极度恐惧 / ≥80 极度贪婪），按规则<span class="ok"> 不单独提示</span>。主要压制的因子：市场广度偏弱（涨跌家数 891:1384≈0.64）、主力净流出、隔夜美存储暴跌推升 VIX。</p>
</div>

<div class="disc">⚠️ 本监控仅供参考，不构成投资建议。市场有风险，投资需谨慎。所有行情为 T2 实时快照，含跟踪误差与延迟，请以基金官方净值为准。</div>
</body></html>'''

out = r"C:/Users/LEGION/Nutstore/1/daily-report/data/reports/2026-07-08/盘中预警_20260708_1421.html"
with open(out, "w", encoding="utf-8") as f:
    f.write(html)
print("MA20 =", round(ma20,2), "| below% =", round(below_ma20_pct,2), "| FG =", fg)
print("written:", out, "| bytes:", os.path.getsize(out))
