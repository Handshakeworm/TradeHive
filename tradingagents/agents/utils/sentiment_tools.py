from langchain_core.tools import tool
from typing import Annotated
from tradingagents.dataflows.interface import route_to_vendor


@tool
def get_reddit_sentiment(
    ticker: Annotated[str, "Stock or crypto ticker symbol"],
    date: Annotated[str, "Reference date in yyyy-mm-dd format"],
    subreddits: Annotated[
        str,
        "Comma-separated subreddits, e.g. 'wallstreetbets,stocks,investing'",
    ] = "wallstreetbets,stocks,investing",
    limit: Annotated[int, "Max posts per subreddit"] = 25,
) -> str:
    """
    Scrape Reddit posts about a ticker and score each post's sentiment
    using VADER. Requires REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET in
    environment (free Reddit API credentials). Falls back gracefully with
    a setup guide if credentials are not configured.
    Args:
        ticker: Stock or crypto ticker symbol
        date: Reference date
        subreddits: Comma-separated list of subreddits to search
        limit: Max posts per subreddit (default 25)
    Returns:
        Formatted sentiment report with per-post scores and aggregate stats
    """
    return route_to_vendor("get_reddit_sentiment", ticker, date, subreddits, limit)
