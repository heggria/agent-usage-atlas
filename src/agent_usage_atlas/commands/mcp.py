"""MCP server command (placeholder)."""

from __future__ import annotations


def add_parser(subparsers):
    parser = subparsers.add_parser(
        "mcp",
        help="Start an MCP server exposing dashboard data as tools",
    )
    parser.set_defaults(func=run)
    return parser


def run(args) -> None:
    raise SystemExit(
        "MCP server mode is not yet implemented.\nUse 'agent-usage-atlas serve' for the live HTTP dashboard."
    )
