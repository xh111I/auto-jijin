import sys, json
raw = sys.stdin.read()
try:
    d = json.loads(raw)
except Exception:
    sys.stdout.write("PARSE_ERR:" + raw[:300]); sys.exit()
api = (d.get("data") or {}).get("apiData") or {}
for a in api.get("apiRecall") or []:
    c = a.get("content","") or ""
    print("###", a.get("type"), "|", a.get("desc",""))
    for line in c.splitlines():
        ls = line.strip()
        if ("涨跌幅" in ls) or ("pt0180" in ls) or ("pt0213" in ls) or ("主力净流入" in ls and "万元" in ls) or ("主力净流出" in ls and "万元" in ls):
            print("   ", ls[:300])
