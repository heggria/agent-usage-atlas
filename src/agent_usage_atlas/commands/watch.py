"""Rolling live consumption monitor -- shows usage for the last N minutes."""

from __future__ import annotations

import os
import sys
import time
import warnings
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from ..models import fmt_int, fmt_usd
from ._ansi import _supports_color, bold, cyan, dim, green, red, yellow

# ── Sparkline ─────────────────────────────────────────────────────────

_SPARK_CHARS = " \u2581\u2582\u2583\u2584\u2585\u2586\u2587\u2588"


def _sparkline(values: list[float]) -> str:
    if not values:
        return ""
    lo = min(values)
    hi = max(values)
    rng = hi - lo if hi > lo else 1.0
    return "".join(_SPARK_CHARS[min(7, int((v - lo) / rng * 7))] for v in values)


def _colored_sparkline(values: list[float]) -> str:
    """Sparkline where each char is colored by its relative value.

    Top 25% → red, middle 50% → yellow, bottom 25% → green.
    """
    if not values:
        return ""
    lo = min(values)
    hi = max(values)
    rng = hi - lo if hi > lo else 1.0
    result = []
    for v in values:
        frac = (v - lo) / rng  # 0.0 … 1.0
        char = _SPARK_CHARS[min(7, int(frac * 7))]
        if frac >= 0.75:
            result.append(red(char))
        elif frac >= 0.25:
            result.append(yellow(char))
        else:
            result.append(green(char))
    return "".join(result)


def _trend_arrow(buckets: list[float]) -> str:
    """Return ↑ (red) or ↓ (green) comparing last bucket to window average."""
    if not buckets or all(v == 0 for v in buckets):
        return dim("→")
    avg = sum(buckets) / len(buckets)
    last = buckets[-1]
    if last > avg:
        return red("↑")
    if last < avg:
        return green("↓")
    return dim("→")


# Source → colored dot character for heatmap
_SOURCE_DOT: dict[str, str] = {}  # populated lazily in _render_to_lines


def _source_dot(source: str) -> str:
    """Return a colored dot for a known source, or a dim dot for unknown."""
    src = source.lower()
    if "claude" in src:
        return cyan("•")
    if "codex" in src:
        return green("•")
    if "hermit" in src:
        return yellow("•")
    if "cursor" in src:
        return dim("•")
    return dim("·")


def _composition_bar(input_tok: int, cache_tok: int, output_tok: int, width: int = 40) -> str:
    """Render a proportional bar: input (dim) | cache (cyan) | output (green)."""
    total = input_tok + cache_tok + output_tok
    if total == 0:
        return dim("─" * width)
    i_w = max(0, round(input_tok / total * width))
    c_w = max(0, round(cache_tok / total * width))
    o_w = width - i_w - c_w
    return dim("█" * i_w) + cyan("█" * c_w) + green("█" * o_w)


# ── Data fetching ─────────────────────────────────────────────────────


def _fetch_window(minutes: int, *, quiet: bool = False) -> dict:
    """Parse all logs, filter to last *minutes* minutes, return summary.

    When *quiet* is True, suppress all warnings so they don't corrupt
    the live-refresh display.
    """
    from ..parsers import parse_all

    local_tz = datetime.now(timezone.utc).astimezone().tzinfo
    now_utc = datetime.now(timezone.utc)
    now_local = now_utc.astimezone(local_tz)
    start_utc = now_utc - timedelta(minutes=minutes)

    if quiet:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result, _, _ = parse_all(start_utc, now_utc, local_tz=local_tz)
    else:
        result, _, _ = parse_all(start_utc, now_utc, local_tz=local_tz)

    events = [e for e in result.events if start_utc <= e.timestamp <= now_utc]
    tool_calls = [t for t in result.tool_calls if start_utc <= t.timestamp <= now_utc]

    # Grand totals
    total_tokens = sum(e.total for e in events)
    total_cost = sum(e.cost for e in events)
    total_tools = len(tool_calls)

    # By source
    source_tokens: dict[str, int] = defaultdict(int)
    source_cost: dict[str, float] = defaultdict(float)
    source_events: dict[str, int] = defaultdict(int)
    for e in events:
        source_tokens[e.source] += e.total
        source_cost[e.source] += e.cost
        source_events[e.source] += 1

    # By model
    model_tokens: dict[str, int] = defaultdict(int)
    model_cost: dict[str, float] = defaultdict(float)
    for e in events:
        model_tokens[e.model] += e.total
        model_cost[e.model] += e.cost

    # Active sessions
    sessions = {(e.source, e.session_id) for e in events}

    # Per-minute buckets for sparkline (last N minutes, 1-min resolution)
    bucket_count = min(minutes, 60)  # cap at 60 buckets for display
    bucket_width = minutes / bucket_count
    buckets_cost: list[float] = [0.0] * bucket_count
    buckets_tokens: list[float] = [0.0] * bucket_count
    # Per-bucket source set for heatmap strip
    buckets_sources: list[set[str]] = [set() for _ in range(bucket_count)]
    for e in events:
        offset_min = (e.timestamp - start_utc).total_seconds() / 60.0
        idx = min(bucket_count - 1, max(0, int(offset_min / bucket_width)))
        buckets_cost[idx] += e.cost
        buckets_tokens[idx] += e.total
        buckets_sources[idx].add(e.source)

    # Tool ranking (top 5)
    tool_counts: dict[str, int] = defaultdict(int)
    for t in tool_calls:
        tool_counts[t.tool_name] += 1
    top_tools = sorted(tool_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    # Token composition totals (input, cache, output+reasoning)
    total_input_tok = sum(e.uncached_input for e in events)
    total_cache_tok = sum(e.cache_read + e.cache_write for e in events)
    total_output_tok = sum(e.output + e.reasoning for e in events)

    return {
        "now_local": now_local,
        "minutes": minutes,
        "total_tokens": total_tokens,
        "total_cost": total_cost,
        "total_tools": total_tools,
        "total_events": len(events),
        "sessions": len(sessions),
        "source_tokens": dict(source_tokens),
        "source_cost": dict(source_cost),
        "source_events": dict(source_events),
        "model_tokens": dict(model_tokens),
        "model_cost": dict(model_cost),
        "top_tools": top_tools,
        "buckets_cost": buckets_cost,
        "buckets_tokens": buckets_tokens,
        "buckets_sources": buckets_sources,
        "rate_per_hour_tokens": total_tokens / (minutes / 60) if minutes > 0 else 0,
        "rate_per_hour_cost": total_cost / (minutes / 60) if minutes > 0 else 0.0,
        "total_input_tok": total_input_tok,
        "total_cache_tok": total_cache_tok,
        "total_output_tok": total_output_tok,
    }


# ── Display (double-buffered for flicker-free refresh) ────────────────


def _render_to_lines(data: dict, *, compact: bool = False, footer: str = "") -> list[str]:
    """Build all output lines into a list (no I/O)."""
    lines: list[str] = []
    now_str = data["now_local"].strftime("%H:%M:%S")
    mins = data["minutes"]

    lines.append(bold(f"  Agent Usage -- last {mins} min  ") + dim(f"@ {now_str}"))
    lines.append(dim("\u2500" * 58))

    # Velocity metrics
    events_per_min = data["total_events"] / mins if mins > 0 else 0.0
    tools_per_min = data["total_tools"] / mins if mins > 0 else 0.0

    # Grand totals
    lines.append(
        f"  Tokens  {bold(fmt_int(data['total_tokens'])):>16}  "
        f"{dim('|')}  Cost  {bold(fmt_usd(data['total_cost'])):>10}"
    )
    lines.append(f"  Events  {data['total_events']:>16,}  {dim('|')}  Tools {data['total_tools']:>10,}")
    lines.append(f"  Sessions{data['sessions']:>16,}  {dim('|')}  Rate  {fmt_usd(data['rate_per_hour_cost'])}/h")
    lines.append(
        f"  {dim('events/min')}  {cyan(f'{events_per_min:.2f}'):>14}  "
        f"{dim('|')}  {dim('tools/min')}  {cyan(f'{tools_per_min:.2f}'):>8}"
    )

    # Sparklines with color-coding and trend arrows
    buckets_cost = data["buckets_cost"]
    buckets_tokens = data["buckets_tokens"]
    cost_spark = _colored_sparkline(buckets_cost)
    token_spark = _colored_sparkline(buckets_tokens)
    if cost_spark:
        cost_arrow = _trend_arrow(buckets_cost)
        token_arrow = _trend_arrow(buckets_tokens)
        lines.append("")
        lines.append(f"  Cost    {cost_spark} {cost_arrow}")
        lines.append(f"  Tokens  {token_spark} {token_arrow}")

    # Activity heatmap strip (sources active per bucket)
    buckets_sources: list[set[str]] = data.get("buckets_sources", [])
    if buckets_sources and any(s for s in buckets_sources):
        # Collect all observed sources in order of first appearance
        seen: list[str] = []
        for bucket in buckets_sources:
            for src in sorted(bucket):
                if src not in seen:
                    seen.append(src)
        # Build heatmap: for each bucket, show dots for active sources
        # (collapsed to one char per bucket — pick dominant source or blank)
        heatmap_chars: list[str] = []
        for bucket in buckets_sources:
            if not bucket:
                heatmap_chars.append(dim(" "))
            else:
                # Pick first active source alphabetically for display
                src = sorted(bucket)[0]
                heatmap_chars.append(_source_dot(src))
        legend_parts = [_source_dot(s) + dim(s) for s in seen]
        lines.append(f"  Sources {''.join(heatmap_chars)}  {dim('|')} {' '.join(legend_parts)}")

    # Token composition bar (input dim | cache cyan | output green)
    input_tok = data.get("total_input_tok", 0)
    cache_tok = data.get("total_cache_tok", 0)
    output_tok = data.get("total_output_tok", 0)
    if input_tok + cache_tok + output_tok > 0:
        bar = _composition_bar(input_tok, cache_tok, output_tok, width=40)
        total_tok = input_tok + cache_tok + output_tok
        pct_cache = cache_tok / total_tok * 100 if total_tok else 0
        pct_out = output_tok / total_tok * 100 if total_tok else 0
        lines.append(
            f"  Toks    {bar}  "
            + dim(f"in/{cyan('cache')}/{green('out')}  "
                  f"cache {pct_cache:.0f}%  out {pct_out:.0f}%")
        )

    # By source
    if data["source_cost"]:
        lines.append("")
        lines.append(f"  {dim('Source'):<20s} {dim('Tokens'):>14s}  {dim('Cost'):>10s}  {dim('Events'):>7s}")
        for src in sorted(data["source_cost"], key=lambda s: data["source_cost"][s], reverse=True):
            tokens = fmt_int(data["source_tokens"].get(src, 0))
            cost = fmt_usd(data["source_cost"][src])
            evts = data["source_events"].get(src, 0)
            lines.append(f"  {src:<20s} {tokens:>14s}  {cost:>10s}  {evts:>7,}")

    if not compact:
        # By model (top 5)
        model_items = sorted(data["model_cost"].items(), key=lambda x: x[1], reverse=True)[:5]
        if model_items:
            lines.append("")
            lines.append(f"  {dim('Model'):<30s} {dim('Cost'):>10s}  {dim('Tokens'):>14s}")
            for model, cost in model_items:
                tokens = fmt_int(data["model_tokens"].get(model, 0))
                lines.append(f"  {model:<30s} {fmt_usd(cost):>10s}  {tokens:>14s}")

        # Top tools
        if data["top_tools"]:
            lines.append("")
            lines.append(f"  {dim('Top Tools'):<30s} {dim('Count'):>10s}")
            for name, count in data["top_tools"]:
                lines.append(f"  {name:<30s} {count:>10,}")

    # Projection
    rate_h = data["rate_per_hour_cost"]
    if rate_h > 0:
        lines.append("")
        projected_day = rate_h * 24
        color_fn = red if rate_h > 10 else (yellow if rate_h > 3 else green)
        proj = f"{color_fn(fmt_usd(rate_h))}/h  ->  {color_fn(fmt_usd(projected_day))}/day"
        lines.append(f"  {dim('Projected:')}  {proj}")

    lines.append(dim("\u2500" * 58))

    if footer:
        lines.append(footer)

    return lines


def _paint(lines: list[str], *, is_refresh: bool = False) -> None:
    """Write pre-built lines to stdout in one shot, flicker-free.

    Each line is prefixed with ``\\033[2K`` (erase entire line) so that
    shorter new content fully replaces longer old content -- no ghosting
    even when ANSI escape codes shift visible widths between frames.
    """
    use_color = _supports_color()
    if is_refresh and use_color:
        # Cursor home, then erase-line + content for every row, then
        # erase-to-end-of-screen to wipe any leftover rows.
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
        "watch",
        help="Show rolling consumption for the last N minutes (live refresh)",
    )
    parser.add_argument(
        "--minutes",
        type=int,
        default=30,
        metavar="N",
        help="Rolling window size in minutes (default: 30)",
    )
    parser.add_argument(
        "--refresh",
        type=int,
        default=0,
        metavar="SECS",
        help="Auto-refresh interval in seconds (0 = one-shot, default: 0)",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Compact output (skip model and tool details)",
    )
    parser.set_defaults(func=run)
    return parser


def run(args) -> None:
    minutes: int = args.minutes
    refresh: int = args.refresh
    compact: bool = args.compact
    use_color = _supports_color()

    if refresh <= 0:
        # One-shot mode -- warnings visible as normal
        data = _fetch_window(minutes, quiet=False)
        _paint(_render_to_lines(data, compact=compact))
        return

    # Live refresh mode -- suppress stderr so warnings don't corrupt display
    saved_stderr = sys.stderr
    try:
        sys.stderr = open(os.devnull, "w")  # noqa: SIM115
    except OSError:
        pass  # keep original stderr if devnull fails

    if use_color:
        sys.stdout.write("\033[?25l\033[2J\033[H")  # hide cursor + clear once
        sys.stdout.flush()
    try:
        first = True
        while True:
            data = _fetch_window(minutes, quiet=True)
            footer = dim(f"  Refreshing every {refresh}s -- Ctrl+C to stop")
            lines = _render_to_lines(data, compact=compact, footer=footer)
            _paint(lines, is_refresh=not first)
            first = False
            time.sleep(refresh)
    except KeyboardInterrupt:
        pass
    finally:
        if use_color:
            sys.stdout.write("\033[?25h")  # restore cursor
            sys.stdout.flush()
        # Restore stderr
        if sys.stderr is not saved_stderr:
            try:
                sys.stderr.close()
            except OSError:
                pass
            sys.stderr = saved_stderr
        print()
