import json

from tradingagents.agents.risk_mgmt.aggressive_debator import _bull_bear_scores_summary


def create_neutral_debator(llm):
    def neutral_node(state) -> dict:
        risk_debate_state = state["risk_debate_state"]
        history = risk_debate_state.get("history", "")
        neutral_history = risk_debate_state.get("neutral_history", "")

        current_aggressive_response = risk_debate_state.get("current_aggressive_response", "")
        current_conservative_response = risk_debate_state.get("current_conservative_response", "")

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
            data_context = "Use the debate history to support a balanced strategy."

        prompt = f"""As the Neutral Risk Analyst, your role is to provide a balanced perspective on the Trader's plan. Evaluate whether the proposed parameters strike the right balance between risk and reward.

The Research Manager identified the current market regime as: **{market_regime}**
Current position is {position_pct:.1f}% (avg cost: ${avg_cost:.2f}, unrealized PnL: {unrealized_pnl:.1f}%). Current price: ${current_price:.2f}

**Evaluate these dimensions:**
1. Does Trader's position size match the current market regime?
2. Is the proposed change from the current position ({position_pct:.1f}%) reasonable, or is it too aggressive a swing?
3. If holding a large position, is the uptrend still intact — or are there reversal signals being ignored?

**Execution rule:** Trades are executed at next trading day's market open at market price. target_position_pct is the total position size after that execution, as a percentage of total capital (0% = no position, 100% = all capital invested).

**Trader's Proposed Plan:**
- Action: {trader_plan.get('action', 'N/A')}
- Target position: {trader_plan.get('target_position_pct', 'N/A')}% of capital

**Your stance — argue for balanced parameters:**
- Position size: evaluate if it matches the conviction level and market conditions
- Weigh opportunity cost of being too cautious against the risk of being too aggressive

Challenge both the aggressive and conservative analysts. Point out where the aggressive stance takes unnecessary gambles AND where the conservative stance leaves money on the table.

{data_context}
Conversation history: {history}
Last aggressive argument: {current_aggressive_response}
Last conservative argument: {current_conservative_response}

If there are no responses from the other viewpoints yet, present your own argument based on the available data. Speak conversationally without special formatting."""

        response = llm.invoke(prompt)

        argument = f"Neutral Analyst: {response.content}"

        new_risk_debate_state = {
            "history": history + "\n" + argument,
            "aggressive_history": risk_debate_state.get("aggressive_history", ""),
            "conservative_history": risk_debate_state.get("conservative_history", ""),
            "neutral_history": neutral_history + "\n" + argument,
            "latest_speaker": "Neutral",
            "current_aggressive_response": risk_debate_state.get("current_aggressive_response", ""),
            "current_conservative_response": risk_debate_state.get("current_conservative_response", ""),
            "current_neutral_response": argument,
            "count": risk_debate_state["count"] + 1,
        }

        return {"risk_debate_state": new_risk_debate_state}

    return neutral_node
