#!/usr/bin/env python3
"""Fetch 250-day K-line for all 9 indices via westock-mcp data_kline (single code each) and save to _raw_<CODE>.json."""
import json, os, datetime, sys

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')

# Index codes to fetch
CODES = {
    "sh000001": "上证",
    "sz399001": "深证",
    "sz399006": "创业板",
    "sh000016": "上证50",
    "sh000300": "沪深300",
    "sh000905": "中证500",
    "sh000688": "科创50",
    "bj899050": "北证50",
}

# The westock-mcp tool is called externally. This script processes the raw JSON response.
# We'll use it after fetching each index.

def save_raw(code, nodes):
    path = os.path.join(DATA, f"_raw_{code}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"code": code, "nodes": nodes}, f, ensure_ascii=False, indent=1)
    print(f"Saved {code} ({len(nodes)} rows) -> {path}")

if __name__ == "__main__":
    print("This script is for processing. Use with external data_kline calls.")
    for code, name in CODES.items():
        print(f"{code} {name}")
