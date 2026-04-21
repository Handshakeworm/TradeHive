"""Backtesting engine: daily loop over historical data."""

from __future__ import annotations

import json
import logging
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from .position import PositionTracker

logger = logging.getLogger(__name__)


class BacktestEngine:
    """Run a daily backtesting loop using TradingAgentsGraph.

    OHLC data is read from the project's bulk cache (data_cache/bulk/{TICKER}/stock_data.csv),
    which is already populated by the bulk prefetch mechanism. No extra API calls needed.

    Usage::

        from tradingagents.graph.trading_graph import TradingAgentsGraph
        from tradingagents.backtesting import BacktestEngine

        ta = TradingAgentsGraph(...)
        engine = BacktestEngine(ta, initial_capital=100_000)
        results = engine.run("NVDA", "2024-01-02", "2024-03-29")
    """

    def __init__(
        self,
        graph: Any,  # TradingAgentsGraph (avoid circular import)
        initial_capital: float = 100_000,
        results_dir: str = "backtest_results",
    ):
        self.graph = graph
        self.initial_capital = initial_capital
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
    ) -> Dict[str, Any]:
        """Execute the backtest over [start_date, end_date].

        Args:
            ticker: Stock ticker symbol.
            start_date: First trading day (inclusive), yyyy-mm-dd.
            end_date: Last trading day (inclusive), yyyy-mm-dd.

        Returns:
            Dict with daily_log, final_value, total_return_pct, etc.
        """
        ohlc = self._load_ohlc(ticker, start_date, end_date)
        if ohlc.empty:
            raise ValueError(
                f"No OHLC data for {ticker} in [{start_date}, {end_date}]. "
                "Make sure bulk cache is populated (run pull_cache.py first)."
            )

        trading_days = ohlc.index.tolist()
        logger.info(
            "Backtest %s: %d trading days from %s to %s",
            ticker, len(trading_days), trading_days[0], trading_days[-1],
        )

        position = PositionTracker(initial_capital=self.initial_capital)
        pending_decision: Optional[Dict] = None
        last_successful_decision: Optional[Dict] = None
        last_regime: str = "consolidation"  # regime state machine continuity
        last_entry_reasoning: str = ""     # residual: entry thesis for current regime
        last_daily_deltas: str = ""        # residual: accumulated daily deltas
        daily_log: List[Dict[str, Any]] = []

        for i, day_str in enumerate(trading_days):
            row = ohlc.loc[day_str]
            open_price = float(row["open"])
            high_price = float(row["high"])
            low_price = float(row["low"])
            close_price = float(row["close"])

            day_record = {
                "date": day_str,
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
            }

            # ----------------------------------------------------------
            # 1. Open: execute previous day's PM decision
            # ----------------------------------------------------------
            if pending_decision is not None:
                order_result = position.execute_order(
                    target_position_pct=pending_decision.get("target_position_pct", 0),
                    price=open_price,
                    action=pending_decision.get("action", "Hold"),
                )
                day_record["order"] = order_result
                logger.info(
                    "Day %s open: executed %s @ %.2f, shares_traded=%s",
                    day_str, order_result["action"], open_price,
                    order_result["shares_traded"],
                )

            # ----------------------------------------------------------
            # 2. Close: update position, run pipeline
            # ----------------------------------------------------------
            pos_state = position.get_state_dict(close_price)
            # Inject previous day's PM reasoning for continuity
            if last_successful_decision:
                reasoning = last_successful_decision.get("reasoning", "")
                pos_state["prev_reasoning"] = reasoning[:500]
            else:
                pos_state["prev_reasoning"] = ""
            pos_state["current_price"] = close_price
            pos_state["prev_regime"] = last_regime
            pos_state["regime_entry_reasoning"] = last_entry_reasoning
            pos_state["regime_daily_deltas"] = last_daily_deltas
            day_record["position"] = pos_state.copy()
            day_record["total_value"] = position.get_total_value(close_price)

            # Run full agent pipeline
            try:
                final_state, decision_str = self.graph.propagate(
                    ticker, day_str, position_state=pos_state,
                )

                # Parse PM's structured output
                try:
                    pending_decision = json.loads(
                        final_state["final_trade_decision"]
                    )
                except (json.JSONDecodeError, TypeError):
                    pending_decision = {"action": decision_str, "target_position_pct": 0}

                day_record["decision"] = pending_decision
                last_successful_decision = pending_decision

                # Extract regime + reasoning for residual connection
                try:
                    rm_plan = json.loads(final_state.get("investment_plan", "{}"))
                    new_regime = rm_plan.get("market_regime", last_regime)
                    new_reasoning = rm_plan.get("entry_thesis", "")
                    new_delta = rm_plan.get("daily_delta", "")

                    if new_regime == last_regime:
                        # Same regime: keep entry thesis, append delta
                        if not last_entry_reasoning:
                            last_entry_reasoning = new_reasoning
                        if new_delta:
                            entry = f"\n[Day {day_str} | {new_regime}] {new_delta}"
                            last_daily_deltas += entry
                    else:
                        # Regime changed: reset with transition note
                        old_summary = last_entry_reasoning[:300]
                        if len(last_entry_reasoning) > 300:
                            old_summary += "..."
                        last_daily_deltas = f"[Transition from {last_regime}] {old_summary}"
                        last_entry_reasoning = new_reasoning

                    last_regime = new_regime
                except (json.JSONDecodeError, TypeError):
                    pass  # keep previous state
                logger.info(
                    "Day %s close: PM decision=%s, target_pct=%.1f%%",
                    day_str,
                    pending_decision.get("action"),
                    pending_decision.get("target_position_pct", 0),
                )

            except Exception as e:
                logger.error("Day %s: pipeline failed: %s", day_str, e, exc_info=True)
                day_record["error"] = str(e)
                pending_decision = None

            daily_log.append(day_record)

        # ----------------------------------------------------------
        # Summary
        # ----------------------------------------------------------
        last_close = float(ohlc.iloc[-1]["close"])
        final_value = position.get_total_value(last_close)
        total_return_pct = (
            (final_value - self.initial_capital) / self.initial_capital * 100
        )

        results = {
            "ticker": ticker,
            "start_date": start_date,
            "end_date": end_date,
            "initial_capital": self.initial_capital,
            "final_value": final_value,
            "total_return_pct": total_return_pct,
            "total_fees": round(position.total_fees, 4),
            "trading_days": len(trading_days),
            "daily_log": daily_log,
        }

        # Save results
        out_path = self.results_dir / f"{ticker}_{start_date}_{end_date}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, default=str)
        logger.info(
            "Backtest complete: %s %.2f%% return, saved to %s",
            ticker, total_return_pct, out_path,
        )

        return results

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _load_ohlc(self, ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Load daily OHLC from bulk cache and slice to [start_date, end_date]."""
        from tradingagents.dataflows.bulk_cache import bulk_has, bulk_load

        if not bulk_has(ticker, "stock_data"):
            logger.warning("Bulk cache not found for %s, attempting to fetch...", ticker)
            # Trigger a single get_stock_data call which will populate bulk cache
            from tradingagents.dataflows.interface import route_to_vendor
            route_to_vendor("get_stock_data", ticker, start_date, end_date)

            if not bulk_has(ticker, "stock_data"):
                return pd.DataFrame()

        csv_text = bulk_load(ticker, "stock_data")

        df = pd.read_csv(StringIO(csv_text))
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp")

        # Filter to date range
        mask = (df["timestamp"] >= start_date) & (df["timestamp"] <= end_date)
        df = df.loc[mask].copy()

        # Use date string as index for easy lookup
        df.index = df["timestamp"].dt.strftime("%Y-%m-%d")
        df.index.name = "date"

        return df
