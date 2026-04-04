# TradeHive — 功能改动记录

> **基线（Baseline）**：原始 [TradingAgents](https://github.com/Handshakeworm/TradeHive) 仓库，仅支持通过 yfinance / Alpha Vantage 获取美股数据，不支持加密货币、宏观指标或情绪分析。
>
> 本文件记录从基线出发的所有功能模块新增与调整，以证明项目是在原始代码基础上进行结构性修改，而非简单复制。

---

## 版本：v0.3.0 — 数据源扩展 + 新 Analyst Agent 接入

**改动日期**：2026-03-28  
**改动摘要**：新增加密货币、宏观经济、情绪分析三类数据源及对应 Analyst Agent；修复数据配置覆盖 Bug；新增 Parquet 本地缓存层

---

## 一、新增功能模块

### 1.1 加密货币数据支持

**基线缺失**：原始版本只支持美股数据，无任何加密货币接口。

**新增内容**：
- 接入 CoinGecko API，支持实时加密货币价格快照与市场总览
- 历史 OHLCV 数据通过 yfinance（`BTC-USD` 格式）获取，保证完整历史覆盖
- 新增 **Crypto Analyst Agent**，可自主调用加密货币数据工具，生成市场分析报告

### 1.2 宏观经济数据支持

**基线缺失**：原始版本无任何宏观经济数据接入。

**新增内容**：
- 接入 FRED（美联储经济数据库）API，覆盖联邦基金利率、CPI、失业率、VIX、10年期国债收益率等 16 个核心宏观系列
- 支持单指标历史序列查询和多指标快照两种模式
- 新增 **Macro Analyst Agent**，负责从宏观角度分析市场环境，辅助交易决策

### 1.3 情绪分析支持

**基线缺失**：原始版本无结构化情绪评分机制。

**新增内容**：
- 集成 VADER 情绪分析模型，对 yfinance 抓取的新闻标题和摘要进行离线情绪评分（-1 至 +1）
- 可选接入 Reddit PRAW，获取社交媒体情绪；若未配置则自动降级为新闻情绪
- 新增 **Sentiment Analyst Agent**，输出结构化情绪报告供交易图使用

### 1.4 本地数据缓存层

**基线缺失**：原始版本每次运行均重新调用 API，无任何数据持久化机制。

**新增内容**：
- 新增基于 Parquet 格式的文件缓存模块，数据首次获取后写入本地，后续直接读取缓存
- 统一缓存路径结构：`data_cache/{category}/{symbol}/{start}_{end}.parquet`
- 缓存数据可直接供 RAP 向量库（Task 3）复用，无需重复采集

---

## 二、调整的原有功能模块

### 2.1 数据路由层扩展

**调整前**：数据路由仅支持 `yfinance` 和 `alpha_vantage` 两个数据源，只有股票相关类别。

**调整后**：新增 `coingecko`、`fred`、`vader` 三个数据源及对应路由类别（`crypto_data` / `macro_data` / `sentiment_data`），新工具函数通过统一路由机制调用，与原有机制完全兼容。

### 2.2 默认配置扩展

**调整前**：`data_vendors` 配置只涵盖股票相关数据源，无缓存配置项。

**调整后**：配置新增加密货币、宏观、情绪三类数据源的默认 vendor 指定，以及本地缓存开关和缓存目录配置（支持通过环境变量覆盖）。

### 2.3 Agent 图扩展

**调整前**：LangGraph 交易图只支持注册 market / social / news / fundamentals 四种 Analyst 节点。

**调整后**：图注册逻辑新增对 sentiment / crypto / macro 三类 Analyst 的支持，与原有四种 Analyst 完全对称，通过 `selected_analysts` 参数按需启用，不影响原有默认流程。

### 2.4 入口配置修复

**调整前**：`main.py` 中对 `data_vendors` 的赋值会覆盖配置中新增的数据源字段，导致新功能失效（Bug）。

**调整后**：修复覆盖问题，确保所有数据源配置完整保留；新增加密货币分析和全量 Analyst 的示例用法（注释形式，不影响默认运行）。

### 2.5 依赖与环境配置

**调整前**：项目依赖中不包含新数据源所需包；`.env.example` 只有 LLM 的 API Key 占位符。

**调整后**：
- 新增四个依赖包：`fredapi`（宏观数据）、`vaderSentiment`（情绪分析）、`pyarrow`（Parquet 缓存）、`praw`（Reddit，可选）
- `.env.example` 补充 FRED、Reddit 等数据源的 API Key 说明及申请链接，方便团队成员配置

---

## 三、设计决策说明

### 为什么新增 Analyst Agent 而不修改原有 Agent？

原有四个 Analyst 已有稳定的调用接口和节点注册逻辑。新增独立 Agent 可按需启用，不破坏已有流程，符合开闭原则。

### 为什么加密货币历史数据用 yfinance 而非仅 CoinGecko？

CoinGecko 免费接口获取完整历史数据有限制，yfinance 的 `BTC-USD` 格式支持任意时间段历史数据，稳定性更好。CoinGecko 保留用于实时快照场景。

### 为什么用 Parquet 文件缓存而非数据库？

项目以研究为主，Parquet 格式轻量、零服务依赖，pandas 原生读写，且可直接供 RAP 向量库使用，无需额外接口转换。

---

## 四、安装与运行

```bash
# 1. 安装依赖（含新增包）
pip install -e .
pip install fredapi vaderSentiment pyarrow praw yfinance

# 2. 配置 API Keys
cp .env.example .env
# 填写 OPENAI_API_KEY（或 OPENROUTER_API_KEY）
# 可选：FRED_API_KEY（使用宏观分析师时需要）

# 3. 运行 demo（NVDA 2024-05-10）
python main.py
```

---

---

## 版本：v0.3.1 — Tools 暴露机制修复

**改动日期**：2026-04-03  
**改动摘要**：审查多 Agent 系统 tools 暴露规则，修复 LLM bind_tools 与 Graph ToolNode 不对齐问题，补全 News Analyst 工具能力

---

### 修复内容

#### 1. News Analyst 工具层不对齐（已修复）

**问题**：`get_insider_transactions` 在 Graph ToolNode（`trading_graph.py`）中已注册到 `tools_news` 节点，但 News Analyst（`news_analyst.py`）的 `llm.bind_tools()` 未包含该工具。LLM 不知道此工具存在，导致内幕交易数据在整个系统中从未被任何 Agent 实际调用。

**修复**：
- `news_analyst.py`：import 中新增 `get_insider_transactions`，tools 列表从 2 个补全为 3 个
- 修复后 LLM bind_tools 与 ToolNode 完全对齐：`get_news`、`get_global_news`、`get_insider_transactions`

**涉及文件**：`tradingagents/agents/analysts/news_analyst.py`


---

## 版本：v0.4.0 — 移除 Sentiment Analyst 节点

**改动日期**：2026-04-04  
**改动摘要**：移除 Sentiment Analyst Agent 节点及其全部图注册、工具绑定、条件路由逻辑，精简分析师管线

---

### 移除内容

#### Sentiment Analyst 节点完整移除

**移除原因**：精简 Agent 管线，去除冗余分析节点。

**涉及文件与改动**：

| 文件 | 操作 |
|------|------|
| `tradingagents/agents/analysts/sentiment_analyst.py` | **删除**（整个文件） |
| `tradingagents/agents/__init__.py` | 移除 `create_sentiment_analyst` 的 import 及 `__all__` 导出 |
| `tradingagents/graph/conditional_logic.py` | 移除 `should_continue_sentiment()` 条件路由方法 |
| `tradingagents/graph/setup.py` | 移除 `if "sentiment" in selected_analysts` 节点创建块 |
| `tradingagents/graph/trading_graph.py` | 移除 `"sentiment"` ToolNode 及 `get_news_sentiment`/`get_reddit_sentiment` import |
| `main.py` | 移除注释示例中的 `"sentiment"` 选项 |

**未受影响**：
- `sentiment_report` 字段保留于 `AgentState`，由 `propagation.py` 初始化为空字符串，下游节点正常兼容
- `sentiment_utils.py` 数据工具模块保留，可供其他模块复用
- `cli/main.py` 中 `sentiment_report` 的显示逻辑绑定于 Social Analyst，不受影响
- 图的前后节点由 `setup.py` 循环自动连接，移除后无需手动补边







---

## 版本：v0.4.1 — Social Media Analyst 改名为 Sentiment Analyst

**改动日期**：2026-04-04  
**改动摘要**：将 Social Media Analyst 节点统一改名为 Sentiment Analyst，同步更新图注册 key、条件路由、状态字段、CLI 映射等全部引用；功能与 prompt 保持不变

---

### 改名映射

| 项目 | 旧值 | 新值 |
|------|------|------|
| 文件名 | `social_media_analyst.py` | `sentiment_analyst.py` |
| 工厂函数 | `create_social_media_analyst()` | `create_sentiment_analyst()` |
| 图 key / `selected_analysts` | `"social"` | `"sentiment"` |
| 条件路由方法 | `should_continue_social()` | `should_continue_sentiment()` |
| 图节点名 | `Social Analyst` / `Msg Clear Social` / `tools_social` | `Sentiment Analyst` / `Msg Clear Sentiment` / `tools_sentiment` |
| 输出状态字段 | `community_report` | `sentiment_report` |
| CLI 枚举 | `AnalystType.SOCIAL` | `AnalystType.SENTIMENT` |

### 涉及文件

| 文件 | 操作 |
|------|------|
| `tradingagents/agents/analysts/sentiment_analyst.py` | 由 `social_media_analyst.py` 重命名；函数名 + 输出字段更新 |
| `tradingagents/agents/__init__.py` | import 路径及 `__all__` 导出更新 |
| `tradingagents/graph/conditional_logic.py` | `should_continue_social` → `should_continue_sentiment` |
| `tradingagents/graph/setup.py` | 所有 `"social"` → `"sentiment"`；默认列表及文档注释同步 |
| `tradingagents/graph/trading_graph.py` | 默认 `selected_analysts` 及 ToolNode key 更新 |
| `tradingagents/agents/utils/agent_states.py` | 移除 `community_report` 字段（不再需要） |
| `tradingagents/agents/researchers/bull_researcher.py` | 移除 `community_report` 读取与拼接 |
| `tradingagents/agents/researchers/bear_researcher.py` | 同上 |
| `tradingagents/agents/trader/trader.py` | 同上 |
| `tradingagents/agents/risk_mgmt/aggressive_debator.py` | 同上 |
| `tradingagents/agents/risk_mgmt/neutral_debator.py` | 同上 |
| `tradingagents/agents/risk_mgmt/conservative_debator.py` | 同上 |
| `main.py` | `selected_analysts` 列表中 `"social"` → `"sentiment"` |
| `cli/models.py` | `SOCIAL` → `SENTIMENT` |
| `cli/main.py` | 所有 `"social"` key 及 `"Social Analyst"` 显示名更新 |

### 说明

- **功能不变**：Agent 的 system prompt、工具绑定（`get_news`）、分析逻辑完全不变，仅改名
- **输出字段合并**：原 `community_report`（仅 social media analyst 写入）合并到已有的 `sentiment_report`，下游 8 个节点原本就直接读取 `sentiment_report`，无需改动
- **`propagation.py` 无需修改**：`sentiment_report` 已在初始状态中初始化为空字符串


## 五、历史 Commit 记录

| Commit | 说明 |
|--------|------|
| `ac43f63` | Update .env.example（本次之前最后一次提交） |
| `d6505f4` | DEV_SPEC 改进，项目排期表建立 |
| `8b4272a` | 完善 baseline/single agent/multi agent 设计 |
| `57e23d2` | Initial commit（原始 TradingAgents 基线） |




