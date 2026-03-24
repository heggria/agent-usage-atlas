"""Benchmark result storage, history, versioning, and machine fingerprinting.

Provides NDJSON-based append-only storage for benchmark results, machine
fingerprinting for result grouping, source-code versioning via content
hashing, and formatted history display with trend analysis.

Storage location defaults to ``~/.cache/agent-usage-atlas/benchmarks/``
and can be overridden via the ``ATLAS_BENCHMARK_DIR`` environment variable.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# ── Storage location ─────────────────────────────────────────────────

STORE_DIR = Path(
    os.environ.get(
        "ATLAS_BENCHMARK_DIR",
        Path.home() / ".cache" / "agent-usage-atlas" / "benchmarks",
    )
)

_RESULTS_FILE = "results.jsonl"

# ── Package root (used by compute_version_hash) ─────────────────────

_PKG_DIR = Path(__file__).resolve().parent


# ── Data classes ─────────────────────────────────────────────────────


@dataclass
class MachineInfo:
    """Machine fingerprint for result grouping."""

    node: str
    platform: str
    python_version: str
    cpu_count: int
    arch: str

    @classmethod
    def capture(cls) -> MachineInfo:
        """Capture current machine info."""
        return cls(
            node=platform.node(),
            platform=platform.platform(),
            python_version=platform.python_version(),
            cpu_count=os.cpu_count() or 1,
            arch=platform.machine(),
        )

    def fingerprint(self) -> str:
        """Short hash of machine identity for grouping.

        Uses node, platform string, cpu_count, and architecture to produce
        a stable 8-character hex digest.
        """
        identity = f"{self.node}:{self.platform}:{self.cpu_count}:{self.arch}"
        return hashlib.sha256(identity.encode()).hexdigest()[:8]


@dataclass
class BenchmarkRecord:
    """A single benchmark run result."""

    timestamp: str  # ISO 8601
    version_hash: str  # hash of benchmark source code
    machine: MachineInfo
    days: int  # data range
    rounds: int  # number of warm rounds
    cold_ms: float
    warm_median_ms: float
    warm_min_ms: float
    warm_max_ms: float
    warm_samples: list[float] = field(default_factory=list)  # all warm round times
    phase_medians: dict[str, float] = field(default_factory=dict)  # parse_ms, aggregate_ms, render_ms
    dataset: dict[str, int] = field(default_factory=dict)  # events, tool_calls, sessions, etc.
    stats: dict[str, float] = field(default_factory=dict)  # ci_lower, ci_upper, mad, p90, p99, etc.
    regression: dict[str, Any] | None = None  # comparison with baseline if available


# ── Version hashing ──────────────────────────────────────────────────

# Relative paths (from the package root) whose contents define the
# benchmark pipeline version.  If a file is missing it is silently
# skipped so that the hash still works during early development.
_VERSION_SOURCES: tuple[str, ...] = (
    "commands/benchmark.py",
    "parsers/__init__.py",
    "aggregation/__init__.py",
    "renderers/__init__.py",
    "builder.py",
)


def compute_version_hash() -> str:
    """Hash the benchmark pipeline source code for versioning.

    Reads the content of the files listed in ``_VERSION_SOURCES``,
    concatenates them in order, and returns the first 12 hex characters
    of the SHA-256 digest.  Missing files are silently skipped.
    """
    h = hashlib.sha256()
    for rel in _VERSION_SOURCES:
        src = _PKG_DIR / rel
        try:
            h.update(src.read_bytes())
        except OSError:
            # File may not exist yet (e.g. benchmark.py during early dev).
            continue
    return h.hexdigest()[:12]


# ── Serialization helpers ────────────────────────────────────────────


def _record_to_dict(record: BenchmarkRecord) -> dict[str, Any]:
    """Convert a ``BenchmarkRecord`` to a plain dict for JSON output."""
    return asdict(record)


def _dict_to_record(raw: dict[str, Any]) -> BenchmarkRecord:
    """Reconstruct a ``BenchmarkRecord`` from a parsed JSON dict.

    Handles the nested ``MachineInfo`` dataclass manually.
    """
    machine_data = raw.pop("machine", {})
    machine = MachineInfo(
        node=machine_data.get("node", ""),
        platform=machine_data.get("platform", ""),
        python_version=machine_data.get("python_version", ""),
        cpu_count=int(machine_data.get("cpu_count", 1)),
        arch=machine_data.get("arch", ""),
    )
    return BenchmarkRecord(
        timestamp=raw.get("timestamp", ""),
        version_hash=raw.get("version_hash", ""),
        machine=machine,
        days=int(raw.get("days", 0)),
        rounds=int(raw.get("rounds", 0)),
        cold_ms=float(raw.get("cold_ms", 0.0)),
        warm_median_ms=float(raw.get("warm_median_ms", 0.0)),
        warm_min_ms=float(raw.get("warm_min_ms", 0.0)),
        warm_max_ms=float(raw.get("warm_max_ms", 0.0)),
        warm_samples=list(raw.get("warm_samples", [])),
        phase_medians=dict(raw.get("phase_medians", {})),
        dataset={k: int(v) for k, v in raw.get("dataset", {}).items()},
        stats={k: v if isinstance(v, list) else float(v) for k, v in raw.get("stats", {}).items()},
        regression=raw.get("regression"),
    )


# ── Storage operations ───────────────────────────────────────────────


def _ensure_store_dir() -> Path:
    """Create the store directory if it does not exist.  Returns the path."""
    try:
        STORE_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"[benchmark_store] warning: cannot create {STORE_DIR}: {exc}", file=sys.stderr)
    return STORE_DIR


def _results_path() -> Path:
    """Return the path to the NDJSON results file."""
    return _ensure_store_dir() / _RESULTS_FILE


def save_record(record: BenchmarkRecord) -> Path:
    """Save a benchmark record to the store.

    Appends one JSON object as a single line to
    ``STORE_DIR / "results.jsonl"``.  Creates the store directory if
    needed.  Returns the path written to.
    """
    path = _results_path()
    line = json.dumps(_record_to_dict(record), default=str, ensure_ascii=False)
    try:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError as exc:
        print(f"[benchmark_store] warning: cannot write to {path}: {exc}", file=sys.stderr)
    return path


def load_history(
    version_hash: str | None = None,
    machine_fingerprint: str | None = None,
    limit: int = 50,
) -> list[BenchmarkRecord]:
    """Load benchmark history, optionally filtered.

    Returns the most recent records first (up to *limit*).
    Corrupted lines are skipped with a warning to stderr.
    """
    path = _results_path()
    if not path.exists():
        return []

    records: list[BenchmarkRecord] = []
    try:
        with open(path, encoding="utf-8") as fh:
            lines = fh.readlines()
    except OSError as exc:
        print(f"[benchmark_store] warning: cannot read {path}: {exc}", file=sys.stderr)
        return []

    # Walk lines in reverse (most recent last in file → first in output).
    for lineno, raw_line in enumerate(reversed(lines), start=1):
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        try:
            data = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            print(
                f"[benchmark_store] warning: skipping corrupted line {len(lines) - lineno + 1}: {exc}",
                file=sys.stderr,
            )
            continue

        rec = _dict_to_record(data)

        # Apply filters.
        if version_hash is not None and rec.version_hash != version_hash:
            continue
        if machine_fingerprint is not None and rec.machine.fingerprint() != machine_fingerprint:
            continue

        records.append(rec)
        if len(records) >= limit:
            break

    return records


def get_baseline(
    version_hash: str,
    machine_fingerprint: str,
) -> BenchmarkRecord | None:
    """Get the most recent matching record as baseline for comparison.

    Matches on both *version_hash* and *machine_fingerprint*.
    Returns ``None`` if no history exists.
    """
    matches = load_history(
        version_hash=version_hash,
        machine_fingerprint=machine_fingerprint,
        limit=1,
    )
    return matches[0] if matches else None


# ── Formatted output ─────────────────────────────────────────────────


def _is_tty() -> bool:
    """Return True if stdout is connected to a terminal."""
    try:
        return sys.stdout.isatty()
    except Exception:
        return False


def _ansi(code: str, text: str) -> str:
    """Wrap *text* in ANSI escape if stdout is a tty."""
    if _is_tty():
        return f"\033[{code}m{text}\033[0m"
    return text


def _trend_arrow(current: float, previous: float) -> str:
    """Return a trend indicator comparing current to previous.

    Returns an arrow character with optional ANSI color:
    - faster (improvement of >2%):  green down arrow
    - slower (regression of >2%):   red up arrow
    - unchanged (within 2%):        yellow right arrow
    """
    if previous <= 0:
        return " "
    pct = (current - previous) / previous * 100
    if pct > 2.0:
        return _ansi("31", "\u2191")  # red up arrow — slower
    if pct < -2.0:
        return _ansi("32", "\u2193")  # green down arrow — faster
    return _ansi("33", "\u2192")  # yellow right arrow — stable


def _fmt_ms(value: float) -> str:
    """Format a millisecond value with appropriate precision."""
    if value >= 1000:
        return f"{value:,.0f}"
    return f"{value:,.1f}"


def format_history_table(records: list[BenchmarkRecord], max_rows: int = 10) -> str:
    """Format recent history as an aligned ASCII table.

    Columns: ``Date | Warm Median | CI 95% | Change | Version``

    Includes trend arrows comparing consecutive records:
    - up arrow (slower / regression)
    - down arrow (faster / improvement)
    - right arrow (unchanged within 2%)
    """
    if not records:
        return "  (no benchmark history)"

    display = records[:max_rows]

    # Column headers.
    hdr_date = "Date"
    hdr_median = "Warm Median"
    hdr_ci = "CI 95%"
    hdr_change = "Chg"
    hdr_version = "Version"

    # Build rows.
    rows: list[tuple[str, str, str, str, str]] = []
    for idx, rec in enumerate(display):
        # Date — try to parse ISO timestamp; fall back to raw string.
        try:
            dt = datetime.fromisoformat(rec.timestamp)
            date_str = dt.strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            date_str = str(rec.timestamp)[:16]

        median_str = f"{_fmt_ms(rec.warm_median_ms)} ms"

        # CI 95% range from stats if available.
        ci_lo = rec.stats.get("ci_lower", 0.0)
        ci_hi = rec.stats.get("ci_upper", 0.0)
        if ci_lo > 0 and ci_hi > 0:
            ci_str = f"\u00b1{_fmt_ms((ci_hi - ci_lo) / 2)} ms"
        else:
            ci_str = "-"

        # Trend arrow: compare with the next record (which is the
        # previous run chronologically, since records are newest-first).
        if idx + 1 < len(display):
            prev = display[idx + 1]
            arrow = _trend_arrow(rec.warm_median_ms, prev.warm_median_ms)
            diff = rec.warm_median_ms - prev.warm_median_ms
            pct = diff / prev.warm_median_ms * 100 if prev.warm_median_ms > 0 else 0
            change_str = f"{arrow} {pct:+.1f}%"
        else:
            change_str = "  base"

        ver_str = rec.version_hash[:8] if rec.version_hash else "-"

        rows.append((date_str, median_str, ci_str, change_str, ver_str))

    # Compute column widths.
    col_w = [
        max(len(hdr_date), *(len(r[0]) for r in rows)),
        max(len(hdr_median), *(len(r[1]) for r in rows)),
        max(len(hdr_ci), *(len(r[2]) for r in rows)),
        max(len(hdr_change) + 4, *(len(r[3]) for r in rows)),  # extra for ANSI
        max(len(hdr_version), *(len(r[4]) for r in rows)),
    ]

    # For change column, strip ANSI for width calculation.
    def _visible_len(s: str) -> int:
        """Length of string without ANSI escape sequences."""
        import re

        return len(re.sub(r"\033\[[0-9;]*m", "", s))

    # Recalculate change column width using visible lengths.
    col_w[3] = max(len(hdr_change), *(_visible_len(r[3]) for r in rows))

    sep = "  "

    def _pad(text: str, width: int, right_align: bool = False) -> str:
        """Pad text to width, accounting for ANSI escapes."""
        visible = _visible_len(text)
        pad_needed = max(0, width - visible)
        if right_align:
            return " " * pad_needed + text
        return text + " " * pad_needed

    # Assemble table.
    lines: list[str] = []

    # Header.
    header = sep.join(
        [
            _pad(hdr_date, col_w[0]),
            _pad(hdr_median, col_w[1], right_align=True),
            _pad(hdr_ci, col_w[2], right_align=True),
            _pad(hdr_change, col_w[3]),
            _pad(hdr_version, col_w[4]),
        ]
    )
    lines.append("  " + _ansi("1", header))

    # Separator line.
    rule = sep.join("\u2500" * w for w in col_w)
    lines.append("  " + rule)

    # Data rows.
    for row in rows:
        line = sep.join(
            [
                _pad(row[0], col_w[0]),
                _pad(row[1], col_w[1], right_align=True),
                _pad(row[2], col_w[2], right_align=True),
                _pad(row[3], col_w[3]),
                _pad(row[4], col_w[4]),
            ]
        )
        lines.append("  " + line)

    return "\n".join(lines)
