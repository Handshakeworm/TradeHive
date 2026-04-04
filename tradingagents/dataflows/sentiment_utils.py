"""
情绪���析模块
- VADER（Valence Aware Dictionary and sEntiment Reasoner）：
  专为金融/社交媒体短文本优化的规则+词典情绪分析器，完全离线运行。
- Reddit（可选，需要 Reddit API Key）作为社交数据源。
- 新闻情绪已由 Alpha Vantage NEWS_SENTIMENT API 自带，不再需要本地 VADER 评分。

依赖：pip install vaderSentiment praw（praw 为可选，仅需 Reddit 时安装）
"""

from typing import Annotated
from datetime import datetime, timedelta
import os
import pandas as pd


# ─────────────────────────────────────────────────────────────────────────────
# VADER 情绪评分核心
# ─────────────────────────────────────────────────────────────────────────────

def _get_vader():
    """获取 VADER 情绪分析器实例（懒加载）。"""
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        return SentimentIntensityAnalyzer()
    except ImportError:
        raise ImportError(
            "vaderSentiment 未安装，请运行: pip install vaderSentiment"
        )


def score_text_sentiment(text: str) -> dict:
    """
    对单条文本进行 VADER 情绪评分。
    返回: {"positive": float, "negative": float, "neutral": float, "compound": float}
    compound 分值: -1（极负面）到 +1（极正面），>0.05 为正面，<-0.05 为负面
    """
    sia = _get_vader()
    scores = sia.polarity_scores(text)
    return {
        "positive": round(scores["pos"], 4),
        "negative": round(scores["neg"], 4),
        "neutral": round(scores["neu"], 4),
        "compound": round(scores["compound"], 4),
    }


def _label_sentiment(compound: float) -> str:
    """将 compound 分值转换为可读标签。"""
    if compound >= 0.05:
        return "POSITIVE"
    elif compound <= -0.05:
        return "NEGATIVE"
    return "NEUTRAL"


# ─────────────────────────────────────────────────────────────────────────────
# 工具函数（供 interface.py 注册为 Agent 可调用工具）
# ─────────────────────────────────────────────────────────────────────────────

def get_reddit_sentiment(
    ticker: Annotated[str, "Stock or crypto ticker symbol"],
    date: Annotated[str, "Reference date in yyyy-mm-dd format"],
    subreddits: Annotated[str, "Comma-separated subreddits, e.g. 'wallstreetbets,stocks,investing'"] = "wallstreetbets,stocks,investing",
    limit: Annotated[int, "Max posts per subreddit"] = 25,
) -> str:
    """
    从 Reddit 抓取相关帖子并进行 VADER 情绪评分（可选功能）。
    需要在 .env 中配置：
      REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT
    申请地址（免费）：https://www.reddit.com/prefs/apps
    """
    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    user_agent = os.getenv("REDDIT_USER_AGENT", "tradehive_sentiment/1.0")

    if not client_id or not client_secret:
        return (
            "Reddit credentials not configured.\n"
            "Please add to .env:\n"
            "  REDDIT_CLIENT_ID=your_id\n"
            "  REDDIT_CLIENT_SECRET=your_secret\n"
            "  REDDIT_USER_AGENT=tradehive_sentiment/1.0\n"
            "Apply at: https://www.reddit.com/prefs/apps (free)"
        )

    try:
        import praw
    except ImportError:
        return "praw 未安装，请运行: pip install praw"

    try:
        sia = _get_vader()
    except ImportError as e:
        return str(e)

    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
    )

    scored = []
    ref_dt = datetime.strptime(date, "%Y-%m-%d")
    # 计算回溯天数窗口（默认抓近7天；time_filter 只是 Reddit 搜索参数，
    # 实际时间过滤在下方通过 post.created_utc 精确筛选）
    cutoff_start = ref_dt - timedelta(days=7)

    for sub_name in [s.strip() for s in subreddits.split(",")]:
        try:
            subreddit = reddit.subreddit(sub_name)
            for post in subreddit.search(ticker, limit=limit, time_filter="month"):
                post_dt = datetime.utcfromtimestamp(post.created_utc)
                # 严格按时间窗口过滤：只保留 [cutoff_start, ref_dt] 范围内的帖子
                if not (cutoff_start <= post_dt <= ref_dt + timedelta(days=1)):
                    continue
                text = f"{post.title}. {post.selftext[:200]}".strip()
                scores = sia.polarity_scores(text)
                compound = round(scores["compound"], 4)
                scored.append({
                    "subreddit": sub_name,
                    "date": post_dt.strftime("%Y-%m-%d"),
                    "title": post.title[:90],
                    "score": post.score,
                    "sentiment": _label_sentiment(compound),
                    "compound": compound,
                })
        except Exception:
            continue

    if not scored:
        return f"No Reddit posts found for {ticker} across {subreddits}."

    df = pd.DataFrame(scored).sort_values("compound")
    avg_compound = df["compound"].mean()
    overall_label = _label_sentiment(avg_compound)

    lines = [
        f"# Reddit Sentiment Report: {ticker.upper()}",
        f"# Reference date: {date} | Subreddits: {subreddits}",
        f"# Source: Reddit API + VADER\n",
        f"Overall Sentiment:   {overall_label} (avg compound: {avg_compound:.4f})",
        f"Posts analyzed:      {len(df)}\n",
        f"{'Subreddit':<22} {'Date':<12} {'Sentiment':<10} {'Score':>7}  Title",
        "-" * 85,
    ]
    for _, row in df.iterrows():
        lines.append(
            f"{row['subreddit']:<22} {row['date']:<12} {row['sentiment']:<10} "
            f"{row['compound']:>7.4f}  {row['title']}"
        )
    return "\n".join(lines)


