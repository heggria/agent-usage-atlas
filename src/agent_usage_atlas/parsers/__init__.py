"""Parser registry and orchestration."""

from __future__ import annotations

import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import timedelta

from ..models import ParseResult
from . import claude, codex, cursor, hermit
from ._base import all_caches_hit
from .claude import CLAUDE_HOME, CLAUDE_ROOT
from .codex import CODEX_HOME, CODEX_ROOTS
from .cursor import CURSOR_DB, CURSOR_ROOT
from .hermit import HERMIT_HOMES, HERMIT_ROOTS

# Fixed wide parse window — parsers always fetch this much data so the
# result cache remains valid when the user switches time ranges.
# The actual requested range is applied as a post-parse filter.
_PARSE_WINDOW_DAYS = 90


def parse_all(start_utc, now_utc, *, local_tz=None) -> tuple[ParseResult, dict, bool]:
    """Run all parsers concurrently and merge results.

    Returns (merged_result, claude_stats_cache, changed).
    ``changed`` is False when every parser returned cached data.

    Each parser checks its own disk cache internally, so only parsers
    whose files actually changed will re-parse.
    """
    merged = ParseResult()

    # Always parse with the widest window so caches survive range switches.
    wide_start = now_utc - timedelta(days=_PARSE_WINDOW_DAYS)
    if start_utc < wide_start:
        wide_start = start_utc  # honour ranges wider than 90 days

    # Use the original (narrow) start for mtime-based file skipping;
    # parsers still parse all matching events for the wide_start window.
    mtime_floor = start_utc

    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {
            pool.submit(codex.parse, wide_start, now_utc, mtime_floor=mtime_floor): "codex",
            pool.submit(claude.parse, wide_start, now_utc, mtime_floor=mtime_floor): "claude",
            pool.submit(cursor.parse, wide_start, now_utc, local_tz): "cursor",
            pool.submit(hermit.parse, wide_start, now_utc): "hermit",
        }
        f_stats = pool.submit(claude.parse_stats_cache)

        for future in as_completed(futures):
            name = futures[future]
            try:
                result = future.result(timeout=30)
                merged.merge(result)
            except Exception as e:
                warnings.warn(f"Parser {name} failed: {e}")

        try:
            claude_stats = f_stats.result(timeout=10)
        except Exception:
            claude_stats = {}

    changed = not all_caches_hit()
    return merged, claude_stats, changed


# Backward-compatible exports for server.py path scanning
__all__ = [
    "parse_all",
    "all_caches_hit",
    "CODEX_ROOTS",
    "CODEX_HOME",
    "CLAUDE_ROOT",
    "CLAUDE_HOME",
    "CURSOR_ROOT",
    "CURSOR_DB",
    "HERMIT_HOMES",
    "HERMIT_ROOTS",
]
