"""NDJSON renderer — one JSON object per line from daily data."""

from __future__ import annotations

import json
from typing import Any


def render(payload: dict[str, Any]) -> str:
    lines = [json.dumps(day, ensure_ascii=False) for day in payload.get("days", [])]
    return "\n".join(lines) + "\n" if lines else ""
