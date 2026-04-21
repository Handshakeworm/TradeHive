"""Pydantic schemas for structured output from decision nodes."""

import re
import time
import json
import logging
from typing import Literal

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Regex to detect "signal not present" entries that LLM shouldn't have listed
_NEGATION_RE = re.compile(
    r"not found|not present|no signal|not detected|not applicable|does not apply|not met",
    re.IGNORECASE,
)


def filter_reversal_signals(signals: list[str]) -> list[str]:
    """Remove reversal signal entries that describe the absence of a signal."""
    filtered = [s for s in signals if not _NEGATION_RE.search(s)]
    removed = len(signals) - len(filtered)
    if removed:
        logger.warning(
            "Filtered %d false reversal signal(s) containing negation phrases", removed,
        )
    return filtered


# ---------------------------------------------------------------------------
# Decision schemas
# ---------------------------------------------------------------------------

class BullBearEvaluation(BaseModel):
    """Bull/Bear structured evaluation output.

    Field order matters: structured output generates fields sequentially.
    Evidence → reversal_signals → scores → conviction ensures KV cache
    contains all evidence before scoring begins.
    """

    # --- Evidence (generated first, populates KV cache) ---
    fundamentals_evidence: list[str] = Field(
        description="Up to 5 key fundamental evidence points, ranked by importance",
        max_length=5,
    )
    technicals_evidence: list[str] = Field(
        description="Up to 5 key technical evidence points, ranked by importance",
        max_length=5,
    )
    macro_evidence: list[str] = Field(
        description="Up to 5 key macro evidence points, ranked by importance",
        max_length=5,
    )
    sentiment_evidence: list[str] = Field(
        description="Up to 5 key sentiment evidence points, ranked by importance",
        max_length=5,
    )

    # --- Reversal signals (before scores, so scores reflect them) ---
    reversal_signals: list[str] = Field(
        description="Detected reversal signals (0-5). Bull: topping signals; Bear: bottoming signals",
        max_length=5,
    )

    # --- Dimensional scores (informed by evidence + reversal signals) ---
    fundamentals_score: int = Field(ge=1, le=10, description="Fundamental strength: 1=weakest, 10=strongest")
    technicals_score: int = Field(ge=1, le=10, description="Technical strength: 1=weakest, 10=strongest")
    macro_score: int = Field(ge=1, le=10, description="Macro favorability: 1=weakest, 10=strongest")
    sentiment_score: int = Field(ge=1, le=10, description="Sentiment strength: 1=weakest, 10=strongest")

    # --- Overall assessment (last, benefits from full KV cache) ---
    conviction_reasoning: str = Field(
        description="Calculate base conviction as the average of your 4 dimension scores (rounded to nearest integer), then explicitly adjust downward for each reversal signal, stating each adjustment. E.g. 'Avg(7+9+6+8)/4=7.5→8. -1 insider selling, -1 extreme valuation → 6'",
    )
    overall_conviction: int = Field(
        ge=1, le=10,
        description="Final conviction after adjustments described in conviction_reasoning",
    )
    time_horizon: str = Field(description="Expected duration, e.g. '2-4 weeks' or '1-3 months'")
    core_thesis: str = Field(description="Single most important argument")


class ResearchManagerDecision(BaseModel):
    """Research Manager output: regime judgment only (no action)."""

    market_regime: Literal[
        "confirmed_uptrend", "early_uptrend", "consolidation",
        "topping", "early_downtrend", "confirmed_downtrend", "bottoming",
    ] = Field(description="Current market trend stage")
    entry_thesis: str = Field(description="The core thesis for this regime — if regime unchanged, restate the existing thesis; if regime changed, write the new entry thesis")
    daily_delta: str = Field(description="One sentence: what changed vs yesterday (new evidence, confirmed, weakened)")


class TraderDecision(BaseModel):
    """Trader output: execution plan with quantitative parameters."""

    action: Literal["Buy", "Sell", "Hold"]
    target_position_pct: float = Field(
        ge=0, le=100, description="Target position as percentage of total capital"
    )
    reasoning: str = Field(description="Explanation of the trading plan")


class PortfolioManagerDecision(BaseModel):
    """Portfolio Manager output: final executable trade instruction."""

    action: Literal["Buy", "Sell", "Hold"]
    target_position_pct: float = Field(
        ge=0, le=100, description="Target position as percentage of total capital"
    )
    reasoning: str = Field(description="Final decision explanation")


# ---------------------------------------------------------------------------
# Structured invocation helper
# ---------------------------------------------------------------------------

def invoke_structured(llm, schema: type[BaseModel], prompt: str, max_retries: int = 5):
    """Invoke an LLM with structured output, returning a validated Pydantic object.

    Uses ``llm.with_structured_output(schema, method="json_schema")`` and
    retries on validation or network errors.

    Args:
        llm: A LangChain chat model instance.
        schema: The Pydantic BaseModel class to validate against.
        prompt: The prompt string to send.
        max_retries: Number of retries on failure (default 2).

    Returns:
        An instance of *schema* with validated fields.
    """
    structured_llm = llm.with_structured_output(schema, method="json_schema")

    last_error = None
    for attempt in range(1 + max_retries):
        try:
            if attempt == 0:
                result = structured_llm.invoke(prompt)
            else:
                # Append validation feedback so the model can self-correct
                retry_prompt = (
                    f"{prompt}\n\n"
                    f"[SYSTEM] Your previous response failed validation: {last_error}\n"
                    f"Please output a valid JSON matching the required schema."
                )
                result = structured_llm.invoke(retry_prompt)

            if result is None:
                raise ValueError("Model returned empty content")

            return result

        except Exception as e:
            last_error = str(e)
            logger.warning(
                "invoke_structured attempt %d/%d failed: %s",
                attempt + 1, 1 + max_retries, last_error,
            )
            if attempt < max_retries:
                time.sleep(2 ** attempt)  # exponential backoff

    raise RuntimeError(
        f"invoke_structured failed after {1 + max_retries} attempts. "
        f"Last error: {last_error}"
    )
