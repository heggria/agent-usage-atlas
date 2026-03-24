"""Tool usage anti-pattern detection and health scoring."""

from __future__ import annotations

from ._context import AggContext

# Search commands that indicate misuse when Grep/Glob tools are also available
_SEARCH_PREFIXES = ("grep", "rg", "find", "ag", "ack")

# Severity levels
_HIGH = "high"
_MEDIUM = "medium"
_LOW = "low"


def _count_consecutive_runs(sequence: list[str], predicate, min_run: int) -> int:
    """Count how many times *predicate* holds for *min_run*+ consecutive items."""
    violations = 0
    run = 0
    for item in sequence:
        if predicate(item):
            run += 1
            if run == min_run:
                violations += 1
        else:
            run = 0
    return violations


def _detect_redundant_read(sequences: dict) -> tuple[int, int]:
    """3+ consecutive Read calls without an intervening Write/Edit."""
    total = 0
    sessions = 0
    for seq in sequences.values():
        hits = _count_consecutive_runs(seq, lambda t: t == "Read", 3)
        if hits:
            total += hits
            sessions += 1
    return total, sessions


def _detect_bash_for_search_precise(ctx: AggContext) -> tuple[int, int]:
    """Bash calls whose command starts with a search prefix, in sessions with Grep/Glob."""
    sessions_with_native: set[tuple[str, str]] = set()
    for key, seq in ctx.tool_sequences.items():
        if any(t in ("Grep", "Glob") for t in seq):
            sessions_with_native.add(key)

    if not sessions_with_native:
        return 0, 0

    # Since we only have tool_sequences (tool names) and command_counts (global),
    # use the session-level proxy: count Bash entries in sessions that have Grep/Glob.
    total = 0
    affected: set[tuple[str, str]] = set()
    for key in sessions_with_native:
        seq = ctx.tool_sequences.get(key, [])
        bash_count = sum(1 for t in seq if t == "Bash")
        if bash_count:
            total += bash_count
            affected.add(key)

    # Refine with global command_counts: only count if search-like commands exist
    search_command_total = sum(count for cmd, count in ctx.command_counts.items() if cmd in _SEARCH_PREFIXES)
    if search_command_total == 0:
        return 0, 0

    # Use the lesser of bash-in-search-sessions and actual search commands
    return min(total, search_command_total), len(affected) if search_command_total else 0


def _detect_error_cascade(sequences: dict) -> tuple[int, int]:
    """3+ consecutive Bash calls (proxy for repeated failing commands)."""
    total = 0
    sessions = 0
    for seq in sequences.values():
        hits = _count_consecutive_runs(seq, lambda t: t == "Bash", 3)
        if hits:
            total += hits
            sessions += 1
    return total, sessions


def _detect_edit_without_verify(sequences: dict) -> tuple[int, int]:
    """Edit followed immediately by another Edit without an intervening Read."""
    total = 0
    sessions = 0
    for seq in sequences.values():
        hits = 0
        prev = None
        for tool in seq:
            if tool == "Edit" and prev == "Edit":
                hits += 1
            prev = tool
        if hits:
            total += hits
            sessions += 1
    return total, sessions


def _detect_glob_storm(sequences: dict) -> tuple[int, int]:
    """5+ consecutive Glob calls."""
    total = 0
    sessions = 0
    for seq in sequences.values():
        hits = _count_consecutive_runs(seq, lambda t: t == "Glob", 5)
        if hits:
            total += hits
            sessions += 1
    return total, sessions


def _detect_tool_repetition(sequences: dict) -> tuple[int, int]:
    """Any single tool appearing 5+ times consecutively."""
    total = 0
    sessions = 0
    for seq in sequences.values():
        hits = 0
        run = 1
        for i in range(1, len(seq)):
            if seq[i] == seq[i - 1]:
                run += 1
                if run == 5:
                    hits += 1
            else:
                run = 1
        if hits:
            total += hits
            sessions += 1
    return total, sessions


def compute(ctx: AggContext) -> dict:
    """Detect tool usage anti-patterns and compute a health score."""
    sequences = ctx.tool_sequences

    # Run all detectors
    redundant_read_count, redundant_read_sessions = _detect_redundant_read(sequences)
    bash_search_count, bash_search_sessions = _detect_bash_for_search_precise(ctx)
    error_cascade_count, error_cascade_sessions = _detect_error_cascade(sequences)
    edit_no_verify_count, edit_no_verify_sessions = _detect_edit_without_verify(sequences)
    glob_storm_count, glob_storm_sessions = _detect_glob_storm(sequences)
    tool_rep_count, tool_rep_sessions = _detect_tool_repetition(sequences)

    # Build violations list (only include patterns that were actually detected)
    detectors = [
        {
            "pattern": "redundant_read",
            "severity": _MEDIUM,
            "count": redundant_read_count,
            "sessions_affected": redundant_read_sessions,
            "recommendation": (
                "Avoid reading the same file repeatedly. Cache file contents or use Edit/Write between reads."
            ),
        },
        {
            "pattern": "bash_for_search",
            "severity": _HIGH,
            "count": bash_search_count,
            "sessions_affected": bash_search_sessions,
            "recommendation": ("Use the Grep/Glob tools instead of shelling out to grep/rg/find/ag/ack via Bash."),
        },
        {
            "pattern": "error_cascade",
            "severity": _HIGH,
            "count": error_cascade_count,
            "sessions_affected": error_cascade_sessions,
            "recommendation": ("Stop and diagnose root cause after a command fails instead of retrying blindly."),
        },
        {
            "pattern": "edit_without_verify",
            "severity": _MEDIUM,
            "count": edit_no_verify_count,
            "sessions_affected": edit_no_verify_sessions,
            "recommendation": ("Read the file after each Edit to verify the change before making further edits."),
        },
        {
            "pattern": "glob_storm",
            "severity": _LOW,
            "count": glob_storm_count,
            "sessions_affected": glob_storm_sessions,
            "recommendation": (
                "Consolidate multiple Glob calls into fewer, broader patterns or use Grep for content-based searches."
            ),
        },
        {
            "pattern": "tool_repetition",
            "severity": _LOW,
            "count": tool_rep_count,
            "sessions_affected": tool_rep_sessions,
            "recommendation": ("Batch or consolidate repeated tool calls to reduce unnecessary context consumption."),
        },
    ]

    violations: list[dict] = [d for d in detectors if d["count"] > 0]

    high_count = sum(1 for v in violations if v["severity"] == _HIGH)
    medium_count = sum(1 for v in violations if v["severity"] == _MEDIUM)
    low_count = sum(1 for v in violations if v["severity"] == _LOW)

    health_penalty = sum(
        d["count"] * (5 if d["severity"] == _HIGH else 2 if d["severity"] == _MEDIUM else 1) for d in violations
    )
    health_score = max(0, 100 - health_penalty)

    return {
        "anti_patterns": {
            "violations": violations,
            "health_score": health_score,
            "summary": {
                "high_count": high_count,
                "medium_count": medium_count,
                "low_count": low_count,
            },
        },
    }
