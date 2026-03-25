"""MCP server command — stdio JSON-RPC server exposing dashboard data as tools."""

from __future__ import annotations

import json
import sys
import traceback

from .. import __version__


def add_parser(subparsers):
    parser = subparsers.add_parser(
        "mcp",
        help="Start an MCP server exposing dashboard data as tools",
    )
    parser.set_defaults(func=run)
    return parser


# ── MCP Protocol Constants ──

_SERVER_INFO = {
    "name": "agent-usage-atlas",
    "version": __version__,
}

_TOOLS = [
    {
        "name": "get_daily_stats",
        "description": "Get daily token and cost statistics for recent days.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Number of days to include (default: 7)",
                    "default": 7,
                },
            },
        },
    },
    {
        "name": "get_cost_summary",
        "description": "Get total cost breakdown by source and model.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Number of days to include (default: 30)",
                    "default": 30,
                },
            },
        },
    },
    {
        "name": "get_session_stats",
        "description": "Get top sessions ranked by cost.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Number of days to include (default: 30)",
                    "default": 30,
                },
                "top_n": {
                    "type": "integer",
                    "description": "Number of top sessions to return (default: 10)",
                    "default": 10,
                },
            },
        },
    },
    {
        "name": "get_model_usage",
        "description": "Get token and cost breakdown by model.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Number of days to include (default: 30)",
                    "default": 30,
                },
            },
        },
    },
]


def _get_payload(days: int) -> dict:
    from ..cli import build_dashboard_payload

    return build_dashboard_payload(days=days)


def _safe_days(args: dict, default: int = 7) -> int:
    """Validate and clamp 'days' parameter to [1, 365]."""
    try:
        return max(1, min(365, int(args.get("days", default))))
    except (TypeError, ValueError):
        return default


def _safe_top_n(args: dict, default: int = 10) -> int:
    """Validate and clamp 'top_n' parameter to [1, 100]."""
    try:
        return max(1, min(100, int(args.get("top_n", default))))
    except (TypeError, ValueError):
        return default


def _handle_daily_stats(args: dict) -> str:
    days = _safe_days(args, 7)
    payload = _get_payload(days)
    daily = payload.get("days", [])
    lines = [f"Daily stats for the last {days} days:", ""]
    for d in daily[-days:]:
        tokens = f"{d.get('total_tokens', 0):,}"
        cost = f"${d.get('cost', 0):.4f}"
        lines.append(f"  {d.get('date', '?')}: {tokens} tokens, {cost}")
    totals = payload.get("totals", {})
    lines.append("")
    lines.append(f"Grand total: {totals.get('grand_total', 0):,} tokens, ${totals.get('grand_cost', 0):.2f}")
    return "\n".join(lines)


def _handle_cost_summary(args: dict) -> str:
    days = _safe_days(args, 30)
    payload = _get_payload(days)
    lines = [f"Cost summary for the last {days} days:", ""]

    # By source
    lines.append("By Source:")
    for card in payload.get("source_cards", []):
        cost = f"${card.get('cost', 0):.2f}" if card.get("token_capable") else "-"
        lines.append(f"  {card.get('source', '?')}: {cost} ({card.get('sessions', 0)} sessions)")

    # By model (top 10) — model_costs lives under trend_analysis, not totals
    totals = payload.get("totals", {})
    model_costs = payload.get("trend_analysis", {}).get("model_costs", [])
    if model_costs:
        lines.append("")
        lines.append("By Model (top 10):")
        for mc in model_costs[:10]:
            lines.append(f"  {mc.get('model', '?')}: ${mc.get('cost', 0):.4f}")

    lines.append("")
    lines.append(f"Grand total: ${totals.get('grand_cost', 0):.2f}")
    return "\n".join(lines)


def _handle_session_stats(args: dict) -> str:
    days = _safe_days(args, 30)
    top_n = _safe_top_n(args, 10)
    payload = _get_payload(days)
    sessions = payload.get("top_sessions", [])[:top_n]
    lines = [f"Top {top_n} sessions by cost (last {days} days):", ""]
    for i, s in enumerate(sessions, 1):
        sid = (s.get("session_id") or "?")[:12]
        lines.append(
            f"  {i}. [{s.get('source', '?')}] {sid}  "
            f"tokens={s.get('total', 0):,}  cost=${s.get('cost', 0):.4f}  "
            f"tools={s.get('tool_calls', 0)}  model={s.get('top_model', '?')}"
        )
    return "\n".join(lines)


def _handle_model_usage(args: dict) -> str:
    days = _safe_days(args, 30)
    payload = _get_payload(days)
    totals = payload.get("totals", {})
    model_costs = payload.get("trend_analysis", {}).get("model_costs", [])
    lines = [f"Model usage for the last {days} days:", ""]
    for mc in model_costs:
        lines.append(f"  {mc.get('model', '?')}: ${mc.get('cost', 0):.4f}  ({mc.get('messages', 0)} messages)")
    lines.append("")
    lines.append(f"Grand total: ${totals.get('grand_cost', 0):.2f}")
    return "\n".join(lines)


_TOOL_HANDLERS = {
    "get_daily_stats": _handle_daily_stats,
    "get_cost_summary": _handle_cost_summary,
    "get_session_stats": _handle_session_stats,
    "get_model_usage": _handle_model_usage,
}


def _send(obj: dict) -> None:
    """Write a JSON-RPC message to stdout."""
    line = json.dumps(obj)
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def _make_response(req_id, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _make_error(req_id, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def run(args) -> None:
    """Run the MCP stdio server."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue

        method = req.get("method", "")
        req_id = req.get("id")
        params = req.get("params") or {}

        # Notifications (no id) — just acknowledge
        if req_id is None:
            continue

        if method == "initialize":
            _send(
                _make_response(
                    req_id,
                    {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {},
                        },
                        "serverInfo": _SERVER_INFO,
                    },
                )
            )

        elif method == "tools/list":
            _send(_make_response(req_id, {"tools": _TOOLS}))

        elif method == "tools/call":
            tool_name = params.get("name", "")
            tool_args = params.get("arguments", {})
            handler = _TOOL_HANDLERS.get(tool_name)
            if handler is None:
                _send(_make_error(req_id, -32601, f"Unknown tool: {tool_name}"))
            else:
                try:
                    text = handler(tool_args)
                    _send(
                        _make_response(
                            req_id,
                            {
                                "content": [{"type": "text", "text": text}],
                            },
                        )
                    )
                except Exception:
                    traceback.print_exc(file=sys.stderr)
                    _send(_make_error(req_id, -32603, "Internal error processing request"))

        elif method == "ping":
            _send(_make_response(req_id, {}))

        else:
            _send(_make_error(req_id, -32601, f"Method not found: {method}"))
