"""5-hour billing window query command."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from ..cli import build_dashboard_payload
from ..models import fmt_int, fmt_usd


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


def run(args) -> None:
    local_tz = datetime.now(timezone.utc).astimezone().tzinfo
    now_local = datetime.now(local_tz)

    # Get last N * 5 hours of data
    hours = args.windows * 5
    since_local = now_local - timedelta(hours=hours)
    since_str = since_local.strftime("%Y-%m-%d")

    try:
        dashboard = build_dashboard_payload(since=since_str)
    except ValueError as exc:
        raise SystemExit(f"Invalid date: {exc}") from exc

    days = dashboard.get("days", [])
    totals = dashboard.get("totals", {})

    print(f"Billing windows (5h) — last {hours}h")
    print(f"Total: {fmt_int(totals.get('grand_total', 0))} tokens, {fmt_usd(totals.get('grand_cost', 0))}")
    print()

    # Simple window display — group daily data
    for day in days:
        cost = day.get("cost", 0)
        tokens = day.get("total_tokens", 0)
        if tokens > 0 or cost > 0:
            print(f"  {day['date']}  {fmt_int(tokens):>16} tokens  {fmt_usd(cost):>10}")
