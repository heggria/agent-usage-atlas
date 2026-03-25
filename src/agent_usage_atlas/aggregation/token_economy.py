"""Token Economy Score (TES): measures how efficiently token budgets are spent."""

from __future__ import annotations

from ._context import AggContext, _percent, _round_money

# Component weights
_W_CACHE = 0.35
_W_OUTPUT = 0.25
_W_COST = 0.25
_W_TOOL = 0.15

# Placeholder until per-session tool failure tracking is implemented
_TOOL_SUCCESS_PLACEHOLDER = 0.8

# 8-hour workday assumption (8 * 60 = 480 minutes)
_WORKDAY_MINUTES = 480

_GRADES = (
    (80, "A"),
    (65, "B"),
    (50, "C"),
    (35, "D"),
)


def _grade(score: float) -> str:
    for threshold, letter in _GRADES:
        if score >= threshold:
            return letter
    return "F"


def _session_tes(session: dict) -> dict:
    """Compute TES for a single session rollup dict (active_sessions format)."""
    cache_read = session.get("cache_read", 0)
    uncached_input = session.get("uncached_input", 0)
    output = session.get("output", 0)
    reasoning = session.get("reasoning", 0)
    total = session.get("total", 0)
    cost = session.get("cost", 0.0)
    minutes = session.get("minutes", 0.0)

    cache_denom = cache_read + uncached_input
    cache_util = _percent(cache_read, cache_denom)

    output_yield = _percent(output + reasoning, total)

    cost_density = 1.0 - min(1.0, cost / max(1.0, minutes))

    tool_success = _TOOL_SUCCESS_PLACEHOLDER

    raw = _W_CACHE * cache_util + _W_OUTPUT * output_yield + _W_COST * cost_density + _W_TOOL * tool_success
    score = round(raw * 100, 1)

    return {
        "source": session.get("source", ""),
        "session_id": session.get("session_id", ""),
        "tes": score,
        "grade": _grade(score),
        "components": {
            "cache_utilization": round(cache_util, 4),
            "output_yield": round(output_yield, 4),
            "cost_density": round(cost_density, 4),
            "tool_success_rate": round(tool_success, 4),
        },
        "cost": _round_money(cost),
        "total_tokens": total,
        "minutes": minutes,
    }


def _day_tes(day: dict) -> dict:
    """Compute TES for a single ordered-day dict."""
    cache_read = day.get("cache_read", 0)
    uncached_input = day.get("uncached_input", 0)
    output = day.get("output", 0)
    reasoning = day.get("reasoning", 0)
    total = day.get("total_tokens", 0)
    cost = day.get("cost", 0.0)

    cache_denom = cache_read + uncached_input
    cache_util = _percent(cache_read, cache_denom)

    output_yield = _percent(output + reasoning, total)

    # For daily, treat cost_density as cost per active hour (assume 8h workday cap)
    # Fallback: use 1.0 - min(1.0, cost / max(1, 480)) to keep scale consistent
    cost_density = 1.0 - min(1.0, cost / max(1.0, float(_WORKDAY_MINUTES)))

    tool_success = _TOOL_SUCCESS_PLACEHOLDER

    raw = _W_CACHE * cache_util + _W_OUTPUT * output_yield + _W_COST * cost_density + _W_TOOL * tool_success
    score = round(raw * 100, 1)

    return {
        "date": day.get("date", ""),
        "label": day.get("label", ""),
        "tes": score,
        "grade": _grade(score),
        "components": {
            "cache_utilization": round(cache_util, 4),
            "output_yield": round(output_yield, 4),
            "cost_density": round(cost_density, 4),
            "tool_success_rate": round(tool_success, 4),
        },
    }


def compute(ctx: AggContext) -> dict:
    """Compute Token Economy Scores for all sessions and days.

    Returns
    -------
    dict
        overall_tes: float — weighted average across all sessions
        grade: str — letter grade for the overall score
        session_scores: list — worst 20 sessions by TES (ascending)
        daily_tes: list — TES per day from ctx.ordered_days
        component_averages: dict — mean of each component across sessions
    """
    # ── Per-session scores ──
    all_session_scores: list[dict] = []
    for session in ctx.active_sessions:
        if session.get("total", 0) == 0 and session.get("cost", 0) == 0:
            continue
        all_session_scores.append(_session_tes(session))

    # Sort ascending by TES so worst sessions come first
    all_session_scores.sort(key=lambda s: s["tes"])
    worst_20 = all_session_scores[:20]

    # Overall TES: token-weighted average across sessions.
    # Use max(total_tokens, 1) so sessions with zero recorded tokens (e.g. cost-only
    # sessions that passed the filter) are not silently excluded from the average;
    # they each receive a weight of 1 instead of 0.
    if all_session_scores:
        weights = [max(s["total_tokens"], 1) for s in all_session_scores]
        total_weight = sum(weights)
        overall_tes = round(
            sum(s["tes"] * w for s, w in zip(all_session_scores, weights)) / total_weight,
            1,
        )
    else:
        overall_tes = 0.0

    # ── Component averages ──
    n = len(all_session_scores) or 1
    component_averages = {
        "cache_utilization": round(sum(s["components"]["cache_utilization"] for s in all_session_scores) / n, 4),
        "output_yield": round(sum(s["components"]["output_yield"] for s in all_session_scores) / n, 4),
        "cost_density": round(sum(s["components"]["cost_density"] for s in all_session_scores) / n, 4),
        "tool_success_rate": round(_TOOL_SUCCESS_PLACEHOLDER, 4),
    }

    # ── Daily TES ──
    daily_tes: list[dict] = [_day_tes(day) for day in ctx.ordered_days]

    return {
        "overall_tes": overall_tes,
        "grade": _grade(overall_tes),
        "session_scores": worst_20,
        "daily_tes": daily_tes,
        "component_averages": component_averages,
    }
