#!/usr/bin/env python3
"""
同花顺投资账本 → 日报系统持仓数据库 同步脚本
─────────────────────────────────────────
读取 data/汇总持仓.xlsx → 合并到 config/watchlist.json

规则:
  - xlsx 提供: 关联板块穿透、单位成本、历史收益(1/3/6/12月)
  - watchlist 提供: 最新成交金额(手动调整优先) + 策略配置(止盈线/调仓框架/尾盘窗口)
  - 策略层永不被 xlsx 覆盖
  - 金额差异 <5% → xlsx自动更新; 差异 >5% → 保留watchlist(认为手动调整过)

用法:
  python scripts/sync_from_xlsx.py                         # 默认 data/汇总持仓.xlsx
  python scripts/sync_from_xlsx.py C:/path/to/汇总持仓.xlsx  # 指定文件
"""

import json, os, sys
from datetime import date, datetime

try:
    import openpyxl
except ImportError:
    print("[FATAL] openpyxl not installed. Run: pip install openpyxl")
    sys.exit(1)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WATCHLIST = os.path.join(ROOT, "config", "watchlist.json")
PORTFOLIO = os.path.join(ROOT, "config", "portfolio.json")
BUILD_WL = os.path.join(ROOT, "scripts", "build_watchlist.py")
XLSX_DEFAULT = os.path.join(ROOT, "data", "汇总持仓.xlsx")


# ─── 加载 ─────────────────────────────────────────────
def load_xlsx(path):
    """读取同花顺 汇总持仓.xlsx → [{code, name, market_value, ...}]"""
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb["持仓数据"]
    rows = list(ws.iter_rows(values_only=True))
    if len(rows) < 2:
        return []

    headers = [str(h).strip() if h else "" for h in rows[0]]
    funds = []
    for row in rows[1:]:
        code = row[0]
        if not code:
            continue
        code_str = str(int(code)).zfill(6) if isinstance(code, (int, float)) else str(code).strip()
        if code_str == "汇总":
            continue

        entry = {"_code_raw": code_str}
        for i, h in enumerate(headers):
            if i >= len(row):
                break
            entry[h] = row[i]
        funds.append(entry)
    return funds


def load_watchlist():
    with open(WATCHLIST, "r", encoding="utf-8") as f:
        return json.load(f)


# ─── 映射 ─────────────────────────────────────────────
UNWANTED = {
    "中证转债",           # 债基→转债指数, 不是权益板块
    "广发中证香港创新药(QDII-ETF)",  # ETF名, 不是板块
    "嘉实中证主要消费ETF",          # ETF名
    "广发纳指100ETF",               # ETF名
}


def sector_from_xlsx(xlsx_sector):
    """清洗同花顺关联板块: 去ETF名, 只留真正的行业/主题板块"""
    if not xlsx_sector:
        return ""
    s = str(xlsx_sector).strip()
    if s in UNWANTED:
        return ""
    return s


def map_xlsx_enrichment(xlsx_entry):
    """提取同花顺xlsx中的可合并字段"""
    def _f(key, default=0.0):
        v = xlsx_entry.get(key)
        if v is None:
            return default
        try:
            return round(float(v), 4)
        except (ValueError, TypeError):
            return default

    raw_sector = str(xlsx_entry.get("关联板块", "")).strip()
    return {
        "xlsx_sector": raw_sector,
        "sector_from_xlsx": sector_from_xlsx(raw_sector),
        "cost_basis": _f("单位成本"),
        "breakeven_pct": _f("回本涨幅"),
        "shares": _f("持有数量"),
        "xlsx_days_held": int(_f("持仓天数") or 0),
        "return_1m": _f("近1月涨幅") if xlsx_entry.get("近1月涨幅") is not None else None,
        "return_3m": _f("近3月涨幅") if xlsx_entry.get("近3月涨幅") is not None else None,
        "return_6m": _f("近6月涨幅") if xlsx_entry.get("近6月涨幅") is not None else None,
        "return_1y": _f("近1年涨幅") if xlsx_entry.get("近1年涨幅") is not None else None,
        "xlsx_market_value": _f("持有金额"),
        "xlsx_hold_return_amount": _f("持有盈亏"),
        "xlsx_hold_return_pct": _f("持有盈亏率"),
    }


def recalc_weights(holdings):
    total = sum(h.get("market_value", 0) for h in holdings
                if h.get("status") not in ("cleared",))
    for h in holdings:
        mv = h.get("market_value", 0)
        h["weight_pct"] = round(mv / total * 100 if total > 0 else 0, 2)


# ─── 合并 ─────────────────────────────────────────────
def sync(xlsx_path=None):
    xlsx_path = xlsx_path or XLSX_DEFAULT
    if not os.path.exists(xlsx_path):
        print(f"[ERROR] xlsx not found: {xlsx_path}")
        print(f"        请从同花顺投资账本导出 → 放置到此路径")
        return None

    wl = load_watchlist()
    xlsx_funds = load_xlsx(xlsx_path)
    print(f"  同花顺 xlsx: {len(xlsx_funds)} 只基金")

    # 代码索引 + name fallback (兼容旧 watchlist 无 code 字段)
    xlsx_by_code = {f["_code_raw"]: f for f in xlsx_funds}
    xlsx_by_name = {str(f.get("名称", "")).strip(): f for f in xlsx_funds}

    wl_holdings = wl.get("holdings", [])
    wl_codes = {h.get("code", "") for h in wl_holdings}

    def _find_xlsx_entry(h):
        """按 code 优先匹配，再 fallback 到 name (截取前10字防全称/简称差异)"""
        code = h.get("code", "")
        if code and code in xlsx_by_code:
            return xlsx_by_code[code]
        name = h.get("name", "").strip()
        if name in xlsx_by_name:
            return xlsx_by_name[name]
        # 模糊匹配: 前10字
        for n, f in xlsx_by_name.items():
            if n[:10] == name[:10] and len(name) > 4:
                return f
        return None

    updated, enriched, added = 0, 0, 0
    today_str = date.today().isoformat()

    # ── 1) 更新已有持仓 ──
    for h in wl_holdings:
        xlsx_entry = _find_xlsx_entry(h)
        if not xlsx_entry:
            continue

        xe = map_xlsx_enrichment(xlsx_entry)
        code = h.get("code", "") or xlsx_entry.get("_code_raw", "")

        # 金额差异检测
        wl_mv = h.get("market_value", 0)
        xl_mv = xe["xlsx_market_value"]
        pct_diff = abs(wl_mv - xl_mv) / max(wl_mv, 0.01) if wl_mv > 0 else 1
        use_xlsx_amounts = pct_diff < 0.05  # <5% → 自动同步

        # 板块穿透 (同花顺 → sector / related_index)
        if xe["sector_from_xlsx"] and (not h.get("sector") or h.get("sector") in ("未知", "混合")):
            h["sector"] = xe["sector_from_xlsx"]

        # 保留 xlsx 原始 sector 作为穿透依据
        h["xlsx_sector"] = xe["xlsx_sector"]
        h["cost_basis"] = max(h.get("cost_basis", 0) or 0, xe["cost_basis"])
        h["breakeven_pct"] = xe["breakeven_pct"] or h.get("breakeven_pct", 0)
        if xe["shares"] > 0:
            h["shares"] = xe["shares"]
        h["xlsx_days_held"] = xe["xlsx_days_held"]

        # 历史收益覆盖
        for k in ("return_1m", "return_3m", "return_6m", "return_1y"):
            if xe[k] is not None:
                h[k] = xe[k]

        # 金额: 仅小差异时自动更新
        if use_xlsx_amounts:
            h["market_value"] = xe["xlsx_market_value"]
            h["hold_return_amount"] = xe["xlsx_hold_return_amount"]
            h["hold_return_pct"] = xe["xlsx_hold_return_pct"]
            updated += 1
        else:
            if pct_diff > 0.1:
                print(f"  [SKIP] {h.get('name','?')} 金额差 {pct_diff:.0%} — 保留 watchlist")
            enriched += 1

        h["xlsx_synced"] = today_str

    # ── 2) 新增基金 ──
    matched_names = set()
    for h in wl_holdings:
        xe = _find_xlsx_entry(h)
        if xe:
            matched_names.add(str(xe.get("名称", "")).strip())
            matched_names.add(xe.get("_code_raw", ""))

    new_funds = []
    for code, xlsx_entry in xlsx_by_code.items():
        if code in wl_codes or code in matched_names:
            continue
        name = str(xlsx_entry.get("名称", "")).strip()
        if name in matched_names:
            continue
        xe = map_xlsx_enrichment(xlsx_entry)
        name = str(xlsx_entry.get("名称", "")).strip()
        new_fund = {
            "code": code,
            "name": name,
            "market_value": xe["xlsx_market_value"],
            "yesterday_pnl": 0,
            "hold_return_amount": xe["xlsx_hold_return_amount"],
            "hold_return_pct": xe["xlsx_hold_return_pct"],
            "weight_pct": 0,
            "status": "active" if xe["xlsx_market_value"] > 1 else "pending_confirm",
            "sector": xe["sector_from_xlsx"] or "未知",
            "related_index": xe["sector_from_xlsx"] or "",
            "underlying_index": "",
            "shares": xe["shares"],
            "cost_basis": xe["cost_basis"],
            "breakeven_pct": xe["breakeven_pct"],
            "xlsx_sector": xe["xlsx_sector"],
            "xlsx_days_held": xe["xlsx_days_held"],
            "return_1m": xe["return_1m"],
            "return_3m": xe["return_3m"],
            "return_6m": xe["return_6m"],
            "return_1y": xe["return_1y"],
            "risk_flag": "",
            "profit_lock": {},
            "rebalance_role": "观察仓（同花顺新导入）",
            "xlsx_synced": today_str,
            "source": "xlsx_import",
        }
        new_funds.append(new_fund)
        added += 1
        print(f"  [NEW] {name} ({code}) — 金额 {new_fund['market_value']:.2f}")

    if new_funds:
        wl_holdings.extend(new_funds)

    # ── 3) 标记已清仓 ──
    for h in wl_holdings:
        if _find_xlsx_entry(h):
            continue
        if h.get("status") != "active":
            continue
        if not h.get("risk_flag") or "已不在" not in h.get("risk_flag", ""):
            h["risk_flag"] = (h.get("risk_flag", "") + "; 已不在同花顺最新导出中").strip("; ")

    # ── 4) 重算 ──
    recalc_weights(wl_holdings)
    total_mv = sum(h.get("market_value", 0) for h in wl_holdings
                   if h.get("status") not in ("cleared", "pending_confirm"))
    total_pnl = sum(h.get("hold_return_amount", 0) for h in wl_holdings
                    if h.get("status") not in ("cleared",))

    # 半导体集中度
    semi_keywords = ("半导体", "芯片", "PCB", "国家大基金", "存储", "通信设备")
    semi_mv = sum(h.get("market_value", 0) for h in wl_holdings
                  if h.get("status") not in ("cleared",)
                  and any(kw in (h.get("sector", "") or "") for kw in semi_keywords))

    # ── 5) 更新 meta ──
    wl["meta"] = wl.get("meta", {})
    wl["meta"]["synced_from_xlsx"] = today_str
    wl["meta"]["source_xlsx_basename"] = os.path.basename(xlsx_path)
    wl["meta"]["source_xlsx_path"] = os.path.abspath(xlsx_path)
    wl["meta"]["fund_count"] = len([h for h in wl_holdings if h.get("status") == "active"])

    # 保留现金(同花顺xlsx不含现金, watchlist 自己维护)
    cash = wl.get("meta", {}).get("cash", 0)
    grand_total = total_mv + cash

    wl["position_summary"] = wl.get("position_summary", {})
    wl["position_summary"]["total_asset"] = round(grand_total, 2)
    wl["position_summary"]["total_cash"] = round(cash, 2)
    wl["position_summary"]["total_hold_return"] = round(total_pnl, 2)
    wl["position_summary"]["semiconductor_exposure_pct"] = round(
        semi_mv / grand_total * 100 if grand_total > 0 else 0, 2
    )

    # ── 6) 写回 watchlist.json（后向兼容）──
    with open(WATCHLIST, "w", encoding="utf-8") as f:
        json.dump(wl, f, ensure_ascii=False, indent=2)

    # ── 7) 同步写 portfolio.json（权威持仓真源）──
    portfolio = json.load(open(PORTFOLIO, encoding="utf-8")) if os.path.exists(PORTFOLIO) else {}
    portfolio["holdings"] = wl.get("holdings", [])
    portfolio["meta"] = wl.get("meta", portfolio.get("meta", {}))
    portfolio["position_summary"] = wl.get("position_summary", {})
    with open(PORTFOLIO, "w", encoding="utf-8") as f:
        json.dump(portfolio, f, ensure_ascii=False, indent=2)

    # ── 8) 重建 watchlist.json（保与拆分 config 一致）──
    if os.path.exists(BUILD_WL):
        import subprocess
        subprocess.run(["python", BUILD_WL], cwd=ROOT, check=False)

    print(f"\n  ✓ 同步完成 → {WATCHLIST}")
    print(f"    更新 {updated} 只(金额自动同步) | 富化 {enriched} 只(保留手动金额)")
    print(f"    新增 {added} 只 | 总持仓 {len(wl_holdings)} 只")
    print(f"    总资产 {grand_total:.2f}(含现金{cash:.2f}) | 半导体集中度 {wl['position_summary']['semiconductor_exposure_pct']:.1f}%")
    return wl


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="同花顺xlsx → watchlist 同步")
    p.add_argument("xlsx", nargs="?", default=None,
                   help="同花顺汇总持仓.xlsx 路径 (默认 data/汇总持仓.xlsx)")
    p.add_argument("--force-amounts", action="store_true",
                   help="强制用xlsx金额覆盖watchlist (慎用)")
    args = p.parse_args()
    sync(args.xlsx)
