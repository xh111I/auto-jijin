#!/usr/bin/env python3
"""Save cs sector westock data to _sector_raw/<code>_wx.json files."""
import json, os

BASE = os.path.dirname(os.path.abspath(__file__))
SECTOR_DIR = os.path.join(BASE, "_sector_raw")
os.makedirs(SECTOR_DIR, exist_ok=True)

DATA = {
    "csH30184_wx.json": ("csH30184", "半导体"),
    "cs931160_wx.json": ("cs931160", "CPO/通信设备"),
    "cs931787_wx.json": ("cs931787", "港股创新药"),
    "cs931071_wx.json": ("cs931071", "人工智能(应用端)"),
}

# Paste the westock MCP output here
NODES = {
    "csH30184": {"nodes": [
        {"date":"2026-07-10","open":18432.7,"last":17131.32,"high":18864.02,"low":17131.32,"volume":47401458,"amount":554883260100},
        {"date":"2026-07-09","open":17190.67,"last":18309.48,"high":18322.2,"low":16903.71,"volume":40468839,"amount":474883244900},
        {"date":"2026-07-08","open":16951.55,"last":16830,"high":17454.72,"low":16214.53,"volume":38290222,"amount":406232615000},
        {"date":"2026-07-07","open":16456.55,"last":16771.62,"high":17159.41,"low":16331.96,"volume":32956286,"amount":364631213700},
        {"date":"2026-07-06","open":17081.78,"last":16793.19,"high":17157.01,"low":16082.54,"volume":34311997,"amount":406780263000},
        {"date":"2026-07-03","open":16775.8,"last":16731.87,"high":17381.94,"low":16394.48,"volume":36283686,"amount":422097592800},
        {"date":"2026-07-02","open":17529.69,"last":16982.08,"high":17991.7,"low":16900.12,"volume":42244739,"amount":474297156200},
        {"date":"2026-07-01","open":18839.14,"last":18520.46,"high":19594.87,"low":18204.64,"volume":47105382,"amount":542470409900}
    ]},
    "cs931160": {"nodes": []},
    "cs931787": {"nodes": []},
    "cs931071": {"nodes": []},
}

# I need to paste the full data from all 4, but let me just write a helper
# that reads from inline data
print("Please use save_cs_sectors_full.py with complete data")
