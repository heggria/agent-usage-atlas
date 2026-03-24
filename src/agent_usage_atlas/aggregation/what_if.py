"""What-if model substitution scenarios: simulate cost with different models."""

from __future__ import annotations

import re
from collections import defaultdict

from ..models import PricingTier, UsageEvent, _gp
from ._context import AggContext, _round_money

_SCENARIOS: list[dict[str, str]] = [
    {
        "name": "Opus \u2192 Sonnet",
        "from_pattern": "opus",
        "to_model": "claude-sonnet-4-6",
    },
    {
        "name": "Opus \u2192 Haiku",
        "from_pattern": "opus",
        "to_model": "claude-haiku-4-5",
    },
    {
        "name": "Sonnet \u2192 Haiku",
        "from_pattern": "sonnet",
        "to_model": "claude-haiku-4-5",
    },
]

_COST_CATEGORIES = ("input", "cache_read", "cache_write", "output", "reasoning")


def _recompute_cost(event: UsageEvent, tier: PricingTier) -> tuple[float, dict[str, float]]:
    """Compute hypothetical cost for an event using the given pricing tier.

    Returns (total_cost, per_category_breakdown).
    """
    values = {
        "input": event.uncached_input * tier.input / 1e6,
        "cache_read": event.cache_read * tier.cache_read / 1e6,
        "cache_write": event.cache_write * tier.cache_write / 1e6,
        "output": event.output * tier.output / 1e6,
        "reasoning": event.reasoning * tier.reasoning / 1e6,
    }
    return sum(values.values()), values


def _run_scenario(
    events: list[UsageEvent],
    from_pattern: str,
    to_model: str,
) -> dict:
    """Evaluate a single what-if scenario against raw events."""
    target_tier = _gp(to_model)

    events_affected = 0
    actual_cost = 0.0
    hypothetical_cost = 0.0
    breakdown: dict[str, dict[str, float]] = defaultdict(lambda: {"actual": 0.0, "hypothetical": 0.0, "delta": 0.0})

    for event in events:
        if not re.search(r"\b" + re.escape(from_pattern) + r"\b", event.model.lower()):
            continue

        events_affected += 1
        event_actual = event.cost
        actual_cost += event_actual

        hyp_total, hyp_parts = _recompute_cost(event, target_tier)
        hypothetical_cost += hyp_total

        actual_bd = event.cost_breakdown
        for cat in _COST_CATEGORIES:
            breakdown[cat]["actual"] += actual_bd.get(cat, 0.0)
            breakdown[cat]["hypothetical"] += hyp_parts[cat]

    # Finalize deltas and round
    finalized_breakdown: dict[str, dict[str, float]] = {}
    for cat in _COST_CATEGORIES:
        entry = breakdown[cat]
        finalized_breakdown[cat] = {
            "actual": _round_money(entry["actual"]),
            "hypothetical": _round_money(entry["hypothetical"]),
            "delta": _round_money(entry["actual"] - entry["hypothetical"]),
        }

    savings = actual_cost - hypothetical_cost
    savings_pct = (savings / actual_cost * 100) if actual_cost > 0 else 0.0

    return {
        "events_affected": events_affected,
        "actual_cost": _round_money(actual_cost),
        "hypothetical_cost": _round_money(hypothetical_cost),
        "savings": _round_money(savings),
        "savings_pct": round(savings_pct, 1),
        "breakdown": finalized_breakdown,
    }


def compute(ctx: AggContext) -> dict:
    """Compute what-if model substitution scenarios.

    Iterates predefined model swap scenarios, recomputing cost for each
    matching event under the target model's pricing tier.
    """
    raw_events: list[UsageEvent] = ctx._raw_events
    total_actual = ctx.grand_cost

    scenarios: list[dict] = []
    best_savings = 0.0
    best_name = ""

    for spec in _SCENARIOS:
        result = _run_scenario(raw_events, spec["from_pattern"], spec["to_model"])
        scenario = {
            "name": spec["name"],
            "from_pattern": spec["from_pattern"],
            "to_model": spec["to_model"],
            **result,
        }
        scenarios.append(scenario)

        if result["savings"] > best_savings:
            best_savings = result["savings"]
            best_name = spec["name"]

    return {
        "scenarios": scenarios,
        "total_actual": _round_money(total_actual),
        "best_scenario_savings": _round_money(best_savings),
        "best_scenario_name": best_name,
    }
