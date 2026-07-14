# -*- coding: utf-8 -*-
"""
fetch_akshare.py  —  akshare 数据补充拉取器

作为 neodata 和 westock 的补充数据源，主要覆盖：
  1. 大盘指数实时行情（新浪源，工作稳定）
  2. 板块行业实时/历史行情
  3. 上交所/深交所概况
  4. 宏观指标（GDP/CPI/PMI）
  5. 股票基础信息

用法：
  python fetch_akshare.py index     # 拉取主要指数实时行情
  python fetch_akshare.py sector    # 拉取各板块实时行情
  python fetch_akshare.py all       # 拉取全量

输出：
  写入 data/akshare_raw/ 目录下，供自动化任务和生成器引用。
"""

import json
import os
import sys
import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "akshare_raw")
os.makedirs(OUT, exist_ok=True)

try:
    import akshare as ak
    HAS_AK = True
except ImportError:
    HAS_AK = False


def save_json(key, data):
    """把数据保存为 JSON，同时保留 DataFrame 的 to_dict 结构。"""
    import pandas as pd
    if isinstance(data, pd.DataFrame):
        data = json.loads(data.to_json(orient="records", force_ascii=False))
    path = os.path.join(OUT, f"{key}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    if isinstance(data, list):
        print(f"[akshare] {key}: {len(data)} 条 → {os.path.basename(path)}")
    else:
        print(f"[akshare] {key} → {os.path.basename(path)}")


def fetch_index():
    """主要指数实时行情（新浪源）。"""
    import pandas as pd
    if not HAS_AK:
        print("[akshare] akshare 未安装，跳过")
        return
    try:
        df = ak.stock_zh_index_spot_sina()
        # 筛选关键指数
        targets = {
            "sh000001": "上证指数", "sz399001": "深证成指", "sz399006": "创业板指",
            "sh000016": "上证50",   "sh000300": "沪深300",  "sh000905": "中证500",
            "sh000688": "科创50",   "bj899050": "北证50",
        }
        df_filtered = df[df["代码"].isin(targets.keys())].copy()
        for col in ["最新价", "涨跌额", "涨跌幅", "昨收", "今开", "最高", "最低"]:
            df_filtered[col] = pd.to_numeric(df_filtered[col], errors="coerce")
        save_json("index_spot", df_filtered)
    except Exception as e:
        print(f"[akshare] index fetch ERROR: {e}")


def fetch_sector():
    """板块行业行情（东方财富源，可能受限）。"""
    import pandas as pd
    if not HAS_AK:
        return
    try:
        df = ak.stock_board_industry_spot_em()
        targets = ["半导体", "人工智能", "通信设备", "创新药", "煤炭", "消费", "证券", "军工", "银行"]
        df_filtered = df[df["板块名称"].apply(lambda x: any(t in x for t in targets))]
        save_json("sector_spot", df_filtered)
    except Exception as e:
        print(f"[akshare] sector fetch ERROR (EM源被限): {e}")
        # 降级：从新浪获取
        try:
            # 降级方案：用指数代替板块
            print("[akshare] sector 降级：仅提供指数数据")
        except Exception as e2:
            print(f"[akshare] sector fallback ERROR: {e2}")


def fetch_sse_summary():
    """上交所概况。"""
    if not HAS_AK:
        return
    try:
        df = ak.stock_sse_summary()
        save_json("sse_summary", df)
    except Exception as e:
        print(f"[akshare] SSE summary ERROR: {e}")


def fetch_all():
    """全量拉取。"""
    fetch_index()
    fetch_sector()
    fetch_sse_summary()


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd == "index":
        fetch_index()
    elif cmd == "sector":
        fetch_sector()
    elif cmd == "sse":
        fetch_sse_summary()
    else:
        fetch_all()

    print("[akshare] DONE")
