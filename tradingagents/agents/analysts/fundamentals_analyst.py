from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import time
import json
from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_balance_sheet,
    get_cashflow,
    get_fundamentals,
    get_income_statement,
)
from tradingagents.dataflows.config import get_config


def create_fundamentals_analyst(llm):
    def fundamentals_analyst_node(state):
        current_date = state["trade_date"]
        instrument_context = build_instrument_context(state["company_of_interest"])

        tools = [
            get_fundamentals,
            get_balance_sheet,
            get_cashflow,
            get_income_statement,
        ]

        system_message = (
            "You are a fundamental analyst tasked with assessing a company's financial health and valuation. "
            "Your workflow: "
            "1) Call get_fundamentals(ticker, curr_date) for key ratios — P/E, P/B, P/S, ROE, margins, EPS, etc. "
            "2) Call get_balance_sheet(ticker, curr_date) to assess debt structure, cash position, and equity trends. "
            "3) Call get_cashflow(ticker, curr_date) to evaluate operating cash flow, free cash flow, and capex. "
            "4) Call get_income_statement(ticker, curr_date) to analyze revenue growth, margin trends, and earnings quality. "
            "Your report MUST cover these dimensions: "
            "(a) Profitability: margins, ROE, earnings growth trajectory. "
            "(b) Financial health: debt-to-equity, current ratio, cash reserves. "
            "(c) Growth: revenue and earnings growth rates, YoY trends across multiple years. "
            "(d) Valuation: P/E, P/B, P/S — is the stock cheap or expensive relative to its historical range and growth? "
            "(e) Cash flow quality: FCF generation, capex intensity, dividend/buyback sustainability. "
            "Append a Markdown summary table at the end."
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

        result = chain.invoke(state["fundamentals_messages"])

        report = ""

        if len(result.tool_calls) == 0:
            report = result.content

        return {
            "fundamentals_messages": [result],
            "fundamentals_report": report,
        }

    return fundamentals_analyst_node
