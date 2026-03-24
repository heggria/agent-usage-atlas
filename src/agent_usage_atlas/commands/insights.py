"""Show behavioral insights and optimization recommendations."""

from __future__ import annotations

from ..cli import build_dashboard_payload
from ._ansi import bold, cyan, dim, red, yellow

# ── Severity ordering (highest -> lowest) ────────────────────────────

_SEVERITY_LEVELS = ("critical", "high", "medium", "low", "info")
_SEVERITY_RANK = {s: i for i, s in enumerate(_SEVERITY_LEVELS)}

# ── Severity -> display icon + color ────────────────────────────────

_SEVERITY_DISPLAY = {
    "critical": lambda: red("✗✗"),
    "high":     lambda: yellow("✗"),
    "medium":   lambda: cyan("~"),
    "low":      lambda: dim("·"),
    "info":     lambda: dim("i"),
}

_SEVERITY_LABEL = {
    "critical": red,
    "high":     yellow,
    "medium":   cyan,
    "low":      dim,
    "info":     dim,
}

_BAR_WIDTH = 10  # max number of █ chars in the impact bar


def _format_rule_name(rule: str) -> str:
    """Convert snake_case rule name to Title Case."""
    return rule.replace("_", " ").title()


def _impact_bar(score: int | float, max_score: int | float) -> str:
    """Return a visual bar proportional to score/max_score (width=_BAR_WIDTH)."""
    if max_score <= 0:
        filled = 0
    else:
        filled = round(_BAR_WIDTH * score / max_score)
    filled = max(0, min(_BAR_WIDTH, filled))
    empty = _BAR_WIDTH - filled
    return "█" * filled + "░" * empty


def _format_data_context(data: dict) -> str:
    """Format the `data` dict into a compact inline string."""
    parts: list[str] = []
    for key, val in data.items():
        label = key.replace("_", " ")
        if isinstance(val, float):
            parts.append(f"{label}: {val:.1f}")
        else:
            parts.append(f"{label}: {val}")
    return ", ".join(parts)


# ── Subcommand registration ────────────────────────────────────────


def add_parser(subparsers):
    parser = subparsers.add_parser(
        "insights",
        help="Show behavioral insights and optimization recommendations",
    )
    parser.add_argument(
        "--severity",
        choices=["critical", "high", "medium", "low", "info", "all"],
        default="all",
        help="Minimum severity to show (default: all)",
    )
    parser.add_argument(
        "--lang",
        choices=["en", "zh"],
        default="en",
        help="Language for suggestions (default: en)",
    )
    parser.set_defaults(func=run)
    return parser


# ── Command implementation ──────────────────────────────────────────


def run(args) -> None:
    try:
        dashboard = build_dashboard_payload(days=args.days, since=args.since)
    except ValueError as exc:
        raise SystemExit(f"Invalid --since date format: {exc}") from exc

    raw_insights: list[dict] = dashboard.get("insights", [])

    # Filter by minimum severity
    if args.severity != "all":
        min_rank = _SEVERITY_RANK.get(args.severity, len(_SEVERITY_LEVELS))
        raw_insights = [
            ins
            for ins in raw_insights
            if _SEVERITY_RANK.get(ins.get("severity", "info"), len(_SEVERITY_LEVELS)) <= min_rank
        ]

    if not raw_insights:
        print("No insights found for the selected criteria.")
        return

    # Count per severity
    counts: dict[str, int] = {s: 0 for s in _SEVERITY_LEVELS}
    for ins in raw_insights:
        sev = ins.get("severity", "info")
        if sev in counts:
            counts[sev] += 1

    actionable = counts["critical"] + counts["high"]
    crit_part = f"{counts['critical']} critical" if counts["critical"] else ""
    high_part = f"{counts['high']} high" if counts["high"] else ""
    action_detail = ", ".join(p for p in [crit_part, high_part] if p)

    # Bold summary header
    if actionable:
        summary = bold(f"{actionable} actionable item{'s' if actionable != 1 else ''} ({action_detail})")
    else:
        summary = bold("No actionable items")
    print(summary)
    print()

    suggestion_key = "suggestion_zh" if args.lang == "zh" else "suggestion_en"

    # Compute max impact score for relative bar scaling
    max_score: int | float = max((ins.get("impact_score", 0) for ins in raw_insights), default=1) or 1

    # Group and display by severity (critical first)
    for severity in _SEVERITY_LEVELS:
        group = [
            ins for ins in raw_insights
            if ins.get("severity", "info") == severity
        ]
        if not group:
            continue

        # Sort group by impact_score descending
        group = sorted(group, key=lambda ins: ins.get("impact_score", 0), reverse=True)

        # Section header
        label_fn = _SEVERITY_LABEL.get(severity, dim)
        header_text = f"── {severity.upper()} ({counts[severity]}) "
        print(label_fn(header_text + "─" * max(0, 50 - len(header_text))))

        for ins in group:
            icon_fn = _SEVERITY_DISPLAY.get(severity, _SEVERITY_DISPLAY["info"])
            icon = icon_fn()
            rule_name = _format_rule_name(ins.get("rule", "unknown"))
            score = ins.get("impact_score", 0)
            bar = _impact_bar(score, max_score)
            suggestion = ins.get(suggestion_key, ins.get("suggestion_en", ""))
            data: dict = ins.get("data") or {}

            # First line: icon, rule name, score bar, score value
            print(f"  {icon} {bold(rule_name)}  {dim(bar)} {dim(str(score))}")

            # Data context line (if present)
            if data:
                data_str = _format_data_context(data)
                print(f"     {dim(data_str)}")

            # Suggestion
            print(f"     {suggestion}")
            print()

        print()

    # Final tally
    parts = [f"{counts[s]} {s}" for s in _SEVERITY_LEVELS if counts[s] > 0]
    print(dim(f"{len(raw_insights)} insight{'s' if len(raw_insights) != 1 else ''} total  ·  {', '.join(parts)}"))
