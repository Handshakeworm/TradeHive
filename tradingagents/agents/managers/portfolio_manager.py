import json
import logging

from tradingagents.agents.utils.agent_utils import build_instrument_context
from tradingagents.agents.utils.schemas import (
    PortfolioManagerDecision,
    invoke_structured,
)

logger = logging.getLogger(__name__)

# Hard position limits per regime (min%, max%)
REGIME_POSITION_LIMITS = {
    "confirmed_uptrend": (75, 100),
    "early_uptrend": (30, 60),
    "consolidation": (0, 15),
    "topping": (20, 40),
    "early_downtrend": (0, 10),
    "confirmed_downtrend": (0, 0),
    "bottoming": (5, 20),
}


def create_portfolio_manager(llm, memory):
    def portfolio_manager_node(state) -> dict:
        instrument_context = build_instrument_context(state["company_of_interest"])

        history = state["risk_debate_state"]["history"]
        risk_debate_state = state["risk_debate_state"]

        # Bull/Bear structured evaluations
        bull = json.loads(state.get("bull_structured_output", "{}"))
        bear = json.loads(state.get("bear_structured_output", "{}"))

        # Trader's quantitative plan
        trader_plan_raw = state["trader_investment_plan"]
        try:
            trader_plan = json.loads(trader_plan_raw)
        except (json.JSONDecodeError, TypeError):
            trader_plan = {"action": "Hold", "target_position_pct": 0, "reasoning": trader_plan_raw}

        # Parse RM's market regime
        rm_plan_raw = state.get("investment_plan", "{}")
        try:
            rm_plan = json.loads(rm_plan_raw)
        except (json.JSONDecodeError, TypeError):
            rm_plan = {}
        market_regime = rm_plan.get("market_regime", "consolidation")

        # Position context
        position_pct = state.get("current_position_pct", 0)
        avg_cost = state.get("avg_cost", 0)
        total_capital = state.get("total_capital", 0)
        unrealized_pnl = state.get("unrealized_pnl_pct", 0)
        last_action = state.get("last_action", "Hold")

        prev_reasoning = state.get("prev_reasoning", "")
        current_price = state.get("current_price", 0)

        # Regime position limits for prompt and code clamp
        pos_min, pos_max = REGIME_POSITION_LIMITS.get(market_regime, (0, 100))

        # Past memories
        memory_key = f"{bull.get('core_thesis', '')}\n\n{bear.get('core_thesis', '')}"
        past_memories = memory.get_memories(memory_key, n_matches=2)
        past_memory_str = "\n\n".join(rec["recommendation"] for rec in past_memories)

        # Format Bull/Bear summary for PM context
        bull_bear_lines = []
        for dim in ("fundamentals", "technicals", "macro", "sentiment"):
            bs = bull.get(f"{dim}_score", "?")
            be = bear.get(f"{dim}_score", "?")
            bull_bear_lines.append(f"  {dim.capitalize()}: Bull {bs}/10 vs Bear {be}/10")
        bull_bear_lines.append(f"  Bull conviction: {bull.get('overall_conviction', '?')}/10 — {bull.get('core_thesis', '')}")
        bull_bear_lines.append(f"  Bear conviction: {bear.get('overall_conviction', '?')}/10 — {bear.get('core_thesis', '')}")
        bull_signals = bull.get("reversal_signals", [])
        bear_signals = bear.get("reversal_signals", [])
        if bull_signals:
            bull_bear_lines.append(f"  Bull topping signals ({len(bull_signals)}): {'; '.join(bull_signals)}")
        if bear_signals:
            bull_bear_lines.append(f"  Bear bottoming signals ({len(bear_signals)}): {'; '.join(bear_signals)}")
        bull_bear_summary = "\n".join(bull_bear_lines)

        prompt = f"""As the Portfolio Manager, you make the final trading decision. Synthesize the risk analysts' debate and the Trader's proposed plan into a definitive, executable instruction.

{instrument_context}

The Research Manager identified the current market regime as: **{market_regime}**

**Bull/Bear Evaluation Summary:**
{bull_bear_summary}

**Trader's Proposed Plan:**
- Action: {trader_plan.get('action', 'Hold')}
- Target position: {trader_plan.get('target_position_pct', 0)}% of capital
- Reasoning: {trader_plan.get('reasoning', 'N/A')}

Yesterday's reasoning: {prev_reasoning or "(First day — no prior decision)"}
Current stock price: ${current_price:.2f}

**Current Position:**
- Position: {position_pct:.1f}% of capital (${total_capital:,.0f} total)
- Average cost: ${avg_cost:.2f}
- Unrealized PnL: {unrealized_pnl:.1f}%
- Last action: {last_action}

**Execution rule:** Trades are executed at next trading day's market open at market price.

**Your task — deliver the final parameters:**
1. **action**: Buy, Sell, or Hold. **Definition based on current position ({position_pct:.1f}%):**
   - **Buy** = target_position_pct HIGHER than current position (increasing exposure)
   - **Sell** = target_position_pct LOWER than current position (reducing exposure)
   - **Hold** = target_position_pct roughly the SAME as current position (within ±3%)
   The action label MUST be consistent with your target_position_pct relative to the current position.
2. **target_position_pct**: The total position size after that execution, as a percentage of total capital (0 = no position, 100 = all capital invested). May differ from Trader's proposal based on risk debate.

**Position sizing by market regime (HARD LIMITS — you MUST NOT exceed these ranges):**
- confirmed_uptrend: 75-100%  |  early_uptrend: 30-60%  |  consolidation: 0-15%
- topping: 20-40%  |  early_downtrend: 0-10%  |  confirmed_downtrend: 0%  |  bottoming: 5-20%

**The current regime is {market_regime}, so your target_position_pct MUST be between {pos_min}% and {pos_max}%. Any value outside this range is invalid and will be clamped by the system.**

**Risk gatekeeping rules:**
- Current position is {position_pct:.1f}%. Ensure the final decision is both profitable AND survivable (survivable = the position size can withstand a sharp single-day adverse move without causing a drawdown that would force a panic exit).
- The regime position limits above are non-negotiable. Do NOT override them based on your own conviction or fundamental analysis.
- In a confirmed uptrend, don't be afraid of large positions.
- In unclear or deteriorating conditions, capital preservation takes priority.

**CRITICAL — Address the risk debate:**
You MUST explicitly address each risk analyst's key argument in your reasoning. For each major point raised in the debate below, state whether you adopt or reject it, and why. Do NOT simply say "I have considered the debate" — you must engage with specific arguments.

**Past decision lessons:**
"{past_memory_str}"

**Risk Analysts Debate History:**
{history}

Be decisive. Ground every conclusion in specific evidence."""

        decision = invoke_structured(llm, PortfolioManagerDecision, prompt)

        # Code-enforced regime position clamp
        raw_pct = decision.target_position_pct
        clamped_pct = max(pos_min, min(pos_max, raw_pct))
        if clamped_pct != raw_pct:
            logger.warning(
                "PM position clamped: %.1f%% → %.1f%% (regime %s allows %d-%d%%)",
                raw_pct, clamped_pct, market_regime, pos_min, pos_max,
            )
            # Determine correct action label after clamp
            if clamped_pct > position_pct + 3:
                clamped_action = "Buy"
            elif clamped_pct < position_pct - 3:
                clamped_action = "Sell"
            else:
                clamped_action = "Hold"
            decision = PortfolioManagerDecision(
                action=clamped_action,
                target_position_pct=clamped_pct,
                reasoning=decision.reasoning + f" [Clamped from {raw_pct:.1f}% to {clamped_pct:.1f}% by regime limit]",
            )

        decision_json = decision.model_dump_json()

        new_risk_debate_state = {
            "judge_decision": decision_json,
            "history": risk_debate_state["history"],
            "aggressive_history": risk_debate_state["aggressive_history"],
            "conservative_history": risk_debate_state["conservative_history"],
            "neutral_history": risk_debate_state["neutral_history"],
            "latest_speaker": "Judge",
            "current_aggressive_response": risk_debate_state["current_aggressive_response"],
            "current_conservative_response": risk_debate_state["current_conservative_response"],
            "current_neutral_response": risk_debate_state["current_neutral_response"],
            "count": risk_debate_state["count"],
        }

        return {
            "risk_debate_state": new_risk_debate_state,
            "final_trade_decision": decision_json,
        }

    return portfolio_manager_node
