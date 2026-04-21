import json
import logging

from tradingagents.agents.utils.agent_utils import build_instrument_context
from tradingagents.agents.utils.schemas import (
    ResearchManagerDecision,
    invoke_structured,
)

logger = logging.getLogger(__name__)

# State machine: legal regime transitions
LEGAL_TRANSITIONS = {
    "confirmed_uptrend": {"confirmed_uptrend", "topping"},
    "early_uptrend": {"early_uptrend", "confirmed_uptrend", "consolidation"},
    "consolidation": {"consolidation", "early_uptrend", "early_downtrend"},
    "topping": {"topping", "consolidation", "early_downtrend", "early_uptrend"},
    "early_downtrend": {"early_downtrend", "confirmed_downtrend", "consolidation"},
    "confirmed_downtrend": {"confirmed_downtrend", "bottoming"},
    "bottoming": {"bottoming", "consolidation", "early_uptrend", "early_downtrend"},
}

# Regime rank: bearish(0) → bullish(6), for closest-legal fallback
_REGIME_RANK = {
    "confirmed_downtrend": 0, "early_downtrend": 1, "bottoming": 2,
    "consolidation": 3, "topping": 4, "early_uptrend": 5, "confirmed_uptrend": 6,
}


def _closest_legal(prev_regime, intended_regime):
    """Find the legal transition from prev_regime closest to intended_regime's direction."""
    legal = LEGAL_TRANSITIONS.get(prev_regime, {prev_regime})
    intended_rank = _REGIME_RANK.get(intended_regime, 3)
    return min(legal, key=lambda r: abs(_REGIME_RANK[r] - intended_rank))


def _validate_regime_transition(new_regime, prev_regime, bull, bear):
    """Enforce state machine rules and confirmed-state thresholds.

    Returns (validated_regime, reason) where reason is None if no override.
    """
    reason = None

    # 1. State machine: illegal transitions → closest legal in intended direction
    if new_regime not in LEGAL_TRANSITIONS.get(prev_regime, {prev_regime}):
        fallback = _closest_legal(prev_regime, new_regime)
        reason = "illegal transition"
        logger.warning(
            "Illegal regime transition %s → %s, closest legal: %s",
            prev_regime, new_regime, fallback,
        )
        new_regime = fallback

    # 2. confirmed_uptrend entry: M-of-N vote, 5 of 6 conditions must be met
    _uptrend_entry_flags = {
        "bull_conviction_ge_8": bull["overall_conviction"] >= 8,
        "bull_tech_ge_8": bull["technicals_score"] >= 8,
        "bull_fund_ge_7": bull["fundamentals_score"] >= 7,
        "bull_no_reversals": len(bull["reversal_signals"]) == 0,
        "bear_conviction_le_6": bear["overall_conviction"] <= 6,
        "bear_tech_le_6": bear["technicals_score"] <= 6,
    }
    _uptrend_entry_hits = sum(_uptrend_entry_flags.values())
    _uptrend_ok = _uptrend_entry_hits >= 5
    if new_regime == "confirmed_uptrend" and prev_regime != "confirmed_uptrend":
        if not _uptrend_ok:
            reason = "uptrend threshold not met"
            logger.info(
                "confirmed_uptrend entry blocked: hits=%d/6, flags=%s",
                _uptrend_entry_hits,
                [k for k, v in _uptrend_entry_flags.items() if v],
            )
            new_regime = prev_regime
    # Auto-upgrade: RM didn't choose confirmed_uptrend but conditions are met
    if (
        new_regime != "confirmed_uptrend"
        and prev_regime != "confirmed_uptrend"
        and _uptrend_ok
        and "confirmed_uptrend" in LEGAL_TRANSITIONS.get(prev_regime, set())
    ):
        reason = "auto-upgrade: confirmed_uptrend conditions met"
        logger.info(
            "Auto-upgrade to confirmed_uptrend: hits=%d/6, flags=%s",
            _uptrend_entry_hits,
            [k for k, v in _uptrend_entry_flags.items() if v],
        )
        new_regime = "confirmed_uptrend"

    # 3. confirmed_uptrend exit: M-of-N vote across 5 deterioration signals
    _uptrend_exit_flags = {
        "bull_conviction_le_7": bull["overall_conviction"] <= 7,
        "bull_reversals_ge_2": len(bull["reversal_signals"]) >= 2,
        "bull_tech_le_7": bull["technicals_score"] <= 7,
        "bear_conviction_ge_8": bear["overall_conviction"] >= 8,
        "bear_tech_ge_8": bear["technicals_score"] >= 8,
    }
    _uptrend_exit_hits = sum(_uptrend_exit_flags.values())
    _uptrend_exit = _uptrend_exit_hits >= 4
    if prev_regime == "confirmed_uptrend" and new_regime != "confirmed_uptrend":
        if not _uptrend_exit:
            reason = "uptrend exit blocked"
            logger.info(
                "confirmed_uptrend exit blocked: hits=%d/5, flags=%s",
                _uptrend_exit_hits,
                [k for k, v in _uptrend_exit_flags.items() if v],
            )
            new_regime = "confirmed_uptrend"
    # Auto-downgrade: RM stayed in confirmed_uptrend but exit conditions are met
    if prev_regime == "confirmed_uptrend" and new_regime == "confirmed_uptrend" and _uptrend_exit:
        reason = "auto-downgrade: confirmed_uptrend exit conditions met"
        logger.info(
            "Auto-downgrade from confirmed_uptrend: hits=%d/5, flags=%s",
            _uptrend_exit_hits,
            [k for k, v in _uptrend_exit_flags.items() if v],
        )
        new_regime = "topping"

    # 4. confirmed_downtrend entry: M-of-N vote, 5 of 6 conditions must be met (mirror of uptrend)
    _downtrend_entry_flags = {
        "bear_conviction_ge_8": bear["overall_conviction"] >= 8,
        "bear_tech_ge_8": bear["technicals_score"] >= 8,
        "bear_fund_ge_7": bear["fundamentals_score"] >= 7,
        "bear_no_reversals": len(bear["reversal_signals"]) == 0,
        "bull_conviction_le_6": bull["overall_conviction"] <= 6,
        "bull_tech_le_6": bull["technicals_score"] <= 6,
    }
    _downtrend_entry_hits = sum(_downtrend_entry_flags.values())
    _downtrend_ok = _downtrend_entry_hits >= 5
    if new_regime == "confirmed_downtrend" and prev_regime != "confirmed_downtrend":
        if not _downtrend_ok:
            reason = "downtrend threshold not met"
            logger.info(
                "confirmed_downtrend entry blocked: hits=%d/6, flags=%s",
                _downtrend_entry_hits,
                [k for k, v in _downtrend_entry_flags.items() if v],
            )
            new_regime = prev_regime
    # Auto-upgrade: RM didn't choose confirmed_downtrend but conditions are met
    if (
        new_regime != "confirmed_downtrend"
        and prev_regime != "confirmed_downtrend"
        and _downtrend_ok
        and "confirmed_downtrend" in LEGAL_TRANSITIONS.get(prev_regime, set())
    ):
        reason = "auto-upgrade: confirmed_downtrend conditions met"
        logger.info(
            "Auto-upgrade to confirmed_downtrend: hits=%d/6, flags=%s",
            _downtrend_entry_hits,
            [k for k, v in _downtrend_entry_flags.items() if v],
        )
        new_regime = "confirmed_downtrend"

    # 5. confirmed_downtrend exit: M-of-N vote across 5 deterioration signals (mirror of uptrend)
    _downtrend_exit_flags = {
        "bear_conviction_le_7": bear["overall_conviction"] <= 7,
        "bear_reversals_ge_2": len(bear["reversal_signals"]) >= 2,
        "bear_tech_le_7": bear["technicals_score"] <= 7,
        "bull_conviction_ge_8": bull["overall_conviction"] >= 8,
        "bull_tech_ge_8": bull["technicals_score"] >= 8,
    }
    _downtrend_exit_hits = sum(_downtrend_exit_flags.values())
    _downtrend_exit = _downtrend_exit_hits >= 4
    if prev_regime == "confirmed_downtrend" and new_regime != "confirmed_downtrend":
        if not _downtrend_exit:
            reason = "downtrend exit blocked"
            logger.info(
                "confirmed_downtrend exit blocked: hits=%d/5, flags=%s",
                _downtrend_exit_hits,
                [k for k, v in _downtrend_exit_flags.items() if v],
            )
            new_regime = "confirmed_downtrend"
    # Auto-downgrade: RM stayed in confirmed_downtrend but exit conditions are met
    if prev_regime == "confirmed_downtrend" and new_regime == "confirmed_downtrend" and _downtrend_exit:
        reason = "auto-downgrade: confirmed_downtrend exit conditions met"
        logger.info(
            "Auto-downgrade from confirmed_downtrend: hits=%d/5, flags=%s",
            _downtrend_exit_hits,
            [k for k, v in _downtrend_exit_flags.items() if v],
        )
        new_regime = "bottoming"

    return new_regime, reason


def _format_evaluation(label, data):
    """Format a Bull/Bear evaluation dict for the RM prompt."""
    lines = [f"## {label} Evaluation"]
    for dim in ("fundamentals", "technicals", "macro", "sentiment"):
        evidence = data.get(f"{dim}_evidence", [])
        score = data.get(f"{dim}_score", "?")
        lines.append(f"**{dim.capitalize()}** (score: {score}/10):")
        for i, e in enumerate(evidence, 1):
            lines.append(f"  {i}. {e}")
    # Reversal signals
    signals = data.get("reversal_signals", [])
    lines.append(f"**Reversal signals** ({len(signals)} detected):")
    for s in signals:
        lines.append(f"  - {s}")
    lines.append(f"**Overall conviction**: {data.get('overall_conviction', '?')}/10")
    lines.append(f"**Time horizon**: {data.get('time_horizon', '?')}")
    lines.append(f"**Core thesis**: {data.get('core_thesis', '?')}")
    return "\n".join(lines)


def create_research_manager(llm, memory):
    def research_manager_node(state) -> dict:
        instrument_context = build_instrument_context(state["company_of_interest"])

        # Parse Bull/Bear structured evaluations
        bull = json.loads(state.get("bull_structured_output", "{}"))
        bear = json.loads(state.get("bear_structured_output", "{}"))
        prev_regime = state.get("prev_regime", "consolidation")
        entry_reasoning = state.get("regime_entry_reasoning", "")
        daily_deltas = state.get("regime_daily_deltas", "")

        # Memory retrieval using Bull/Bear core theses
        memory_key = f"{bull.get('core_thesis', '')}\n\n{bear.get('core_thesis', '')}"
        past_memories = memory.get_memories(memory_key, n_matches=2)
        past_memory_str = "\n\n".join(rec["recommendation"] for rec in past_memories)

        bull_summary = _format_evaluation("Bull", bull)
        bear_summary = _format_evaluation("Bear", bear)

        prompt = f"""You are the Research Manager. Your ONLY task is to determine the current market regime. You do NOT decide Buy/Sell/Hold — that is the Trader's job.

{instrument_context}

## Regime Continuity Context
These three fields are YOUR OWN prior outputs carried forward by the backtest engine, NOT external data. Use them to maintain consistency across trading days.

**Current regime** (your judgment from the previous trading day): **{prev_regime}**

**Entry thesis** (the reasoning YOU wrote when you first assigned this regime — unchanged as long as the regime persists):
{entry_reasoning or "(First day or no prior thesis — you are starting fresh)"}

**Daily deltas** (incremental thesis updates YOU wrote on each subsequent day within this regime; if the regime recently changed, a brief summary of the old regime's thesis appears as a `[Transition from ...]` note):
{daily_deltas or "(No prior updates — this is the first day in this regime)"}

## Bull/Bear Structured Evaluations

{bull_summary}

{bear_summary}

## Regime Judgment Instructions

**Your default output is: {prev_regime} (no change).** You must provide specific, concrete evidence to justify any regime transition.

**Legal transitions from {prev_regime}:**
{', '.join(LEGAL_TRANSITIONS.get(prev_regime, set()))}

**How to compare Bull vs Bear:**
- Compare dimension by dimension (e.g., Bull fundamentals 8 vs Bear fundamentals 3 → strong fundamental support)
- Where both sides agree (similar scores), that dimension has high confidence
- Where they diverge sharply, use the evidence quality and reversal signals to break the tie

**Reversal signal interpretation:**
- If Bull reports 2+ topping signals → potential regime downgrade even if scores look good
- If Bear reports 2+ bottoming signals → potential regime upgrade even if scores look bad
- When the side that SHOULD be strongest admits weakness, that is high-conviction evidence

**Confirmed state rules:**
- Entering confirmed_uptrend requires at least 5 of these 6 conditions: Bull conviction ≥ 8, Bull technicals ≥ 8, Bull fundamentals ≥ 7, Bull zero reversal_signals, Bear conviction ≤ 6, Bear technicals ≤ 6
- Entering confirmed_downtrend requires at least 5 of these 6 conditions: Bear conviction ≥ 8, Bear technicals ≥ 8, Bear fundamentals ≥ 7, Bear zero reversal_signals, Bull conviction ≤ 6, Bull technicals ≤ 6
- Exiting confirmed_uptrend requires at least 4 of these 5 deterioration signals: Bull conviction ≤ 7, Bull reversal_signals ≥ 2, Bull technicals ≤ 7, Bear conviction ≥ 8, Bear technicals ≥ 8
- Exiting confirmed_downtrend requires at least 4 of these 5 deterioration signals: Bear conviction ≤ 7, Bear reversal_signals ≥ 2, Bear technicals ≤ 7, Bull conviction ≥ 8, Bull technicals ≥ 8
- Normal pullbacks, single bad news events, or short-term technical weakness are NOT sufficient to exit confirmed states

**Thesis continuity**: Before concluding, explicitly assess whether the entry thesis still holds. If it does, your default should be to maintain the current regime. The thesis is invalidated when the key assumption it rests on is contradicted by new Bull/Bear evidence — e.g., a support level cited in the thesis has been broken, a catalyst it expected has failed to materialize, or the dimension scores that originally supported it have reversed direction. Only transition when such invalidation is clear.

## Your Output Fields
You must produce exactly three fields:
- **market_regime**: one of the 7 legal regime values (confirmed_uptrend, early_uptrend, consolidation, topping, early_downtrend, confirmed_downtrend, bottoming)
- **entry_thesis**: the core thesis for this regime. If the regime is unchanged, restate the existing entry thesis (shown above). If the regime changed, write a new entry thesis. This will be shown back to you as "Entry thesis" on the next trading day.
- **daily_delta**: one sentence summarizing what changed vs yesterday — new evidence that appeared, thesis confirmed, or thesis weakened. This will be appended to the "Daily deltas" list shown to you on the next trading day.

Past reflections on similar situations:
{past_memory_str or "(None)"}"""

        decision = invoke_structured(llm, ResearchManagerDecision, prompt)

        # Code-enforced regime validation (does not rely on LLM compliance)
        validated_regime, override_reason = _validate_regime_transition(
            decision.market_regime, prev_regime, bull, bear
        )
        if validated_regime != decision.market_regime:
            logger.info(
                "Regime overridden: %s → %s reverted to %s (%s)",
                prev_regime, decision.market_regime, validated_regime, override_reason,
            )
            decision = ResearchManagerDecision(
                market_regime=validated_regime,
                entry_thesis=decision.entry_thesis + f" [Code override: {decision.market_regime} → {validated_regime}]",
                daily_delta=f"Attempted {decision.market_regime} but reverted to {validated_regime} ({override_reason})",
            )

        decision_json = decision.model_dump_json()

        return {
            "investment_plan": decision_json,
        }

    return research_manager_node
