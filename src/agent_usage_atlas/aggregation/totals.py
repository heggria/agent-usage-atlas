"""Grand totals and source card computation."""

from __future__ import annotations

from statistics import median

from ._context import AggContext, _percent, _round_money, _source_rank


def compute(ctx: AggContext) -> dict:
    source_cards = _source_cards(ctx)
    active_sessions = _active_sessions(ctx)
    ordered_days = ctx.ordered_days

    grand_total = sum(d["total_tokens"] for d in ordered_days)
    grand_cost = sum(d["cost"] for d in ordered_days)
    grand_cache_read = sum(d["cache_read"] for d in ordered_days)
    grand_cache_write = sum(d["cache_write"] for d in ordered_days)
    grand_output = sum(d["output"] for d in ordered_days)
    grand_reasoning = sum(d["reasoning"] for d in ordered_days)
    cache_ratio = _percent(grand_cache_read + grand_cache_write, grand_total)
    token_capable_cards = [c for c in source_cards if c["token_capable"]]
    tracked_messages = sum(c["messages"] for c in token_capable_cards)

    session_tokens = [s["total"] for s in active_sessions if s["total"] > 0]
    session_minutes = [s["minutes"] for s in active_sessions if s["minutes"] > 0]
    session_costs = [s["cost"] for s in active_sessions if s["cost"] > 0]

    peak_day = max(ordered_days, key=lambda i: i["total_tokens"], default=None)
    cost_peak_day = max(ordered_days, key=lambda i: i["cost"], default=None)
    total_cache_read_full = sum(c["cost_cache_read_full"] for c in source_cards)
    total_cost_cache_read = sum(c["cost_cache_read"] for c in source_cards)
    cache_savings_usd = max(0.0, total_cache_read_full - total_cost_cache_read)
    cache_savings_ratio = _percent(cache_savings_usd, total_cache_read_full)

    combined_tool_counts = _combined_tool_counts(ctx)
    project_count = len(_project_rollups(ctx, active_sessions))

    recent_window = ordered_days[-7:] if ordered_days else []
    average_daily_burn = round(sum(d["cost"] for d in recent_window) / len(recent_window), 4) if recent_window else 0.0
    projected_total_30d = round(average_daily_burn * 30, 2)

    return {
        "grand_total": grand_total,
        "grand_cost": round(grand_cost, 2),
        "cache_read": grand_cache_read,
        "cache_write": grand_cache_write,
        "output": grand_output,
        "reasoning": grand_reasoning,
        "cache_ratio": cache_ratio,
        "tracked_session_count": sum(c["sessions"] for c in token_capable_cards),
        "average_per_day": round(grand_total / max(1, len(ordered_days))),
        "median_session_tokens": round(median(session_tokens)) if session_tokens else 0,
        "median_session_minutes": round(median(session_minutes), 1) if session_minutes else 0.0,
        "median_session_cost": round(median(session_costs), 4) if session_costs else 0.0,
        "peak_day_label": peak_day["label"] if peak_day else "-",
        "peak_day_total": peak_day["total_tokens"] if peak_day else 0,
        "cost_peak_day_label": cost_peak_day["label"] if cost_peak_day else "-",
        "cost_peak_day_total": round(cost_peak_day["cost"], 4) if cost_peak_day else 0.0,
        "average_cost_per_day": round(grand_cost / max(1, len(ordered_days)), 2),
        "cost_per_message": round(grand_cost / max(1, tracked_messages), 4),
        "cost_input": round(sum(d["cost_input"] for d in ordered_days), 2),
        "cost_cache_read": round(sum(d["cost_cache_read"] for d in ordered_days), 2),
        "cost_cache_write": round(sum(d["cost_cache_write"] for d in ordered_days), 2),
        "cost_output": round(sum(d["cost_output"] for d in ordered_days), 2),
        "cost_reasoning": round(sum(d["cost_reasoning"] for d in ordered_days), 2),
        "cache_savings_usd": round(cache_savings_usd, 2),
        "cache_savings_ratio": cache_savings_ratio,
        "tool_call_total": sum(combined_tool_counts.values()),
        "project_count": project_count,
        "avg_daily_burn": round(average_daily_burn, 2),
        "burn_rate_projection_30d": projected_total_30d,
    }


def source_cards(ctx: AggContext) -> list[dict]:
    return _source_cards(ctx)


def _source_cards(ctx: AggContext) -> list[dict]:
    cards = []
    for source_name in sorted(ctx.source_rollups, key=_source_rank):
        s = ctx.source_rollups[source_name]
        cards.append(
            {
                "source": source_name,
                "total": s["total_tokens"],
                "uncached_input": s["uncached_input"],
                "cache_read": s["cache_read"],
                "cache_write": s["cache_write"],
                "output": s["output"],
                "reasoning": s["reasoning"],
                "sessions": len(s["sessions"]),
                "messages": s["messages"],
                "top_model": s["models"].most_common(1)[0][0] if s["models"] else "-",
                "token_capable": s["token_capable"],
                "cost": _round_money(s["cost"]),
                "cost_input": _round_money(s["cost_input"]),
                "cost_cache_read": _round_money(s["cost_cache_read"]),
                "cost_cache_write": _round_money(s["cost_cache_write"]),
                "cost_output": _round_money(s["cost_output"]),
                "cost_reasoning": _round_money(s["cost_reasoning"]),
                "cost_cache_read_full": _round_money(s["cost_cache_read_full"]),
            }
        )
    return cards


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


def _combined_tool_counts(ctx: AggContext):
    from collections import Counter

    combined = Counter()
    for counts in ctx.tool_counts_by_source.values():
        combined.update(counts)
    return combined


def _project_rollups(ctx: AggContext, active_sessions):
    from collections import defaultdict

    project_rollups = defaultdict(
        lambda: {"project": "", "sessions": 0, "total_tokens": 0, "cost": 0.0, "tool_calls": 0}
    )
    for session in active_sessions:
        meta = ctx.session_meta_map.get((session["source"], session["session_id"]))
        project_name = (meta.project if meta else None) or "unknown"
        project = project_rollups[project_name]
        project["project"] = project_name
        project["sessions"] += 1
        project["total_tokens"] += session["total"]
        project["cost"] += session["cost"]
        project["tool_calls"] += session["tool_calls"]
    return project_rollups
