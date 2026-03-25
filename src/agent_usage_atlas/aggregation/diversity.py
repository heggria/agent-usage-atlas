"""Agent Diversity Score: Shannon entropy across sources."""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import date

from ._context import AggContext


def _shannon_entropy(shares: list[float]) -> float:
    """Compute Shannon entropy from a list of probability shares (must sum to ~1)."""
    return -sum(p * math.log2(p) for p in shares if p > 0)


def _entropy_to_score(entropy: float, max_entropy: float) -> int:
    """Normalize entropy to a 0-100 score."""
    if max_entropy <= 0:
        return 0
    return round((entropy / max_entropy) * 100)


def _iso_week_key(iso_date_str: str) -> str:
    """Return 'YYYY-Www' ISO week string from an ISO date string."""
    d = date.fromisoformat(iso_date_str)
    iso_year, iso_week, _ = d.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


def _compute_weekly_trend(ordered_days: list[dict]) -> list[dict]:
    """Group days by ISO week and compute diversity score per week."""
    weekly_totals: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    week_order: list[str] = []

    for day in ordered_days:
        week_key = _iso_week_key(day["date"])
        if week_key not in weekly_totals:
            week_order.append(week_key)
        for source, tokens in day["source_totals"].items():
            weekly_totals[week_key][source] += tokens or 0

    trend: list[dict] = []
    for week_key in week_order:
        source_tokens = weekly_totals[week_key]
        week_total = sum(source_tokens.values())
        if week_total <= 0:
            trend.append({"week": week_key, "score": 0})
            continue

        shares = [tokens / week_total for tokens in source_tokens.values()]
        num_sources = len(shares)
        if num_sources <= 1:
            trend.append({"week": week_key, "score": 0})
            continue

        entropy = _shannon_entropy(shares)
        max_entropy = math.log2(num_sources)
        trend.append({"week": week_key, "score": _entropy_to_score(entropy, max_entropy)})

    return trend


def _determine_trend_direction(weekly_trend: list[dict]) -> str:
    """Determine trend direction from the last 3 weeks."""
    if len(weekly_trend) < 2:
        return "stable"

    recent = weekly_trend[-3:] if len(weekly_trend) >= 3 else weekly_trend
    scores = [w["score"] for w in recent]

    deltas = [scores[i + 1] - scores[i] for i in range(len(scores) - 1)]
    avg_delta = sum(deltas) / len(deltas)

    if avg_delta > 5:
        return "increasing"
    if avg_delta < -5:
        return "decreasing"
    return "stable"


def _build_suggestions(agent_shares: dict[str, float], num_sources: int, score: int) -> list[str]:
    """Generate rule-based suggestions for improving diversity."""
    suggestions: list[str] = []

    if num_sources == 0:
        suggestions.append("No agent usage data found. Start using AI coding agents to see diversity metrics.")
        return suggestions

    if num_sources == 1:
        if agent_shares:
            sole_source = next(iter(agent_shares))
            suggestions.append(
                f"You are only using {sole_source}. "
                "Consider trying other agents to compare capabilities and find the best fit for different tasks."
            )
        else:
            suggestions.append(
                "Only one agent source detected but no usage data recorded yet. "
                "Consider trying other agents to compare capabilities."
            )
        return suggestions

    dominant_threshold = 0.70
    for source, share in sorted(agent_shares.items(), key=lambda kv: kv[1], reverse=True):
        pct = round(share * 100)
        if share >= dominant_threshold:
            suggestions.append(
                f"You rely heavily on {source} ({pct}%). Consider diversifying across agents for different task types."
            )
            break

    if score < 30:
        suggestions.append(
            "Your diversity score is low. Experimenting with multiple agents "
            "can reveal strengths for specific workflows."
        )
    elif score >= 80:
        suggestions.append("Great diversity! You are effectively leveraging multiple agents.")

    underused_threshold = 0.10
    underused = [source for source, share in agent_shares.items() if 0 < share < underused_threshold]
    if underused:
        names = ", ".join(underused)
        suggestions.append(f"Underused agents: {names}. Consider assigning them to tasks they excel at.")

    return suggestions


def compute(ctx: AggContext) -> dict:
    """Compute agent diversity score using Shannon entropy across sources."""
    source_rollups = ctx.source_rollups
    grand_total = ctx.grand_total

    num_sources = len(source_rollups)

    # Edge case: 0 or 1 source
    if num_sources <= 1 or grand_total <= 0:
        agent_shares = {}
        if num_sources == 1 and grand_total > 0:
            source_name = next(iter(source_rollups))
            agent_shares = {source_name: 1.0}
        elif num_sources > 1:
            agent_shares = {source: 0.0 for source in source_rollups}

        return {
            "diversity_score": 0,
            "entropy": 0.0,
            "max_entropy": 0.0,
            "agent_shares": agent_shares,
            "weekly_trend": _compute_weekly_trend(ctx.ordered_days),
            "trend_direction": "stable",
            "suggestions": _build_suggestions(agent_shares, num_sources, 0),
        }

    # Per-source shares
    agent_shares = {source: round((rollup["total_tokens"] or 0) / grand_total, 4) for source, rollup in source_rollups.items()}

    shares = list(agent_shares.values())
    entropy = round(_shannon_entropy(shares), 4)
    max_entropy = round(math.log2(num_sources), 4)
    diversity_score = _entropy_to_score(entropy, max_entropy)

    weekly_trend = _compute_weekly_trend(ctx.ordered_days)
    trend_direction = _determine_trend_direction(weekly_trend)
    suggestions = _build_suggestions(agent_shares, num_sources, diversity_score)

    return {
        "diversity_score": diversity_score,
        "entropy": entropy,
        "max_entropy": max_entropy,
        "agent_shares": agent_shares,
        "weekly_trend": weekly_trend,
        "trend_direction": trend_direction,
        "suggestions": suggestions,
    }
