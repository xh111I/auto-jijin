#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复 _sector_raw/<code>_wx.json 中个别数值后误带的尾引号(如 "open":12428.31")，
使其能被标准 json 解析。仅删除 "冒号+数字+引号+分隔符" 模式中的多余引号，
不会误伤合法字符串(合法字符串是 "xxx":"123"，冒号后是引号而非数字)。"""
import json
import os
import re

BASE = "C:/Users/LEGION/Nutstore/1/daily-report/data/_sector_raw"
FILES = ["csH30184_wx.json", "cs931160_wx.json", "cs931787_wx.json", "cs931071_wx.json"]

# 冒号后紧跟数字(可带负号/小数点)再紧跟引号，引号后为 , } ] (可含空白)
BAD = re.compile(r'(?<=:)(-?\d+(?:\.\d+)?)"(\s*[,\]}])')


def repair_one(fname):
    path = os.path.join(BASE, fname)
    with open(path, encoding="utf-8") as f:
        text = f.read()
    fixed = BAD.sub(r'\1\2', text)
    n_fixed = len(text) - len(fixed)
    # 重新解析校验
    obj = json.loads(fixed)
    nodes = obj.get("nodes", [])
    # 写回(原样美化)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)
    print("%-20s nodes=%-4d removed_stray_quotes=%d OK" % (fname, len(nodes), n_fixed))


def main():
    for fn in FILES:
        try:
            repair_one(fn)
        except Exception as e:
            print("%-20s ERROR: %s" % (fn, e))


if __name__ == "__main__":
    main()
