"""Trend analysis and efficiency metrics command."""

from __future__ import annotations

import sys

from ..cli import build_dashboard_payload
from ..models import fmt_int, fmt_usd
from ._ansi import bold, cyan, dim, green, red, yellow

_SPARK_CHARS = " ▁▂▃▄▅▆▇█"


def _sparkline(values: list[float], width: int = 28) -> str:
    """Render a fixed-width sparkline from a list of float values using block chars."""
    if not values:
        return dim("(no data)")
    # Sample or pad to `width` points
    n = len(values)
    if n >= width:
        step = n / width
        sampled = [values[int(i * step)] for i in range(width)]
    else:
        sampled = values
    lo, hi = min(sampled), max(sampled)
    span = hi - lo or 1.0
    chars = [_SPARK_CHARS[min(8, int((v - lo) / span * 8))] for v in sampled]
    return "".join(chars)


def _pct_change_label(old_val: float, new_val: float) -> str:
    """Return a coloured percentage-change string."""
    if old_val == 0 and new_val == 0:
        return dim("no change")
    if old_val == 0:
        return green("+∞%")
    pct = (new_val - old_val) / old_val * 100
    if pct > 5:
        return red(f"+{pct:.1f}%")
    if pct < -5:
        return green(f"{pct:.1f}%")
    return yellow(f"{pct:+.1f}%")


# ── Subcommand registration ──────────────────────────────────────────


def add_parser(subparsers):
    parser = subparsers.add_parser(
        "trends",
        help="Show trend analysis and efficiency metrics",
    )
    parser.add_argument(
        "--daily",
        action="store_true",
        help="Show daily cost/token breakdown",
    )
    parser.add_argument(
        "--efficiency",
        action="store_true",
        help="Show efficiency metrics",
    )
    parser.set_defaults(func=run)
    return parser


# ── Helpers ───────────────────────────────────────────────────────────


def _trend_label(first_half_avg: float, second_half_avg: float) -> str:
    """Compare first-half vs second-half average daily cost."""
    if first_half_avg == 0 and second_half_avg == 0:
        return dim("no activity")
    if first_half_avg == 0:
        return green("trending up (from zero)")
    ratio = second_half_avg / first_half_avg
    if ratio > 1.15:
        return red(f"trending up (+{(ratio - 1) * 100:.0f}%)")
    if ratio < 0.85:
        return green(f"trending down ({(ratio - 1) * 100:.0f}%)")
    return yellow("flat")


def _separator(width: int = 60) -> str:
    return dim("-" * width)


# ── Main command ─────────────────────────────────────────────────────


def run(args) -> None:
    try:
        dashboard = build_dashboard_payload(days=args.days, since=args.since)
    except ValueError as exc:
        raise SystemExit(f"Invalid --since date format: {exc}") from exc

    days_data: list[dict] = dashboard.get("days", [])
    efficiency_metrics: dict = dashboard.get("efficiency_metrics", {})
    trend_analysis: dict = dashboard.get("trend_analysis", {})
    totals: dict = dashboard.get("totals", {})

    lines: list[str] = []

    # ── Overview ──────────────────────────────────────────────────
    lines.append("")
    lines.append(bold("  Trend Overview"))
    lines.append(_separator())

    grand_cost = totals.get("grand_cost", 0)
    grand_total = totals.get("grand_total", 0)
    avg_daily_cost = totals.get("average_cost_per_day", 0)
    avg_daily_tokens = totals.get("average_per_day", 0)

    active_days = [d for d in days_data if d.get("total_tokens", 0) > 0 or d.get("cost", 0) > 0]
    total_days = len(days_data)
    active_count = len(active_days)

    lines.append(f"  Total cost:         {bold(fmt_usd(grand_cost))}")
    lines.append(f"  Total tokens:       {bold(fmt_int(grand_total))}")
    lines.append(f"  Avg daily cost:     {fmt_usd(avg_daily_cost)}")
    lines.append(f"  Avg daily tokens:   {fmt_int(avg_daily_tokens)}")
    lines.append(f"  Active days:        {active_count} / {total_days}")

    # Cost trend: first half vs second half
    if len(active_days) >= 2:
        mid = len(active_days) // 2
        first_half = active_days[:mid]
        second_half = active_days[mid:]
        first_avg = sum(d.get("cost", 0) for d in first_half) / len(first_half)
        second_avg = sum(d.get("cost", 0) for d in second_half) / len(second_half)
        lines.append(f"  Cost trend:         {_trend_label(first_avg, second_avg)}")

    # ── 1. Daily sparkline ─────────────────────────────────────────
    cost_values = [d.get("cost", 0.0) for d in days_data]
    if any(v > 0 for v in cost_values):
        spark = _sparkline(cost_values)
        lines.append(f"  Daily cost spark:   {cyan(spark)}")

    # ── 2. Week-over-week comparison ───────────────────────────────
    if total_days >= 14:
        last7 = days_data[-7:]
        prev7 = days_data[-14:-7]
        wow_cost_last = sum(d.get("cost", 0.0) for d in last7)
        wow_cost_prev = sum(d.get("cost", 0.0) for d in prev7)
        wow_tok_last = sum(d.get("total_tokens", 0) for d in last7)
        wow_tok_prev = sum(d.get("total_tokens", 0) for d in prev7)
        wow_tool_last = sum(d.get("tool_calls", 0) for d in last7)
        wow_tool_prev = sum(d.get("tool_calls", 0) for d in prev7)
        lines.append("")
        lines.append(bold("  Week-over-Week (last 7d vs prior 7d)"))
        lines.append(_separator())
        lines.append(
            f"  Cost:       {fmt_usd(wow_cost_last):>10}  vs  {fmt_usd(wow_cost_prev):<10}  "
            f"{_pct_change_label(wow_cost_prev, wow_cost_last)}"
        )
        lines.append(
            f"  Tokens:     {fmt_int(wow_tok_last):>10}  vs  {fmt_int(wow_tok_prev):<10}  "
            f"{_pct_change_label(float(wow_tok_prev), float(wow_tok_last))}"
        )
        lines.append(
            f"  Tool calls: {fmt_int(wow_tool_last):>10}  vs  {fmt_int(wow_tool_prev):<10}  "
            f"{_pct_change_label(float(wow_tool_prev), float(wow_tool_last))}"
        )

    # Token burn projection
    burn_rate = trend_analysis.get("burn_rate_30d", {})
    projected_monthly = burn_rate.get("projected_total_30d")
    avg_daily_burn = burn_rate.get("average_daily_cost")
    if projected_monthly is not None:
        lines.append("")
        lines.append(bold("  Token Burn Projection"))
        lines.append(_separator())
        if avg_daily_burn is not None:
            lines.append(f"  Avg daily burn (7d): {fmt_usd(avg_daily_burn)}")
        lines.append(f"  Projected 30d cost:  {cyan(fmt_usd(projected_monthly))}")

        # ── 3. Burn rate trend indicator ───────────────────────────
        burn_history: list[dict] = burn_rate.get("history", [])
        burn_costs = [h.get("cost", 0.0) for h in burn_history if h.get("cost", 0.0) > 0]
        if len(burn_costs) >= 4:
            half = len(burn_costs) // 2
            first_h_avg = sum(burn_costs[:half]) / half
            second_h_avg = sum(burn_costs[half:]) / max(1, len(burn_costs) - half)
            if first_h_avg == 0:
                trend_str = green("accelerating (from zero)")
            else:
                ratio = second_h_avg / first_h_avg
                if ratio > 1.15:
                    trend_str = red(f"accelerating (+{(ratio - 1) * 100:.0f}%)")
                elif ratio < 0.85:
                    trend_str = green(f"decelerating ({(ratio - 1) * 100:.0f}%)")
                else:
                    trend_str = yellow("stable")
            lines.append(f"  Burn rate:           {trend_str}")
            burn_spark = _sparkline(burn_costs)
            lines.append(f"  Burn sparkline:      {cyan(burn_spark)}")

    # ── 4. Cost per tool call trend ────────────────────────────────
    cptc_series: list[dict] = trend_analysis.get("daily_cost_per_tool_call", [])
    cptc_values = [item.get("value", 0.0) for item in cptc_series if item.get("tool_calls", 0) > 0]
    if cptc_values:
        avg_cptc = sum(cptc_values) / len(cptc_values)
        latest_cptc = cptc_values[-1]
        cptc_spark = _sparkline(cptc_values)
        lines.append("")
        lines.append(bold("  Cost per Tool Call"))
        lines.append(_separator())
        lines.append(f"  Average:             {fmt_usd(avg_cptc)}")
        lines.append(f"  Latest day:          {fmt_usd(latest_cptc)}")
        cptc_label = _pct_change_label(avg_cptc, latest_cptc)
        lines.append(f"  vs average:          {cptc_label}")
        lines.append(f"  Trend sparkline:     {cyan(cptc_spark)}")

    # ── 5. Peak day highlight ──────────────────────────────────────
    peak_label = totals.get("cost_peak_day_label")
    peak_total = totals.get("cost_peak_day_total", 0.0)
    if peak_label and peak_label != "-" and peak_total > 0 and avg_daily_cost > 0:
        lines.append("")
        lines.append(bold("  Peak Day"))
        lines.append(_separator())
        excess_pct = (peak_total - avg_daily_cost) / avg_daily_cost * 100
        lines.append(f"  Highest cost day:    {bold(peak_label)}  {fmt_usd(peak_total)}")
        lines.append(f"  vs daily average:    {red(f'+{excess_pct:.0f}%')} above {fmt_usd(avg_daily_cost)}")

    lines.append("")

    # ── Daily table ───────────────────────────────────────────────
    if args.daily:
        lines.append(bold("  Daily Breakdown"))
        lines.append(_separator())
        header = f"  {'Date':<12}| {'Tokens':>13} | {'Cost':>10} | {'Tool Calls':>10}"
        lines.append(dim(header))
        lines.append(dim(f"  {'-' * 12}+{'-' * 15}+{'-' * 12}+{'-' * 12}"))

        for day in reversed(days_data):
            tokens = day.get("total_tokens", 0)
            cost = day.get("cost", 0)
            tool_calls = day.get("tool_calls", 0)
            if tokens == 0 and cost == 0:
                continue
            date_str = day.get("date", "?")
            lines.append(f"  {date_str:<12}| {fmt_int(tokens):>13} | {fmt_usd(cost):>10} | {tool_calls:>10}")

        lines.append("")

    # ── Efficiency metrics ────────────────────────────────────────
    if args.efficiency:
        lines.append(bold("  Efficiency Metrics"))
        lines.append(_separator())

        summary = efficiency_metrics.get("summary", {})
        daily_eff = efficiency_metrics.get("daily", [])

        _LABELS = {
            "avg_reasoning_ratio": "Avg reasoning ratio",
            "avg_cache_hit_rate": "Avg cache hit rate",
            "avg_tokens_per_message": "Avg tokens/message",
            "tokens_per_session": "Tokens/session",
            "cost_per_session": "Cost/session",
            "tool_calls_per_session": "Tool calls/session",
            "cache_ratio": "Cache ratio",
            "avg_session_minutes": "Avg session minutes",
        }

        if summary:
            for key, value in summary.items():
                label = _LABELS.get(key, key.replace("_", " ").title())
                if isinstance(value, float):
                    if "ratio" in key or "rate" in key:
                        lines.append(f"  {label + ':':<26} {value * 100:.1f}%")
                    else:
                        lines.append(f"  {label + ':':<26} {value:,.1f}")
                else:
                    lines.append(f"  {label + ':':<26} {fmt_int(value)}")
        else:
            lines.append(dim("  No efficiency data available."))

        # Also show per-day efficiency if daily data is available
        if daily_eff:
            lines.append("")
            lines.append(bold("  Daily Efficiency"))
            lines.append(dim(f"  {'Date':<12}| {'Reasoning':>10} | {'Cache Hit':>10} | {'Tok/Msg':>10}"))
            lines.append(dim(f"  {'-' * 12}+{'-' * 12}+{'-' * 12}+{'-' * 12}"))
            for d in reversed(daily_eff):
                r_ratio = d.get("reasoning_ratio", 0)
                c_rate = d.get("cache_hit_rate", 0)
                t_per_m = d.get("tokens_per_message", 0)
                lines.append(
                    f"  {d.get('date', '?'):<12}| {r_ratio * 100:>9.1f}% | {c_rate * 100:>9.1f}% | {t_per_m:>10,.0f}"
                )

        lines.append("")

    # Show any extra top-level keys from efficiency_metrics
    if args.efficiency:
        extra_keys = set(efficiency_metrics.keys()) - {"summary", "daily"}
        if extra_keys:
            lines.append(bold("  Additional Efficiency Data"))
            lines.append(_separator())
            for key in sorted(extra_keys):
                value = efficiency_metrics[key]
                label = key.replace("_", " ").title()
                if isinstance(value, (int, float)):
                    lines.append(f"  {label + ':':<26} {value}")
            lines.append("")

    # ── Summary footer ────────────────────────────────────────────
    lines.append(_separator())
    lines.append(f"  Total cost: {bold(fmt_usd(grand_cost))}")
    lines.append("")

    output_path = getattr(args, "output", None)
    # Strip ANSI for file output
    if output_path:
        import re

        ansi_escape = re.compile(r"\033\[\d+m")
        plain = "\n".join(ansi_escape.sub("", line) for line in lines)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(plain + "\n", encoding="utf-8")
        print(f"Trends exported -> {output_path}")
    else:
        sys.stdout.write("\n".join(lines) + "\n")
