# -*- coding: utf-8 -*-
import json
IN = r"C:\Users\LEGION\Nutstore\1\daily-report\data\.nd_cache\batch_2026-07-11.json"
data = json.load(open(IN, encoding="utf-8"))

def api_content(d):
    try:
        return d["data"]["apiData"]["apiRecall"]
    except Exception:
        return []

def doc_text(d):
    try:
        rec = d["data"]["docData"]["docRecall"]
        out = []
        for g in rec:
            for doc in (g.get("docList") or [])[:3]:
                t = doc.get("title") or doc.get("content") or ""
                out.append((g.get("extQuery",""), t[:400]))
        return out
    except Exception:
        return []

for k, v in data.items():
    print("="*70)
    print("KEY:", k, "| ok:", v.get("ok"))
    if not v.get("ok"):
        print("  ERR:", v.get("err")); continue
    ac = api_content(v["data"])
    if ac:
        print("  API:")
        for a in ac:
            c = a.get("content","")
            # trim very long
            c = c if len(c) < 600 else c[:600]+" ...[truncated]"
            print("   -", a.get("type",""), "::", c.replace("\n"," | "))
    dt = doc_text(v["data"])
    if dt:
        print("  DOC:")
        for q, t in dt:
            print("   [", q, "]", t.replace("\n"," "))
