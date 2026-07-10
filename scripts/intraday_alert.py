#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
盘中预警触发式监控系统 v1
================================
核心能力：
  1. 特殊价位监控（对子号/豹子号/叠数/整数关口/顺子号/对称数）—— 纯字符串自动识别
  2. 极端资金情绪（涨跌家数比、涨停/跌停家数）
  3. 持仓主线异动（半导体/CPO 等 >3%）、硬止损临近、减仓线、中期趋势
  4. 三级优先级（高/中/低）+ 去重冷却（30分钟同类型 / 每价位每日1次）
  5. 时间线 HTML 页面（顶部悬浮栏 + 倒序时间线 + 分类筛选 + 折叠区）
  6. 仅在有新预警时 rebuild + publish，静默时零产出零推送

数据源：neodata-financial-search（唯一；失败则仅输出「数据源缺失」）

用法：
  python intraday_alert.py                 # 自动（时段闸门+检测+生成+发布）
  python intraday_alert.py --precompute    # 仅预计算（保留接口，当前 MA 关闭）
  python intraday_alert.py --force         # 忽略交易时段闸门（用于测试）
  python intraday_alert.py --selftest      # 特殊价位识别单测（不联网）
状态：data/reports/YYYY-MM-DD/alert_state.json
页面：data/reports/YYYY-MM-DD/盘中预警时间线-YYYYMMDD.html
"""
import os, sys, json, re, subprocess, shutil, datetime, argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG_PATH = os.path.join(ROOT, "config", "intraday_alert_config.json")
REPORT_DIR = os.path.join(ROOT, "data", "reports")

# ---------- 定位 neodata query.py ----------
def find_query_py():
    cands = [
        r"E:/新建文件夹/WorkBuddy/resources/app.asar.unpacked/resources/builtin-skills/neodata-financial-search/scripts/query.py",
        os.path.expanduser(r"~/.workbuddy/skills/neodata-financial-search/scripts/query.py"),
        os.path.join(ROOT, "scripts", "neodata_query.py"),
    ]
    for p in cands:
        if os.path.exists(p):
            return p
    # 兜底：全盘轻量搜索
    for base in [os.path.expanduser("~/.workbuddy"), r"E:/新建文件夹/WorkBuddy"]:
        if os.path.isdir(base):
            for root, _, files in os.walk(base):
                if "query.py" in files and "neodata" in root.lower():
                    return os.path.join(root, "query.py")
    return None

QUERY_PY = find_query_py()

# ---------- 北京时间 ----------
def beijing_now():
    # 优先：显式 Asia/Shanghai（需 tzdata，已安装到托管 Python）
    try:
        from zoneinfo import ZoneInfo
        return datetime.datetime.now(ZoneInfo("Asia/Shanghai"))
    except Exception:
        pass
    # 回退：用系统本地时区（当前沙箱时钟已配置为北京时间，避免盲加 8h 造成重复偏移）
    try:
        return datetime.datetime.now().astimezone()
    except Exception:
        return datetime.datetime.now()

# ---------- neodata 调用 ----------
def neodata_query(q):
    if not QUERY_PY:
        return None
    try:
        out = subprocess.run(
            [sys.executable, QUERY_PY, "--query", q],
            capture_output=True, text=True, timeout=90, cwd=ROOT,
        )
        txt = out.stdout.strip()
        if "TOKEN_EXPIRED" in txt or "TOKEN_MISSING" in txt:
            return None
        d = json.loads(txt)
        if d.get("code") == "200" and d.get("suc"):
            return d
    except Exception:
        return None
    return None

def extract_blocks(data):
    if not data:
        return []
    return data.get("data", {}).get("apiData", {}).get("apiRecall", [])

def _num(s):
    if s is None:
        return None
    s = s.replace(",", "").replace("，", "")
    try:
        return float(s)
    except Exception:
        return None

# 解析一个 apiRecall content 中的多个实体（NAME(代码:CODE)在...行情：...）
def parse_entities(content):
    if not content:
        return {}
    pat = re.compile(r"([\s\S]+?)\(代码[:：]([^)]+)\)")
    ms = list(pat.finditer(content))
    res = {}
    for i, m in enumerate(ms):
        # name 取「(代码:CODE)」紧前方那一段（按换行切最后一段），
        # 兼容多实体被拼接在同一块时前一实体的数据混入前缀的情况。
        # 注意：不可对 name 做 rstrip(")")，否则会误删名称中自带的括号（如「共封装光模块(CPO)」）。
        name = m.group(1).strip().split("\n")[-1].strip()
        code = m.group(2).strip()
        start = m.end()
        end = ms[i + 1].start() if i + 1 < len(ms) else len(content)
        seg = content[start:end]
        price = _num(re.search(r"最新价格[:：]?\s*([\d,]+\.?\d*)", seg).group(1)) \
            if re.search(r"最新价格[:：]?\s*([\d,]+\.?\d*)", seg) else None
        cm = re.search(r"当日涨跌幅[:：]?\s*([-\d.]+)\s*%", seg)
        chg = _num(cm.group(1)) if cm else None
        tm = re.search(r"数据更新时间[:：]?\s*([\d/]+\s*[\d:]+)", seg)
        d20 = re.search(r"20日涨跌幅[:：]?\s*([-\d.]+)\s*%", seg)
        d20v = _num(d20.group(1)) if d20 else None
        if price is not None:
            res[code] = {"name": name, "code": code, "price": price,
                         "change_pct": chg, "d20_pct": d20v,
                         "update": tm.group(1) if tm else None}
    return res

def parse_table_column(content, col_header_hint, idx):
    """从 markdown 表格提取某列数值（按表头匹配列索引）。"""
    if not content:
        return []
    lines = [l for l in content.split("\n") if l.strip().startswith("|")]
    if len(lines) < 3:
        return []
    header = [h.strip() for h in lines[0].strip().strip("|").split("|")]
    ci = None
    for i, h in enumerate(header):
        if col_header_hint in h:
            ci = i
            break
    if ci is None:
        ci = idx
    vals = []
    for l in lines[2:]:
        cells = [c.strip() for c in l.strip().strip("|").split("|")]
        if len(cells) <= ci:
            continue
        v = _num(cells[ci])
        if v is not None:
            vals.append(v)
    return vals

# ---------- 特殊价位识别（集中实现，便于复用与单测） ----------
def detect_gate(price, step):
    mod = price % step
    if mod < 0.2 or mod > step - 0.2:
        return int(round(price / step) * step)
    return None

def detect_straight(prices_str):
    dig = prices_str.replace(".", "")
    if len(dig) < 4:
        return False
    inc = all(dig[i + 1] == str(int(dig[i]) + 1) for i in range(len(dig) - 1))
    dec = all(dig[i + 1] == str(int(dig[i]) - 1) for i in range(len(dig) - 1))
    return inc or dec

def detect_symmetric(prices_str):
    dig = prices_str.replace(".", "")
    return len(dig) >= 4 and dig == dig[::-1]

def detect_special(price, cfg_sp, step):
    """返回 (价格字符串, [(type, kind, note), ...])"""
    s = f"{price:.2f}"
    ip, dp = s.split(".")
    alerts = []
    # 对子号
    if dp[0] == dp[1]:
        if dp in cfg_sp.get("pair_top", []):
            kind, note = "对子顶", "高位叠数对子，阶段性情绪见顶警示，注意冲高回落"
        elif dp in cfg_sp.get("pair_bottom", []):
            kind, note = "对子底", "低位叠数对子，阶段性支撑信号，关注短线反弹"
        else:
            kind, note = "对子号", "普通叠数对子，关注度一般"
        alerts.append(("对子号", kind, note))
    # 豹子号/叠数：整数位末三位相同
    if len(ip) >= 3 and ip[-3:] == ip[-1] * 3:
        alerts.append(("豹子号", "整数叠数", "整数位高度叠数，强心理关口，易引发变盘"))
    # 全位高度叠数：如 3333.33
    if ip and dp and set(ip) == {ip[0]} and set(dp) == {dp[0]} and ip[0] == dp[0]:
        alerts.append(("叠数", "全位叠数", "整数位与小数位全同，极强特殊数字"))
    # 整数关口
    gate = detect_gate(price, step)
    if gate is not None:
        alerts.append(("整数关口", f"{gate}点", "整数关口考验/突破，久攻不过则警惕变盘"))
    # 顺子号
    if detect_straight(s):
        alerts.append(("顺子号", s, "顺子号特殊数字，资金关注度提升"))
    # 对称数（回文，如 2888.82）
    if detect_symmetric(s):
        alerts.append(("对称数", s, "对称数特殊数字"))
    return s, alerts

# ---------- 状态 ----------
def state_path(date_str):
    d = os.path.join(REPORT_DIR, date_str)
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "alert_state.json")

def load_state(date_str):
    p = state_path(date_str)
    if os.path.exists(p):
        try:
            return json.load(open(p, encoding="utf-8"))
        except Exception:
            pass
    return {"date": date_str, "alerts": [], "seen": {}, "last_quotes": {}, "updated_at": None}

def save_state(st):
    p = state_path(st["date"])
    json.dump(st, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

# ---------- 主检测 ----------
def run_detection(cfg, st, now):
    wl = cfg["whitelist"]
    codes = [w["code"] for w in wl]
    names = {w["code"]: w["name"] for w in wl}
    # 1) 行情批量查询：对每个监控标的单独发「实时报价/板块实时行情」查询（并行），
    #    避免合并查询返回内容交错/拼接导致解析错位（已验证合并查询会把多标的拼进同一块）。
    from concurrent.futures import ThreadPoolExecutor, as_completed
    def _q_one(w):
        phrase = " 实时报价" if w.get("bar") else " 板块实时行情"
        d = neodata_query(w["name"] + phrase)
        if not d:
            return []
        return extract_blocks(d)
    data_all_blocks = []
    with ThreadPoolExecutor(max_workers=min(12, len(wl) or 1)) as ex:
        futs = [ex.submit(_q_one, w) for w in wl]
        for f in as_completed(futs):
            try:
                data_all_blocks.extend(f.result())
            except Exception:
                pass
    if not data_all_blocks:
        return None  # 数据源缺失
    ents = {}
    for b in data_all_blocks:
        ents.update(parse_entities(b.get("content", "")))
    # 广度（neodata 对「涨跌家数」常返回排行榜而非汇总，best-effort，取不到则跳过资金情绪）
    q_breadth = "今日A股两市的总成交量、成交额和涨跌家数"
    bdata = neodata_query(q_breadth)
    breadth = None
    if bdata:
        txt = " ".join(b.get("content", "") for b in extract_blocks(bdata))
        up = re.search(r"上涨[家数]*[：: ]*?(\d[\d,]*)", txt)
        dn = re.search(r"下跌[家数]*[：: ]*?(\d[\d,]*)", txt)
        lu = re.search(r"涨停[家数]*[：: ]*?(\d[\d,]*)", txt)
        ld = re.search(r"跌停[家数]*[：: ]*?(\d[\d,]*)", txt)
        if up and dn:
            u, d = _num(up.group(1)), _num(dn.group(1))
            breadth = {"up": int(u), "down": int(d),
                       "limit_up": int(_num(lu.group(1))) if lu else None,
                       "limit_down": int(_num(ld.group(1))) if ld else None}

    new_alerts = []
    seen = st.setdefault("seen", {})
    now_ts = now.timestamp()

    def cooled(key):
        last = seen.get(key)
        if last is None:
            return False
        return (now_ts - last) < cfg["cooldown_minutes"] * 60

    def commit(alert):
        key = f"{alert['code']}|{alert['type']}"
        if cooled(key):
            return
        # 特殊价位额外：每价位每日1次
        if alert["type"] in cfg["priority_categories"]["特殊价位"]:
            lvlkey = f"{alert['code']}|{alert['type']}|{alert.get('level')}"
            if lvlkey in seen:
                return
            seen[lvlkey] = now_ts
        seen[key] = now_ts
        alert["time"] = now.strftime("%H:%M:%S")
        new_alerts.append(alert)

    # 更新悬浮栏行情
    for code, e in ents.items():
        st["last_quotes"][code] = {"name": e["name"], "price": e["price"],
                                    "change_pct": e["change_pct"], "update": e.get("update")}

    # 2) 特殊价位 + 关键位 + 趋势
    for w in wl:
        code = w["code"]
        e = ents.get(code)
        if not e:
            continue
        price = e["price"]
        chg = e["change_pct"]
        s, specials = detect_special(price, cfg["special_price"], w.get("gate_step", 100))
        dp = s.split(".")[1]
        tb = cfg["special_price"].get("pair_top", []) + cfg["special_price"].get("pair_bottom", [])
        for (atype, kind, note) in specials:
            pri = "低" if (atype == "对子号" and dp not in tb) else "高"
            commit({"type": atype, "category": "特殊价位", "priority": pri,
                    "name": w["name"], "code": code, "price": price, "level": s,
                    "change_pct": chg,
                    "content": f"{w['name']} 触及 {s} 点（{kind}）",
                    "interpretation": note})
        # 关键位（减仓线等）
        for lvl in w.get("key_levels", []):
            if price <= lvl:
                commit({"type": "减仓预警", "category": "持仓预警", "priority": "高",
                        "name": w["name"], "code": code, "price": price, "level": s,
                        "change_pct": chg,
                        "content": f"{w['name']} 跌破关键位 {lvl} 点（{price:.2f}）",
                        "interpretation": "破关键减仓线，触发减仓预警"})
        # 中期趋势（20日涨跌幅）
        if e.get("d20_pct") is not None and e["d20_pct"] < -3:
            commit({"type": "中期趋势偏弱", "category": "板块异动", "priority": "中",
                    "name": w["name"], "code": code, "price": price, "level": s,
                    "change_pct": chg,
                    "content": f"{w['name']} 20日涨跌幅 {e['d20_pct']:.2f}%（中期趋势偏弱）",
                    "interpretation": "20日维度走弱，持仓主线需关注趋势延续性"})

    # 3) 资金情绪（广度）
    if breadth:
        up, dn = breadth["up"], breadth["down"]
        if up and dn:
            ratio = up / dn
            if ratio < 1 / cfg["breadth"]["extreme_ratio"]:
                commit({"type": "涨跌家数冰点", "category": "资金情绪", "priority": "高",
                        "name": "全市场", "code": "ALL", "price": None, "level": "breadth",
                        "change_pct": None,
                        "content": f"涨跌家数比 {up}:{dn}（≈1:{1/ratio:.1f}），普跌冰点",
                        "interpretation": "市场恐慌性普跌，警惕情绪极端"})
            elif ratio > cfg["breadth"]["extreme_ratio"]:
                commit({"type": "涨跌家数亢奋", "category": "资金情绪", "priority": "高",
                        "name": "全市场", "code": "ALL", "price": None, "level": "breadth",
                        "change_pct": None,
                        "content": f"涨跌家数比 {up}:{dn}（≈{ratio:.1f}:1），普涨亢奋",
                        "interpretation": "市场亢奋普涨，警惕追高"})
            elif ratio < 1 / cfg["breadth"]["medium_ratio"] or ratio > cfg["breadth"]["medium_ratio"]:
                commit({"type": "涨跌家数分化", "category": "资金情绪", "priority": "中",
                        "name": "全市场", "code": "ALL", "price": None, "level": "breadth",
                        "change_pct": None,
                        "content": f"涨跌家数比 {up}:{dn}（≈{ratio:.1f}:1），明显分化",
                        "interpretation": "多空分歧加大"})
        if breadth.get("limit_up") and breadth["limit_up"] > cfg["breadth"]["limit_up_high"]:
            commit({"type": "涨停潮", "category": "资金情绪", "priority": "高",
                    "name": "全市场", "code": "ALL", "price": None, "level": "breadth",
                    "change_pct": None,
                    "content": f"涨停家数 {breadth['limit_up']} 家（> {cfg['breadth']['limit_up_high']}）",
                    "interpretation": "涨停潮，情绪极度亢奋"})
        if breadth.get("limit_down") and breadth["limit_down"] > cfg["breadth"]["limit_down_high"]:
            commit({"type": "跌停潮", "category": "资金情绪", "priority": "高",
                    "name": "全市场", "code": "ALL", "price": None, "level": "breadth",
                    "change_pct": None,
                    "content": f"跌停家数 {breadth['limit_down']} 家（> {cfg['breadth']['limit_down_high']}）",
                    "interpretation": "跌停潮，踩踏风险升高"})

    # 4) 持仓主线异动 + 硬止损临近（持仓关联板块 >3% / 距 -8% 不足 1%）
    wl_by_name = {w["name"]: w for w in wl}
    for w in wl:
        if not w.get("holding"):
            continue
        e = ents.get(w["code"])
        if not e or e.get("change_pct") is None:
            continue
        if abs(e["change_pct"]) >= cfg["holding_move_threshold_pct"]:
            direction = "大幅拉升" if e["change_pct"] > 0 else "跳水"
            commit({"type": "持仓主线异动", "category": "持仓预警", "priority": "高",
                    "name": w["name"], "code": w["code"], "price": e["price"], "level": f"{e['price']:.2f}",
                    "change_pct": e["change_pct"],
                    "content": f"持仓主线 {w['name']} {direction} {e['change_pct']:+.2f}%",
                    "interpretation": "持仓核心赛道单时段大幅波动，关注趋势延续与仓位"})

    # 硬止损临近（持仓成本 + 今日板块估算）
    try:
        wl_json = json.load(open(os.path.join(ROOT, "config", "watchlist.json"), encoding="utf-8"))
        for h in wl_json.get("holdings", []):
            if h.get("status") not in ("active",) or (h.get("market_value") or 0) <= 0:
                continue
            sname = h.get("related_index") or h.get("sector")
            proxy = None
            for w in wl:
                if w["name"] == sname and w["code"] in ents:
                    proxy = ents[w["code"]].get("change_pct")
                    break
            if proxy is None:
                continue
            hold_ret = h.get("hold_return_pct") or 0
            est = hold_ret + proxy
            if est <= (cfg["stop_loss_pct"] + 1):  # 距 -8% 不足 1%
                commit({"type": "硬止损临近", "category": "持仓预警", "priority": "高",
                        "name": h.get("name"), "code": w.get("code", "FUND"), "price": None,
                        "level": "stop", "change_pct": proxy,
                        "content": f"{h.get('name')} 估算收益 {est:+.2f}%（距 -8% 硬止损不足 1%）",
                        "interpretation": "逼近硬止损线，需评估是否减仓/止损"})
    except Exception:
        pass

    return new_alerts, breadth

# ---------- HTML 生成 ----------
CSS = """
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif; background:#f4f6f9; color:#1f2733; padding-bottom:20px; }
.topbar { position:sticky; top:0; z-index:50; background:linear-gradient(135deg,#1f2a44,#2b3a5c); color:#fff; padding:10px 14px; box-shadow:0 2px 10px rgba(0,0,0,.2); }
.topbar .row1 { display:flex; align-items:center; gap:10px; flex-wrap:wrap; }
.topbar .tt { font-size:13px; font-weight:700; }
.topbar .quotes { display:flex; gap:12px; flex-wrap:wrap; }
.topbar .q { font-size:12px; }
.topbar .q b { font-weight:700; }
.topbar .up { color:#ff7875; } .topbar .dn { color:#95de64; }
.topbar .scroll { margin-top:8px; font-size:13px; background:rgba(255,77,79,.18); border-left:3px solid #ff4d4f; padding:6px 10px; border-radius:6px; animation:blink 1.4s infinite; }
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:.55} }
.topbar .meta { margin-top:6px; font-size:11px; opacity:.8; }
.filters { display:flex; gap:8px; padding:12px 14px 4px; flex-wrap:wrap; }
.filters button { border:none; background:#e9edf3; color:#4b5563; font-size:12px; padding:5px 12px; border-radius:16px; cursor:pointer; }
.filters button.on { background:#2b3a5c; color:#fff; }
.timeline { padding:6px 14px; }
.card { background:#fff; border-radius:12px; padding:12px 14px; margin:10px 0; box-shadow:0 1px 4px rgba(0,0,0,.06); border-left:4px solid #cbd2dc; }
.card.高 { border-left-color:#ff4d4f; background:#fff6f5; }
.card.中 { border-left-color:#faad14; background:#fffaef; }
.card.低 { border-left-color:#cbd2dc; }
.card .hd { display:flex; align-items:center; gap:8px; }
.card .pri { font-size:11px; font-weight:700; padding:1px 8px; border-radius:10px; }
.card .pri.高 { background:#ff4d4f; color:#fff; } .card .pri.中 { background:#faad14; color:#fff; } .card .pri.低 { background:#cbd2dc; color:#333; }
.card .cat { font-size:11px; color:#8a94a3; }
.card .tm { margin-left:auto; font-size:11px; color:#a3adba; }
.card .ct { font-size:14px; font-weight:600; margin:6px 0 3px; }
.card .it { font-size:12px; color:#5b6b7f; }
.collapse { margin:14px; }
.collapse summary { cursor:pointer; font-size:13px; color:#5b6b7f; font-weight:600; }
.collapse .body { font-size:12px; color:#6b7888; margin-top:8px; line-height:1.7; }
.kv { display:flex; justify-content:space-between; padding:4px 0; border-bottom:1px dashed #eef1f5; }
.foot { text-align:center; font-size:11px; color:#a3adba; padding:14px; }
"""

def gen_html(cfg, st, date_str, breadth):
    alerts = st.get("alerts", [])
    # 倒序（新在前）
    alerts_sorted = sorted(alerts, key=lambda a: a.get("time", ""), reverse=True)
    high_n = sum(1 for a in alerts if a["priority"] == "高")
    mid_n = sum(1 for a in alerts if a["priority"] == "中")
    # 悬浮栏行情
    bar_codes = [w["code"] for w in cfg["whitelist"] if w.get("bar")]
    quotes_html = ""
    for code in bar_codes:
        q = st["last_quotes"].get(code)
        if not q:
            continue
        cls = "up" if (q.get("change_pct") or 0) >= 0 else "dn"
        sign = "+" if (q.get("change_pct") or 0) >= 0 else ""
        quotes_html += f'<span class="q">{q["name"]} <b>{q["price"]:.2f}</b> <span class="{cls}">{sign}{q["change_pct"]:.2f}%</span></span>'
    # 最新高优先级滚动
    latest_high = next((a for a in alerts_sorted if a["priority"] == "高"), None)
    scroll_html = f'🔴 最新高优先级：{latest_high["content"]}' if latest_high else "✅ 当前无高优先级预警"
    update_t = st.get("updated_at") or ""
    # 时间线卡片
    cards = []
    for a in alerts_sorted:
        sign = (("+" if (a.get("change_pct") or 0) >= 0 else "") + f'{a["change_pct"]:.2f}%') if a.get("change_pct") is not None else ""
        cards.append(f"""
<div class="card {a['priority']}" data-cat="{a['category']}">
  <div class="hd"><span class="pri {a['priority']}">{a['priority']}</span><span class="cat">{a['category']} · {a['type']}</span><span class="tm">{a.get('time','')}</span></div>
  <div class="ct">{a['content']}</div>
  <div class="it">📌 {a.get('interpretation','')} {('｜ 当时涨跌 '+sign) if sign else ''}</div>
</div>""")
    cards_html = "\n".join(cards) if cards else '<div class="card 低"><div class="ct">今日暂无触发预警</div><div class="it">市场平稳 / 未触及任何监控阈值，系统静默运行中。</div></div>'
    breadth_html = ""
    if breadth:
        breadth_html = f"涨跌家数 {breadth.get('up')}:{breadth.get('down')} ｜ 涨停 {breadth.get('limit_up')} ｜ 跌停 {breadth.get('limit_down')}"
    cats = ["全部", "特殊价位", "资金情绪", "板块异动", "持仓预警"]
    cats_html = "".join(
        f'<button class="{"on" if c=="全部" else ""}" data-f="{"all" if c=="全部" else c}">{c}</button>'
        for c in cats)
    html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>盘中预警时间线 {date_str}</title>
<style>{CSS}</style></head><body>
<div class="topbar">
  <div class="row1"><span class="tt">📡 盘中预警时间线</span><span class="quotes">{quotes_html}</span></div>
  <div class="scroll">{scroll_html}</div>
  <div class="meta">更新时间 {update_t} ｜ 当日预警 {len(alerts)} 条（高 {high_n} / 中 {mid_n}）｜ 数据源 NeoData</div>
</div>
<div class="filters">{cats_html}</div>
<div class="timeline">{cards_html}</div>
<details class="collapse"><summary>⚙️ 监控规则 / 阈值 / 数据源</summary>
<div class="body">
  <div class="kv"><span>巡检频率</span><span>每 10 分钟（交易日 09:30–14:55，午休跳过）</span></div>
  <div class="kv"><span>特殊价位</span><span>对子号 / 豹子号 / 叠数 / 整数关口(指数100·板块50) / 顺子 / 对称</span></div>
  <div class="kv"><span>资金情绪</span><span>涨跌家数比 &lt;1:3 或 &gt;3:1 高；&gt;2:1 中 ｜ 涨停&gt;200 / 跌停&gt;50 高</span></div>
  <div class="kv"><span>持仓主线</span><span>关联板块单时段 &gt;±3% 高 ｜ 距 -8% 硬止损不足 1% 高 ｜ 破减仓线 高</span></div>
  <div class="kv"><span>去重冷却</span><span>同指数同类型 30 分钟内不重复；特殊价位每价位每日仅 1 次</span></div>
  <div class="kv"><span>广度快照</span><span>{breadth_html or '（本次未取到）'}</span></div>
  <div class="kv"><span>数据源</span><span>NeoData Financial Search（唯一；失败则中止本轮）</span></div>
  <div class="kv"><span>说明</span><span>场外基金无盘中实时净值，持仓以关联板块指数作估值代理，含跟踪误差。</span></div>
</div></details>
<div class="foot">⚠️ 本监控仅供参考，不构成投资建议。市场有风险，投资需谨慎。<br>每日基金自动报告系统 · 盘中预警 · {date_str}</div>
<script>
const btns=document.querySelectorAll('.filters button');
btns.forEach(b=>b.onclick=()=>{{
  btns.forEach(x=>x.classList.remove('on')); b.classList.add('on');
  const f=b.dataset.f;
  document.querySelectorAll('.card').forEach(c=>{{
    c.style.display=(f==='all'||c.dataset.cat===f)?'':'none';
  }});
}});
</script>
</body></html>"""
    return html

# ---------- 发布 ----------
def publish():
    try:
        subprocess.run(["bash", "publish.sh"], cwd=ROOT, capture_output=True, text=True, timeout=180)
        return True
    except Exception:
        return False

# ---------- 主流程 ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="忽略时段闸门（测试用）")
    ap.add_argument("--no-publish", action="store_true", help="仅生成不发布（测试用）")
    ap.add_argument("--precompute", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        sp = {"pair_top": ["66","77","88","99"], "pair_bottom": ["00","11","22"], "neutral_pair": ["33","44","55"]}
        cases = [("3938.88","对子号"),("4000.00","豹子号"),("3333.33","叠数"),
                 ("3456.78","顺子号"),("2888.82","对称数"),("3999.12","豹子号"),("1234.56","顺子号")]
        ok = True
        for p, exp in cases:
            res = detect_special(float(p), sp, 100)[1]
            types = [t[0] for t in res]
            flag = "OK" if exp in types else "FAIL"
            if flag == "FAIL":
                ok = False
            print(f"  {p}: {types}  [{flag}]")
        print("SELFTEST", "PASS" if ok else "FAIL")
        return

    try:
        cfg = json.load(open(CFG_PATH, encoding="utf-8"))
    except Exception as e:
        print(f"配置读取失败：{e}")
        return

    now = beijing_now()
    date_str = now.strftime("%Y-%m-%d")
    st = load_state(date_str)

    if args.precompute:
        st["precomputed"] = True
        save_state(st)
        print(f"预计算完成（当前 MA 关闭，仅标记）：{date_str}")
        return

    # 时段闸门
    hm = now.hour * 60 + now.minute
    open_hm = 9 * 60 + 30
    close_hm = 14 * 60 + 55
    lunch_s = 11 * 60 + 30
    lunch_e = 13 * 60
    in_window = (open_hm <= hm <= close_hm) and not (lunch_s < hm < lunch_e)
    if not args.force and not in_window:
        print("非交易时段，静默")
        return

    res = run_detection(cfg, st, now)
    if res is None:
        print("数据源缺失")
        return
    new_alerts, breadth = res
    if new_alerts:
        st["alerts"].extend(new_alerts)
        st["updated_at"] = now.strftime("%Y-%m-%d %H:%M:%S")
        save_state(st)
        page = gen_html(cfg, st, date_str, breadth)
        page_path = os.path.join(REPORT_DIR, date_str, f"盘中预警时间线-{now.strftime('%Y%m%d')}.html")
        open(page_path, "w", encoding="utf-8").write(page)
        if args.no_publish:
            print(f"（--no-publish）已生成 {page_path}，跳过发布")
        else:
            publish()
        high = sum(1 for a in new_alerts if a["priority"] == "高")
        mid = sum(1 for a in new_alerts if a["priority"] == "中")
        status = "（未发布 --no-publish）" if args.no_publish else "（已发布）"
        print(f"盘中预警：新增 {len(new_alerts)} 条（高{high}/中{mid}），累计 {len(st['alerts'])} 条 {status}")
    else:
        print(f"盘中预警：无新增（静默）｜ 累计 {len(st['alerts'])} 条")

if __name__ == "__main__":
    main()
