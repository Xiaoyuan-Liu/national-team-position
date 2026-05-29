# national-team-position · 国家队持仓估计

一个 [Claude Code](https://claude.com/claude-code) Agent Skill：通过追踪上交所核心**宽基 ETF 份额**变化，估计中国 A 股「国家队」（中央汇金）的持仓变动与结构轮动，并生成可视化图表。

> A Claude Code Agent Skill that estimates China's "national team" (Central Huijin) broad-base ETF positioning by tracking Shanghai Stock Exchange ETF share changes, and renders charts.

## 它能做什么

- 覆盖六大上交所宽基：**沪深300 / 上证50 / 中证500 / 中证1000 / 中证A500 / 科创50**
- 追踪 ETF **份额**（而非规模，已排除价格涨跌干扰），更真实地反映净买卖行为
- 输出一张**六合一总图** + 六张**各指数单图**（每张 = 该宽基份额 + 对应指数价格双轴）+ JSON 数据
- 能区分「真减仓」与「换仓轮动」（例如沪深300 见顶后资金是否流向新发的中证A500）

### 示例输出

![六合一总图：各宽基 ETF 份额 vs 对应指数走势](assets/overview.png)

> 上图为 2023 至今的六合一总图：每格的彩色线是该宽基的 ETF 份额（左轴，估计国家队持仓），灰线是对应指数价格（右轴）。

| 文件 | 内容 |
|------|------|
| `national_team_overview.png` | 六合一总图（2×3） |
| `national_team_hs300/sse50/csi500/csi1000/csiA500/star50.png` | 各指数单图 |
| `national_team_position.json` | 各宽基份额时间序列 + 全宽基合计 |

## 安装

本仓库即一个独立 skill，直接克隆到 Claude Code 的 skills 目录：

```bash
git clone https://github.com/Xiaoyuan-Liu/national-team-position.git \
  ~/.claude/skills/national-team-position
```

安装依赖：

```bash
pip install akshare matplotlib pandas
```

> macOS 自带中文字体；Linux 需自备中文字体（如 `fonts-noto-cjk`），否则图中中文会显示为方块。

## 使用

在 Claude Code 中直接说「**看看国家队持仓**」「**国家队最近在加仓还是减仓**」即可自动触发，
或手动执行脚本：

```bash
# 推荐看 2023 至今，完整覆盖「建仓 → 轮动 → 撤离」
python ~/.claude/skills/national-team-position/scripts/national_team_position.py \
  --start 2023-01-01 --output-dir ./
```

| 参数 | 说明 |
|------|------|
| `--start` / `--end` | 日期范围 `YYYY-MM-DD`，默认 2024-01-01 ~ 今天 |
| `--output-dir` | 输出目录，默认当前目录 |
| `--freq` | 采样频率 `weekly`（默认）/ `monthly` |
| `--data-only` | 仅输出 JSON，不画图 |

## 原理

中央汇金是宽基 ETF 的绝对控盘方，其申赎会直接体现在 ETF **份额**上。脚本按周（或按月）从
上交所 ETF 份额接口（经 [AKShare](https://github.com/akfamily/akshare) 封装的 `fund_etf_scale_sse`，
一次调用即返回当日全部 ETF）采样各宽基份额，并叠加各指数日线走势。

## 局限与免责声明

- 创业板等 ETF 全在**深交所**，本数据源取不到，未纳入。
- 份额变化含非国家队的散户/机构申赎，**科创50 / 中证500 / 中证A500 噪音较大**，绝对值会高估国家队持仓，建议结合增量口径看趋势。
- 上交所接口在节假日/周末无数据，脚本会自动回退到前几个交易日。
- **本工具仅用于数据可视化与研究，不构成任何投资建议。**

## License

[MIT](LICENSE)
