"""Tool Diversity Index (Shannon entropy) and Markov transition model."""

from __future__ import annotations

import math
from collections import Counter

from ._context import AggContext


def compute(ctx: AggContext) -> dict:
    diversity = _compute_diversity(ctx)
    markov = _compute_markov(ctx)
    return {"diversity": diversity, "markov": markov}


# ── Diversity (Shannon entropy + Pielou's J evenness) ──────────────────


def _compute_diversity(ctx: AggContext) -> dict:
    session_results: list[dict] = []

    for (source, session_id), sequence in ctx.tool_sequences.items():
        if not sequence:
            continue

        counts = Counter(sequence)
        total = sum(counts.values())
        n_distinct = len(counts)

        # Shannon entropy H = -sum(p * log2(p))
        h = 0.0
        for count in counts.values():
            p = count / total
            if p > 0:
                h -= p * math.log2(p)

        # Pielou's J evenness = H / log2(n) when n > 1, else 0.0 (single tool = maximally focused)
        if n_distinct > 1:
            j = h / math.log2(n_distinct)
        else:
            j = 0.0  # n_distinct <= 1: H == 0, so J == 0 (focused, not exploratory)

        classification = _classify_evenness(j)

        session_results.append(
            {
                "source": source,
                "session_id": session_id,
                "entropy": round(h, 4),
                "evenness": round(j, 4),
                "n_distinct_tools": n_distinct,
                "total_calls": total,
                "classification": classification,
            }
        )

    # Sort by evenness descending, take top 30
    session_results.sort(key=lambda r: (-r["evenness"], -r["total_calls"]))
    top_sessions = session_results[:30]

    # Global statistics
    all_evenness = [r["evenness"] for r in session_results]
    all_evenness_sorted = sorted(all_evenness)
    mean_evenness = sum(all_evenness) / len(all_evenness) if all_evenness else 0.0
    median_evenness = _median(all_evenness_sorted)

    classification_counts: dict[str, int] = Counter(r["classification"] for r in session_results)

    return {
        "sessions": top_sessions,
        "global": {
            "mean_evenness": round(mean_evenness, 4),
            "median_evenness": round(median_evenness, 4),
        },
        "classification_counts": {
            "focused": classification_counts.get("focused", 0),
            "structured": classification_counts.get("structured", 0),
            "exploratory": classification_counts.get("exploratory", 0),
            "highly_exploratory": classification_counts.get("highly_exploratory", 0),
        },
    }


def _classify_evenness(j: float) -> str:
    if j < 0.3:
        return "focused"
    if j < 0.6:
        return "structured"
    if j < 0.8:
        return "exploratory"
    return "highly_exploratory"


def _median(sorted_values: list[float]) -> float:
    if not sorted_values:
        return 0.0
    n = len(sorted_values)
    mid = n // 2
    if n % 2 == 0:
        return (sorted_values[mid - 1] + sorted_values[mid]) / 2
    return sorted_values[mid]


# ── Markov transition model ────────────────────────────────────────────


def _compute_markov(ctx: AggContext) -> dict:
    # Build first-order transition counts
    transition_counts: dict[str, Counter] = {}
    trigram_counts: Counter = Counter()

    for sequence in ctx.tool_sequences.values():
        if not sequence:
            continue
        for i in range(len(sequence) - 1):
            src_tool = sequence[i]
            dst_tool = sequence[i + 1]
            if src_tool not in transition_counts:
                transition_counts[src_tool] = Counter()
            transition_counts[src_tool][dst_tool] += 1

        # Trigrams
        for i in range(len(sequence) - 2):
            trigram = (sequence[i], sequence[i + 1], sequence[i + 2])
            trigram_counts[trigram] += 1

    # Normalize to probabilities
    transition_matrix: list[dict] = []
    self_loop_tools: list[dict] = []

    for src_tool in sorted(transition_counts):
        row = transition_counts[src_tool]
        row_total = sum(row.values())
        if row_total == 0:
            continue

        for dst_tool, count in row.most_common():
            prob = count / row_total
            transition_matrix.append(
                {
                    "from": src_tool,
                    "to": dst_tool,
                    "probability": round(prob, 4),
                    "count": count,
                }
            )

        # Detect self-loops: P(A|A) > 0.4
        self_count = row.get(src_tool, 0)
        self_prob = self_count / row_total
        if self_prob > 0.4:
            self_loop_tools.append(
                {
                    "tool": src_tool,
                    "self_prob": round(self_prob, 4),
                }
            )

    self_loop_tools.sort(key=lambda r: -r["self_prob"])

    top_trigrams = [{"sequence": list(tri), "count": count} for tri, count in trigram_counts.most_common(10)]

    return {
        "transition_matrix": transition_matrix,
        "self_loop_tools": self_loop_tools,
        "top_trigrams": top_trigrams,
    }
