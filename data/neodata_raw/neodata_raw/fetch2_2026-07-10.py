# -*- coding: utf-8 -*-
import subprocess, os, concurrent.futures, datetime

BASE = os.path.dirname(os.path.abspath(__file__))
RAW = BASE
QPY = r"E:/新建文件夹/WorkBuddy/resources/app.asar.unpacked/resources/builtin-skills/neodata-financial-search/scripts/query.py"
PY = r"C:/Users/LEGION/.workbuddy/binaries/python/versions/3.13.12/python.exe"

INDICES = [
    ("上证", "sh000001", "000001.SH"),
    ("深证", "sz399001", "399001.SZ"),
    ("创业板", "sz399006", "399006.SZ"),
    ("上证50", "sh000016", "000016.SH"),
    ("沪深300", "sh000300", "000300.SH"),
    ("中证500", "sh000905", "000905.SH"),
    ("科创50", "sh000688", "000688.SH"),
    ("北证50", "bj899050", "899050.BJ"),
    ("恒生科技", "hstech", "HSTECH.HK"),
]

JOBS = []
for nm, code, neo in INDICES:
    JOBS.append((f"mf_{code}", f"{nm}({neo})今日主力资金净流入多少亿元、超大单净流入", False))

SECTORS = {
    "semicon": "今日半导体板块涨跌幅与主力资金净流入（亿元）",
    "cpo": "今日CPO/通信设备板块涨跌幅与主力资金净流入（亿元）",
    "hkdrug": "今日港股创新药/创新药板块涨跌幅与主力资金净流入（亿元）",
    "finance": "今日证券/大金融板块涨跌幅与主力资金净流入（亿元）",
    "coal": "今日煤炭板块涨跌幅与主力资金净流入（亿元）",
    "consum": "今日主要消费/食品饮料板块涨跌幅与主力资金净流入（亿元）",
    "loser": "今日A股行业板块跌幅榜排名（前15名）",
    "ai": "今日人工智能板块涨跌幅与主力资金净流入（亿元）",
}
for k, q in SECTORS.items():
    JOBS.append((f"sec_{k}", q, False))

def run(job):
    name, q, api = job
    out = os.path.join(RAW, f"{name}.json")
    cmd = [PY, QPY, "--query", q]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        open(out, "w", encoding="utf-8").write(r.stdout)
        return name, "ok", len(r.stdout)
    except Exception as e:
        return name, "err", str(e)

if __name__ == "__main__":
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=17) as ex:
        futs = [ex.submit(run, j) for j in JOBS]
        for f in concurrent.futures.as_completed(futs):
            results.append(f.result())
    for n, s, info in sorted(results):
        print(n, s, info)
    print("DONE", datetime.datetime.now().isoformat())
