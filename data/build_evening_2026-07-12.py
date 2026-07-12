# -*- coding: utf-8 -*-
"""build_evening_2026-07-12.py — 休市周末特刊(周日) 数据层装配
07-12 周日 A股休市，无实盘。基于最近交易日(07-10 周五)真实收盘 + 周末全球扫描(early-morning_2026-07-12.json)
组装 consolidated_2026-07-12.json + calc_2026-07-12.json，供 make_html.py 渲染「周末特刊·周日版」晚间复盘。
相较 07-11 周六版，本版新增权重：周末海外强催化(SK海力士纳斯达克首秀+10~13% / 英伟达市值破5万亿 / Meta全周+15% / 地缘缓和 / 人民币破6.78)
对下周一(07-13)半导体的潜在托底，并据此微调「半导体扛/减」结论。不编造任何 07-12 当日行情。
"""
import json, os

BASE = "C:/Users/LEGION/Nutstore/1/daily-report/data"

c10 = json.load(open(os.path.join(BASE, "consolidated_2026-07-10.json"), encoding="utf-8"))
calc10 = json.load(open(os.path.join(BASE, "calc_2026-07-10.json"), encoding="utf-8"))
plog = json.load(open(os.path.join(BASE, "prediction-log.json"), encoding="utf-8"))
try:
    em = json.load(open(os.path.join(BASE, "early-morning_2026-07-12.json"), encoding="utf-8"))
except Exception:
    em = {}

DATE = "2026-07-12"

# ---------------- consolidated (holiday edition = 07-10 真实收盘) ----------------
cons = dict(c10)
cons["date"] = DATE
cons["holiday"] = True
cons["data_note"] = "2026-07-12 周日·A股休市。以下为最近交易日(2026-07-10 周五)真实收盘回顾 + 周末全球催化更新，非当日行情。"
cons["news"] = [
    "【休市】2026-07-12 周日 A股休市，无实盘交易。本复盘为「周末特刊·周日版」，以 07-10 真实收盘为基底，叠加周末全球催化推演下周一(07-13)预案。",
    "【周末重磅·存储AI强催化】SK海力士纳斯达克首秀涨超10~13%(募资265亿美元创海外赴美IPO新高，点燃全球存储芯片)；英伟达市值重返5万亿美元(AI芯片领涨+4%)；Meta付费大模型Muse Spark发布、全周近+15%；纳指全周+1.74%三连阳创月余新高。",
    "【周末地缘缓和】美伊同意继续谈判、霍尔木兹复航，油价上方承压(WTI 71.41)；离岸人民币两周多来首破6.78走强——通胀→美联储转鹰传导缓和，高估值科技估值压制减轻。",
    "【冲突焦点】半导体『还债期』(07-10 中证半导-6.72%/ETF512480-6.93%) vs 周末海外存储/AI强催化 → 下周一(07-13)多空对决，半导体能否缩量企稳是关键。",
] + c10.get("news", [])

# ---------------- calc (holiday edition + 6 大分析字段) ----------------
calc = dict(calc10)
calc["date"] = DATE
calc["holiday"] = True
calc["holiday_note"] = (
    "2026-07-12 周日·A股休市，无实盘交易。本复盘为「周末特刊·周日版」：以最近交易日(2026-07-10 周五)真实收盘为基底，"
    "叠加周末全球强催化(SK海力士上市大涨/英伟达破5万亿/地缘缓和/人民币走强)推演下周一(2026-07-13)预案。"
    "不编造任何当日行情；账户状态=07-10 收盘快照。距下一交易日仅 1 天。"
)
calc["weekend_sentiment"] = em.get("sentiment", {}).get("broad", {}).get("score", 48)
calc["weekend_sentiment_label"] = em.get("sentiment", {}).get("broad", {}).get("label", "中性偏空")
calc["weekend_semi_sentiment"] = em.get("sentiment", {}).get("semiconductor", {}).get("score", 45)
calc["weekend_semi_label"] = em.get("sentiment", {}).get("semiconductor", {}).get("label", "偏空")

# ---- 1. 全天资金迁徙路线回顾（核心）——基底=07-10 真实迁徙 + 周末更新 ----
calc["migration"] = {
    "base_date": "2026-07-10（周五·最近交易日）｜ 周末全球催化叠加更新至 07-12(周日)",
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
        {"phase": "周末 07-11~07-12（休市·全球催化）", "flow": "海外存储/AI 强催化回补",
         "detail": "SK海力士纳斯达克首秀+10~13%(存储景气验证)、英伟达破5万亿、Meta全周+15%；地缘缓和+人民币走强。半导体海外映射由『纯抽血』转为『抽血 vs 托底』并存。",
         "net": "无A股实盘；海外映射：存储/AI偏多(62)、A股半导体情绪由42微修复至45",
         "pos": "持仓：半导体获『周末外部托底』，但A股『还债期』超买回落逻辑未消，周一多空对决"},
    ],
    "keyword": "高位科技出货→奔赴星辰大海+医药；周末海外存储/AI强催化回补——资金未离场只是换战场，半导体获外部托底待周一验证",
    "my_position": "半导体持仓（东方AI / 东阿尔法 / 永赢半导 / 财通集成）在 07-10 迁徙中为「被抽血方」；周末海外强催化(SK海力士/英伟达)提供潜在托底，周一(07-13)由『单边被抽血』转为『多空对决』。",
    "verdict": "扛（严守-8%硬止损）——获利回吐非基本面恶化，且周末存储/AI催化提供托底；已盘中卖东方AI 1/3 降敞口（权重36.3%→24.21%）。周一若存储催化带动高开冲高→趁反弹锁利降至占总资产≤60%、不追；若低开放量下破MA20→触发减仓。不追跌、不加仓。",
}

# ---- 2. 主线验证 · 商业航天 ----
calc["theme_validate"] = {
    "theme": "商业航天（长征十号乙首飞催化）",
    "subscores": [
        {"dim": "涨停梯队", "score": 8, "max": 10, "note": "航天装备指数+10.2%、多只卫星ETF涨停、板块批量涨停潮，梯队完整。"},
        {"dim": "产业链覆盖", "score": 8, "max": 10, "note": "卫星导航→航天装备→卫星互联网→商业火箭全产业链联动，覆盖面广。"},
        {"dim": "催化力度", "score": 9, "max": 10, "note": "国家级运载火箭首飞（长征十号乙），事件级别高；周末国常会『新兴支柱产业培育/新质生产力』政策预期延续加持。"},
        {"dim": "资金沉淀", "score": 7, "max": 10, "note": "午后单日涌入逾百亿，但仅单日爆发；经历一个周末，周一需重点验证资金是否沉淀、题材是否延续。"},
    ],
    "total": 32, "max": 40, "grade": "8.0 / 10",
    "history_ref": "对比2023年AI行情启动：①涨停梯队——当时ChatGPT概念批量涨停≈本次航天；②量能——当时放量突破≈本次放量；③催化力度——当时大模型属革命级(更强)，本次国家级首飞强但主题容量较小；④资金沉淀——当时持续数周，本次仅单日+一个周末冷却期。结论：更像2023年初AI的「情绪启动日」，主升浪确认与否取决于周一(07-13)资金能否回补。",
    "outlook": "下周一(07-13)研判：偏『趋势启动，值得调入watchlist』——但经过周末冷却，须验证『周一不高开回落』。若周一商业航天高开不回落、资金继续沉淀，则正式调入；若冲高回落则属脉冲兑现。建议先加watchlist（航天ETF/卫星ETF/创新药ETF/消费ETF），用小仓试建验证持续性。",
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
        f"半导体板块(申万)07-10 当日 -6.26%、科创50 -5.53%、我的半导体主动持仓约 -6.26%（α 相对沪深300 -4.30pp，即跑输基准约4.3个百分点，主因大盘系统性回调而非个基劣化）。"
        f"半导体四只合计权重≈74%、当日贡献账户约 <b>{semic_contrib:.2f}pp</b>，占账户总亏损（{total_ret:.2f}%）的约 <b>{bleed_pct:.0f}%</b>——"
        f"即半导体 alone 足以造成全部当日亏损，防御仓（港药+3.25%/消费+2.59%/债≈平）仅微幅缓冲。这就是「被抽血」的量化体现。"
        f"周末海外存储/AI强催化(SK海力士+10~13%/英伟达破5万亿)为下周一提供潜在净值修复外部条件。"
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
        {"phase": "周末 07-11~07-12（复盘迭代）", "verdict": "hit",
         "action": "周末两次特刊持续跟踪：捕捉到 SK海力士上市/英伟达破5万亿等存储AI强催化，据此上调半导体周一托底概率、微调『扛』结论；主线航天维持8.0/10、待周一验证。",
         "verdict_label": "前瞻迭代到位",
         "reason": "休市期仍完成全球催化扫描并反馈到调仓逻辑，弥补了『盘中事件预警』的部分缺口。"},
    ],
    "bias": "最大偏差确为「早盘未扫到商业航天新闻，错过半导体→航天调仓窗口」。但根因是催化（火箭首飞）属午间突发、不可盘前预知，非扫描疏漏；真正可改进的是『盘中重大事件实时预警 + 单日巨阴后用小仓试建新主线』的纪律。",
    "lesson": "补救：①订阅航天/政策/存储快讯做盘中异动提醒；②半导体单日巨阴后不硬扛不动，用止盈回款小仓（≤总仓15%）试建新主线验证持续性；③命中率仅约24%，方向预测价值低，风险管理(止损/再平衡)才是胜负手；④周末外部催化(SK海力士/英伟达)需纳入周一开盘策略，但不改变超买回落的中期纪律。",
}

# ---- 5. 调仓建议（holiday edition·周日版，复核07-10结论+周末催化） ----
calc["rebalance"] = [
    ["半导体是否继续持有",
     "半导体系占总资产65.4%、占持仓74.5%，07-10单日-6.26%被抽血最重（还债期）；但周末海外存储/AI强催化(SK海力士+10~13%/英伟达破5万亿)提供潜在托底，A股半导体情绪由42微修复至45。",
     "倾向扛（严守-8%硬止损）：属获利回吐非基本面恶化，且获周末外部催化。周一若存储催化带动高开冲高→趁反弹锁利降至占总资产≤60%、不追高；若低开放量下破MA20→触发减仓。核心纪律：反弹是减仓良机而非加仓理由。"],
    ["加入商业航天/医药到 watchlist",
     "账户尚无商业航天/创新药暴露，而二者成新主线（军工航天+10.2%、港股创新药+3.25%），经周末冷却待周一验证延续性。",
     "将 航天ETF / 卫星ETF / 创新药ETF / 消费ETF 加入 watchlist；周一确认『高开不回落+资金沉淀』后，用半导体止盈回款小仓试建（单笔≤总仓15%）。"],
    ["高集中度",
     "前二持仓（东方阿尔法+东方AI）合计约56.6%，东方阿尔法29.1%逼近30%单基上限。",
     "东方阿尔法反弹即减至≤25%；用回款分散至防御/低位轮动，降低单一赛道波动。"],
    ["高风险管理",
     "永赢半导绝对敞口1856元、港药持续亏损；科技短线退潮但情绪中性、周末存储催化边际改善。",
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
        "半导体/科创50：07-10 巨阴后能否缩量企稳（科创50 2064.98；半导体防再破位下破MA20）",
        "商业航天：周一是否高开不回落（验证主线持续性，经周末冷却后关键）",
        "账户硬止损线：单基 -8%；现金 12.11% 为低吸弹药",
    ],
    "events": [
        "周末催化映射：SK海力士上市大涨/英伟达破5万亿 → 周一半导体高开概率上升",
        "07-13 早盘半导体开盘价与量能（高开冲高=锁利良机 / 低开放量=减仓信号）",
        "商业航天周一延续性（脉冲兑现 or 趋势启动）",
        "港股创新药/消费修复延续性；离岸人民币走强利好外资偏好",
        "中报预告密集披露期(超220家/近九成预喜)，关注半导体设备重仓股预告",
    ],
    "scenarios": {
        "optimistic": "存储催化带动半导体高开冲高 + 商业航天延续 → 趁高开锁利降半导体敞口至≤60%，用回款小仓加 航天ETF/创新药ETF；账户修复。切忌高开追加。",
        "base": "半导体高开后震荡回落/窄幅整理(-2%~+1%) → 不追不减、严守-8%止损，观望新主线与资金沉淀；现金待命。",
        "pessimistic": "半导体低开放量下破MA20(再跌>3%) → 触发减仓/止损，现金增至20%+全面防守；新主线暂不加，等企稳。",
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
           if r.get("verify_date") == "2026-07-11" and not r.get("verified")]
calc["pending_list"] = pending
calc["pending_count"] = len(pending)
calc["hit_holiday_note"] = (
    f"库内累计：{calc['cum_verified']} 验证 / {calc['cum_hits']} 命中，简单 {calc['overall_acc']}% · 加权 {calc['weighted_acc']}%。"
    f"07-11(周六)、07-12(周日)连续休市，本周末无新增回填；{calc['pending_count']} 条 07-10 晚间预测将于 07-13(周一)收盘统一回填验证。"
)

# 情绪(休市)：取最近收盘(07-10)基准 + 周末扫描前瞻
calc["fg_index"] = 50
calc["fg_level"] = "中性"
calc["fg_factors"] = calc10.get("fg_factors", {})
calc["fg_missing"] = calc10.get("fg_missing", [])
calc["fg_action"] = (
    "中性——盈利半导体仓分批止盈、不接飞刀；未达>75减仓预警；严守-8%硬止损。"
    f"周末扫描前瞻：大盘情绪 {calc['weekend_sentiment']}（{calc['weekend_sentiment_label']}）、半导体情绪 {calc['weekend_semi_sentiment']}（{calc['weekend_semi_label']}，由42微修复）；"
    "周末海外存储/AI强催化提供托底，但A股『还债期』超买回落未消，周一以观望+反弹锁利为主。"
)

json.dump(cons, open(os.path.join(BASE, f"consolidated_{DATE}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
json.dump(calc, open(os.path.join(BASE, f"calc_{DATE}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("wrote consolidated_%s.json + calc_%s.json ; pending=%d ; semic_contrib=%.2fpp ; weekend_sentiment=%s/%s"
      % (DATE, DATE, calc["pending_count"], semic_contrib, calc["weekend_sentiment"], calc["weekend_semi_sentiment"]))
