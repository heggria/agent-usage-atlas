"""Project-level usage statistics command."""

from __future__ import annotations

from ..cli import build_dashboard_payload
from ..models import fmt_int, fmt_short, fmt_usd
from ._ansi import bold, cyan, dim, green, magenta, yellow


def add_parser(subparsers):
    parser = subparsers.add_parser(
        "projects",
        help="Show project-level usage statistics",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=15,
        help="Number of projects to show (default: 15)",
    )
    parser.add_argument(
        "--branches",
        action="store_true",
        help="Show active branches",
    )
    parser.add_argument(
        "--files",
        action="store_true",
        help="Show file type distribution",
    )
    parser.set_defaults(func=run)
    return parser


_BAR_WIDTH = 15


def _bar(value: float, max_value: float, width: int = _BAR_WIDTH) -> str:
    """Return a block bar proportional to value/max_value, padded to width."""
    if max_value <= 0:
        return " " * width
    filled = round((value / max_value) * width)
    filled = max(0, min(filled, width))
    return "\u2588" * filled + " " * (width - filled)


def _rank_color(rank: int, text: str) -> str:
    """Apply rank-based coloring: rank 1 bold green, 2-3 yellow, 11+ dim."""
    if rank == 1:
        return bold(green(text))
    if rank <= 3:
        return yellow(text)
    if rank > 10:
        return dim(text)
    return text


def _print_ranking(ranking: list[dict], top: int) -> None:
    rows = ranking[:top]
    if not rows:
        print(f"  {dim('(no project data)')}")
        return

    max_cost = max((r["cost"] for r in rows), default=0.0)

    # Compute column widths from data
    max_proj = max(len(r["project"]) for r in rows)
    col_proj = max(max_proj, 7)  # "Project" header length

    bar_hdr = f"{'Cost Bar':<{_BAR_WIDTH}}"
    hdr_left = f"{'#':>3} | {'Project':<{col_proj}} | {'Sessions':>8} | {'Tok/Sess':>10} | "
    hdr_right = f"{'Tokens':>10} | {'Cost':>9} | {bar_hdr} | {'Tools':>7}"
    header = f"  {bold(hdr_left + hdr_right)}"
    sep = (
        f"  {'---':>3}-+-{'-' * col_proj}-+-{'--------':>8}-+-{'----------':>10}-+-"
        f"{'-' * 10}-+-{'-' * 9}-+-{'-' * _BAR_WIDTH}-+-{'-' * 7}"
    )

    print(header)
    print(sep)

    for i, row in enumerate(rows, 1):
        proj = row["project"]
        sessions_raw = row["sessions"]
        tokens_raw = row["total_tokens"]
        cost_raw = row["cost"]
        tools_raw = row["tool_calls"]

        tok_per_sess = tokens_raw // max(sessions_raw, 1)

        sessions = fmt_int(sessions_raw)
        tokens = fmt_short(tokens_raw)
        cost = fmt_usd(cost_raw)
        tools = fmt_int(tools_raw)
        tok_sess = fmt_short(tok_per_sess)
        bar = _bar(cost_raw, max_cost)

        num = cyan(f"{i:>3}")
        # Color the bar: green for #1, yellow for 2-3, dim for 11+
        colored_bar = _rank_color(i, bar)
        proj_colored = _rank_color(i, f"{proj:<{col_proj}}")
        print(
            f"  {num} | {proj_colored} | {sessions:>8} | {tok_sess:>10} | "
            f"{tokens:>10} | {cost:>9} | {colored_bar} | {tools:>7}"
        )


def _print_branches(branch_activity: list[dict]) -> None:
    if not branch_activity:
        print(f"  {dim('(no branch data)')}")
        return

    max_branch = max(len(b["branch"]) for b in branch_activity)
    col_branch = max(max_branch, 6)
    max_sessions = max((b["sessions"] for b in branch_activity), default=0)

    hdr_inner = f"{'Branch':<{col_branch}}  {'Sessions':>8}  {'Activity':<{_BAR_WIDTH}}"
    hdr = f"  {bold(hdr_inner)}"
    sep = f"  {'-' * col_branch}  {'--------':>8}  {'-' * _BAR_WIDTH}"
    print(hdr)
    print(sep)

    for item in branch_activity:
        branch = item["branch"]
        sessions_raw = item["sessions"]
        sessions = fmt_int(sessions_raw)
        bar = _bar(sessions_raw, max_sessions)
        colored_bar = green(bar)
        print(f"  {green(f'{branch:<{col_branch}}')}  {sessions:>8}  {colored_bar}")


def _print_file_types(file_types: list[dict]) -> None:
    if not file_types:
        print(f"  {dim('(no file type data)')}")
        return

    max_ext = max(len(f["extension"]) for f in file_types)
    col_ext = max(max_ext, 4)
    total_count = sum(f["count"] for f in file_types) or 1
    max_count = max(f["count"] for f in file_types)

    hdr_inner = f"{'Ext':<{col_ext}}  {'Count':>8}  {'Pct':>6}  {'Distribution':<{_BAR_WIDTH}}"
    hdr = f"  {bold(hdr_inner)}"
    sep = f"  {'-' * col_ext}  {'--------':>8}  {'------':>6}  {'-' * _BAR_WIDTH}"
    print(hdr)
    print(sep)

    for item in file_types:
        ext = item["extension"]
        count_raw = item["count"]
        count = fmt_int(count_raw)
        pct = count_raw / total_count * 100
        bar = _bar(count_raw, max_count)
        colored_bar = magenta(bar)
        print(f"  {yellow(f'{ext:<{col_ext}}')}  {count:>8}  {pct:>5.1f}%  {colored_bar}")


def _print_summary_footer(ranking: list[dict], count: int, top: int) -> None:
    """Print totals footer: total projects, avg cost/project, total sessions."""
    all_cost = sum(r["cost"] for r in ranking)
    all_sessions = sum(r["sessions"] for r in ranking)
    avg_cost = all_cost / max(len(ranking), 1)

    shown = min(len(ranking), top)
    footer_parts = [
        bold(f"{count}") + dim(" projects tracked"),
        bold(fmt_usd(avg_cost)) + dim(" avg cost/project"),
        bold(fmt_int(all_sessions)) + dim(" sessions total"),
    ]
    print(f"  {dim('─' * 60)}")
    print(f"  {' · '.join(footer_parts)}")
    if shown < len(ranking):
        print(f"  {dim(f'(showing top {shown} of {len(ranking)} projects in period)')}")


def run(args) -> None:
    try:
        dashboard = build_dashboard_payload(days=args.days, since=args.since)
    except ValueError as exc:
        raise SystemExit(f"Invalid --since date format: {exc}") from exc

    projects = dashboard.get("projects", {})
    ranking = projects.get("ranking", [])
    branch_activity = projects.get("branch_activity", [])
    file_types = projects.get("file_types", [])
    count = projects.get("count", 0)

    print(f"\n{bold('Project Rankings')}")
    print()
    _print_ranking(ranking, args.top)
    print()
    _print_summary_footer(ranking, count, args.top)

    if args.branches:
        print(f"\n{bold('Active Branches (top 20)')}")
        print()
        _print_branches(branch_activity)

    if args.files:
        print(f"\n{bold('File Types')}")
        print()
        _print_file_types(file_types)

    print()
