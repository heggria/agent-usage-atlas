"""Shared utilities for all parsers."""

from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path

_FILE_CACHE_LOCK = threading.Lock()
_JSONL_CACHE: dict[str, tuple[tuple[int, int], list[dict]]] = {}


def _file_signature(path: Path) -> tuple[int, int]:
    st = path.stat()
    return st.st_size, int(st.st_mtime_ns)


def _read_json_lines(path: Path) -> list[dict]:
    key = str(path)
    try:
        signature = _file_signature(path)
    except OSError:
        with _FILE_CACHE_LOCK:
            _JSONL_CACHE.pop(key, None)
        return []

    cached = None
    with _FILE_CACHE_LOCK:
        cached = _JSONL_CACHE.get(key)
    if cached is not None and cached[0] == signature:
        return cached[1]

    rows: list[dict] = []
    try:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            for raw in fh:
                try:
                    obj = json.loads(raw)
                except Exception:
                    continue
                if isinstance(obj, dict):
                    rows.append(obj)
    except Exception:
        rows = []

    with _FILE_CACHE_LOCK:
        _JSONL_CACHE[key] = (signature, rows)

    return rows


def _ts(raw):
    return datetime.fromisoformat(str(raw).replace("Z", "+00:00")) if raw else None


def _si(v):
    return int(v or 0)
