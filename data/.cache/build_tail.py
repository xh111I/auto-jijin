# -*- coding: utf-8 -*-
import json, os, datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # data/
CACHE = os.path.join(BASE, ".cache")
DATE = "2026-07-10"
UPD = "2026-07-10 14:25"

kl = json.load(open(os.path.join(CACHE, "klines.json"), encoding="utf-8"))

def attach_kline(slug, last_nav):
    if slug in kl and kl[slug]["ohlc"]:
        d = kl[slug]
        ohlc = d["ohlc"]
        lows = [r[2] for r in ohlc[-10:]]
        highs = [r[3] for r in ohlc[-10:]]
        return {"dates": d["dates"], "ohlc": ohlc,
                "current_price": round(last_nav, 4),
                "support": round(min(lows), 4),
                "pressure": round(max(highs), 4)}
    return None

def ktext(s):
    return "⚠ 日K(NAV)数据未抓取 · 板块联动详见板块量化"

# ---------- holdings ----------
holdings = [
 {"name":"东方人工智能主题混合C","sector":"半导体材料设备/AI","weight_pct":36.12,"hold_return_pct":5.66,
  "related_index":"半导体材料设备","related_index_chg":-2.40,"sector_tendency":"偏空","instruction":"HOLD",
  "overweight":True,"stop_loss_pct":-8,
  "logic":"板块高位出货(半导体-2.40%·主力净流出-167亿·PE158极高)；单仓36.12%>30%超限→禁止加仓；趋势未破但安全边际不足，建议择机降至≤30%",
  "main_force":{"net_inflow":-167.59,"big_order_pct":34.0,"qualitative":"出货偏空","hint":"半导体单日-2.4%主力净流出167亿，PE158历史极高，主力高位派发中"},
  "tech_score":{"composite":38,"level":"偏空","trend":"半导体高位回落破MA10/20","vol_price":"价跌量增·主力出","shape":"长上影见顶"}},
 {"name":"东方阿尔法科技优选混合C","sector":"半导体材料设备/科技优选","weight_pct":25.56,"hold_return_pct":5.29,
  "related_index":"半导体材料设备","related_index_chg":-2.40,"sector_tendency":"偏空","instruction":"HOLD",
  "overweight":False,"stop_loss_pct":-8,
  "logic":"同半导体板块出货阶段；单仓25.56%未超30%上限，不追高；若半导体继续破位放量可减仓，否则持有",
  "main_force":{"net_inflow":-167.59,"big_order_pct":34.0,"qualitative":"出货偏空","hint":"跟随半导体板块主力净流出，未独立走强"},
  "tech_score":{"composite":42,"level":"偏空","trend":"板块回调·均线纠缠","vol_price":"价跌量平","shape":"高位震荡"}},
 {"name":"鹏华丰诚债券C","sector":"固定收益/纯债安全垫","weight_pct":9.61,"hold_return_pct":0.0,
  "related_index":None,"related_index_chg":None,"sector_tendency":"中性","instruction":"HOLD",
  "overweight":False,"stop_loss_pct":-8,
  "logic":"纯债安全垫，与权益低相关；作为组合压舱石持有，不择时",
  "main_force":{"net_inflow":0.0,"big_order_pct":0.0,"qualitative":"避险","hint":"债基无板块主力流向，防御属性"},
  "tech_score":{"composite":55,"level":"中性","trend":"债基平稳","vol_price":"低波动","shape":"横盘"}},
 {"name":"广发港股创新药ETF联接(QDII)C","sector":"医药/港股创新药","weight_pct":11.92,"hold_return_pct":-13.07,
  "related_index":"恒生医疗保健","related_index_chg":4.10,"sector_tendency":"偏多","instruction":"HOLD",
  "overweight":False,"stop_loss_pct":-8,
  "logic":"今日港股创新药+4.10%强反弹、资金流入(创新药+29亿)，近期亏损回收未触-8%硬止损；反弹低位不割肉(市场先生逆向)，不减不增，观察反弹持续性",
  "main_force":{"net_inflow":29.45,"big_order_pct":41.0,"qualitative":"建仓偏多","hint":"创新药主力净流入29亿，低位放量反弹，主力回补"},
  "tech_score":{"composite":66,"level":"偏多","trend":"低位放量反弹","vol_price":"价涨量增·资金入","shape":"大阳线"}},
 {"name":"永赢先锋半导体智选混合C","sector":"半导体材料设备","weight_pct":6.74,"hold_return_pct":-15.9,
  "related_index":"半导体材料设备","related_index_chg":-2.40,"sector_tendency":"偏空","instruction":"减仓",
  "overweight":False,"stop_loss_pct":-8,
  "logic":"近期亏损已触及-8%硬止损线(累计-15.9%、近期≈-8.3%)，且半导体板块出货(PE158/主力-167亿净流出)；按铁律尾盘强制减仓/止损，释放风险与额度",
  "main_force":{"net_inflow":-167.59,"big_order_pct":34.0,"qualitative":"出货","hint":"板块派发中，持有即持续承担下跌风险"},
  "tech_score":{"composite":28,"level":"偏空","trend":"弱势下行","vol_price":"主力净流出","shape":"破位"}},
 {"name":"富国中证煤炭指数C","sector":"资源/高股息防御","weight_pct":3.82,"hold_return_pct":2.31,
  "related_index":"中证煤炭","related_index_chg":-0.18,"sector_tendency":"偏空","instruction":"HOLD",
  "overweight":False,"stop_loss_pct":-8,
  "logic":"煤炭今日-0.18%、20日-11.14%弱势阴跌；高股息防御但动能弱，小幅持有观察，不补仓",
  "main_force":{"net_inflow":-1.58,"big_order_pct":30.0,"qualitative":"观望","hint":"主力小幅净流出，无明确方向"},
  "tech_score":{"composite":35,"level":"偏空","trend":"弱势震荡","vol_price":"地量阴跌","shape":"缩量"}},
 {"name":"嘉实中证主要消费ETF发起联接C","sector":"指数/大消费","weight_pct":3.78,"hold_return_pct":-0.68,
  "related_index":"中证主要消费指数","related_index_chg":1.53,"sector_tendency":"中性","instruction":"HOLD",
  "overweight":False,"stop_loss_pct":-8,
  "logic":"今日食品饮料+1.53%低位反弹、主力净流入+11亿；但YTD-18.8%长期弱势，仅视为超跌修复，不追高",
  "main_force":{"net_inflow":11.28,"big_order_pct":38.0,"qualitative":"建仓偏多","hint":"消费低位放量反弹，资金回补"},
  "tech_score":{"composite":52,"level":"中性","trend":"低位反弹","vol_price":"价涨量增","shape":"止跌回升"}},
 {"name":"广发纳斯达克100ETF联接(QDII)C","sector":"海外/美股指数","weight_pct":0.60,"hold_return_pct":10.51,
  "related_index":"纳斯达克100","related_index_chg":1.62,"sector_tendency":"偏多","instruction":"HOLD",
  "overweight":False,"stop_loss_pct":-8,
  "logic":"纳指+1.62%延续强势，美股分散配置；小仓持有，QDII T+1净值，不加仓",
  "main_force":{"net_inflow":0.0,"big_order_pct":0.0,"qualitative":"—","hint":"美股无板块主力流向数据"},
  "tech_score":{"composite":60,"level":"偏多","trend":"美股上行","vol_price":"量能温和","shape":"多头"}},
 {"name":"财通集成电路产业股票C","sector":"半导体/CPO光模块","weight_pct":0.80,"hold_return_pct":5.0,
  "related_index":"半导体","related_index_chg":-2.40,"sector_tendency":"偏空","instruction":"HOLD",
  "overweight":False,"stop_loss_pct":-8,
  "logic":"半导体/CPO小仓(0.8%)，板块出货期持有不动，不追不补",
  "main_force":{"net_inflow":-80.23,"big_order_pct":33.0,"qualitative":"分歧偏空","hint":"CPO主力净流出80亿，分歧加大"},
  "tech_score":{"composite":40,"level":"偏空","trend":"板块回落","vol_price":"量能分歧","shape":"震荡"}},
 {"name":"财通成长优选混合C","sector":"成长风格/混合","weight_pct":0.80,"hold_return_pct":4.91,
  "related_index":"沪深300成长","related_index_chg":-0.82,"sector_tendency":"中性","instruction":"HOLD",
  "overweight":False,"stop_loss_pct":-8,
  "logic":"成长混合小仓(0.8%)，随大盘中性偏弱，持有观察",
  "main_force":{"net_inflow":-219.77,"big_order_pct":32.0,"qualitative":"观望","hint":"沪深300主力净流出219亿，整体偏弱"},
  "tech_score":{"composite":48,"level":"中性","trend":"跟随大盘","vol_price":"量平","shape":"震荡"}},
 {"name":"天弘中证全指通信设备指数C","sector":"通信/CPO","weight_pct":0.08,"hold_return_pct":5.91,
  "related_index":"中证全指通信设备","related_index_chg":-1.84,"sector_tendency":"偏空","instruction":"HOLD",
  "overweight":False,"stop_loss_pct":-8,
  "logic":"通信设备-1.84%小仓(0.08%)，板块分歧期持有，不操作",
  "main_force":{"net_inflow":-28.54,"big_order_pct":33.0,"qualitative":"分歧偏空","hint":"通信设备主力净流出28亿"},
  "tech_score":{"composite":42,"level":"偏空","trend":"板块回调","vol_price":"量能分歧","shape":"震荡"}},
]

# attach kline
kmap = {"东方人工智能主题混合C":"dfzr","东方阿尔法科技优选混合C":"dfae",
        "广发港股创新药ETF联接(QDII)C":"ghc","永赢先锋半导体智选混合C":"yys",
        "鹏华丰诚债券C":"ph","富国中证煤炭指数C":"fg","嘉实中证主要消费ETF发起联接C":"js"}
for h in holdings:
    slug = kmap.get(h["name"])
    if slug:
        kn = attach_kline(slug, kl[slug]["last_nav"])
        h["kline"] = kn
    else:
        h["kline_text"] = ktext(h["name"])

# fix nav on kline current_price already set; fine.
# re-derive kline current_price from last_nav
for h in holdings:
    if "kline" in h:
        h["kline"]["current_price"] = round(kl[kmap[h["name"]]]["last_nav"], 4)

instruction = {
 "core_conclusion":"全场HOLD · 禁净买入 · 永赢半导体触发-8%止损减仓",
 "core_conclusion_cls":"watch",
 "active_action":"永赢先锋半导体触及-8%硬止损→尾盘减仓/止损；东方AI单仓超限择机降至≤30%",
 "risk_floor":"单基 -8% 硬止损不变：永赢半导体已触及→执行减仓",
 "timestamp_label":"数据截至 2026-07-10 14:25",
 "discipline_note":"总仓≈99.83%>90%上限、东方AI单仓36.12%>30%→全场禁止净买入；唯一主动=永赢止损减仓+东方AI超限择机降至≤30%（须先减后加）"
}

position = {
 "snapshot_note":"持仓实时净值 · T0 用户实盘(07-09收盘OCR校准) + 07-10尾盘板块实时(neodata T2)",
 "index_kpis":[
   {"label":"上证","value":"-0.06%","cls":"down"},
   {"label":"创业板","value":"-2.59%","cls":"down","tag":"领跌"},
   {"label":"港股创新药","value":"+4.10%","cls":"up","tag":"领涨"},
   {"label":"半导体主力净流入","value":"-167.6亿","cls":"down","tag":"主力出"}
 ],
 "holdings":holdings
}

sector = {
 "bars":[
   {"name":"港股创新药","score":66,"tendency":"偏多","net_inflow":29.45,"linked":True,"tag":"持仓强关联"},
   {"name":"纳斯达克100","score":60,"tendency":"偏多","net_inflow":0.0,"linked":True},
   {"name":"主要消费","score":52,"tendency":"中性","net_inflow":11.28,"linked":True},
   {"name":"通信设备/CPO","score":40,"tendency":"偏空","net_inflow":-80.23,"linked":True,"tag":"分歧"},
   {"name":"煤炭","score":35,"tendency":"偏空","net_inflow":-1.58,"linked":True},
   {"name":"半导体材料设备","score":30,"tendency":"偏空","net_inflow":-167.59,"linked":True,"tag":"出货"}
 ],
 "detail":"主力行为呈现明显高低切换：①半导体(PE158历史极高)单日-2.40%且主力净流出-167.6亿、超大单撤离，处高位派发出货阶段；CPO/通信设备净流出-80/-28亿同步分歧。②创新药(主力+29亿)、港股创新药(+4.10%)、主要消费(+1.53%主力+11亿)低位放量反弹，属建仓/回补。③全市场主力净流出约-511亿(上证-62/深证-129/创业板-100/沪深300-220)，整体高位兑现。",
 "bottom_signals":"创新药/港股创新药低位底背离后放量反弹；主要消费YTD-18.8%后首现资金回补，止跌信号。",
 "top_signals":"半导体PE158+单日-2.4%主力净流出167亿=高位派发见顶；创业板指-2.59%长上影射击之星，见顶回落。",
 "close_special":"上证十字星(收≈开)变盘临界点；半导体长上影留上引线；创新药大阳线确认反弹。"
}

risk = {
 "hard_stop":{
   "items":[
     {"name":"永赢先锋半导体智选混合C","cur_loss_pct":-8.3,"stop_pct":-8,"warn":True,"warn_label":"强制止损"},
     {"name":"广发港股创新药ETF联接(QDII)C","cur_loss_pct":-3.8,"stop_pct":-8,"warn":False,"warn_label":"持有"}
   ],
   "floor_text":"永赢先锋半导体触及-8%硬止损线 → 尾盘执行减仓/止损；其余标的近期未触强制卖出"
 },
 "alerts":[
   {"level":"red","text":"总仓≈99.83% 超 90% 上限","detail":"今日禁净买入；仅可通过减仓腾额度"},
   {"level":"orange","text":"永赢半导体 触及 -8% 硬止损","detail":"尾盘减仓/止损释放风险"},
   {"level":"orange","text":"东方AI 单仓 36.12% > 30% 上限","detail":"禁止加仓，择机降至≤30%"},
   {"level":"orange","text":"港药 累计 -13.07% 深套","detail":"今日+4.1%反弹未触近期止损，观察持续性"}
 ]
}

sentiment = {
 "index":56,"level":"中性",
 "divergence":"广度恐惧(涨跌家数比≈0.55)与VIX/ERP贪婪(75-80)结构性背离；半导体高位但主力净流出-511亿，隐性派发",
 "action":"中性，按技术/基本面决策；不覆盖 -8% 硬止损铁律",
 "factors":[
   {"name":"市场广度","raw":"涨跌家数比≈0.55(估)","score":40,"weight":"15%","src":"T2⚠待验证"},
   {"name":"涨跌停家数","raw":"涨停稀少·跌多涨少","score":50,"weight":"10%","src":"T2⚠"},
   {"name":"主力资金净流入","raw":"全市场净流出≈-511亿","score":25,"weight":"15%","src":"T2"},
   {"name":"北向资金净买入","raw":"实时披露暂停(缺失)","score":50,"weight":"12%","src":"缺失"},
   {"name":"融资余额变化","raw":"未知","score":50,"weight":"8%","src":"缺失"},
   {"name":"量能亢奋度","raw":"两市≈2.9万亿(高)","score":80,"weight":"10%","src":"T2⚠"},
   {"name":"VIX恐慌指数","raw":"≈16(估)","score":75,"weight":"15%","src":"T2⚠待验证"},
   {"name":"股债风险溢价ERP","raw":"沪深300PE≈13·ERP≈6%(估)","score":80,"weight":"15%","src":"T2⚠待验证"}
 ]
}

logic = {
 "tail_buy":"①午盘HOLD/BUY且下午未转弱 ②关联指数企稳 ③加仓后单基≤30%且总仓≤90% ④无未知事件。\n当前总仓≈100%>90%且东方AI单仓>30% → 四项均不满足，全场禁止净买入。",
 "tail_sell":"①单基亏≥-8%强制止损(永赢半导体已触发) ②关联指数破位放量(创业板-2.59%长上影) ③板块单日暴涨>5%后滞涨(半导体昨+7.88%今-2.4%高位派发)。\n→ 永赢半导体执行止损减仓。",
 "tail_noadd":"①大盘跳水>0.5%(今日结构弱未触发但需盯) ②账户日亏>-3% ③未知事件待落地。\n叠加：东方AI单仓超限+总仓超限 → 任何加仓均禁止。",
 "emotion":"F&G≈56中性 → 不额外调整。半导体PE158+主力-167亿净流出属'市场先生'过热/贪婪区→不追高(巴菲特安全边际)；港药今日+4.1%反弹属恐慌修复非贪婪→不割肉。情绪不覆盖-8%硬止损。",
 "action_rows":[
   {"fund":"东方人工智能C","cmd":"HOLD","price":"持有不加仓","adj":"择机降至≤30%","emo":"— 不干预","logic":"板块出货但单仓超限禁买，只减不增"},
   {"fund":"东方阿尔法C","cmd":"HOLD","price":"持有","adj":"板块破位再减","emo":"— 不干预","logic":"半导体出货期，单仓未超限"},
   {"fund":"鹏华丰诚债C","cmd":"HOLD","price":"持有","adj":"防御垫","emo":"— 不干预","logic":"债基压舱石"},
   {"fund":"广发港药C","cmd":"HOLD","price":"持有","adj":"反弹不减","emo":"恐慌修复·不割","logic":"今日+4.1%反弹未触止损"},
   {"fund":"永赢半导体C","cmd":"减仓","price":"尾盘止损","adj":"清仓/大幅减","emo":"— 铁律","logic":"触及-8%硬止损+板块出货"},
   {"fund":"富国煤炭C","cmd":"HOLD","price":"持有","adj":"不补","emo":"— 不干预","logic":"弱势阴跌"},
   {"fund":"嘉实消费C","cmd":"HOLD","price":"持有","adj":"不追","emo":"— 不干预","logic":"超跌反弹非趋势"},
   {"fund":"广发纳指C","cmd":"HOLD","price":"持有","adj":"不加","emo":"— 不干预","logic":"美股强势分散"},
   {"fund":"财通集成C","cmd":"HOLD","price":"持有","adj":"不动","emo":"— 不干预","logic":"小仓半导体"},
   {"fund":"财通成长C","cmd":"HOLD","price":"持有","adj":"不动","emo":"— 不干预","logic":"小仓成长"},
   {"fund":"天弘通信C","cmd":"HOLD","price":"持有","adj":"不动","emo":"— 不干预","logic":"小仓CPO"}
 ]
}

sources = {"items":[
   {"item":"持仓实时净值/仓位","note":"T0 用户实盘(腾讯自选股OCR校准·07-09收盘)"},
   {"item":"指数/板块行情·主力净流入","note":"neodata T2 实时(2026-07-10 14:17-14:19)"},
   {"item":"基金近20日NAV","note":"neodata T2 净值历史(截至07-09 T+1)"},
   {"item":"VIX/沪深300PE/涨跌家数","note":"neodata部分缺失→估算并标注[⚠待验证]"}
]}

disclaimer = "⚠️ 本分析仅供参考，不构成投资建议。行情为 T2 实时快照(2026-07-10 14:25)，含跟踪误差与延迟；基金以官方净值为准。VIX/沪深300PE/涨跌家数为估算值[⚠待验证]。巴菲特逻辑为分析框架参考，非个股推荐。历史不代表未来，预测为模型研判。"

doc = {
 "date":DATE, "updated_at":UPD, "data_tier":"T2",
 "instruction":instruction, "position":position, "sector":sector,
 "risk":risk, "sentiment":sentiment, "logic":logic,
 "sources":sources, "disclaimer":disclaimer
}

out = os.path.join(BASE, "tail_%s.json" % DATE)
json.dump(doc, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("WROTE", out, os.path.getsize(out), "bytes")
print("holdings:", len(holdings), "with kline:", sum(1 for h in holdings if 'kline' in h))
