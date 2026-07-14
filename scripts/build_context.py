import json, os
from datetime import datetime

today = "2026-07-14"
outdir = "C:/Users/LEGION/Nutstore/1/daily-report/data/cache"

# Watchlist summary
with open("C:/Users/LEGION/Nutstore/1/daily-report/config/watchlist.json") as f:
    wl = json.load(f)

meta = wl["meta"]
m = meta["strategy"]
holdings = wl["holdings"]
active = [h for h in holdings if h["status"] == "active"]
pos_summary = wl["position_summary"]

watchlist_summary = {
    "account_total_asset": meta["account_total_asset"],
    "cash": meta["cash"], "cash_pct": meta["cash_pct"],
    "total_hold_return": pos_summary["total_hold_return"],
    "total_hold_return_pct": meta["account_hold_return_pct"],
    "active_funds": len(active),
    "hard_constraints": {
        "stop_loss_pct": m["stop_loss_pct"], "take_profit_pct": m["take_profit_pct"],
        "max_single_position_pct": m["max_single_position_pct"],
        "target_total_position_pct": m["target_total_position_pct"],
        "principal": m["principal"]
    },
    "top3_concentration_pct": pos_summary["top3_concentration_pct"],
    "semiconductor_exposure_pct": pos_summary["semiconductor_exposure_pct"],
    "risk_alerts": pos_summary["risk_alerts"][:3],
    "snapshot_date": meta["snapshot_date"]
}

# Strategy
with open("C:/Users/LEGION/Nutstore/1/daily-report/config/strategy.json") as f:
    st = json.load(f)

# Sentiment 7d
with open("C:/Users/LEGION/Nutstore/1/daily-report/data/sentiment-log.json") as f:
    sl = json.load(f)

sent_7d = []
for rec in sl["records"][-7:]:
    sent_7d.append({"date": rec["date"], "fear_greed_index": rec["fear_greed_index"], "level": rec["level"]})

sent_trend = {
    "records": sent_7d,
    "latest_index": sent_7d[-1]["fear_greed_index"] if sent_7d else None,
    "latest_level": sent_7d[-1]["level"] if sent_7d else None,
    "trend": [r["fear_greed_index"] for r in sent_7d]
}

# Index data
bdt = [10222.17, 10613.29, 11377.82, 10375.77, 10173.43, 10032.91, 10012.71, 10210.22, 11265.14, 11350.28,
       10974.86, 10270.97, 10100.71, 9778.24, 9292.98, 9317.01, 9120.09, 8815.78, 8246.04, 8266.78,
       7882.71, 7989.50, 7684.95, 7562.95, 7106.73, 7349.00, 7642.74, 7442.31, 7252.12, 7096.93,
       7532.89, 7980.18, 7883.42, 8236.28, 8424.28, 7889.62, 7820.06, 8180.88, 7714.82, 7321.53,
       7271.14, 7050.16, 7291.26, 7058.18, 6916.08, 6507.92, 6718.69, 6592.57, 6368.23, 6056.25,
       6090.51, 6083.44, 5739.19, 5638.56, 5689.72, 5531.39, 5640.11, 5591.78, 5585.34, 5510.38,
       5559.16, 5406.74, 5452.46, 5392.22, 5332.36, 4970.81, 4911.79, 4928.68, 5118.02, 5000.25,
       5190.20, 5088.47, 4999.82, 5104.02, 4973.12, 4874.70, 5100.40, 5131.26, 5251.56, 5143.60,
       5272.89, 5221.43, 5270.75, 5349.26, 5427.94, 5306.76, 5443.54, 5498.52, 5389.34, 5425.51,
       5719.89, 5802.24, 5924.03, 5838.85, 5636.65, 5635.74, 5592.95, 5557.74, 5623.51, 5603.74]

rgz = [3106.14, 3211.93, 3299.58, 3103.16, 3073.18, 3104.34, 3131.33, 3114.10, 3355.22, 3422.48,
       3238.77, 3209.26, 3363.55, 3252.02, 3162.01, 3283.66, 3224.22, 3064.06, 2975.73, 2976.52,
       2798.25, 2799.09, 2887.74, 2953.30, 2855.71, 2944.46, 3054.94, 3079.82, 2992.49, 2908.35,
       2961.68, 3072.14, 3007.85, 3070.21, 3078.94, 2954.32, 2883.76, 2992.65, 2987.16, 2939.35,
       2919.12, 2973.94, 3034.90, 2926.78, 2896.40, 2818.27, 2854.15, 2775.03, 2671.75, 2584.89,
       2558.86, 2618.17, 2605.85, 2656.69, 2677.59, 2596.53, 2631.51, 2605.87, 2556.11, 2473.60,
       2493.71, 2439.28, 2432.27, 2369.23, 2389.05, 2218.17, 2194.56, 2176.30, 2257.00, 2170.57,
       2220.16, 2228.13, 2232.76, 2297.51, 2241.87, 2203.06, 2299.22, 2317.15, 2352.07, 2265.69,
       2329.38, 2304.14, 2352.21, 2393.96, 2434.96, 2389.80, 2377.56, 2359.94, 2308.20, 2348.56,
       2450.70, 2485.35, 2470.49, 2413.54, 2415.25, 2442.45, 2453.45, 2406.96, 2443.88, 2412.70]

cyb = [3723.52, 3842.73, 4018.17, 3845.35, 3911.91, 3948.86, 4019.93, 4017.27, 4260.72, 4342.71,
       4216.70, 4194.21, 4371.99, 4251.42, 4192.19, 4359.39, 4252.39, 4167.05, 4102.94, 4033.53,
       3830.35, 3811.25, 3854.79, 3961.75, 3811.79, 3957.94, 4088.88, 4122.99, 4055.87, 3950.94,
       4037.95, 4125.07, 4045.77, 4043.07, 4021.16, 3938.50, 3829.78, 3921.79, 3908.44, 3914.88,
       3929.06, 3951.14, 4038.33, 3934.88, 3928.97, 3796.13, 3833.06, 3778.16, 3677.15, 3687.17,
       3596.71, 3648.79, 3667.79, 3720.25, 3752.76, 3688.94, 3677.58, 3678.29, 3626.27, 3514.96,
       3558.53, 3476.44, 3448.79, 3323.30, 3347.61, 3160.82, 3149.60, 3172.65, 3247.52, 3184.95,
       3273.36, 3295.88, 3272.49, 3316.97, 3251.55, 3235.22, 3352.10, 3309.10, 3346.37, 3280.06,
       3357.02, 3310.28, 3317.52, 3349.53, 3306.14, 3208.58, 3229.30, 3216.94, 3164.37, 3209.48,
       3294.16, 3310.30, 3344.98, 3354.82, 3308.26, 3275.96, 3328.06, 3284.74, 3320.54, 3332.77]

def ma(data, n):
    if len(data) < n:
        return round(sum(data) / len(data), 2)
    return round(sum(data[:n]) / n, 2)

def change_pct(current, prev):
    if prev and prev != 0:
        return round((current - prev) / prev * 100, 2)
    return None

index_baseline = {
    "中证半导": {
        "code": "cs931865", "last_close": bdt[0], "prev_close": bdt[1],
        "change_pct": change_pct(bdt[0], bdt[1]),
        "MA20": ma(bdt, 20), "MA60": ma(bdt, 60),
        "above_MA20": bdt[0] > ma(bdt, 20), "above_MA60": bdt[0] > ma(bdt, 60)
    },
    "人工智能": {
        "code": "cs931071", "last_close": rgz[0], "prev_close": rgz[1],
        "change_pct": change_pct(rgz[0], rgz[1]),
        "MA20": ma(rgz, 20), "MA60": ma(rgz, 60),
        "above_MA20": rgz[0] > ma(rgz, 20), "above_MA60": rgz[0] > ma(rgz, 60)
    },
    "创业板指": {
        "code": "sz399006", "last_close": cyb[0], "prev_close": cyb[1],
        "change_pct": change_pct(cyb[0], cyb[1]),
        "MA20": ma(cyb, 20), "MA60": ma(cyb, 60),
        "above_MA20": cyb[0] > ma(cyb, 20), "above_MA60": cyb[0] > ma(cyb, 60)
    }
}

context = {
    "watchlist": watchlist_summary,
    "strategy": { "trading": st["trading"], "risk_controls": st["risk_controls"] },
    "sentiment_7d": sent_trend,
    "index_baseline": index_baseline,
    "update_ts": datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00"),
    "data_as_of": "2026-07-13 close (last trading day)"
}

os.makedirs(outdir, exist_ok=True)
outpath = os.path.join(outdir, f"context_{today}.json")
with open(outpath, "w", encoding="utf-8") as f:
    json.dump(context, f, ensure_ascii=False, indent=2)

size = os.path.getsize(outpath)
print(f"上下文预加载完成 -> data/cache/context_{today}.json ({size}字节)")
