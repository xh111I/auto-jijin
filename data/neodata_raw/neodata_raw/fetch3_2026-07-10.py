# -*- coding: utf-8 -*-
import subprocess, os, concurrent.futures, datetime
BASE = os.path.dirname(os.path.abspath(__file__))
QPY = r"E:/新建文件夹/WorkBuddy/resources/app.asar.unpacked/resources/builtin-skills/neodata-financial-search/scripts/query.py"
PY = r"C:/Users/LEGION/.workbuddy/binaries/python/versions/3.13.12/python.exe"
JOBS = [
    ("s3_breadth", "今日A股收盘，沪深两市（含北交所）共有多少只股票上涨、多少只下跌、多少只平盘，给出具体家数", False),
    ("s3_limit", "今日A股收盘共有多少只股票涨停、多少只跌停，给出具体家数", False),
    ("s3_hs300pe", "沪深300指数最新市盈率TTM是多少", False),
    ("s3_vix", "VIX恐慌指数最新收盘数值是多少", False),
    ("s3_north", "今日北向资金（陆股通）净买入还是净卖出，金额多少亿元", False),
]
def run(job):
    name, q, api = job
    out = os.path.join(BASE, f"{name}.json")
    cmd = [PY, QPY, "--query", q]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        open(out, "w", encoding="utf-8").write(r.stdout)
        return name, "ok", len(r.stdout)
    except Exception as e:
        return name, "err", str(e)
if __name__ == "__main__":
    res = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
        for f in concurrent.futures.as_completed([ex.submit(run, j) for j in JOBS]):
            res.append(f.result())
    for n, s, i in sorted(res): print(n, s, i)
    print("DONE", datetime.datetime.now().isoformat())
