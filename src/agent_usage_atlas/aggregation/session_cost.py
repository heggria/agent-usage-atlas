"""Session cost waterfall decomposition."""

from __future__ import annotations

from collections import defaultdict

from ._context import AggContext, _percent, _round_money


def compute(ctx: AggContext) -> dict:
    """Decompose each session's cost into a waterfall structure.

    Groups raw events by (source, session_id), sums cost breakdown
    components, computes cache savings and cost ratios, and returns
    the top 20 most expensive sessions with aggregate statistics.
    """
    # ── Group events by (source, session_id) ──
    session_costs: dict[tuple[str, str], dict[str, float]] = defaultdict(
        lambda: {
            "input": 0.0,
            "cache_read": 0.0,
            "cache_write": 0.0,
            "output": 0.0,
            "reasoning": 0.0,
            "cache_read_full": 0.0,
        }
    )

    for event in ctx._raw_events:
        key = (event.source, event.session_id)
        bd = event.cost_breakdown
        bucket = session_costs[key]
        bucket["input"] += bd.get("input", 0.0)
        bucket["cache_read"] += bd.get("cache_read", 0.0)
        bucket["cache_write"] += bd.get("cache_write", 0.0)
        bucket["output"] += bd.get("output", 0.0)
        bucket["reasoning"] += bd.get("reasoning", 0.0)
        bucket["cache_read_full"] += bd.get("cache_read_full", 0.0)

    # ── Build per-session records ──
    records: list[dict] = []
    total_cache_savings = 0.0
    reasoning_shares: list[float] = []
    cache_efficiencies: list[float] = []

    for (source, session_id), costs in session_costs.items():
        cache_savings = max(0.0, costs["cache_read_full"] - costs["cache_read"])
        total_cost = costs["input"] + costs["cache_read"] + costs["cache_write"] + costs["output"] + costs["reasoning"]

        if total_cost <= 0:
            continue

        waterfall = [
            {"label": "Input", "value": _round_money(costs["input"]), "type": "cost"},
            {"label": "Cache Write", "value": _round_money(costs["cache_write"]), "type": "cost"},
            {"label": "Output", "value": _round_money(costs["output"]), "type": "cost"},
            {"label": "Reasoning", "value": _round_money(costs["reasoning"]), "type": "cost"},
            {"label": "Cache Read", "value": _round_money(costs["cache_read"]), "type": "cost"},
            {"label": "Cache Savings", "value": _round_money(-cache_savings) if cache_savings else 0.0, "type": "savings"},
        ]

        reasoning_share = _percent(costs["reasoning"], total_cost)
        cache_efficiency = _percent(cache_savings, costs["cache_read_full"])
        output_share = _percent(costs["output"], total_cost)

        reasoning_shares.append(reasoning_share)
        cache_efficiencies.append(cache_efficiency)
        total_cache_savings += cache_savings

        records.append(
            {
                "session_id": session_id,
                "source": source,
                "total_cost": _round_money(total_cost),
                "_raw_total": total_cost,
                "waterfall": waterfall,
                "ratios": {
                    "reasoning_share": round(reasoning_share, 4),
                    "cache_efficiency": round(cache_efficiency, 4),
                    "output_share": round(output_share, 4),
                },
            }
        )

    # ── Sort by total_cost descending, keep top 20 ──
    records.sort(key=lambda r: r["_raw_total"], reverse=True)
    top_sessions = records[:20]
    for s in top_sessions:
        s.pop("_raw_total", None)

    # ── Aggregate statistics ──
    n = len(reasoning_shares)
    avg_reasoning = sum(reasoning_shares) / n if n else 0.0
    avg_cache_eff = sum(cache_efficiencies) / n if n else 0.0

    return {
        "sessions": top_sessions,
        "aggregate": {
            "avg_reasoning_share": round(avg_reasoning, 4),
            "avg_cache_efficiency": round(avg_cache_eff, 4),
            "total_cache_savings": _round_money(total_cache_savings),
        },
    }
