# -*- coding: utf-8 -*-
import json, os
BASE = os.path.dirname(os.path.abspath(__file__))
DATE = "2026-07-10"
TOTAL = 13138.74  # account_total_asset (T0)

# holdings: name, mv, ret(持有收益% or None)
H = [
    ("东方人工智能主题混合C", 4747.32, 13.28),
    ("东方阿尔法科技优选混合C", 3358.57, 11.95),
    ("鹏华丰诚债券C", 1262.55, None),
    ("广发港股创新药ETF联接(QDII)C", 1566.81, -3.75),
    ("永赢先锋半导体智选混合C", 885.22, None),
    ("富国中证煤炭指数C", 502.23, None),
    ("嘉实中证主要消费ETF发起联接C", 496.51, None),
    ("广发纳斯达克100ETF联接(QDII)C", 78.92, None),
    ("财通集成电路产业股票C", 105.0, None),
    ("财通成长优选混合C", 104.91, None),
    ("天弘中证全指通信设备指数C", 10.59, None),
]

def risk_dist(ret):
    if ret is None:
        return None
    v = (-ret) / 8.0 * 100.0
    return int(round(max(0.0, min(100.0, v))))

holdings = []
for name, mv, ret in H:
    wp = round(mv / TOTAL * 100, 2)
    rd = risk_dist(ret)
    # default action/risk
    if name.startswith("东方人工智能"):
        act, rk, sig = "减仓", "高", "重仓半导体(36.1%超30%上限)+隔夜SOX+3.5%强修复，高位继续锁利、禁加仓"
    elif name.startswith("东方阿尔法"):
        act, rk, sig = "警惕", "高", "半导体25.6%接近上限、随板块修复，逢高可减、防集群回撤"
    elif name.startswith("鹏华"):
        act, rk, sig = "持有", "低", "纯债安全垫，避险属性，今日无操作"
    elif name.startswith("广发港股创新药"):
        act, rk, sig = "观望", "中", "港股高开托底(+1.25%)但美团/信达内部分化，温和跟涨不宜追高；距-8%止损约47%"
    elif name.startswith("永赢先锋"):
        act, rk, sig = "持有", "中", "半导体小仓(6.7%)，隔夜板块修复跟随，无需动作"
    elif name.startswith("富国中证煤炭"):
        act, rk, sig = "持有", "低", "煤炭防御仓，与科技低相关，持有"
    elif name.startswith("嘉实中证主要消费"):
        act, rk, sig = "持有", "低", "主要消费防御仓，持有"
    elif name.startswith("广发纳斯达克"):
        act, rk, sig = "持有", "中", "纳指隔夜+1.62%反弹托底，小仓(0.6%)持有"
    elif name.startswith("财通集成电路"):
        act, rk, sig = "持有", "中", "半导体/CPO小仓，新易盛+3.39%/天孚+3.50%催化，持有观察"
    elif name.startswith("财通成长"):
        act, rk, sig = "持有", "中", "成长混合小仓，跟随市场，持有"
    elif name.startswith("天弘中证全指通信设备"):
        act, rk, sig = "持有", "低", "CPO光通信催化(中际旭创+1.26%)，极小仓持有"
    else:
        act, rk, sig = "持有", "中", ""
    holdings.append({
        "name": name, "weight_pct": wp, "ret": ret, "signal": sig,
        "action_tag": act, "risk_level": rk, "risk_dist": rd
    })

data = {
    "date": DATE,
    "updated_at": "09:00（北京时间）· A股开盘前",
    "data_tier": "T1",
    "sentiment": {
        "broad": {"score": 55, "label": "中性偏多",
                  "note": "隔夜美股反弹+半导体存储暴涨(美光+4.52%/闪迪+7.59%)托底、港股高开，但中东油价悬顶、美团/信达走弱，整体中性偏多。"},
        "semiconductor": {"score": 62, "label": "偏多",
                  "note": "美光+4.52%/闪迪+7.59%领涨，SOXX+3.50%，半导体情绪修复偏多。"}
    },
    "core": {
        "mood_bars": [
            {"k": "美股隔夜", "score": 60, "label": "偏多"},
            {"k": "半导体", "score": 62, "label": "偏多"},
            {"k": "港股盘前", "score": 58, "label": "偏多"},
            {"k": "地缘/油价", "score": 45, "label": "偏空"},
            {"k": "汇率", "score": 55, "label": "中性偏多"}
        ],
        "one_liner": "隔夜美股反弹+半导体存储暴涨(美光+4.52%/闪迪+7.59%)托底、港股高开，但中东油价悬顶、美团/信达走弱，盘前中性偏多中带分化，重仓半导体今日有修复但勿追高、宜借反弹锁利。",
        "action_rules": "总仓≈99.8%超90%、东方AI单仓36.1%超30%、半导体集群≈69%高集中 → 全天禁净买入；重仓半导体(东方AI/阿尔法)逢高继续锁利；港药/纳指跟随外围；破-8%硬止损。",
        "top_risk": "中东霍尔木兹冲突再升级→油价传导通胀→高估值科技中期承压；叠加总仓与单仓双超限，上行空间受限、回撤缓冲薄。"
    },
    "global": [
        {"group": "美股", "rows": [
            {"name": "纳斯达克100", "close": "29,727.10", "chg": 1.62, "tier": "T1", "signal": "偏多·纳指QDII隔夜反弹托底", "key": True},
            {"name": "标普500", "close": "7,543.64", "chg": 0.81, "tier": "T1", "signal": "偏多"},
            {"name": "道琼斯", "close": "52,487.41", "chg": 0.27, "tier": "T1", "signal": "中性偏多"},
            {"name": "费城半导体SOX(SOXX代理)", "close": "581.70", "chg": 3.50, "tier": "T1", "signal": "偏多·存储龙头领涨，半导体重仓直接映射", "key": True},
            {"name": "美光 MU", "close": "991.64", "chg": 4.52, "tier": "T1", "signal": "强多·存储涨价超预期", "key": True},
            {"name": "闪迪 SNDK", "close": "1,858.27", "chg": 7.59, "tier": "T1", "signal": "强多·存储龙头暴涨", "key": True},
            {"name": "英伟达 NVDA", "close": "202.78", "chg": -0.66, "tier": "T1", "signal": "中性偏空·AI芯片分化"},
            {"name": "博通 AVGO", "close": "401.11", "chg": 3.20, "tier": "T1", "signal": "偏多"},
            {"name": "迈威尔 MRVL", "close": "243.27", "chg": 4.99, "tier": "T1", "signal": "偏多"},
            {"name": "阿斯麦 ASML", "close": "1,804.25", "chg": 2.01, "tier": "T1", "signal": "偏多·设备景气"},
            {"name": "应用材料 AMAT", "close": "588.66", "chg": 3.18, "tier": "T1", "signal": "偏多"},
            {"name": "泛林 LRCX", "close": "353.17", "chg": 6.01, "tier": "T1", "signal": "强多"}
        ]},
        {"group": "亚太(盘前)", "rows": [
            {"name": "恒生指数", "close": "24,213.44", "chg": 0.76, "tier": "T1", "signal": "偏多·港股高开"},
            {"name": "恒生科技", "close": "4,790.51", "chg": 1.25, "tier": "T1", "signal": "偏多·港药映射托底", "key": True},
            {"name": "腾讯控股", "close": "472.80", "chg": 0.68, "tier": "T1", "signal": "偏多"},
            {"name": "阿里巴巴", "close": "110.00", "chg": 1.85, "tier": "T1", "signal": "偏多"},
            {"name": "美团-W", "close": "76.90", "chg": -2.04, "tier": "T1", "signal": "偏空·港股内部分化", "warn": "走弱"},
            {"name": "药明生物", "close": "37.20", "chg": 0.38, "tier": "T1", "signal": "中性偏多·18A"},
            {"name": "信达生物", "close": "86.30", "chg": -0.06, "tier": "T1", "signal": "中性·18A分化", "warn": "走平"},
            {"name": "康方生物", "close": "95.30", "chg": 0.69, "tier": "T1", "signal": "偏多·18A"},
            {"name": "中际旭创", "close": "1,210.00", "chg": 1.26, "tier": "T1", "signal": "偏多·CPO催化"},
            {"name": "新易盛", "close": "564.00", "chg": 3.39, "tier": "T1", "signal": "偏多·CPO量产"},
            {"name": "天孚通信", "close": "281.00", "chg": 3.50, "tier": "T1", "signal": "偏多·CPO"},
            {"name": "半导体ETF 512480", "close": "1.485", "chg": 0.95, "tier": "T1", "signal": "偏多·映射SOX", "key": True}
        ]},
        {"group": "大宗", "rows": [
            {"name": "WTI原油", "close": "72.11", "chg": 0.04, "tier": "T1", "signal": "中性·霍尔木兹紧张但价稳", "warn": "地缘悬顶"},
            {"name": "COMEX黄金", "close": "4,135.80", "chg": -0.12, "tier": "T1", "signal": "中性·避险平淡"},
            {"name": "COMEX铜", "close": "6.275", "chg": 0.15, "tier": "T1", "signal": "中性偏多"}
        ]},
        {"group": "汇率", "rows": [
            {"name": "美元指数 DXY", "close": "100.79", "chg": -0.15, "tier": "T1", "signal": "中性偏空·美元走弱利好风险资产"},
            {"name": "美元兑离岸人民币 USDCNH", "close": None, "chg": None, "tier": "T2", "signal": "待验证·源未返回具体值，参考美元走弱人民币偏强", "warn": "未返回"}
        ]}
    ],
    "conflicts": [
        {"level": "orange", "title": "中东霍尔木兹冲突再升级→油价传导通胀",
         "body": "美军7/7起再以'商船遭袭'为由袭击伊朗、伊朗反击美军中东基地，霍尔木兹航运'接近停滞'；但当前WTI 72.11(+0.04%)仍平稳，停火预期仍在。",
         "chain": "中东冲突→霍尔木兹通航受阻→原油供应风险→通胀预期→美联储转鹰→高估值科技承压",
         "impact": "半导体/纳指QDII(东方AI、阿尔法、纳指100QDII)中期估值承压；若WTI突破80触发避险。"},
        {"level": "orange", "title": "半导体集群≈69% + 东方AI单仓36.1% 双超限",
         "body": "总仓≈99.8%超90%、东方AI单仓36.1%超30%、半导体(东方AI+阿尔法+永赢+财通集成)≈69%高集中。",
         "chain": "单一板块高集中→板块回撤放大→账户波动加剧、回撤缓冲薄",
         "impact": "若半导体今日高开低走，账户回撤显著；宜借反弹锁利而非加仓。"},
        {"level": "yellow", "title": "港股内部分化：美团-2.04%、信达-0.06%走弱",
         "body": "恒指/恒科高开(+0.76%/+1.25%)，但美团-2.04%、信达-0.06%走弱，港股赚钱效应分化。",
         "chain": "港股分化→港药(广发港股创新药)跟涨动能存疑",
         "impact": "港药(11.9%仓位)今日或温和跟涨但不宜过高预期。"}
    ],
    "bulls": [
        {"strength": "强", "text": "存储龙头暴涨：美光+4.52%、闪迪+7.59%领涨，存储周期景气+AI需求", "target": "半导体(东方AI/阿尔法/永赢/财通集成)", "impact": "重仓半导体盘前情绪强修复，开盘有冲高动能"},
        {"strength": "中", "text": "港股高开：恒指+0.76%、恒科+1.25%、阿里+1.85%", "target": "港药(广发港股创新药)", "impact": "港药外围托底，温和跟涨"},
        {"strength": "中", "text": "CPO光通信催化：中际旭创+1.26%、新易盛+3.39%、天孚+3.50%，光模块量产实锤", "target": "通信设备(天弘通信)/半导体CPO(财通集成)", "impact": "CPO方向开盘有催化，关注财通集成"},
        {"strength": "弱", "text": "美元走弱：美元指数-0.15%，人民币偏强", "target": "港股/新兴市场", "impact": "汇率端利好风险资产，幅度有限"}
    ],
    "bears": [
        {"strength": "中", "text": "中东油价悬顶：霍尔木兹'接近停滞'、美军再袭伊朗，油价随时破位", "target": "半导体/纳指QDII/通胀敏感资产", "impact": "中期估值压制，WTI破80触发避险"},
        {"strength": "中", "text": "港股内部分化：美团-2.04%、信达-0.06%走弱", "target": "港药", "impact": "港药跟涨动能打折"},
        {"strength": "弱", "text": "英伟达分化：NVDA -0.66%弱于板块，AI芯片冷热不均", "target": "半导体情绪", "impact": "板块虽涨非普涨，注意追高回调"},
        {"strength": "中", "text": "仓位双超限：总仓≈99.8%>90%、东方AI36.1%>30%", "target": "全账户", "impact": "无加仓空间、回撤缓冲薄，破位易被动"}
    ],
    "earnings": [
        {"name": "美光 MU", "dynamic": "存储涨价超预期，MU +4.52%创高，Q3财报季临近", "impact": "利好半导体存储链(东方AI/阿尔法持仓映射)"},
        {"name": "阿里巴巴", "dynamic": "阿里+1.85%，港股科技情绪回暖", "impact": "间接托底港药/港股映射"},
        {"name": "SK海力士 ADR", "dynamic": "美国存托凭证7/10起首日交易(今日事件)", "impact": "存储供给端新增比价变量，关注对美光比价"}
    ],
    "holdings": holdings,
    "holdings_constraint": "⚠ 总仓≈99.8% 超目标90% · 东方AI单仓36.1% 超上限30% · 半导体集群≈69% 高集中 → 今日全天禁净买入，重仓半导体借反弹锁利、破-8%硬止损。",
    "tech": [
        {"index": "纳斯达克100", "close": "29,727.10", "chg": 1.62, "ma20": None, "ma60": None,
         "interpret": "隔夜反弹+1.62%站回短期均线附近，但20日仅+2.21%、5日-0.28%显示前几日偏弱；技术中性偏多，需确认能否站稳3万点。", "macd": None, "kdj": None},
        {"index": "费城半导体SOX(SOXX)", "close": "581.70", "chg": 3.50, "ma20": None, "ma60": None,
         "interpret": "SOXX+3.50%强反、存储龙头领涨；但前几日已现回调(部分半导体较高点回撤明显)，属短线超跌修复，非趋势反转确认。", "macd": None, "kdj": None},
        {"index": "恒生科技", "close": "4,790.51", "chg": 1.25, "ma20": None, "ma60": None,
         "interpret": "恒科高开+1.25%站上短期均线，港股科技情绪修复；但美团/信达分化提示内部分歧。", "macd": None, "kdj": None},
        {"index": "半导体ETF 512480", "close": "1.485", "chg": 0.95, "ma20": None, "ma60": None,
         "interpret": "A股半导体ETF +0.95% 集合竞价走强，映射隔夜SOX；注意高开易遭获利盘兑现。", "macd": None, "kdj": None}
    ],
    "events": [
        {"time": "09:30", "event": "A股开盘", "impact": "半导体/CPO高开兑现观察，重仓半导体锁利窗口"},
        {"time": "04:30", "event": "美联储资产负债表数据(未公布)", "impact": "关注缩表节奏与美元走向"},
        {"time": "全天", "event": "IEA月度原油市场报告", "impact": "油价供给预期，影响中东传导链"},
        {"time": "全天", "event": "SK海力士ADR首日交易", "impact": "存储比价新变量"},
        {"time": "全天", "event": "630亿元7天逆回购到期", "impact": "流动性小幅扰动"},
        {"time": "全天", "event": "朝鲜代表团访华/具身智能机器人展", "impact": "机器人/AI主题催化"}
    ],
    "credibility": [
        {"item": "美股/港股/大宗/汇率行情", "status": "ok", "note": "neodata T1 实时/收盘行情，时间戳2026-07-09美东收盘 / 2026-07-10早盘"},
        {"item": "费城半导体SOX", "status": "warn", "note": "源未直接返回SOX，采用SOXX(+3.50%)作等价代理(T2推断)"},
        {"item": "USDCNH离岸人民币", "status": "q", "note": "源未返回具体数值，以美元指数-0.15%走弱参考，开盘验证"},
        {"item": "持仓持有收益/距止损", "status": "warn", "note": "收益取用户T0快照备注(东方AI+13.28%/阿尔法+11.95%/港药-3.75%)，其余持仓未单独回填"},
        {"item": "技术面MA/MACD/KDJ", "status": "warn", "note": "neodata历史K线中段省略，均线/指标无法精确计算，仅作定性解读"},
        {"item": "中东地缘", "status": "ok", "note": "财联社/环球/央视等多源(T2)一致，冲突升级事实成立"}
    ],
    "disclaimer": "本分析由自动化系统基于 neodata 公开行情数据生成，仅供盘前参考，不构成任何投资建议。基金有风险，投资需谨慎；持仓数据为T0用户快照，操作决策请结合自身风险承受能力。"
}

out = os.path.join(BASE, "early-morning_%s.json" % DATE)
json.dump(data, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("wrote", out, "holdings:", len(holdings))
