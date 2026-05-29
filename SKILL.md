---
name: national-team-position
description: 估计中国 A 股"国家队"(中央汇金)的宽基 ETF 持仓变动趋势——追踪上交所沪深300/上证50/中证500/中证1000/中证A500/科创50 的 ETF 份额变化,叠加各自指数走势,生成六合一总图与各指数单图。Estimates China's "national team" (Central Huijin) broad-base ETF positioning by tracking Shanghai Stock Exchange ETF share changes. Use when the user asks about 国家队持仓 / 国家队仓位 / 中央汇金持仓 / 国家队加仓 / 国家队减仓 / ETF份额变化 / 看看国家队 / national team holdings / Central Huijin positions.
license: MIT
---

# 国家队持仓估计（全宽基版）

通过追踪上交所核心宽基 ETF 的份额变化，估计国家队（中央汇金）的持仓变动与结构轮动，
并为每个宽基叠加其对应指数走势生成可视化图表。

当用户提到以下任何场景时必须触发：国家队持仓、国家队仓位、中央汇金持仓、ETF份额变化、
国家队加仓、国家队减仓、看看国家队、国家队最近在干嘛。

## 原理

- 中央汇金是宽基 ETF 的绝对控盘方，追踪 ETF **份额**（而非规模）可准确反映买卖行为
- 在沪深300 基础上覆盖全部上交所核心宽基，能区分「真减仓」与「换仓轮动」
- 数据来源：上海证券交易所官网 ETF 份额接口（AKShare `fund_etf_scale_sse`，一次返回当日全部 ETF）
  + AKShare 指数日线

## 覆盖的宽基指数

| 指数 | 代表 ETF | 价格 symbol | 信号干净度 |
|------|----------|-------------|------------|
| 沪深300 | 510300/510310/510330… | sh000300 | ⭐⭐⭐ 汇金绝对主力 |
| 上证50 | 510050/510710/510850… | sh000016 | ⭐⭐⭐ 护盘核心 |
| 中证500 | 510500/512500… | sh000905 | ⭐⭐ 含较多散户 |
| 中证1000 | 512100/560010 | sh000852 | ⭐⭐ 散户/对冲盘多 |
| 中证A500 | 名称含 "A500" 的全部 | sh000510 | ⭐⭐ 2024末新发，汇金基石 |
| 科创50 | 588000/588080… | sh000688 | ⭐ 散户/杠杆重，噪音大 |

> 创业板等 ETF 全在**深交所**，本接口取不到，未纳入。
> 科创50/中证500 散户底仓重，绝对值会高估"国家队持仓"，解读时建议参考增量（相对早期基线）。

## 依赖

```bash
pip install akshare matplotlib pandas
```

## 使用方式

```bash
# 默认：2024-01-01 至今，按周采样
python <skill-path>/scripts/national_team_position.py --output-dir ./

# 指定日期范围（推荐看 2023 至今，能完整覆盖建仓→轮动→撤离）
python <skill-path>/scripts/national_team_position.py --start 2023-01-01 --output-dir ./

# 仅获取数据不画图
python <skill-path>/scripts/national_team_position.py --data-only --output-dir ./
```

`<skill-path>` 替换为此 SKILL.md 所在目录的实际路径。

### 参数说明

| 参数 | 必填 | 说明 |
|------|------|------|
| `--start` | 否 | 起始日期，格式 YYYY-MM-DD，默认 2024-01-01 |
| `--end` | 否 | 结束日期，格式 YYYY-MM-DD，默认今天 |
| `--output-dir` | 否 | 输出目录，默认当前目录 |
| `--data-only` | 否 | 仅输出 JSON 数据，不画图 |
| `--freq` | 否 | 采样频率：weekly（默认）或 monthly |

### 输出文件

| 文件 | 说明 |
|------|------|
| `national_team_overview.png` | **六合一总图**（2x3，每格 = 该宽基份额 + 对应指数价格双轴） |
| `national_team_hs300.png` | 沪深300 单图（份额 + 指数价格双轴） |
| `national_team_sse50.png` | 上证50 单图 |
| `national_team_csi500.png` | 中证500 单图 |
| `national_team_csi1000.png` | 中证1000 单图 |
| `national_team_csiA500.png` | 中证A500 单图 |
| `national_team_star50.png` | 科创50 单图 |
| `national_team_position.json` | 各宽基份额时间序列 + 全宽基合计 JSON |

## 推荐工作流

1. 运行脚本获取数据并生成全部图表
2. 先发**总图**（national_team_overview.png）给用户，再按需发单图
3. 解读：各宽基的建仓/减仓时间点、份额变化量、与指数走势的对应关系；
   重点区分「真减仓」与「轮动换仓」（如沪深300 见顶后资金是否流向新发的 A500）
4. 如用户有后续问题，读取 JSON 做进一步分析（如增量口径、轮动窗口拆解）

## 注意事项

- 上交所 API 部分日期（节假日/周末）无数据，脚本会自动尝试前几个交易日
- AKShare 请求频率不宜过高，脚本内置间隔
- 首次运行较慢（按周采样 2-3 年约需 2-3 分钟，每个采样日仅 1 次份额接口调用）
- 图表使用中文字体，macOS 上使用 Arial Unicode MS / PingFang SC；Linux 需自备中文字体（如 Noto Sans CJK）
- 份额变化含非国家队的散户/机构申赎，尤其科创50/中证500/A500 噪音较大，结论需打折看趋势
- **本工具仅用于数据可视化与研究，不构成任何投资建议**
