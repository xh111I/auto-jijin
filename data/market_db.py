# -*- coding: utf-8 -*-
"""
market_db.py  —  市场数据库引擎（SQLite）
==========================================
职责：数据仓储层。所有自动化任务从此读取，不再自行拉取数据。
数据源刷新由 refresh_db.py 独立完成。

用法：
  from market_db import MarketDB
  db = MarketDB()
  db.get_index_spot()       # 指数实时行情
  db.get_sector_spot()      # 板块行情
  db.get_fund_nav()         # 基金净值
  db.get_capital_flow()     # 资金流向
  db.get_sentiment()        # 情绪因子
  db.get_global()           # 全球市场
  db.get_freshness()        # 数据新鲜度
"""

import sqlite3
import os
import json
import datetime
from typing import Optional, List, Dict

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE, "market.db")

# ── 建表 DDL（所有表结构） ──

SCHEMA_SQL = """
-- 数据新鲜度追踪
CREATE TABLE IF NOT EXISTS data_freshness (
    source      TEXT PRIMARY KEY,          -- 'neodata'/'westock'/'jin10'/'finance_dcths'/'akshare'
    table_name  TEXT NOT NULL,             -- 对应的表名
    updated_at  TEXT NOT NULL,             -- ISO 时间戳
    record_count INTEGER DEFAULT 0,
    status      TEXT DEFAULT 'ok',         -- 'ok'/'stale'/'error'
    note        TEXT
);

-- 大盘指数实时行情
CREATE TABLE IF NOT EXISTS index_spot (
    code        TEXT PRIMARY KEY,          -- 'sh000001'
    name        TEXT NOT NULL,             -- '上证指数'
    price       REAL,                     -- 最新价
    change_pct  REAL,                     -- 涨跌幅%
    change_amt  REAL,                     -- 涨跌额
    open        REAL,                     -- 今开
    high        REAL,                     -- 最高
    low         REAL,                     -- 最低
    volume      REAL,                     -- 成交量
    amount      REAL,                     -- 成交额
    updated_at  TEXT NOT NULL
);

-- 板块实时行情
CREATE TABLE IF NOT EXISTS sector_spot (
    code        TEXT PRIMARY KEY,          -- 板块代码
    name        TEXT NOT NULL,             -- 板块名称
    price       REAL,
    change_pct  REAL,
    turnover    REAL,                     -- 换手率
    net_inflow  REAL,                     -- 主力净流入（亿）
    updated_at  TEXT NOT NULL
);

-- 板块历史走势（用于日K分析）
CREATE TABLE IF NOT EXISTS sector_history (
    code        TEXT NOT NULL,
    date        TEXT NOT NULL,
    open        REAL,
    close       REAL,
    high        REAL,
    low         REAL,
    volume      REAL,
    amount      REAL,
    change_pct  REAL,
    PRIMARY KEY (code, date)
);

-- 基金净值快照
CREATE TABLE IF NOT EXISTS fund_nav (
    fund_id     TEXT NOT NULL,              -- 基金标识
    date        TEXT NOT NULL,              -- YYYY-MM-DD
    nav         REAL,                      -- 单位净值
    acc_nav     REAL,                      -- 累计净值
    day_return  REAL,                      -- 日涨跌幅%
    fund_scale  REAL,                      -- 基金规模（亿）
    PRIMARY KEY (fund_id, date)
);

-- 持仓关联指数近60日OHLC
CREATE TABLE IF NOT EXISTS index_ohlc (
    code        TEXT NOT NULL,
    date        TEXT NOT NULL,
    open        REAL,
    high        REAL,
    low         REAL,
    close       REAL,
    volume      REAL,
    PRIMARY KEY (code, date)
);

-- 北向资金
CREATE TABLE IF NOT EXISTS northbound (
    date        TEXT PRIMARY KEY,           -- YYYY-MM-DD
    net_buy     REAL,                      -- 净买入（亿）
    sh_net      REAL,                      -- 沪股通
    sz_net      REAL,                      -- 深股通
   累计净买入    REAL,
    updated_at  TEXT
);

-- 市场广度
CREATE TABLE IF NOT EXISTS market_breadth (
    date        TEXT PRIMARY KEY,
    up_count    INTEGER,                   -- 上涨家数
    down_count  INTEGER,                   -- 下跌家数
    flat_count  INTEGER,                   -- 平盘
    limit_up    INTEGER,                   -- 涨停
    limit_down  INTEGER,                   -- 跌停
    total_turnover REAL,                   -- 总成交额（亿）
    updated_at  TEXT
);

-- 情绪因子（恐惧贪婪指数）
CREATE TABLE IF NOT EXISTS sentiment (
    date            TEXT PRIMARY KEY,
    fear_greed      INTEGER,               -- 恐惧贪婪指数 0-100
    level           TEXT,                   -- '极度恐惧'/'恐惧'/'中性'/'贪婪'/'极度贪婪'
    breadth_score   REAL,
    main_force_score REAL,
    north_score     REAL,
    volume_score    REAL,
    vix_score       REAL,
    margin_score    REAL,
    limit_score     REAL,
    erp_score       REAL,
    note            TEXT,
    updated_at      TEXT
);

-- 全球市场（隔夜行情）
CREATE TABLE IF NOT EXISTS global_market (
    group_name  TEXT NOT NULL,              -- '美股'/'大宗'/'汇率'/'港股'
    name        TEXT NOT NULL,             -- 标的名称
    price       REAL,
    change_pct  REAL,
    tier        TEXT DEFAULT 'T2',         -- 可信度等级
    is_key      INTEGER DEFAULT 0,         -- 是否重点标的
    note        TEXT,
    updated_at  TEXT NOT NULL,
    PRIMARY KEY (group_name, name)
);

-- 主力资金流向（行业）
CREATE TABLE IF NOT EXISTS capital_flow (
    date        TEXT NOT NULL,
    sector_name TEXT NOT NULL,              -- 行业名称
    net_inflow  REAL,                      -- 净流入（亿）
    rank        INTEGER,                   -- 排名
    updated_at  TEXT,
    PRIMARY KEY (date, sector_name)
);

CREATE INDEX IF NOT EXISTS idx_index_ohlc_code ON index_ohlc(code);
CREATE INDEX IF NOT EXISTS idx_sector_history_code ON sector_history(code);
CREATE INDEX IF NOT EXISTS idx_capital_flow_date ON capital_flow(date);
CREATE INDEX IF NOT EXISTS idx_global_updated ON global_market(updated_at);
"""


class MarketDB:
    """市场数据库封装。"""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_schema()

    def _init_schema(self):
        """初始化表结构。"""
        conn = sqlite3.connect(self.db_path)
        conn.executescript(SCHEMA_SQL)
        conn.commit()
        conn.close()

    def _conn(self):
        return sqlite3.connect(self.db_path)

    # ── 写入接口 ──

    def upsert(self, table: str, data: dict, conflict_col: str = None):
        """插入或更新单行。"""
        if not data:
            return
        cols = list(data.keys())
        placeholders = ", ".join("?" for _ in cols)
        if conflict_col:
            updates = ", ".join(f"{c}=excluded.{c}" for c in cols if c != conflict_col)
            sql = f"""INSERT INTO {table} ({", ".join(cols)})
                      VALUES ({placeholders})
                      ON CONFLICT({conflict_col}) DO UPDATE SET {updates}"""
        else:
            sql = f"INSERT OR REPLACE INTO {table} ({', '.join(cols)}) VALUES ({placeholders})"
        conn = self._conn()
        try:
            conn.execute(sql, [data.get(c) for c in cols])
            conn.commit()
        finally:
            conn.close()

    def upsert_many(self, table: str, rows: List[dict], conflict_col: str = None):
        """批量插入或更新。"""
        if not rows:
            return
        cols = list(rows[0].keys())
        placeholders = ", ".join("?" for _ in cols)
        if conflict_col:
            updates = ", ".join(f"{c}=excluded.{c}" for c in cols if c != conflict_col)
            sql = f"""INSERT INTO {table} ({", ".join(cols)})
                      VALUES ({placeholders})
                      ON CONFLICT({conflict_col}) DO UPDATE SET {updates}"""
        else:
            sql = f"INSERT OR REPLACE INTO {table} ({', '.join(cols)}) VALUES ({placeholders})"
        conn = self._conn()
        try:
            conn.executemany(sql, [[r.get(c) for c in cols] for r in rows])
            conn.commit()
        finally:
            conn.close()

    def mark_freshness(self, source: str, table_name: str, count: int = 0,
                       status: str = "ok", note: str = ""):
        """更新数据新鲜度。"""
        self.upsert("data_freshness", {
            "source": source, "table_name": table_name,
            "updated_at": datetime.datetime.now().isoformat(),
            "record_count": count, "status": status, "note": note,
        }, conflict_col="source")

    # ── 读取接口 ──

    def query(self, sql: str, params: tuple = ()) -> List[Dict]:
        """通用查询，返回 dict 列表。"""
        conn = self._conn()
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()

    def get_index_spot(self) -> List[Dict]:
        """获取大盘指数实时行情。"""
        return self.query("SELECT * FROM index_spot ORDER BY code")

    def get_index_by_code(self, code: str) -> Optional[Dict]:
        """获取单个指数。"""
        rows = self.query("SELECT * FROM index_spot WHERE code=?", (code,))
        return rows[0] if rows else None

    def get_sector_spot(self, names: list = None) -> List[Dict]:
        """获取板块行情。"""
        if names:
            ph = ", ".join("?" for _ in names)
            return self.query(f"SELECT * FROM sector_spot WHERE name IN ({ph}) ORDER BY name", tuple(names))
        return self.query("SELECT * FROM sector_spot ORDER BY change_pct DESC")

    def get_fund_nav(self, fund_id: str = None, date: str = None) -> List[Dict]:
        """获取基金净值。"""
        cond, params = [], []
        if fund_id:
            cond.append("fund_id=?"); params.append(fund_id)
        if date:
            cond.append("date=?"); params.append(date)
        where = f"WHERE {' AND '.join(cond)}" if cond else ""
        return self.query(f"SELECT * FROM fund_nav {where} ORDER BY date DESC")

    def get_index_ohlc(self, code: str, days: int = 60) -> List[Dict]:
        """获取指数近N日日K。"""
        return self.query(
            "SELECT * FROM index_ohlc WHERE code=? ORDER BY date DESC LIMIT ?",
            (code, days)
        )

    def get_northbound(self, date: str = None) -> Optional[Dict]:
        """获取北向资金。"""
        if date:
            rows = self.query("SELECT * FROM northbound WHERE date=?", (date,))
        else:
            rows = self.query("SELECT * FROM northbound ORDER BY date DESC LIMIT 1")
        return rows[0] if rows else None

    def get_breadth(self, date: str = None) -> Optional[Dict]:
        """获取市场广度。"""
        if date:
            rows = self.query("SELECT * FROM market_breadth WHERE date=?", (date,))
        else:
            rows = self.query("SELECT * FROM market_breadth ORDER BY date DESC LIMIT 1")
        return rows[0] if rows else None

    def get_sentiment(self, date: str = None) -> Optional[Dict]:
        """获取情绪因子数据。"""
        if date:
            rows = self.query("SELECT * FROM sentiment WHERE date=?", (date,))
        else:
            rows = self.query("SELECT * FROM sentiment ORDER BY date DESC LIMIT 1")
        return rows[0] if rows else None

    def get_global_market(self, group: str = None) -> List[Dict]:
        """获取全球市场行情。"""
        if group:
            return self.query("SELECT * FROM global_market WHERE group_name=? ORDER BY change_pct DESC", (group,))
        return self.query("SELECT * FROM global_market ORDER BY group_name, change_pct DESC")

    def get_capital_flow(self, date: str = None, top_n: int = 10) -> List[Dict]:
        """获取主力资金流向（行业排行）。"""
        if date:
            return self.query(
                "SELECT * FROM capital_flow WHERE date=? ORDER BY net_inflow DESC LIMIT ?",
                (date, top_n)
            )
        return self.query(
            "SELECT * FROM capital_flow ORDER BY date DESC, net_inflow DESC LIMIT ?",
            (top_n,)
        )

    def get_freshness(self) -> List[Dict]:
        """获取数据新鲜度状态。"""
        return self.query("SELECT * FROM data_freshness ORDER BY source")

    def is_stale(self, source: str, max_minutes: int = 30) -> bool:
        """检查数据源是否过期。"""
        rows = self.query(
            "SELECT updated_at FROM data_freshness WHERE source=? AND status='ok'",
            (source,)
        )
        if not rows:
            return True
        try:
            updated = datetime.datetime.fromisoformat(rows[0]["updated_at"])
            age = (datetime.datetime.now() - updated).total_seconds() / 60
            return age > max_minutes
        except Exception:
            return True

    def summary(self) -> str:
        """数据源摘要（用于报告页脚）。"""
        lines = []
        rows = self.get_freshness()
        for r in rows:
            time_str = r["updated_at"][11:19] if r["updated_at"] else "—"
            lines.append(f"{r['source']}: {r['record_count']}条 @{time_str}")
        return " | ".join(lines)


if __name__ == "__main__":
    # 测试建表
    db = MarketDB()
    print(f"✅ 数据库已创建: {db.db_path}")
    print(f"   表: index_spot / sector_spot / fund_nav / index_ohlc / "
          f"northbound / market_breadth / sentiment / global_market / capital_flow / data_freshness")
    print(f"   数据新鲜度: {db.get_freshness()}")
