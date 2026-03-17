"""Tool analysis: ranking, bigrams, chord diagram, commands."""

from __future__ import annotations

from collections import Counter

from ._context import AggContext, _percent


def compute(ctx: AggContext) -> dict:
    combined = Counter()
    for counts in ctx.tool_counts_by_source.values():
        combined.update(counts)
    tool_ranking = [
        {
            "name": name,
            "count": count,
            "by_source": {src: ctx.tool_counts_by_source[src][name] for src in ctx.tool_counts_by_source},
        }
        for name, count in combined.most_common(30)
    ]

    bigram_counts = Counter()
    tool_degrees = Counter()
    for sequence in ctx.tool_sequences.values():
        for i in range(len(sequence) - 1):
            pair = (sequence[i], sequence[i + 1])
            bigram_counts[pair] += 1
            tool_degrees[pair[0]] += 1
            tool_degrees[pair[1]] += 1
    tool_bigrams = [{"from": s, "to": t, "count": c} for (s, t), c in bigram_counts.most_common(20)]
    chord_tools = {n for n, _ in tool_degrees.most_common(8)}
    bigram_chord = {
        "nodes": [
            {"name": n, "value": tool_degrees[n]} for n in sorted(chord_tools, key=lambda i: (-tool_degrees[i], i))
        ],
        "links": [
            {"source": s, "target": t, "value": c}
            for (s, t), c in bigram_counts.most_common()
            if s in chord_tools and t in chord_tools
        ],
    }

    return {
        "ranking": tool_ranking,
        "tool_bigrams": tool_bigrams,
        "bigram_chord": bigram_chord,
        "total_tool_calls": sum(combined.values()),
    }


def commands(ctx: AggContext) -> dict:
    total_commands = sum(ctx.command_counts.values())
    successful_commands = sum(d["command_successes"] for d in ctx.ordered_days)
    top_commands = [
        {
            "command": cmd,
            "count": count,
            "failures": ctx.command_failures[cmd],
            "failure_rate": round(_percent(ctx.command_failures[cmd], count), 3),
        }
        for cmd, count in ctx.command_counts.most_common(20)
    ]
    daily_command_success = [
        {
            "date": d["date"],
            "label": d["label"],
            "successes": d["command_successes"],
            "failures": d["command_failures"],
            "total": d["command_successes"] + d["command_failures"],
        }
        for d in ctx.ordered_days
    ]
    return {
        "summary": {
            "success_rate": round(_percent(successful_commands, total_commands), 3),
            "total_commands": total_commands,
        },
        "top_commands": top_commands,
        "daily_success": daily_command_success,
    }
