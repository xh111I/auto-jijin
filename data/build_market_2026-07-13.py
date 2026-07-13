#!/usr/bin/env python3
"""Build market_2026-07-13.json from raw index/sector data."""
import json, os

DATA = os.path.dirname(os.path.abspath(__file__))

# ── 指数数据 ──
INDICES = [
    {
        "name": "上证",
        "code": "sh000001",
        "close": 3913.79,
        "chg_pct": -2.06,
        "amount_yi": 13349,
        "main_flow_yi": -754.0,
        "score": 28,
        "tendency": "偏空",
        "warn": "跌破全部均线，放量破位，主力-754亿出逃",
        "kline": {
            "trend": {"label": "偏空", "score": 20, "detail": "收盘3913.79，跌破MA5/20/60/120，仅MA250(3939)下方"},
            "volprice": {"label": "放量下跌", "score": 15, "detail": "放量-2.06%，成交13349亿，量比1.06"},
            "shape": {"label": "中阴线", "score": 30, "detail": "长下影中阴，3996→3900探底反弹"},
            "mainforce": {"label": "大规模出逃", "score": 10, "detail": "主力净流出754亿，恐慌抛售"},
            "close_signal": {"label": "空头主导收盘", "detail": "收盘在日内低位，空头主导"}
        },
        "series": [3913.79]
    },
    {
        "name": "深证",
        "code": "sz399001",
        "close": 14522.85,
        "chg_pct": -3.48,
        "amount_yi": 14829,
        "main_flow_yi": -634.0,
        "score": 22,
        "tendency": "强空",
        "warn": "放量巨阴-3.48%，跌破所有均线，强空格局确立",
        "kline": {
            "trend": {"label": "强空", "score": 15, "detail": "收盘14522.85，全部均线下方"},
            "volprice": {"label": "放量暴跌", "score": 10, "detail": "放量-3.48%，成交14829亿，量比1.01"},
            "shape": {"label": "大阴线", "score": 25, "detail": "实体大阴线，14997→14437宽幅震荡"},
            "mainforce": {"label": "大规模出逃", "score": 10, "detail": "主力净流出634亿"},
            "close_signal": {"label": "空头主导收盘", "detail": "收盘位偏日内低位，空头主导"}
        },
        "series": [14522.85]
    },
    {
        "name": "创业板",
        "code": "sz399006",
        "close": 3723.52,
        "chg_pct": -3.10,
        "amount_yi": 6930,
        "main_flow_yi": -243.3,
        "score": 24,
        "tendency": "强空",
        "warn": "放量-3.10%，跌破短期均线，主力-243亿出逃",
        "kline": {
            "trend": {"label": "偏空", "score": 20, "detail": "收盘3723.52，跌破MA5/20"},
            "volprice": {"label": "放量下跌", "score": 20, "detail": "放量-3.10%，量比1.05"},
            "shape": {"label": "大阴线", "score": 25, "detail": "实体大阴线，3856→3691"},
            "mainforce": {"label": "出逃", "score": 15, "detail": "主力净流出243亿"},
            "close_signal": {"label": "空头主导收盘", "detail": "收盘位偏低，空头主导"}
        },
        "series": [3723.52]
    },
    {
        "name": "上证50",
        "code": "sh000016",
        "close": 2913.19,
        "chg_pct": -1.43,
        "amount_yi": 2555,
        "main_flow_yi": -138.8,
        "score": 38,
        "tendency": "偏空",
        "warn": "相对抗跌-1.43%，保险/银行逆势护盘",
        "kline": {
            "trend": {"label": "震荡偏空", "score": 35, "detail": "收盘2913.19，下MA20(2953)"},
            "volprice": {"label": "放量下跌", "score": 30, "detail": "量比1.13放量，-1.43%跌幅相对克制"},
            "shape": {"label": "中阴线", "score": 35, "detail": "带下影中阴，银行护盘托底"},
            "mainforce": {"label": "流出", "score": 25, "detail": "主力净流出139亿，但银行有逆势流入"},
            "close_signal": {"label": "中性收盘", "detail": "尾盘微有回升，非空头主导"}
        },
        "series": [2913.19]
    },
    {
        "name": "沪深300",
        "code": "sh000300",
        "close": 4695.38,
        "chg_pct": -1.79,
        "amount_yi": 9079,
        "main_flow_yi": -510.7,
        "score": 30,
        "tendency": "偏空",
        "warn": "跌破MA20，放量-1.79%，主力-511亿流出",
        "kline": {
            "trend": {"label": "偏空", "score": 25, "detail": "收盘4695.38，跌破MA20(4775)"},
            "volprice": {"label": "放量下跌", "score": 20, "detail": "量比1.02，放量-1.79%"},
            "shape": {"label": "中阴线", "score": 30, "detail": "中阴线，4745→4670"},
            "mainforce": {"label": "大规模出逃", "score": 15, "detail": "主力净流出511亿"},
            "close_signal": {"label": "空头主导收盘", "detail": "收盘位偏低"}
        },
        "series": [4695.38]
    },
    {
        "name": "中证500",
        "code": "sh000905",
        "close": 8138.14,
        "chg_pct": -4.30,
        "amount_yi": 5730,
        "main_flow_yi": None,
        "score": 18,
        "tendency": "强空",
        "warn": "暴跌-4.30%，跌破所有均线，中小盘恐慌踩踏",
        "kline": {
            "trend": {"label": "强空", "score": 10, "detail": "收盘8138.14，全部均线下方"},
            "volprice": {"label": "放量暴跌", "score": 10, "detail": "放量-4.30%"},
            "shape": {"label": "大阴线", "score": 20, "detail": "大阴线实体长"},
            "mainforce": {"label": "数据缺失", "score": 30, "detail": "主力净流入数据缺失"},
            "close_signal": {"label": "空头主导收盘", "detail": "收盘低位"}
        },
        "series": [8138.14]
    },
    {
        "name": "科创50",
        "code": "sh000688",
        "close": 1994.32,
        "chg_pct": -3.42,
        "amount_yi": 2149,
        "main_flow_yi": -92.7,
        "score": 25,
        "tendency": "偏空",
        "warn": "冲高回落巨幅震荡，早盘冲2110(+2.2%)→收1994(-3.42%)，高低差6.59%",
        "kline": {
            "trend": {"label": "偏空", "score": 20, "detail": "收盘1994.32，跌破MA5(2087)"},
            "volprice": {"label": "放量暴跌", "score": 15, "detail": "量比1.04，放量-3.42%"},
            "shape": {"label": "倒锤头巨阴", "score": 20, "detail": "早盘冲2110后一路回落，高点→低点6.59%振幅"},
            "mainforce": {"label": "流出", "score": 25, "detail": "主力净流出93亿"},
            "close_signal": {"label": "空头主导收盘", "detail": "收盘接近全日最低"}
        },
        "series": [1994.32]
    },
    {
        "name": "北证50",
        "code": "bj899050",
        "close": 1127.22,
        "chg_pct": -6.78,
        "amount_yi": 171,
        "main_flow_yi": None,
        "score": 8,
        "tendency": "强空",
        "warn": "暴跌-6.78%创年内新低！跌破全部均线，北交所流动性危机",
        "kline": {
            "trend": {"label": "强空", "score": 5, "detail": "收盘1127.22，全部均线下方，创52周新低"},
            "volprice": {"label": "恐慌抛售", "score": 5, "detail": "-6.78%暴跌，量比0.99"},
            "shape": {"label": "光头光脚巨阴", "score": 5, "detail": "最低价收盘，无任何反弹"},
            "mainforce": {"label": "数据缺失", "score": 30, "detail": "北交所主力数据缺失"},
            "close_signal": {"label": "空头绝对主导收盘", "detail": "光头光脚最低收盘"}
        },
        "series": [1127.22]
    },
    {
        "name": "恒生科技",
        "code": "hstech",
        "close": 4730,
        "chg_pct": -0.30,
        "amount_yi": None,
        "main_flow_yi": None,
        "score": 48,
        "tendency": "中性偏空",
        "warn": "港股相对A股抗跌，腾讯-0.56%/美团-0.95%，阿里+0.45%抬升整体",
        "kline": {
            "trend": {"label": "中性", "score": 45, "detail": "港股横盘，A股大跌传导有限"},
            "volprice": {"label": "平量", "score": 50, "detail": "成交平平，量比约0.6"},
            "shape": {"label": "普通K线", "score": 50, "detail": "小幅震荡，无方向"},
            "mainforce": {"label": "数据缺失", "score": 50, "detail": "恒生科技主力数据缺失"},
            "close_signal": {"label": "中性收盘", "detail": "窄幅震荡收盘"}
        },
        "series": [4730]
    }
]

# ── 情绪面 ──
# 今日全线普跌，估计涨跌比极差
SENTIMENT = {
    "fear_greed": 22,
    "factors": {
        "breadth": 15,
        "limit_up_down": 20,
        "main_flow": 10,
        "northbound": 35,
        "margin": 40,
        "volume": 15,
        "vix": None,
        "erp": None
    },
    "note": "今日全线暴跌，上证-2.06%/深证-3.48%/中证500-4.3%/北证50-6.78%，仅中药/银行逆势上涨。[[恐慌抛售|全市场主力净流出超1300亿，恐慌指数飙升]]，恐惧贪婪指数≈22(恐惧区间)。北向/融资/VIX数据延迟，按可比估算。"
}

# ── 板块传导 ──
SECTORS = {
    "strong": ["中药Ⅱ(+3.28%)", "国有大型银行Ⅱ(+2.15%)", "调味发酵品Ⅱ(+1.37%)", "白色家电(+1.22%)"],
    "rising": ["化学制药(-0.81%相对抗跌)", "医疗服务(-1.84%)", "创新药概念(-0.01%)"],
    "weak": ["消费电子(-6.50%)", "玻璃玻纤(-8.52%)", "半导体(-4.91%)", "元件(-6.28%)", "通信设备(-3.34%)", "光学光电子(-7.92%)", "电子化学品(-6.15%)"],
    "rotation": "资金从成长/科技集中出逃，全面转向防御：大银行(+2.15%)、中药(+3.28%)逆势大涨。成长→价值[[高低切换|高位科技→低位防御]]，恐慌级别轮动。",
    "chain": "半导体(-4.91%)及消费电子(-6.5%)领跌→通信设备(-3.34%)/元件(-6.28%)跟跌→北证50(-6.78%)中小盘流动性踩踏。银行/中药逆势为唯一避风港。"
}

# ── 核心研判 ──
CORE = {
    "market_qual": "全市场恐慌暴跌，A股全线崩跌（上证-2.06%/深证-3.48%/中证500-4.30%/北证50-6.78%），全市场主力净流出超1300亿。仅银行/中药/调味品等防御品种逆势飘红。科创50早盘冲+2%后倒灌收-3.42%[[日内反转|盘中冲高后急剧回落，空头完全主导]]，恐慌情绪蔓延。",
    "main_line": "全面溃败：半导体-4.91%/消费电子-6.50%/通信设备-3.34%等科技全线重挫；仅中药+3.28%/银行+2.15%/调味品+1.37%成为少数避风港。",
    "action_guideline": "⚠️ 系统性风险释放，执行防御应对：①半导体重仓（约65%）偏空·警惕，逢反抽大幅降仓至30%以下，不抄底；②港股创新药逆势偏多持有观察；③医药/消费防守仓不加仓；④现金提高至30%+准备急跌后低吸机会；⑤严格停损，若某标的一周内继续-8%则无条件止损；⑥北证50暴跌预警，相关持仓重点关注流动性风险。",
    "metrics": {
        "amount_yi": 28178,
        "fear_greed": 22,
        "breadth_ratio": 0.35
    }
}

# ── 持仓联动（从portfolio.json读取） ──
def build_holdings():
    try:
        pm = json.load(open(os.path.join(os.path.dirname(DATA), "config", "portfolio.json"), encoding="utf-8"))
        hs = []
        for h in pm.get("holdings", []):
            # 判断安全距
            try:
                rp = float(h.get("hold_return_pct", 0))
            except (TypeError, ValueError):
                rp = 0
            # risk_dist: 从成本线到-8%止损的距离(%)
            try:
                cost = float(h.get("cost_basis", 0))
                mv = float(h.get("market_value", 0))
                if cost > 0 and mv > 0:
                    shares = abs(mv / cost)
                    stop_loss_val = cost * 0.92  # -8% from cost
                    rd = abs(mv - stop_loss_val * shares) / mv * 100 if mv > 0 else None
                else:
                    rd = None
            except (TypeError, ValueError):
                rd = None
            if isinstance(rp, (int, float)):
                if rp <= -5:
                    lv = "警惕"; sig = "强空"
                elif rp <= -3:
                    lv = "警惕"; sig = "偏空"
                elif rp >= 3:
                    lv = "持有"; sig = "偏多"
                elif rp >= 0:
                    lv = "中性"; sig = "中性偏多"
                else:
                    lv = "中性"; sig = "中性"
            else:
                lv = "中性"; sig = "中性"
            sector = h.get("sector", "")
            related = h.get("related_index", "")
            sup = h.get("cost_basis", None)
            hs.append({
                "name": h.get("name", ""),
                "related": related or sector,
                "level": lv,
                "signal": sig,
                "support": round(float(sup) * 0.92, 2) if sup else None,
                "pressure": None,
                "risk_dist_pct": round(rd, 2) if rd else None,
            })
        return hs
    except Exception as e:
        print(f"portfolio load fail: {e}")
        return []

# ── 预测 ──
PREDICTIONS = [
    {"target": "上证", "d1": "偏空震荡", "d2": "震荡", "d3": "震荡企稳", "conf": "中"},
    {"target": "深证", "d1": "偏空", "d2": "偏空震荡", "d3": "震荡", "conf": "高"},
    {"target": "创业板", "d1": "偏空", "d2": "偏空震荡", "d3": "震荡", "conf": "高"},
    {"target": "上证50", "d1": "震荡", "d2": "中性", "d3": "偏多震荡", "conf": "低"},
    {"target": "沪深300", "d1": "偏空震荡", "d2": "震荡", "d3": "震荡", "conf": "中"},
    {"target": "中证500", "d1": "偏空", "d2": "偏空震荡", "d3": "震荡", "conf": "高"},
    {"target": "科创50", "d1": "偏空", "d2": "震荡", "d3": "偏空震荡", "conf": "中"},
    {"target": "北证50", "d1": "偏空", "d2": "偏空", "d3": "偏空震荡", "conf": "高"},
    {"target": "恒生科技", "d1": "中性", "d2": "中性", "d3": "中性偏多", "conf": "低"},
]

WATCH_LEVELS = [
    {"type": "上行触发", "text": "上证若收复MA250(3939)+放量，可能企稳反弹"},
    {"type": "下行触发", "text": "上证若跌破今日低点3900+缩量，继续探底"},
    {"type": "上行触发", "text": "科创50若能站稳2000+放量，或短期超跌反弹"},
    {"type": "下行触发", "text": "北证50若继续-4%+，可能触发流动性危机扩散"},
    {"type": "上行触发", "text": "银行/中药持续性决定防御强度"},
]

# ── 风险提示 ──
RISKS = [
    {"level": "高", "text": "北证50暴跌-6.78%创52周新低，警惕中小盘流动性危机蔓延"},
    {"level": "高", "text": "半导体/科技股全线重挫（-4.91%~-8.52%），持仓集中度>60%风险暴露"},
    {"level": "高", "text": "全市场主力净流出超1300亿，恐慌情绪蔓延，短期可能继续下探"},
    {"level": "中", "text": "科创50早盘冲高后倒灌收-3.42%，技术面恶化"},
    {"level": "中", "text": "防御品种（中药+3.28%/银行+2.15%）逆势走强但容量有限"},
]

DISCLAIMER = "⚠️ 本报告结论基于公开行情数据（westock-mcp），辅助个人投资决策参考，不构成投资建议。技术面指标为纯量化计算(MA/MACD/KDJ)，不预测黑天鹅等不可控事件。股市有风险，投资需谨慎。"

# ── 数据可信度 ──
CREDIBILITY = [
    {"item": "指数快照/涨跌幅", "status": "ok", "note": "westock实时(收盘2026-07-13)"},
    {"item": "MA/技术面", "status": "ok", "note": "westock实时(T2)"},
    {"item": "主力净流入", "status": "warn", "note": "中证500/北证50/恒科主力流入缺失（westock字段为空）"},
    {"item": "情绪8因子", "status": "warn", "note": "涨跌家数为07-10未更新，今日按指数跌幅大幅估算下调"},
    {"item": "板块资金流向", "status": "ok", "note": "westock板块排名(含行业/概念)，半导体-41.2亿主力净流出"},
    {"item": "250日OHLC日K", "status": "pending", "note": "待 fetch_kline + tech_calc 后渲染蜡烛图"},
    {"item": "更新时间", "status": "ok", "note": "2026-07-13 16:16 收盘"}
]

def main():
    holdings = build_holdings()
    out = {
        "date": "2026-07-13",
        "updated_at": "2026-07-13 15:30 收盘",
        "data_tier": "T2",
        "core": CORE,
        "credibility": CREDIBILITY,
        "indices": INDICES,
        "sentiment": SENTIMENT,
        "sectors": SECTORS,
        "holdings": holdings,
        "predictions": PREDICTIONS,
        "watch_levels": WATCH_LEVELS,
        "risks": RISKS,
        "disclaimer": DISCLAIMER,
    }
    out_path = os.path.join(DATA, "market_2026-07-13.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"saved {out_path} ({os.path.getsize(out_path)} bytes)")
    print(f"holdings: {len(holdings)} items")

if __name__ == "__main__":
    main()
