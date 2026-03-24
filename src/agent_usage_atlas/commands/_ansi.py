"""Shared ANSI terminal color helpers."""

from __future__ import annotations

import os
import sys


def _supports_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def _c(code: str, text: str) -> str:
    if _supports_color():
        return f"\033[{code}m{text}\033[0m"
    return str(text)


def bold(t: object) -> str:
    return _c("1", str(t))


def dim(t: object) -> str:
    return _c("2", str(t))


def red(t: object) -> str:
    return _c("31", str(t))


def green(t: object) -> str:
    return _c("32", str(t))


def yellow(t: object) -> str:
    return _c("33", str(t))


def blue(t: object) -> str:
    return _c("34", str(t))


def magenta(t: object) -> str:
    return _c("35", str(t))


def cyan(t: object) -> str:
    return _c("36", str(t))


# ---------------------------------------------------------------------------
# Sparkline / bar helpers
# ---------------------------------------------------------------------------

_SPARK_CHARS = " ▁▂▃▄▅▆▇█"


def sparkline(values: list[float]) -> str:
    """Return a sparkline string built from Unicode block characters.

    Empty list → empty string.  All-equal values → flat line of spaces.
    """
    if not values:
        return ""
    lo, hi = min(values), max(values)
    span = hi - lo
    result: list[str] = []
    for v in values:
        if span == 0:
            idx = 0
        else:
            # Scale to [0, len-1] and clamp.
            idx = int((v - lo) / span * (len(_SPARK_CHARS) - 1))
            idx = max(0, min(idx, len(_SPARK_CHARS) - 1))
        result.append(_SPARK_CHARS[idx])
    return "".join(result)


def bar(value: float, max_value: float, width: int = 20) -> str:
    """Return a horizontal bar of '█' chars scaled to *width* columns.

    Handles edge cases: zero/negative values and zero max_value all return an
    empty bar.
    """
    if max_value <= 0 or value <= 0 or width <= 0:
        return ""
    filled = int(min(value / max_value, 1.0) * width)
    return "█" * filled


def colored_sparkline(values: list[float]) -> str:
    """Like *sparkline* but colorises each character by its relative position.

    * Top 25 % of the value range  → red
    * Middle 50 % of the range     → yellow
    * Bottom 25 % of the range     → green
    """
    if not values:
        return ""
    lo, hi = min(values), max(values)
    span = hi - lo
    parts: list[str] = []
    for v in values:
        if span == 0:
            char = _SPARK_CHARS[0]
            parts.append(green(char))
        else:
            idx = int((v - lo) / span * (len(_SPARK_CHARS) - 1))
            idx = max(0, min(idx, len(_SPARK_CHARS) - 1))
            char = _SPARK_CHARS[idx]
            ratio = (v - lo) / span  # 0.0 … 1.0
            if ratio >= 0.75:
                parts.append(red(char))
            elif ratio >= 0.25:
                parts.append(yellow(char))
            else:
                parts.append(green(char))
    return "".join(parts)
