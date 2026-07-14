# 自动化共享配置 · automation_config.md
> 所有自动化任务 prompt 引用此文件，消除重复。
> 修改一处，所有任务自动生效。

---

## 1. 固定路径（所有任务通用）

| 用途 | 路径 |
|------|------|
| 项目根 | `C:/Users/LEGION/Nutstore/1/daily-report` |
| 持仓配置 | `{project}/config/watchlist.json` |
| 数据协议 | `{project}/data/{credibility,sentiment,kline}-protocol.md` |
| 共享渲染库 | `{project}/data/render_utils.py`（含 RULES 常量字典：阈值/权重/风控） |
| 脚本目录 | `{project}/scripts/` |
| 产出目录 | `{project}/data/reports/{今天YYYY-MM-DD}/` |
| 收件箱首页 | `{project}/index.html` |
| Python | `C:/Users/LEGION/.workbuddy/binaries/python/versions/3.13.12/python.exe` |
| 数据源 | `neodata-financial-search`（`connect_cloud_service` + `python3`） |

## 2. 性能铁律（所有分析任务通用）

```
所有数据抓取**并行批量**：同一条消息一次性发起全部 neodata 查询，禁止串行。
硬时限：早报 20min / 午盘 15min / 尾盘 12min / 复盘 25min / 大盘研判 30min
模型已关思考链，勿主动长篇推理。
报告由生成器渲染(见上面路径)，agent 只负责分析+落盘 JSON。
```

## 3. 风控硬约束（引用 render_utils.RULES）

| 约束 | 值 |
|------|-----|
| 单基金仓位上限 | `max_single_position_pct` = 30%（RULES.pos_max_single） |
| 总仓位上限 | `target_total_position_pct` = 90%（RULES.total_pos_max） |
| 强制止损 | `stop_loss_pct` = -8%（RULES.stop_loss_pct） |
| 止盈线 | `take_profit_pct` = 15% |
| 半导体集中度警告 | ≥ 60%（RULES.semic_concentration） |
| 单日跌幅强风险 | ≥ 3%（RULES.sector_drop_alert） |

## 4. 数据可信度等级（credibility-protocol.md）

| 等级 | 来源 | 用途 |
|------|------|------|
| T0 | 用户持仓/养基宝穿透 | 持仓净值/收益（不可更改） |
| T1 | 交易所/基金官网 | 官方净值披露 |
| T2 | 东财/新浪/雪球（双源验证） | 大盘/板块行情 |
| T3 | 自媒体/AI 生成 | 仅情绪参考，禁入决策 |

## 5. 色板约定（涨红跌绿）

```
--up:#f5564d(红涨) --down:#26c281(绿跌) --neu:#d9a441(橙中性)
信号等级(独立轴)：多=绿系 / 空=红系 / 强度:强=红·中=橙·弱=灰
操作标签：持有=绿 / 减仓=红 / 警惕=橙 / 观望=蓝
风险标签：高=红 / 中=橙 / 低=黄
```

## 6. 生成器调用模板

```python
# 分析完毕后用 python3 渲染 HTML
import subprocess
subprocess.run([
    "{python}",
    "{project}/data/make_<类型>_html.py",  # morning/midday/tail/market/alert
    "<YYYY-MM-DD>"
])
```

## 7. 因子回测后置任务（尾盘决策专用）

尾盘报告渲染完成后，自动触发因子入库+权重迭代：
```
python3 data/factor_backtest.py <YYYY-MM-DD>
```

| 输出文件 | 说明 |
|---------|------|
| `data/factor_log.json` | 时序因子日志（永久保留，IC/ICIR/权重历史） |
| `data/factor_weights.json` | 当前因子权重（每日自动迭代） |

权重迭代规则：ICIR前2因子+5%/后2因子-5%，归一化到[5%,50%]区间。
因子回测表自动嵌入尾盘HTML报告尾部。
