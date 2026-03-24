"""Tool usage statistics command."""

from __future__ import annotations

from ..cli import build_dashboard_payload
from ..models import fmt_int
from ._ansi import _supports_color, bold, cyan, dim, green, red, yellow

# ── Subcommand registration ──────────────────────────────────────────


def add_parser(subparsers):
    parser = subparsers.add_parser(
        "tools",
        help="Show tool usage statistics",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=20,
        help="Number of tools to show (default: 20)",
    )
    parser.add_argument(
        "--bigrams",
        action="store_true",
        help="Show tool transition bigrams",
    )
    parser.add_argument(
        "--commands",
        action="store_true",
        help="Show command stats with failure rates",
    )
    parser.set_defaults(func=run)
    return parser


# ── Formatters / helpers ──────────────────────────────────────────────

_BAR_WIDTH = 20
_SOURCE_LABELS: dict[str, tuple[str, str]] = {
    # source-key → (display letter, ANSI color code)
    "Claude": ("C", "36"),   # cyan
    "Codex":  ("X", "32"),   # green
    "Hermit": ("H", "33"),   # yellow
    "Cursor": ("U", "35"),   # magenta
}


def _pct(value: float) -> str:
    """Format a percentage with one decimal place."""
    return f"{value:.1f}%"


def _bar(count: int, max_count: int) -> str:
    """Inline block bar scaled to _BAR_WIDTH relative to max_count."""
    if max_count <= 0:
        return " " * _BAR_WIDTH
    filled = round(_BAR_WIDTH * count / max_count)
    return "█" * filled + " " * (_BAR_WIDTH - filled)


def _source_badges(by_source: dict[str, int]) -> str:
    """Colored single-letter badges for each source that has calls."""
    if not _supports_color():
        return " ".join(
            letter
            for key, (letter, _code) in _SOURCE_LABELS.items()
            if by_source.get(key, 0) > 0
        )
    parts = []
    for key, (letter, code) in _SOURCE_LABELS.items():
        if by_source.get(key, 0) > 0:
            parts.append(f"\033[{code}m{letter}\033[0m")
    return " ".join(parts)


# ── Run ───────────────────────────────────────────────────────────────


def run(args) -> None:
    try:
        dashboard = build_dashboard_payload(days=args.days, since=args.since)
    except ValueError as exc:
        raise SystemExit(f"Invalid --since date format: {exc}") from exc

    tooling = dashboard.get("tooling", {})
    ranking = tooling.get("ranking", [])
    total_tool_calls = tooling.get("total_tool_calls", 0)
    tool_bigrams = tooling.get("tool_bigrams", [])

    commands_data = dashboard.get("commands", {})
    summary = commands_data.get("summary", {})
    top_commands = commands_data.get("top_commands", [])

    # ── Tool ranking table ────────────────────────────────────────
    top_n = min(args.top, len(ranking))
    display_ranking = ranking[:top_n]

    if not display_ranking:
        print("No tool usage data found.")
        return

    # Determine column widths
    name_width = max(len(t["name"]) for t in display_ranking)
    name_width = max(name_width, len("Tool Name"))
    rank_width = len(str(top_n))
    rank_width = max(rank_width, 1)
    max_count = display_ranking[0]["count"] if display_ranking else 1

    # ANSI escape overhead for alignment calculations
    _ansi_pad = len("\033[36m") + len("\033[0m") if _supports_color() else 0

    print()
    print(bold(f"Tool Ranking (top {top_n} of {fmt_int(len(ranking))})"))
    print()

    header_line = (
        f"{'#':>{rank_width}} | {'Tool Name':<{name_width}} | "
        f"{'Count':>8} | {'% of Total':>10} | {'Usage':^{_BAR_WIDTH}} | Src"
    )
    print(dim(header_line))
    print(dim("-" * len(header_line)))

    for i, tool in enumerate(display_ranking, 1):
        name = tool["name"]
        count = tool["count"]
        pct = (count / total_tool_calls * 100) if total_tool_calls else 0.0
        bar = _bar(count, max_count)
        by_source = tool.get("by_source", {})
        badges = _source_badges(by_source)
        print(
            f"{i:>{rank_width}} | {name:<{name_width}} | "
            f"{cyan(fmt_int(count)):>{8 + _ansi_pad}} | {_pct(pct):>10} | "
            f"{bar} | {badges}"
        )

    print()
    print(f"Total tool calls: {bold(fmt_int(total_tool_calls))}")

    # ── Diversity metrics ─────────────────────────────────────────
    if ranking and total_tool_calls:
        distinct = len(ranking)
        diversity = distinct / total_tool_calls
        top3_pct = sum(t["count"] for t in ranking[:3]) / total_tool_calls * 100
        top3_names = ", ".join(t["name"] for t in ranking[:3])
        print(
            f"Diversity score:  {bold(f'{diversity:.4f}')}"
            f"  ({fmt_int(distinct)} distinct tools / {fmt_int(total_tool_calls)} calls)"
        )
        print(f"Top-3 coverage:   {bold(_pct(top3_pct))}  ({dim(top3_names)})")

    # ── Bigrams ───────────────────────────────────────────────────
    if args.bigrams:
        _print_bigrams(tool_bigrams, args.top)

    # ── Commands ──────────────────────────────────────────────────
    if args.commands:
        _print_commands(top_commands, summary, args.top)


def _print_bigrams(bigrams: list[dict], top_n: int) -> None:
    display = bigrams[:top_n]

    if not display:
        print()
        print(dim("No bigram data available."))
        return

    from_width = max(len(b["from"]) for b in display)
    to_width = max(len(b["to"]) for b in display)
    max_count = display[0]["count"] if display else 1

    # Arrow shaft width: 3–12 chars, proportional to count
    _ARROW_MAX = 12

    print()
    print(bold(f"Tool Transitions (top {len(display)})"))
    print()

    for bigram in display:
        src = bigram["from"]
        tgt = bigram["to"]
        count = bigram["count"]
        shaft_len = max(3, round(_ARROW_MAX * count / max_count))
        shaft = "═" * shaft_len
        arrow = f"{src:<{from_width}} {shaft}> {tgt:<{to_width}}"
        print(f"  {cyan(arrow)}  {bold(fmt_int(count))}")


def _print_commands(top_commands: list[dict], summary: dict, top_n: int) -> None:
    display = top_commands[:top_n]

    if not display:
        print()
        print(dim("No command data available."))
        return

    cmd_width = max(len(c["command"]) for c in display)
    cmd_width = max(cmd_width, len("Command"))
    rank_width = len(str(len(display)))
    rank_width = max(rank_width, 1)

    # ANSI escape overhead for alignment calculations
    _ansi_pad = len("\033[31m") + len("\033[0m") if _supports_color() else 0

    print()
    print(bold("Commands"))
    print()

    header_line = f"{'#':>{rank_width}} | {'Command':<{cmd_width}} | {'Count':>8} | {'Failures':>8} | {'Fail Rate':>9}"
    print(dim(header_line))
    print(dim("-" * len(header_line)))

    for i, cmd in enumerate(display, 1):
        fail_rate = cmd["failure_rate"]
        # Color failure rate: green if low, yellow if moderate, red if high
        if fail_rate >= 10:
            rate_color_fn = red
        elif fail_rate >= 5:
            rate_color_fn = yellow
        else:
            rate_color_fn = green

        rate_str = rate_color_fn(_pct(fail_rate))

        print(
            f"{i:>{rank_width}} | "
            f"{cmd['command']:<{cmd_width}} | "
            f"{fmt_int(cmd['count']):>8} | "
            f"{fmt_int(cmd['failures']):>8} | "
            f"{rate_str:>{9 + _ansi_pad}}"
        )

    total = summary.get("total_commands", 0)
    success_rate = summary.get("success_rate", 0.0)
    successful = round(total * success_rate / 100) if total else 0

    print()
    print(f"Success rate: {green(_pct(success_rate))} ({fmt_int(successful)} of {fmt_int(total)} commands)")
