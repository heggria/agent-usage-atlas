"""CSV renderer — flatten daily data into CSV rows."""

from __future__ import annotations

import csv
import io
from typing import Any

_FIELDS = [
    "date",
    "total_tokens",
    "uncached_input",
    "cache_read",
    "cache_write",
    "output",
    "reasoning",
    "messages",
    "cost",
    "cost_input",
    "cost_cache_read",
    "cost_cache_write",
    "cost_output",
    "cost_reasoning",
    "tool_calls",
    "cumulative_tokens",
    "cost_cumulative",
]


def render(payload: dict[str, Any]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=_FIELDS)
    writer.writeheader()
    for day in payload.get("days", []):
        writer.writerow({k: day.get(k, "") for k in _FIELDS})
    return buf.getvalue()
