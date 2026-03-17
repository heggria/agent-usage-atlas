"""HTML renderer — delegates to builder.py for single-file HTML generation."""

from __future__ import annotations

from typing import Any

from ..builder import build_html


def render(payload: dict[str, Any] | None = None, *, poll_interval_ms: int = 0) -> str:
    return build_html(payload, poll_interval_ms=poll_interval_ms)
