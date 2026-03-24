"""Today's usage summary -- from midnight to now, with optional live refresh."""

from __future__ import annotations

import os
import sys
import time
import warnings
from datetime import datetime, timezone

from ..cli import build_dashboard_payload
from ..models import fmt_int, fmt_short, fmt_usd
from ._ansi import _supports_color, bold, cyan, dim, red, yellow

# today.py historically used _green mapped to ANSI code 36 (cyan).
# Preserve that behavior by aliasing cyan as the "green" display color.
_green = cyan


# ── Rendering ─────────────────────────────────────────────────────────


def _build_frame(*, quiet: bool = False, footer: str = "") -> list[str]:
    """Fetch today's data and render to a list of lines (no I/O)."""
    local_tz = datetime.now(timezone.utc).astimezone().tzinfo
    now_local = datetime.now(local_tz)
    today_str = now_local.strftime("%Y-%m-%d")
    hour_now = now_local.hour
    min_now = now_local.minute

    if quiet:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            dashboard = build_dashboard_payload(since=today_str)
    else:
        dashboard = build_dashboard_payload(since=today_str)

    totals = dashboard.get("totals", {})
    source_cards = dashboard.get("source_cards", [])
    model_costs = dashboard.get("trend_analysis", {}).get("model_costs", [])
    hourly_rows = dashboard.get("working_patterns", {}).get("hourly_source_totals", [])

    grand_tokens = totals.get("grand_total", 0)
    grand_cost = totals.get("grand_cost", 0.0)
    tool_total = totals.get("tool_call_total", 0)
    session_count = totals.get("session_count", 0)

    elapsed_h = hour_now + min_now / 60.0
    rate_h = grand_cost / elapsed_h if elapsed_h > 0.1 else 0.0
    projected_day = rate_h * 24

    lines: list[str] = []

    # Header
    lines.append(bold(f"  Today  {today_str}") + dim(f"  ({hour_now}h {min_now}m elapsed)"))
    lines.append(dim("\u2500" * 50))

    # Grand totals
    cost_color = red if grand_cost > 50 else (yellow if grand_cost > 10 else _green)
    lines.append(f"  Tokens   {bold(fmt_int(grand_tokens))}")
    lines.append(f"  Cost     {bold(cost_color(fmt_usd(grand_cost)))}")
    lines.append(f"  Tools    {fmt_int(tool_total)}")
    lines.append(f"  Sessions {session_count:,}")

    # Cache efficiency
    cache_ratio = totals.get("cache_ratio", 0)
    cache_savings = totals.get("cache_savings_usd", 0.0)
    if cache_ratio > 0:
        ratio_color = _green if cache_ratio >= 0.5 else (yellow if cache_ratio >= 0.2 else dim)
        pct = f"{cache_ratio * 100:.0f}%"
        lines.append(f"  Cache    {ratio_color(pct)} hit  {dim('saved ' + fmt_usd(cache_savings))}")

    # Rate
    if rate_h > 0:
        proj_color = red if projected_day > 100 else (yellow if projected_day > 30 else _green)
        lines.append("")
        lines.append(f"  Rate     {fmt_usd(rate_h)}/h  ->  {proj_color(fmt_usd(projected_day))}/day projected")

    # By source
    active_sources = [c for c in source_cards if c.get("cost", 0) > 0 or c.get("messages", 0) > 0]
    if active_sources:
        lines.append("")
        for card in sorted(active_sources, key=lambda c: c.get("cost", 0), reverse=True):
            src = card["source"]
            if card.get("token_capable"):
                tok = fmt_int(card["total"])
                cst = fmt_usd(card["cost"])
            else:
                tok = f"{fmt_int(card['messages'])} msgs"
                cst = "-"
            lines.append(f"  {src:<12s} {tok:>14s}  {cst:>10s}  {card['sessions']:>3} sessions")

    # Top 3 models
    if model_costs:
        lines.append("")
        for mc in model_costs[:3]:
            lines.append(f"  {mc['model']:<28s} {fmt_usd(mc['cost']):>10s}")

    # Hourly breakdown
    sources_in_hourly = ("Claude", "Codex", "Hermit", "Cursor")
    active_hours = [
        r for r in hourly_rows
        if r["hour"] <= hour_now and sum(r.get(s, 0) for s in sources_in_hourly) > 0
    ]
    if active_hours:
        peak_cost = max((r.get("cost", 0.0) for r in active_hours), default=0.0)
        lines.append("")
        lines.append(bold("  Hour   Tokens        Out+Reason    Cost"))
        lines.append(dim("  " + "\u2500" * 44))
        for r in active_hours:
            h = r["hour"]
            total_h = sum(r.get(s, 0) for s in sources_in_hourly)
            out_reason = r.get("output", 0) + r.get("reasoning", 0)
            cost_h = r.get("cost", 0.0)
            marker = " <" if h == hour_now else ""
            t_s = fmt_short(total_h)
            o_s = fmt_short(out_reason)
            c_s = fmt_usd(cost_h)
            row = f"  {h:02d}:00  {t_s:>10s}  {o_s:>12s}  {c_s:>8s}{dim(marker)}"
            lines.append(bold(row) if (peak_cost > 0 and cost_h == peak_cost) else row)

        _SPARK = " \u2581\u2582\u2583\u2584\u2585\u2586\u2587\u2588"
        costs_by_hour = {r["hour"]: r.get("cost", 0.0) for r in active_hours}
        all_hour_costs = [costs_by_hour.get(h, 0.0) for h in range(hour_now + 1)]
        max_c = max(all_hour_costs) if any(all_hour_costs) else 1.0
        spark_chars = "".join(_SPARK[min(8, int(c / max_c * 8))] for c in all_hour_costs)
        lines.append(f"  {dim('Cost curve')}  {_green(spark_chars)}")

        total_out = sum(r.get("output", 0) for r in active_hours)
        total_reason = sum(r.get("reasoning", 0) for r in active_hours)
        if grand_tokens > 0:
            out_pct = total_out / grand_tokens * 100
            reason_pct = total_reason / grand_tokens * 100
            o_s = fmt_short(total_out)
            r_s = fmt_short(total_reason)
            lines.append(
                f"  {dim('Output')} {o_s} ({out_pct:.0f}%)  "
                f"{dim('Reasoning')} {r_s} ({reason_pct:.0f}%)"
            )

    lines.append(dim("\u2500" * 50))

    if footer:
        lines.append(footer)

    return lines


def _paint(lines: list[str], *, is_refresh: bool = False) -> None:
    """Write frame to stdout. Erase each line individually to avoid ghosting."""
    use_color = _supports_color()
    if is_refresh and use_color:
        parts = ["\033[H"]
        for line in lines:
            parts.append(f"\033[2K{line}\n")
        parts.append("\033[J")
        sys.stdout.write("".join(parts))
    else:
        sys.stdout.write("\n".join(lines) + "\n")
    sys.stdout.flush()


# ── CLI ───────────────────────────────────────────────────────────────


def add_parser(subparsers):
    parser = subparsers.add_parser(
        "today",
        help="Show today's total token and cost consumption (midnight to now)",
    )
    parser.add_argument(
        "--refresh",
        type=int,
        default=0,
        metavar="SECS",
        help="Auto-refresh interval in seconds (0 = one-shot, default: 0)",
    )
    parser.set_defaults(func=run)
    return parser


def run(args) -> None:
    refresh: int = args.refresh
    use_color = _supports_color()

    if refresh <= 0:
        _paint(_build_frame(quiet=False))
        return

    # Live mode -- suppress stderr to keep display clean
    saved_stderr = sys.stderr
    try:
        sys.stderr = open(os.devnull, "w")  # noqa: SIM115
    except OSError:
        pass

    if use_color:
        sys.stdout.write("\033[?25l\033[2J\033[H")  # hide cursor + clear once
        sys.stdout.flush()
    try:
        first = True
        while True:
            footer = dim(f"  Refreshing every {refresh}s -- Ctrl+C to stop")
            lines = _build_frame(quiet=True, footer=footer)
            _paint(lines, is_refresh=not first)
            first = False
            time.sleep(refresh)
    except KeyboardInterrupt:
        pass
    finally:
        if use_color:
            sys.stdout.write("\033[?25h")
            sys.stdout.flush()
        if sys.stderr is not saved_stderr:
            try:
                sys.stderr.close()
            except OSError:
                pass
            sys.stderr = saved_stderr
        print()
