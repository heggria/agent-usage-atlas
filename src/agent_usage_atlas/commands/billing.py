"""5-hour billing window query command."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import NamedTuple

from ..cli import build_dashboard_payload
from ..models import fmt_int, fmt_usd
from ._ansi import bold, cyan, dim, green, red, yellow

# Cost thresholds for color coding (per 5h window)
_THRESHOLD_RED = 100.0
_THRESHOLD_YELLOW = 30.0

# Bar chart settings
_BAR_WIDTH = 20  # max █ chars


class _Window(NamedTuple):
    label: str          # e.g. "14:00–19:00"
    start_hour: int     # 0-based hour of the window start (within a day)
    date: str           # YYYY-MM-DD of the window's start
    cost: float
    tokens: int
    tool_calls: int


def add_parser(subparsers):
    parser = subparsers.add_parser(
        "billing",
        help="Show cost for recent billing windows (5h rolling)",
    )
    parser.add_argument(
        "--windows",
        type=int,
        default=6,
        help="Number of 5h windows to show (default: 6, covering 30h)",
    )
    parser.set_defaults(func=run)
    return parser


def _color_cost(cost: float, text: str) -> str:
    if cost >= _THRESHOLD_RED:
        return red(text)
    if cost >= _THRESHOLD_YELLOW:
        return yellow(text)
    return green(text)


def _bar(cost: float, max_cost: float) -> str:
    if max_cost <= 0:
        return dim("─" * _BAR_WIDTH)
    filled = round(_BAR_WIDTH * cost / max_cost)
    filled = max(0, min(_BAR_WIDTH, filled))
    bar = "█" * filled + dim("░" * (_BAR_WIDTH - filled))
    return bar


def _pct_change(prev: float, curr: float) -> str:
    if prev <= 0:
        return dim("  n/a ")
    pct = (curr - prev) / prev * 100
    sign = "+" if pct >= 0 else ""
    s = f"{sign}{pct:5.1f}%"
    if pct > 20:
        return red(s)
    if pct < -20:
        return green(s)
    return yellow(s)


def _build_windows(hourly_rows: list[dict], n_windows: int, now_local: datetime) -> list[_Window]:
    """
    Slice the last n_windows * 5 hours into fixed 5h buckets, working
    backwards from *now* so the most recent window is always shown.

    hourly_rows: list of 24 dicts keyed by hour (0-23), each with 'cost',
    'output', 'reasoning', and source totals.  These come from
    working_patterns.hourly_source_totals which aggregates across all
    days in the requested date range.

    Because the hourly data is already collapsed to a 24-hour view (no
    per-day breakdown), we use the daily rows to split cost by day and
    then assign hours proportionally.  Where a window spans midnight the
    window cost is the sum of the relevant fractional days.

    Actually the payload gives us only aggregate hourly rows (hour 0-23
    across all days), so we build windows from those directly.  Each
    window is a 5-hour slice of the 24-hour clock, anchored to the
    current hour so "window 0" always ends at *now*.
    """
    # Build a cost/token lookup by hour-of-day (0-23)
    cost_by_hour: dict[int, float] = {}
    tokens_by_hour: dict[int, int] = {}
    tools_by_hour: dict[int, int] = {}

    for row in hourly_rows:
        h = row.get("hour")
        if h is None:
            continue
        cost_by_hour[h] = row.get("cost") or 0.0
        # tokens = output + reasoning (raw tokens visible here)
        tokens_by_hour[h] = (row.get("output") or 0) + (row.get("reasoning") or 0)
        # tool density not available in hourly_source_totals — leave 0
        tools_by_hour[h] = 0

    # Anchor windows to the current hour (truncate minutes)
    current_hour = now_local.hour  # 0-23
    windows: list[_Window] = []

    for i in range(n_windows):
        # Window i ends at (current_hour - i*5), exclusive
        end_offset = i * 5          # hours before now
        start_offset = end_offset + 5

        # Compute which hours this window covers (mod 24, backwards)
        hours_in_window = [(current_hour - start_offset + j) % 24 for j in range(5)]

        w_cost = sum(cost_by_hour.get(h, 0.0) for h in hours_in_window)
        w_tokens = sum(tokens_by_hour.get(h, 0) for h in hours_in_window)
        w_tools = sum(tools_by_hour.get(h, 0) for h in hours_in_window)

        # Compute the wall-clock start/end for the label
        win_end_dt = now_local.replace(minute=0, second=0, microsecond=0) - timedelta(hours=end_offset)
        win_start_dt = win_end_dt - timedelta(hours=5)
        label = f"{win_start_dt.strftime('%H:%M')}–{win_end_dt.strftime('%H:%M')}"
        date_str = win_start_dt.strftime("%Y-%m-%d")

        windows.append(
            _Window(
                label=label,
                start_hour=win_start_dt.hour,
                date=date_str,
                cost=w_cost,
                tokens=w_tokens,
                tool_calls=w_tools,
            )
        )

    # Reverse so oldest is first
    windows.reverse()
    return windows


def run(args) -> None:
    local_tz = datetime.now(timezone.utc).astimezone().tzinfo
    now_local = datetime.now(local_tz)

    # Request enough days to cover all windows plus a buffer day
    n_windows: int = args.windows
    hours = n_windows * 5 + 24  # extra 24h buffer
    since_local = now_local - timedelta(hours=hours)
    since_str = since_local.strftime("%Y-%m-%d")

    try:
        dashboard = build_dashboard_payload(since=since_str)
    except ValueError as exc:
        raise SystemExit(f"Invalid date: {exc}") from exc

    totals = dashboard.get("totals", {})
    working_patterns = dashboard.get("working_patterns", {})
    hourly_rows: list[dict] = working_patterns.get("hourly_source_totals", [])
    days: list[dict] = dashboard.get("days", [])

    grand_tokens: int = totals.get("grand_total") or 0

    windows = _build_windows(hourly_rows, n_windows, now_local)
    max_cost = max((w.cost for w in windows), default=0.0)

    # ── Header ────────────────────────────────────────────────────────────
    print()
    print(bold(f"  Billing Windows (5h)  ·  last {n_windows * 5}h  ·  {now_local.strftime('%Y-%m-%d %H:%M %Z')}"))
    print(dim("  " + "─" * 72))

    # Column headers
    hdr = (
        f"  {'Window':<22}"
        f"{'Cost':>10}"
        f"  {'Bar':<{_BAR_WIDTH + 2}}"
        f"{'Δ prev':>8}"
        f"{'Tokens':>14}"
        f"{'Running':>12}"
    )
    print(dim(hdr))
    print(dim("  " + "─" * 72))

    running_total = 0.0
    prev_cost: float | None = None

    for win in windows:
        running_total += win.cost
        cost_str = fmt_usd(win.cost)
        colored_cost = _color_cost(win.cost, f"{cost_str:>10}")
        bar_str = _color_cost(win.cost, _bar(win.cost, max_cost))
        delta_str = _pct_change(prev_cost, win.cost) if prev_cost is not None else dim("  n/a ")
        tokens_str = fmt_int(win.tokens) if win.tokens > 0 else dim("      –")
        running_str = fmt_usd(running_total)

        print(
            f"  {cyan(win.date)} {dim(win.label):<13}"
            f"{colored_cost}"
            f"  {bar_str}  "
            f"{delta_str}"
            f"  {dim(tokens_str):>14}"
            f"  {bold(running_str):>12}"
        )
        prev_cost = win.cost

    # ── Divider ───────────────────────────────────────────────────────────
    print(dim("  " + "─" * 72))

    # ── Daily breakdown (if any data) ─────────────────────────────────────
    active_days = [d for d in days if d.get("cost", 0) > 0 or d.get("total_tokens", 0) > 0]
    if active_days:
        print()
        print(bold("  Daily breakdown"))
        print(dim("  " + "─" * 72))
        day_header = f"  {'Date':<14}{'Cost':>10}  {'Tokens':>16}  {'Tool calls':>12}"
        print(dim(day_header))
        for d in active_days:
            d_date = d.get("date")
            if not d_date:
                continue
            d_cost = d.get("cost", 0.0)
            d_tokens = d.get("total_tokens", 0)
            d_tools = d.get("tool_calls", 0)
            print(
                f"  {cyan(d_date):<14}"
                f"{_color_cost(d_cost, fmt_usd(d_cost)):>10}"
                f"  {dim(fmt_int(d_tokens)):>16}"
                f"  {dim(fmt_int(d_tools)):>12}"
            )
        print(dim("  " + "─" * 72))

    # ── Summary ───────────────────────────────────────────────────────────
    n_active = sum(1 for w in windows if w.cost > 0)
    avg_cost = running_total / max(n_active, 1)
    # Project a 24h day: 24h / 5h * avg window cost
    projected_daily = avg_cost * (24 / 5)

    print()
    print(
        f"  {bold('Total (window range)'):<30}  "
        f"{_color_cost(running_total, bold(fmt_usd(running_total)))}"
        f"  {dim(fmt_int(grand_tokens) + ' tok')}"
    )
    print(
        f"  {dim('Average per 5h window'):<30}  "
        f"{_color_cost(avg_cost, fmt_usd(avg_cost))}"
    )
    print(
        f"  {dim('Projected daily (24h)'):<30}  "
        f"{_color_cost(projected_daily, fmt_usd(projected_daily))}"
    )
    print()
