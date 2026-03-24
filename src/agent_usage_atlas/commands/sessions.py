"""List and filter sessions from agent usage logs."""

from __future__ import annotations

import statistics

from ..cli import build_dashboard_payload
from ..models import fmt_int, fmt_short, fmt_usd
from ._ansi import bold, cyan, dim, green, red, yellow

# ── Subcommand registration ───────────────────────────────────────────


def add_parser(subparsers):
    parser = subparsers.add_parser(
        "sessions",
        help="List and filter sessions from agent usage logs",
    )
    parser.add_argument(
        "--source",
        choices=["claude", "codex", "cursor", "hermit"],
        default=None,
        help="Filter by source",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="Number of sessions to show (default: 10)",
    )
    parser.add_argument(
        "--sort",
        choices=["cost", "tokens", "tools", "duration"],
        default="cost",
        help="Sort criterion (default: cost)",
    )
    parser.add_argument(
        "--min-cost",
        type=float,
        default=0.0,
        help="Minimum cost threshold (default: 0.0)",
    )
    parser.set_defaults(func=run)
    return parser


# ── Sort key mapping ──────────────────────────────────────────────────

_SORT_KEYS: dict[str, str] = {
    "cost": "cost",
    "tokens": "total",
    "tools": "tool_calls",
    "duration": "minutes",
}


# ── Command implementation ────────────────────────────────────────────


def run(args) -> None:
    try:
        dashboard = build_dashboard_payload(days=args.days, since=args.since)
    except ValueError as exc:
        raise SystemExit(f"Invalid --since date format: {exc}") from exc

    all_sessions: list[dict] = dashboard.get("top_sessions", [])
    total_count = len(all_sessions)

    # Apply source filter (case-insensitive)
    if args.source:
        source_lower = args.source.lower()
        filtered = [s for s in all_sessions if s.get("source", "").lower() == source_lower]
    else:
        filtered = list(all_sessions)

    # Apply minimum cost filter
    if args.min_cost > 0:
        filtered = [s for s in filtered if s.get("cost", 0) >= args.min_cost]

    filtered_count = len(filtered)

    # Sort by chosen criterion (descending)
    sort_key = _SORT_KEYS[args.sort]
    filtered.sort(key=lambda s: s.get(sort_key, 0), reverse=True)

    # Take top N
    top_n = filtered[: args.top]

    # ── Pre-compute bar chart scale ────────────────────────────────────
    _BAR_CHARS = "▏▎▍▌▋▊▉█"
    _BAR_WIDTH = 8
    max_cost = max((s.get("cost", 0) for s in top_n), default=0) or 1.0

    def _cost_bar(cost_val: float) -> str:
        ratio = max(0.0, min(1.0, cost_val / max_cost))
        filled_eighths = round(ratio * _BAR_WIDTH * 8)
        full_blocks = filled_eighths // 8
        partial = filled_eighths % 8
        bar = "█" * full_blocks
        if partial and full_blocks < _BAR_WIDTH:
            bar += _BAR_CHARS[partial - 1]
        bar = bar.ljust(_BAR_WIDTH)
        return bar

    def _color_cost(cost_val: float, text: str) -> str:
        if cost_val > 50:
            return red(text)
        if cost_val > 10:
            return yellow(text)
        return green(text)

    def _parse_hhmm(iso: str) -> str:
        """Extract HH:MM from an ISO-format datetime string."""
        try:
            # handles both "2026-03-23T14:05:00" and "2026-03-23 14:05:00"
            time_part = iso.replace("T", " ").split(" ")[1]
            return time_part[:5]
        except (IndexError, AttributeError):
            return "--:--"

    def _cache_pct(s: dict) -> str:
        total = s.get("total", 0)
        if not total:
            return " --%"
        cr = s.get("cache_read", 0)
        cw = s.get("cache_write", 0)
        pct = (cr + cw) / total * 100
        return f"{pct:4.0f}%"

    # ── Print table ────────────────────────────────────────────────────
    cols = [
        f"{'#':>3}",
        f"{'Source':<8}",
        f"{'Session ID':<14}",
        f"{'Time':>5}",
        f"{'Tokens':>12}",
        f"{'Cache%':>6}",
        f"{'Cost':>10}",
        f"{'Bar':<{_BAR_WIDTH}}",
        f"{'Tools':>5}",
        f"{'Dur':>5}",
        "Model",
    ]
    header = " | ".join(cols)
    separator = "-" * len(header)

    print(bold(header))
    print(separator)

    for idx, session in enumerate(top_n, start=1):
        source = session.get("source", "-")
        sid = session.get("session_id", "-")
        if len(sid) > 14:
            sid = sid[:12] + ".."
        tokens = fmt_int(session.get("total", 0))
        cost_val = session.get("cost", 0)
        cost_str = fmt_usd(cost_val)
        colored_cost = _color_cost(cost_val, f"{cost_str:>10}")
        bar = _cost_bar(cost_val)
        tools = session.get("tool_calls", 0)
        minutes = session.get("minutes", 0)
        dur = f"{int(minutes)}m" if minutes else "-"
        model = session.get("top_model", "-")
        first_local = session.get("first_local", "")
        time_str = _parse_hhmm(first_local)
        cache_str = _cache_pct(session)

        row = " | ".join(
            [
                f"{idx:>3}",
                f"{source:<8}",
                f"{sid:<14}",
                cyan(f"{time_str:>5}"),
                f"{tokens:>12}",
                f"{cache_str:>6}",
                colored_cost,
                bar,
                f"{tools:>5}",
                f"{dur:>5}",
                model,
            ]
        )
        print(row)

    print(separator)
    shown = len(top_n)
    print(dim(f"Showing {shown} of {filtered_count} sessions (filtered from {total_count} total)"))

    # ── Summary footer ─────────────────────────────────────────────────
    if top_n:
        total_cost = sum(s.get("cost", 0) for s in top_n)
        durations = [s.get("minutes", 0) for s in top_n if s.get("minutes", 0) > 0]
        avg_dur = statistics.mean(durations) if durations else 0
        token_list = [s.get("total", 0) for s in top_n]
        median_tokens = statistics.median(token_list) if token_list else 0

        avg_dur_str = f"{avg_dur:.0f}m" if avg_dur else "-"
        print()
        print(
            bold("Summary: ")
            + f"total cost {_color_cost(total_cost, fmt_usd(total_cost))}  |  "
            + f"avg duration {cyan(avg_dur_str)}  |  "
            + f"median tokens {cyan(fmt_short(median_tokens))}"
        )
