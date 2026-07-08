import subprocess, json, os, sys

PY = "C:/Users/LEGION/.workbuddy/binaries/python/versions/3.13.12/python.exe"
SCRIPT = "E:/新建文件夹/WorkBuddy/resources/app.asar.unpacked/resources/builtin-skills/neodata-financial-search/scripts/query.py"
BASE = "C:/Users/LEGION/Nutstore/1/daily-report/data"
OUT = os.path.join(BASE, "neodata_raw")
os.makedirs(OUT, exist_ok=True)

FUNDS = [
    ("dfaic", "东方人工智能主题混合C"),
    ("dfa", "东方阿尔法科技优选混合C"),
    ("gfhd", "广发港股创新药ETF联接(QDII)C"),
    ("yw", "永赢先锋半导体智选混合C"),
    ("fgcoal", "富国中证煤炭指数C"),
    ("jsxf", "嘉实中证主要消费ETF发起联接C"),
    ("ctic", "财通集成电路产业股票C"),
    ("ctcz", "财通成长优选混合C"),
    ("thcpo", "天弘中证全指通信设备指数C"),
    ("gfnas", "广发纳斯达克100ETF联接"),
]

QUERIES = []
for short, name in FUNDS:
    QUERIES.append((f"f3_{short}", f"{name} 同类排名 十大重仓股 十大持仓"))
    QUERIES.append((f"f2_{short}", f"{name} 最新基金规模 资产净值 总份额"))

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
            status = "OK api=%d" % len(api)
        except Exception:
            status = "PARSE_FAIL len=%d" % len(out)
        print("[%s] %s" % (key, status), flush=True)
    except Exception as e:
        print("[%s] ERROR %s" % (key, e), flush=True)

if __name__ == "__main__":
    for k, q in QUERIES:
        run(k, q)
    print("DONE2")
