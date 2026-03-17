"""Export dashboard data in JSON or CSV format."""

from __future__ import annotations

import sys

from ..cli import build_dashboard_payload
from ..renderers import render


def add_parser(subparsers):
    parser = subparsers.add_parser(
        "export",
        help="Export dashboard data as JSON or CSV",
    )
    parser.add_argument(
        "--format",
        choices=["json", "csv"],
        default="json",
        help="Output format (default: json)",
    )
    parser.set_defaults(func=run)
    return parser


def run(args) -> None:
    try:
        dashboard = build_dashboard_payload(days=args.days, since=args.since)
    except ValueError as exc:
        raise SystemExit(f"Invalid --since date format: {exc}") from exc

    content = render(dashboard, fmt=args.format)
    output_path = args.output

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
        print(f"{args.format.upper()} exported -> {output_path}")
    else:
        sys.stdout.write(content)
        if not content.endswith("\n"):
            sys.stdout.write("\n")
