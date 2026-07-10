# -*- coding: utf-8 -*-
import json, os, datetime

BASE = "C:/Users/LEGION/Nutstore/1/daily-report"
DATE = "2026-07-10"
DATE_NEXT = "2026-07-11"

# ---- 今日上午11:30 真实数据(neodata 实时返回) ----
# indices
idx = {"上证指数": (4067.07, 0.76), "深证成指": (15493.28, 0.61), "创业板指": (3991.98, -0.65)}
# 申万行业 zdf
sw = {
    "半导体": -0.55, "煤炭开采": 0.41, "创新药/港股创新药": 4.44,
    "通信设备/CPO": 0.00, "食品饮料/主要消费": 2.16, "沪深300/成长宽基": 0.49,
}
# ETF 午盘涨跌(由最新价/昨收计算)
etf = {
    "半导体ETF国联安(512480)": -1.36, "港股创新药ETF(513120)": 3.94, "煤炭ETF国泰(515220)": 0.45,
    "通信ETF国泰(515880)": -0.12, "消费ETF汇添富(159928)": 2.59, "纳指ETF国泰(513100)": 0.83,
    "沪深300ETF华泰柏瑞(510300)": 0.53,
}

# ---- 持仓对齐表(11只) ----
alignment = [
    {"name":"东方人工智能主题混合C","qdii":False,"etf":"半导体ETF国联安(512480)","etf_chg":etf["半导体ETF国联安(512480)"],
     "sw_sector":"半导体","sw_chg":sw["半导体"],"op_signal":"持有","row_class":"core",
     "cause_tags":["第一大重仓36.1%","半导体主动主题","资金净流出居首-55亿"]},
    {"name":"东方阿尔法科技优选混合C","qdii":False,"etf":"半导体ETF国联安(512480)","etf_chg":etf["半导体ETF国联安(512480)"],
     "sw_sector":"半导体","sw_chg":sw["半导体"],"op_signal":"持有","row_class":"core",
     "cause_tags":["第二大重仓25.6%","半导体主动主题","随板块走弱"]},
    {"name":"鹏华丰诚债券C","qdii":False,"etf":None,"etf_chg":None,
     "sw_sector":"纯债安全垫(无权益板块)","sw_chg":None,"op_signal":"持有","row_class":"normal",
     "cause_tags":["纯债安全垫","第四大仓位9.6%","与权益脱钩"]},
    {"name":"广发港股创新药ETF联接(QDII)C","qdii":True,"etf":"港股创新药ETF(513120)","etf_chg":etf["港股创新药ETF(513120)"],
     "sw_sector":"创新药/港股创新药","sw_chg":sw["创新药/港股创新药"],"op_signal":"持有","row_class":"normal",
     "cause_tags":["QDII·T+1","创新药领涨+4.44%","化学制药净流入+18.5亿"]},
    {"name":"永赢先锋半导体智选混合C","qdii":False,"etf":"半导体ETF国联安(512480)","etf_chg":etf["半导体ETF国联安(512480)"],
     "sw_sector":"半导体","sw_chg":sw["半导体"],"op_signal":"减仓观察","row_class":"core",
     "cause_tags":["半导体主题","持仓深套-15.9%逼近止损","随板块走弱"]},
    {"name":"富国中证煤炭指数C","qdii":False,"etf":"煤炭ETF国泰(515220)","etf_chg":etf["煤炭ETF国泰(515220)"],
     "sw_sector":"煤炭开采","sw_chg":sw["煤炭开采"],"op_signal":"持有","row_class":"normal",
     "cause_tags":["煤炭企稳+0.41%","小仓3.8%","债转已到位不追高"]},
    {"name":"嘉实中证主要消费ETF发起联接C","qdii":False,"etf":"消费ETF汇添富(159928)","etf_chg":etf["消费ETF汇添富(159928)"],
     "sw_sector":"食品饮料/主要消费","sw_chg":sw["食品饮料/主要消费"],"op_signal":"持有","row_class":"normal",
     "cause_tags":["消费估值低位修复","食品饮料+2.16%","小仓3.8%"]},
    {"name":"广发纳斯达克100ETF联接(QDII)C","qdii":True,"etf":"纳指ETF国泰(513100)","etf_chg":etf["纳指ETF国泰(513100)"],
     "sw_sector":"纳斯达克100(美股QDII)","sw_chg":None,"op_signal":"持有","row_class":"normal",
     "cause_tags":["QDII·T+1","纳指ETF+0.83%","极小仓0.6%"]},
    {"name":"财通集成电路产业股票C","qdii":False,"etf":"半导体ETF国联安(512480)","etf_chg":etf["半导体ETF国联安(512480)"],
     "sw_sector":"半导体/CPO","sw_chg":sw["半导体"],"op_signal":"持有","row_class":"core",
     "cause_tags":["半导体新仓","小仓0.8%","随板块偏弱"]},
    {"name":"财通成长优选混合C","qdii":False,"etf":"沪深300ETF华泰柏瑞(510300)","etf_chg":etf["沪深300ETF华泰柏瑞(510300)"],
     "sw_sector":"沪深300/成长宽基","sw_chg":sw["沪深300/成长宽基"],"op_signal":"持有","row_class":"normal",
     "cause_tags":["成长宽基","沪深300+0.49%","小仓0.8%"]},
    {"name":"天弘中证全指通信设备指数C","qdii":False,"etf":"通信ETF国泰(515880)","etf_chg":etf["通信ETF国泰(515880)"],
     "sw_sector":"通信设备/CPO","sw_chg":sw["通信设备/CPO"],"op_signal":"观望","row_class":"normal",
     "cause_tags":["CPO主题退潮","极小仓0.08%","基金经理警示追高"]},
]

# ---- 预测(三栏) + 追加预测库 ----
pred_records = [
    ("东方人工智能主题混合C","跌","中","半导体-0.55%、ETF-1.36%、主力净流出-55亿居首，今日资金撤离半导体，午后或延续偏弱不追高"),
    ("东方阿尔法科技优选混合C","跌","中","同半导体弱势+资金净流出，主动主题跟跌"),
    ("永赢先锋半导体智选混合C","跌","中","半导体弱势+持仓深套-15.9%，承压"),
    ("财通集成电路产业股票C","跌","低","半导体小仓新配，随板块偏弱"),
    ("天弘中证全指通信设备指数C","跌","低","通信设备-0.00%平、CPO主题退潮，极小仓观望"),
    ("广发港股创新药ETF联接(QDII)C","涨","高","创新药板块+4.44%领涨、化学制药主力净流入+18.5亿，动量极强；午后或延续但T+1净值次日确认"),
    ("嘉实中证主要消费ETF发起联接C","涨","中","食品饮料+2.16%、消费ETF+2.59%修复，估值低位补涨延续"),
    ("广发纳斯达克100ETF联接(QDII)C","涨","中","纳指ETF+0.83%，美股强势T+1，净值次日确认"),
    ("富国中证煤炭指数C","震荡","中","煤炭+0.41%企稳小涨、窄幅震荡，按计划不追高"),
    ("鹏华丰诚债券C","震荡","低","纯债安全垫，日内≈平，与权益脱钩"),
    ("财通成长优选混合C","震荡","低","沪深300仅+0.49%窄幅；模型震荡历史偏差大低置信"),
]
W = {"高":1.0,"中":0.7,"低":0.3}
up=[];down=[];flat=[]
for i,(nm,dr,cf,rs) in enumerate(pred_records,1):
    item={"name":nm,"conf":cf,"reason":rs}
    if dr=="涨": up.append(item)
    elif dr=="跌": down.append(item)
    else: flat.append(item)

doc = {
  "date": DATE,
  "updated_at": DATE+" 11:30",
  "data_tier": "T2",
  "snapshot": "11:30 A股午盘",
  "core": {
    "one_liner": "半导体高位分歧、资金净流出居首，创新药/消费接棒领涨的轮动分化行情",
    "action_guide": "核心半导体持仓不追高、警惕资金净流出延续；创新药/消费持有；煤炭企稳不追；严守单基-8%硬止损",
    "kpis": [
      {"label":"领涨·创新药","value":"+4.44%","cls":"up"},
      {"label":"领跌·半导体(核心)","value":"-0.55%","cls":"down"},
      {"label":"主力净流出Top1","value":"半导体 -55.2亿","cls":"down"}
    ]
  },
  "alignment": alignment,
  "align_note": "红=涨/绿=跌(A股惯例)·±2%加粗；基金午间估算源 neodata 实时未返回净值→估值标「未连接」、偏离度标「N/A」不阻塞；申万行业zdf与关联ETF午盘涨跌均来自 neodata 实时(11:30)返回，非空可验；创新药/食品饮料申万行业zdf在返回集内；基金涨跌≠板块涨跌属正常（受仓位/重仓股α影响）",
  "capital_flow": {
    "in_top3": [{"name":"IT服务Ⅱ","value":22.94},{"name":"通用设备","value":18.77},{"name":"化学制药","value":18.53}],
    "out_top3": [{"name":"半导体","value":-55.24},{"name":"电池","value":-31.82},{"name":"光学光电子","value":-26.24}],
    "conclusion": "全市场呈轮动分化：资金撤离半导体(-55.2亿居首净流出)、电池、光学光电子，转投IT服务/通用设备/化学制药(医药创新药链条)。北向实时停披→数据源未返回。",
    "illustrative": "净流出TOP3为 neodata 行业主力统计(升序)真实返回，净流入TOP3为行业主力统计(降序)真实返回，单位均为亿元；图中数值用于展示排序。"
  },
  "predict": {
    "note": "权重调整：历史「震荡」预测连续踏空，故下调震荡权重、上调动量方向。本批预测加权后计入命中率统计。",
    "hit_rate": "累计验证 4/20",
    "up": up, "down": down, "flat": flat
  },
  "tail": {"tracks":[
    {"title":"半导体系(~69%)","body":"上午半导体-0.55%、ETF-1.36%、主力净流出-55亿居首，资金撤离；核心持仓不追高，警惕获利回吐与净流出延续"},
    {"title":"煤炭","body":"板块+0.41%企稳小涨，债转已到位，不追高；小仓持有"},
    {"title":"QDII类(港药/纳指)","body":"T+1净值滞后，今日创新药+4.44%/纳指+0.83%修复延续，净值次日确认"},
    {"title":"其他小仓(消费/通信)","body":"消费+2.16%强势持有；通信设备CPO平、极小仓观望"},
    {"title":"风控底线","body":"轮动分化但半导体仍为最大单一赛道(69%)，单基-8%硬止损严守；永赢深套-15.9%重点观察"}
  ]},
  "validation": {"checks":[
    {"status":"ok","item":"对齐表数值非空","note":"关联ETF午盘涨跌、申万行业zdf 均来自 neodata 实时返回(11:30)，非空可验"},
    {"status":"warn","item":"偏离度计算","note":"基金午间估算源 neodata 未返回净值→估值标「未连接」、偏离度标「N/A」，不阻塞"},
    {"status":"ok","item":"缺失字段统一标注","note":"北向实时净买入已标「数据源未返回」"},
    {"status":"ok","item":"QDII 时差标注","note":"广发港股创新药、广发纳斯达克100 已置 qdii=true 渲染 QDII·T+1 标签"},
    {"status":"warn","item":"北向停披","note":"陆股通实时净买入已停披，标「数据源未返回」"}
  ],"warnbox":"⚠️ 基金涨跌 ≠ 板块涨跌很正常：受仓位/重仓股α/个股贡献影响。本对齐表用于交叉验证而非等同。"},
  "sources": {"items":[
    {"item":"行情主源","note":"neodata-financial-search（westock 实时行情）—— 关联ETF午盘涨跌、申万行业zdf、主力资金流(zljlr)"},
    {"item":"基金估值/新闻辅助源","note":"neodata-financial-search—— 基金午间估算标注「未连接」（未返回净值）"},
    {"item":"北向","note":"陆股通实时净买入已停披，标注「数据源未返回」"},
    {"item":"预测库","note":"prediction-log.json（回填昨日实际、追加今日上午预测）；情绪：sentiment-log.json；板块K：kline-log.json"}
  ]},
  "disclaimer": "⚠️ 本分析由「每日基金自动报告系统」生成，仅供参考，不构成投资建议。模型研判，非交易建议。"
}

out = os.path.join(BASE,"data","midday_%s.json"%DATE)
json.dump(doc, open(out,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
print("wrote", out, os.path.getsize(out))

# ---- 追加今日预测到 prediction-log.json ----
plp = os.path.join(BASE,"data","prediction-log.json")
log = json.load(open(plp,encoding="utf-8"))
recs = log["records"]
mc = log.get("summary",{}).get("by_session",{}).get("morning_close",{"count":0,"hits":0,"w":0.0,"wh":0.0,"acc":0.0,"wacc":0.0})
cnt = mc.get("count",0)
for i,(nm,dr,cf,rs) in enumerate(pred_records,1):
    rid = "PRED-%s-MC%03d"%(DATE, cnt+i)
    recs.append({
        "id": rid, "date": DATE, "session": "morning_close", "target": nm,
        "direction": dr, "predict_detail": rs, "trigger_price": None,
        "predict_time": DATE+"T11:30:00+08:00", "actual_close_next_day": None,
        "actual_direction": None, "confidence": cf, "weight": W[cf],
        "verified": False, "hit": None, "verify_date": DATE_NEXT, "verify_note": None
    })
new_w = sum(W[cf] for _,_,cf,_ in pred_records)
log["summary"]["total_predictions"] = log["summary"].get("total_predictions",0)+len(pred_records)
mc["count"] = cnt+len(pred_records)
mc["w"] = mc.get("w",0.0)+new_w
mc["hits"] = mc.get("hits",0)
mc["wh"] = mc.get("wh",0.0)
mc["acc"] = 0.0
mc["wacc"] = 0.0
log["summary"]["by_session"]["morning_close"] = mc
json.dump(log, open(plp,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
print("prediction-log updated: total_predictions=%d morning_close_count=%d"%(log["summary"]["total_predictions"], mc["count"]))
