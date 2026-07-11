# -*- coding: utf-8 -*-
import sys, os, json, time
from concurrent.futures import ThreadPoolExecutor, as_completed

SKILL = r"E:\新建文件夹\WorkBuddy\resources\app.asar.unpacked\resources\builtin-skills\neodata-financial-search\scripts"
sys.path.insert(0, SKILL)
from query import query_neodata

QUERIES = {
    # 隔夜美股（7/10 美东收盘）
    "ndx": "纳斯达克100指数最新点位和涨跌幅",
    "spx": "标普500指数最新点位和涨跌幅",
    "dji": "道琼斯工业平均指数最新点位和涨跌幅",
    "sox": "费城半导体指数SOX最新点位和涨跌幅",
    "soxx": "半导体ETF iShares SOXX 最新价格和涨跌幅",
    "mu": "美光科技MU最新股价和涨跌幅",
    "sndk": "闪迪SNDK最新股价和涨跌幅",
    "nvda": "英伟达NVDA最新股价和涨跌幅",
    "avgo": "博通AVGO最新股价和涨跌幅",
    "mrvl": "迈威尔MRVL最新股价和涨跌幅",
    "asml": "阿斯麦ASML最新股价和涨跌幅",
    "amat": "应用材料AMAT最新股价和涨跌幅",
    "lrcx": "泛林LRCX最新股价和涨跌幅",
    # 大宗 / 汇率
    "wti": "WTI原油期货最新价格和涨跌幅",
    "gold": "COMEX黄金期货最新价格和涨跌幅",
    "copper": "COMEX铜期货最新价格和涨跌幅",
    "dxy": "美元指数DXY最新点位和涨跌幅",
    "usdcnh": "美元兑离岸人民币USDCNH最新汇率",
    "vix": "VIX恐慌指数最新点位",
    # 港股（7/10 收盘）
    "hsi": "恒生指数最新点位和涨跌幅",
    "hstech": "恒生科技指数最新点位和涨跌幅",
    "tencent": "腾讯控股00700最新股价和涨跌幅",
    "baba": "阿里巴巴9988最新股价和涨跌幅",
    "meituan": "美团3690最新股价和涨跌幅",
    "wuxi": "药明生物2269最新股价和涨跌幅",
    "innovent": "信达生物1801最新股价和涨跌幅",
    "akeso": "康方生物9926最新股价和涨跌幅",
    # A股映射（7/10 收盘）
    "zjxc": "中际旭创300308最新股价和涨跌幅",
    "xys": "新易盛300502最新股价和涨跌幅",
    "tf": "天孚通信300394最新股价和涨跌幅",
    "etf512480": "半导体ETF 512480最新净值和涨跌幅",
    # 利率
    "us10y": "美国10年期国债收益率最新",
    "cn10y": "中国10年期国债收益率最新",
    # 新闻 / 财报季
    "news": "今日A股全市场重大新闻：产业政策 技术突破 公司公告 突发事件 半导体 航天 生物医药 新能源",
    "afterhours": "昨日A股盘后公告和龙虎榜异动",
    "turnover": "昨日A股全市场成交额和近5日量能趋势 连续放量还是缩量",
    "earnings": "本周A股中报预告披露情况 哪些公司发布中报业绩预告 预喜率",
    "semi_earn": "半导体板块中报业绩预告 预喜率",
    # 持仓净值快照（最新可得）
    "ai017811": "东方人工智能主题混合C 017811 最新净值",
    "alpha024424": "东方阿尔法科技优选混合C 024424 最新净值",
    "ying025209": "永赢先锋半导体智选混合C 025209 最新净值",
    "hk019671": "广发港股创新药ETF联接C 019671 最新净值",
    "semi_index": "中证半导体材料设备指数 最新点位和涨跌幅",
    "ai_index": "中证人工智能指数 最新点位和涨跌幅",
}

OUT = r"C:\Users\LEGION\Nutstore\1\daily-report\data\.nd_cache\batch_2026-07-11.json"

def run(key, q):
    try:
        r = query_neodata(query=q, data_type="all")
        return key, {"ok": True, "data": r}
    except Exception as e:
        return key, {"ok": False, "err": str(e)}

def main():
    results = {}
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=12) as ex:
        futs = {ex.submit(run, k, v): k for k, v in QUERIES.items()}
        for f in as_completed(futs):
            k, v = f.result()
            results[k] = v
            status = "OK" if v["ok"] else "FAIL"
            print(f"[{status}] {k}", flush=True)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(results, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("saved", OUT, "elapsed", round(time.time()-t0, 1), "s", "count", len(results))

if __name__ == "__main__":
    main()
