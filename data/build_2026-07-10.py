# -*- coding: utf-8 -*-
"""Build market_2026-07-10.json + market_raw_ohlc_2026-07-10.json from neodata raw."""
import json, os, re

RAW = r"C:/Users/LEGION/Nutstore/1/daily-report/data/neodata_raw/neodata_raw"
DATA = r"C:/Users/LEGION/Nutstore/1/daily-report/data"
DATE = "2026-07-10"

INDICES = [
    ("上证", "sh000001"), ("深证", "sz399001"), ("创业板", "sz399006"),
    ("上证50", "sh000016"), ("沪深300", "sh000300"), ("中证500", "sh000905"),
    ("科创50", "sh000688"), ("北证50", "bj899050"), ("恒生科技", "hstech"),
]

def load(name):
    return json.load(open(os.path.join(RAW, name), encoding="utf-8"))

def num(s):
    if s is None: return None
    s = str(s).replace(",", "").replace("%", "").strip()
    try: return float(s)
    except: return None

def parse_snap(code):
    d = load(f"snap_{code}.json")
    ap = d["data"]["apiData"]["apiRecall"]
    info = {"close":None,"chg":None,"open":None,"high":None,"low":None,"amount":None,"turnover":None,
            "ma":{}, "macd":{}, "kdj":{}}
    for a in ap:
        c = a.get("content","")
        if "历史行情数据" in c:
            # find the 2026-07-10 row
            for line in c.splitlines():
                if line.startswith("| 2026-07-10"):
                    parts = [p.strip() for p in line.split("|")]
                    # [ '', date, open, close, chg, vol, amount, high, low, turnover, '' ]
                    try:
                        info["open"]=num(parts[2]); info["close"]=num(parts[3]); info["chg"]=num(parts[4])
                        info["turnover"]=num(parts[9]); info["high"]=num(parts[7]); info["low"]=num(parts[8])
                        amt=num(parts[6])  # 元
                        if amt: info["amount"]=round(amt/1e8,1)
                    except Exception as e: pass
        if "技术面信息" in c or "技术面指标" in c:
            # MA table: 交易日期|开盘|收盘|最高|最低|MA5|MA10|MA20|MA30|MA60|MA120|MA250
            for line in c.splitlines():
                if line.startswith("| 20260710"):
                    parts=[p.strip() for p in line.split("|")]
                    try:
                        if info["open"] is None: info["open"]=num(parts[2])
                        if info["close"] is None: info["close"]=num(parts[3])
                        if info["high"] is None: info["high"]=num(parts[4])
                        if info["low"] is None: info["low"]=num(parts[5])
                        info["ma"]={"ma5":num(parts[6]),"ma10":num(parts[7]),"ma20":num(parts[8]),
                                   "ma60":num(parts[10]),"ma120":num(parts[11]),"ma250":num(parts[12])}
                    except: pass
                if "MACD差离值" in line and line.startswith("| 20260710"):
                    parts=[p.strip() for p in line.split("|")]
                    try: info["macd"]={"dif":num(parts[2]),"dea":num(parts[3]),"hist":num(parts[4])}
                    except: pass
                if "KDJ指标K线" in line and line.startswith("| 20260710"):
                    parts=[p.strip() for p in line.split("|")]
                    try: info["kdj"]={"k":num(parts[2]),"d":num(parts[3]),"j":num(parts[4])}
                    except: pass
    return info

def parse_mf(code):
    # prefer mf_ file
    try:
        d = load(f"mf_{code}.json")
        t = d["data"]["apiData"]["apiRecall"][0]["content"]
        m = re.search(r"主力净流入([-\d.]+)元", t)
        if m:
            v = round(float(m.group(1))/1e8, 1)
            if abs(v) < 1: return None   # neodata returned 0/empty -> treat as missing
            return v
    except: pass
    return None

# ---- parse all indices ----
idx_raw = {}
for nm, code in INDICES:
    s = parse_snap(code)
    mf = parse_mf(code)
    s["mainflow"] = mf
    idx_raw[code] = (nm, s)

# ---- overrides where neodata truncated / returned empty ----
# 沪深300: 技术面信息 block truncated -> use real 07-09 MA (one day stale, acceptable)
idx_raw["sh000300"][1]["ma"] = {"ma5":4821.65,"ma10":4865.41,"ma20":4887.25,
                                "ma60":4850.42,"ma120":None,"ma250":None}
# 恒科: 历史走势 rows are "未开盘"; daily chg from 07-09 close 4731.56
idx_raw["hstech"][1]["chg"] = round((4730.32-4731.56)/4731.56*100, 2)

# ---- five-dimension scoring ----
def score_index(nm, s):
    c = s["close"]; ma = s["ma"]; chg = s["chg"]; mf = s["mainflow"]
    ma5,ma10,ma20,ma60 = ma.get("ma5"),ma.get("ma10"),ma.get("ma20"),ma.get("ma60")
    mas = [x for x in (ma5,ma10,ma20,ma60) if x is not None]
    # trend
    n = sum(1 for x in mas if c>x)
    arrange = (ma5 and ma10 and ma20 and ma60 and ma5>ma10>ma20>ma60)
    if not mas:
        trend=50
    elif n==len(mas) and arrange: trend=92
    elif n==len(mas): trend=82
    elif c and ma20 and c>ma20: trend=68
    elif c and ma5 and c>ma5: trend=55
    elif c and ma60 and c>ma60: trend=40
    else: trend=25
    # volprice
    heavy = (s.get("turnover") or 0) >= 2.0
    if chg is None: vp=50
    elif chg>0 and heavy: vp=85
    elif chg>0: vp=60
    elif chg<0 and heavy: vp=20
    else: vp=58
    # shape
    o,h,l,cc = s.get("open"),s.get("high"),s.get("low"),s.get("close")
    if None in (o,h,l,cc) or cc==0:
        shp=50
    else:
        rng=h-l; body=cc-o
        if rng==0: shp=50
        elif body/rng<0.1: shp=50
        elif body>0 and body/rng>0.6: shp=85
        elif body>0: shp=62
        elif body<0 and abs(body)/rng>0.6: shp=20
        else: shp=42
    # mainforce
    if mf is None: mfsc=50
    elif mf>=0: mfsc=min(80, 70+mf/20.0)
    else: mfsc=max(15, 30+mf/20.0)
    score = round(0.40*trend+0.30*vp+0.15*shp+0.15*mfsc)
    # tendency label
    if score>=80: tend="强多"
    elif score>=65: tend="偏多"
    elif score>=45: tend="中性"
    elif score>=35: tend="偏空"
    else: tend="强空"
    return {"trend":trend,"vp":vp,"shp":shp,"mfsc":round(mfsc,1),"score":score,"tend":tend}

# ---- close signal ----
def close_signal(nm, s):
    c=s["close"]; ma=s["ma"]
    above=[k for k in ("ma5","ma10","ma20","ma60") if ma.get(k) is not None and c>ma[k]]
    below=[k for k in ("ma5","ma10","ma20","ma60") if ma.get(k) is not None and c<ma[k]]
    if below and not above: lab="跌破"+below[0].upper()
    elif above and not below: lab="站上"+above[-1].upper()
    else: lab="均线纠缠"
    # candle detail
    chg=s["chg"]
    if chg is not None:
        if chg<=-3: det="大阴线,获利盘兑现"
        elif chg<0: det="小阴线,回调"
        elif chg>=3: det="大阳线"
        else: det="小阳线,反弹"
    else: det=""
    return lab, det

D = {}
for code,(nm,s) in idx_raw.items():
    sc = score_index(nm,s)
    lab,det = close_signal(nm,s)
    D[code] = {"nm":nm,"s":s,"sc":sc,"clab":lab,"cdet":det}

# ---- print summary for verification ----
for code,(nm,s) in idx_raw.items():
    sc=D[code]["sc"]
    print(f"{nm:6} close={s['close']} chg={s['chg']} amt={s['amount']} mf={s['mainflow']} "
          f"MA5={s['ma'].get('ma5')} MA20={s['ma'].get('ma20')} MA60={s['ma'].get('ma60')} "
          f"trend={sc['trend']} vp={sc['vp']} shp={sc['shp']} mfsc={sc['mfsc']} SCORE={sc['score']} {sc['tend']} | {D[code]['clab']}")

# persist intermediate for next step
json.dump({"D":{c:{"nm":v["nm"],"s":v["s"],"sc":v["sc"],"clab":v["clab"],"cdet":v["cdet"]} for c,v in D.items()}},
          open(os.path.join(DATA,"_interim_2026-07-10.json"),"w",encoding="utf-8"), ensure_ascii=False, indent=1)
print("INTERIM SAVED")
