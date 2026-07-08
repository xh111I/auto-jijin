import json, os, datetime

BASE = "C:/Users/LEGION/Nutstore/1/daily-report/data"
REP = os.path.join(BASE, "reports", "2026-07-08")
os.makedirs(REP, exist_ok=True)
C = json.load(open(os.path.join(BASE, "consolidated_2026-07-08.json"), encoding="utf-8"))
DATE = "2026-07-08"
TODAY = "2026-07-08"

# ============ 1. 资金流 / 市场 ============
indices = C["indices"]
sectors = C["sectors_0708"]
# mainflow narrative (from neodata docs)
mainflow_notes = [
    "计算机行业获主力净流入 +76.45 亿元（全市场最强）",
    "计算机、通信板块合计吸金超 119 亿元",
    "电子（含半导体/存储）主力净流出约 187 亿元，半导体存储与新能源遭抛售",
    "AI 算力产业链受资金追捧，但半导体存储端承压",
]
breadth_ratio = "约 1:7（涨跌比，来源：7月8日市场舆情，⚠️ 估算）"
northbound_status = "数据源未返回（陆股通实时净买入披露已于2024年暂停，neodata 未提供该字段）"

# ============ 2. α (already in C['funds']) ============
funds = C["funds"]

# ============ 3. 调仓建议 ============
# concentration
total_mv = C["total_mv"]
semic_exposure = sum(f["weight_pct"] for f in funds if "半导体" in (f["sector"] or "") and f["status"]=="active")
top2 = sorted([f for f in funds if f["status"]=="active"], key=lambda x:-(x["weight_pct"] or 0))[:2]
top2_pct = sum(f["weight_pct"] for f in top2)
high_risk = [f["name"] for f in funds if f["risk_flag"]=="HIGH"]
rebalance = []
if top2_pct > 50:
    rebalance.append(("高集中度", "前两大持仓（%s %.1f%% + %s %.1f%%）合计 %.1f%%，显著高于分散基准；单一持仓 %s 达 %.1f%% 已超策略上限 30%%。" % (
        top2[0]["name"][:8], top2[0]["weight_pct"], top2[1]["name"][:8], top2[1]["weight_pct"], top2_pct, top2[0]["name"][:8], top2[0]["weight_pct"]),
        "建议将 %s 由 %.1f%% 降至 ≤30%%，释放资金用于分散。" % (top2[0]["name"][:8], top2[0]["weight_pct"])))
if semic_exposure > 50:
    rebalance.append(("半导体暴露过高", "半导体/科技类（含AI、集成、存储）活跃持仓合计约 %.1f%%，单一行业风险集中。" % semic_exposure,
        "延续「煤炭→债券」降风险思路，适度将半导体仓位向债券/消费/港股创新药再平衡，目标半导体暴露 ≤60%。"))
if high_risk:
    rebalance.append(("高风险管理", "%s 标记为 HIGH（存储芯片，且隔夜美存储暴跌 美光-9%%/闪迪-14%%），07-07 α=%s 显著为负。" % (high_risk[0][:8], [f["alpha"] for f in funds if f["risk_flag"]=="HIGH"][0]),
        "维持谨慎，不追加；若跌破 -8%% 硬止损线立即执行，不因「市场恐惧」扛单。"))
# dormant small positions
rebalance.append(("新建小仓观察", "财通集成/财通成长/天弘通信/嘉实消费为近期新建小仓（合计 <5%），属 CPO/消费试探性布局。",
        "继续小额观察，待趋势确认再加码，不做重仓押注。"))
rebalance.append(("已排队的降风险操作", "待确认：煤炭→鹏华丰诚债转换 247.77 份（主动降风险）、定投纳指 10 元。",
        "待交易确认后在下个复盘更新持仓结构。"))

# ============ 4. 预测命中率 ============
plog = json.load(open(os.path.join(BASE, "prediction-log.json"), encoding="utf-8"))
# map target -> sector proxy 07-08
target_proxy = {
    "东方人工智能": (sectors["半导体"]+sectors["人工智能"])/2,
    "东方阿尔法科": (sectors["半导体"]+sectors["人工智能"])/2,
    "永赢先锋半导体": sectors["半导体"],
    "广发港股创新药": sectors["港股创新药"],
    "广发纳斯达克100": sectors["纳斯达克100"],
    "富国中证煤炭": sectors["煤炭"],
    "财通集成电路": sectors["半导体"],
    "财通成长优选": sectors["人工智能"],
    "天弘中证全指": sectors["CPO通信"],
    "嘉实中证主要消费": sectors["中证主要消费"],
}
def classify(x):
    if x is None: return None
    if x > 0.5: return "涨"
    if x < -0.5: return "跌"
    return "震荡"

backfilled = 0
hits = 0
w_total = 0.0
w_hit = 0.0
for rec in plog["records"]:
    tgt = rec["target"]
    if tgt in target_proxy and rec.get("verified") is False:
        actual = target_proxy[tgt]
        direction = classify(actual)
        hit = (direction == rec["direction"])
        rec["actual_close_next_day"] = round(actual, 2)
        rec["actual_direction"] = direction
        rec["verified"] = True
        rec["hit"] = hit
        rec["verify_note"] = "实际值采用关联板块/指数 07-08 真实收盘变动作为估值代理（基金官方净值 07-08 未更新）"
        backfilled += 1
        w_total += rec["weight"]
        if hit:
            hits += 1
            w_hit += rec["weight"]

overall_acc = round(hits/backfilled*100, 1) if backfilled else 0.0
weighted_acc = round(w_hit/w_total*100, 1) if w_total else 0.0

# append new predictions for 07-09
new_preds = [
    ("东方人工智能主题混合C","震荡","光模块量产/CPO热点延续，但半导体短期消化获利盘，方向模糊","中",0.7),
    ("东方阿尔法科技优选混合C","震荡","同半导体板块，缺乏明确催化，跟随震荡","中",0.7),
    ("永赢先锋半导体智选混合C","震荡","隔夜美存储暴跌(美光-9%/闪迪-14%)但A股半导体抗跌，方向不确定、波动放大","低",0.3),
    ("广发港股创新药ETF联接(QDII)C","震荡","07-08 再跌-1.39%已近超卖，政策面利好但与大盘共振弱","低",0.3),
    ("广发纳斯达克100ETF联接","震荡","纳指 07-08 微跌-0.44%，美股方向待隔夜指引","中",0.7),
    ("富国中证煤炭指数C","震荡","07-08 逆势+1.2%显强，但煤价预期偏弱，持续性存疑","低",0.3),
    ("财通集成电路产业股票C","震荡","半导体板块横盘，跟随基准震荡","中",0.7),
    ("财通成长优选混合C","震荡","成长风格偏弱(-0.34%)，无独立催化","低",0.3),
    ("天弘中证全指通信设备指数C","震荡","CPO主题强但当日-0.39%，多空分歧","低",0.3),
    ("嘉实中证主要消费ETF发起联接C","震荡","消费估值低位、07-08 近平，等待拐点","低",0.3),
]
next_id = 1
for name, direction, detail, conf, w in new_preds:
    plog["records"].append({
        "id": "PRED-%s-%03d" % (TODAY, next_id),
        "date": TODAY, "session": "evening_review", "target": name,
        "direction": direction, "predict_detail": detail, "trigger_price": None,
        "predict_time": "2026-07-08T21:25:00+08:00", "actual_close_next_day": None,
        "actual_direction": None, "confidence": conf, "weight": w,
        "verified": False, "hit": None, "verify_date": "2026-07-09"
    })
    next_id += 1

plog["summary"] = {
    "total_predictions": len([r for r in plog["records"] if r["session"]=="evening_review"]),
    "total_hits": hits,
    "weighted_accuracy_pct": weighted_acc,
    "by_target": {},
    "by_session": {"morning_close":{"count":0,"hits":0,"accuracy_pct":0.0},
                   "pre_close":{"count":0,"hits":0,"accuracy_pct":0.0},
                   "evening_review":{"count":backfilled,"hits":hits,"accuracy_pct":overall_acc}}
}
json.dump(plog, open(os.path.join(BASE,"prediction-log.json"),"w",encoding="utf-8"), ensure_ascii=False, indent=2)

# ============ 5. 收盘情绪校准 (fear-greed) ============
fg_weights = {"breadth":0.15,"limit_up_down":0.10,"main_flow":0.15,"northbound":0.12,
              "margin":0.08,"volume":0.10,"vix":0.15,"erp":0.15}
fg_factors = {
    "breadth": 12,        # 涨跌比1:7 -> 极度恐惧区
    "limit_up_down": 50,  # [数据缺失] 中性计入
    "main_flow": 35,      # 电子净流出187亿，半导体遭抛售
    "northbound": 50,     # [数据缺失]
    "margin": 50,         # [数据缺失]
    "volume": 45,         # 缩量
    "vix": 50,            # [数据缺失]
    "erp": 50,            # [数据缺失]
}
fg_missing = [k for k,v in fg_factors.items() if v==50 and k in ("limit_up_down","northbound","margin","vix","erp")]
fg_index = round(sum(fg_factors[k]*fg_weights[k] for k in fg_factors), 1)
def fg_level(x):
    if x<20: return "极度恐惧"
    if x<40: return "恐惧"
    if x<60: return "中性"
    if x<80: return "贪婪"
    return "极度贪婪"
fg_level_str = fg_level(fg_index)
fg_action = "中性偏恐惧。8因子中5项（涨跌停/北向/融资/VIX/ERP）数据源未返回，按协议以中性50计入，致综合指数被拉向中性；但广度(涨跌比约1:7)显示真实情绪偏恐惧。当前账户半导体集中度过高(约%.0f%%)，情绪恐惧+高集中度下不宜加仓，维持防御，严守单基-8%%硬止损。" % semic_exposure

sentiment_record = {
    "date": DATE, "fear_greed_index": fg_index, "level": fg_level_str,
    "factors": fg_factors, "factor_weights": fg_weights, "missing_factors": fg_missing,
    "sentiment_action": fg_action,
    "note": "收盘校准：基于可得因子(广度/主力资金/量能)估算；北向/融资/VIX/ERP未返回按中性计。⚠️ 模型研判，非交易建议。"
}
slog = json.load(open(os.path.join(BASE,"sentiment-log.json"),encoding="utf-8"))
slog["records"].append(sentiment_record)
json.dump(slog, open(os.path.join(BASE,"sentiment-log.json"),"w",encoding="utf-8"), ensure_ascii=False, indent=2)

# ============ 6. 板块K信号 ============
def ksig(name, chg, trend_s, trend_j, vp_s, vp_j, pattern, mainf, close_sig, bias, meaning):
    return {"sector":name,"change_0708":chg,"trend_score":trend_s,"trend_judg":trend_j,
            "vp_score":vp_s,"vp_judg":vp_j,"pattern":pattern,"main_force":mainf,
            "close_signal":close_sig,"bias":bias,"preclose_meaning":meaning}
kline_records = [
    ksig("半导体", sectors["半导体"], 38, "偏空（近两日微跌，均线纠缠）", 50, "价平量平，观望", "无明确形态", "电子净流出187亿，分歧/出货迹象 ⚠️模型研判", "收盘近平，未站上/跌破关键均线", "偏空", "A股抗住隔夜美存储暴跌显韧性，但主力资金撤离，观望为宜"),
    ksig("人工智能", sectors["人工智能"], 35, "偏空（07-08 -0.34%）", 48, "AI算力吸金但整体偏弱", "无明确形态", "计算机+76亿但AI指数仍跌，内部分化 ⚠️模型研判", "收盘偏弱", "偏空", "算力链受捧、应用端承压，等待企稳"),
    ksig("CPO通信", sectors["CPO通信"], 45, "中性（主题强、当日弱）", 52, "光模块量产热点 vs 当日-0.39%", "无明确形态", "主题资金活跃但分歧 ⚠️模型研判", "收盘偏弱", "中性", "光模块量产实锤支撑中长期，短期震荡"),
    ksig("煤炭", sectors["煤炭"], 72, "偏多（07-08 +1.2% 逆势强）", 70, "价涨，资金偏流入", "无明确顶部信号", "防御属性凸显，资金避险 ⚠️模型研判", "收盘偏强", "偏多", "高股息防御受捧；账户正转债券降风险，不追高"),
    ksig("中证主要消费", sectors["中证主要消费"], 48, "中性（07-08 -0.01% 平）", 50, "地量持平", "估值低位，缩量止跌迹象", "左侧布局资金零星 ⚠️模型研判", "收盘近平", "中性", "估值低位等待拐点，小仓试探"),
]
klog = json.load(open(os.path.join(BASE,"kline-log.json"),encoding="utf-8"))
for r in kline_records:
    r["date"]=DATE; r["note"]="⚠️ 模型研判，形态/主力行为为AI推断"
klog["records"].extend(kline_records)
json.dump(klog, open(os.path.join(BASE,"kline-log.json"),"w",encoding="utf-8"), ensure_ascii=False, indent=2)

# save computed summary for HTML
calc = {
    "fg_index": fg_index, "fg_level": fg_level_str, "fg_factors": fg_factors, "fg_missing": fg_missing,
    "fg_action": fg_action, "overall_acc": overall_acc, "weighted_acc": weighted_acc,
    "backfilled": backfilled, "hits": hits, "w_total": w_total, "w_hit": w_hit,
    "semic_exposure": round(semic_exposure,1), "top2_pct": round(top2_pct,1),
    "rebalance": rebalance, "mainflow_notes": mainflow_notes, "breadth_ratio": breadth_ratio,
    "northbound_status": northbound_status, "kline": kline_records,
}
json.dump(calc, open(os.path.join(BASE,"calc_2026-07-08.json"),"w",encoding="utf-8"), ensure_ascii=False, indent=2)
print("logs written. fg_index=",fg_index, fg_level_str, "| hitrate overall=",overall_acc,"% weighted=",weighted_acc,"% | backfilled=",backfilled)
