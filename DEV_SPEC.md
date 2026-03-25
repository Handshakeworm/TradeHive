# pending

- 模型选型，minimax，kimi，glm，qwen，deeepseek，豆包，跑 baseline
- 单 agent 设计，跑单 agent baseline
- 定制或扩展一个或多个 agent 角色（如技术分析师、情绪分析 agent、风险管理者）
- 集成替代模型或数据源（如其他 LLM、不同市场、不同新闻来源）
- 对多 agent 策略进行严格的金融回测与评估
- 撰写研究报告并制作演示，将多 agent bot 与经典基准进行对比

## 交付物

- 修改后的 TradingAgents 代码（不能只是复制，需清晰记录改动）
- 数据收集、回测与指标计算脚本
- `requirements.txt` 或 `environment.yml`（确保环境可复现）
- 小型 demo 脚本（展示如何对指定 ticker 和日期运行 bot）
- 支持通过 config 切换模型

## 对比基准

多 agent bot 必须与以下基准进行对比：

- **Buy-and-Hold**：基准指数或 ETF
- **单 agent bot**：无辩论 / 无多角色的原始 TradingAgents
- **传统量化策略**：如动量策略或基于 RSI 的规则策略

## 评估指标

| 指标 | 说明 |
|------|------|
| 年化收益率（Annualized Return / CAGR） | 测试期间的复合年增长率 |
| 波动率（Volatility） | 收益率的标准差 |
| 夏普比率（Sharpe Ratio） | 收益 / 波动率，衡量风险调整后的收益 |
| 最大回撤（Max Drawdown） | 从历史最高点到最低点的最大跌幅 |
| 换手率（Turnover） | 持仓随时间变化的频率或幅度 |
| 交易成本（Transaction Costs） | 交易带来的总成本影响 |



# guideline写明建议

以下方向可获得额外加分：

- **新增 Agent 角色**：如基于宏观经济数据发布的宏观事件预测 agent
- **滚动前向验证（Roll-forward Validation）**：优化滚动窗口以降低过拟合
- **检索增强提示（RAG）**：通过向量库注入结构化外部数据
- **多资产组合**：将 TradingAgents 扩展为支持组合管理，而非仅单支股票
- **加密货币市场**：扩展 TradingAgents 支持加密资产交易

# 光神的建议

### 模型选型

- 测试股票/日期参考：NVDA 2024-05-10；也可替换为其他主流美股（如 AAPL、MSFT）或其他日期区间

### 新数据资源建议

- 数据源：从 yfinance 换成 Alpha Vantage、Tiingo、Polygon、新浪财经
- 市场覆盖：集成港股、A 股、加密货币等市场数据接口
- 数据类型：增加 alternative data、社交媒体情绪、宏观经济指标


### 新增 Agent 说明

**技术分析师 Agent**（`technical_analyst.py`）

- 只关注技术面分析（均线、MACD、RSI、布林带等），不考虑基本面或新闻
- 优先调用 `get_stock_data` 和 `get_indicators` 工具获取历史价格与技术指标
- 输出趋势判断与买卖建议，并给出简明理由
- 相比 baseline：在分析流程最前面新增技术面独立分析段落，后续其他 agent 内容不变
- 分析输出结果存储至独立文件夹

**情绪分析 Agent**（Sentiment Agent）

- 在 `TradingAgentsGraph` 的 `selected_analysts` 列表中新增 `”sentiment”` 节点
- 独立调用 LLM，对目标股票的新闻与社交数据进行情绪分析，输出正面 / 中性 / 负面情绪分数及解释
- 实现方式与 technical、market 等 analyst 一致，作为独立节点插入分析流程
- 相比 baseline：额外输出一段”情绪面分析”结果，便于对比各 agent 的贡献

**风险管理 Agent**（Risk Manager）

- 文件已存在：`tradingagents/agents/managers/risk_manager.py`（含 `create_risk_manager` 函数）
- 当前状态：尚未集成进 `main.py`，待接入运行流程


# 我的ideas
1. 加入skills
   - 不做 tool 的上层封装（当前每个 Analyst 节点本身已是"技能单元"，LangGraph 编排已实现组合）
   - 核心价值：让 agent 在运行时根据情境动态选择调用哪些分析能力，而非固定顺序全跑
   - 仅在执行层（Analyst）引入 skill 选择机制；推理层（Researchers、Debators、Managers）保持自由推理，不加约束
   - 避免过度结构化 skill 输出格式，防止限制辩论阶段的创造力

2. 应用rag建立向量库（有使用BM25,无稠密向量检索，无重排步骤）
BM25索引倒排还是什么，数据pipeline

3. 上下文管理探究/明确

### 目标：压缩上下文提高能力，智能保留防止关键信息丢失

#### 核心思路：上下文管理的七个生命周期决策（参考 OpenClaw 3.7 ContextEngine）
   这些决策加在一起决定了整个系统的"智商上限"——不是模型的智商，是系统的智商。

   | 钩子 | 时机 | 决策 |
   |------|------|------|
   | **bootstrap** | Agent 启动 | 加载什么初始信息 |
   | **ingest** | 新消息进入 | 原样存储还是预处理/过滤关键部分 |
   | **assemble**（最核心） | 调用模型时 | 从所有可用信息中选什么送入上下文窗口（100 条历史、20 个工具输出、5 个外部文档，窗口只够三分之一，选什么？） |
   | **compact** | 上下文接近上限 | 压缩策略——摘要粒度、哪些信息不可丢弃 |
   | **afterTurn** | 模型回复完成 | 哪些中间结果持久化到磁盘、哪些丢弃 |
   | **prepareSubagentSpawn** | 子 Agent 启动 | 传递什么上下文给子 Agent |
   | **onSubagentEnded** | 子 Agent 结束 | 如何回收成果到父 Agent 的上下文 |

#### 压缩机制与风险
   **触发条件（OpenClaw 方案）：**
   - **溢出恢复**：模型返回上下文溢出错误时触发压缩并重试
   - **阈值维护**：任务成功完成后，检测到 token 超过预留阈值时触发

   **核心风险——关键指令丢失：**
   - 典型案例：用户让 Agent 处理收件箱数千条消息，压缩后"在我说可以之前不要做任何事"的指令从摘要中消失，Agent 回到自主模式开始删除邮件，造成灾难性后果
   - 策略因场景而异：编码 Agent 和邮件处理 Agent 的上下文管理策略完全不同，没有通用答案
   - 因此 OpenClaw 3.7 将上下文管理变成可插拔接口（ContextEngine 插件槽位），LegacyContextEngine 包装器保留原有行为，新插件可获得全部控制权

#### 参考案例：Lossless-Claw 插件
   - **问题**：简单摘要压缩是有损的，可能丢失关键信息
   - **方案**：激进压缩 + 保留指向原始数据的"无损指针"，原始消息始终保留在数据库中，摘要链接回源消息
   - **工具**：`lcm_grep`（搜索）、`lcm_describe`（描述）、`lcm_expand`（展开恢复原始细节）
   - **启示**：上下文管理策略可插件化，不改核心循环一行代码即可替换，让 Agent "过目不忘"

#### 对 TradeHive 的启发
   当前 `create_msg_delete()` 是简单清除消息防 token 溢出，可探索更智能的上下文保留/压缩机制



### 目前的上下文管理策略：

---

#### A. 主状态结构（LangGraph `MessagesState`）

[agent_states.py](tradingagents/agents/utils/agent_states.py) 使用 TypedDict 扩展 LangGraph 的 `MessagesState`，将各阶段产物（分析报告、辩论历史）存为独立具名字段，而非全堆入 `messages` 列表。核心字段：
- `company_of_interest`（`str`）：目标股票 ticker
- `trade_date`（`str`）：交易日期
- `sender`（`str`）：发送消息的 agent 名称（仅 Trader 写入，实际无下游消费者）
- `market_report` / `sentiment_report` / `news_report` / `fundamentals_report`：各分析师输出
- `investment_debate_state`（`InvestDebateState`）：Bull/Bear 辩论状态，含 `bull_history`、`bear_history`、`history`、`current_response`、`judge_decision`、`count`
- `risk_debate_state`（`RiskDebateState`）：风险辩论状态，含 `aggressive_history`、`conservative_history`、`neutral_history`、`history`、`latest_speaker`、`current_aggressive_response`、`current_conservative_response`、`current_neutral_response`、`judge_decision`、`count`
- `investment_plan`、`trader_investment_plan`、`final_trade_decision`：各决策阶段输出

初始状态由 [propagation.py](tradingagents/graph/propagation.py) 的 `create_initial_state()` 构建：`messages` 初始化为 `[("human", company_name)]`，所有报告字段为空字符串，两个 debate state 的 `count` 初始化为 0、所有历史字段初始化为空字符串。`sender`、`investment_plan`、`trader_investment_plan`、`final_trade_decision` 四个字段**不在**初始状态中，由各 agent 在运行时首次写入；图拓扑保证写入先于读取。

---

#### B. 各阶段上下文策略

##### B1. 分析师阶段：messages 内部累积 + 阶段间统一清除

分析师（market/social/news/fundamentals）使用 `ChatPromptTemplate` + `MessagesPlaceholder`，读取完整 `state["messages"]`，同时读取 `state["trade_date"]` 作为当前日期注入 prompt、通过 `build_instrument_context(state["company_of_interest"])` 注入 ticker 身份。四个分析师共享同一个"协作助手"模板外壳（含 `FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL**` 前缀指令），仅 `system_message`（领域 prompt）和绑定工具不同。

- **节点内部**：工具调用循环期间，tool call 与 tool result 在 messages 里逐轮累积，让 LLM 知道已取了哪些数据
- **节点之间**：分析师输出最终报告（无 tool_calls）后，`Msg Clear` 节点用 `RemoveMessage` 删掉所有消息，仅保留占位符 `HumanMessage("Continue")`，防止多个分析师的消息叠加撑爆上下文窗口
- **执行顺序**：按 `selected_analysts` 列表顺序严格串行（默认 market → social → news → fundamentals），每个分析师的 Msg Clear 连接到下一个，最后一个连接到 Bull Researcher
- **轮次控制**：工具调用循环**没有硬性轮次限制**，完全依赖 LLM 自主判断何时停止（不输出 tool_calls 则结束）。唯一保护是全局 `recursion_limit=100`，若 LLM 持续调用工具会触发递归上限报错而非优雅截止

##### B2. 辩论阶段：双层上下文结构，完全绕过 messages

Bull/Bear 辩论和风险评估辩论完全绕过 `state["messages"]`（不读也不写），通过字符串字段手动管理，形成两层结构：
- **全量历史层**（`history`）：每轮发言追加拼接，注入 LLM 获得完整辩论上下文
- **最新一轮层**（`current_response` / `current_aggressive_response` 等）：只保存各方最新一轮发言，注入 LLM 用于定向反驳，路由逻辑也依赖此字段（`current_response.startswith("Bull")` 决定下一个发言者；`latest_speaker` 决定风险辩论轮序）

这种双层设计使 LLM 既能看到完整辩论脉络，又能精确聚焦到需要反驳的对手最新观点。

**轮次控制**（[conditional_logic.py](tradingagents/graph/conditional_logic.py)）：通过 `count` 计数器强制截止——
- 投资辩论：默认最多 1 轮（2 次发言，Bull → Bear → Research Manager），截止条件 `count >= 2 * max_debate_rounds`
- 风险讨论：默认最多 1 轮（3 次发言，3 个角色各一次 → Portfolio Manager），截止条件 `count >= 3 * max_risk_discuss_rounds`
- `count` 递增语义：辩论双方/三方每次发言 `count += 1`，裁判不递增，count 只统计辩论发言次数

##### B3. Trader / Manager：绕过 messages，手动构建 prompt

这三个 agent 构建 prompt 时完全不读 `state["messages"]`，只从 state 具名字段（报告、辩论历史、memory）取内容，上下文窗口精确可控。
- **Trader**：读 `investment_plan`（Research Manager 输出），写回 `messages` 和 `sender`（实际无下游消费者，属无效写入）。调用方式不对称：Trader 是唯一使用 message list（system/user role 分离）调用 LLM 的 agent，其余非分析师 agent 都使用 `llm.invoke(prompt_string)` 直接传字符串。Trader 也是唯一显式处理空记忆的 agent（`if past_memories:` + fallback），其余 agent 空记忆时 `past_memory_str` 为空字符串
- **Research Manager**：不读/写 messages；输出双写到 `investment_debate_state.judge_decision` 和 `investment_plan`。同时将 `current_response` 覆写为裁判决策文本——虽然辩论已结束不影响路由，但破坏了 `current_response` 的语义一致性
- **Portfolio Manager**：不读/写 messages；读取 `state["investment_plan"]`（Research Manager 的输出）并命名为 `trader_plan`，标注为 "Trader's proposed plan"——实际从未读取 `state["trader_investment_plan"]`（真正的 Trader 输出），是一处设计 bug

---

#### C. 跨切面机制

##### C1. 两档 LLM 分层处理

[trading_graph.py](tradingagents/graph/trading_graph.py) 初始化两个 LLM 实例：
- **`deep_thinking_llm`**（高推理强度）：仅分配给 Research Manager 和 Portfolio Manager 两个终审裁判节点，它们接收已经压缩过的辩论历史 `history`，需要从中提炼最终决策
- **`quick_thinking_llm`**（次级推理）：其余所有 agent（四个分析师、Bull/Bear、风险三方辩手、Trader），以及 Reflection 反思阶段

体现"推理三明治"思路：在上下文被充分蒸馏后，才动用高推理强度模型做最终判断。

##### C2. 跨运行长期记忆（BM25 检索）

[memory.py](tradingagents/agents/utils/memory.py) 用 **BM25** 算法存储"过去情境 → 建议"对，不调 API。每次运行取 top-2 相似记忆，但注入 prompt 时**只传 `recommendation`（反思教训文本），丢弃 `matched_situation`（原始情境描述）**，LLM 无法看到匹配的原始情境是什么，只看到结论建议。

[reflection.py](tradingagents/graph/reflection.py) 在得知真实收益后使用 `quick_thinking_llm` 生成反思，更新记忆，5 个 agent 各有独立记忆池（bull/bear/trader/invest_judge/portfolio_manager）。

**当前限制**：`FinancialSituationMemory` 只在内存（Python list + BM25 index）中存储，**每次重新实例化 `TradingAgentsGraph` 后记忆全部清空**，进程重启后归零，无磁盘持久化。

记忆匹配上下文：所有使用记忆的 agent 构建 `curr_situation` 时只拼接四份报告，**不包含** `investment_plan` 或 `trader_investment_plan`。BM25 匹配完全基于市场情境，不考虑决策内容。设计意图可能是"相似市场环境下的教训可迁移"，但也导致不同决策在相同市场下命中相同记忆。

##### C3. Ticker 身份注入与日期注入

- **Ticker 注入**：[agent_utils.py](tradingagents/agents/utils/agent_utils.py) 的 `build_instrument_context()` 注入固定文本，要求保留交易所后缀（如 `.TO`、`.HK`）。**覆盖范围**：四个分析师、Trader、Research Manager、Portfolio Manager。Bull/Bear 研究员和风险三方辩手**没有**此注入。
- **日期注入**：`state["trade_date"]` **仅被四个分析师读取**并作为 `{current_date}` 注入 prompt，其余所有 agent **均不读取** `trade_date`，只能通过分析师报告内容间接获知日期信息。

##### C4. Reasoning token 过滤（防污染）

[base_client.py](tradingagents/llm_clients/base_client.py) 的 `normalize_content()` 在所有 LLM 响应返回前，将 `[{type: "reasoning",...}, {type: "text",...}]` 列表结构转成纯字符串，丢弃 reasoning blocks，防止 thinking tokens 污染下游 agent 的上下文。

##### C5. 兜底保护

- LangGraph `recursion_limit=100`：防止图中出现无限循环
- 分析师可动态选择（`selected_analysts` 参数），不需要的分析师节点不加入图，减少无效上下文传播

---

#### D. 已知设计问题与不对称

| 类别 | 问题 | 说明 |
|------|------|------|
| **Bug** | Portfolio Manager 读错字段 | 读 `investment_plan`（Research Manager 输出）而非 `trader_investment_plan`（Trader 输出），prompt 中标注为 "Trader's proposed plan" 但实际来源是 Research Manager |
| **Bug** | 工具绑定与 ToolNode 不一致 | News 分析师 LLM 只绑定 `get_news` 和 `get_global_news`，但 ToolNode（[trading_graph.py:175-181](tradingagents/graph/trading_graph.py#L175-L181)）额外包含 `get_insider_transactions`，LLM 永远不会调用，是死代码。[fundamentals_analyst.py:10](tradingagents/agents/analysts/fundamentals_analyst.py#L10) 也导入了该函数但未使用 |
| **不对称** | 风险辩手无记忆 | Bull/Bear 研究员有独立记忆池并注入 `past_memory_str`，但 Aggressive/Conservative/Neutral 没有记忆参数，无法从历史决策中学习 |
| **不对称** | Ticker/日期注入不完整 | `build_instrument_context()` 和 `trade_date` 仅覆盖部分 agent，Bull/Bear 和风险三方辩手无直接 ticker 身份和日期感知 |
| **不对称** | Trader 调用方式独特 | 唯一用 message list（role 分离）调 LLM 的非分析师 agent，唯一显式处理空记忆的 agent |
| **冗余** | Trader 无效写入 | 写 `messages` + `sender`，无下游消费者，历史遗留可清理 |
| **冗余** | Research Manager 覆写 `current_response` | 裁判决策覆盖了辩论发言字段，破坏语义一致性（辩论已结束，不影响运行） |
| **潜在问题** | 辩论中每轮重复注入全量报告 | 每次辩论 agent 被调用都把四份完整报告重新拼入 prompt，无压缩或摘要，辩论轮数增多时 token 消耗显著上升 |
| **潜在问题** | 分析师无工具调用轮次限制 | 完全依赖 LLM 自主停止，仅靠 `recursion_limit=100` 兜底，非优雅截止 |

---

#### E. 策略汇总

| 阶段 | 上下文方式 | 控制机制 |
|------|-----------|----------|
| 分析师节点内部 | messages 累积 tool call/result | LLM 自主停止 + `recursion_limit=100` 兜底 |
| 分析师节点之间 | `RemoveMessage` 清空 | 按 `selected_analysts` 串行，按需裁剪 |
| 辩论阶段 | 双层：`history`（全量）+ `current_*`（最新轮） | `count` 计数器 + 条件路由截止 |
| Trader / Manager | 绕过 messages，手动构建 prompt | 精确选取具名字段，不受 messages 长度影响 |
| 长期记忆 | BM25 检索 top-2 注入 prompt | 仅传 recommendation，不传原始情境；仅存内存 |
| LLM 分层 | deep 给裁判，quick 给执行层 | 蒸馏后高推理（"推理三明治"） |
| 防污染 | `normalize_content()` 过滤 reasoning token | 所有 LLM 响应统一处理 |
| Ticker / 日期 | `build_instrument_context()` + `trade_date` 注入 | 仅覆盖部分 agent（见 D 节不对称） |

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

11. 注意需要A/B test

12. **待办：为风险辩手补充记忆**：当前 Aggressive/Conservative/Neutral 三个风险辩手没有记忆（DEV_SPEC 已标记为不对称问题），而投资辩论的 Bull/Bear 有独立记忆池。应为风险辩手新增 `aggressive_memory`、`conservative_memory`、`neutral_memory` 三个 `FinancialSituationMemory` 实例，使风险辩论也能从历史决策中学习。同时确保 Single-Agent 对比实验中该阶段有记忆维度的对比价值。






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
| 新闻分析师 | `analysts/news_analyst.py` | Quick | `get_news`, `get_global_news` (⚠️ `get_insider_transactions` 存在于 ToolNode 但未通过 `bind_tools` 绑定给 LLM，实际不可调用) | 无 |
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

此函数在所有 4 个分析师 (市场、社交媒体、新闻、基本面) 以及研究经理、交易员、投资组合经理中被调用, 确保国际 Ticker 后缀不被丢失。

---

## 6. 数据流层

### 6.1 工具总览

系统共有 **9 个 `@tool` 工具**，全部定义在 `agents/utils/` 下，仅在第一阶段（分析师数据收集）被调用。后续的辩论、裁判、交易决策阶段均不使用工具。

| 工具 | 定义文件 | 参数 | 功能 | 绑定给 |
|------|---------|------|------|--------|
| `get_stock_data` | `core_stock_tools.py` | `symbol`, `start_date`, `end_date` | 获取 OHLCV 历史股价数据 | 市场分析师 |
| `get_indicators` | `technical_indicators_tools.py` | `symbol`, `indicator`, `curr_date`, `look_back_days=30` | 获取技术指标（支持逗号分隔多个指标名） | 市场分析师 |
| `get_news` | `news_data_tools.py` | `ticker`, `start_date`, `end_date` | 获取个股相关新闻 | 社交媒体分析师、新闻分析师 |
| `get_global_news` | `news_data_tools.py` | `curr_date`, `look_back_days=7`, `limit=5` | 获取全球宏观新闻 | 新闻分析师 |
| `get_insider_transactions` | `news_data_tools.py` | `ticker` | 获取内部人交易记录 | ⚠️ 存在于新闻 ToolNode 但未 bind_tools 给 LLM |
| `get_fundamentals` | `fundamental_data_tools.py` | `ticker`, `curr_date` | 获取公司基本面概览 | 基本面分析师 |
| `get_balance_sheet` | `fundamental_data_tools.py` | `ticker`, `freq="quarterly"`, `curr_date=None` | 获取资产负债表 | 基本面分析师 |
| `get_cashflow` | `fundamental_data_tools.py` | `ticker`, `freq="quarterly"`, `curr_date=None` | 获取现金流量表 | 基本面分析师 |
| `get_income_statement` | `fundamental_data_tools.py` | `ticker`, `freq="quarterly"`, `curr_date=None` | 获取利润表 | 基本面分析师 |

**工具调用时机**：分析师节点调用 LLM → LLM 返回 `tool_calls` → ToolNode 执行工具并返回结果 → LLM 继续分析或停止。当 LLM 不再返回 `tool_calls` 时，该分析师阶段结束，进入 Msg Clear → 下一阶段。工具调用轮次无硬性限制，依赖 LLM 自主判断，仅靠全局 `recursion_limit=100` 兜底。

### 6.2 数据源路由机制

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

```mermaid
flowchart TD
    START([START])

    %% ===== 第一阶段：分析师串行（默认 4 个，顺序由 selected_analysts 决定） =====
    START --> MA["① Market Analyst\n(quick_think_llm)"]
    MA -->|有 tool_calls| TM["tools_market\n• get_stock_data\n• get_indicators"]
    TM --> MA
    MA -->|"无 tool_calls\n→ 写入 market_report"| MC1["Msg Clear Market\n(RemoveMessage 清空 messages)"]

    MC1 --> SA["② Social Media Analyst\n(quick_think_llm)"]
    SA -->|有 tool_calls| TS["tools_social\n• get_news"]
    TS --> SA
    SA -->|"无 tool_calls\n→ 写入 sentiment_report"| MC2["Msg Clear Social\n(RemoveMessage)"]

    MC2 --> NA["③ News Analyst\n(quick_think_llm)"]
    NA -->|有 tool_calls| TN["tools_news\n• get_news\n• get_global_news\n• get_insider_transactions"]
    TN --> NA
    NA -->|"无 tool_calls\n→ 写入 news_report"| MC3["Msg Clear News\n(RemoveMessage)"]

    MC3 --> FA["④ Fundamentals Analyst\n(quick_think_llm)"]
    FA -->|有 tool_calls| TF["tools_fundamentals\n• get_fundamentals\n• get_balance_sheet\n• get_cashflow\n• get_income_statement"]
    TF --> FA
    FA -->|"无 tool_calls\n→ 写入 fundamentals_report"| MC4["Msg Clear Fundamentals\n(RemoveMessage)"]

    %% ===== 第二阶段：投资辩论（无工具，读取 4 份报告 + memory） =====
    MC4 --> Bull["Bull Researcher\n(quick_think_llm + bull_memory)"]

    Bull -->|"count < 2 × max_debate_rounds"| Bear["Bear Researcher\n(quick_think_llm + bear_memory)"]
    Bull -->|"count ≥ 2 × max_debate_rounds"| RM["Research Manager\n(deep_think_llm + invest_judge_memory)"]

    Bear -->|"count < 2 × max_debate_rounds"| Bull
    Bear -->|"count ≥ 2 × max_debate_rounds"| RM

    %% ===== 第三阶段：交易计划（无工具） =====
    RM -->|"输出 investment_plan"| Trader["Trader\n(quick_think_llm + trader_memory)"]

    %% ===== 第四阶段：风控辩论（无工具，无 memory） =====
    Trader -->|"输出 trader_investment_plan"| Agg["Aggressive Analyst\n(quick_think_llm)"]

    Agg -->|"count < 3 × max_risk_discuss_rounds"| Con["Conservative Analyst\n(quick_think_llm)"]
    Agg -->|"count ≥ 3 × max_risk_discuss_rounds"| PM["Portfolio Manager\n(deep_think_llm + pm_memory)"]

    Con -->|"count < 3 × max_risk_discuss_rounds"| Neu["Neutral Analyst\n(quick_think_llm)"]
    Con -->|"count ≥ 3 × max_risk_discuss_rounds"| PM

    Neu -->|"count < 3 × max_risk_discuss_rounds"| Agg
    Neu -->|"count ≥ 3 × max_risk_discuss_rounds"| PM

    %% ===== 输出 =====
    PM -->|"输出 final_trade_decision\nBuy / Overweight / Hold / Underweight / Sell"| END([END])
```

> **注**:
> - 分析师数量和顺序由 `selected_analysts` 列表决定，默认为 `["market", "social", "news", "fundamentals"]`。
> - **仅第一阶段（分析师）使用工具**，后续阶段全部是纯 LLM 文本交互。
> - 投资辩论和风控辩论中，**每个节点**都独立调用同一个条件路由函数判断是否终止。
> - `Msg Clear` 使用 `RemoveMessage` 删除所有 messages，仅保留 `HumanMessage("Continue")`，防止多分析师消息叠加撑爆上下文。

### 9.3 条件路由逻辑详细

**分析师工具路由** (`should_continue_{type}`):
- 检查 `messages[-1].tool_calls` 是否存在
- 有工具调用 → `"tools_{type}"` (执行工具后返回分析师继续)
- 无工具调用 → `"Msg Clear {Type}"` (清除消息, 进入下一阶段)

**投资辩论路由** (`should_continue_debate`, 同时应用于 Bull Researcher 和 Bear Researcher 两个节点):
- `count >= 2 * max_debate_rounds` → `"Research Manager"` (结束辩论)
- `current_response` 以 `"Bull"` 开头 → `"Bear Researcher"` (轮到看空方)
- 否则 → `"Bull Researcher"` (轮到看多方)

**风控辩论路由** (`should_continue_risk_analysis`, 同时应用于 Aggressive、Conservative、Neutral 三个节点):
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
    "max_recur_limit": 100,              # ⚠️ 此配置项当前未生效：Propagator() 初始化时未读取此值，递归限制硬编码为 100

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
   → ⚠️ normalize_ticker_symbol() (strip + upper) 定义于 cli/utils.py，但实际 CLI 流程中
     main.py 的本地 get_ticker() 函数 shadow 了它，使用 typer.prompt 且未调用归一化
2. 选择分析日期 (YYYY-MM-DD, 含格式校验 + 拒绝未来日期)
3. 选择启用的分析师 (多选 checkbox: Market/Social/News/Fundamentals)
4. 选择研究深度:
   - Shallow (1轮) / Medium (3轮) / Deep (5轮)
   → 同时设置 max_debate_rounds 和 max_risk_discuss_rounds
5. 选择 LLM 供应商 (OpenAI/Google/Anthropic/xAI/Openrouter/Ollama)
   → 返回 (display_name, base_url) 元组
6. 选择 Quick Thinking 模型 + Deep Thinking 模型 (选项随供应商变化，合并为一步)
7. [供应商特定] 思维配置 (仅在对应供应商时出现):
   - OpenAI → 选择 Reasoning Effort (Medium/High/Low)
   - Anthropic → 选择 Effort Level (High/Medium/Low)
   - Google → 选择 Thinking Mode (Enable/Minimal)
8. 执行分析 (实时展示进度)
```

### 11.2 MessageBuffer (实时状态追踪)

`MessageBuffer` 是 CLI 层的核心状态管理类:

- **agent_status**: 动态追踪每个智能体的 `pending` / `in_progress` / `completed` / `error` 状态
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
| 数据存储 | `redis` (>=6.2.0) | ⚠️ 在 pyproject.toml 中存在，但当前代码中无任何使用，用途待确认 |
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
