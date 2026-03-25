"""Budget burn rate analysis with Monte Carlo confidence intervals."""

from __future__ import annotations

import random
from calendar import monthrange

from ._context import AggContext, _percentile, _round_money


def compute(ctx: AggContext, budget: float = 100.0) -> dict:
    """Compute budget burn rate with percentile scenarios and bootstrap simulation.

    Returns a dict with spend tracking, percentile-based exhaustion forecasts,
    and Monte Carlo probability of exceeding the budget this month.
    Returns ``{"error": "..."}`` when there is insufficient data.
    """
    today = ctx.now_local.date()
    _, days_in_month = monthrange(today.year, today.month)
    days_elapsed = today.day
    days_remaining = days_in_month - days_elapsed

    # Current month spend from ordered_days
    current_month_prefix = today.strftime("%Y-%m")
    month_costs = [d["cost"] for d in ctx.ordered_days if d["date"].startswith(current_month_prefix)]
    spent_this_month = sum(month_costs)

    # Collect all active daily costs (cost > 0) across full history for sampling
    active_daily_costs = sorted(d["cost"] for d in ctx.ordered_days if d["cost"] > 0)

    if not active_daily_costs:
        return {"error": "no active daily cost data available"}

    remaining = max(budget - spent_this_month, 0.0)
    percent_used = (spent_this_month / budget * 100) if budget > 0 else 0.0

    # -- Percentile scenarios (P50, P75, P95) --
    scenarios = {}
    for label, fraction in [("p50", 0.50), ("p75", 0.75), ("p95", 0.95)]:
        daily_rate = _percentile(active_daily_costs, fraction)
        if daily_rate > 0:
            exhaustion_day = int(remaining / daily_rate)
        else:
            exhaustion_day = days_remaining  # zero rate never exhausts
        will_exceed = exhaustion_day < days_remaining
        scenarios[label] = {
            "daily_rate": _round_money(daily_rate),
            "exhaustion_day": exhaustion_day,
            "will_exceed": will_exceed,
        }

    # -- Monte Carlo bootstrap (N=1000) --
    # When no days remain in the month the simulation loop would never execute
    # (range(1, 1) is empty), leaving exceed_count=0 and exceed_probability=0.0
    # even when the budget is already exhausted.  Return a deterministic result.
    if days_remaining == 0:
        already_exceeded = spent_this_month > budget
        return {
            "budget": _round_money(budget),
            "spent_this_month": _round_money(spent_this_month),
            "remaining": _round_money(remaining),
            "days_elapsed": days_elapsed,
            "days_remaining": days_remaining,
            "percent_used": round(percent_used, 2),
            "scenarios": scenarios,
            "bootstrap": {
                "exceed_probability": 1.0 if already_exceeded else 0.0,
                "p50_exhaust_day": None,
                "p95_exhaust_day": None,
            },
            "safe_daily_budget": 0.0,
        }

    n_simulations = 1000
    exceed_count = 0
    exhaust_days: list[float] = []

    rng = random.Random(42)  # deterministic seed for reproducibility
    for _ in range(n_simulations):
        cumulative = 0.0
        path_exhausted_day: int | None = None
        for day_offset in range(1, days_remaining + 1):
            sampled_cost = rng.choice(active_daily_costs)
            cumulative += sampled_cost
            if path_exhausted_day is None and cumulative >= remaining:
                path_exhausted_day = day_offset
        if cumulative >= remaining:
            exceed_count += 1
        if path_exhausted_day is not None:
            exhaust_days.append(float(path_exhausted_day))

    exceed_probability = round(exceed_count / n_simulations, 4)

    sorted_exhaust = sorted(exhaust_days)
    bootstrap_p50 = _percentile(sorted_exhaust, 0.50) if sorted_exhaust else None
    bootstrap_p95 = _percentile(sorted_exhaust, 0.95) if sorted_exhaust else None
    # _percentile returns float; convert to int when not None
    p50_exhaust_day = int(bootstrap_p50) if bootstrap_p50 is not None else None
    p95_exhaust_day = int(bootstrap_p95) if bootstrap_p95 is not None else None

    # Safe daily budget
    safe_daily_budget = _round_money(remaining / days_remaining) if days_remaining > 0 else 0.0

    return {
        "budget": _round_money(budget),
        "spent_this_month": _round_money(spent_this_month),
        "remaining": _round_money(remaining),
        "days_elapsed": days_elapsed,
        "days_remaining": days_remaining,
        "percent_used": round(percent_used, 2),
        "scenarios": scenarios,
        "bootstrap": {
            "exceed_probability": exceed_probability,
            "p50_exhaust_day": p50_exhaust_day,
            "p95_exhaust_day": p95_exhaust_day,
        },
        "safe_daily_budget": safe_daily_budget,
    }
