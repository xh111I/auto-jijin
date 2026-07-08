import subprocess, json, os

PY = "C:/Users/LEGION/.workbuddy/binaries/python/versions/3.13.12/python.exe"
SCRIPT = "E:/新建文件夹/WorkBuddy/resources/app.asar.unpacked/resources/builtin-skills/neodata-financial-search/scripts/query.py"
OUT = "C:/Users/LEGION/Nutstore/1/daily-report/data/neodata_raw"

FUNDS = [
    ("dfaic", "东方人工智能主题混合C"),
    ("dfa", "东方阿尔法科技优选混合C"),
    ("yw", "永赢先锋半导体智选混合C"),
    ("fgcoal", "富国中证煤炭指数C"),
    ("jsxf", "嘉实中证主要消费ETF发起联接C"),
    ("ctic", "财通集成电路产业股票C"),
    ("ctcz", "财通成长优选混合C"),
    ("thcpo", "天弘中证全指通信设备指数C"),
    ("gfnas", "广发纳斯达克100ETF联接"),
]

def run(key, q):
    r = subprocess.run([PY, SCRIPT, "--query", q], capture_output=True, text=True, timeout=150, encoding="utf-8")
    open(os.path.join(OUT, key + ".json"), "w", encoding="utf-8").write(r.stdout)
    try:
        d = json.loads(r.stdout); api = (d.get("data") or {}).get("apiData", {}).get("apiRecall", [])
        print("[%s] api=%d" % (key, len(api)))
    except Exception as e:
        print("[%s] ERR %s" % (key, e))

for short, name in FUNDS:
    run("f3_" + short, "%s 基金规模 同类排名 十大重仓股" % name)
print("DONE4")
