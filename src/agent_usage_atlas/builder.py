"""Build single-file HTML dashboard from frontend/ directory files."""

from __future__ import annotations

import json
from pathlib import Path

_FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"


def _read_frontend(relative_path: str) -> str:
    return (_FRONTEND_DIR / relative_path).read_text(encoding="utf-8")


def _frontend_subdir(category: str) -> Path:
    return _FRONTEND_DIR / category


def build_html(data: dict | None = None, *, poll_interval_ms: int = 0) -> str:
    """Read frontend/ files and assemble a single self-contained HTML."""
    html_skeleton = _read_frontend("index.html")
    css = _read_frontend("styles/main.css")

    # Collect all JS files in dependency order
    js_parts = []
    for category in ["lib", "components", "charts", "sections"]:
        subdir = _frontend_subdir(category)
        if subdir.is_dir():
            for f in sorted(subdir.iterdir()):
                if f.suffix == ".js":
                    js_parts.append(f.read_text(encoding="utf-8"))

    # Inject CSS and JS into skeleton
    result = html_skeleton.replace("__CSS__", css).replace("__JS__", "\n".join(js_parts))

    # Inject data payload and polling interval
    payload = "null" if data is None else json.dumps(data, ensure_ascii=False).replace("</", r"<\/")
    interval = max(1000, int(poll_interval_ms or 0))
    result = result.replace("__DATA__", payload).replace("__POLL_MS__", str(interval))

    return result
