from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import time
import json
from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_global_news,
    get_insider_transactions,
    get_news,
)
from tradingagents.dataflows.config import get_config


def create_news_analyst(llm):
    def news_analyst_node(state):
        current_date = state["trade_date"]
        instrument_context = build_instrument_context(state["company_of_interest"])

        tools = [
            get_news,
            get_global_news,
            get_insider_transactions,
        ]

        system_message = (
            "You are a news researcher tasked with analyzing recent news and trends over the past week. "
            "Your workflow: "
            "1) Call get_news(ticker, start_date, end_date) for company-specific news and sentiment. "
            "2) Call get_global_news(curr_date, look_back_days, limit) for broader macroeconomic and sector news. "
            "3) Call get_insider_transactions(ticker, curr_date) to check recent insider buying/selling activity — significant insider sales or purchases can signal management's confidence level. "
            "Write a comprehensive report covering company-specific developments, sector trends, macro context, and insider activity. Provide specific, actionable insights with supporting evidence."
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
        result = chain.invoke(state["news_messages"])

        report = ""

        if len(result.tool_calls) == 0:
            report = result.content

        return {
            "news_messages": [result],
            "news_report": report,
        }

    return news_analyst_node
