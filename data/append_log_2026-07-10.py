# -*- coding: utf-8 -*-
import json, os
DATA = r"C:/Users/LEGION/Nutstore/1/daily-report/data"
DATE = "2026-07-10"
interim = json.load(open(os.path.join(DATA, "_interim_2026-07-10.json"), encoding="utf-8"))["D"]
log = json.load(open(os.path.join(DATA, "index-kline-log.json"), encoding="utf-8"))

# per-index prediction (next_day/t+2/t+3)
PRED = {
 "sh000001": ("偏空","-0.3~1%","均线下方弱势震荡","中","收复MA5(4007)转强"),
 "sz399001": ("偏空","-0.5~1.5%","跌破全部均线","中","收复MA20(15687)"),
 "sz399006": ("偏空","-0.5~2%","MA60(3938)支撑","中","收复MA60转强"),
 "sh000016": ("震荡","±0.8%","守住全部均线抗跌","中高","失守MA60(2943)转弱"),
 "sh000300": ("震荡","±1%","等MA20(4887)方向","中","站稳4887确认"),
 "sh000905": ("偏弱","-0.5~1%","下MA5/20","中","收复MA20(8669)"),
 "sh000688": ("震荡","-1~2%","测MA5(2053)支撑","中","跌破MA5转弱/守MA20(1979)偏多"),
 "bj899050": ("偏空","-0.5~1%","持续弱势","中","跌破1203前低加速"),
 "hstech": ("中性","±1%","港股创新药对冲","中","美股扰动→下行"),
}
name_cn = {"sh000001":"上证指数","sz399001":"深证成指","sz399006":"创业板指","sh000016":"上证50",
           "sh000300":"沪深300","sh000905":"中证500","sh000688":"科创50","bj899050":"北证50","hstech":"恒生科技"}

recs = []
for code, v in interim.items():
    s = v["s"]; sc = v["sc"]
    nd,t2,t3,conf,trig = PRED.get(code,("中性","±1%","等待方向","中",""))
    recs.append({
        "date": DATE, "index": code, "name": name_cn[code],
        "close": s["close"], "change_pct": s["chg"], "amount_yi": s.get("amount"),
        "main_inflow_yi": s.get("mainflow"),
        "ma": {k: s["ma"].get(k) for k in ("ma5","ma10","ma20","ma60")},
        "dimensions": {"trend": sc["trend"], "volume_price": sc["vp"], "pattern": sc["shp"], "main_force": sc["mfsc"]},
        "bias": sc["tend"], "bias_score": sc["score"],
        "predictions": {
            "next_day": {"dir": nd, "range": t2, "logic": t3, "conf": conf, "trigger": trig},
            "t+2": {"dir": t2.split("~")[0].replace("±","").replace("-","").replace("+","") and "震荡" or "震荡", "range": "±1.5%", "logic": "消化获利盘", "conf": "中", "trigger": ""},
            "t+3": {"dir": t3.split("(")[0].strip(), "range": "±1.5%", "logic": "等待新催化", "conf": "低", "trigger": ""},
        },
    })

# de-dup: remove existing records for DATE
log["records"] = [r for r in log["records"] if r.get("date") != DATE]
log["records"].extend(recs)
log["last_update"] = f"{DATE}T15:30:00+08:00"
log["fear_greed_index"] = 50
json.dump(log, open(os.path.join(DATA, "index-kline-log.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("appended", len(recs), "records; total", len(log["records"]))
