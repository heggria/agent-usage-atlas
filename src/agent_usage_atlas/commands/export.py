"""Export dashboard data in JSON, CSV, TSV, NDJSON, or Prometheus format."""

from __future__ import annotations

import sys

from ..cli import build_dashboard_payload
from ..renderers import render


def add_parser(subparsers):
    parser = subparsers.add_parser(
        "export",
        help="Export dashboard data as JSON, CSV, TSV, NDJSON, or Prometheus",
    )
    parser.add_argument(
        "--format",
        choices=["json", "csv", "tsv", "ndjson", "prometheus"],
        default="json",
        help="Output format (default: json)",
    )
    parser.set_defaults(func=run)
    return parser


def run(args) -> None:
    dashboard = build_dashboard_payload(days=args.days, since=args.since)

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
