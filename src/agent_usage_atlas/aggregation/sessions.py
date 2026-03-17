"""Session analysis: top sessions, duration histogram, complexity scatter."""

from __future__ import annotations

from statistics import median

from ._context import AggContext, _percentile, _round_money


def _active_sessions(ctx: AggContext) -> list[dict]:
    sessions = []
    for rollup in ctx.session_rollups.values():
        first_local = rollup["first_local"]
        last_local = rollup["last_local"]
        minutes = 0.0
        if first_local and last_local:
            minutes = round((last_local - first_local).total_seconds() / 60, 1)
        sessions.append(
            {
                "source": rollup["source"],
                "session_id": rollup["session_id"],
                "total": rollup["total_tokens"],
                "uncached_input": rollup["uncached_input"],
                "cache_read": rollup["cache_read"],
                "cache_write": rollup["cache_write"],
                "output": rollup["output"],
                "reasoning": rollup["reasoning"],
                "messages": rollup["messages"],
                "tool_calls": rollup["tool_calls"],
                "first_local": first_local.isoformat(timespec="minutes") if first_local else "-",
                "last_local": last_local.isoformat(timespec="minutes") if last_local else "-",
                "minutes": minutes,
                "top_model": rollup["models"].most_common(1)[0][0] if rollup["models"] else "-",
                "cost": _round_money(rollup["cost"]),
            }
        )
    sessions.sort(key=lambda i: (i["total"], i["cost"], i["tool_calls"]), reverse=True)
    return sessions


def compute(ctx: AggContext) -> list[dict]:
    return _active_sessions(ctx)[:20]


def deep_dive(ctx: AggContext) -> dict:
    active_sessions = _active_sessions(ctx)
    complexity_scatter = active_sessions[:50]

    duration_buckets = [
        ("<5m", 0, 5),
        ("5-15m", 5, 15),
        ("15-30m", 15, 30),
        ("30-60m", 30, 60),
        (">60m", 60, float("inf")),
    ]
    duration_histogram = []
    for label, start, end in duration_buckets:
        count = sum(1 for s in active_sessions if start <= s["minutes"] < end)
        duration_histogram.append({"label": label, "count": count})

    sorted_minutes = sorted(s["minutes"] for s in active_sessions if s["minutes"] > 0)
    tokens_per_minute = [s["total"] / s["minutes"] for s in active_sessions if s["minutes"] > 0 and s["total"] > 0]
    sorted_tools = sorted(s["tool_calls"] for s in active_sessions)
    latency_stats = {
        "median_session_minutes": round(median(sorted_minutes), 1) if sorted_minutes else 0.0,
        "p90_session_minutes": round(_percentile(sorted_minutes, 0.9), 1) if sorted_minutes else 0.0,
        "avg_tokens_per_minute": (
            round(sum(tokens_per_minute) / len(tokens_per_minute), 1) if tokens_per_minute else 0.0
        ),
        "median_tools_per_session": round(median(sorted_tools), 1) if sorted_tools else 0.0,
    }

    return {
        "duration_histogram": duration_histogram,
        "complexity_scatter": [
            {
                "source": s["source"],
                "session_id": s["session_id"],
                "duration_minutes": s["minutes"],
                "total_tokens": s["total"],
                "cache_total": s["cache_read"] + s["cache_write"],
                "tool_calls": s["tool_calls"],
                "cost": s["cost"],
            }
            for s in complexity_scatter
        ],
        "latency_stats": latency_stats,
    }
