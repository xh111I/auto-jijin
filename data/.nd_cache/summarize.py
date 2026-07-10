# -*- coding: utf-8 -*-
import json, glob, os
base = os.path.dirname(os.path.abspath(__file__))
files = sorted(glob.glob(os.path.join(base, "q_*.txt")))
for f in files:
    name = os.path.basename(f)
    print("\n================ %s ================" % name)
    try:
        d = json.load(open(f, encoding="utf-8"))
    except Exception as e:
        print("PARSE_FAIL", e)
        # print raw first 800 chars
        raw = open(f, encoding="utf-8").read()[:800]
        print(raw)
        continue
    data = d.get("data", {})
    api = data.get("apiData", {})
    for block in api.get("apiRecall", []) or []:
        print("[API:%s] %s" % (block.get("type"), block.get("content", "")[:600]))
    doc = data.get("docData", {})
    for grp in doc.get("docRecall", []) or []:
        for docitem in (grp.get("docList") or [])[:4]:
            t = docitem.get("title", "")
            c = (docitem.get("content") or docitem.get("summary") or "")[:300]
            print("[DOC] %s :: %s" % (t, c))
