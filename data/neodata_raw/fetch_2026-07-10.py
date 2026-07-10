# -*- coding: utf-8 -*-
"""Batch fetch neodata for daily market report 2026-07-10.
Saves raw JSON per query to neodata_raw/ for offline parsing.
"""
import subprocess, json, os, concurrent.futures, datetime

BASE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(BASE, "neodata_raw")
os.makedirs(RAW, exist_ok=True)
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
    ("恒生科技", "hstech", "HSTECH"),
]

JOBS = []
for nm, code, neo in INDICES:
    q = (f"{nm}({neo})今日实时行情：最新价、涨跌幅、成交额、量比、今开、最高、最低、"
         f"主力净流入、以及MA5/MA10/MA20/MA60均线值、5日涨跌幅、20日涨跌幅")
    JOBS.append((f"snap_{code}", q, False))

SENT = {
    "breadth": "今日沪深两市A股上涨家数、下跌家数、平盘家数各是多少",
    "limit": "今日A股涨停家数、跌停家数各是多少",
    "mainflow": "今日A股全市场主力资金净流入总额（亿元）",
    "margin": "最新一期两市融资余额及较上一期环比变化",
    "vix": "CBOE VIX恐慌指数最新数值",
    "erp": "沪深300指数最新市盈率TTM 与 中国10年期国债收益率最新值",
    "north": "今日北向资金（陆股通）净买入额多少亿元",
    "amount": "今日沪深两市总成交额多少亿元",
}
for k, q in SENT.items():
    JOBS.append((f"sent_{k}", q, False))

def run(job):
    name, q, api = job
    out = os.path.join(RAW, f"{name}.json")
    cmd = [PY, QPY, "--query", q]
    if api:
        cmd += ["--data-type", "api"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        txt = r.stdout
        # strip a leading/embedded literal that query.py may print
        open(out, "w", encoding="utf-8").write(txt)
        return name, "ok", len(txt)
    except Exception as e:
        return name, "err", str(e)

if __name__ == "__main__":
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as ex:
        futs = [ex.submit(run, j) for j in JOBS]
        for f in concurrent.futures.as_completed(futs):
            results.append(f.result())
    for n, s, info in sorted(results):
        print(n, s, info)
    print("DONE", datetime.datetime.now().isoformat())
