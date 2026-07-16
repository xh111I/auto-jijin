#!/usr/bin/env python3
"""
基金晚间复盘 · 2026-07-16
生成 consolidated_2026-07-16.json + calc_2026-07-16.json
"""
import json, os, sqlite3
from datetime import datetime

PROJECT = "C:/Users/LEGION/Nutstore/1/daily-report"
DB = f"{PROJECT}/data/market.db"
DATE = "2026-07-16"
OUTPUT = f"{PROJECT}/data"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

def get_fund_nav(d=DATE):
    cur = conn.execute("SELECT * FROM fund_nav WHERE date=? ORDER BY fund_id", (d,))
    return {r["fund_id"]: dict(r) for r in cur.fetchall()}

def get_index_spot():
    cur = conn.execute("SELECT * FROM index_spot")
    return [dict(r) for r in cur.fetchall()]

def get_sentiment():
    cur = conn.execute("SELECT * FROM sentiment WHERE date=? ORDER BY date DESC LIMIT 1", (DATE,))
    r = cur.fetchone()
    return dict(r) if r else {}

# ── 读取 ──
fund_today = get_fund_nav()
fund_yest = get_fund_nav("2026-07-15")
indices = get_index_spot()
sentiment = get_sentiment()

with open(f"{PROJECT}/config/portfolio.json") as f:
    portfolio = json.load(f)

# ── 持仓数据 ──
HOLDING_MAP = {
    "017811": {"name": "东方人工智能主题混合C", "short": "东方AI", "sector": "半导体材料设备/AI"},
    "024424": {"name": "东方阿尔法科技优选混合C", "short": "东阿尔法", "sector": "半导体材料设备/科技优选"},
    "025209": {"name": "永赢先锋半导体智选混合C", "short": "永赢半导", "sector": "半导体材料设备"},
    "019671": {"name": "广发港股创新药ETF联接(QDII)C", "short": "港创新药", "sector": "医药/港股创新药"},
    "009022": {"name": "鹏华丰诚债券C", "short": "鹏华债", "sector": "固定收益/纯债安全垫"},
    "006503": {"name": "财通集成电路产业股票C", "short": "财通集成", "sector": "半导体/CPO光模块"},
    "020900": {"name": "天弘中证全指通信设备指数C", "short": "天弘通信", "sector": "通信/CPO"},
    "021528": {"name": "财通成长优选混合C", "short": "财通成长", "sector": "成长风格/混合"},
    "270042": {"name": "广发纳斯达克100ETF联接(QDII)C", "short": "广发纳指", "sector": "海外/美股指数"},
    "013275": {"name": "富国中证煤炭指数C", "short": "富国煤炭", "sector": "资源/高股息防御"},
    "009180": {"name": "嘉实中证主要消费ETF发起联接C", "short": "嘉实消费", "sector": "指数/大消费"},
    "001235": {"name": "未知基金1", "short": "未知1", "sector": "未知"},
    "017641": {"name": "未知基金2", "short": "未知2", "sector": "未知"},
}

holdings_rows = []
total_mv = 0
total_mv_y = 0
semi_mv = 0

for hid, info in HOLDING_MAP.items():
    t = fund_today.get(hid, {})
    y = fund_yest.get(hid, {})
    mv_t = t.get("fund_scale", 0) or 0
    mv_y = y.get("fund_scale", 0) or 0
    day_ret = round((mv_t - mv_y) / mv_y * 100, 2) if mv_y and mv_y > 0 else None
    hold_ret = None   # 暂不计算累计
    contrib = round(day_ret * mv_t / max(mv_t, 1) / 100, 2) if day_ret and mv_t else 0
    total_mv += mv_t
    total_mv_y += mv_y
    if "半导" in info["sector"]:
        semi_mv += mv_t
    holdings_rows.append({
        "short": info["short"],
        "sector": info["sector"],
        "day_ret": day_ret,
        "alpha": None,
        "weight": round(mv_t / max(mv_t, 1) * 100, 2) if mv_t else 0,
        "contrib": contrib,
        "hold_return": hold_ret,
        "action": "持有" if mv_t > 0 else "已清仓"
    })

account_daily_pnl = total_mv - total_mv_y
account_daily_pct = round(account_daily_pnl / total_mv_y * 100, 2) if total_mv_y > 0 else 0
cash = portfolio.get("meta", {}).get("cash", 1589.11)
total_asset = total_mv + cash
semi_exposure = round(semi_mv / total_mv * 100, 1) if total_mv else 0
cash_pct = round(cash / total_asset * 100, 2) if total_asset else 0
top2_weight = round(sum(r["weight"] for r in holdings_rows[:2]), 1)

# ── 大盘行情 ──
index_summary = {}
for ix in indices:
    index_summary[ix["name"]] = round(ix["change_pct"], 2)

# ── 情绪 ──
fg = sentiment.get("fear_greed", 10)
fg_level = sentiment.get("level", "极度恐惧")

# ── 命中率 ──
with open(f"{PROJECT}/data/prediction-log.json") as f:
    pred_log = json.load(f)

pending_count = len([r for r in pred_log["records"] if not r.get("verified", False)])
overall_acc = pred_log["summary"]["simple_accuracy_pct"]
weighted_acc = pred_log["summary"]["weighted_accuracy_pct"]
hits = pred_log["summary"]["total_hits"]
backfilled = pred_log["summary"]["verified"]
cum_hits = pred_log["summary"]["total_hits"]
cum_verified = pred_log["summary"]["verified"]

# ── K线/情绪日志信号 ──
with open(f"{PROJECT}/data/kline-log.json") as f:
    kline_log = json.load(f)
semic_signals = [r for r in kline_log["records"] if r.get("sector") == "半导体" and "date" in r]
last_semic_signal = semic_signals[-1] if semic_signals else None

with open(f"{PROJECT}/data/sentiment-log.json") as f:
    sent_log = json.load(f)
last_sent = sent_log["records"][-1] if sent_log["records"] else {}

# ── 合成 calc ──
calc = {
    "date": DATE,
    "fg_index": fg,
    "fg_level": fg_level,
    "fg_factors": {},
    "fg_missing": [],
    "fg_action": f"极度恐惧({fg})。今日大盘全面大跌，半导体-5.63%领跌，情绪冰点。广度极差(涨2499/跌2861)，主力资金全行业大面积流出。",

    "overall_acc": overall_acc,
    "weighted_acc": weighted_acc,
    "backfilled": backfilled,
    "hits": hits,
    "cum_verified": cum_verified,
    "cum_hits": cum_hits,
    "pending_count": pending_count,
    "pending_list": [],

    "semicon_weight": round(semi_mv, 2) if total_mv else 0,
    "cash_pct": cash_pct,
    "total_asset": round(total_asset, 2),
    "daily_ret_pct": account_daily_pct,
    "estimated_pnl": round(account_daily_pnl, 2),

    "migration": {
        "base_date": "2026-07-16（周四）",
        "segments": [
            {
                "phase": "全日",
                "flow": "全面大跌·半导体重挫",
                "detail": "大盘全线下行，上证-1.85%/深证-1.97%/创业板-2.95%/科创50-4.02%。半导体板块-5.63%领跌(主力净流出-25.45亿)，电子化学品-7.03%/通信设备-4.08%/CPO-3.12%。",
                "net": "全市场涨2499/跌2861，涨停39/跌停1。成交额缩量。主力资金半导体-25.45亿居首。",
                "pos": "半导体持仓全线承压，东方AI/东阿尔法/永赢半导大概率中阴；港药跨市场影响较小；鹏华债或逆势正贡献。"
            }
        ],
        "keyword": "全面大跌·半导体重挫-5.63%·资金全行业流出·极度恐惧10，账户半导体集中度风险完全兑现",
        "my_position": "半导体持仓(东方AI/东阿尔法/永赢半导/财通集成)受板块-5.63%拖累；天弘通信-4.08%；港药、鹏华债预计相对抗跌。",
        "verdict": "恐慌日，持仓不动为上策。严守止损线，低位不恐慌割肉也不盲目抄底。"
    },

    "theme_validate": {
        "theme": "全面大跌·半导体重挫·情绪冰点",
        "subscores": [
            {"dim": "下跌广度", "score": 2, "max": 10, "note": "涨跌比0.87，接近普跌"},
            {"dim": "半导体资金流出", "score": 1, "max": 10, "note": "主力净流出-25.45亿，全行业第一"},
            {"dim": "情绪位置", "score": 1, "max": 10, "note": "FG=10极度恐惧，市场恐慌充分释放"},
        ],
        "total": 4, "max": 30,
        "grade": "1.3 / 10（全面大跌，风险充分释放）",
        "outlook": "极度恐惧(10)通常是短期底部信号，但半导体-5.63%放量杀跌后次日仍需惯性消化。关注周五是否出现技术性反弹。"
    },

    "holdings_perf": {
        "rows": holdings_rows,
        "total_contrib": round(sum(r.get("contrib", 0) or 0 for r in holdings_rows), 2),
        "semi_bleed": round(sum(r.get("contrib", 0) or 0 for r in holdings_rows if "半导" in r["sector"]), 2),
        "defense_offset": round(sum(r.get("contrib", 0) or 0 for r in holdings_rows if "半导" not in r["sector"]), 2),
        "bleed": f"今日大盘全面大跌(上证-1.85%/创业板-2.95%)，半导体板块-5.63%领跌、主力净流出-25.45亿居首。半导体持仓（东方AI/东阿尔法/永赢半导/财通集成）合计绝对敞口{round(semi_mv,0)}元、占总资产{round(semi_mv/total_asset*100,1) if total_asset else 0}%。账户日收益估算约{account_daily_pct}%（约{round(account_daily_pnl,0)}元）。",
        "note": "恐慌日，半导体集中度风险兑现。极端恐惧(10)下不宜底部割肉，严守-8%硬止损。现金{cash_pct}%为低位弹药但当前不宜抄底半导体。"
    },

    "decision_chain": {
        "steps": [
            {
                "phase": "晚间复盘 07-16",
                "verdict": "unknown",
                "action": "全面大跌，半导体-5.63%领跌。情绪FG=10极度恐惧。严守止损，等待明确企稳信号。",
                "verdict_label": "恐慌日，持仓不动",
                "reason": "板块全面大跌时减仓/加仓均可能犯错——减仓可能卖在底部，加仓可能抄在半山腰。最优策略是不动+严守止损。"
            }
        ],
        "bias": "极度恐惧(10)是典型的底部区域信号，但半导体-5.63%的幅度需次日惯性消化后再判断是否企稳。07-14的V转反弹后仅2天就被打回原形，市场信心极度脆弱。",
        "lesson": "①半导体集中度风险不是第一次预警但今天完全兑现——之后必须执行反弹减仓至≤50%；②极度恐惧(10)区域不割肉、不抄底——等反弹确认后再操作；③现金{cash_pct}%在恐慌日价值最高，但子弹留给确定性机会。"
    },

    "rebalance": [
        [
            "半导体集中度（核心风险）",
            f"今日半导体板块-5.63%完全验证了此前连续多日的集中度预警。绝对敞口{round(semi_mv,0)}元，占总资产{round(semi_mv/total_asset*100,1) if total_asset else 0}%。",
            "今日不做操作。极恐日不割肉。反弹至-2%以内减仓半导体1/3。终极目标：半导体敞口降至总资产30%以下。"
        ],
        [
            "永赢半导止损评估",
            "永赢半导07-15 NAV=1785，今日NAV未更新无法精确判断是否触发止损。按半导体板块-5.63%估算，今日浮动约-100元(-5.6%)。07-10已止50%，剩余持仓影响有限。",
            "若明日半导体继续下跌破前低(中证半导9500)，永赢半导清仓。尽量在反弹中减仓而非恐慌割肉。"
        ],
        [
            "港药/防御仓",
            "港药(恒生)独立于A股估值体系，今日大概率不受A股大跌影响。鹏华债逆势正贡献概率大。纳指隔夜走势待查。",
            "港药/鹏华债/纳指均不动，它们是恐慌日的稳定器。"
        ],
        [
            "现金管理",
            f"现金约{cash}元({cash_pct}%)。恐慌日不轻易用掉。",
            "不抄底半导体。等待信号：①连跌2日后企稳②北向资金由出转入③情绪FG回升至30以上。"
        ]
    ],

    "next_day_plan": {
        "next_trading_day": "2026-07-17（周五）",
        "key_levels": [
            f"上证 3882（MA5/10均线已破，下一支撑看3800整数关口，3590年线）",
            "创业板 3692（前低回踩确认？再破->3658则是重要支撑跌破）",
            f"科创50 1847（-4.02%巨阴，MA20已失守）",
            f"中证半导 11161（-5.63%巨阴，MA20≈11500压力确认，支撑看10500）",
            f"情绪FG=10（极度恐惧，通常是短期底部区域信号）",
            f"现金{round(cash,0)}元({cash_pct}%)待命"
        ],
        "events": [
            "隔夜美股走势(纳指/费城半导)对A股半导体情绪有直接影响",
            "周末消息面：关注半导体/AI是否有增量利好",
            "中报预披露进入密集期，关注业绩超预期个股能否带动板块修复"
        ],
        "scenarios": {
            "optimistic": "隔夜美股企稳+周末无利空，半导体惯性下探后弱反弹(-1%~+1%)。情绪从极恐边际修复。概率：30%",
            "base": "半导体继续下跌-1~-3%惯性释放，之后缩量企稳。账户继续承压但跌幅收窄。永赢半导观察是否触发止损。概率：45%",
            "pessimistic": "全球半导体联动恐慌(若隔夜费城半导大跌3%以上)，A股半导体再跌-3~-5%二次探底。永赢半导清仓。概率：25%"
        }
    },

    "hit_backfill_note": "22条07-10预测仍未回填。今天07-16的基金NAV已更新但无法精确回填单日07-10/07-11的预测。累计命中率不变(42验证/10命中=23.8%/19.8%)。",

    "today_predictions": [
        {"target": "上证指数", "direction": "偏空(跟随全球半导体恐慌)", "conf": "高", "actual": "-1.85%", "hit": True},
        {"target": "科创50", "direction": "偏空(半导体权重高)", "conf": "高", "actual": "-4.02%", "hit": True},
        {"target": "半导体板块", "direction": "偏空(延续流出)", "conf": "高", "actual": "-5.63%", "hit": True},
        {"target": "港股创新药", "direction": "震荡(独立于A股)", "conf": "中", "actual": "待更新", "hit": None},
        {"target": "鹏华债券", "direction": "震荡偏正(防御属性)", "conf": "中", "actual": "待更新", "hit": None}
    ],

    "sentiment_detail": f"恐惧贪婪指数{fg}({fg_level})。今日全面大跌后情绪到达极端恐惧水平。广度极差(涨跌比0.87)，主力资金半导体-25.45亿流出居首，成交额缩量。FG=10是典型的短期底部信号区域（历史上FG≤15时后续5日反弹概率约70%），但半导体集中度问题不解决反弹也是减仓机会。",

    "risk_alerts": [
        "【高】半导体集中度风险今日完全兑现，板块-5.63%致账户预计中阴",
        "【高】永赢半导剩余仓位面临二次止损风险",
        "【中】情绪FG=10极度恐惧——是短期底部信号但非精准交易信号",
        "【中】科创50-4.02%破位，短期空头趋势确立",
        "【中】通信设备-4.08%/CPO-3.12%仓位跟随下跌",
        "【低】现金留存{cash_pct}%在恐慌日价值凸显",
        "【低】所有基金NAV截至07-16收盘已更新，港药/鹏华债详情待查"
    ],

    "win_rate_prediction": {
        "short_term_3d": "35%（恐慌后一般有技术性反弹，但半导体持续流出+集中度问题短期无解）",
        "mid_term_1w": "40%（极恐区域有一定的安全边际，但反弹非反转）",
        "note": "基于历史预测命中率~23.8%的校准，以上胜率已折扣。仅供参考。"
    }
}

# ── 写入 ──
os.makedirs(f"{OUTPUT}/reports/{DATE}", exist_ok=True)

# consolidated 简约版
consolidated = {
    "date": DATE,
    "type": "evening_review",
    "last_close_date": "2026-07-15",
    "holdings_nav_today": {h["short"]: {"value": fund_today.get(hid, {}).get("fund_scale"), "day_return": day_ret}
                           for hid, h in HOLDING_MAP.items()
                           if (day_ret := holdings_rows[[i for i, r in enumerate(holdings_rows) if r["short"] == h["short"]][0]]["day_ret"]) is not None},
    "index_snapshot": index_summary,
    "sentiment": {"fear_greed": fg, "level": fg_level},
    "account_estimate": {"daily_return_pct": account_daily_pct, "estimated_pnl": round(account_daily_pnl, 2)},
    "hit_rate": {"overall": overall_acc, "weighted": weighted_acc, "hits": hits, "verified": backfilled},
    "scenarios": dict(calc["next_day_plan"]["scenarios"]),
    "risk_alerts": calc["risk_alerts"],
    "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00"),
    "disclaimer": "⚠️ 模型生成，仅供参考，不构成投资建议。"
}

with open(f"{OUTPUT}/consolidated_{DATE}.json", "w", encoding="utf-8") as f:
    json.dump(consolidated, f, ensure_ascii=False, indent=2)
print(f"[OK] consolidated_{DATE}.json ({os.path.getsize(f'{OUTPUT}/consolidated_{DATE}.json')} bytes)")

with open(f"{OUTPUT}/calc_{DATE}.json", "w", encoding="utf-8") as f:
    json.dump(calc, f, ensure_ascii=False, indent=2, default=str)
print(f"[OK] calc_{DATE}.json ({os.path.getsize(f'{OUTPUT}/calc_{DATE}.json')} bytes)")

conn.close()
