import subprocess, json, os, sys

PY = "C:/Users/LEGION/.workbuddy/binaries/python/versions/3.13.12/python.exe"
SCRIPT = "E:/新建文件夹/WorkBuddy/resources/app.asar.unpacked/resources/builtin-skills/neodata-financial-search/scripts/query.py"
BASE = "C:/Users/LEGION/Nutstore/1/daily-report/data"
OUT = os.path.join(BASE, "neodata_raw")
os.makedirs(OUT, exist_ok=True)

QUERIES = [
    ("mkt_sz", "上证指数 2026年7月8日 收盘点位 涨跌幅 成交额"),
    ("mkt_cyb", "创业板指 2026年7月8日 收盘点位 涨跌幅"),
    ("mkt_hs300", "沪深300 2026年7月8日 收盘点位 涨跌幅"),
    ("breadth", "2026年7月8日 A股 上涨家数 下跌家数 涨停家数 跌停家数 两市成交额"),
    ("northbound", "2026年7月8日 北向资金 净流入 净买入"),
    ("mainflow", "2026年7月8日 A股 主力资金 净流入 行业板块资金流向"),
    ("feargreed", "2026年7月8日 市场情绪 恐惧贪婪指数 A股"),
    ("rating", "今日 机构评级 上调 下调 研报 2026年7月8日"),
    ("sector_semicon", "半导体板块 2026年7月8日 涨跌幅 资金流向 收盘"),
    ("sector_ai", "人工智能板块 2026年7月8日 涨跌幅 资金流向"),
    ("sector_cpo", "CPO 通信设备板块 2026年7月8日 涨跌幅 资金流向"),
    ("sector_coal", "煤炭板块 2026年7月8日 涨跌幅 资金流向"),
    ("sector_consum", "中证主要消费 板块 2026年7月8日 涨跌幅 资金流向"),
    ("sector_hkdrug", "港股创新药 2026年7月8日 涨跌幅"),
    ("sector_nasdaq", "纳斯达克100 2026年7月8日 涨跌 美股"),
    ("fund_dfaic", "东方人工智能主题混合C 最新净值 日涨跌幅 规模 今年以来收益 同类排名 十大重仓股"),
    ("fund_dfa", "东方阿尔法科技优选混合C 最新净值 日涨跌幅 规模 今年以来收益 同类排名 十大重仓股"),
    ("fund_gfhd", "广发港股创新药ETF联接C 最新净值 日涨跌幅 规模 今年以来收益 同类排名 十大重仓股"),
    ("fund_yw", "永赢先锋半导体智选混合C 最新净值 日涨跌幅 规模 今年以来收益 同类排名 十大重仓股"),
    ("fund_fgcoal", "富国中证煤炭指数C 最新净值 日涨跌幅 规模 今年以来收益 同类排名 十大重仓股"),
    ("fund_jsxf", "嘉实中证主要消费ETF发起联接C 最新净值 日涨跌幅 规模 今年以来收益 同类排名 十大重仓股"),
    ("fund_ctic", "财通集成电路产业股票C 最新净值 日涨跌幅 规模 今年以来收益 同类排名 十大重仓股"),
    ("fund_ctcz", "财通成长优选混合C 最新净值 日涨跌幅 规模 今年以来收益 同类排名 十大重仓股"),
    ("fund_thcpo", "天弘中证全指通信设备指数C 最新净值 日涨跌幅 规模 今年以来收益 同类排名 十大重仓股"),
    ("fund_gfnas", "广发纳斯达克100ETF联接 最新净值 日涨跌幅 规模 今年以来收益 同类排名 十大重仓股"),
    ("news_semicon", "2026年7月8日 半导体 行业政策 重仓股动态 基金公告 分红 经理变更 限购"),
    ("news_hkdrug", "2026年7月8日 港股创新药 行业新闻 政策"),
    ("news_market", "2026年7月8日 A股 收评 市场总结 资金"),
]

def run(key, q):
    try:
        r = subprocess.run([PY, SCRIPT, "--query", q], capture_output=True, text=True, timeout=150, encoding="utf-8")
        out = r.stdout
        path = os.path.join(OUT, key + ".json")
        with open(path, "w", encoding="utf-8") as f:
            f.write(out)
        try:
            d = json.loads(out)
            api = d.get("data", {}).get("apiData", {}).get("apiRecall", [])
            docs = d.get("data", {}).get("docData", {})
            dl = docs.get("docRecall", []) if docs else []
            docs_n = sum(len(g.get("docList", [])) for g in dl)
            status = "OK api=%d docs=%d" % (len(api), docs_n)
        except Exception:
            status = "PARSE_FAIL len=%d" % len(out)
        print("[%s] %s" % (key, status), flush=True)
    except Exception as e:
        print("[%s] ERROR %s" % (key, e), flush=True)

if __name__ == "__main__":
    keys = sys.argv[1:] if len(sys.argv) > 1 else None
    for k, q in QUERIES:
        if keys and k not in keys:
            continue
        run(k, q)
    print("DONE")
