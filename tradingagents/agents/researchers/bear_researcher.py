import logging

from tradingagents.agents.utils.schemas import BullBearEvaluation, invoke_structured, filter_reversal_signals

logger = logging.getLogger(__name__)


def create_bear_researcher(llm, memory):
    def bear_node(state) -> dict:
        market_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]
        macro_report = state["macro_report"]
        prev_regime = state.get("prev_regime", "consolidation")

        # Memory retrieval
        curr_situation = (
            f"{market_report}\n\n{sentiment_report}\n\n{news_report}\n\n"
            f"{fundamentals_report}\n\n{macro_report}"
        )
        past_memories = memory.get_memories(curr_situation, n_matches=2)
        past_memory_str = "\n\n".join(rec["recommendation"] for rec in past_memories)

        prompt = f"""You are the Bear Evaluator. Your job is to objectively assess all BEARISH (negative/risk) evidence from the 5 analyst reports below, and identify any bottoming/reversal signals even if the overall picture looks negative.

Current market regime (from previous day): **{prev_regime}**

## Regime State Machine
7 regimes and their legal next-day transitions (each regime can also stay unchanged):
- **confirmed_uptrend** → topping
- **early_uptrend** → confirmed_uptrend | consolidation
- **consolidation** → early_uptrend | early_downtrend
- **topping** → consolidation | early_downtrend | early_uptrend (last = false-alarm recovery back to uptrend)
- **early_downtrend** → confirmed_downtrend | consolidation
- **confirmed_downtrend** → bottoming
- **bottoming** → consolidation | early_uptrend | early_downtrend (last = false-alarm recovery back to downtrend)

As the Bear evaluator, identify evidence supporting movement along the **downward path** or staying in a bearish state from the current regime ({prev_regime}).

## Analyst Reports

### Market Analysis (Technical + Position Structure)
{market_report}

### Sentiment Analysis
{sentiment_report}

### News Analysis
{news_report}

### Fundamentals Analysis
{fundamentals_report}

### Macro Analysis
{macro_report}

### Lessons from similar past situations
{past_memory_str}

## Your Task

1. **Classify evidence into 4 dimensions** (fundamentals, technicals, macro, sentiment). Each piece of information goes into the single most relevant dimension.

2. **Filter for bearish evidence**: In the context of the current regime ({prev_regime}), select evidence that supports downgrading or maintaining the regime along the state machine's downward path. For each dimension, list up to 5 key points ranked by importance.

3. **Reversal signal check**: Even though you are the Bear evaluator, honestly check for BOTTOMING signals. There are ONLY four valid signal types:
   - Volume-price divergence: price is making a NEW swing low (lower than any close in the past 20 trading days), yet volume on that decline is clearly lower than the volume on the prior sell-off leg that set the previous low — indicates selling pressure exhausting at the bottom. Normal volume fluctuations during consolidation or mild bounces do NOT qualify.
   - Extreme news sentiment: the news sentiment scores from analyst reports are overwhelmingly and uniformly negative with near-zero positive coverage — contrarian warning of panic capitulation. This signal only applies when current sentiment is at an extreme negative level; a recovery in sentiment from negative to neutral/positive does NOT qualify.
   - Price desensitization to bad news: a specific, clearly negative catalyst (earnings miss, major contract loss, adverse policy) occurred, but the stock failed to drop or moved up — the market is no longer punishing bad news. The catalyst must be a discrete event, not a general trend.
   - **Decisive capitulation reversal**: a single-day sharp upward move against the downtrend (daily change ≥ +8% on volume ≥ 1.5x the 20-day average) combined with at least one of — reclaim of a short-term moving average (20 or 30 SMA), RSI lifting sharply off oversold (<30) to neutral (≥50), or broad market breadth reversal where most peer stocks also rally strongly on the same day. This signal type specifically captures V-reversals that the other three types do not cover.

   **CRITICAL RULES for reversal signals:**
   - **Default expectation**: in confirmed_downtrend and early_downtrend regimes, the default number of reversal signals is ZERO. You need strong evidence to override this default. Do NOT list a signal just because the market looks "oversold", "washed out", or "due for a bounce".
   - **Multi-day persistence requirement**: each reversal signal MUST normally be supported by evidence spanning at least **2 consecutive trading days** within the recent market data shown to you. You MUST explicitly cite the specific dates (e.g., "May 19 and May 20 both showed declining volume on price declines"). Single-day observations are noise and do NOT qualify.
   - **Single-day exception for decisive events**: a single trading day showing a decisive reversal event — specifically the "Decisive capitulation reversal" signal type above, or a gap and reclaim of a key moving average on heavy volume — counts as a valid reversal signal even without a second confirming day. The 2-day rule exists to filter noise, NOT to ignore decisive high-conviction single-day events.
   - **Anti-double-counting rule**: lowering your dimension scores (fundamentals, technicals, macro, sentiment) does NOT substitute for listing reversal_signals. If you are scoring any dimension substantially below its default baseline for the current regime because of today's price action, you MUST also list the concrete reversal signals in the reversal_signals field. Dimension scores and reversal_signals serve different downstream consumers — never omit one on the grounds that you already expressed the evidence in the other. In particular: if your Bear technicals_score drops to ≤ 6 in a downtrend due to a strong rebound, you MUST list the corresponding reversal signal(s).
   - If a signal is NOT present, do NOT include it in the list. Output an EMPTY list if no signals are found. Listing "NOT FOUND" or "NOT PRESENT" entries inflates the signal count and corrupts the conviction calculation.
   - Do NOT invent signal types beyond the four above. RSI alone, MACD alone, insider selling, valuation, options positioning, etc. are NOT reversal signals.
   - Each signal MUST cite specific data points with dates (e.g., "volume dropped from 450M on May 19 to 270M on May 20 while price held new low $95").

4. **Score each dimension** (1-10, higher = more bearish) using this scale:
   - 1-2: Evidence is absent or contradicts the bearish position
   - 3-4: Weak evidence, easily countered
   - 5-6: Mixed, no clear edge
   - 7-8: Strong evidence with minor caveats
   - 9-10: Overwhelming, near-unanimous evidence

5. **Conviction reasoning then score**: Calculate your base conviction as the average of your 4 dimension scores (rounded to nearest integer), then explicitly adjust downward for each reversal signal you identified, stating each adjustment. Your final overall_conviction (1-10) must match this calculation.

6. **Time horizon**: How long you expect the bearish risk to persist (e.g., "2-4 weeks", "1-3 months").

7. **Core thesis**: The single most important bearish argument.

Important context for scoring:
- In {prev_regime}, normal technical rebounds or short-term positive news should NOT dramatically lower your bearish score — distinguish between dead-cat bounce and genuine trend reversal
- **Bear technicals baseline in uptrends**: in confirmed_uptrend or early_uptrend regimes, the default Bear technicals_score should be **4-6** (weak bearish technical evidence is the norm in an uptrend). You should score Bear technicals ≥ 7 when there is genuine short-term breakdown evidence — broken key support on volume, trend change confirmation, **breakdown of any short- or medium-term moving average (20 SMA, 30 SMA, or 50 SMA)**, or a high-volume single-day breakdown from extension levels. Overbought RSI alone or generic "due for a pullback" reasoning are NOT bearish technical evidence in an uptrend; they are normal features of trend strength.
- **Bear technicals ceiling in downtrends**: in confirmed_downtrend or early_downtrend regimes, the default Bear technicals_score should be **7-8**, NOT 9-10. Score 9-10 only for rare, decisive acceleration in the last 1-2 sessions — a new panic low on volume expansion ≥ 1.5x the 20-day average, a decisive breakdown of a support level that was previously holding, or a breadth collapse where most peers also break down on the same day. Do NOT score 9-10 just because "price is still below the 50 SMA" or "MACD is still negative" — those are features of the established trend, not fresh deterioration, and reusing them day after day is double-counting. On days when the market shows a clear technical rebound (e.g., a strong up day on volume, RSI lifting off oversold, reclaim of the 20 SMA), the Bear technicals_score should drop to **≤ 6** even if the broader downtrend structure is intact — the stronger and more decisive the rebound, the lower the score (a powerful single-day V-reversal with multiple confirmations can justify 3-5).
- A single piece of overwhelming news (e.g., major policy shock, earnings collapse) can justifiably dominate your overall conviction regardless of other dimension scores
"""

        result = invoke_structured(llm, BullBearEvaluation, prompt)

        # Filter out "NOT FOUND" / "NOT PRESENT" false signals
        result.reversal_signals = filter_reversal_signals(result.reversal_signals)
        result_json = result.model_dump_json()

        logger.info("Bear evaluation: conviction=%d, reversal_signals=%d",
                     result.overall_conviction, len(result.reversal_signals))

        return {"bear_structured_output": result_json}

    return bear_node
