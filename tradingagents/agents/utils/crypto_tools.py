from langchain_core.tools import tool
from typing import Annotated
from tradingagents.dataflows.interface import route_to_vendor



@tool
def get_crypto_historical(
    symbol: Annotated[str, "Crypto ticker symbol, e.g. BTC, ETH"],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
    currency: Annotated[str, "Quote currency, default usd"] = "usd",
) -> str:
    """
    Get daily OHLCV historical data for a cryptocurrency.
    Data columns: date, open, high, low, close, volume, market_cap.
    Uses CoinGecko public API (no API key required).
    Args:
        symbol: Crypto ticker such as BTC, ETH
        start_date: Start date in yyyy-mm-dd format
        end_date: End date in yyyy-mm-dd format
        currency: Quote currency (default: usd)
    Returns:
        CSV-formatted historical price data
    """
    return route_to_vendor("get_crypto_historical", symbol, start_date, end_date, currency)


@tool
def get_crypto_market_overview(
    top_n: Annotated[int, "Number of top coins by market cap"] = 10,
    currency: Annotated[str, "Quote currency, default usd"] = "usd",
) -> str:
    """
    Get a market overview table of the top N cryptocurrencies by market cap,
    including price, 24h change, market cap, and volume.
    Uses CoinGecko public API (no API key required).
    Args:
        top_n: How many top coins to include (default 10)
        currency: Quote currency (default: usd)
    Returns:
        Formatted table of top crypto assets
    """
    return route_to_vendor("get_crypto_market_overview", top_n, currency)
