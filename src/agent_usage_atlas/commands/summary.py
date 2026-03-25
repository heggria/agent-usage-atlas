"""Quick terminal summary of agent usage metrics."""

from __future__ import annotations

from ..cli import build_dashboard_payload
from ..models import fmt_int, fmt_short, fmt_usd
from ._ansi import blue, bold, cyan, dim, green, magenta, red, yellow

# ── Subcommand registration ───────────────────────────────────────────


def add_parser(subparsers):
    parser = subparsers.add_parser(
        "summary",
        help="Show a quick terminal summary of agent usage metrics",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=False,
        help="Show additional efficiency metrics, working patterns, and cache ratio",
    )
    parser.set_defaults(func=run)
    return parser


# ── Formatting helpers ─────────────────────────────────────────────────


def _separator(width: int = 60) -> str:
    return dim("-" * width)


def _section(title: str) -> str:
    return bold(cyan(f"\n  {title}"))


def _bar(value: float, maximum: float, width: int = 20) -> str:
    """Return a filled-block bar scaled to *maximum*, up to *width* chars."""
    if maximum <= 0:
        return " " * width
    filled = max(1, round(value / maximum * width)) if value > 0 else 0
    return green("█" * filled) + dim("░" * (width - filled))


def _pct(part: float, whole: float) -> str:
    if whole <= 0:
        return "  0.0%"
    return f"{part / whole * 100:5.1f}%"


# ── Main runner ────────────────────────────────────────────────────────


def run(args) -> None:
    try:
        dashboard = build_dashboard_payload(days=args.days, since=args.since)
    except ValueError as exc:
        raise SystemExit(f"Invalid --since date format: {exc}") from exc

    rng = dashboard.get("range", {})
    totals = dashboard.get("totals", {})
    source_cards = dashboard.get("source_cards", [])
    trend_analysis = dashboard.get("trend_analysis", {})
    top_sessions = dashboard.get("top_sessions", [])
    daily_costs = dashboard.get("daily_costs", [])

    # ── Header ─────────────────────────────────────────────────────
    start = rng.get("start_local", "?")[:10]
    end = rng.get("end_local", "?")[:10]
    day_count = rng.get("day_count", 0)

    print()
    print(bold("  Agent Usage Atlas"))
    print(f"  {dim(f'{start} .. {end}')}  {dim(f'({day_count} days)')}")
    print(_separator())

    # ── Grand totals ───────────────────────────────────────────────
    print(_section("Grand Totals"))
    print(f"    Tokens     {bold(fmt_int(totals.get('grand_total', 0)))}")
    print(f"    Cost       {green(fmt_usd(totals.get('grand_cost', 0)))}")
    print(f"    Tool calls {fmt_int(totals.get('tool_call_total', 0))}")
    print(f"    Sessions   {fmt_int(totals.get('tracked_session_count', 0))}")
    print(f"    Projects   {totals.get('project_count', 0)}")

    # ── Per-source breakdown ───────────────────────────────────────
    if source_cards:
        print(_section("By Source"))
        max_cost = max((c["cost"] for c in source_cards if c.get("token_capable")), default=0)
        for card in source_cards:
            name = card["source"]
            sessions = card["sessions"]
            if card["token_capable"]:
                usage = fmt_int(card["total"])
                cost = card["cost"]
                bar = _bar(cost, max_cost)
                cost_str = green(fmt_usd(cost))
            else:
                usage = f"{fmt_int(card['messages'])} msgs"
                bar = " " * 20
                cost_str = dim("-")
            print(f"    {bold(name):.<24s} {bar} {cost_str:>12}  {dim(f'{usage} / {sessions} sessions')}")

    # ── Cost cards ─────────────────────────────────────────────────
    print(_section("Cost Breakdown"))
    cost_input = totals.get("cost_input", 0)
    cost_output = totals.get("cost_output", 0)
    cost_cache_read = totals.get("cost_cache_read", 0)
    cost_cache_write = totals.get("cost_cache_write", 0)
    cost_reasoning = totals.get("cost_reasoning", 0)
    print(f"    Input      {fmt_usd(cost_input)}")
    print(f"    Output     {fmt_usd(cost_output)}")
    print(f"    Cache Read {fmt_usd(cost_cache_read)}")
    print(f"    Cache Write{fmt_usd(cost_cache_write)}")
    print(f"    Reasoning  {fmt_usd(cost_reasoning)}")

    # ── Cache savings highlight ────────────────────────────────────
    cache_savings = totals.get("cache_savings_usd", 0)
    cache_savings_ratio = totals.get("cache_savings_ratio", 0)
    if cache_savings > 0:
        savings_pct = f"{cache_savings_ratio * 100:.1f}%" if cache_savings_ratio else ""
        suffix = f" ({savings_pct} of potential cost)" if savings_pct else ""
        print(f"    {bold(green(f'Cache saved {fmt_usd(cache_savings)}{suffix}'))}")

    # ── Today vs daily average ─────────────────────────────────────
    avg_cost_per_day = totals.get("average_cost_per_day", 0)
    if avg_cost_per_day and daily_costs:
        from datetime import date as _date
        today_str = _date.today().isoformat()
        today_entry = next((d for d in daily_costs if d.get("date", "")[:10] == today_str), None)
        if today_entry is not None:
            today_cost = today_entry.get("cost", 0)
            if avg_cost_per_day > 0:
                delta_pct = (today_cost - avg_cost_per_day) / avg_cost_per_day * 100
                sign = "+" if delta_pct >= 0 else ""
                color = red if delta_pct > 20 else (green if delta_pct < -10 else yellow)
                delta = f"{sign}{delta_pct:.0f}%"
                detail = f"({fmt_usd(today_cost)} vs {fmt_usd(avg_cost_per_day)} avg/day)"
                print(f"    Today vs avg: {color(delta)} {dim(detail)}")

    # ── Token composition ──────────────────────────────────────────
    total_tokens = 0
    tok_input = tok_cache_read = tok_cache_write = tok_output = tok_reasoning = 0
    for card in source_cards:
        if card.get("token_capable"):
            tok_input += card.get("uncached_input", 0)
            tok_cache_read += card.get("cache_read", 0)
            tok_cache_write += card.get("cache_write", 0)
            tok_output += card.get("output", 0)
            tok_reasoning += card.get("reasoning", 0)
    total_tokens = tok_input + tok_cache_read + tok_cache_write + tok_output + tok_reasoning
    if total_tokens > 0:
        print(_section("Token Composition"))
        rows = [
            ("Input (uncached)", tok_input, cyan),
            ("Cache read",       tok_cache_read, blue),
            ("Cache write",      tok_cache_write, magenta),
            ("Output",           tok_output, yellow),
            ("Reasoning",        tok_reasoning, dim),
        ]
        for label, val, color_fn in rows:
            if val == 0:
                continue
            pct = val / total_tokens * 100
            bar = _bar(val, total_tokens, width=16)
            print(f"    {label:<18s} {bar}  {color_fn(f'{pct:5.1f}%')}  {dim(fmt_short(val))}")

    # ── Session velocity ───────────────────────────────────────────
    session_count = totals.get("tracked_session_count", 0)
    median_tokens = totals.get("median_session_tokens", 0)
    day_count_v = rng.get("day_count", 0)
    if session_count and day_count_v:
        sessions_per_day = session_count / day_count_v
        print(_section("Session Velocity"))
        print(f"    {bold(f'{sessions_per_day:.1f}')} sessions/day avg  ·  "
              f"{bold(fmt_short(median_tokens))} tokens/session median")

    # ── Top 3 models by cost ───────────────────────────────────────
    model_costs = trend_analysis.get("model_costs", [])
    if model_costs:
        print(_section("Top Models by Cost"))
        for entry in model_costs[:3]:
            model = entry.get("model", "?")
            cost = entry.get("cost", 0)
            msgs = entry.get("messages", 0)
            print(f"    {yellow(model):<32s}  {green(fmt_usd(cost)):>12}  {dim(f'{fmt_int(msgs)} msgs')}")

    # ── Top 3 sessions by cost ─────────────────────────────────────
    if top_sessions:
        print(_section("Top Sessions by Cost"))
        for sess in top_sessions[:3]:
            sid = sess.get("session_id", "?")
            source = sess.get("source", "?")
            cost = sess.get("cost", 0)
            tok = sess.get("total", 0)
            short_id = sid[:12] if len(sid) > 12 else sid
            print(f"    {dim(source)}/{short_id:<14s}  {green(fmt_usd(cost)):>12}  {dim(fmt_int(tok) + ' tokens')}")

    # ── Verbose extras ─────────────────────────────────────────────
    if getattr(args, "verbose", False):
        _print_verbose(dashboard, totals)

    print()


def _print_verbose(dashboard: dict, totals: dict) -> None:
    """Print additional detail when --verbose is set."""
    efficiency = dashboard.get("efficiency_metrics", {})
    working = dashboard.get("working_patterns", {})

    # ── Efficiency metrics ─────────────────────────────────────────
    summary = efficiency.get("summary", {})
    if summary:
        print(_section("Efficiency"))
        avg_reason = summary.get("avg_reasoning_ratio") or 0
        avg_cache = summary.get("avg_cache_hit_rate") or 0
        avg_tpm = summary.get("avg_tokens_per_message") or 0
        print(f"    Avg reasoning ratio   {avg_reason:.1f}%")
        print(f"    Avg cache hit rate    {avg_cache:.1f}%")
        print(f"    Avg tokens/message    {fmt_int(int(avg_tpm))}")

    # ── Working patterns peak hour ─────────────────────────────────
    hourly = working.get("hourly_source_totals", [])
    if hourly:
        peak_hour = max(hourly, key=lambda h: sum(v for k, v in h.items() if k not in {"hour", "cost"} and v is not None))
        hour_label = f"{peak_hour['hour']:02d}:00"
        total_at_peak = sum(v for k, v in peak_hour.items() if k not in {"hour", "cost"} and v is not None)
        print(_section("Working Patterns"))
        print(f"    Peak hour  {bold(hour_label)}  {dim(fmt_int(total_at_peak) + ' tokens')}")

    # ── Cache ratio ────────────────────────────────────────────────
    cache_ratio = totals.get("cache_ratio", 0)
    print(_section("Cache"))
    print(f"    Cache ratio  {cache_ratio:.1f}%")
    savings = totals.get("cache_savings_usd", 0)
    if savings > 0:
        print(f"    Savings      {green(fmt_usd(savings))}")
