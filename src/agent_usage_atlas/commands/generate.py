"""Static HTML dashboard generation command."""

from __future__ import annotations

import webbrowser
from pathlib import Path

from ..cli import build_dashboard_payload, print_summary
from ..renderers import render


def add_parser(subparsers):
    parser = subparsers.add_parser(
        "generate",
        help="Generate a static HTML dashboard (default command)",
    )
    parser.set_defaults(func=run)
    return parser


def run(args) -> None:
    try:
        dashboard = build_dashboard_payload(days=args.days, since=args.since)
    except ValueError as exc:
        raise SystemExit(f"Invalid --since date format: {exc}") from exc
    output_path = args.output or (Path.cwd() / "reports" / "dashboard.html")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render(dashboard, fmt="html"), encoding="utf-8")

    print(f"Dashboard -> {output_path}")
    print_summary(dashboard)

    if args.open_browser:
        webbrowser.open(output_path.resolve().as_uri())
