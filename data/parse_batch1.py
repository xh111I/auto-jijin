import json, os, re

BASE = "C:/Users/LEGION/Nutstore/1/daily-report/data/neodata_raw"
OUT = "C:/Users/LEGION/Nutstore/1/daily-report/data"

def load(key):
    p = os.path.join(BASE, key + ".json")
    if not os.path.exists(p):
        return None
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return None

def api_blocks(key):
    d = load(key)
    if not d: return []
    return d.get("data", {}).get("apiData", {}).get("apiRecall", [])

def doc_blocks(key):
    d = load(key)
    if not d: return []
    dd = d.get("data", {}).get("docData", {})
    return dd.get("docRecall", []) if dd else []

def first_table_row(content):
    """Return dict of header->value for the first data row of the first markdown table."""
    if not content: return None
    lines = [l for l in content.split("\n") if l.strip().startswith("|")]
    if len(lines) < 3: return None
    header = [h.strip() for h in lines[0].strip().strip("|").split("|")]
    # line[1] is separator
    row = [v.strip() for v in lines[2].strip().strip("|").split("|")]
    if len(row) < len(header): return None
    return dict(zip(header, row))

def get_change_pct(content):
    r = first_table_row(content)
    if not r: return None
    for k in r:
        if "涨跌幅" in k or "增长率" in k:
            try: return float(r[k])
            except: pass
    return None

def get_close(content):
    r = first_table_row(content)
    if not r: return None
    for k in r:
        if "收盘价" in k or "最新价格" in k or "收盘点位" in k:
            try: return float(r[k])
            except: pass
    return None

consolidated = {"date": "2026-07-08", "source": "neodata-financial-search", "market": {}, "sectors": {}, "funds_nav": {}, "news": {}}

# ---- Indices ----
for key, name in [("mkt_sz","上证指数"),("mkt_cyb","创业板指"),("mkt_hs300","沪深300")]:
    blocks = api_blocks(key)
    if blocks:
        c = blocks[0].get("content","")
        r = first_table_row(c)
        consolidated["market"][name] = {"close": get_close(c), "change_pct": get_change_pct(c),
                                         "date": r.get("日期") if r else None}

# ---- Breadth ----
b = api_blocks("breadth")
if b:
    txt = b[0].get("content","")
    up = re.search(r"上涨[家数]*[：: ]*?(\d+)", txt)
    down = re.search(r"下跌[家数]*[：: ]*?(\d+)", txt)
    limit_up = re.search(r"涨停[家数]*[：: ]*?(\d+)", txt)
    limit_down = re.search(r"跌停[家数]*[：: ]*?(\d+)", txt)
    amt = re.search(r"成交额[：: ]*?([\d.]+)", txt)
    consolidated["market"]["breadth"] = {"raw": txt[:800]}
    # also try table
    r = first_table_row(txt)
    if r:
        consolidated["market"]["breadth"]["table"] = r

# ---- Northbound / mainflow / feargreed / rating ----
for key in ["northbound","mainflow","feargreed","rating"]:
    blocks = api_blocks(key)
    txt = blocks[0].get("content","") if blocks else ""
    consolidated["market"][key] = {"raw": txt[:1000]}

# ---- Sectors (07-08 change) ----
sector_map = [("sector_semicon","半导体"),("sector_ai","人工智能"),("sector_cpo","CPO通信"),
              ("sector_coal","煤炭"),("sector_consum","中证主要消费"),("sector_hkdrug","港股创新药"),
              ("sector_nasdaq","纳斯达克100")]
for key, name in sector_map:
    blocks = api_blocks(key)
    if blocks:
        c = blocks[0].get("content","")
        r = first_table_row(c)
        consolidated["sectors"][name] = {"change_pct": get_change_pct(c), "close": get_close(c),
                                          "date": r.get("日期") if r else None}

# ---- Funds NAV (latest) ----
fund_keys = [("fund_dfaic","东方人工智能主题混合C"),("fund_dfa","东方阿尔法科技优选混合C"),
             ("fund_gfhd","广发港股创新药ETF联接(QDII)C"),("fund_yw","永赢先锋半导体智选混合C"),
             ("fund_fgcoal","富国中证煤炭指数C"),("fund_jsxf","嘉实中证主要消费ETF发起联接C"),
             ("fund_ctic","财通集成电路产业股票C"),("fund_ctcz","财通成长优选混合C"),
             ("fund_thcpo","天弘中证全指通信设备指数C"),("fund_gfnas","广发纳斯达克100ETF联接")]
for key, name in fund_keys:
    blocks = api_blocks(key)
    if blocks:
        c = blocks[0].get("content","")
        r = first_table_row(c)
        if r:
            nav=None; chg=None; ytd=None; dt=None
            try: nav=float(r.get("单位净值(元)"))
            except: pass
            try: chg=float(r.get("复权单位净值日增长率"))
            except: pass
            try: ytd=float(r.get("今年以来回报率(%)"))
            except: pass
            dt=r.get("交易日期")
            consolidated["funds_nav"][name] = {"nav":nav,"daily_change_pct":chg,"ytd_pct":ytd,"date":dt}

with open(os.path.join(OUT,"consolidated_2026-07-08.json"),"w",encoding="utf-8") as f:
    json.dump(consolidated, f, ensure_ascii=False, indent=2)

# Print summary
print("=== INDICES ===")
for k,v in consolidated["market"].items():
    if isinstance(v,dict) and "close" in v:
        print(k, v.get("close"), v.get("change_pct"), v.get("date"))
print("=== SECTORS ===")
for k,v in consolidated["sectors"].items():
    print(k, v.get("change_pct"))
print("=== FUNDS NAV (latest) ===")
for k,v in consolidated["funds_nav"].items():
    print(k, "| nav",v.get("nav"),"| dchg%",v.get("daily_change_pct"),"| ytd%",v.get("ytd_pct"),"| date",v.get("date"))
print("=== BREADTH raw (first 300) ===")
print(consolidated["market"].get("breadth",{}).get("raw","")[:300])
print("saved consolidated_2026-07-08.json")
