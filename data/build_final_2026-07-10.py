# -*- coding: utf-8 -*-
"""Assemble market_2026-07-10.json + market_raw_ohlc_2026-07-10.json."""
import json, os, re

DATA = r"C:/Users/LEGION/Nutstore/1/daily-report/data"
RAW = os.path.join(DATA, "neodata_raw", "neodata_raw")
DATE = "2026-07-10"

interim = json.load(open(os.path.join(DATA, "_interim_2026-07-10.json"), encoding="utf-8"))["D"]
yest = json.load(open(os.path.join(DATA, "market_2026-07-09.json"), encoding="utf-8"))
yest_series = {x["code"]: x.get("series") for x in yest["indices"]}

def num(s):
    try: return float(str(s).replace(",","").replace("%","").strip())
    except: return None

# ---------- label helpers ----------
def trend_label(s):
    if s>=85: return "强多"
    if s>=65: return "偏多"
    if s>=40: return "震荡"
    if s>=16: return "偏空"
    return "强空"
def vp_label(s):
    if s>=80: return "抢筹"
    if s>=60: return "健康"
    if s>=50: return "平量"
    if s>=40: return "缩量止跌"
    return "恐慌抛售"
def shp_label(chg):
    if chg is None: return "中性"
    if chg>=3: return "突破"
    if chg>0: return "反弹"
    if chg<=-3: return "高位巨阴"
    return "回调"
def mf_label(mf):
    if mf is None: return "待验证"
    if mf>=50: return "抢筹"
    if mf>=0: return "做多"
    if mf>-100: return "减仓"
    return "出货"

# ---------- indices ----------
indices = []
for code, v in interim.items():
    nm = v["nm"]; s = v["s"]; sc = v["sc"]; clab = v["clab"]; cdet = v["cdet"]
    c = s["close"]; chg = s["chg"]; ma = s["ma"]; mf = s["mainflow"]
    ma5,ma20 = ma.get("ma5"), ma.get("ma20")
    # detail strings
    trend_det = clab
    if ma5 and ma20:
        trend_det = f"收盘{c:.2f}，上MA5({ma5:.0f})" + ("" if (c>ma5) else "失败") + f"，下MA20({ma20:.0f})"
    elif ma5:
        trend_det = f"收盘{c:.2f}，MA5 {ma5:.0f}"
    vp_det = f"{'放量' if (s.get('turnover') or 0)>=2 else '平量'}{chg:+.2f}%"
    shp_det = cdet
    mf_det = f"主力{'净流出' if (mf or 0)<0 else '净流入'}{abs(mf) if mf else '—'}亿" if mf is not None else "缺失"
    kline = {
        "trend": {"label": trend_label(sc["trend"]), "score": sc["trend"], "detail": trend_det},
        "volprice": {"label": vp_label(sc["vp"]), "score": sc["vp"], "detail": vp_det},
        "shape": {"label": shp_label(chg), "score": sc["shp"], "detail": shp_det},
        "mainforce": {"label": mf_label(mf), "score": sc["mfsc"], "detail": mf_det},
        "close_signal": {"label": clab, "detail": cdet},
    }
    # warn
    warn = None
    if code=="sh000688":
        warn="单日-5.53%高位巨阴：昨日+8.41%极端超买后的获利回吐；距MA5(2053)仅一步，破位则短线转弱"
    elif code in ("sz399001","sz399006","bj899050"):
        warn="收盘跌破全部均线，短线偏弱"
    elif code=="sh000001":
        warn="跌破MA5/20/60，全市场主力净流出拖累"
    # series
    ser = yest_series.get(code)
    if isinstance(ser, list) and ser:
        series = ser + [round(c,2)]
    else:
        series = [round(c,2)] if c else None
    indices.append({
        "name": nm, "code": code, "close": round(c,2) if c else None,
        "chg_pct": chg, "amount_yi": s.get("amount"), "main_flow_yi": mf,
        "score": sc["score"], "tendency": sc["tend"], "kline": kline, "warn": warn,
        "series": series,
    })

# ---------- sectors conduction ----------
sectors = {
    "strong": ["军工(航天装备/航海装备)", "医疗服务", "港股创新药"],
    "rising": ["食品饮料/大消费", "人工智能(应用端)"],
    "weak": ["半导体", "CPO/通信设备", "证券/大金融", "北证50"],
    "rotation": "资金由昨日半导体/AI硬件主线大幅获利了结(半导体-269亿主力出逃)，高低切至军工、医药、消费等低位景气/防御方向；高低切换特征明显",
    "chain": "传导链：半导体-6.26%重挫→拖累科创50(-5.53%)/创业板(-4.37%)；沪深300(-1.96%)/上证(-1%)受权重蓝筹(上证50守住均线)支撑跌幅收窄；恒科平盘(港股创新药+3.25%对冲科技回调)；中证500(-1.72%)中小成长跟跌；北证50(-0.02%)持续弱势。板块：半导体/CPO资金出逃→AI硬件链承压；军工/医疗服务/消费/港股创新药获流入→成新主线。",
}

# ---------- sentiment ----------
sentiment = {
    "fear_greed": 50,
    "factors": {"breadth":50,"limit_up_down":50,"main_flow":25,"northbound":50,"margin":50,"volume":70,"vix":50,"erp":62},
    "note":"逆向校准：综合指数约50处中性区间，未达>75减仓预警；但全市场主力净流出显著(上证-205/深证-245/沪深300-363亿，半导体-269亿领衔)，局部科技退潮需警惕。情绪指令：中性——盈利半导体仓分批止盈、不接飞刀；不覆盖-8%硬止损。广度/涨跌停/北向/融资/VIX 因子缺失按中性(50)计。",
}

# ---------- holdings linkage (from watchlist) ----------
wl = json.load(open(r"C:/Users/LEGION/Nutstore/1/daily-report/config/watchlist.json", encoding="utf-8"))
# map related_index -> tendency label (from sectors / index conduction)
sec_tend = {
    "半导体": "偏空", "半导体材料设备": "偏空", "通信设备/CPO": "偏空", "沪深300成长": "偏空",
    "恒生医疗": "偏多", "港股创新药": "偏多", "中证煤炭": "中性", "主要消费": "中性偏多",
    "纯债": "中性", "纳斯达克100": "中性",
}
def risk_dist(r):
    r = num(r) or 0
    return round(max(0, -r)/8.0*100, 1)

holdings = []
for h in wl["holdings"]:
    rel = h.get("related_index") or h.get("sector")
    lvl = sec_tend.get(rel, "中性")
    if lvl=="偏空": sig="偏空·警惕"
    elif lvl=="偏多": sig="偏多·持有"
    elif lvl=="中性偏多": sig="中性偏多·持有"
    else: sig="中性·防御"
    holdings.append({
        "name": h["name"], "related": rel, "signal": sig, "level": lvl,
        "support": None, "pressure": None,
        "risk_dist_pct": risk_dist(h.get("hold_return_pct")),
    })

# ---------- predictions ----------
predictions = [
    {"target":"科创50","d1":"震荡-1~2%(测MA5 2053)","d2":"震荡±2%","d3":"偏多(守MA20 1979)","conf":"中","trigger":"跌破MA5(2053)→短线转弱"},
    {"target":"创业板","d1":"偏空-0.5~2%","d2":"偏弱","d3":"中性","conf":"中","trigger":"收复MA60(3938)转强"},
    {"target":"沪深300","d1":"震荡±1%","d2":"震荡","d3":"中性偏多","conf":"中","trigger":"站稳4887(MA20)确认"},
    {"target":"上证50","d1":"震荡±0.8%(抗跌)","d2":"中性","d3":"中性偏多","conf":"中高","trigger":"失守MA60(2943)转弱"},
    {"target":"半导体板块","d1":"继续回调-2~4%或弱反弹","d2":"震荡","d3":"中性","conf":"中","trigger":"龙头放量反包→修复"},
    {"target":"北证50","d1":"偏弱-0.5~1%","d2":"偏弱","d3":"中性","conf":"中","trigger":"跌破1203前低→加速"},
    {"target":"恒生科技","d1":"中性±1%","d2":"中性","d3":"中性偏多","conf":"中","trigger":"美股/中东扰动→下行"},
]

watch_levels = [
    {"type":"上行确认","text":"沪深300 收复4887（MA20）"},
    {"type":"下行预警","text":"科创50 跌破2053（MA5）则短线转弱"},
    {"type":"风险预警","text":"半导体龙头继续放量下挫→科技情绪退潮"},
]
risks = [
    {"level":"高","text":"半导体/科创高位巨阴，获利盘兑现压力大(半导体-269亿主力出逃)"},
    {"level":"高","text":"半导体集中度占总资产65.5%/占持仓74.5%，单一板块敞口过大"},
    {"level":"中","text":"全市场主力净流出(上证-205/深证-245/沪深300-363亿)，价跌量增"},
    {"level":"中","text":"科创50单日-5.53%技术破位风险(破MA5则转弱)"},
    {"level":"低","text":"外部扰动/美股波动"},
]
core = {
    "market_qual":"全市场放量回调，昨日半导体/AI主线今日重挫(-6.26%)，资金高低切至军工/医药/消费；科创50单日-5.53%高位巨阴[[巨阴线|单日大实体阴线，高位获利盘集中兑现，空头动能释放]]",
    "main_line":"军工(航天+10.2%/航海+4%)、医疗服务、港股创新药(+3.25%)、消费接力；半导体/CPO/证券获利回吐",
    "action_guideline":"持仓以锁利为主：半导体重仓逢高分批止盈、不追跌；港药/消费转强可持有；严守-8%硬止损，现金12%待急跌低吸",
    "metrics":{"amount_yi":33000,"fear_greed":50,"breadth_ratio":None},
}
credibility = [
    {"item":"指数快照/涨跌幅","status":"ok","note":"neodata实时(收盘)"},
    {"item":"MA/技术面","status":"ok","note":"技术面接口(T2)"},
    {"item":"主力净流入","status":"warn","note":"资金流向为估算值(T2)，中证500/北证50/恒科缺失"},
    {"item":"情绪8因子","status":"warn","note":"广度/涨跌停/北向/融资/VIX缺失→中性计"},
    {"item":"250日OHLC日K","status":"warn","note":"neodata历史序列截断，蜡烛图降级为迷你走势"},
    {"item":"更新时间","status":"ok","note":"2026-07-10 15:30 收盘"},
]

out = {
    "date": DATE, "updated_at": "2026-07-10 15:30 收盘", "data_tier": "T2",
    "core": core, "credibility": credibility, "indices": indices,
    "sentiment": sentiment, "sectors": sectors, "holdings": holdings,
    "predictions": predictions, "watch_levels": watch_levels, "risks": risks,
    "disclaimer":"⚠ 本分析仅供参考,预测为模型研判,历史不代表未来。数据含T2估算与AI模型推断,不构成投资建议。涨红跌绿按A股惯例。",
}
json.dump(out, open(os.path.join(DATA, f"market_{DATE}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("WROTE market_%s.json" % DATE)

# ---------- raw ohlc (best-effort; neodata truncates history -> mostly <6 rows) ----------
name_map = {c: v["nm"] for c,v in interim.items()}
raw_indices = []
for code, v in interim.items():
    s = v["s"]
    # single today row (honest; history truncated by neodata)
    if s.get("close"):
        raw_indices.append({"code": code, "name": v["nm"],
            "ohlc": [[DATE, s.get("open"), s.get("high"), s.get("low"), s.get("close"),
                      s.get("amount")]]})
raw = {"date": DATE, "indices": raw_indices, "sectors": []}
json.dump(raw, open(os.path.join(DATA, f"market_raw_ohlc_{DATE}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("WROTE market_raw_ohlc_%s.json (%d indices)" % (DATE, len(raw_indices)))
