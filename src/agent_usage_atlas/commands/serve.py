"""Live dashboard server command."""

from __future__ import annotations


def add_parser(subparsers):
    parser = subparsers.add_parser(
        "serve",
        help="Start a live dashboard server with SSE updates",
    )
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Server host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8765, help="Server port (default: 8765)")
    parser.add_argument("--interval", type=int, default=5, help="Refresh interval in seconds (default: 5)")
    parser.set_defaults(func=run)
    return parser


def run(args) -> None:
    from ..server import run_server

    run_server(
        host=args.host,
        port=args.port,
        days=args.days,
        since=args.since,
        interval=args.interval,
        open_browser=args.open_browser,
    )
