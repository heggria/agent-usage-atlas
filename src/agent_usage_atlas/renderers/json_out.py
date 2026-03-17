"""JSON renderer — serialize dashboard payload as formatted JSON."""

from __future__ import annotations

import json
from typing import Any


def render(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)
