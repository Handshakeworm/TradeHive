import json
import logging

from tradingagents.agents.utils.agent_utils import build_instrument_context
from tradingagents.agents.utils.schemas import TraderDecision, invoke_structured

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


def _format_bull_bear_summary(bull, bear):
    """Format Bull/Bear evaluations as a concise comparison for the Trader prompt."""
    lines = ["## Bull vs Bear Comparison\n"]
    for dim in ("fundamentals", "technicals", "macro", "sentiment"):
        bs = bull.get(f"{dim}_score", "?")
        be = bear.get(f"{dim}_score", "?")
        lines.append(f"**{dim.capitalize()}**: Bull {bs}/10 vs Bear {be}/10")
        # Top evidence from each side
        for e in bull.get(f"{dim}_evidence", [])[:2]:
            lines.append(f"  + {e}")
        for e in bear.get(f"{dim}_evidence", [])[:2]:
            lines.append(f"  - {e}")

    lines.append(f"\n**Bull conviction**: {bull.get('overall_conviction', '?')}/10 — {bull.get('core_thesis', '')}")
    lines.append(f"**Bear conviction**: {bear.get('overall_conviction', '?')}/10 — {bear.get('core_thesis', '')}")
    lines.append(f"**Bull time horizon**: {bull.get('time_horizon', '?')}")
    lines.append(f"**Bear time horizon**: {bear.get('time_horizon', '?')}")

    bull_signals = bull.get("reversal_signals", [])
    bear_signals = bear.get("reversal_signals", [])
    if bull_signals:
        lines.append(f"\n**Bull topping signals** ({len(bull_signals)}):")
        for s in bull_signals:
            lines.append(f"  ⚠ {s}")
    if bear_signals:
        lines.append(f"\n**Bear bottoming signals** ({len(bear_signals)}):")
        for s in bear_signals:
            lines.append(f"  ⚠ {s}")

    return "\n".join(lines)


def create_trader(llm, memory):
    def trader_node(state) -> dict:
        company_name = state["company_of_interest"]
        instrument_context = build_instrument_context(company_name)

        # Research Manager's regime judgment
        investment_plan = state["investment_plan"]
        try:
            rm_decision = json.loads(investment_plan)
        except (json.JSONDecodeError, TypeError):
            rm_decision = {"market_regime": "consolidation", "entry_thesis": str(investment_plan)}
        market_regime = rm_decision.get("market_regime", "consolidation")

        # Bull/Bear structured evaluations
        bull = json.loads(state.get("bull_structured_output", "{}"))
        bear = json.loads(state.get("bear_structured_output", "{}"))
        bull_bear_summary = _format_bull_bear_summary(bull, bear)

        # Position context
        position_pct = state.get("current_position_pct", 0)
        avg_cost = state.get("avg_cost", 0)
        total_capital = state.get("total_capital", 0)
        unrealized_pnl = state.get("unrealized_pnl_pct", 0)
        last_action = state.get("last_action", "Hold")

        current_price = state.get("current_price", 0)

        # Past memories
        memory_key = f"{bull.get('core_thesis', '')}\n\n{bear.get('core_thesis', '')}"
        past_memories = memory.get_memories(memory_key, n_matches=2)
        past_memory_str = "\n\n".join(rec["recommendation"] for rec in past_memories) if past_memories else "No past memories found."

        prompt = f"""You are the Execution Planner (Trader). The Research Manager has identified the market regime. Your job is to decide the trading direction AND translate it into a concrete, quantitative trading plan.

{instrument_context}

**Market Regime (from Research Manager):** {market_regime}
**RM Entry Thesis:** {rm_decision.get('entry_thesis', 'N/A')}

{bull_bear_summary}

Current stock price: ${current_price:.2f}

**Current Position:**
- Position: {position_pct:.1f}% of capital (${total_capital:,.0f} total)
- Average cost: ${avg_cost:.2f}
- Unrealized PnL: {unrealized_pnl:.1f}%
- Last action: {last_action}

**Execution rule:** Trades are executed at next trading day's market open at market price.

**Your task — decide direction AND position size:**
1. **action**: Buy, Sell, or Hold. Use Bull/Bear evaluations to decide direction:
   - If Bull conviction significantly exceeds Bear → lean Buy
   - If Bear conviction significantly exceeds Bull → lean Sell
   - If roughly balanced or regime is consolidation → lean Hold
   **Definition based on current position ({position_pct:.1f}%):**
   - **Buy** = target_position_pct HIGHER than current position
   - **Sell** = target_position_pct LOWER than current position
   - **Hold** = target_position_pct roughly the SAME (within ±3%)
   The action label MUST be consistent with your target_position_pct relative to the current position.
2. **target_position_pct**: Total position size after execution (0-100%).

**Position sizing by market regime:**
- confirmed_uptrend: 75-100%  |  early_uptrend: 30-60%  |  consolidation: 0-15%
- topping: 20-40%  |  early_downtrend: 0-10%  |  confirmed_downtrend: 0%  |  bottoming: 5-20%

Within each range, use Bull/Bear conviction scores to fine-tune. Higher Bull conviction → higher end of range. More reversal signals → lower end.

**Past trading lessons:**
{past_memory_str}

Ground your reasoning in specific evidence from the Bull/Bear evaluations above."""

        decision = invoke_structured(llm, TraderDecision, prompt)

        # Code-enforced regime position clamp
        pos_min, pos_max = REGIME_POSITION_LIMITS.get(market_regime, (0, 100))
        raw_pct = decision.target_position_pct
        clamped_pct = max(pos_min, min(pos_max, raw_pct))
        if clamped_pct != raw_pct:
            logger.warning(
                "Trader position clamped: %.1f%% → %.1f%% (regime %s allows %d-%d%%)",
                raw_pct, clamped_pct, market_regime, pos_min, pos_max,
            )
            if clamped_pct > position_pct + 3:
                clamped_action = "Buy"
            elif clamped_pct < position_pct - 3:
                clamped_action = "Sell"
            else:
                clamped_action = "Hold"
            decision = TraderDecision(
                action=clamped_action,
                target_position_pct=clamped_pct,
                reasoning=decision.reasoning + f" [Clamped from {raw_pct:.1f}% to {clamped_pct:.1f}% by regime limit]",
            )

        decision_json = decision.model_dump_json()

        return {
            "messages": [],
            "trader_investment_plan": decision_json,
            "sender": "Trader",
        }

    return trader_node
