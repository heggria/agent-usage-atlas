"""Output format renderers for dashboard data."""

from __future__ import annotations

from typing import Any


def render(payload: dict[str, Any], *, fmt: str = "html", **kwargs) -> str:
    """Render dashboard payload in the specified format.

    Args:
        payload: Dashboard data dict from build_dashboard_payload().
        fmt: Output format — "html", "json", "csv", "tsv", "ndjson",
             or "prometheus".
        **kwargs: Format-specific options (e.g. poll_interval_ms for html).

    Returns:
        Rendered string content.
    """
    if fmt == "html":
        from .html import render as render_html

        return render_html(payload, **kwargs)
    elif fmt == "json":
        from .json_out import render as render_json

        return render_json(payload)
    elif fmt == "csv":
        from .csv_out import render as render_csv

        return render_csv(payload)
    elif fmt == "tsv":
        from .tsv_out import render as render_tsv

        return render_tsv(payload)
    elif fmt == "ndjson":
        from .ndjson_out import render as render_ndjson

        return render_ndjson(payload)
    elif fmt == "prometheus":
        from .prometheus_out import render as render_prometheus

        return render_prometheus(payload)
    else:
        raise ValueError(f"Unknown format: {fmt!r}. Supported: html, json, csv, tsv, ndjson, prometheus")
