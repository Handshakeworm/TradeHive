# TradeHive — 代码改动记录

> **基线（Baseline）**：原始 [TradingAgents](https://github.com/Handshakeworm/TradeHive) 仓库，仅支持通过 yfinance / Alpha Vantage 获取美股数据，不支持加密货币、宏观指标或情绪分析。
>
> 本文件记录从基线出发的所有代码改动，以证明项目是在原始代码基础上进行结构性修改，而非简单复制。

---

## 版本：v0.3.0 — 数据源扩展 + 新 Analyst Agent 接入

**改动日期**：2026-03-28  
**改动范围**：21 个文件（10 个修改 + 11 个新增）  
**改动摘要**：新增加密货币、宏观经济、情绪分析三类数据源及对应 Agent；修复 `main.py` 数据配置覆盖 Bug；补充 Parquet 本地缓存层

---

## 一、新增文件（11 个）

### 1.1 数据采集层（`tradingagents/dataflows/`）

| 文件 | 功能 | 原始代码中无此功能原因 |
|------|------|----------------------|
| `coingecko.py` | CoinGecko API：实时加密货币价格快照、市场总览；yfinance 作为历史 OHLCV 主力（`BTC-USD` 格式） | 原始版本无加密货币支持，仅有股票接口 |
| `fred_macro.py` | FRED API：16 个宏观系列（联邦基金利率 FEDFUNDS、CPI、失业率 UNRATE、VIX、10年期国债 GS10 等）；支持单指标查询和多指标快照 | 原始版本无宏观经济数据接口 |
| `sentiment_utils.py` | VADER 情绪评分：对 yfinance 新闻标题+摘要打 compound 分（-1 至 +1），可选接入 Reddit PRAW；结果写入 Parquet 缓存 | 原始版本无情绪分析数据层 |
| `local_cache.py` | Parquet 文件缓存：`save_dataframe()` / `load_dataframe()` / `get_cache_summary()`；路径结构 `data_cache/{category}/{symbol}/{start}_{end}.parquet`；供 RAP 向量库（Task 3）直接读取 | 原始版本无本地数据持久化机制 |

### 1.2 Agent 工具层（`tradingagents/agents/utils/`）

| 文件 | 包含 `@tool` 函数 | 说明 |
|------|-------------------|------|
| `crypto_tools.py` | `get_crypto_price`, `get_crypto_historical`, `get_crypto_market_overview` | LangChain tool 包装，内部调用 `route_to_vendor()` → `coingecko` 路由 |
| `macro_tools.py` | `get_macro_indicator`, `get_macro_snapshot`, `list_available_macro_series` | 路由 → `fred` |
| `sentiment_tools.py` | `get_news_sentiment`, `get_reddit_sentiment` | 路由 → `vader` |

### 1.3 Analyst Agent 层（`tradingagents/agents/analysts/`）

| 文件 | 写入 State 字段 | 绑定工具 | 加分依据 |
|------|----------------|----------|----------|
| `crypto_analyst.py` | `state["market_report"]` | `get_crypto_price/historical/overview`, `get_macro_snapshot` | 教授明确：**加密货币有加分** |
| `sentiment_analyst.py` | `state["sentiment_report"]` | `get_news`, `get_news_sentiment`, `get_reddit_sentiment` | 新增 Agent 角色加分 |
| `macro_analyst.py` | `state["news_report"]` | `get_macro_snapshot/indicator`, `list_available_macro_series` | 宏观事件预测 Agent 加分 |

---

## 二、修改的原有文件（10 个）

### 2.1 `tradingagents/dataflows/interface.py`

**原始**：仅有 `yfinance` / `alpha_vantage` 两个 vendor，`TOOLS_CATEGORIES` 只含 4 类，`VENDOR_METHODS` 只有股票相关函数。

**改动**（+72 行）：
- 新增 3 个 import 块（`coingecko`, `fred_macro`, `sentiment_utils`）
- `TOOLS_CATEGORIES` 新增 `crypto_data` / `macro_data` / `sentiment_data` 三个类别
- `VENDOR_LIST` 新增 `"coingecko"`, `"fred"`, `"vader"`
- `VENDOR_METHODS` 新增 8 个函数的 vendor 路由映射（替代硬编码调用）

### 2.2 `tradingagents/default_config.py`

**原始**：`data_vendors` 只有 4 个 key（core_stock_apis / technical_indicators / fundamental_data / news_data）。

**改动**（+9 行）：
- `data_vendors` 新增 3 个 key：`crypto_data: "coingecko"`, `macro_data: "fred"`, `sentiment_data: "vader"`
- 新增 `data_cache_enabled: True` 和 `data_cache_dir`（默认 `./data_cache`，可通过 `TRADEHIVE_CACHE_DIR` 环境变量覆盖）

### 2.3 `tradingagents/agents/__init__.py`

**原始**：只导出 4 个分析师 create 函数（market/social/news/fundamentals）。

**改动**（+8 行）：
- 新增 3 个 import：`create_sentiment_analyst`, `create_crypto_analyst`, `create_macro_analyst`
- `__all__` 列表中增加对应 3 个名称

### 2.4 `tradingagents/agents/utils/agent_utils.py`

**原始**：只导入原有 4 类工具函数。

**改动**（+15 行）：
- 新增 3 个 import 块（9 个工具函数），使新工具在整个 Agent 工具空间中可见

### 2.5 `tradingagents/graph/conditional_logic.py`

**原始**：`ConditionalLogic` 类只有 4 个 `should_continue_*` 方法（market/social/news/fundamentals）。

**改动**（+24 行，结构性扩展）：
- 新增 `should_continue_sentiment()` → 返回 `"tools_sentiment"` 或 `"Msg Clear Sentiment"`
- 新增 `should_continue_crypto()` → 返回 `"tools_crypto"` 或 `"Msg Clear Crypto"`
- 新增 `should_continue_macro()` → 返回 `"tools_macro"` 或 `"Msg Clear Macro"`
- 每个方法遵循与原有方法完全相同的模式，保持架构一致性

### 2.6 `tradingagents/graph/setup.py`

**原始**：`setup_graph()` 只处理 `"market"/"social"/"news"/"fundamentals"` 四种 analyst 类型。

**改动**（+22 行）：
- 新增 3 个 `if "xxx" in selected_analysts:` 分支，分别注册 sentiment / crypto / macro 的 analyst_node、delete_node、tool_node
- 与原有 4 种 analyst 的注册逻辑完全对称，零架构改动，纯扩展

### 2.7 `tradingagents/graph/trading_graph.py`

**原始**：`TradingAgentsGraph` 只导入原有工具函数，`_create_tool_nodes()` 只创建 4 个 ToolNode。

**改动**（+34 行）：
- import 段新增 9 个工具函数名
- `_create_tool_nodes()` 字典新增 `"sentiment"` / `"crypto"` / `"macro"` 三个 `ToolNode`，各自绑定对应工具列表

### 2.8 `main.py`

**原始**：`config["data_vendors"]` 赋值只含 4 个 key，直接覆盖了 `DEFAULT_CONFIG` 中新增的 crypto/macro/sentiment 配置（Bug）；`TradingAgentsGraph()` 调用没有显式传 `selected_analysts`。

**改动**（保持功能，修复 Bug）：
- `config["data_vendors"]` 补全全部 7 个 key，防止覆盖新增配置
- `TradingAgentsGraph()` 显式传入 `selected_analysts=["market", "social", "news", "fundamentals"]`
- 注释中新增加密货币和全量分析的使用示例（注释状态，不影响默认运行）
- 添加数据采集策略说明注释

### 2.9 `pyproject.toml`

**原始**：依赖列表无数据源新增包。

**改动**（+4 行）：
```
fredapi>=0.5.1        # FRED 宏观经济数据
vaderSentiment>=3.3.2 # VADER 情绪分析（纯离线）
pyarrow>=14.0.0       # Parquet 本地缓存
praw>=7.7.0           # Reddit API（可选）
```

### 2.10 `.env.example`

**原始**：只有 LLM Provider 的 API Key 占位符。

**改动**（+19 行）：新增数据源 API Key 说明和申请链接：
- `ALPHA_VANTAGE_API_KEY`（股票）
- `FRED_API_KEY`（宏观，必填才能用 macro analyst）
- `REDDIT_CLIENT_ID/SECRET/USER_AGENT`（可选，不填自动降级为新闻情绪）
- `TRADEHIVE_CACHE_DIR`（缓存目录，可选）

---

## 三、核心设计决策记录

### 为什么不直接修改原有 Analyst，而是新增？

原有 market/social/news/fundamentals 四个 analyst 使用独立 `selected_analysts` 参数控制是否启用，采用相同的 LangGraph 节点注册模式。新增 analyst 遵循相同模式，**零侵入原有节点逻辑**，不破坏原有 API。

### 为什么加密货币历史数据用 yfinance 而非仅 CoinGecko？

CoinGecko 免费 tier 的 `/market_chart/range` 端点需要认证，且 `/market_chart?days=N` 只能查最近 N 天。yfinance 的 `BTC-USD` 代码支持完整历史，CoinGecko 保留用于实时快照（无需 API Key 的实时端点免费可用）。

### 为什么用 Parquet 而非数据库？

项目以研究为主，Parquet 满足：① pandas 原生读写；② 列式存储节省空间；③ `#3 RAP 向量库` 直接 `pd.read_parquet()` 无需额外接口；④ 零依赖（pyarrow 已是必选依赖）。无需维护数据库连接和 schema 迁移。

---

## 四、安装与运行

```bash
# 1. 安装依赖（含新增包）
pip install -e .
pip install fredapi vaderSentiment pyarrow praw yfinance

# 2. 配置 API Keys
cp .env.example .env
# 填写 OPENAI_API_KEY（或 OPENROUTER_API_KEY）
# 可选：FRED_API_KEY（使用 macro analyst 时需要）

# 3. 运行 demo（NVDA 2024-05-10）
python main.py
```

---

## 历史 Commit 记录（原始仓库）

| Commit | 说明 |
|--------|------|
| `3f817c4` | Update .env.example（本次之前最后一次提交） |
| `d6505f4` | DEV_SPEC 改进，项目排期表建立 |
| `8b4272a` | 完善 baseline/single agent/multi agent 设计 |
| `57e23d2` | Initial commit（原始 TradingAgents 基线） |
