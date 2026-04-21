# TradingAgents/graph/conditional_logic.py

from tradingagents.agents.utils.agent_states import AgentState


class ConditionalLogic:
    """Handles conditional logic for determining graph flow."""

    def __init__(self, max_risk_discuss_rounds=1):
        """Initialize with configuration parameters."""
        self.max_risk_discuss_rounds = max_risk_discuss_rounds

    @staticmethod
    def _has_pending_tool_calls_for(state: AgentState, messages_key: str) -> bool:
        """Check if the last message in a per-analyst channel has pending tool calls."""
        last_message = state[messages_key][-1]
        if last_message.tool_calls:
            return True
        if getattr(last_message, "invalid_tool_calls", None):
            return True
        return False

    def should_continue_market(self, state: AgentState):
        if self._has_pending_tool_calls_for(state, "market_messages"):
            return "tools_market"
        return "Msg Clear Market"

    def should_continue_sentiment(self, state: AgentState):
        if self._has_pending_tool_calls_for(state, "sentiment_messages"):
            return "tools_sentiment"
        return "Msg Clear Sentiment"

    def should_continue_news(self, state: AgentState):
        if self._has_pending_tool_calls_for(state, "news_messages"):
            return "tools_news"
        return "Msg Clear News"

    def should_continue_fundamentals(self, state: AgentState):
        if self._has_pending_tool_calls_for(state, "fundamentals_messages"):
            return "tools_fundamentals"
        return "Msg Clear Fundamentals"

    def should_continue_macro(self, state: AgentState):
        if self._has_pending_tool_calls_for(state, "macro_messages"):
            return "tools_macro"
        return "Msg Clear Macro"


    def should_continue_risk_analysis(self, state: AgentState) -> str:
        """Determine if risk analysis should continue."""
        if (
            state["risk_debate_state"]["count"] >= 3 * self.max_risk_discuss_rounds
        ):  # 3 rounds of back-and-forth between 3 agents
            return "Portfolio Manager"
        if state["risk_debate_state"]["latest_speaker"].startswith("Aggressive"):
            return "Conservative Analyst"
        if state["risk_debate_state"]["latest_speaker"].startswith("Conservative"):
            return "Neutral Analyst"
        return "Aggressive Analyst"
