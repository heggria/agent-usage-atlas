#!/usr/bin/env python3
"""Generate a multi-source local agent usage dashboard."""
from __future__ import annotations

import argparse
import webbrowser
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from aggregation import aggregate
from models import fmt_int, fmt_usd
from parsers import (
    parse_claude_events,
    parse_claude_session_meta,
    parse_claude_tool_calls,
    parse_codex_events,
    parse_codex_session_meta,
    parse_codex_tool_calls,
    parse_cursor_events,
)
from template import build_html


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-usage-atlas",
        description="Generate a local agent usage dashboard from Codex CLI / Claude Code / Cursor logs.",
    )
    parser.add_argument(
        "--days", type=int, default=30,
        help="Number of recent days to include (default: 30)",
    )
    parser.add_argument(
        "--since", type=str, default=None, metavar="YYYY-MM-DD",
        help="Custom start date (overrides --days)",
    )
    parser.add_argument(
        "--output", type=Path, default=None, metavar="PATH",
        help="Output HTML file path (default: ./reports/dashboard.html)",
    )
    parser.add_argument(
        "--open", action="store_true", dest="open_browser",
        help="Open the dashboard in the default browser after generation",
    )
    parser.add_argument(
        "--serve", action="store_true",
        help="Start a local web dashboard instead of generating a static file",
    )
    parser.add_argument(
        "--host", type=str, default="127.0.0.1",
        help="Serve host for --serve mode (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port", type=int, default=8765,
        help="Serve port for --serve mode (default: 8765)",
    )
    parser.add_argument(
        "--interval", type=int, default=5,
        help="Refresh interval in seconds for --serve mode (default: 5)",
    )
    return parser


def build_dashboard_payload(
    *,
    days: int = 30,
    since: str | None = None,
    now_local: datetime | None = None,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    local_tz = now_local.tzinfo if now_local and now_local.tzinfo else datetime.now(timezone.utc).astimezone().tzinfo
    now_local = now_local or datetime.now(local_tz)
    if now_local.tzinfo is None:
        now_local = now_local.replace(tzinfo=local_tz)
    now_utc = now_utc or now_local.astimezone(timezone.utc)
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)

    if since:
        start_local = datetime.strptime(since, "%Y-%m-%d").replace(tzinfo=local_tz)
    else:
        start_local = (now_local - timedelta(days=days)).replace(
            hour=0, minute=0, second=0, microsecond=0,
        )
    start_utc = start_local.astimezone(timezone.utc)

    events = (
        parse_codex_events(start_utc, now_utc)
        + parse_claude_events(start_utc, now_utc)
        + parse_cursor_events(start_utc, now_utc, local_tz)
    )
    tool_calls = parse_codex_tool_calls() + parse_claude_tool_calls()
    session_metas = parse_codex_session_meta() + parse_claude_session_meta()

    # Aggregate & render
    dashboard = aggregate(
        events, tool_calls, session_metas,
        start_local=start_local, now_local=now_local, local_tz=local_tz,
    )
    dashboard["_meta"] = {
        "generated_at": now_local.isoformat(timespec="seconds"),
        "since": since,
        "days": days,
        "local_timezone": str(local_tz),
    }
    return dashboard


def print_summary(dashboard: dict[str, Any]) -> None:
    totals = dashboard["totals"]
    print(f"Dashboard -> {dashboard['_meta']['generated_at']}")
    print(f"Tokens: {fmt_int(totals['grand_total'])}  Cost: {fmt_usd(totals['grand_cost'])}  "
          f"Tools: {fmt_int(totals['tool_call_total'])}  Projects: {totals['project_count']}")
    for card in dashboard["source_cards"]:
        label = fmt_int(card["total"]) if card["token_capable"] else f"{fmt_int(card['messages'])} msgs"
        cost = fmt_usd(card["cost"]) if card["token_capable"] else "-"
        print(f"  {card['source']}: usage={label} cost={cost} sessions={card['sessions']}")


def main() -> None:
    args = _build_parser().parse_args()

    if args.serve:
        from server import run_server

        run_server(
            host=args.host,
            port=args.port,
            days=args.days,
            since=args.since,
            interval=args.interval,
            open_browser=args.open_browser,
        )
        return

    try:
        dashboard = build_dashboard_payload(days=args.days, since=args.since)
    except ValueError as exc:
        raise SystemExit(f"Invalid --since date format: {exc}") from exc
    output_path = args.output or (Path(__file__).resolve().parent / "reports" / "dashboard.html")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_html(dashboard))

    print(f"Dashboard -> {output_path}")
    print_summary(dashboard)

    if args.open_browser:
        webbrowser.open(output_path.as_uri())


if __name__ == "__main__":
    main()
