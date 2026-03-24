"""Session complexity scoring (0-100) with weighted multi-dimensional analysis."""

from __future__ import annotations

import bisect

from ._context import AggContext

_WEIGHTS = {
    "tool_chain_depth": 0.20,
    "unique_tools": 0.15,
    "reasoning_intensity": 0.15,
    "model_switches": 0.15,
    "iteration_patterns": 0.15,
    "session_length": 0.10,
    "tool_count": 0.10,
}

_CLASSIFICATIONS = [
    (25, "trivial"),
    (50, "moderate"),
    (75, "complex"),
    (100, "extreme"),
]

_MIN_TOOL_CALLS = 3
_TOP_N = 30


def compute(ctx: AggContext) -> dict:
    raw_records = _collect_raw_records(ctx)
    if not raw_records:
        return {
            "session_scores": [],
            "distribution": {"trivial": 0, "moderate": 0, "complex": 0, "extreme": 0},
            "average_complexity": 0.0,
            "most_complex": None,
        }

    _apply_percentile_ranks(raw_records)
    scored = _score_and_classify(raw_records)

    scored.sort(key=lambda r: r["score"], reverse=True)
    top = scored[:_TOP_N]

    distribution = {"trivial": 0, "moderate": 0, "complex": 0, "extreme": 0}
    total_score = 0.0
    for record in scored:
        distribution[record["classification"]] += 1
        total_score += record["score"]

    average = round(total_score / len(scored), 2) if scored else 0.0

    session_scores = [
        {
            "session_id": r["session_id"],
            "source": r["source"],
            "score": r["score"],
            "classification": r["classification"],
            "components": {dim: round(r["ranks"][dim], 4) for dim in _WEIGHTS},
        }
        for r in top
    ]

    return {
        "session_scores": session_scores,
        "distribution": distribution,
        "average_complexity": average,
        "most_complex": session_scores[0] if session_scores else None,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _collect_raw_records(ctx: AggContext) -> list[dict]:
    """Build one raw record per qualifying session."""
    records: list[dict] = []
    for session in ctx.active_sessions:
        if session["tool_calls"] < _MIN_TOOL_CALLS:
            continue

        key = (session["source"], session["session_id"])
        seq = ctx.tool_sequences.get(key, [])
        if not seq:
            continue

        rollup = ctx.session_rollups.get(key)
        if rollup is None:
            continue

        records.append(
            {
                "session_id": session["session_id"],
                "source": session["source"],
                "raw": {
                    "tool_chain_depth": _longest_tool_run(seq),
                    "unique_tools": len(set(seq)) / len(seq) if seq else 0.0,
                    "reasoning_intensity": rollup["reasoning"] / (rollup["output"] + 1),
                    "model_switches": len(rollup["models"]),
                    "iteration_patterns": _count_iteration_patterns(seq),
                    "session_length": session["minutes"],
                    "tool_count": session["tool_calls"],
                },
                "ranks": {},
            }
        )

    return records


def _longest_tool_run(seq: list[str]) -> int:
    """Length of the longest consecutive run of the same tool."""
    if not seq:
        return 0
    best = 1
    current = 1
    for i in range(1, len(seq)):
        if seq[i] == seq[i - 1]:
            current += 1
            if current > best:
                best = current
        else:
            current = 1
    return best


def _count_iteration_patterns(seq: list[str]) -> int:
    """Count Read->Edit->Bash subsequences (not necessarily adjacent)."""
    count = 0
    i = 0
    while i < len(seq):
        if _matches_tool(seq[i], "Read"):
            j = i + 1
            while j < len(seq):
                if _matches_tool(seq[j], "Edit"):
                    k = j + 1
                    while k < len(seq):
                        if _matches_tool(seq[k], "Bash"):
                            count += 1
                            i = k  # advance past this match
                            break
                        k += 1
                    break
                j += 1
        i += 1
    return count


def _matches_tool(name: str, target: str) -> bool:
    """Case-insensitive check whether *name* contains *target*."""
    return target.lower() in name.lower()


def _apply_percentile_ranks(records: list[dict]) -> None:
    """Replace raw values with percentile ranks (0.0-1.0) across all sessions."""
    for dim in _WEIGHTS:
        values = sorted(r["raw"][dim] for r in records)
        n = len(values)
        for record in records:
            val = record["raw"][dim]
            # Fraction of values that are strictly less than val
            rank = bisect.bisect_left(values, val) / n if n > 0 else 0.0
            record["ranks"][dim] = rank


def _score_and_classify(records: list[dict]) -> list[dict]:
    """Compute weighted score and classification for each record."""
    for record in records:
        score = sum(_WEIGHTS[dim] * record["ranks"][dim] for dim in _WEIGHTS)
        record["score"] = round(score * 100, 2)
        record["classification"] = _classify(record["score"])
    return records


def _classify(score: float) -> str:
    for threshold, label in _CLASSIFICATIONS:
        if score <= threshold:
            return label
    return "extreme"
