# -*- coding: utf-8 -*-
"""构建 2026-07-10 晚间复盘：consolidated / calc + 回填 prediction/sentiment/kline 日志。"""
import json, os

BASE = "C:/Users/LEGION/Nutstore/1/daily-report/data"
DATE = "2026-07-10"

def load(p, d):
    try:
        return json.load(open(os.path.join(BASE, p), encoding="utf-8"))
    except Exception:
        return d

def save(p, obj):
    json.dump(obj, open(os.path.join(BASE, p), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

# ---------- 07-10 各标的收盘/板块代理（真实收盘, 全天） ----------
# 半导体系全天 -6.26%(主线重挫)，科创50 -5.53%，创业板 -4.37%，沪深300 -1.96%
SEMIC = -6.26
HS300 = -1.96
PROXY = {
    "东方人工智能主题混合C": SEMIC,
    "东方阿尔法科技优选混合C": SEMIC,
    "永赢先锋半导体智选混合C": SEMIC,
    "广发港股创新药ETF联接(QDII)C": 3.25,
    "鹏华丰诚债券C": 0.02,
    "财通集成电路产业股票C": SEMIC,
    "财通成长优选混合C": HS300,
    "广发纳斯达克100ETF联接(QDII)C": 0.83,
    "天弘中证全指通信设备指数C": -0.12,
    "富国中证煤炭指数C": 0.41,
    "嘉实中证主要消费ETF发起联接C": 2.59,
}
SHORT = {
    "东方人工智能主题混合C": "东方AI",
    "东方阿尔法科技优选混合C": "东阿尔法",
    "永赢先锋半导体智选混合C": "永赢半导",
    "广发港股创新药ETF联接(QDII)C": "港创新药",
    "鹏华丰诚债券C": "鹏华债",
    "财通集成电路产业股票C": "财通集成",
    "财通成长优选混合C": "财通成长",
    "广发纳斯达克100ETF联接(QDII)C": "广发纳指",
    "天弘中证全指通信设备指数C": "天弘通信",
    "富国中证煤炭指数C": "富国煤炭",
    "嘉实中证主要消费ETF发起联接C": "嘉实消费",
}

def direction(a):
    if a is None: return None
    if a > 0.5: return "涨"
    if a < -0.5: return "跌"
    return "震荡"

# ================= 1) consolidated_2026-07-10.json =================
wl = load("../config/watchlist.json", {})
holds = {h["name"]: h for h in wl.get("holdings", [])}

funds = []
tot_mv = 0.0
w_ret = 0.0
for name, h in holds.items():
    mv = h.get("market_value", 0.0)
    tot_mv += mv
    dp = PROXY.get(name)
    alpha = round(dp - HS300, 2) if dp is not None else None
    funds.append({
        "name": name,
        "short": SHORT.get(name, name[:4]),
        "sector": h.get("sector", ""),
        "nav": None,                      # 官方净值未更新
        "daily_0707": dp,                 # 07-10 日收益(板块代理, 沿用字段名)
        "ytd_pct": None,
        "alpha": alpha,                   # α = 板块代理 − 沪深300
        "ranking": None,
        "proxy_0708": dp,                 # 关联板块代理(沿用字段名)
        "top10": [],
        "risk_flag": "HIGH" if h.get("risk_flag") else None,
        "status": h.get("status", "active"),
        "weight_pct": h.get("weight_pct"),
        "benchmark_note": "α 基准=沪深300(-1.96%)",
    })
    if dp is not None and h.get("weight_pct"):
        w_ret += h["weight_pct"] / 100.0 * dp

acct_ret = round(w_ret, 2)                 # 持仓加权估算日收益
acct_pnl = round(acct_ret / 100.0 * tot_mv, 2)

news = [
    "【商业航天】长征十号乙运载火箭 12:15 首飞成功，午后卫星导航/航天装备产业链集体爆发，航天装备指数+10.2%、多只卫星ETF涨停，资金涌入逾百亿",
    "【半导体】昨日+8.58%极端超买后今日高位巨阴，半导体主线-6.26%、科创50单日-5.53%，主力净流出-269亿领衔全市场，获利盘集中兑现",
    "【医药】港股创新药+3.25%续强，化学制药主力净流入+18.5亿；创新药出海BD交易与南向资金托底，成防御新主线",
    "【消费】食品饮料+2.16%、消费ETF+2.59%修复，估值低位补涨；资金自高位科技高低切至消费/医药/军工",
    "【资金面】全市场放量回调：上证-205亿/深证-245亿/沪深300-363亿/创业板-163亿主力净流出，价跌量增",
    "【指数】上证3996.16(-1.0%)守住4000关口下沿；创业板3842.73(-4.37%)、科创50 2064.98(-5.53%)领跌；上证50抗跌(-1.34%守均线)",
    "【港股】恒生科技4730.32(-0.03%)平盘，港股创新药对冲科技回调；南向资金延续净买入",
    "【风险】半导体龙头放量下挫，科技情绪短线退潮；需警惕高位巨阴后的破位加速",
    "【策略】账户盘中已卖出东方AI 1/3锁利，回收现金约1589元(占总资产12.11%)，东方AI权重36.3%→24.21%已解除超30%上限",
    "【外围】美股/中东扰动待隔夜指引，纳指ETF当日+0.83%相对强势(QDII T+1净值次日确认)",
]

consolidated = {
    "date": DATE,
    "updated_at": "2026-07-10 22:30 晚间复盘",
    "indices": {
        "上证指数": {"close": 3996.16, "change_pct": -1.0, "date": DATE},
        "创业板指": {"close": 3842.73, "change_pct": -4.37, "date": DATE},
        "沪深300": {"close": 4780.79, "change_pct": -1.96, "date": DATE},
    },
    "funds": funds,
    "account_est_return_0708_pct": acct_ret,
    "account_est_pnl_0708": acct_pnl,
    "total_mv": round(tot_mv, 2),
    "news": news,
}
save(f"consolidated_{DATE}.json", consolidated)
print("consolidated:", acct_ret, "%", acct_pnl, "元  total_mv", round(tot_mv, 2))

# ================= 2) 回填 prediction-log.json =================
plog = load("prediction-log.json", {"records": []})

# 07-09 verify(07-10) 实际值映射
ACT = {
    "PRED-2026-07-09-MC001": SEMIC, "PRED-2026-07-09-MC002": SEMIC,
    "PRED-2026-07-09-MC003": SEMIC, "PRED-2026-07-09-MC004": SEMIC,
    "PRED-2026-07-09-MC005": 3.25, "PRED-2026-07-09-MC006": 0.83,
    "PRED-2026-07-09-MC007": -0.12, "PRED-2026-07-09-MC008": 0.41,
    "PRED-2026-07-09-MC009": 2.59, "PRED-2026-07-09-MC010": HS300,
    "PRED-2026-07-09-MC011": 0.02,
    "PRED-2026-07-09-ER001": SEMIC, "PRED-2026-07-09-ER002": SEMIC,
    "PRED-2026-07-09-ER003": SEMIC, "PRED-2026-07-09-ER004": 3.25,
    "PRED-2026-07-09-ER005": 0.02, "PRED-2026-07-09-ER006": 0.41,
    "PRED-2026-07-09-ER007": 2.59, "PRED-2026-07-09-ER008": 0.83,
    "PRED-2026-07-09-ER009": SEMIC, "PRED-2026-07-09-ER010": HS300,
    "PRED-2026-07-09-ER011": -0.12,
}
VNOTE = ("实际值采用关联板块/ETF 2026-07-10 收盘变动作为估值代理："
         "半导体-6.26%/科创50-5.53% 全市场获利回吐；港股创新药+3.25%；纳指+0.83%；"
         "消费+2.59%；煤炭+0.41%；通信-0.12%；债≈平")

for rec in plog["records"]:
    rid = rec.get("id")
    if rid in ACT and not rec.get("verified"):
        a = ACT[rid]
        d = direction(a)
        rec["actual_close_next_day"] = a
        rec["actual_direction"] = d
        rec["hit"] = (rec["direction"] == d)
        rec["verified"] = True
        rec["verify_note"] = VNOTE

# 追加 07-10 晚间预测(→07-11)
er_new = [
    ("ER001", "东方人工智能主题混合C", "震荡", "中", 0.7, "半导体高位巨阴-6.26%回吐后超跌，07-11 或技术性反弹但主力持续流出，方向模糊；不追高、扛住看-8%止损"),
    ("ER002", "东方阿尔法科技优选混合C", "震荡", "中", 0.7, "同半导体板块，超买修复后跟随震荡"),
    ("ER003", "永赢先锋半导体智选混合C", "震荡", "低", 0.3, "存储子板块偏弱+持仓深套，反弹力度存疑"),
    ("ER004", "广发港股创新药ETF联接(QDII)C", "涨", "中", 0.7, "创新药+3.25%成新主线，BD/南向托底，T+1净值补涨概率高"),
    ("ER005", "鹏华丰诚债券C", "震荡", "低", 0.3, "纯债安全垫，日内≈平，与权益脱钩"),
    ("ER006", "富国中证煤炭指数C", "震荡", "低", 0.3, "煤炭+0.41%窄幅企稳，几乎清仓不操作"),
    ("ER007", "嘉实中证主要消费ETF发起联接C", "涨", "中", 0.7, "消费+2.59%修复延续，估值低位补涨"),
    ("ER008", "广发纳斯达克100ETF联接(QDII)C", "震荡", "中", 0.7, "纳指+0.83%相对强，美股方向待隔夜，T+1"),
    ("ER009", "财通集成电路产业股票C", "震荡", "低", 0.3, "半导体小仓，随板块超跌反复"),
    ("ER010", "财通成长优选混合C", "震荡", "低", 0.3, "沪深300成长-1.96%，跟随大盘弱震荡"),
    ("ER011", "天弘中证全指通信设备指数C", "震荡", "低", 0.3, "通信-0.12%平、CPO主题退潮，极小仓观望"),
]
existing_ids = {r["id"] for r in plog["records"]}
for sfx, tgt, dire, conf, w, detail in er_new:
    rid = f"PRED-2026-07-10-{sfx}"
    if rid in existing_ids:
        continue
    plog["records"].append({
        "id": rid, "date": DATE, "session": "evening_review",
        "target": tgt, "direction": dire, "predict_detail": detail,
        "trigger_price": None, "predict_time": "2026-07-10T22:30:00+08:00",
        "actual_close_next_day": None, "actual_direction": None,
        "confidence": conf, "weight": w, "verified": False, "hit": None,
        "verify_date": "2026-07-11", "verify_note": None,
    })

# 重算 summary
recs = plog["records"]
verified = [r for r in recs if r.get("verified")]
hits = [r for r in verified if r.get("hit")]
def wsum(rs): return sum(r.get("weight", 0) for r in rs)
by = {}
for sess in ("evening_review", "morning_close"):
    sv = [r for r in verified if r.get("session") == sess]
    sh = [r for r in sv if r.get("hit")]
    by[sess] = {
        "count": len(sv), "hits": len(sh),
        "w": round(wsum(sv), 4), "wh": round(wsum(sh), 4),
        "acc": round(len(sh)/len(sv)*100, 1) if sv else 0.0,
        "wacc": round(wsum(sh)/wsum(sv)*100, 1) if wsum(sv) else 0.0,
    }
plog["summary"] = {
    "total_predictions": len(recs),
    "verified": len(verified),
    "total_hits": len(hits),
    "simple_accuracy_pct": round(len(hits)/len(verified)*100, 1) if verified else 0.0,
    "weighted_accuracy_pct": round(wsum(hits)/wsum(verified)*100, 1) if wsum(verified) else 0.0,
    "by_session": by,
}
save("prediction-log.json", plog)
print("prediction summary:", plog["summary"]["verified"], "verified /",
      plog["summary"]["total_hits"], "hits  simple",
      plog["summary"]["simple_accuracy_pct"], "wacc",
      plog["summary"]["weighted_accuracy_pct"])

# 本次 07-10 回填口径（用于 calc 展示）
bf = [r for r in verified if r.get("verify_date") == DATE]
bf_hits = [r for r in bf if r.get("hit")]
overall_acc = round(len(bf_hits)/len(bf)*100, 1)
w_total = round(wsum(bf), 2)
w_hit = round(wsum(bf_hits), 2)
weighted_acc = round(w_hit/w_total*100, 1) if w_total else 0.0
print("07-10 backfill:", len(bf), "rows", len(bf_hits), "hits  acc", overall_acc, "wacc", weighted_acc)

# ================= 3) sentiment-log.json 追加 07-10 =================
slog = load("sentiment-log.json", {"records": []})
if not any(r.get("date") == DATE for r in slog["records"]):
    slog["records"].append({
        "date": DATE, "fear_greed_index": 50, "level": "中性",
        "factors": {"breadth": 50, "limit_up_down": 50, "main_flow": 25,
                     "northbound": 50, "margin": 50, "volume": 70, "vix": 50, "erp": 62},
        "factor_weights": {"breadth": 0.15, "limit_up_down": 0.10, "main_flow": 0.15,
                            "northbound": 0.12, "margin": 0.08, "volume": 0.10,
                            "vix": 0.15, "erp": 0.15},
        "missing_factors": ["breadth", "limit_up_down", "northbound", "margin", "vix"],
        "sentiment_action": "中性——盈利半导体仓分批止盈、不接飞刀；不触发>75减仓预警；严守-8%硬止损。",
        "note": ("综合约50中性区间；但全市场主力净流出显著(上证-205/深证-245/沪深300-363亿，"
                 "半导体-269亿领衔)，局部科技退潮。5/8因子源缺失按中性50计，真实广度普跌偏恐惧。"),
    })
    save("sentiment-log.json", slog)
    print("sentiment appended", DATE)

# ================= 4) kline-log.json 追加 07-10 =================
klog = load("kline-log.json", {"records": []})
KLN = [
    {"sector": "半导体", "change_0708": SEMIC, "trend_score": 25, "trend_judg": "偏空",
     "vp_score": 20, "vp_judg": "恐慌抛售", "pattern": "高位巨阴", "main_force": "主力净流出-269亿",
     "close_signal": "跌破MA5", "bias": "偏空",
     "preclose_meaning": "昨日+8.58%极端超买后单日重挫-6.26%，获利盘集中兑现，短线转弱需防破位加速", "date": DATE, "note": ""},
    {"sector": "军工/航天装备", "change_0708": 10.2, "trend_score": 82, "trend_judg": "强多",
     "vp_score": 78, "vp_judg": "放量突破", "pattern": "涨停潮/长阳", "main_force": "主力大幅净流入",
     "close_signal": "站上所有均线", "bias": "偏多",
     "preclose_meaning": "长征十号乙首飞点燃商业航天，午后爆发资金涌入逾百亿，新主线确立但需防次日高开回落", "date": DATE, "note": ""},
    {"sector": "港股创新药", "change_0708": 3.25, "trend_score": 70, "trend_judg": "偏多",
     "vp_score": 62, "vp_judg": "温和放量", "pattern": "阳线上攻", "main_force": "化学制药净流入+18.5亿",
     "close_signal": "站上MA5", "bias": "偏多",
     "preclose_meaning": "BD出海+南向托底，防御新主线；持仓QDII T+1净值次日补涨", "date": DATE, "note": ""},
    {"sector": "大消费/食品饮料", "change_0708": 2.59, "trend_score": 60, "trend_judg": "偏多",
     "vp_score": 58, "vp_judg": "温和放量", "pattern": "低位反弹", "main_force": "资金高低切流入",
     "close_signal": "均线纠缠上行", "bias": "偏多",
     "preclose_meaning": "估值低位补涨，高低切承接资金，持续性待量能确认", "date": DATE, "note": ""},
    {"sector": "通信设备/CPO", "change_0708": -0.12, "trend_score": 45, "trend_judg": "震荡",
     "vp_score": 50, "vp_judg": "平量", "pattern": "冲高回落", "main_force": "主力小幅流出",
     "close_signal": "均线纠缠", "bias": "中性",
     "preclose_meaning": "CPO主题退潮，随半导体承压转弱，极小仓观望", "date": DATE, "note": ""},
]
existd = {(r.get("sector"), r.get("date")) for r in klog["records"]}
added = 0
for k in KLN:
    if (k["sector"], k["date"]) not in existd:
        klog["records"].append(k); added += 1
if added:
    save("kline-log.json", klog)
print("kline appended", added, "records")

# ================= 5) calc_2026-07-10.json =================
top2 = round(sum(sorted([f.get("weight_pct", 0) for f in funds], reverse=True)[:2]), 1)
calc = {
    "date": DATE,
    "fg_index": 50, "fg_level": "中性",
    "fg_factors": {"breadth": 50, "limit_up_down": 50, "main_flow": 25,
                    "northbound": 50, "margin": 50, "volume": 70, "vix": 50, "erp": 62},
    "fg_missing": ["breadth", "limit_up_down", "northbound", "margin", "vix"],
    "fg_action": "中性——盈利半导体仓分批止盈、不接飞刀；未达>75减仓预警；严守-8%硬止损，现金12%待急跌低吸。",
    "overall_acc": overall_acc, "weighted_acc": weighted_acc,
    "backfilled": len(bf), "hits": len(bf_hits),
    "w_total": w_total, "w_hit": w_hit,
    "semic_exposure": 65.4, "top2_pct": top2,
    "breadth_ratio": "约 1:4（个股普跌）",
    "northbound_status": "N/A（neodata 未返回北向数据）",
    "mainflow_notes": [
        "全市场主力净流出显著：上证 -205.4亿 / 深证 -244.6亿 / 沪深300 -363.3亿 / 创业板 -163.5亿",
        "半导体板块主力净流出 -269亿 领衔全市场，高位科技集中出货",
        "资金高低切：流出半导体/CPO/证券 → 流入军工航天(航天装备+10.2%)、医药(港股创新药+3.25%)、消费(+2.59%)",
        "长征十号乙 12:15 首飞成功点燃商业航天，午后卫星/航天产业链爆发、资金涌入逾百亿",
        "北向资金：neodata 未返回，标注 N/A",
    ],
    "rebalance": [
        ["半导体暴露过高",
         "半导体系(东方AI/东方阿尔法/永赢/财通集成)占总资产 65.4%、占持仓 74.5%，今日单日 -6.26% 被资金抽血最重；已盘中卖东方AI 1/3 降敞口。",
         "半导体属获利回吐非基本面恶化，倾向扛(严守-8%硬止损)；反弹至成本线附近继续分批降至占总资产≤60%，不追跌不加仓。"],
        ["高集中度",
         f"前二持仓(东方阿尔法+东方AI)合计约 {top2}%，东方阿尔法 29.1% 逼近 30% 单基上限。",
         "东方阿尔法反弹即减至≤25%；用回款分散至防御/低位轮动，降低单一赛道波动。"],
        ["高风险管理",
         "永赢半导绝对敞口 1856元(每跌1%亏18.5元)、港药持续亏损；情绪中性但科技短线退潮。",
         "永赢触-2%止损50%；港药按两级阈值(-5%减半/回升-1%内减1/3)；保留鹏华债/纳指防御底仓。"],
        ["新建小仓观察",
         "商业航天(长征十号乙首飞)与创新药/消费成新主线，账户尚无相关暴露。",
         "将 航天ETF/卫星ETF、创新药ETF、消费ETF 加入 watchlist；用半导体止盈回款小仓试建(单笔≤总仓15%)，次日确认持续性再加。"],
        ["已排队的降风险操作",
         "现金 1589元(12.11%)为尾盘急跌低吸弹药，勿闲置；调仓资金全部来自止盈回款不新增投入。",
         "分3-4批、每周一批执行再平衡；单日板块涨跌超3%暂停，避免追涨杀跌。"],
    ],
    "kline": KLN,
}
save(f"calc_{DATE}.json", calc)
print("calc written: overall", overall_acc, "wacc", weighted_acc, "top2", top2)
print("DONE")
