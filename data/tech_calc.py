# -*- coding: utf-8 -*-
"""
tech_calc.py — 大盘·板块 技术面增强 · 量化计算（纯 Python，零依赖）

读取  market_raw_ohlc_<DATE>.json
  （由『大盘·板块·日K研判』(15:30) 自动化经 neodata 并行拉取的九大指数 + 板块 近 250 交易日日线 OHLC）
  - indices : [{code,name,ohlc}]   →  by_code   （按 code 索引，渲染模块⑦指数日K）
  - sectors : [{name,ohlc}]        →  by_sector（按 name 索引，渲染板块日K模块）
计算并输出  market_tech_<DATE>.json  ，供 make_market_html.py 渲染。

计算项（与用户落地方案一一对应）：
  ① 均线系统 MA5/10/20/60/120/250 + 乖离率 + 排列判定 + 年线专项（牛熊/斜率/距年线%）
  ② 三级支撑压力：均线(S/R) / 历史高低点(强) / 枢轴点 Pivot(S1/S2/R1/R2) / 整数关口
  ③ K线形态：单K（大阳/大阴/十字星/长上影/长下影/光头光脚/跳空） + 近3日组合
  ④ 辅助：量比 / 近5·20·60日涨跌幅 / MACD金叉死叉 / KDJ超买超卖
  ⑤ 特殊价位：豹子号 / 对子号 / 整数关口
  ⑥ 固定4句话结论模板（数据填充，禁止自由发挥）

用法：
  python tech_calc.py <DATE>
  python tech_calc.py            # 取最新的 market_raw_ohlc_*.json
"""
import json
import os
import sys
import glob
import datetime

BASE = os.path.dirname(os.path.abspath(__file__))


# ---------- 基础指标 ----------
def sma(vals, n):
    """滚动简单均值，预热期返回 None。"""
    out = [None] * len(vals)
    for i in range(n - 1, len(vals)):
        out[i] = round(sum(vals[i - n + 1:i + 1]) / n, 3)
    return out


def _ema(vals, n):
    """指数移动平均，前 n-1 个为 None，第 n 个以 SMA 播种。"""
    if len(vals) < n:
        return [None] * len(vals)
    k = 2.0 / (n + 1)
    out = [None] * len(vals)
    seed = sum(vals[:n]) / n
    out[n - 1] = seed
    prev = seed
    for i in range(n, len(vals)):
        prev = vals[i] * k + prev * (1 - k)
        out[i] = round(prev, 4)
    return out


def calc_ma(ohlc):
    """ohlc: 每行 [date, open, high, low, close, vol]"""
    closes = [r[4] for r in ohlc]
    mas = {p: sma(closes, p) for p in (5, 10, 20, 60, 120, 250)}
    n = len(closes)
    c = closes[-1]
    m5, m20, m250 = mas[5][-1], mas[20][-1], mas[250][-1]
    bias5 = round((c - m5) / m5 * 100, 2) if m5 else None
    bias20 = round((c - m20) / m20 * 100, 2) if m20 else None
    lv = [mas[5][-1], mas[10][-1], mas[20][-1], mas[60][-1], mas[250][-1]]
    # 跳过尚未形成的长周期均线(如上市/采样<250日时 MA250 为 None)
    present = [v for v in lv if v is not None]
    if len(present) >= 2 and all(present[i] >= present[i + 1] for i in range(len(present) - 1)):
        pat = "多头排列"
    elif len(present) >= 2 and all(present[i] <= present[i + 1] for i in range(len(present) - 1)):
        pat = "空头排列"
    else:
        pat = "均线纠缠"
    if m250 is None:
        ystat, yslope, ydist = "年线不足(上市<250日)", "—", None
    else:
        yslope_v = m250 - (mas[250][-20] if mas[250][-20] is not None else m250)
        ystat = "年线上方(牛市格局)" if c > m250 else "年线下方(熊市格局)"
        yslope = "向上" if yslope_v > 0 else ("向下" if yslope_v < 0 else "走平")
        ydist = round((c - m250) / m250 * 100, 2)
    return mas, {"bias5": bias5, "bias20": bias20, "ma_pattern": pat,
                 "year": {"status": ystat, "slope": yslope, "distance": ydist}}


def calc_sr(ohlc, index_type="broad"):
    closes = [r[4] for r in ohlc]
    highs = [r[2] for r in ohlc]
    lows = [r[1] for r in ohlc]
    c = closes[-1]
    mas = {p: sma(closes, p) for p in (5, 20, 60, 250)}
    sup, res = [], []
    for name, p in (("MA5", 5), ("MA20", 20), ("MA60", 60), ("MA250", 250)):
        v = mas[p][-1]
        if v is None:
            continue
        if v < c:
            sup.append({"price": round(v, 2), "type": name, "strength": "中"})
        else:
            res.append({"price": round(v, 2), "type": name, "strength": "中"})
    h20 = max(highs[-20:])
    l20 = min(lows[-20:])
    sup.append({"price": round(l20, 2), "type": "20日低点", "strength": "强"})
    res.append({"price": round(h20, 2), "type": "20日高点", "strength": "强"})
    ph, pl, pc = ohlc[-2][2], ohlc[-2][1], ohlc[-2][4]
    pivot = (ph + pl + pc) / 3.0
    s1 = 2 * pivot - ph
    r1 = 2 * pivot - pl
    s2 = pivot - (ph - pl)
    r2 = pivot + (ph - pl)
    sup += [{"price": round(s1, 2), "type": "Pivot S1", "strength": "中"},
            {"price": round(s2, 2), "type": "Pivot S2", "strength": "弱"}]
    res += [{"price": round(r1, 2), "type": "Pivot R1", "strength": "中"},
            {"price": round(r2, 2), "type": "Pivot R2", "strength": "弱"}]
    step = 100 if c >= 1000 else 50
    near = min(c % step, step - c % step)
    if 0 < near < c * 0.002:
        gate = round(c // step * step, 2)
        sup.append({"price": gate, "type": "整数关口", "strength": "弱"})
        res.append({"price": round(gate + step, 2), "type": "整数关口+", "strength": "弱"})
    sup.sort(key=lambda x: x["price"], reverse=True)   # 支撑由近及远
    res.sort(key=lambda x: x["price"])               # 压力由近及远
    return sup, res


def check_special(price):
    s = "%.2f" % price
    ip, dp = s.split(".")
    tags = []
    if dp[0] == dp[1]:
        tags.append("对子号")
    if len(ip) >= 3 and ip[-3] == ip[-2] == ip[-1] and dp[0] == dp[1]:
        tags.append("豹子号")
    step = 100 if len(ip) >= 4 else 50
    m = price % step
    if m < 0.2 or m > step - 0.2:
        tags.append("整数关口")
    return tags


def k_single(o, h, l, c):
    body = c - o
    rng = h - l
    if rng == 0:
        return "一字线"
    body_r = abs(body) / rng
    up = body > 0
    upper = h - max(o, c)
    lower = min(o, c) - l
    if body_r < 0.1:
        return "十字星"
    if up and body_r > 0.6:
        return "光头光脚大阳" if upper < rng * 0.1 else "大阳线"
    if (not up) and body_r > 0.6:
        return "光头光脚大阴" if lower < rng * 0.1 else "大阴线"
    if upper > rng * 0.5 and lower < rng * 0.2:
        return "长上影"
    if lower > rng * 0.5 and upper < rng * 0.2:
        return "长下影"
    return "阳线" if up else "阴线"


def k_combo(a, b, c):
    u = lambda x, y: x < y
    if u(a, b) and u(b, c):
        return "两连阳"
    if (not u(a, b)) and (not u(b, c)):
        return "两连阴"
    if (not u(a, b)) and u(b, c) and c > b and b < a:
        return "阳包阴"
    if u(a, b) and (not u(b, c)) and c < b and b > a:
        return "阴包阳"
    return "—"


def macd_state(closes):
    e12 = _ema(closes, 12)
    e26 = _ema(closes, 26)
    dif = [(a - b) if (a is not None and b is not None) else None
           for a, b in zip(e12, e26)]
    clean = [d for d in dif if d is not None]
    dea_full = _ema(clean, 9)
    dea = [None] * len(dif)
    j = 0
    for i in range(len(dif)):
        if dif[i] is not None:
            dea[i] = dea_full[j]
            j += 1
    a, b, cc, d = dif[-2], dif[-1], dea[-2], dea[-1]
    if None in (a, b, cc, d):
        return "—"
    if a < cc and b >= d:
        return "金叉"
    if a > cc and b <= d:
        return "死叉"
    return "—"


def kdj_state(highs, lows, closes):
    n = 9
    if len(closes) < n:
        return "—"
    K, D = 50.0, 50.0
    for i in range(len(closes) - n + 1, len(closes)):
        hh = max(highs[i:i + n])
        ll = min(lows[i:i + n])
        r = (closes[i] - ll) / (hh - ll) * 100 if hh != ll else 50.0
        K = K * 2 / 3 + r / 3
        D = D * 2 / 3 + K / 3
    if K >= 80:
        return "超买"
    if K <= 20:
        return "超卖"
    return "—"


def pct(a, b):
    return round((a - b) / b * 100, 2) if b else None


def build_tech(rec):
    """rec: {"code","name","ohlc":[[date,o,h,l,c,v],...]} → tech dict"""
    code = rec.get("code")
    name = rec.get("name", code)
    ohlc = rec.get("ohlc") or []
    if len(ohlc) < 6:
        return None
    closes = [r[4] for r in ohlc]
    highs = [r[2] for r in ohlc]
    lows = [r[1] for r in ohlc]
    vols = [r[5] for r in ohlc]
    dates = [r[0] for r in ohlc]

    mas, ma_info = calc_ma(ohlc)
    sup, res = calc_sr(ohlc)
    special = check_special(closes[-1])

    o, h, l, c = ohlc[-1][1], ohlc[-1][2], ohlc[-1][3], ohlc[-1][4]
    pat1 = k_single(o, h, l, c)
    pat3 = k_combo(closes[-3], closes[-2], closes[-1])
    macd = macd_state(closes)
    kdj = kdj_state(highs, lows, closes)
    vr = round(vols[-1] / (sum(vols[-5:]) / 5.0), 2) if vols[-1] else None
    chg5 = pct(c, closes[-6])
    chg20 = pct(c, closes[-21])
    chg60 = pct(c, closes[-61]) if len(closes) >= 61 else None

    # K线配色顺序：ECharts candlestick 需要 [open, close, low, high]
    candle = [[round(r[1], 3), round(r[4], 3), round(r[3], 3), round(r[2], 3)] for r in ohlc]

    # 距最近支撑/压力 %
    near_sup = next((s for s in sup if s["price"] < c), None)
    near_res = next((s for s in res if s["price"] > c), None)
    sup_pct = round((c - near_sup["price"]) / c * 100, 2) if near_sup else None
    res_pct = round((near_res["price"] - c) / c * 100, 2) if near_res else None

    # 4句话模板（数据填充，禁止自由发挥）
    y = ma_info["year"]
    trend_text = ("均线%s；%s（距年线%s%%），年线%s。"
                  % (ma_info["ma_pattern"], y["status"], y["distance"], y["slope"]))
    vol_judge = "放量" if (vr or 0) > 1.05 else ("缩量" if (vr or 0) < 0.95 else "平量")
    kline_text = ("当日%s；量比%s%s，%s；近5日%s%%、近20日%s%%。"
                  % (pat1, ("%.2f" % vr) if vr else "—", vol_judge,
                     ("MACD%s" % macd) if macd != "—" else "MACD中性",
                     chg5, chg20))
    if near_sup and near_res:
        price_text = ("现价距最近支撑%s(%s)约%s%%，距最近压力%s(%s)约%s%%；关注%s得失。"
                      % (near_sup["type"], near_sup["price"], sup_pct,
                         near_res["type"], near_res["price"], res_pct,
                         near_sup["type"] if abs(sup_pct or 99) <= abs(res_pct or 99) else near_res["type"]))
    elif near_sup:
        price_text = "现价距最近支撑%s(%s)约%s%%。" % (near_sup["type"], near_sup["price"], sup_pct)
    elif near_res:
        price_text = "现价距最近压力%s(%s)约%s%%。" % (near_res["type"], near_res["price"], res_pct)
    else:
        price_text = "暂无明显支撑/压力位。"

    td = (rec.get("tendency") or "").replace("临界", "")
    if "空" in td:
        op_ref = "关联持仓警惕，破位减仓；年线下行则控仓。"
    elif "多" in td:
        op_ref = "关联持仓可持有，回踩中期均线不破可分批加仓。"
    else:
        op_ref = "关联持仓持有观察，等方向确认。"

    return {
        "code": code,
        "name": name,
        "dates": dates,
        "candle": candle,
        "ma": {k: mas[k] for k in (5, 10, 20, 60, 120, 250)},
        "ma_pattern": ma_info["ma_pattern"],
        "bias5": ma_info["bias5"],
        "bias20": ma_info["bias20"],
        "year": y,
        "support": sup,
        "resistance": res,
        "pattern_single": pat1,
        "pattern_3d": pat3,
        "macd": macd,
        "kdj": kdj,
        "vol_ratio": vr,
        "chg5": chg5,
        "chg20": chg20,
        "chg60": chg60,
        "special": special,
        "trend_text": trend_text,
        "kline_text": kline_text,
        "price_text": price_text,
        "op_ref": op_ref,
    }


def load_raw(date):
    p = os.path.join(BASE, "market_raw_ohlc_%s.json" % date)
    if not os.path.exists(p):
        fs = sorted(glob.glob(os.path.join(BASE, "market_raw_ohlc_*.json")))
        if not fs:
            raise SystemExit("找不到 market_raw_ohlc_%s.json" % date)
        p = fs[-1]
        date = os.path.basename(p)[len("market_raw_ohlc_"):-5]
    return json.load(open(p, encoding="utf-8")), date


def main():
    if len(sys.argv) > 1:
        date = sys.argv[1]
    else:
        fs = sorted(glob.glob(os.path.join(BASE, "market_raw_ohlc_*.json")))
        if not fs:
            raise SystemExit("用法: tech_calc.py <YYYY-MM-DD>")
        date = os.path.basename(fs[-1])[len("market_raw_ohlc_"):-5]

    raw, date = load_raw(date)
    recs = raw.get("indices") or []
    by_code = {}
    for rec in recs:
        try:
            t = build_tech(rec)
        except Exception as e:
            sys.stderr.write("skip %s: %s\n" % (rec.get("code"), e))
            t = None
        if t:
            by_code[t["code"]] = t

    # 板块（按 name 索引，渲染板块日K模块）
    sec_recs = raw.get("sectors") or []
    by_sector = {}
    for rec in sec_recs:
        try:
            t = build_tech(rec)
        except Exception as e:
            sys.stderr.write("skip sector %s: %s\n" % (rec.get("name"), e))
            t = None
        if t:
            by_sector[t["name"]] = t

    out = {
        "date": date,
        "generated_at": (datetime.datetime.now()).strftime("%Y-%m-%d %H:%M"),
        "count": len(by_code) + len(by_sector),
        "by_code": by_code,
        "by_sector": by_sector,
    }
    op = os.path.join(BASE, "market_tech_%s.json" % date)
    json.dump(out, open(op, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("saved", op, "indices:", len(by_code), "sectors:", len(by_sector))


if __name__ == "__main__":
    main()
