# -*- coding: utf-8 -*-
"""
refresh_db.py  —  数据刷新流水线
==================================
执行时机：每个自动化任务运行时的第 0 步。
纯 Python 可执行的部分：akshare + 情绪计算 + watchlist 同步。
MCP 依赖部分（sector_spot/global_market/northbound）由 agent 后续用工具补充。

用法：
  python refresh_db.py all          # 全量刷新（akshare+情绪+watchlist）
  python refresh_db.py index        # 仅刷新指数
  python refresh_db.py watchlist    # 仅同步持仓到 DB
"""

import sys
import datetime
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

from market_db import MarketDB
db = MarketDB()


# ================================================================
#  数据源：akshare → index_spot（新浪源，最快最稳）
# ================================================================

def refresh_akshare():
    """akshare → index_spot (新浪源，独立于 westock/neodata)"""
    try:
        import akshare as ak
        import pandas as pd
    except ImportError:
        print("[refresh] akshare 未安装，跳过")
        return 0

    try:
        df = ak.stock_zh_index_spot_sina()
        targets = {
            "sh000001": "上证指数", "sz399001": "深证成指", "sz399006": "创业板指",
            "sh000016": "上证50",   "sh000300": "沪深300",  "sh000905": "中证500",
            "sh000688": "科创50",   "bj899050": "北证50",
        }
        count = 0
        for code, name in targets.items():
            row = df[df["代码"] == code]
            if row.empty:
                continue
            r = row.iloc[0]
            price = float(r["最新价"]) if pd.notna(r["最新价"]) else None
            chg = float(r["涨跌幅"]) if pd.notna(r["涨跌幅"]) else None
            amt = float(r["涨跌额"]) if pd.notna(r["涨跌额"]) else None
            db.upsert("index_spot", {
                "code": code, "name": name, "price": price,
                "change_pct": chg, "change_amt": amt,
                "open": float(r["今开"]) if pd.notna(r["今开"]) else None,
                "high": float(r["最高"]) if pd.notna(r["最高"]) else None,
                "low": float(r["最低"]) if pd.notna(r["最低"]) else None,
                "volume": float(r["成交量"]) if pd.notna(r["成交量"]) else None,
                "amount": float(r["成交额"]) if pd.notna(r["成交额"]) else None,
                "updated_at": datetime.datetime.now().isoformat(),
            }, conflict_col="code")
            count += 1
        db.mark_freshness("akshare", "index_spot", count)
        print(f"[refresh] akshare: {count} 条指数写入 ✅")
        return count
    except Exception as e:
        db.mark_freshness("akshare", "index_spot", 0, "error", str(e)[:100])
        print(f"[refresh] akshare ERROR: {e}")
        return 0


# ================================================================
#  计算：情绪因子（从指数涨跌推理）
# ================================================================

def refresh_sentiment():
    """从指数涨跌估算恐惧贪婪指数，写入 sentiment 表。"""
    today = datetime.date.today().isoformat()
    index_data = db.get_index_spot()
    breadth = db.get_breadth(today)

    down_count = 0
    total_count = 0
    for idx in index_data:
        chg = idx.get("change_pct")
        if chg is not None:
            total_count += 1
            if chg < -1:
                down_count += 1

    if total_count > 0:
        down_ratio = down_count / total_count
        if down_ratio > 0.6:
            fg = max(10, 30 - int(down_ratio * 30))
        elif down_ratio < 0.2:
            fg = min(90, 60 + int((1 - down_ratio) * 30))
        else:
            fg = 50
    else:
        fg = 50

    if fg <= 20:        level = "极度恐惧"
    elif fg <= 40:      level = "恐惧"
    elif fg <= 60:      level = "中性"
    elif fg <= 80:      level = "贪婪"
    else:               level = "极度贪婪"

    db.upsert("sentiment", {
        "date": today, "fear_greed": fg, "level": level,
        "note": f"从{total_count}个指数涨跌幅自动估算",
        "updated_at": datetime.datetime.now().isoformat(),
    }, conflict_col="date")
    db.mark_freshness("db_calc", "sentiment", 1)
    print(f"[refresh] sentiment: FG={fg} · {level} ✅")


# ================================================================
#  数据源：akshare → index_ohlc（指数近60日OHLC，新浪源）
# ================================================================

def refresh_index_ohlc():
    """从 akshare 获取各指数近60日OHLC，写入 index_ohlc 表。"""
    try:
        import akshare as ak
        import pandas as pd
    except ImportError:
        print("[refresh] akshare 未安装，跳过 index_ohlc")
        return 0

    index_codes = {
        "sh000001": "上证指数", "sz399001": "深证成指", "sz399006": "创业板指",
        "sh000016": "上证50",   "sh000300": "沪深300",  "sh000905": "中证500",
        "sh000688": "科创50",
    }
    # 追加持仓关联指数
    from market_db import MarketDB
    local_db = MarketDB()
    fund_rows = local_db.query("SELECT DISTINCT fund_id FROM fund_nav")
    # 基金代码到指数的映射（可扩展）
    extra_codes = {
        "931865": "中证半导", "931071": "中证人工智能", "512480": "半导体ETF",
    }
    for code, name in extra_codes.items():
        if code not in index_codes:
            index_codes[code] = name

    count = 0
    for code, name in index_codes.items():
        try:
            df = ak.stock_zh_index_daily(symbol=code)
            if df.empty:
                print(f"  ⚠ {code}({name}) 无数据，跳过")
                continue
            # 取近60日
            recent = df.tail(60)
            rows = []
            for _, r in recent.iterrows():
                # 计算涨跌幅
                prev_close = None
                rows.append({
                    "code": code,
                    "date": str(r["date"]),
                    "open": float(r["open"]) if pd.notna(r["open"]) else None,
                    "high": float(r["high"]) if pd.notna(r["high"]) else None,
                    "low": float(r["low"]) if pd.notna(r["low"]) else None,
                    "close": float(r["close"]) if pd.notna(r["close"]) else None,
                    "volume": float(r["volume"]) if pd.notna(r["volume"]) else None,
                })
            db.upsert_many("index_ohlc", rows, conflict_col=None)
            count += len(rows)
            print(f"  {code}({name}): {len(rows)} 日")
        except Exception as e:
            print(f"  ⚠ {code} ERROR: {e}")

    db.mark_freshness("akshare", "index_ohlc", count)
    print(f"[refresh] index_ohlc: {count} 条 ✅")
    return count


# ================================================================
#  计算：板块行情估算（从指数推导 + sector_mapping）
# ================================================================

def refresh_sector_estimate():
    """从指数涨跌和 sector_mapping 估算板块行情。
    精确数据需要 agent 通过 finance-dcths MCP 补充。"""
    try:
        mapping = json.load(open(os.path.join(os.path.dirname(BASE), "config", "sector_mapping.json"), encoding="utf-8"))
    except Exception:
        mapping = {}

    # 按已存在的 index_spot 数据估计
    index_data = db.get_index_spot()
    today = datetime.date.today().isoformat()

    # 从持仓关联指数倒推板块
    fund_rows = db.query("SELECT DISTINCT fund_id FROM fund_nav")
    if not fund_rows:
        print("[refresh] sector_estimate: fund_nav 为空，跳过")
        return 0

    # 用指数涨跌幅填充 sector_spot（placeholder，精确数据需 MCP）
    semic_idx = db.get_index_by_code("sh000688")  # 科创50近似半导体
    if semic_idx:
        db.upsert("sector_spot", {
            "code": "semic", "name": "半导体(估算)",
            "change_pct": semic_idx.get("change_pct"),
            "net_inflow": None,
            "updated_at": datetime.datetime.now().isoformat(),
        }, conflict_col="code")

    db.mark_freshness("db_calc", "sector_spot", 1, "ok", "估算值，精确数据需 finance-dcths MCP")
    print(f"[refresh] sector_estimate: 1条占位 ✅")
    return 1


# ================================================================
#  同步：watchlist.json → fund_nav 表
# ================================================================

def refresh_watchlist():
    """从 watchlist.json 同步持仓快照到 fund_nav 表。
    让所有自动化任务通过 DB 读取持仓数据，无需重复读 JSON。"""
    wl_path = os.path.join(os.path.dirname(BASE), "config", "watchlist.json")
    if not os.path.exists(wl_path):
        print("[refresh] watchlist.json 不存在，跳过")
        return 0

    try:
        wl = json.load(open(wl_path, encoding="utf-8"))
    except Exception as e:
        print(f"[refresh] watchlist 读取失败: {e}")
        return 0

    today = datetime.date.today().isoformat()
    holdings = wl.get("holdings", [])
    meta = wl.get("meta", {})
    strategy = wl.get("strategy", {})

    count = 0
    for h in holdings:
        name = h.get("name", "")
        fund_id = h.get("code") or name.replace(" ", "_")
        mv = h.get("market_value")
        ret_pct = h.get("hold_return_pct")
        wp = h.get("weight_pct")
        # 用持仓市值 + 持有收益推算净值
        gain = mv - mv / (1 + ret_pct/100) if mv and ret_pct else None
        nav = mv if mv else None

        db.upsert("fund_nav", {
            "fund_id": fund_id, "date": today,
            "nav": nav, "day_return": h.get("yesterday_return_pct"),
            "fund_scale": mv,
        }, conflict_col=None)  # no conflict since (fund_id, date) is PK
        count += 1

        # 写入 index_ohlc 关联指数（如果有 related_index）
        related = h.get("related_index")
        if related:
            # 用简单的标记：把持仓关联关系存入 data_freshness 的 note
            pass

    db.mark_freshness("watchlist", "fund_nav", count)
    print(f"[refresh] watchlist: {count} 只持仓写入 fund_nav ✅")
    return count


# ================================================================
#  全量刷新
# ================================================================

def refresh_all():
    """全量刷新。自动化任务第 0 步调用此函数。"""
    refresh_akshare()
    refresh_sentiment()
    refresh_watchlist()
    refresh_index_ohlc()
    refresh_sector_estimate()
    print(f"[refresh] === 全量刷新完成 @{datetime.datetime.now().isoformat()[:19]} ===")
    print(f"[refresh] agent 后续需补充: sector_spot(精确·finance-dcths) + global_market(jin10) + northbound/breadth/capital_flow(neodata)")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    cmds = {
        "index": refresh_akshare,
        "sentiment": refresh_sentiment,
        "watchlist": refresh_watchlist,
        "ohlc": refresh_index_ohlc,
    }
    if cmd in cmds:
        cmds[cmd]()
    else:
        refresh_all()
