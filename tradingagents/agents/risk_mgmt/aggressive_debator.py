import json


def _bull_bear_scores_summary(bull, bear):
    """One-line per dimension for risk debate context."""
    lines = []
    for dim in ("fundamentals", "technicals", "macro", "sentiment"):
        bs = bull.get(f"{dim}_score", "?")
        be = bear.get(f"{dim}_score", "?")
        lines.append(f"  {dim.capitalize()}: Bull {bs}/10 vs Bear {be}/10")
    lines.append(f"  Bull conviction: {bull.get('overall_conviction', '?')}/10 | Bear conviction: {bear.get('overall_conviction', '?')}/10")
    bull_signals = bull.get("reversal_signals", [])
    bear_signals = bear.get("reversal_signals", [])
    if bull_signals:
        lines.append(f"  Bull topping signals ({len(bull_signals)}): {'; '.join(bull_signals)}")
    if bear_signals:
        lines.append(f"  Bear bottoming signals ({len(bear_signals)}): {'; '.join(bear_signals)}")
    return "\n".join(lines)


def create_aggressive_debator(llm):
    def aggressive_node(state) -> dict:
        risk_debate_state = state["risk_debate_state"]
        history = risk_debate_state.get("history", "")
        aggressive_history = risk_debate_state.get("aggressive_history", "")

        current_conservative_response = risk_debate_state.get("current_conservative_response", "")
        current_neutral_response = risk_debate_state.get("current_neutral_response", "")

        # Parse Trader's quantitative plan
        trader_plan_raw = state["trader_investment_plan"]
        try:
            trader_plan = json.loads(trader_plan_raw)
        except (json.JSONDecodeError, TypeError):
            trader_plan = {}

        # Parse RM's market regime
        rm_plan_raw = state.get("investment_plan", "{}")
        try:
            rm_plan = json.loads(rm_plan_raw)
        except (json.JSONDecodeError, TypeError):
            rm_plan = {}
        market_regime = rm_plan.get("market_regime", "consolidation")

        # Bull/Bear structured evaluations
        bull = json.loads(state.get("bull_structured_output", "{}"))
        bear = json.loads(state.get("bear_structured_output", "{}"))

        position_pct = state.get("current_position_pct", 0)
        avg_cost = state.get("avg_cost", 0)
        unrealized_pnl = state.get("unrealized_pnl_pct", 0)
        current_price = state.get("current_price", 0)

        count = risk_debate_state.get("count", 0)

        if count == 0:
            data_context = f"""Bull/Bear evaluation summary:
{_bull_bear_scores_summary(bull, bear)}"""
        else:
            data_context = ""

        prompt = f"""As the Aggressive Risk Analyst, your role is to argue for MAXIMIZING returns by taking on more risk. You are reviewing the Trader's specific plan and debating whether the parameters are too conservative.

The Research Manager identified the current market regime as: **{market_regime}**
Current position is {position_pct:.1f}% (avg cost: ${avg_cost:.2f}, unrealized PnL: {unrealized_pnl:.1f}%). Current price: ${current_price:.2f}

**Evaluate these dimensions:**
1. Does Trader's position size match the current market regime?
2. Is the proposed change from the current position ({position_pct:.1f}%) reasonable, or is it too conservative a swing?
3. If holding a large position, is the uptrend still intact — or are there reversal signals being ignored?

**Execution rule:** Trades are executed at next trading day's market open at market price. target_position_pct is the total position size after that execution, as a percentage of total capital (0% = no position, 100% = all capital invested).

**Trader's Proposed Plan:**
- Action: {trader_plan.get('action', 'N/A')}
- Target position: {trader_plan.get('target_position_pct', 'N/A')}% of capital

**Your stance — argue for bolder parameters:**
- Position size should be LARGER (e.g. if Trader says 30%, argue for 50%+)
- In favorable conditions, the Trader is being too timid

Respond directly to the conservative and neutral analysts' specific counter-arguments. Use data to support why higher risk is justified here.

{data_context}
Conversation history: {history}
Last conservative argument: {current_conservative_response}
Last neutral argument: {current_neutral_response}

If there are no responses from the other viewpoints yet, present your own argument based on the available data. Speak conversationally without special formatting."""

        response = llm.invoke(prompt)

        argument = f"Aggressive Analyst: {response.content}"

        new_risk_debate_state = {
            "history": history + "\n" + argument,
            "aggressive_history": aggressive_history + "\n" + argument,
            "conservative_history": risk_debate_state.get("conservative_history", ""),
            "neutral_history": risk_debate_state.get("neutral_history", ""),
            "latest_speaker": "Aggressive",
            "current_aggressive_response": argument,
            "current_conservative_response": risk_debate_state.get("current_conservative_response", ""),
            "current_neutral_response": risk_debate_state.get("current_neutral_response", ""),
            "count": risk_debate_state["count"] + 1,
        }

        return {"risk_debate_state": new_risk_debate_state}

    return aggressive_node
