import json, os, re

BASE = "C:/Users/LEGION/Nutstore/1/daily-report/data"
RAW = os.path.join(BASE, "neodata_raw")
DATE = "2026-07-08"
WL = json.load(open(os.path.join(BASE, "..", "config", "watchlist.json"), encoding="utf-8"))

def load(key):
    p = os.path.join(RAW, key + ".json")
    if not os.path.exists(p): return None
    try: return json.load(open(p, encoding="utf-8"))
    except: return None

def api_blocks(key):
    d = load(key);  dd = (d or {}).get("data") or {}
    return dd.get("apiData", {}).get("apiRecall", []) or []

def doc_groups(key):
    d = load(key);  dd = (d or {}).get("data") or {}
    docs = dd.get("docData", {})
    return docs.get("docRecall", []) if docs else []

def num(s):
    if s is None: return None
    s = str(s).replace(",", "").replace("%", "").strip()
    try: return float(s)
    except: return None

def first_row(content):
    lines = [l for l in content.split("\n") if l.strip().startswith("|")]
    if len(lines) < 3: return None
    hdr = [h.strip() for h in lines[0].strip().strip("|").split("|")]
    row = [v.strip() for v in lines[2].strip().strip("|").split("|")]
    if len(row) < len(hdr): return None
    return dict(zip(hdr, row))

def first_change_pct(content):
    lines = [l for l in content.split("\n") if l.strip().startswith("|")]
    for i, l in enumerate(lines):
        if "单日涨跌幅" in l:
            hdr = [h.strip() for h in l.strip().strip("|").split("|")]
            if i + 2 < len(lines):
                row = [v.strip() for v in lines[i+2].strip().strip("|").split("|")]
                if len(row) >= len(hdr):
                    d = dict(zip(hdr, row))
                    return num(d.get("单日涨跌幅(%)"))
    return None

def scan_change(content):
    # any table with 单日涨跌幅 / 涨跌幅
    v = first_change_pct(content)
    if v is not None: return v
    r = first_row(content)
    if r:
        for k, val in r.items():
            if "涨跌幅" in k or "增长率" in k:
                n = num(val)
                if n is not None: return n
    return None

# ---------- Indices (07-08) ----------
indices = {}
for key, name in [("mkt_sz","上证指数"),("mkt_cyb","创业板指"),("mkt_hs300","沪深300")]:
    for b in api_blocks(key):
        c = b.get("content","")
        r = first_row(c)
        if r and ("收盘价" in " ".join(r.keys()) or "最新价格" in " ".join(r.keys())):
            close = None; chg = None
            for k,v in r.items():
                if "收盘价" in k or "最新价格" in k: close = num(v)
                if "涨跌幅" in k: chg = num(v)
            indices[name] = {"close": close, "change_pct": chg, "date": r.get("日期")}
            break

# ---------- Sectors 07-08 ----------
sectors_0708 = {}
for key, name in [("sector_semicon","半导体"),("sector_ai","人工智能"),("sector_cpo","CPO通信"),
                  ("sector_coal","煤炭"),("sector_consum","中证主要消费"),("sector_hkdrug","港股创新药"),
                  ("sector_nasdaq","纳斯达克100")]:
    v = None
    for b in api_blocks(key):
        v = scan_change(b.get("content",""))
        if v is not None: break
    sectors_0708[name] = v

# ---------- Benchmarks 07-07 ----------
benchmarks_0707 = {}
for key, name in [("bm_semicon_0707","半导体"),("bm_ai_0707","人工智能"),("bm_hkdrug_0707","港股创新药"),
                  ("bm_coal_0707","煤炭"),("bm_consum_0707","中证主要消费"),("bm_comm_0707","通信设备"),
                  ("bm_nasdaq_0707","纳斯达克100"),("bm_sz_0707","上证指数"),("bm_cyb_0707","创业板指")]:
    v = None
    for b in api_blocks(key):
        v = scan_change(b.get("content",""))
        if v is not None: break
    benchmarks_0707[name] = v

# ---------- Fund NAV (07-07 official) ----------
fund_nav = {}
for key, name in [("fund_dfaic","东方人工智能主题混合C"),("fund_dfa","东方阿尔法科技优选混合C"),
                  ("fund_yw","永赢先锋半导体智选混合C"),("fund_fgcoal","富国中证煤炭指数C"),
                  ("fund_ctic","财通集成电路产业股票C"),("fund_ctcz","财通成长优选混合C"),
                  ("fund_thcpo","天弘中证全指通信设备指数C"),("fund_gfnas","广发纳斯达克100ETF联接")]:
    nav=None; dchg=None; ytd=None; dt=None
    for b in api_blocks(key):
        r = first_row(b.get("content",""))
        if r and "单位净值" in " ".join(r.keys()):
            try: nav=num(r.get("单位净值(元)"))
            except: pass
            try: dchg=num(r.get("复权单位净值日增长率"))
            except: pass
            try: ytd=num(r.get("今年以来回报率(%)"))
            except: pass
            dt=r.get("交易日期")
            break
    fund_nav[name] = {"nav":nav,"daily_0707":dchg,"ytd":ytd,"date":dt}

# ctic from re-query
for b in api_blocks("fund_ctic_nav"):
    r = first_row(b.get("content",""))
    if r and "单位净值" in " ".join(r.keys()):
        fund_nav["财通集成电路产业股票C"] = {"nav":num(r.get("单位净值(元)")),
            "daily_0707":num(r.get("复权单位净值日增长率")),
            "ytd":num(r.get("今年以来回报率(%)")), "date":r.get("交易日期")}
# jsxf from re-query
for b in api_blocks("fund_jsxf_nav"):
    r = first_row(b.get("content",""))
    if r and "单位净值" in " ".join(r.keys()):
        fund_nav["嘉实中证主要消费ETF发起联接C"] = {"nav":num(r.get("单位净值(元)")),
            "daily_0707":num(r.get("复权单位净值日增长率")),
            "ytd":num(r.get("今年以来回报率(%)")), "date":r.get("交易日期")}

# ---------- Fundamentals: ranking / top10 / industry ----------
def extract_ranking(key):
    for b in api_blocks(key):
        if b.get("type") in ("基金季度年度收益排名","基金各阶段同类排名数据"):
            r = first_row(b.get("content",""))
            if r:
                rank = r.get("该基金在指定季度/年度的同类基金收益排名")
                total = r.get("参与排名的同类基金总数量")
                tdesc = r.get("时间描述，例如：2023年第四季度")
                return {"rank": num(rank), "total": num(total), "period": tdesc}
    return None

def extract_top10(key):
    for b in api_blocks(key):
        if b.get("type") == "基金重仓资产查询":
            c = b.get("content","")
            lines = [l for l in c.split("\n") if l.strip().startswith("|")]
            hdr_i = None
            for i,l in enumerate(lines):
                if "股票名称" in l and "持仓比例" in l:
                    hdr_i = i; break
            if hdr_i is None: return []
            hdr = [h.strip() for h in lines[hdr_i].strip().strip("|").split("|")]
            out = []
            for j in range(hdr_i+2, len(lines)):
                row = [v.strip() for v in lines[j].strip().strip("|").split("|")]
                if len(row) < len(hdr): continue
                d = dict(zip(hdr, row))
                nm = d.get("股票名称")
                if not nm or nm in ("股票名称",): continue
                out.append({"name": nm, "code": d.get("股票代码"), "weight": num(d.get("持仓比例")),
                            "trend": d.get("持仓比例变化趋势")})
                if len(out) >= 10: break
            return out
    return []

def extract_industry(key):
    for b in api_blocks(key):
        if b.get("type") == "基金行业组合查询":
            c = b.get("content","")
            lines = [l for l in c.split("\n") if l.strip().startswith("|")]
            hdr_i=None
            for i,l in enumerate(lines):
                if "行业" in l and "持仓比例" in l:
                    hdr_i=i; break
            if hdr_i is None: return []
            hdr=[h.strip() for h in lines[hdr_i].strip().strip("|").split("|")]
            out=[]
            for j in range(hdr_i+2,len(lines)):
                row=[v.strip() for v in lines[j].strip().strip("|").split("|")]
                if len(row)<len(hdr): continue
                d=dict(zip(hdr,row))
                nm=d.get("行业分类") or d.get("申万一级行业") or d.get("行业名称")
                if not nm: continue
                out.append({"industry":nm,"weight":num(d.get("持仓比例"))})
                if len(out)>=8: break
            return out
    return []

# ---------- Fund master list ----------
funds_cfg = [
    ("东方人工智能主题混合C","dfaic","半导体/AI","半导体",["半导体","人工智能"]),
    ("东方阿尔法科技优选混合C","dfa","半导体/科技优选","半导体",["半导体"]),
    ("广发港股创新药ETF联接(QDII)C","gfhd","港股创新药/QDII","港股创新药",["港股创新药"]),
    ("永赢先锋半导体智选混合C","yw","半导体/存储芯片","半导体",["半导体"]),
    ("富国中证煤炭指数C","fgcoal","中证煤炭/高股息防御","煤炭",["煤炭"]),
    ("嘉实中证主要消费ETF发起联接C","jsxf","中证主要消费","中证主要消费",["中证主要消费"]),
    ("财通集成电路产业股票C","ctic","集成电路","半导体",["半导体"]),
    ("财通成长优选混合C","ctcz","成长优选","人工智能",["人工智能"]),
    ("天弘中证全指通信设备指数C","thcpo","通信设备/CPO","CPO通信",["通信设备"]),
    ("广发纳斯达克100ETF联接","gfnas","纳斯达克100/美股QDII","纳斯达克100",["纳斯达克100"]),
]

# watchlist lookup
wl_hold = {h["name"]: h for h in WL["holdings"]}

funds = []
for name, short, sector, proxy_sector, bm_list in funds_cfg:
    wh = wl_hold.get(name, {})
    mv = wh.get("market_value"); wpct = wh.get("weight_pct"); risk = wh.get("risk_flag"); status = wh.get("status")
    # 07-07 official
    fv = fund_nav.get(name, {})
    # 07-08 proxy (sector)
    proxy = None
    for s in bm_list:
        if sectors_0708.get(s) is not None:
            proxy = sectors_0708[s]; break
    if proxy is None:
        proxy = sectors_0708.get(proxy_sector)
    # benchmark 07-07
    bm = None
    for s in bm_list:
        if benchmarks_0707.get(s) is not None:
            bm = benchmarks_0707[s]; break
    if bm is None:
        bm = benchmarks_0707.get(proxy_sector)
    daily0707 = fv.get("daily_0707")
    # alpha = fund 07-07 return - benchmark 07-07 return
    alpha = None
    if daily0707 is not None and bm is not None:
        alpha = round(daily0707 - bm, 2)
    # special: gfhd wrong fund -> use watchlist T0 daily
    if name.startswith("广发港股创新药"):
        # neodata resolves to wrong fund; use watchlist embedded T0 yesterday_return
        daily0707 = wh.get("yesterday_return_pct")  # -2.56 from 支付宝 T0
        fv = {"nav": None, "daily_0707": daily0707, "ytd": None, "date": "2026-07-07(T0截图)"}
        # proxy for 07-08
        proxy = sectors_0708.get("港股创新药")
        # alpha vs hkdrug benchmark 07-07
        if benchmarks_0707.get("港股创新药") is not None and daily0707 is not None:
            alpha = round(daily0707 - benchmarks_0707["港股创新药"], 2)
    funds.append({
        "name": name, "short": short, "sector": sector, "proxy_sector": proxy_sector,
        "mv": mv, "weight_pct": wpct, "risk_flag": risk, "status": status,
        "nav": fv.get("nav"), "nav_date": fv.get("date"),
        "daily_0707": daily0707, "ytd_pct": fv.get("ytd"),
        "proxy_0708": proxy, "benchmark_0707": bm, "alpha": alpha,
        "ranking": extract_ranking("f3_"+short),
        "top10": extract_top10("f3_"+short),
        "industry": extract_industry("f3_"+short),
    })

# ---------- Account est return 07-08 (sector proxy weighted) ----------
total_mv = sum(f["mv"] for f in funds if f["mv"])
acct_ret = 0.0
for f in funds:
    if f["mv"] and f["proxy_0708"] is not None:
        acct_ret += (f["mv"]/total_mv) * f["proxy_0708"]
acct_ret = round(acct_ret, 3)
acct_pnl = round(total_mv * acct_ret/100, 2)

# ---------- News ----------
news = []
for key in ["news_semicon","news_hkdrug","news_market"]:
    for g in doc_groups(key):
        for doc in g.get("docList", [])[:6]:
            t = doc.get("title") or doc.get("summary","")
            if t: news.append(t[:120])

consolidated = {
    "date": DATE,
    "indices": indices,
    "sectors_0708": sectors_0708,
    "benchmarks_0707": benchmarks_0707,
    "funds": funds,
    "account_est_return_0708_pct": acct_ret,
    "account_est_pnl_0708": acct_pnl,
    "total_mv": round(total_mv,2),
    "news": news,
}
json.dump(consolidated, open(os.path.join(BASE,"consolidated_2026-07-08.json"),"w",encoding="utf-8"), ensure_ascii=False, indent=2)

# Print summary
print("=== INDICES ===")
for k,v in indices.items(): print(k, v)
print("=== SECTORS 07-08 ===")
for k,v in sectors_0708.items(): print(" ",k,v)
print("=== BENCH 07-07 ===")
for k,v in benchmarks_0707.items(): print(" ",k,v)
print("=== FUNDS ===")
for f in funds:
    print(f["name"][:14], "| mv",f["mv"],"| w%",f["weight_pct"],"| d0707",f["daily_0707"],"| ytd",f["ytd_pct"],
          "| proxy08",f["proxy_0708"],"| bm07",f["benchmark_0707"],"| alpha",f["alpha"],
          "| rank",(f["ranking"] or {}).get("rank"),"/",(f["ranking"] or {}).get("total"),
          "| top10",len(f["top10"]),"| risk",f["risk_flag"],"| st",f["status"])
print("ACCT est 07-08 return%%: ", acct_ret, " pnl ~", acct_pnl, " total_mv", round(total_mv,2))
print("news items:", len(news))
print("saved consolidated_2026-07-08.json")
