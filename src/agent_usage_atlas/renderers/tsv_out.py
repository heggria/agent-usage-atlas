"""TSV renderer — flatten daily data into tab-separated rows."""

from __future__ import annotations

import csv
import io
from typing import Any

from .csv_out import _FIELDS


def render(payload: dict[str, Any]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=_FIELDS, delimiter="\t")
    writer.writeheader()
    for day in payload.get("days", []):
        writer.writerow({k: day.get(k, "") for k in _FIELDS})
    return buf.getvalue()
