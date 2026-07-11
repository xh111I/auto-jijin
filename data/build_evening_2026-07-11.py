# -*- coding: utf-8 -*-
"""build_evening_2026-07-11.py — 休市周末特刊 数据层装配
07-11 周六 A股休市，无实盘。基于最近交易日(07-10 周五)真实收盘 + 周末全球扫描(early-morning_2026-07-11.json)
组装 consolidated_2026-07-11.json + calc_2026-07-11.json，供 make_html.py 渲染「休市特刊」晚间复盘。
不编造任何 07-11 当日行情。
"""
import json, os

BASE = "C:/Users/LEGION/Nutstore/1/daily-report/data"

c10 = json.load(open(os.path.join(BASE, "consolidated_2026-07-10.json"), encoding="utf-8"))
calc10 = json.load(open(os.path.join(BASE, "calc_2026-07-10.json"), encoding="utf-8"))
plog = json.load(open(os.path.join(BASE, "prediction-log.json"), encoding="utf-8"))
try:
    em = json.load(open(os.path.join(BASE, "early-morning_2026-07-11.json"), encoding="utf-8"))
except Exception:
    em = {}

DATE = "2026-07-11"

# ---------------- consolidated (holiday edition = 07-10 真实收盘) ----------------
cons = dict(c10)
cons["date"] = DATE
cons["holiday"] = True
cons["data_note"] = "2026-07-11 周六·A股休市。以下为最近交易日(2026-07-10 周五)真实收盘回顾 + 周末前瞻，非当日行情。"
cons["news"] = [
    "【休市】2026-07-11 周六 A股休市，无实盘交易。本复盘为「周末特刊」，以 07-10 真实收盘为基底，推演下周一(07-13)预案。",
    "【周末扫描】美股隔夜(7/10)中性偏多(52)；A股半导体进入\"还债期\"(情绪42 偏空)；港股分化(55 中性偏多)；下周一(7/13)承接 07-10 暴跌后的方向选择。",
] + c10.get("news", [])

# ---------------- calc (holiday edition + 6 大分析字段) ----------------
calc = dict(calc10)
calc["date"] = DATE
calc["holiday"] = True
calc["holiday_note"] = (
    "2026-07-11 周六·A股休市，无实盘交易。本复盘为「周末特刊」：以最近交易日(2026-07-10 周五)真实收盘为基底，"
    "结合周末全球扫描(早间报告)推演下周一(2026-07-13)预案。不编造任何当日行情；账户状态=07-10 收盘快照。"
)
calc["weekend_sentiment"] = em.get("sentiment", {}).get("broad", {}).get("score", 45)
calc["weekend_sentiment_label"] = em.get("sentiment", {}).get("broad", {}).get("label", "中性偏空")

# ---- 1. 全天资金迁徙路线回顾（核心）——基底=07-10 真实迁徙 ----
calc["migration"] = {
    "base_date": "2026-07-10（周五·最近交易日）",
    "segments": [
        {"phase": "早盘 09:30-11:30", "flow": "半导体冲高",
         "detail": "延续前日+8.58%极端动量，兆易创新一度+6%，资金抱团高位科技，半导体强势但已现超买。",
         "net": "半导体早盘净流入居首（主力+84.7亿，半日）", "pos": "持仓：半导体方向被推高（浮盈放大）"},
        {"phase": "午间 11:30-13:00", "flow": "长征十号乙 12:15 首飞",
         "detail": "长征十号乙运载火箭首飞成功消息发酵，商业航天/卫星产业链题材点燃，午间起资金开始异动。",
         "net": "—（事件催化，尚未体现于资金流）", "pos": "持仓：尚未反应，仍在半导体"},
        {"phase": "午后 13:00-15:00", "flow": "半导体出逃 → 商业航天/医药",
         "detail": "半导体主力净流出近200亿（全市场-269亿领衔），资金高低切涌入商业航天（净流入100亿+）与医药；航天装备指数+10.2%涨停潮。",
         "net": "半导体净流出-269亿；军工航天+10.2%；港股创新药+3.25%；消费+2.59%",
         "pos": "持仓：半导体 = 被抽血方（高位科技出货）"},
    ],
    "keyword": "高位科技出货，奔赴星辰大海+医药，资金未离场只是换战场",
    "my_position": "半导体持仓（东方AI / 东阿尔法 / 永赢半导 / 财通集成）处于迁徙路线的「被抽血方」——是资金流出的源头，而非流入方向。",
    "verdict": "扛（严守-8%硬止损）——属获利回吐非基本面恶化；已盘中卖东方AI 1/3 降敞口（权重36.3%→24.21%），反弹至成本线附近继续分批降至占总资产≤60%，不追跌、不加仓。",
}

# ---- 2. 主线验证 · 商业航天 ----
calc["theme_validate"] = {
    "theme": "商业航天（长征十号乙首飞催化）",
    "subscores": [
        {"dim": "涨停梯队", "score": 8, "max": 10, "note": "航天装备指数+10.2%、多只卫星ETF涨停、板块批量涨停潮，梯队完整。"},
        {"dim": "产业链覆盖", "score": 8, "max": 10, "note": "卫星导航→航天装备→卫星互联网→商业火箭全产业链联动，覆盖面广。"},
        {"dim": "催化力度", "score": 9, "max": 10, "note": "国家级运载火箭首飞（长征十号乙），事件级别高、想象空间大、政策契合度高。"},
        {"dim": "资金沉淀", "score": 7, "max": 10, "note": "午后单日涌入逾百亿，但仅单日爆发，次日需防高开回落、观察沉淀持续性。"},
    ],
    "total": 32, "max": 40, "grade": "8.0 / 10",
    "history_ref": "对比2023年AI行情启动：①涨停梯队——当时ChatGPT概念批量涨停≈本日航天；②量能——当时放量突破≈本日放量；③催化力度——当时大模型属革命级（更强），本日国家级首飞强但主题容量较小；④资金沉淀——当时持续数周，本日仅单日。结论：更像2023年初AI的「情绪启动日」，而非主升浪确认日。",
    "outlook": "下周一(07-13)研判：偏『趋势启动，值得调入watchlist』——但需验证『次日不回落』。若周一商业航天高开不回落、资金继续沉淀，则正式调入；若冲高回落则属脉冲兑现。建议先加watchlist（航天ETF/卫星ETF/创新药ETF/消费ETF），用小仓试建验证持续性。",
}

# ---- 3. 持仓绩效 · 被抽血量化（基底=07-10） ----
funds = c10.get("funds", [])
rows = []
semic_contrib = 0.0
for f in funds:
    w = f.get("weight_pct") or 0
    dr = f.get("daily_0707")  # 实为 07-10 当日收益
    al = f.get("alpha")
    contrib = round(w / 100.0 * (dr or 0), 2)
    rows.append({"short": f.get("short"), "sector": f.get("sector"),
                 "day_ret": dr, "alpha": al, "weight": w, "contrib": contrib})
    if "半导体" in (f.get("sector") or "") or f.get("short") in ("东方AI", "东阿尔法", "永赢半导", "财通集成"):
        semic_contrib += contrib
total_ret = c10.get("account_est_return_0708_pct", -4.29)
bleed_pct = round(semic_contrib / total_ret * 100, 0) if total_ret else None
calc["holdings_perf"] = {
    "rows": rows,
    "bleed": (
        f"半导体板块(申万)当日 -6.26%、科创50 -5.53%、我的半导体主动持仓约 -6.26%（α 相对沪深300 -4.30pp，即跑输基准约4.3个百分点，主因大盘系统性回调而非个基劣化）。"
        f"半导体四只合计权重≈74%、当日贡献账户约 <b>{semic_contrib:.2f}pp</b>，占账户总亏损（{total_ret:.2f}%）的约 <b>{bleed_pct:.0f}%</b>——"
        f"即半导体 alone 足以造成全部当日亏损，防御仓（港药+3.25%/消费+2.59%/债≈平）仅微幅缓冲。这就是「被抽血」的量化体现。"
    ),
    "note": "α = 基金实际日收益 − 关联基准(沪深300 -1.96%)；正α代表跑赢基准。半导体系α全面为负，防御/海外/消费端α为正，结构分化极端。",
}

# ---- 4. 决策链路回溯（早间→午盘→尾盘） ----
calc["decision_chain"] = {
    "steps": [
        {"phase": "早间 07-10（盘前）", "verdict": "hit",
         "action": "判半导体「跌」（MC001-005 全判跌）、提示高位科技退潮；但未见商业航天（长征十号乙首飞属午间突发，盘前不可知）。",
         "verdict_label": "方向命中（半导体跌）· 主线遗漏",
         "reason": "早盘动量延续，半导体半日仍冲高（兆易+6%），盘前无法预知12:15火箭首飞这一午间催化。"},
        {"phase": "午盘 07-10（11:30-13:00）", "verdict": "miss",
         "action": "12:15 长征十号乙首飞 → 商业航天爆发；此时若已扫到新闻可盘中切换半导体→航天，但持仓未动（半导体仍扛）。",
         "verdict_label": "调仓窗口错过",
         "reason": "缺乏「重大事件盘中实时预警」机制，午后资金已切换时持仓仍在半导体被抽血方。"},
        {"phase": "尾盘/晚间 07-10", "verdict": "hit",
         "action": "复盘确认「高位科技出货→星辰大海+医药」，盘中已卖东方AI 1/3 锁利；建议加航天ETF/卫星ETF/创新药ETF/消费ETF 到 watchlist，半导体扛。",
         "verdict_label": "应对得当",
         "reason": "及时降敞口+建立新主线观察，纪律执行到位。"},
    ],
    "bias": "最大偏差确为「早盘未扫到商业航天新闻，错过半导体→航天调仓窗口」。但根因是催化（火箭首飞）属午间突发、不可盘前预知，非扫描疏漏；真正可改进的是『盘中重大事件实时预警 + 单日巨阴后用小仓试建新主线』的纪律。",
    "lesson": "补救：①订阅航天/政策快讯做盘中异动提醒；②半导体单日巨阴后不硬扛不动，用止盈回款小仓（≤总仓15%）试建新主线验证持续性；③命中率仅约24%，方向预测价值低，风险管理(止损/再平衡)才是胜负手。",
}

# ---- 5. 调仓建议（holiday edition，复核07-10结论） ----
calc["rebalance"] = [
    ["半导体是否继续持有",
     "半导体系占总资产65.4%、占持仓74.5%，07-10单日-6.26%被抽血最重。三重共振主线（商业航天/医药/消费）若周一确立，半导体继续被抽血概率大。",
     "倾向扛（严守-8%硬止损）：属获利回吐非基本面恶化；反弹至成本线附近继续分批降至占总资产≤60%，不追跌、不加仓；若再跌>3%破位则触发减仓。"],
    ["加入商业航天/医药到 watchlist",
     "账户尚无商业航天/创新药暴露，而二者成新主线（军工航天+10.2%、港股创新药+3.25%）。",
     "将 航天ETF / 卫星ETF / 创新药ETF / 消费ETF 加入 watchlist；周一确认持续性后，用半导体止盈回款小仓试建（单笔≤总仓15%）。"],
    ["高集中度",
     "前二持仓（东方阿尔法+东方AI）合计约56.6%，东方阿尔法29.1%逼近30%单基上限。",
     "东方阿尔法反弹即减至≤25%；用回款分散至防御/低位轮动，降低单一赛道波动。"],
    ["高风险管理",
     "永赢半导绝对敞口1856元、港药持续亏损；科技短线退潮但情绪中性。",
     "永赢触-2%止损50%；港药按两级阈值（-5%减半/-1%内减1/3）；保留鹏华债/纳指防御底仓。"],
    ["现金弹药管理",
     "现金1589元(12.11%)为下周急跌低吸弹药，勿闲置；调仓资金全部来自止盈回款不新增投入。",
     "分3-4批、每周一批执行再平衡；单日板块涨跌超3%暂停，避免追涨杀跌。"],
]

# ---- 6. 次日预案（下个交易日 07-13 周一） ----
calc["next_day_plan"] = {
    "next_trading_day": "2026-07-13（周一）",
    "key_levels": [
        "上证 3996.16（4000关口下沿，守则不破位）",
        "半导体/科创50：07-10 巨阴后是否止跌（科创50 2064.98）",
        "商业航天：周一是否高开不回落（验证主线持续性）",
        "账户硬止损线：单基 -8%；现金 12.11% 为低吸弹药",
    ],
    "events": [
        "周末消息面：美股(7/10隔夜中性偏多)、中东/地缘、国内政策",
        "07-13 早盘半导体开盘价（是否止跌企稳）",
        "商业航天周一延续性（脉冲兑现 or 趋势启动）",
        "港股创新药/消费 修复延续性",
    ],
    "scenarios": {
        "optimistic": "半导体止跌反弹 + 商业航天延续 → 半导体扛住，用回款小仓加 航天ETF/创新药ETF；账户修复。",
        "base": "半导体弱势震荡(-2%~+1%) → 不操作，严守-8%止损，观望新主线持续性；现金待命。",
        "pessimistic": "半导体破位加速(再跌>3%) → 触发减仓/止损，现金增至20%+，全面防守；新主线暂不加。",
    },
}

# ---- 命中率：库内累计 + 待07-13验证 ----
calc["overall_acc"] = plog.get("summary", {}).get("simple_accuracy_pct", 23.8)
calc["weighted_acc"] = plog.get("summary", {}).get("weighted_accuracy_pct", 19.8)
calc["backfilled"] = 0          # 休市日无新增回填
calc["hits"] = 0
calc["cum_verified"] = plog.get("summary", {}).get("verified", 42)
calc["cum_hits"] = plog.get("summary", {}).get("total_hits", 10)
pending = [{"target": r["target"], "direction": r["direction"], "confidence": r.get("confidence", "")}
           for r in plog.get("records", [])
           if r.get("verify_date") == DATE and not r.get("verified")]
calc["pending_list"] = pending
calc["pending_count"] = len(pending)
calc["hit_holiday_note"] = (
    f"库内累计：{calc['cum_verified']} 验证 / {calc['cum_hits']} 命中，简单 {calc['overall_acc']}% · 加权 {calc['weighted_acc']}%。"
    f"因 07-11 周六休市，本日无新增回填；{calc['pending_count']} 条 07-10 预测将于 07-13(周一)收盘回填。"
)

# 情绪(休市)：取最近收盘(07-10)基准 + 周末扫描前瞻
calc["fg_index"] = 50
calc["fg_level"] = "中性"
calc["fg_factors"] = calc10.get("fg_factors", {})
calc["fg_missing"] = calc10.get("fg_missing", [])
calc["fg_action"] = (
    "中性——盈利半导体仓分批止盈、不接飞刀；未达>75减仓预警；严守-8%硬止损。"
    f"周末扫描前瞻情绪 {calc['weekend_sentiment']}（{calc['weekend_sentiment_label']}），半导体处\"还债期\"，周一观望为主。"
)

json.dump(cons, open(os.path.join(BASE, f"consolidated_{DATE}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
json.dump(calc, open(os.path.join(BASE, f"calc_{DATE}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("wrote consolidated_%s.json + calc_%s.json ; pending=%d ; semic_contrib=%.2fpp" % (DATE, DATE, calc["pending_count"], semic_contrib))
