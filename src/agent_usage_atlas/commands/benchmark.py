"""Pipeline benchmark command -- measures parse/aggregate/render timings.

Integrates with ``benchmark_stats`` (statistical analysis) and
``benchmark_store`` (history persistence) when available, falling back to
basic output otherwise.
"""

from __future__ import annotations

import sys
import time
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import Any

from ._ansi import bold, cyan, dim, green, magenta, red, yellow

# ── Cache clearing ────────────────────────────────────────────────────


def _clear_all_caches() -> None:
    """Reset every layer of caching so the next run is truly cold."""
    from .. import cli as cli_mod

    cli_mod._dashboard_cache = None
    cli_mod._dashboard_cache_key = None

    from ..parsers._base import (
        _JSONL_CACHE,
        _RESULT_CACHE,
        _RESULT_HIT_FLAGS,
    )

    _JSONL_CACHE.clear()
    _RESULT_CACHE.clear()
    _RESULT_HIT_FLAGS.clear()


# ── Pipeline phases ───────────────────────────────────────────────────


def _run_pipeline(days: int) -> dict[str, Any]:
    """Run the full parse-aggregate-render pipeline, returning timing + stats.

    Returns dict with keys:
        total_ms, parse_ms, aggregate_ms, render_ms,
        events, tool_calls, sessions, jsonl_cache_entries, html_bytes
    """
    from ..aggregation import aggregate
    from ..parsers import parse_all
    from ..parsers._base import _JSONL_CACHE
    from ..renderers import render

    local_tz = datetime.now(timezone.utc).astimezone().tzinfo
    now_local = datetime.now(local_tz)
    now_utc = now_local.astimezone(timezone.utc)
    start_local = (now_local - timedelta(days=days)).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )
    start_utc = start_local.astimezone(timezone.utc)

    # Phase 1: parse
    t0 = time.perf_counter()
    result, claude_stats, _changed = parse_all(start_utc, now_utc, local_tz=local_tz)
    t_parse = time.perf_counter()

    events = [e for e in result.events if start_utc <= e.timestamp <= now_utc]
    tool_calls = [t for t in result.tool_calls if start_utc <= t.timestamp <= now_utc]
    turn_durations = [t for t in result.turn_durations if start_utc <= t.timestamp <= now_utc]
    user_messages = [m for m in result.user_messages if start_utc <= m.timestamp <= now_utc]

    # Phase 2: aggregate
    dashboard = aggregate(
        events,
        tool_calls,
        result.session_metas,
        start_local=start_local,
        now_local=now_local,
        local_tz=local_tz,
        task_events=result.task_events,
        turn_durations=turn_durations,
        cursor_codegen=result.code_gen,
        cursor_commits=result.scored_commits,
        claude_stats_cache=claude_stats,
        user_messages=user_messages,
    )
    t_agg = time.perf_counter()

    # Phase 3: render
    html = render(dashboard, fmt="html")
    t_render = time.perf_counter()

    return {
        "total_ms": (t_render - t0) * 1000,
        "parse_ms": (t_parse - t0) * 1000,
        "aggregate_ms": (t_agg - t_parse) * 1000,
        "render_ms": (t_render - t_agg) * 1000,
        "events": len(events),
        "tool_calls": len(tool_calls),
        "sessions": len(result.session_metas),
        "jsonl_cache_entries": len(_JSONL_CACHE),
        "html_bytes": len(html.encode("utf-8")),
    }


# ── Formatting helpers ────────────────────────────────────────────────


def _fmt_ms(ms: float) -> str:
    return f"{ms:,.1f} ms"


def _fmt_size(nbytes: int) -> str:
    if nbytes >= 1_048_576:
        return f"{nbytes / 1_048_576:,.1f} MB"
    if nbytes >= 1024:
        return f"{nbytes / 1024:,.0f} KB"
    return f"{nbytes:,} B"


def _rule() -> str:
    return "\u2550" * 58


def _sep() -> str:
    return dim("\u2502")


# ── Optional module loading ──────────────────────────────────────────

_HAS_STATS = False
_HAS_STORE = False

try:
    from ..benchmark_stats import (
        BenchStats as _BenchStats,
    )
    from ..benchmark_stats import (
        RegressionResult as _RegressionResult,
    )
    from ..benchmark_stats import (
        WarmupResult as _WarmupResult,
    )
    from ..benchmark_stats import (
        compare_runs as _compare_runs,
    )
    from ..benchmark_stats import (
        compute_stats as _compute_stats,
    )
    from ..benchmark_stats import (
        detect_warmup as _detect_warmup,
    )

    _HAS_STATS = True
except ImportError:
    _BenchStats = None  # type: ignore[assignment,misc]
    _RegressionResult = None  # type: ignore[assignment,misc]
    _WarmupResult = None  # type: ignore[assignment,misc]
    _compute_stats = None  # type: ignore[assignment]
    _detect_warmup = None  # type: ignore[assignment]
    _compare_runs = None  # type: ignore[assignment]

try:
    from ..benchmark_store import (
        BenchmarkRecord as _BenchmarkRecord,
    )
    from ..benchmark_store import (
        MachineInfo as _MachineInfo,
    )
    from ..benchmark_store import (
        compute_version_hash as _compute_version_hash,
    )
    from ..benchmark_store import (
        format_history_table as _format_history_table,
    )
    from ..benchmark_store import (
        get_baseline as _get_baseline,
    )
    from ..benchmark_store import (
        load_history as _load_history,
    )
    from ..benchmark_store import (
        save_record as _save_record,
    )

    _HAS_STORE = True
except ImportError:
    _BenchmarkRecord = None  # type: ignore[assignment,misc]
    _MachineInfo = None  # type: ignore[assignment,misc]
    _compute_version_hash = None  # type: ignore[assignment]
    _format_history_table = None  # type: ignore[assignment]
    _get_baseline = None  # type: ignore[assignment]
    _load_history = None  # type: ignore[assignment]
    _save_record = None  # type: ignore[assignment]


# ── CLI registration ─────────────────────────────────────────────────


def add_parser(subparsers):  # noqa: ANN001
    parser = subparsers.add_parser(
        "benchmark",
        help="Benchmark the parse-aggregate-render pipeline",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=5,
        metavar="N",
        help="Number of warm rounds (default: 5)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of recent days to include (default: 30)",
    )
    parser.add_argument(
        "--history",
        action="store_true",
        default=False,
        help="Show recent benchmark history and exit",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        default=False,
        help="Don't save results to history",
    )
    parser.add_argument(
        "--warmup",
        type=int,
        default=-1,
        metavar="N",
        help="Warmup rounds to discard (default: auto-detect)",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        default=False,
        help="Compare with last saved baseline",
    )
    parser.set_defaults(func=run)
    return parser


# ── Output sections ──────────────────────────────────────────────────


def _print_header(rounds: int, days: int, machine_label: str) -> None:
    print(bold(_rule()))
    title = f"Benchmark: {rounds} rounds, {days} days"
    machine_part = f"machine: {machine_label}"
    # Pad the middle so the line looks balanced
    gap = 58 - len(title) - len(machine_part) - 5
    gap = max(gap, 2)
    print(bold(f"  {title}{' ' * gap}{_sep()}  {dim(machine_part)}"))
    print(bold(_rule()))


def _print_cold(cold_ms: float) -> None:
    print()
    label = "Cold pipeline:"
    print(f"  {cyan(label):<40s}{bold(_fmt_ms(cold_ms)):>18s}")


def _print_warm_stats_rich(stats: Any) -> None:
    """Print warm pipeline stats using BenchStats from benchmark_stats."""
    print()
    label = "Warm pipeline (median):"
    print(f"  {green(label):<40s}{bold(_fmt_ms(stats.median)):>18s}")

    ci_text = f"[{stats.ci_lower:,.1f}, {stats.ci_upper:,.1f}] ms"
    print(f"    {'95% CI:':<34s}{ci_text:>18s}")

    p_text = f"{stats.p90:,.1f} / {stats.p99:,.1f} ms"
    print(f"    {'P90 / P99:':<34s}{p_text:>18s}")

    mad_text = _fmt_ms(stats.mad)
    print(f"    {'MAD:':<34s}{mad_text:>18s}")

    outlier_text = f"{stats.outlier_count} of {stats.n}"
    print(f"    {'Outliers:':<34s}{outlier_text:>18s}")


def _print_warm_stats_basic(
    warm_totals: list[float],
) -> None:
    """Print warm pipeline stats using stdlib statistics only."""
    import statistics

    if not warm_totals:
        return

    median_total = statistics.median(warm_totals)
    min_total = min(warm_totals)
    max_total = max(warm_totals)

    print()
    label = "Warm pipeline (median):"
    print(f"  {green(label):<40s}{bold(_fmt_ms(median_total)):>18s}")
    minmax = f"{_fmt_ms(min_total)} / {_fmt_ms(max_total)}"
    print(f"    {'min / max:':<34s}{minmax}")

    if len(warm_totals) >= 3:
        stdev = statistics.stdev(warm_totals)
        print(f"    {'Stddev:':<34s}{_fmt_ms(stdev):>18s}")


def _print_phase_breakdown(
    phase_medians: dict[str, float],
    total_median: float,
) -> None:
    """Print per-phase breakdown with percentage of total."""
    print()
    print(f"  {dim('Phase breakdown (warm median):')}")
    for name, med in phase_medians.items():
        pct = (med / total_median * 100.0) if total_median > 0 else 0.0
        ms_str = _fmt_ms(med)
        pct_str = f"({pct:4.1f}%)"
        print(f"    {name + ':':<30s}{ms_str:>14s}  {dim(pct_str)}")


def _print_regression(
    regression: Any,
    baseline_ts: str,
) -> None:
    """Print comparison vs baseline using RegressionResult."""
    print()
    ts_label = baseline_ts[:10] if len(baseline_ts) >= 10 else baseline_ts
    print(f"  {magenta(f'vs baseline ({ts_label}):')}")

    # Direction arrow and label
    if regression.changed:
        if regression.direction == "faster":
            change_str = green(f"{abs(regression.pct_change):.1f}% faster \u2193")
        else:
            change_str = red(f"{abs(regression.pct_change):.1f}% slower \u2191")
    else:
        change_str = dim(f"{abs(regression.pct_change):.1f}%")

    welch_label = "Welch's t p-value:"
    cohen_label = "Cohen's d:"
    print(f"    {'Change:':<34s}{change_str:>18s}")
    print(f"    {welch_label:<34s}{regression.p_value:>18.3f}")
    print(f"    {cohen_label:<34s}{regression.cohens_d:>10.2f} ({regression.effect_label})")

    # Verdict
    if not regression.changed:
        verdict = dim("No significant change")
    elif regression.direction == "faster":
        verdict = green("Significant improvement \u2193")
    else:
        verdict = red("Significant regression \u2191")

    print(f"    {'Verdict:':<34s}{verdict}")


def _print_dataset(
    events: int,
    tool_calls: int,
    sessions: int,
    html_bytes: int,
) -> None:
    print()
    print(f"  {yellow('Dataset:')}")
    print(f"    {'Events:':<34s}{events:>14,}")
    print(f"    {'Tool calls:':<34s}{tool_calls:>14,}")
    print(f"    {'Sessions:':<34s}{sessions:>14,}")
    print(f"    {'HTML size:':<34s}{_fmt_size(html_bytes):>14s}")


def _print_footer(
    version_hash: str | None,
    saved: bool,
) -> None:
    print()
    parts: list[str] = []
    if version_hash:
        parts.append(f"Version: {version_hash}")
    if saved:
        parts.append("Saved to history")
    elif not saved and _HAS_STORE:
        parts.append("Not saved (--no-save)")
    if parts:
        footer_body = f"  {(f'  {_sep()}  ').join(parts)}"
        print(dim(footer_body))
    print(bold(_rule()))


# ── History mode ─────────────────────────────────────────────────────


def _handle_history() -> None:
    """Print benchmark history table and exit."""
    if not _HAS_STORE:
        print(red("Error: benchmark_store module not available."))
        print("Install it to use --history.")
        sys.exit(1)

    records = _load_history(limit=50)  # type: ignore[misc]
    if not records:
        print(dim("No benchmark history found."))
        return

    table = _format_history_table(records, max_rows=20)  # type: ignore[misc]
    print(table)


# ── Warm run collector ───────────────────────────────────────────────


def _collect_warm_runs(
    rounds: int,
    days: int,
    warmup_n: int,
) -> tuple[list[float], list[float], list[float], list[float], int]:
    """Run warmup + measured rounds. Returns (totals, parse, agg, render, warmup_discarded).

    If *warmup_n* is ``-1`` (auto), we run a few extra rounds and then
    use ``detect_warmup`` to find the steady-state boundary.  Otherwise
    we discard exactly *warmup_n* leading rounds.
    """
    auto_warmup = warmup_n == -1

    # Decide how many total iterations to execute.
    # For auto-warmup we add a small buffer so the detector has data.
    if auto_warmup and _HAS_STATS:
        extra = min(max(rounds // 2, 3), 10)
    else:
        extra = max(warmup_n, 0)

    total_iters = rounds + extra

    all_totals: list[float] = []
    all_parse: list[float] = []
    all_agg: list[float] = []
    all_render: list[float] = []

    for _ in range(total_iters):
        w = _run_pipeline(days)
        all_totals.append(w["total_ms"])
        all_parse.append(w["parse_ms"])
        all_agg.append(w["aggregate_ms"])
        all_render.append(w["render_ms"])

    # Determine how many leading samples to discard.
    discard = 0
    if auto_warmup and _HAS_STATS:
        warmup_result = _detect_warmup(all_totals)  # type: ignore[misc]
        discard = warmup_result.warmup_end
    elif not auto_warmup and warmup_n > 0:
        discard = min(warmup_n, total_iters - 1)

    return (
        all_totals[discard:],
        all_parse[discard:],
        all_agg[discard:],
        all_render[discard:],
        discard,
    )


# ── Entry point ───────────────────────────────────────────────────────


def run(args: Any) -> None:  # noqa: C901
    rounds: int = args.rounds
    days: int = args.days
    no_save: bool = getattr(args, "no_save", False)
    warmup_n: int = getattr(args, "warmup", -1)
    do_compare: bool = getattr(args, "compare", False)
    show_history: bool = getattr(args, "history", False)

    # ── History mode: print table and exit ────────────────────────────
    if show_history:
        _handle_history()
        return

    # ── Machine info ──────────────────────────────────────────────────
    machine_label = "unknown"
    machine_fp = ""
    machine_info = None
    if _HAS_STORE:
        try:
            machine_info = _MachineInfo.capture()  # type: ignore[union-attr]
            machine_fp = machine_info.fingerprint()
            # Short label: first 6 chars of fingerprint
            machine_label = machine_fp[:6] if machine_fp else "unknown"
        except Exception:
            pass

    # ── Version hash ──────────────────────────────────────────────────
    version_hash: str | None = None
    if _HAS_STORE:
        try:
            version_hash = _compute_version_hash()  # type: ignore[misc]
        except Exception:
            pass

    _print_header(rounds, days, machine_label)

    # ── (a) Cold run ──────────────────────────────────────────────────
    _clear_all_caches()
    cold = _run_pipeline(days)
    _print_cold(cold["total_ms"])

    # ── (b-c) Warmup detection + warm runs ────────────────────────────
    warm_totals, warm_parse, warm_agg, warm_render, warmup_discarded = _collect_warm_runs(rounds, days, warmup_n)

    if warmup_discarded > 0:
        print()
        print(f"  {dim(f'Warmup: {warmup_discarded} rounds discarded')}")

    # ── (d) Compute stats ─────────────────────────────────────────────
    import statistics as _stdlib_stats

    stats_obj = None
    if _HAS_STATS and len(warm_totals) >= 2:
        stats_obj = _compute_stats(warm_totals)  # type: ignore[misc]
        _print_warm_stats_rich(stats_obj)
    else:
        _print_warm_stats_basic(warm_totals)

    # ── Phase breakdown ───────────────────────────────────────────────
    phase_medians: dict[str, float] = {
        "Parse": _stdlib_stats.median(warm_parse) if warm_parse else 0.0,
        "Aggregate": _stdlib_stats.median(warm_agg) if warm_agg else 0.0,
        "Render": _stdlib_stats.median(warm_render) if warm_render else 0.0,
    }
    warm_median = (
        stats_obj.median if stats_obj is not None else (_stdlib_stats.median(warm_totals) if warm_totals else 0.0)
    )
    _print_phase_breakdown(phase_medians, warm_median)

    # ── (e-g) Baseline comparison ─────────────────────────────────────
    regression = None
    baseline_ts = ""
    baseline_record = None

    if do_compare and _HAS_STORE and _HAS_STATS and version_hash:
        try:
            baseline_record = _get_baseline(version_hash, machine_fp)  # type: ignore[misc]
        except Exception:
            baseline_record = None

        if baseline_record is not None and baseline_record.warm_samples and warm_totals:
            try:
                regression = _compare_runs(  # type: ignore[misc]
                    baseline=baseline_record.warm_samples,
                    contender=warm_totals,
                )
                baseline_ts = baseline_record.timestamp
            except Exception:
                regression = None

    if regression is not None:
        _print_regression(regression, baseline_ts)
    elif do_compare:
        print()
        if not _HAS_STORE:
            print(f"  {dim('Compare skipped: benchmark_store not available')}")
        elif not _HAS_STATS:
            print(f"  {dim('Compare skipped: benchmark_stats not available')}")
        elif baseline_record is None:
            print(f"  {dim('No baseline found for comparison')}")

    # ── Dataset ───────────────────────────────────────────────────────
    _print_dataset(
        events=cold["events"],
        tool_calls=cold["tool_calls"],
        sessions=cold["sessions"],
        html_bytes=cold["html_bytes"],
    )

    # ── (h) Save to history ───────────────────────────────────────────
    saved = False
    if not no_save and _HAS_STORE:
        try:
            record = _BenchmarkRecord(  # type: ignore[misc]
                timestamp=datetime.now(timezone.utc).isoformat(),
                version_hash=version_hash or "",
                machine=machine_info,
                days=days,
                rounds=rounds,
                cold_ms=cold["total_ms"],
                warm_median_ms=warm_median,
                warm_min_ms=min(warm_totals) if warm_totals else 0.0,
                warm_max_ms=max(warm_totals) if warm_totals else 0.0,
                warm_samples=list(warm_totals),
                phase_medians=phase_medians,
                dataset={
                    "events": cold["events"],
                    "tool_calls": cold["tool_calls"],
                    "sessions": cold["sessions"],
                    "html_bytes": cold["html_bytes"],
                },
                stats=(
                    asdict(stats_obj)
                    if stats_obj is not None and hasattr(stats_obj, "__dataclass_fields__")
                    else (stats_obj or {})
                ),
                regression=regression,
            )
            _save_record(record)  # type: ignore[misc]
            saved = True
        except Exception as exc:
            print(f"  {yellow(f'Warning: failed to save record: {exc}')}")

    # ── Footer ────────────────────────────────────────────────────────
    _print_footer(version_hash, saved)
