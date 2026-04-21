from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import time
import json
from tradingagents.agents.utils.agent_utils import build_instrument_context
from tradingagents.agents.utils.sentiment_tools import get_sentiment_summary, get_vix
from tradingagents.dataflows.config import get_config


def create_sentiment_analyst(llm):
    def sentiment_analyst_node(state):
        current_date = state["trade_date"]
        instrument_context = build_instrument_context(state["company_of_interest"])

        tools = [
            get_sentiment_summary,
            get_vix,
        ]

        system_message = (
            "You are a sentiment analyst tasked with quantifying and interpreting market sentiment for a specific company. "
            "Your workflow: "
            "1) Call get_sentiment_summary(ticker, start_date, end_date) to get a daily aggregated sentiment table — this shows average sentiment scores, bullish/neutral/bearish article counts per day, and the overall period average. "
            "2) Call get_vix(start_date, end_date) to get the VIX volatility index as macroeconomic fear/greed context for the same period. "
            "Your report must include: a quantitative sentiment trend section (referencing the daily scores from get_sentiment_summary), VIX context (whether market fear elevated or suppressed sentiment), and an overall sentiment verdict. "
            "Focus on patterns in the data: sudden sentiment shifts, divergence between sentiment and VIX, sustained bullish/bearish streaks, etc."
            + """ Make sure to append a Markdown table at the end of the report to organize key points in the report, organized and easy to read."""
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are an analyst assistant. Your ONLY job is to produce a factual research report."
                    " Do NOT make any trading recommendations, buy/sell/hold proposals, or suggest entry/exit prices, stop-losses, or take-profit levels."
                    " Use the provided tools to gather data and write your report."
                    " If you are unable to fully answer, that's OK; another assistant with different tools"
                    " will help where you left off. Execute what you can to make progress."
                    " You have access to the following tools: {tool_names}.\n{system_message}"
                    "For your reference, the current date is {current_date}. {instrument_context}",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(instrument_context=instrument_context)

        chain = prompt | llm.bind_tools(tools)

        result = chain.invoke(state["sentiment_messages"])

        report = ""

        if len(result.tool_calls) == 0:
            report = result.content

        return {
            "sentiment_messages": [result],
            "sentiment_report": report,
        }

    return sentiment_analyst_node
