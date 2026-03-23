# 教授的建议
Bonus points will be given to teams that employ
：
• New Agent Role: e.g., a macroeconomic events predictor using macro releases.
• Roll-forward Validation: optimize rolling windows to minimize overfitting.
• Retrieval Augmented Prompts: inject structured external data (via vector store).
• Multi-Asset Portfolio: extend TradingAgents to handle portfolios, not just single 
tickers.
• Crypto Market: extend TradingAgents to trade crypto assets
# 光神ideas
调试

LLM先从gpt-5.2变为使用ollama

但ollama官方llama3不支持toolss，所以要先拉取支持tools的模型：llama3-groq-tool-use

但这个模型需要很大的本地可用内存，所以要切换到小内存版的tools模型：functiongemma:270m但推理能力和财经理解有限，无法给出投资建议或深入分析，只能做基础数据查询。

更强的推理和财经分析能力，建议升级硬件，拉取更大参数的 tools 支持模型（如 granite3.1-moe:tools-1b、qwen2.5:tools-1.5b 等 granite3.1-moe:1b

NVDA 2024-05-10 可以但不必要换用其他的日期区间（如近几天或2024年初），或换用其它主流美股代码（如 AAPL、MSFT：yf.download('AAPL', period='5d')）。

总结一下，现在添加的technical analyst遵循的是什么逻辑，会比baseline多输出？
新的数据资源
-	从 yfinance 换成 Alpha Vantage、Tiingo、Polygon、新浪财经
-	集成其它市场（如港股、A股、加密货币等）的数据接口
-	增加新的信息类型（如 alternative data、社交媒体情绪、宏观经济指标

可替代的模型
-	Llama3-groq-tool-use
-	Functiongemma:270m
-	granite3.1-moe:1b

Baseline tradingagents framework from github：

TradingAgents 框架在本地 LLM（如 granite3.1-moe:1b）和当前配置下的“baseline”表现。它代表了在未做任何自定义 agent 角色扩展、未集成新数据源、未调整回测逻辑等情况下，系统的基础推理和分析能力。

新增technical analyst agent
Technical_analyst.py
还可以基于此进一步自定义technical analyst 的分析逻辑
当前版本：
1.	technical analyst 逻辑
-	新增的 technical analyst agent 只关注技术面分析（如均线、MACD、RSI、布林带等），不考虑基本面或新闻。
-	它会优先调用 get_stock_data 和 get_indicators 工具，获取股票的历史价格和技术指标数据。
-	基于这些技术指标，technical analyst 会输出自己的分析结论（如趋势判断、买卖建议），并给出简明理由。
2.	比 baseline 多输出什么
●	baseline 只包含 market、social、news、fundamentals 等原有 agent 的分析内容。
●	新版本会在分析流程最前面增加 technical analyst 的分析输出，内容包括：
○	 技术指标的调用和解读（如“当前为上升趋势，建议BUY”或“波动大，建议SELL”）。
○	 只基于技术面，不受新闻、基本面等影响。
●	会在完整分析报告中看到 technical analyst 的独立分析段落，后面才是其他 agent 的内容。
后续输出的分析内容会被存储到一个单独的文件夹当中。



新增sentiment agent
1.	sentiment agent 遵循的逻辑如下：
●	在 TradingAgentsGraph 的 selected_analysts 列表中新增了 "sentiment"，即分析链路会多经过 sentiment agent。
●	sentiment agent 会独立调用 LLM，对目标股票的新闻、社交等数据进行情绪面分析，输出情绪分数（正面/中性/负面）及简要解释。
●	其实现方式与 technical、market 等 analyst 类似，作为一个独立节点插入分析流程。
2.	比 baseline 多的输出：
●	baseline 只包含 market、social、news、fundamentals 等分析结果。
●	现在的版本会在分析文档和终端输出中，额外包含一段“情绪面分析”结果（如情绪分数和解释），便于对比不同 agent 的贡献和效果。

新增risk manager agent
tradingagents/agents/managers/risk_manager.py（包含 create_risk_manager 函数）已经有了，只是没放入到main.py中运行而已


# 我的ideas
1. 加入skills管理提示词

2. 应用rag建立向量库（有使用BM25,无稠密向量检索，无重排步骤）

3. 上下文管理探究/明确

4. 数据流结构化保证（注意是否会限制大模型能力）：提示词few-shot，使用tool提前定义硬限制，最后兜底机制检查验证

5. 使用能力强的大模型，规划阶段使用最高推理强度，简单部分/执行部分可以使用次级模型节省推理成本或用高推理强度，查验审查时再使用最高推理强度（推理三明治）保证不超时的同时，效果也可以更好

6. 在各个环节注意中间件设计，确保大模型

7. 现有tool审查，如不冗余无需删除，可以实验性加入更多

8. agent自验证循环探究改进：
如何避免死循环：中间件是否跟踪了文件编辑次数，超过阈值则提醒重新审视？
如何避免跳过验证：中间件强制执行玩这个验证

9. 上下文隔离
子agent作为上下文防火墙，父agent只看到给出的指令，和子agent返回的结果，中间所有产物和调用都隔离

10. 熵治理：引入后台运行的文档梳理agent，避免长时间运行文档过失，架构飘逸，知识库和代码不一致问题，定期扫描过时文档并提交修复

11. 所有都需要A/B test








# TradeHive - 开发者文档

> **版本**: v0.2.2
> **生成日期**: 2026-03-23
> **项目名称**: TradingAgents (TradeHive)
> **定位**: 基于多智能体 LLM 的金融交易决策框架

---

## 1. 项目概述

TradeHive 是一个模拟真实交易公司组织架构的多智能体系统。系统通过部署多个具有专业分工的 LLM 智能体，协作完成市场数据收集、分析辩论、风险评估，最终输出交易决策信号。

**核心技术栈**:
- **编排引擎**: LangGraph (状态图工作流)
- **LLM 集成**: LangChain (OpenAI / Anthropic / Google / xAI / OpenRouter / Ollama)
- **数据源**: yfinance (默认) / Alpha Vantage (备选)
- **记忆系统**: BM25 词汇相似度匹配 (rank-bm25)
- **CLI**: Typer + Rich + Questionary

---

## 2. 系统架构

### 2.1 分层架构图

```
┌──────────────────────────────────────────────────────┐
│                    CLI 层 (cli/)                       │
│        用户交互 · 参数配置 · 实时状态展示               │
├──────────────────────────────────────────────────────┤
│                  图编排层 (graph/)                      │
│     LangGraph StateGraph · 条件路由 · 状态传播          │
├──────────────────────────────────────────────────────┤
│                  智能体层 (agents/)                     │
│   分析师 · 研究员 · 交易员 · 风控辩论员 · 管理者        │
├──────────────────────────────────────────────────────┤
│                  工具层 (agents/utils/)                 │
│    股票数据 · 技术指标 · 基本面 · 新闻 · 记忆系统       │
├──────────────────────────────────────────────────────┤
│                 数据流层 (dataflows/)                   │
│     接口路由 · yfinance · Alpha Vantage · stockstats   │
├──────────────────────────────────────────────────────┤
│                LLM 客户端层 (llm_clients/)              │
│   OpenAI · Anthropic · Google · xAI · OpenRouter       │
└──────────────────────────────────────────────────────┘
```

### 2.2 目录结构

```
TradeHive/
├── main.py                          # 程序化调用入口示例
├── test.py                          # 数据获取测试
├── pyproject.toml                   # 包元数据与依赖
├── .env.example                     # 环境变量模板
│
├── cli/                             # CLI 交互层
│   ├── main.py                      # Typer 应用主入口 (含 MessageBuffer)
│   ├── utils.py                     # 输入辅助 (ticker/日期/分析师/模型选择)
│   ├── models.py                    # 数据模型 (AnalystType 枚举)
│   ├── config.py                    # CLI 配置 (公告 URL 等)
│   ├── stats_handler.py             # LangChain 回调统计处理器
│   ├── announcements.py             # 公告展示 (从 api.tauric.ai 获取)
│   └── static/welcome.txt           # 欢迎界面 ASCII Art
│
├── tradingagents/                   # 核心框架
│   ├── __init__.py                  # 设置 PYTHONUTF8=1 环境变量
│   ├── default_config.py            # 默认配置字典
│   │
│   ├── graph/                       # 图编排引擎
│   │   ├── trading_graph.py         # 主编排器 TradingAgentsGraph
│   │   ├── setup.py                 # GraphSetup - 图构建
│   │   ├── conditional_logic.py     # 条件路由逻辑
│   │   ├── propagation.py           # 状态初始化/传播
│   │   ├── reflection.py            # 决策反思与学习
│   │   └── signal_processing.py     # 输出信号提取
│   │
│   ├── agents/                      # 智能体定义
│   │   ├── __init__.py              # 统一导出所有 create_* 工厂函数
│   │   ├── analysts/                # 分析师 (数据收集)
│   │   │   ├── market_analyst.py    # 市场/技术分析
│   │   │   ├── social_media_analyst.py  # 社交媒体情感分析
│   │   │   ├── news_analyst.py      # 全球宏观新闻分析
│   │   │   └── fundamentals_analyst.py  # 基本面分析
│   │   │
│   │   ├── researchers/             # 研究员 (辩论)
│   │   │   ├── bull_researcher.py   # 看多研究员
│   │   │   └── bear_researcher.py   # 看空研究员
│   │   │
│   │   ├── trader/                  # 交易员
│   │   │   └── trader.py            # 生成投资计划
│   │   │
│   │   ├── risk_mgmt/              # 风险管理辩论
│   │   │   ├── aggressive_debator.py    # 激进派
│   │   │   ├── conservative_debator.py  # 保守派
│   │   │   └── neutral_debator.py       # 中立派
│   │   │
│   │   ├── managers/               # 管理者 (决策者)
│   │   │   ├── research_manager.py  # 研究经理 (裁判 Bull/Bear)
│   │   │   └── portfolio_manager.py # 投资组合经理 (最终决策)
│   │   │
│   │   └── utils/                  # 工具与辅助
│   │       ├── agent_states.py     # 状态定义 (AgentState 等)
│   │       ├── agent_utils.py      # 工具导入汇总 + build_instrument_context + create_msg_delete
│   │       ├── core_stock_tools.py # 股票数据工具
│   │       ├── technical_indicators_tools.py  # 技术指标工具
│   │       ├── fundamental_data_tools.py      # 基本面数据工具
│   │       ├── news_data_tools.py             # 新闻数据工具
│   │       └── memory.py           # BM25 记忆系统
│   │
│   ├── dataflows/                  # 数据访问层
│   │   ├── interface.py            # 统一路由接口 (route_to_vendor)
│   │   ├── config.py               # 数据源配置管理 (get_config/set_config)
│   │   ├── y_finance.py            # yfinance 实现
│   │   ├── yfinance_news.py        # yfinance 新闻
│   │   ├── alpha_vantage.py        # Alpha Vantage 入口
│   │   ├── alpha_vantage_common.py # AV 公共工具 + AlphaVantageRateLimitError
│   │   ├── alpha_vantage_stock.py  # AV 股票数据
│   │   ├── alpha_vantage_indicator.py  # AV 技术指标
│   │   ├── alpha_vantage_fundamentals.py  # AV 基本面
│   │   ├── alpha_vantage_news.py   # AV 新闻
│   │   ├── stockstats_utils.py     # 技术指标计算 (stockstats)
│   │   └── utils.py                # 数据工具函数
│   │
│   └── llm_clients/                # LLM 客户端抽象
│       ├── base_client.py          # 抽象基类 BaseLLMClient + normalize_content()
│       ├── factory.py              # 工厂函数 create_llm_client()
│       ├── openai_client.py        # OpenAI/xAI/OpenRouter/Ollama + NormalizedChatOpenAI
│       ├── anthropic_client.py     # Claude 系列 + NormalizedChatAnthropic
│       ├── google_client.py        # Gemini 系列 + NormalizedChatGoogleGenerativeAI
│       └── validators.py           # 模型名称验证
│
└── tests/
    └── test_ticker_symbol_handling.py  # Ticker 符号处理测试
```

---

## 3. 核心工作流

### 3.1 完整执行流程

> **重要**: 分析师阶段为**串行执行** (按 `selected_analysts` 列表顺序依次执行)，而非并行。
> 每个分析师完成后，其消息会被清除 (`create_msg_delete`) 再传递给下一个分析师。

```
用户输入 (Ticker + 日期)
        │
        ▼
┌──────────────────────────────────────────────────┐
│            第一阶段: 数据分析 (串行)               │
│                                                  │
│  市场分析师 ──► [工具调用循环] ──► 消息清除         │
│       │                                          │
│       ▼                                          │
│  社交媒体分析师 ──► [工具调用循环] ──► 消息清除     │
│       │                                          │
│       ▼                                          │
│  新闻分析师 ──► [工具调用循环] ──► 消息清除         │
│       │                                          │
│       ▼                                          │
│  基本面分析师 ──► [工具调用循环] ──► 消息清除       │
│       │                                          │
│       ▼                                          │
│  各分析师报告写入 AgentState 对应字段               │
└──────────────────┬───────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────┐
│          第二阶段: 投资研究辩论                     │
│                                                  │
│  ┌────────────┐   ┌────────────┐                │
│  │ 看多研究员  │◄─►│ 看空研究员  │                │
│  │ (Bull)      │   │ (Bear)     │                │
│  └──────┬──────┘   └──────┬─────┘                │
│         └────────┬────────┘                      │
│    (循环 count < 2 * max_debate_rounds)           │
│                  ▼                               │
│  ┌──────────────────────────────┐                │
│  │ 研究经理 (Research Manager)   │                │
│  │ → 裁决: BUY / HOLD / SELL    │                │
│  └──────────────┬───────────────┘                │
└─────────────────┬────────────────────────────────┘
                  │
                  ▼
┌──────────────────────────────────────────────────┐
│            第三阶段: 交易计划                      │
│                                                  │
│  ┌──────────────────────────────┐                │
│  │ 交易员 (Trader)               │                │
│  │ → 生成具体投资计划            │                │
│  └──────────────┬───────────────┘                │
└─────────────────┬────────────────────────────────┘
                  │
                  ▼
┌──────────────────────────────────────────────────┐
│          第四阶段: 风险管理辩论                     │
│                                                  │
│  激进派 ──► 保守派 ──► 中立派 ──► (循环)          │
│  (循环 count < 3 * max_risk_discuss_rounds)       │
│                  ▼                               │
│  ┌──────────────────────────────┐                │
│  │ 投资组合经理 (Portfolio Mgr)  │                │
│  │ → 最终决策 (五级评级)         │                │
│  └──────────────┬───────────────┘                │
└─────────────────┬────────────────────────────────┘
                  │
                  ▼
┌──────────────────────────────────────────────────┐
│              信号处理与输出                        │
│                                                  │
│   BUY │ OVERWEIGHT │ HOLD │ UNDERWEIGHT │ SELL   │
└──────────────────────────────────────────────────┘
```

### 3.2 辩论机制

系统包含两轮结构化辩论:

**投资辩论 (Bull vs Bear)**:
1. 看多研究员基于分析报告 + 历史记忆，提出看多论点
2. 看空研究员基于分析报告 + 历史记忆，提出看空论点
3. 双方轮流辩论，终止条件: `count >= 2 * max_debate_rounds` (每人发言一次计 count+1)
4. 研究经理 (Deep Thinking LLM) 综合评估，做出 BUY/HOLD/SELL 裁决

**风险辩论 (Aggressive vs Conservative vs Neutral)**:
1. 三方分别从不同风险偏好角度评估交易计划
2. 轮流发言顺序: Aggressive → Conservative → Neutral → 循环
3. 终止条件: `count >= 3 * max_risk_discuss_rounds` (三人各发言一次计 count+3)
4. 投资组合经理 (Deep Thinking LLM) 综合评估，输出五级评级

### 3.3 消息清除机制

每个分析师完成后, `create_msg_delete()` 会:
1. 删除 messages 列表中所有消息 (通过 `RemoveMessage`)
2. 添加一条 `HumanMessage(content="Continue")` 占位消息 (Anthropic 兼容性要求)

这确保下一个分析师从干净的消息历史开始, 只通过 AgentState 的报告字段传递数据。

---

## 4. 状态管理

### 4.1 AgentState (主状态)

```python
class AgentState(MessagesState):
    """继承自 LangGraph 的 MessagesState (自带 messages 字段)"""
    company_of_interest: Annotated[str, "Company that we are interested in trading"]
    trade_date: Annotated[str, "What date we are trading at"]

    sender: Annotated[str, "Agent that sent this message"]

    # 分析师报告
    market_report: Annotated[str, "Report from the Market Analyst"]
    sentiment_report: Annotated[str, "Report from the Social Media Analyst"]
    news_report: Annotated[str, "Report from the News Researcher"]
    fundamentals_report: Annotated[str, "Report from the Fundamentals Researcher"]

    # 投资决策链
    investment_debate_state: Annotated[InvestDebateState, "..."]
    investment_plan: Annotated[str, "Plan generated by the Analyst"]
    trader_investment_plan: Annotated[str, "Plan generated by the Trader"]

    # 风险管理链
    risk_debate_state: Annotated[RiskDebateState, "..."]
    final_trade_decision: Annotated[str, "Final decision made by the Risk Analysts"]
```

> **注意**: `AgentState` 继承 `MessagesState` (非 `TypedDict`), 其 `messages` 字段自带 `operator.add` 归约器, 支持消息追加和 `RemoveMessage` 操作。

### 4.2 InvestDebateState (投资辩论状态)

```python
class InvestDebateState(TypedDict):
    bull_history: Annotated[str, "Bullish Conversation history"]    # 字符串拼接, 非列表
    bear_history: Annotated[str, "Bearish Conversation history"]    # 字符串拼接, 非列表
    history: Annotated[str, "Conversation history"]                 # 合并辩论全文
    current_response: Annotated[str, "Latest response"]             # 最新论点 (含 "Bull/Bear Analyst:" 前缀)
    judge_decision: Annotated[str, "Final judge decision"]          # 研究经理裁决
    count: Annotated[int, "Length of the current conversation"]     # 发言计数器
```

### 4.3 RiskDebateState (风控辩论状态)

```python
class RiskDebateState(TypedDict):
    aggressive_history: Annotated[str, "Aggressive Agent's Conversation history"]
    conservative_history: Annotated[str, "Conservative Agent's Conversation history"]
    neutral_history: Annotated[str, "Neutral Agent's Conversation history"]
    history: Annotated[str, "Conversation history"]               # 合并辩论全文
    latest_speaker: Annotated[str, "Analyst that spoke last"]     # 用于路由 (Aggressive/Conservative/Neutral/Judge)
    current_aggressive_response: Annotated[str, "Latest response by the aggressive analyst"]
    current_conservative_response: Annotated[str, "Latest response by the conservative analyst"]
    current_neutral_response: Annotated[str, "Latest response by the neutral analyst"]
    judge_decision: Annotated[str, "Judge's decision"]
    count: Annotated[int, "Length of the current conversation"]   # 发言计数器
```

> **注意**: 所有 `*_history` 和 `history` 字段类型均为 `str` (字符串拼接), **不是** `list`。辩论历史通过字符串 `+=` 不断追加。

---

## 5. 智能体详细设计

### 5.1 智能体一览

| 智能体 | 文件 | LLM 类型 | ToolNode 绑定的工具 | 记忆实例 |
|--------|------|----------|-------------------|---------|
| 市场分析师 | `analysts/market_analyst.py` | Quick | `get_stock_data`, `get_indicators` | 无 |
| 社交媒体分析师 | `analysts/social_media_analyst.py` | Quick | `get_news` | 无 |
| 新闻分析师 | `analysts/news_analyst.py` | Quick | `get_news`, `get_global_news`, `get_insider_transactions` | 无 |
| 基本面分析师 | `analysts/fundamentals_analyst.py` | Quick | `get_fundamentals`, `get_balance_sheet`, `get_cashflow`, `get_income_statement` | 无 |
| 看多研究员 | `researchers/bull_researcher.py` | Quick | 无 | `bull_memory` |
| 看空研究员 | `researchers/bear_researcher.py` | Quick | 无 | `bear_memory` |
| 研究经理 | `managers/research_manager.py` | **Deep** | 无 | `invest_judge_memory` |
| 交易员 | `trader/trader.py` | Quick | 无 | `trader_memory` |
| 激进派辩论员 | `risk_mgmt/aggressive_debator.py` | Quick | 无 | 无 |
| 保守派辩论员 | `risk_mgmt/conservative_debator.py` | Quick | 无 | 无 |
| 中立派辩论员 | `risk_mgmt/neutral_debator.py` | Quick | 无 | 无 |
| 投资组合经理 | `managers/portfolio_manager.py` | **Deep** | 无 | `portfolio_manager_memory` |

### 5.2 双模型策略

- **Deep Thinking LLM** (如 gpt-5.2, claude-opus-4-6): 用于需要深度推理的决策节点 → 研究经理、投资组合经理
- **Quick Thinking LLM** (如 gpt-5-mini, claude-sonnet-4-6): 用于数据处理和论点生成 → 分析师、研究员、辩论员、交易员、信号处理器、反思器

### 5.3 智能体创建模式

所有智能体采用**闭包工厂模式**: `create_xxx()` 返回一个闭包节点函数, 供 LangGraph 直接作为节点使用。

**分析师模式** (有工具):
```python
def create_market_analyst(llm):
    def market_analyst_node(state):
        tools = [get_stock_data, get_indicators]
        # 1. 从 state 提取 trade_date, company_of_interest
        # 2. 构建 ChatPromptTemplate + system_message
        # 3. chain = prompt | llm.bind_tools(tools)
        # 4. result = chain.invoke(state["messages"])
        # 5. 如果没有 tool_calls, 将 result.content 写入 market_report
        return {"messages": [result], "market_report": report}
    return market_analyst_node
```

**研究员/辩论员模式** (无工具, 有辩论状态):
```python
def create_bull_researcher(llm, memory):
    def bull_node(state):
        # 1. 从 state 提取四份分析报告 + 辩论历史
        # 2. 从 memory.get_memories() 检索相似情景
        # 3. 构建 prompt 字符串 (含报告 + 历史 + 记忆)
        # 4. response = llm.invoke(prompt)
        # 5. 更新 investment_debate_state (追加历史, count+1)
        return {"investment_debate_state": new_state}
    return bull_node
```

**交易员模式** (使用 functools.partial):
```python
def create_trader(llm, memory):
    def trader_node(state, name):
        # ... 生成投资计划 ...
        return {"messages": [result], "trader_investment_plan": result.content, "sender": name}
    return functools.partial(trader_node, name="Trader")
```

### 5.4 Ticker 上下文注入

`build_instrument_context(ticker)` 为每个智能体生成标准化的 Ticker 说明:

```python
def build_instrument_context(ticker: str) -> str:
    return (
        f"The instrument to analyze is `{ticker}`. "
        "Use this exact ticker in every tool call, report, and recommendation, "
        "preserving any exchange suffix (e.g. `.TO`, `.L`, `.HK`, `.T`)."
    )
```

此函数在市场分析师、研究经理、交易员、投资组合经理中被调用, 确保国际 Ticker 后缀不被丢失。

---

## 6. 数据流层

### 6.1 数据源路由机制

```
Tool 调用 (如 get_stock_data)
        │
        ▼
  route_to_vendor(method, *args, **kwargs)
        │
        ├─ get_category_for_method(method) → 确定所属分类
        ├─ get_vendor(category, method)
        │   ├─ 优先检查 tool_vendors[method] (工具级覆盖)
        │   └─ 回退到 data_vendors[category] (分类级配置)
        │
        ▼
  构建降级链: [配置的主供应商, ...其余可用供应商]
        │
        ├─ 尝试第一个供应商
        │   ├─ 成功 → 返回数据
        │   └─ AlphaVantageRateLimitError → 继续
        │
        ├─ 尝试第二个供应商
        │   └─ ...
        │
        └─ 全部失败 → RuntimeError
```

> **关键细节**: 供应商配置值支持逗号分隔 (如 `"yfinance,alpha_vantage"`), `route_to_vendor` 会按顺序拆分为主供应商列表。**只有 `AlphaVantageRateLimitError` 才会触发降级**, 其他异常会直接抛出。

### 6.2 数据分类映射

| 分类 | 默认供应商 | 包含工具 |
|------|-----------|---------|
| `core_stock_apis` | yfinance | `get_stock_data` |
| `technical_indicators` | yfinance | `get_indicators` |
| `fundamental_data` | yfinance | `get_fundamentals`, `get_balance_sheet`, `get_cashflow`, `get_income_statement` |
| `news_data` | yfinance | `get_news`, `get_global_news`, `get_insider_transactions` |

### 6.3 技术指标

市场分析师通过 prompt 从以下指标中选择最多 8 个互补指标:

| 类别 | 指标 | 说明 |
|------|------|------|
| 移动均线 | `close_50_sma` | 50 周期简单移动均线 |
| | `close_200_sma` | 200 周期简单移动均线 |
| | `close_10_ema` | 10 周期指数移动均线 |
| MACD | `macd`, `macds`, `macdh` | MACD线 / 信号线 / 柱状图 |
| 动量 | `rsi` | 相对强弱指标 (70/30 阈值) |
| 波动率 | `boll`, `boll_ub`, `boll_lb` | 布林带 (中/上/下轨, 20周期 2σ) |
| | `atr` | 平均真实波幅 |
| 成交量 | `vwma` | 成交量加权移动均线 |

底层通过 stockstats 库计算, 数据源为 yfinance 或 Alpha Vantage 的 OHLCV 数据。

---

## 7. LLM 客户端抽象层

### 7.1 类层次

```
normalize_content(response)          # 独立函数: 将列表类型的 content 标准化为字符串
                                     # 提取 type="text" 的块, 丢弃 reasoning/metadata

BaseLLMClient (ABC)
├── get_llm() → Any                  # 抽象方法: 返回配置好的 LangChain LLM 实例
├── validate_model() → bool          # 抽象方法: 验证模型名是否合法
│
├── OpenAIClient
│   ├── 内部使用 NormalizedChatOpenAI (继承 ChatOpenAI, invoke 时自动 normalize)
│   ├── 支持: openai, xai, openrouter, ollama
│   ├── 原生 OpenAI: 启用 use_responses_api=True (Responses API)
│   ├── 第三方 (xai/openrouter/ollama): 使用标准 Chat Completions
│   ├── 可透传参数: timeout, max_retries, reasoning_effort, api_key, callbacks, http_client, http_async_client
│   └── 供应商自动配置: xai→api.x.ai, openrouter→openrouter.ai, ollama→localhost:11434
│
├── AnthropicClient
│   ├── 内部使用 NormalizedChatAnthropic (继承 ChatAnthropic, invoke 时自动 normalize)
│   ├── 可透传参数: timeout, max_retries, api_key, max_tokens, callbacks, http_client, http_async_client, effort
│   └── effort 参数控制扩展思维 (low/medium/high)
│
└── GoogleClient
    ├── 内部使用 NormalizedChatGoogleGenerativeAI
    ├── 可透传参数: timeout, max_retries, google_api_key, callbacks, http_client, http_async_client
    └── 思维配置按模型系列区分:
        ├── Gemini 3 系列: thinking_level (minimal/low/medium/high)
        │   └── Gemini 3 Pro 不支持 "minimal", 自动映射为 "low"
        └── Gemini 2.5 系列: thinking_budget (-1=动态, 0=禁用)
```

### 7.2 工厂函数

```python
create_llm_client(provider, model, base_url=None, **kwargs) → BaseLLMClient
# provider: "openai" | "anthropic" | "google" | "xai" | "openrouter" | "ollama"
#
# 路由逻辑:
#   openai / ollama / openrouter → OpenAIClient
#   xai                          → OpenAIClient (provider="xai")
#   anthropic                    → AnthropicClient
#   google                       → GoogleClient
```

### 7.3 内容标准化机制

多个 LLM 供应商 (OpenAI Responses API, Gemini 3, Claude Extended Thinking) 返回的 `response.content` 为类型化块列表:
```python
[{"type": "reasoning", "text": "..."}, {"type": "text", "text": "实际内容"}]
```

每个客户端使用 `Normalized*` 包装类, 在 `invoke()` 后自动调用 `normalize_content()` 将其转为纯字符串, 确保下游所有智能体都收到一致的字符串格式。

---

## 8. 记忆系统

### 8.1 FinancialSituationMemory

```python
class FinancialSituationMemory:
    """基于 BM25 的金融情景记忆"""

    def __init__(self, name: str, config: dict = None):
        # name: 记忆实例标识符
        # config: 保留用于 API 兼容性, BM25 实际不使用

    def add_situations(self, situations_and_advice: List[Tuple[str, str]]):
        # 添加 (情景描述, 推荐/反思) 对, 自动重建 BM25 索引

    def get_memories(self, current_situation: str, n_matches: int = 1) -> List[dict]:
        # 默认返回 1 条最匹配记忆 (注意: 调用时多数传 n_matches=2)
        # 返回: [{"matched_situation": str, "recommendation": str, "similarity_score": float}]

    def clear(self):
        # 清空所有记忆
```

**特点**:
- 纯词汇匹配 (BM25 Okapi), 无需 API 调用
- 离线可用, 无 token 限制
- 每个关键角色独立记忆实例
- 分词方式: 小写化 + 按 `\b\w+\b` 正则拆分
- 相似度分数归一化到 0-1 范围

### 8.2 记忆使用者

| 代码中的实例名 | 使用智能体 | 用途 | 检索数 |
|---------------|-----------|------|--------|
| `bull_memory` | 看多研究员 | 检索历史看多反思 | 2 |
| `bear_memory` | 看空研究员 | 检索历史看空反思 | 2 |
| `trader_memory` | 交易员 | 检索历史交易反思 | 2 |
| `invest_judge_memory` | 研究经理 | 检索历史投资判断反思 | 2 |
| `portfolio_manager_memory` | 投资组合经理 | 检索历史组合决策反思 | 2 |

### 8.3 反思学习循环

```
执行交易决策 → 获取实际收益/损失 (数值)
        │
        ▼
  reflect_and_remember(returns_losses)
        │
        ├─ Reflector 使用 quick_thinking_llm (非 deep)
        ├─ 对 5 个角色分别生成反思:
        │   ├─ Bull Researcher  → 反思看多论点 vs 实际结果
        │   ├─ Bear Researcher  → 反思看空论点 vs 实际结果
        │   ├─ Trader           → 反思交易计划 vs 实际结果
        │   ├─ Invest Judge     → 反思投资裁决 vs 实际结果
        │   └─ Portfolio Manager → 反思最终决策 vs 实际结果
        │
        ├─ 输入上下文 = 四份分析报告拼接
        ├─ Reflection Prompt 要求分析: 推理/改进/总结/精简查询
        └─ 反思结果存入对应记忆 → 下次 get_memories() 时可检索到
```

---

## 9. 图编排引擎

### 9.1 TradingAgentsGraph (主入口)

```python
class TradingAgentsGraph:
    def __init__(
        self,
        selected_analysts=["market", "social", "news", "fundamentals"],
        debug=False,
        config: Dict[str, Any] = None,    # 默认使用 DEFAULT_CONFIG
        callbacks: Optional[List] = None,  # LangChain 回调处理器 (如 StatsCallbackHandler)
    ):
        # 1. set_config(config) → 更新 dataflows 全局配置
        # 2. 创建 data_cache 目录
        # 3. 根据 provider 提取 thinking kwargs (reasoning_effort / effort / thinking_level)
        # 4. create_llm_client() × 2 (deep + quick)
        # 5. 初始化 5 个 FinancialSituationMemory 实例
        # 6. 创建 4 个 ToolNode (market/social/news/fundamentals)
        # 7. 初始化 ConditionalLogic, GraphSetup, Propagator, Reflector, SignalProcessor
        # 8. graph_setup.setup_graph(selected_analysts) → 编译图

    def propagate(self, company_name, trade_date):
        # debug=True: graph.stream() 逐步打印
        # debug=False: graph.invoke() 一次执行
        # 日志写入 eval_results/{ticker}/TradingAgentsStrategy_logs/
        # 返回 (final_state, signal)

    def reflect_and_remember(self, returns_losses):
        # 对当前 state 进行 5 角色反思

    def process_signal(self, full_signal):
        # SignalProcessor 提取评级
```

### 9.2 图节点与边 (精确流程)

```
START
  │
  ▼
{first_selected_analyst} Analyst      ◄─── 第一个选定的分析师
  │
  ├──[有 tool_calls]──► tools_{type} ──► 回到该分析师 (循环)
  │
  └──[无 tool_calls]──► Msg Clear {Type} ──► 下一个分析师 / Bull Researcher
                                                    │
(所有选定分析师串行执行完毕)                          │
                                                    ▼
                                            Bull Researcher
                                                    │
                        ┌───────────────────────────┤
                        │                           │
             count < 2*max_debate_rounds    count >= 2*max_debate_rounds
                        │                           │
                        ▼                           │
                  Bear Researcher                   │
                        │                           │
             ┌──────────┤                           │
             │          │                           │
          继续辩论  达到上限                          │
             │          │                           │
             ▼          ▼                           ▼
        Bull Researcher                     Research Manager
                                                    │
                                                    ▼
                                                 Trader
                                                    │
                                                    ▼
                                          Aggressive Analyst
                                                    │
                        ┌───────────────────────────┤
                        │                           │
             count < 3*max_risk_discuss      count >= 3*max_risk_discuss
                        │                           │
                        ▼                           │
                Conservative Analyst                │
                        │                           │
                        ▼                           │
                  Neutral Analyst                   │
                        │                           │
                     (循环)                          │
                                                    ▼
                                           Portfolio Manager
                                                    │
                                                    ▼
                                                   END
```

### 9.3 条件路由逻辑详细

**分析师工具路由** (`should_continue_{type}`):
- 检查 `messages[-1].tool_calls` 是否存在
- 有工具调用 → `"tools_{type}"` (执行工具后返回分析师继续)
- 无工具调用 → `"Msg Clear {Type}"` (清除消息, 进入下一阶段)

**投资辩论路由** (`should_continue_debate`):
- `count >= 2 * max_debate_rounds` → `"Research Manager"` (结束辩论)
- `current_response` 以 `"Bull"` 开头 → `"Bear Researcher"` (轮到看空方)
- 否则 → `"Bull Researcher"` (轮到看多方)

**风控辩论路由** (`should_continue_risk_analysis`):
- `count >= 3 * max_risk_discuss_rounds` → `"Portfolio Manager"` (结束辩论)
- `latest_speaker` 以 `"Aggressive"` 开头 → `"Conservative Analyst"`
- `latest_speaker` 以 `"Conservative"` 开头 → `"Neutral Analyst"`
- 否则 → `"Aggressive Analyst"`

---

## 10. 配置系统

### 10.1 默认配置 (default_config.py)

```python
DEFAULT_CONFIG = {
    # 路径
    "project_dir": "<tradingagents 包的绝对路径>",
    "results_dir": os.getenv("TRADINGAGENTS_RESULTS_DIR", "./results"),
    "data_cache_dir": "<project_dir>/dataflows/data_cache",

    # LLM 设置
    "llm_provider": "openai",
    "deep_think_llm": "gpt-5.2",
    "quick_think_llm": "gpt-5-mini",
    "backend_url": "https://api.openai.com/v1",

    # 供应商特定思维配置
    "openai_reasoning_effort": None,     # "low" | "medium" | "high"
    "anthropic_effort": None,            # "low" | "medium" | "high"
    "google_thinking_level": None,       # "minimal" | "low" | "medium" | "high"

    # 辩论轮次
    "max_debate_rounds": 1,              # 投资辩论轮数 (实际发言 = 2 * N)
    "max_risk_discuss_rounds": 1,        # 风控辩论轮数 (实际发言 = 3 * N)
    "max_recur_limit": 100,              # LangGraph 递归限制

    # 数据源 (分类级)
    "data_vendors": {
        "core_stock_apis": "yfinance",       # 可选: alpha_vantage, yfinance
        "technical_indicators": "yfinance",
        "fundamental_data": "yfinance",
        "news_data": "yfinance",
    },

    # 数据源 (工具级覆盖, 优先级更高)
    "tool_vendors": {},
}
```

### 10.2 环境变量 (.env.example)

```bash
# LLM 供应商 (设置你使用的那个)
OPENAI_API_KEY=
GOOGLE_API_KEY=
ANTHROPIC_API_KEY=
XAI_API_KEY=
OPENROUTER_API_KEY=

# 数据源 (可选, 使用 Alpha Vantage 时需要)
ALPHAVANTAGE_API_KEY=
```

### 10.3 配置传递流程

```
TradingAgentsGraph.__init__(config)
    │
    ├─ set_config(config)  → 写入 dataflows.config 全局变量
    │                        所有 route_to_vendor() 调用通过 get_config() 读取
    │
    ├─ _get_provider_kwargs()  → 根据 provider 提取 thinking 配置
    │   ├─ google → {"thinking_level": ...}
    │   ├─ openai → {"reasoning_effort": ...}
    │   └─ anthropic → {"effort": ...}
    │
    └─ create_llm_client(provider, model, base_url, **kwargs)
        └─ 传入 LangChain LLM 构造函数
```

---

## 11. CLI 交互流程

### 11.1 用户交互步骤

```
1. 输入 Ticker 代号 (支持国际后缀: .TO, .L, .HK, .T)
   → normalize_ticker_symbol(): strip + upper
2. 选择分析日期 (YYYY-MM-DD, 含格式校验)
3. 选择启用的分析师 (多选 checkbox: Market/Social/News/Fundamentals)
4. 选择研究深度:
   - Shallow (1轮) / Medium (3轮) / Deep (5轮)
   → 同时设置 max_debate_rounds 和 max_risk_discuss_rounds
5. 选择 LLM 供应商 (OpenAI/Google/Anthropic/xAI/Openrouter/Ollama)
   → 返回 (display_name, base_url) 元组
6. 选择 Quick Thinking 模型 (选项随供应商变化)
7. 选择 Deep Thinking 模型 (选项随供应商变化)
8. [供应商特定] 思维配置:
   - OpenAI → 选择 Reasoning Effort (Low/Medium/High)
   - Anthropic → 选择 Effort Level (Low/Medium/High)
   - Google → 选择 Thinking Mode (Enable/Minimal)
9. 执行分析 (实时展示进度)
```

### 11.2 MessageBuffer (实时状态追踪)

`MessageBuffer` 是 CLI 层的核心状态管理类:

- **agent_status**: 动态追踪每个智能体的 `pending` / `running` / `completed` 状态
- **report_sections**: 追踪 7 个报告段 (4 分析报告 + investment_plan + trader_plan + final_decision)
- **messages/tool_calls**: 带时间戳的消息和工具调用记录 (deque, 最大 100 条)
- **init_for_analysis(selected_analysts)**: 根据选定分析师动态构建状态和报告追踪
- **get_completed_reports_count()**: 统计已完成报告数 (要求报告有内容 + 对应智能体已 completed)

固定团队 (始终包含):
- Research Team: Bull Researcher, Bear Researcher, Research Manager
- Trading Team: Trader
- Risk Management: Aggressive Analyst, Neutral Analyst, Conservative Analyst
- Portfolio Management: Portfolio Manager

### 11.3 StatsCallbackHandler (统计回调)

线程安全的 LangChain 回调处理器, 追踪:
- `llm_calls`: LLM 调用次数 (on_llm_start + on_chat_model_start)
- `tool_calls`: 工具调用次数 (on_tool_start)
- `tokens_in`: 输入 Token 数 (从 AIMessage.usage_metadata 提取)
- `tokens_out`: 输出 Token 数

### 11.4 公告系统

CLI 启动时从 `https://api.tauric.ai/v1/announcements` 获取公告 (超时 1 秒), 失败时显示 GitHub 链接回退文本。

---

## 12. 输出格式

### 12.1 最终决策信号

五级评级:

| 信号 | 含义 |
|------|------|
| **BUY** | 强烈建议买入 |
| **OVERWEIGHT** | 建议增持 |
| **HOLD** | 建议持有/观望 |
| **UNDERWEIGHT** | 建议减持 |
| **SELL** | 强烈建议卖出 |

信号由 `SignalProcessor` 使用 quick_thinking_llm 从 Portfolio Manager 的完整决策文本中提取。

### 12.2 输出内容

`propagate()` 返回 `(state, signal)`:
- `state`: 完整 AgentState dict, 包含所有分析报告和辩论记录
- `signal`: 字符串, 由 LLM 从 `final_trade_decision` 中提取的评级

### 12.3 日志存储

每次执行自动生成 JSON 日志:
- 路径: `eval_results/{ticker}/TradingAgentsStrategy_logs/full_states_log_{trade_date}.json`
- 内容: 所有报告、辩论历史、裁决、最终决策的完整快照

---

## 13. 设计模式

| 模式 | 应用 |
|------|------|
| **工厂模式** | `create_llm_client()`, `create_*_analyst()`, `create_*_researcher()`, `create_trader()` |
| **闭包模式** | 所有智能体节点函数通过闭包捕获 llm/memory |
| **策略模式** | 数据供应商路由 (yfinance ↔ Alpha Vantage) |
| **装饰器模式** | LangChain `@tool` 工具注册; `Normalized*` 包装类 |
| **状态模式** | AgentState + InvestDebateState + RiskDebateState 管理工作流 |
| **备选链 (Fallback)** | 数据供应商失败时自动降级 (仅限速率限制错误) |
| **全局配置** | `get_config()` / `set_config()` 管理数据源配置 |
| **部分应用** | Trader 使用 `functools.partial` 绑定 name 参数 |

---

## 14. 依赖清单

| 类别 | 库 | 用途 |
|------|-----|------|
| LLM 编排 | `langgraph` (>=0.4.8), `langchain-core` (>=0.3.81) | 图工作流引擎 |
| LLM 客户端 | `langchain-openai` (>=0.3.23), `langchain-anthropic` (>=0.3.15), `langchain-google-genai` (>=2.1.5) | 多供应商支持 |
| LLM 扩展 | `langchain-experimental` (>=0.3.4) | 实验性功能 |
| 数据获取 | `yfinance` (>=0.2.63) | 股票/新闻数据 |
| 技术分析 | `pandas` (>=2.3.0), `stockstats` (>=0.6.5) | 指标计算 |
| 回测 | `backtrader` (>=1.9.78) | 回测框架 |
| 记忆 | `rank-bm25` (>=0.2.2) | BM25 相似度匹配 |
| CLI | `typer` (>=0.21.0), `questionary` (>=2.1.0), `rich` (>=14.0.0) | 终端交互 |
| 网络/解析 | `requests` (>=2.32.4), `parsel` (>=1.10.0) | HTTP 请求 / HTML 解析 |
| 数据存储 | `redis` (>=6.2.0) | Redis 客户端 |
| 工具 | `python-dotenv`, `pytz` (>=2025.2), `tqdm` (>=4.67.1), `typing-extensions` (>=4.14.0) | 环境/时区/进度条 |

> Python 版本要求: `>=3.10`

---

## 15. 扩展点

1. **新增分析师**: 在 `agents/analysts/` 添加新文件, 在 `agents/__init__.py` 导出, 在 `graph/setup.py` 注册节点和边, 在 `conditional_logic.py` 添加 `should_continue_xxx` 方法
2. **新增数据源**: 在 `dataflows/` 实现供应商模块, 在 `interface.py` 的 `VENDOR_METHODS` 和 `VENDOR_LIST` 中注册
3. **新增 LLM 供应商**: 继承 `BaseLLMClient`, 实现 `get_llm()` 和 `validate_model()`, 在 `factory.py` 注册路由, 在 `validators.py` 添加模型白名单
4. **调整辩论轮次**: 修改配置中 `max_debate_rounds` / `max_risk_discuss_rounds` (注意: 实际发言次数分别为 2N 和 3N)
5. **自定义评级体系**: 修改 `signal_processing.py` 的 system prompt 中的评级选项
6. **新增记忆角色**: 在 `TradingAgentsGraph.__init__` 中创建新的 `FinancialSituationMemory` 实例, 在 `Reflector` 中添加对应反思方法
