from langchain_core.tools import tool
from typing import Annotated
from tradingagents.dataflows.interface import route_to_vendor

@tool
def get_indicators(
    symbol: Annotated[str, "ticker symbol of the company"],
    indicator: Annotated[str, "one or more indicator names, comma-separated, e.g. 'rsi,macd,boll,atr'"],
    curr_date: Annotated[str, "The current trading date you are trading on, YYYY-mm-dd"],
    look_back_days: Annotated[int, "how many days to look back"] = 30,
) -> str:
    """
    Retrieve technical indicators for a given ticker symbol.
    You can request multiple indicators in a single call by passing a comma-separated string.
    Example: indicator='rsi,macd,macds,macdh,boll,boll_ub,boll_lb,atr'
    Args:
        symbol (str): Ticker symbol of the company, e.g. AAPL, TSM
        indicator (str): Comma-separated indicator names, e.g. 'rsi,macd,boll,atr'
        curr_date (str): The current trading date you are trading on, YYYY-mm-dd
        look_back_days (int): How many days to look back, default is 30
    Returns:
        str: Formatted data for each requested indicator.
    """
    # LLMs sometimes pass multiple indicators as a comma-separated string;
    # split and process each individually.
    indicators = [i.strip() for i in indicator.split(",") if i.strip()]
    if len(indicators) > 1:
        results = []
        for ind in indicators:
            results.append(route_to_vendor("get_indicators", symbol, ind, curr_date, look_back_days))
        return "\n\n".join(results)
    return route_to_vendor("get_indicators", symbol, indicator.strip(), curr_date, look_back_days)