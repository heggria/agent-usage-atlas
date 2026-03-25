"""Prometheus exposition format renderer."""

from __future__ import annotations

from typing import Any


def _sanitize_label(v: str) -> str:
    return v.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _metric(name: str, value, labels: dict[str, str] | None = None) -> str:
    """Format a single Prometheus metric line."""
    if labels:
        label_str = ",".join(f'{k}="{_sanitize_label(v)}"' for k, v in labels.items())
        return f"{name}{{{label_str}}} {value}"
    return f"{name} {value}"


def render(payload: dict[str, Any]) -> str:
    lines: list[str] = []

    # Per-source metrics from source_cards
    source_cards = payload.get("source_cards", [])
    if source_cards:
        lines.append("# HELP atlas_tokens_total Total tokens by source")
        lines.append("# TYPE atlas_tokens_total gauge")
        lines.append("# HELP atlas_cost_usd Total cost in USD by source")
        lines.append("# TYPE atlas_cost_usd gauge")
        lines.append("# HELP atlas_sessions_total Total sessions by source")
        lines.append("# TYPE atlas_sessions_total gauge")
    for card in source_cards:
        source = card.get("source", "unknown")
        labels = {"source": source}

        lines.append(_metric("atlas_tokens_total", card.get("total_tokens", 0), labels))
        lines.append(_metric("atlas_cost_usd", card.get("cost", 0), labels))
        lines.append(_metric("atlas_sessions_total", card.get("sessions", 0), labels))

    # Aggregate metrics from totals
    totals = payload.get("totals", {})

    if "cost" in totals:
        lines.append("# HELP atlas_cost_daily_usd Daily cost in USD")
        lines.append("# TYPE atlas_cost_daily_usd gauge")
        lines.append(_metric("atlas_cost_daily_usd", totals["cost"]))

    if "burn_rate" in totals:
        lines.append("# HELP atlas_burn_rate_daily_usd Daily burn rate in USD")
        lines.append("# TYPE atlas_burn_rate_daily_usd gauge")
        lines.append(_metric("atlas_burn_rate_daily_usd", totals["burn_rate"]))

    # Efficiency metrics
    efficiency = payload.get("efficiency_metrics", {})

    if "cache_ratio" in efficiency:
        lines.append("# HELP atlas_cache_ratio Cache hit ratio")
        lines.append("# TYPE atlas_cache_ratio gauge")
        lines.append(_metric("atlas_cache_ratio", efficiency["cache_ratio"]))

    lines.append("")  # trailing newline
    return "\n".join(lines)
