import subprocess, json, os

PY = "C:/Users/LEGION/.workbuddy/binaries/python/versions/3.13.12/python.exe"
SCRIPT = "E:/新建文件夹/WorkBuddy/resources/app.asar.unpacked/resources/builtin-skills/neodata-financial-search/scripts/query.py"
OUT = "C:/Users/LEGION/Nutstore/1/daily-report/data/neodata_raw"

# benchmark 07-07 returns (same day as latest official fund NAV)
QUERIES = [
    ("bm_semicon_0707", "半导体板块 2026年7月7日 涨跌幅"),
    ("bm_ai_0707", "人工智能板块 2026年7月7日 涨跌幅"),
    ("bm_hkdrug_0707", "港股创新药 2026年7月7日 涨跌幅"),
    ("bm_coal_0707", "煤炭板块 2026年7月7日 涨跌幅"),
    ("bm_consum_0707", "中证主要消费 板块 2026年7月7日 涨跌幅"),
    ("bm_comm_0707", "通信设备 CPO 板块 2026年7月7日 涨跌幅"),
    ("bm_nasdaq_0707", "纳斯达克100 2026年7月7日 涨跌幅"),
    ("bm_sz_0707", "上证指数 2026年7月7日 涨跌幅"),
    ("bm_cyb_0707", "创业板指 2026年7月7日 涨跌幅"),
]

def run(key, q):
    r = subprocess.run([PY, SCRIPT, "--query", q], capture_output=True, text=True, timeout=150, encoding="utf-8")
    open(os.path.join(OUT, key + ".json"), "w", encoding="utf-8").write(r.stdout)
    try:
        d = json.loads(r.stdout); api = d.get("data",{}).get("apiData",{}).get("apiRecall",[])
        print("[%s] api=%d" % (key, len(api)))
    except Exception as e:
        print("[%s] ERR %s" % (key, e))

for k,q in QUERIES:
    run(k,q)
print("DONE3")
