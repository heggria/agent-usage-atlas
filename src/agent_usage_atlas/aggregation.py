"""Aggregate parsed events into a rich dashboard payload."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import timedelta
from pathlib import Path
from statistics import median

SOURCE_ORDER = ["Codex", "Claude", "Cursor"]
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _source_rank(name: str) -> int:
    return SOURCE_ORDER.index(name) if name in SOURCE_ORDER else len(SOURCE_ORDER)


def _round_money(value: float) -> float:
    return round(value, 4)


def _percent(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _percentile(sorted_values: list[float], fraction: float) -> float:
    if not sorted_values:
        return 0.0
    index = min(len(sorted_values) - 1, max(0, round((len(sorted_values) - 1) * fraction)))
    return sorted_values[index]


def _build_sankey(cards: list[dict], specs: list[tuple[str, str]]) -> dict:
    nodes = []
    links = []
    for card in cards:
        nodes.append({"name": card["source"], "kind": "source"})
    for _, label in specs:
        nodes.append({"name": label, "kind": "bucket"})
    for card in cards:
        for key, label in specs:
            value = card.get(key, 0)
            if value > 0:
                links.append({"source": card["source"], "target": label, "value": value})
    return {"nodes": nodes, "links": links}


def aggregate(events, tool_calls, session_metas, *, start_local, now_local, local_tz,
              task_events=None, turn_durations=None, cursor_codegen=None,
              cursor_commits=None, claude_stats_cache=None):
    source_rollups = defaultdict(
        lambda: {
            "source": "",
            "total_tokens": 0,
            "uncached_input": 0,
            "cache_read": 0,
            "cache_write": 0,
            "output": 0,
            "reasoning": 0,
            "messages": 0,
            "sessions": set(),
            "models": Counter(),
            "token_capable": False,
            "cost": 0.0,
            "cost_input": 0.0,
            "cost_cache_read": 0.0,
            "cost_cache_write": 0.0,
            "cost_output": 0.0,
            "cost_reasoning": 0.0,
            "cost_cache_read_full": 0.0,
        }
    )
    daily_rollups = defaultdict(
        lambda: {
            "date": "",
            "label": "",
            "total_tokens": 0,
            "uncached_input": 0,
            "cache_read": 0,
            "cache_write": 0,
            "output": 0,
            "reasoning": 0,
            "messages": 0,
            "cost": 0.0,
            "cost_input": 0.0,
            "cost_cache_read": 0.0,
            "cost_cache_write": 0.0,
            "cost_output": 0.0,
            "cost_reasoning": 0.0,
            "source_totals": defaultdict(int),
            "cost_sources": defaultdict(float),
            "tool_calls": 0,
            "command_successes": 0,
            "command_failures": 0,
        }
    )
    session_rollups = defaultdict(
        lambda: {
            "source": "",
            "session_id": "",
            "first_local": None,
            "last_local": None,
            "total_tokens": 0,
            "uncached_input": 0,
            "cache_read": 0,
            "cache_write": 0,
            "output": 0,
            "reasoning": 0,
            "messages": 0,
            "tool_calls": 0,
            "models": Counter(),
            "cost": 0.0,
        }
    )
    hourly_source_totals = defaultdict(lambda: defaultdict(int))
    weekday_hour_heatmap = defaultdict(lambda: defaultdict(int))
    tool_counts_by_source = defaultdict(Counter)
    tool_sequences = defaultdict(list)
    tool_calls_by_hour = Counter()
    command_counts = Counter()
    command_failures = Counter()
    file_types = Counter()
    model_cost_totals = defaultdict(float)
    model_rollups = defaultdict(
        lambda: {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_tokens": 0,
            "cost": 0.0,
            "messages": 0,
        }
    )

    session_meta_map = {(meta.source, meta.session_id): meta for meta in session_metas}

    for event in sorted(events, key=lambda item: item.timestamp):
        local_ts = event.timestamp.astimezone(local_tz)
        date_key = local_ts.date().isoformat()
        day = daily_rollups[date_key]
        day["date"] = date_key
        day["label"] = local_ts.strftime("%m/%d")

        total_tokens = event.total
        cost = event.cost
        cost_breakdown = event.cost_breakdown

        source = source_rollups[event.source]
        source["source"] = event.source
        source["total_tokens"] += total_tokens
        source["uncached_input"] += event.uncached_input
        source["cache_read"] += event.cache_read
        source["cache_write"] += event.cache_write
        source["output"] += event.output
        source["reasoning"] += event.reasoning
        source["messages"] += event.activity_messages
        source["sessions"].add(event.session_id)
        source["models"][event.model] += max(1, event.activity_messages)
        source["token_capable"] = source["token_capable"] or total_tokens > 0
        source["cost"] += cost
        source["cost_input"] += cost_breakdown["input"]
        source["cost_cache_read"] += cost_breakdown["cache_read"]
        source["cost_cache_write"] += cost_breakdown["cache_write"]
        source["cost_output"] += cost_breakdown["output"]
        source["cost_reasoning"] += cost_breakdown["reasoning"]
        source["cost_cache_read_full"] += cost_breakdown["cache_read_full"]

        day["total_tokens"] += total_tokens
        day["uncached_input"] += event.uncached_input
        day["cache_read"] += event.cache_read
        day["cache_write"] += event.cache_write
        day["output"] += event.output
        day["reasoning"] += event.reasoning
        day["messages"] += event.activity_messages
        day["cost"] += cost
        day["cost_input"] += cost_breakdown["input"]
        day["cost_cache_read"] += cost_breakdown["cache_read"]
        day["cost_cache_write"] += cost_breakdown["cache_write"]
        day["cost_output"] += cost_breakdown["output"]
        day["cost_reasoning"] += cost_breakdown["reasoning"]
        day["source_totals"][event.source] += total_tokens
        day["cost_sources"][event.source] += cost

        hourly_source_totals[local_ts.hour][event.source] += total_tokens
        weekday_hour_heatmap[local_ts.weekday()][local_ts.hour] += total_tokens

        session = session_rollups[(event.source, event.session_id)]
        session["source"] = event.source
        session["session_id"] = event.session_id
        session["first_local"] = session["first_local"] or local_ts
        session["last_local"] = local_ts
        session["total_tokens"] += total_tokens
        session["uncached_input"] += event.uncached_input
        session["cache_read"] += event.cache_read
        session["cache_write"] += event.cache_write
        session["output"] += event.output
        session["reasoning"] += event.reasoning
        session["messages"] += event.activity_messages
        session["models"][event.model] += max(1, event.activity_messages)
        session["cost"] += cost

        model_cost_totals[event.model] += cost
        model_data = model_rollups[event.model]
        model_data["input_tokens"] += event.uncached_input
        model_data["cache_tokens"] += event.cache_read + event.cache_write
        model_data["output_tokens"] += event.output + event.reasoning
        model_data["cost"] += cost
        model_data["messages"] += event.activity_messages

    for tool_call in sorted(tool_calls, key=lambda item: item.timestamp):
        local_ts = tool_call.timestamp.astimezone(local_tz)
        date_key = local_ts.date().isoformat()
        day = daily_rollups[date_key]
        day["date"] = date_key
        day["label"] = local_ts.strftime("%m/%d")
        day["tool_calls"] += 1

        tool_counts_by_source[tool_call.source][tool_call.tool_name] += 1
        tool_sequences[(tool_call.source, tool_call.session_id)].append(tool_call.tool_name)
        tool_calls_by_hour[local_ts.hour] += 1

        session = session_rollups[(tool_call.source, tool_call.session_id)]
        session["source"] = tool_call.source
        session["session_id"] = tool_call.session_id
        session["first_local"] = session["first_local"] or local_ts
        session["last_local"] = session["last_local"] or local_ts
        session["first_local"] = min(session["first_local"], local_ts)
        session["last_local"] = max(session["last_local"], local_ts)
        session["tool_calls"] += 1

        if tool_call.file_path:
            file_types[Path(tool_call.file_path).suffix or "(none)"] += 1

        if tool_call.command:
            first_word = tool_call.command.split()[0] if tool_call.command.split() else "(empty)"
            command_counts[first_word] += 1
            if tool_call.exit_code is not None and tool_call.exit_code != 0:
                command_failures[first_word] += 1
                day["command_failures"] += 1
            else:
                day["command_successes"] += 1

    ordered_days = []
    cumulative_tokens = 0
    cumulative_cost = 0.0
    current_date = start_local.date()
    while current_date <= now_local.date():
        date_key = current_date.isoformat()
        day = daily_rollups[date_key]
        day["date"] = date_key
        day["label"] = current_date.strftime("%m/%d")
        cumulative_tokens += day["total_tokens"]
        cumulative_cost += day["cost"]
        ordered_days.append(
            {
                "date": day["date"],
                "label": day["label"],
                "total_tokens": day["total_tokens"],
                "uncached_input": day["uncached_input"],
                "cache_read": day["cache_read"],
                "cache_write": day["cache_write"],
                "output": day["output"],
                "reasoning": day["reasoning"],
                "messages": day["messages"],
                "source_totals": dict(day["source_totals"]),
                "cumulative_tokens": cumulative_tokens,
                "cost": _round_money(day["cost"]),
                "cost_sources": {key: _round_money(value) for key, value in day["cost_sources"].items()},
                "cost_cumulative": _round_money(cumulative_cost),
                "cost_input": _round_money(day["cost_input"]),
                "cost_cache_read": _round_money(day["cost_cache_read"]),
                "cost_cache_write": _round_money(day["cost_cache_write"]),
                "cost_output": _round_money(day["cost_output"]),
                "cost_reasoning": _round_money(day["cost_reasoning"]),
                "tool_calls": day["tool_calls"],
                "command_successes": day["command_successes"],
                "command_failures": day["command_failures"],
            }
        )
        current_date += timedelta(days=1)

    source_cards = []
    for source_name in sorted(source_rollups, key=_source_rank):
        source = source_rollups[source_name]
        source_cards.append(
            {
                "source": source_name,
                "total": source["total_tokens"],
                "uncached_input": source["uncached_input"],
                "cache_read": source["cache_read"],
                "cache_write": source["cache_write"],
                "output": source["output"],
                "reasoning": source["reasoning"],
                "sessions": len(source["sessions"]),
                "messages": source["messages"],
                "top_model": source["models"].most_common(1)[0][0] if source["models"] else "-",
                "token_capable": source["token_capable"],
                "cost": _round_money(source["cost"]),
                "cost_input": _round_money(source["cost_input"]),
                "cost_cache_read": _round_money(source["cost_cache_read"]),
                "cost_cache_write": _round_money(source["cost_cache_write"]),
                "cost_output": _round_money(source["cost_output"]),
                "cost_reasoning": _round_money(source["cost_reasoning"]),
                "cost_cache_read_full": _round_money(source["cost_cache_read_full"]),
            }
        )

    active_sessions = []
    for rollup in session_rollups.values():
        first_local = rollup["first_local"]
        last_local = rollup["last_local"]
        minutes = 0.0
        if first_local and last_local:
            minutes = round((last_local - first_local).total_seconds() / 60, 1)
        active_sessions.append(
            {
                "source": rollup["source"],
                "session_id": rollup["session_id"],
                "total": rollup["total_tokens"],
                "uncached_input": rollup["uncached_input"],
                "cache_read": rollup["cache_read"],
                "cache_write": rollup["cache_write"],
                "output": rollup["output"],
                "reasoning": rollup["reasoning"],
                "messages": rollup["messages"],
                "tool_calls": rollup["tool_calls"],
                "first_local": first_local.isoformat(timespec="minutes") if first_local else "-",
                "last_local": last_local.isoformat(timespec="minutes") if last_local else "-",
                "minutes": minutes,
                "top_model": rollup["models"].most_common(1)[0][0] if rollup["models"] else "-",
                "cost": _round_money(rollup["cost"]),
            }
        )

    active_sessions.sort(key=lambda item: (item["total"], item["cost"], item["tool_calls"]), reverse=True)
    top_sessions = active_sessions[:20]
    complexity_scatter = active_sessions[:50]

    grand_total = sum(day["total_tokens"] for day in ordered_days)
    grand_cost = sum(day["cost"] for day in ordered_days)
    grand_cache_read = sum(day["cache_read"] for day in ordered_days)
    grand_cache_write = sum(day["cache_write"] for day in ordered_days)
    grand_output = sum(day["output"] for day in ordered_days)
    grand_reasoning = sum(day["reasoning"] for day in ordered_days)
    cache_ratio = _percent(grand_cache_read + grand_cache_write, grand_total)
    token_capable_cards = [card for card in source_cards if card["token_capable"]]
    tracked_messages = sum(card["messages"] for card in token_capable_cards)
    session_tokens = [session["total"] for session in active_sessions if session["total"] > 0]
    session_minutes = [session["minutes"] for session in active_sessions if session["minutes"] > 0]
    session_costs = [session["cost"] for session in active_sessions if session["cost"] > 0]

    peak_day = max(ordered_days, key=lambda item: item["total_tokens"], default=None)
    cost_peak_day = max(ordered_days, key=lambda item: item["cost"], default=None)
    total_cache_read_full = sum(card["cost_cache_read_full"] for card in source_cards)
    total_cost_cache_read = sum(card["cost_cache_read"] for card in source_cards)
    cache_savings_usd = max(0.0, total_cache_read_full - total_cost_cache_read)
    cache_savings_ratio = _percent(cache_savings_usd, total_cache_read_full)

    combined_tool_counts = Counter()
    for counts in tool_counts_by_source.values():
        combined_tool_counts.update(counts)
    tool_ranking = [
        {
            "name": name,
            "count": count,
            "by_source": {source: tool_counts_by_source[source][name] for source in tool_counts_by_source},
        }
        for name, count in combined_tool_counts.most_common(30)
    ]

    bigram_counts = Counter()
    tool_degrees = Counter()
    for sequence in tool_sequences.values():
        for index in range(len(sequence) - 1):
            pair = (sequence[index], sequence[index + 1])
            bigram_counts[pair] += 1
            tool_degrees[pair[0]] += 1
            tool_degrees[pair[1]] += 1
    tool_bigrams = [
        {"from": source, "to": target, "count": count}
        for (source, target), count in bigram_counts.most_common(20)
    ]
    chord_tools = {name for name, _ in tool_degrees.most_common(8)}
    bigram_chord = {
        "nodes": [
            {"name": name, "value": tool_degrees[name]}
            for name in sorted(chord_tools, key=lambda item: (-tool_degrees[item], item))
        ],
        "links": [
            {"source": source, "target": target, "value": count}
            for (source, target), count in bigram_counts.most_common()
            if source in chord_tools and target in chord_tools
        ],
    }

    total_commands = sum(command_counts.values())
    successful_commands = sum(
        day["command_successes"] for day in ordered_days
    )
    top_commands = [
        {
            "command": command,
            "count": count,
            "failures": command_failures[command],
            "failure_rate": round(_percent(command_failures[command], count), 3),
        }
        for command, count in command_counts.most_common(20)
    ]
    daily_command_success = [
        {
            "date": day["date"],
            "label": day["label"],
            "successes": day["command_successes"],
            "failures": day["command_failures"],
            "total": day["command_successes"] + day["command_failures"],
        }
        for day in ordered_days
    ]

    project_rollups = defaultdict(lambda: {"project": "", "sessions": 0, "total_tokens": 0, "cost": 0.0, "tool_calls": 0})
    branch_activity = Counter()
    active_session_keys = {(session["source"], session["session_id"]) for session in active_sessions}
    for session in active_sessions:
        meta = session_meta_map.get((session["source"], session["session_id"]))
        project_name = (meta.project if meta else None) or "unknown"
        project = project_rollups[project_name]
        project["project"] = project_name
        project["sessions"] += 1
        project["total_tokens"] += session["total"]
        project["cost"] += session["cost"]
        project["tool_calls"] += session["tool_calls"]
    for meta in session_metas:
        if (meta.source, meta.session_id) in active_session_keys and meta.git_branch:
            branch_activity[meta.git_branch] += 1
    project_ranking = sorted(project_rollups.values(), key=lambda item: item["total_tokens"], reverse=True)[:20]

    hourly_rows = []
    for hour in range(24):
        hourly_rows.append({"hour": hour, **{source: hourly_source_totals[hour][source] for source in SOURCE_ORDER}})
    heatmap_rows = [{"weekday": WEEKDAYS[index], "values": [weekday_hour_heatmap[index][hour] for hour in range(24)]} for index in range(7)]

    max_daily_tokens = max((day["total_tokens"] for day in ordered_days), default=0)
    max_daily_messages = max((day["messages"] for day in ordered_days), default=0)
    max_daily_tools = max((day["tool_calls"] for day in ordered_days), default=0)
    max_daily_cost = max((day["cost"] for day in ordered_days), default=0.0)
    daily_productivity = []
    for day in ordered_days:
        score = (
            0.3 * _percent(day["total_tokens"], max_daily_tokens)
            + 0.2 * _percent(day["messages"], max_daily_messages)
            + 0.3 * _percent(day["tool_calls"], max_daily_tools)
            + 0.2 * _percent(day["cost"], max_daily_cost)
        )
        daily_productivity.append(
            {
                "date": day["date"],
                "label": day["label"],
                "score": round(score, 3),
                "tokens": day["total_tokens"],
                "messages": day["messages"],
                "tool_calls": day["tool_calls"],
                "cost": day["cost"],
            }
        )

    efficiency_daily = []
    for day in ordered_days:
        tracked_input = day["uncached_input"] + day["cache_read"]
        efficiency_daily.append(
            {
                "date": day["date"],
                "label": day["label"],
                "reasoning_ratio": round(_percent(day["reasoning"], day["total_tokens"]), 4),
                "cache_hit_rate": round(_percent(day["cache_read"], tracked_input), 4),
                "tokens_per_message": round(_percent(day["total_tokens"], day["messages"]), 2) if day["messages"] else 0,
            }
        )

    duration_buckets = [
        ("<5m", 0, 5),
        ("5-15m", 5, 15),
        ("15-30m", 15, 30),
        ("30-60m", 30, 60),
        (">60m", 60, float("inf")),
    ]
    duration_histogram = []
    for label, start, end in duration_buckets:
        count = sum(1 for session in active_sessions if start <= session["minutes"] < end)
        duration_histogram.append({"label": label, "count": count})

    sorted_minutes = sorted(session["minutes"] for session in active_sessions if session["minutes"] > 0)
    tokens_per_minute = [
        session["total"] / session["minutes"]
        for session in active_sessions
        if session["minutes"] > 0 and session["total"] > 0
    ]
    sorted_tools = sorted(session["tool_calls"] for session in active_sessions)
    latency_stats = {
        "median_session_minutes": round(median(sorted_minutes), 1) if sorted_minutes else 0.0,
        "p90_session_minutes": round(_percentile(sorted_minutes, 0.9), 1) if sorted_minutes else 0.0,
        "avg_tokens_per_minute": round(sum(tokens_per_minute) / len(tokens_per_minute), 1) if tokens_per_minute else 0.0,
        "median_tools_per_session": round(median(sorted_tools), 1) if sorted_tools else 0.0,
    }

    model_costs = sorted(
        [
            {
                "model": model,
                "cost": _round_money(stats["cost"]),
                "messages": stats["messages"],
                "input_tokens": stats["input_tokens"],
                "cache_tokens": stats["cache_tokens"],
                "output_tokens": stats["output_tokens"],
            }
            for model, stats in model_rollups.items()
            if stats["cost"] > 0
        ],
        key=lambda item: item["cost"],
        reverse=True,
    )
    top_models = model_costs[:5]
    max_input = max((item["input_tokens"] for item in top_models), default=1)
    max_output = max((item["output_tokens"] for item in top_models), default=1)
    max_cache = max((item["cache_tokens"] for item in top_models), default=1)
    max_cost = max((item["cost"] for item in top_models), default=1)
    max_messages = max((item["messages"] for item in top_models), default=1)
    model_radar = [
        {
            "name": item["model"],
            "input_tokens": item["input_tokens"],
            "output_tokens": item["output_tokens"],
            "cache_tokens": item["cache_tokens"],
            "cost": item["cost"],
            "messages": item["messages"],
            "normalized": [
                round(_percent(item["input_tokens"], max_input), 3),
                round(_percent(item["output_tokens"], max_output), 3),
                round(_percent(item["cache_tokens"], max_cache), 3),
                round(_percent(item["cost"], max_cost), 3),
                round(_percent(item["messages"], max_messages), 3),
            ],
        }
        for item in top_models
    ]

    recent_window = ordered_days[-7:] if ordered_days else []
    average_daily_burn = round(sum(day["cost"] for day in recent_window) / len(recent_window), 4) if recent_window else 0.0
    projected_total_30d = round(average_daily_burn * 30, 2)
    projected_cumulative = ordered_days[-1]["cost_cumulative"] if ordered_days else 0.0
    projection = []
    for offset in range(1, 31):
        future_date = now_local.date() + timedelta(days=offset)
        projected_cumulative += average_daily_burn
        projection.append(
            {
                "date": future_date.isoformat(),
                "label": future_date.strftime("%m/%d"),
                "projected_daily_cost": average_daily_burn,
                "projected_cumulative_cost": round(projected_cumulative, 4),
            }
        )

    daily_cost_per_tool_call = []
    for day in ordered_days:
        value = round(day["cost"] / day["tool_calls"], 4) if day["tool_calls"] else 0.0
        daily_cost_per_tool_call.append(
            {
                "date": day["date"],
                "label": day["label"],
                "value": value,
                "cost": day["cost"],
                "tool_calls": day["tool_calls"],
            }
        )

    peak_markers = [
        {"date": day["date"], "label": day["label"], "total_tokens": day["total_tokens"], "cumulative_tokens": day["cumulative_tokens"]}
        for day in sorted(
            [item for item in ordered_days if item["total_tokens"] > 0],
            key=lambda item: item["total_tokens"],
            reverse=True,
        )[:4]
    ]
    peak_markers.sort(key=lambda item: item["date"])

    source_notes = [
        f"{card['source']} 主力模型 {card['top_model']}，{card['sessions']} 个 session，{card['messages']} 条消息。"
        for card in source_cards
    ]
    source_notes_en = [
        f"{card['source']} primary model {card['top_model']}, {card['sessions']} sessions, {card['messages']} messages."
        for card in source_cards
    ]
    jokes = []
    jokes_en = []
    if cache_ratio > 0.75:
        jokes.append("缓存占比高得像给模型办了无限次回访卡。")
        jokes_en.append("Cache ratio so high it's like the model has an unlimited loyalty card.")
    if peak_day and peak_day["total_tokens"] > 300_000_000:
        jokes.append("峰值日像给 Agent 背后装了双涡轮。")
        jokes_en.append("Peak day looks like the Agent had twin turbos installed.")
    if any(not card["token_capable"] for card in source_cards):
        jokes.append("有些来源很勤奋，但没有留下完整 token 小票。")
        jokes_en.append("Some sources work hard but don't leave a full token receipt.")

    _tool_total = sum(combined_tool_counts.values())
    _cmd_rate = _percent(successful_commands, total_commands)
    _peak_label = (peak_day or {}).get("label", "-")
    _peak_tokens = (peak_day or {}).get("total_tokens", 0)
    _cache_total = grand_cache_read + grand_cache_write

    story_narrative = [
        {"icon": "fa-bolt", "text": f"统计窗口内共处理 {grand_total:,} tokens，估算成本 ${grand_cost:,.2f}。"},
        {"icon": "fa-fire", "text": f"峰值日是 {_peak_label}, 当天跑了 {_peak_tokens:,} tokens。"},
        {"icon": "fa-database", "text": f"缓存读写共 {_cache_total:,} tokens，省下约 ${cache_savings_usd:,.2f}。"},
        {"icon": "fa-wrench", "text": f"全局工具调用 {_tool_total:,} 次，命令成功率 {_cmd_rate:.1%}。"},
    ]
    story_narrative_en = [
        {"icon": "fa-bolt", "text": f"Processed {grand_total:,} tokens in this window, estimated cost ${grand_cost:,.2f}."},
        {"icon": "fa-fire", "text": f"Peak day was {_peak_label}, with {_peak_tokens:,} tokens."},
        {"icon": "fa-database", "text": f"Cache read/write totalled {_cache_total:,} tokens, saving ~${cache_savings_usd:,.2f}."},
        {"icon": "fa-wrench", "text": f"Total tool calls: {_tool_total:,}, command success rate {_cmd_rate:.1%}."},
    ]
    tempo_notes = []
    tempo_notes_en = []
    hottest_hour = max(hourly_rows, key=lambda row: sum(row.get(source, 0) for source in SOURCE_ORDER), default=None)
    if hottest_hour:
        tempo_notes.append(f"最热小时是 {hottest_hour['hour']:02d}:00。")
        tempo_notes_en.append(f"Hottest hour is {hottest_hour['hour']:02d}:00.")
    if cost_peak_day:
        tempo_notes.append(f"最烧钱的一天是 {cost_peak_day['label']}，花了 ${cost_peak_day['cost']:.2f}。")
        tempo_notes_en.append(f"Most expensive day was {cost_peak_day['label']}, spent ${cost_peak_day['cost']:.2f}.")

    token_sankey = _build_sankey(
        source_cards,
        [
            ("uncached_input", "Uncached Input"),
            ("cache_read", "Cache Read"),
            ("cache_write", "Cache Write"),
            ("output", "Output"),
            ("reasoning", "Reasoning"),
        ],
    )
    cost_sankey = _build_sankey(
        source_cards,
        [
            ("cost_input", "Input Cost"),
            ("cost_cache_read", "Cache Read"),
            ("cost_cache_write", "Cache Write"),
            ("cost_output", "Output"),
            ("cost_reasoning", "Reasoning"),
        ],
    )

    # ── Extended analytics: turn durations, task events, cursor codegen, claude stats ──
    task_events = task_events or []
    turn_durations = turn_durations or []
    cursor_codegen = cursor_codegen or []
    cursor_commits = cursor_commits or []
    claude_stats_cache = claude_stats_cache or {}

    # Turn duration stats (response time analysis)
    dur_by_source = defaultdict(list)
    for td in turn_durations:
        dur_by_source[td.source].append(td.duration_ms)
    dur_all = [td.duration_ms for td in turn_durations]
    sorted_dur = sorted(dur_all)

    turn_duration_stats = {
        "total_turns": len(dur_all),
        "median_ms": round(median(sorted_dur)) if sorted_dur else 0,
        "p90_ms": round(_percentile(sorted_dur, 0.9)) if sorted_dur else 0,
        "p99_ms": round(_percentile(sorted_dur, 0.99)) if sorted_dur else 0,
        "by_source": {},
    }
    for src, vals in dur_by_source.items():
        sv = sorted(vals)
        turn_duration_stats["by_source"][src] = {
            "count": len(sv),
            "median_ms": round(median(sv)),
            "p90_ms": round(_percentile(sv, 0.9)),
        }

    # Duration histogram buckets (in seconds)
    dur_buckets = [
        ("<5s", 0, 5000),
        ("5-15s", 5000, 15000),
        ("15-30s", 15000, 30000),
        ("30-60s", 30000, 60000),
        ("1-5m", 60000, 300000),
        (">5m", 300000, float("inf")),
    ]
    turn_dur_histogram = []
    for label, lo, hi in dur_buckets:
        count = sum(1 for d in dur_all if lo <= d < hi)
        turn_dur_histogram.append({"label": label, "count": count})

    # Daily turn duration (median per day)
    daily_dur = defaultdict(list)
    for td in turn_durations:
        local_ts = td.timestamp.astimezone(local_tz)
        daily_dur[local_ts.date().isoformat()].append(td.duration_ms)
    daily_turn_durations = []
    current_date = start_local.date()
    while current_date <= now_local.date():
        dk = current_date.isoformat()
        vals = daily_dur.get(dk, [])
        daily_turn_durations.append({
            "date": dk,
            "label": current_date.strftime("%m/%d"),
            "median_ms": round(median(sorted(vals))) if vals else 0,
            "count": len(vals),
        })
        current_date += timedelta(days=1)

    # Task events (Codex task success rate)
    started_count = sum(1 for te in task_events if te.event_type == "started")
    complete_count = sum(1 for te in task_events if te.event_type == "complete")
    task_stats = {
        "started": started_count,
        "completed": complete_count,
        "completion_rate": round(_percent(complete_count, started_count), 3),
    }

    # Cursor code generation by model
    codegen_by_model = Counter()
    codegen_by_ext = Counter()
    codegen_by_source = Counter()
    codegen_daily = defaultdict(int)
    for cg in cursor_codegen:
        codegen_by_model[cg.model] += 1
        if cg.file_extension:
            codegen_by_ext[cg.file_extension] += 1
        codegen_by_source[cg.gen_source] += 1
        local_ts = cg.timestamp.astimezone(local_tz)
        codegen_daily[local_ts.date().isoformat()] += 1

    cursor_codegen_data = {
        "total": len(cursor_codegen),
        "by_model": [{"model": m, "count": c} for m, c in codegen_by_model.most_common(10)],
        "by_extension": [{"ext": e, "count": c} for e, c in codegen_by_ext.most_common(15)],
        "by_source": [{"source": s, "count": c} for s, c in codegen_by_source.most_common()],
        "daily": [
            {"date": dk, "label": dk[5:].replace("-", "/"), "count": codegen_daily.get(dk, 0)}
            for dk in (d["date"] for d in ordered_days)
        ],
    }

    # Cursor AI contribution (scored commits)
    total_ai_added = sum(c.composer_added + c.tab_added for c in cursor_commits)
    total_human_added = sum(c.human_added for c in cursor_commits)
    total_ai_deleted = sum(c.composer_deleted + c.tab_deleted for c in cursor_commits)
    total_human_deleted = sum(c.human_deleted for c in cursor_commits)
    total_lines = total_ai_added + total_human_added + total_ai_deleted + total_human_deleted
    ai_contribution_data = {
        "total_commits": len(cursor_commits),
        "ai_lines_added": total_ai_added,
        "human_lines_added": total_human_added,
        "ai_lines_deleted": total_ai_deleted,
        "human_lines_deleted": total_human_deleted,
        "ai_ratio": round(_percent(total_ai_added + total_ai_deleted, total_lines), 3),
        "commits": [
            {
                "hash": c.commit_hash[:8],
                "ai_added": c.composer_added + c.tab_added,
                "human_added": c.human_added,
                "ai_deleted": c.composer_deleted + c.tab_deleted,
                "human_deleted": c.human_deleted,
            }
            for c in sorted(cursor_commits, key=lambda x: (x.composer_added + x.tab_added), reverse=True)[:20]
        ],
    }

    # Claude stats cache (hourly distribution, longest session)
    claude_stats_data = {}
    if claude_stats_cache:
        claude_stats_data = {
            "hour_counts": claude_stats_cache.get("hour_counts", []),
            "total_sessions": claude_stats_cache.get("total_sessions", 0),
            "total_messages": claude_stats_cache.get("total_messages", 0),
            "longest_session": claude_stats_cache.get("longest_session"),
            "first_session_date": claude_stats_cache.get("first_session_date"),
        }

    return {
        "range": {
            "start_local": start_local.isoformat(timespec="minutes"),
            "end_local": now_local.isoformat(timespec="minutes"),
            "day_count": len(ordered_days),
        },
        "totals": {
            "grand_total": grand_total,
            "grand_cost": round(grand_cost, 2),
            "cache_read": grand_cache_read,
            "cache_write": grand_cache_write,
            "output": grand_output,
            "reasoning": grand_reasoning,
            "cache_ratio": cache_ratio,
            "tracked_session_count": sum(card["sessions"] for card in token_capable_cards),
            "average_per_day": round(grand_total / max(1, len(ordered_days))),
            "median_session_tokens": round(median(session_tokens)) if session_tokens else 0,
            "median_session_minutes": round(median(session_minutes), 1) if session_minutes else 0.0,
            "median_session_cost": round(median(session_costs), 4) if session_costs else 0.0,
            "peak_day_label": peak_day["label"] if peak_day else "-",
            "peak_day_total": peak_day["total_tokens"] if peak_day else 0,
            "cost_peak_day_label": cost_peak_day["label"] if cost_peak_day else "-",
            "cost_peak_day_total": round(cost_peak_day["cost"], 4) if cost_peak_day else 0.0,
            "average_cost_per_day": round(grand_cost / max(1, len(ordered_days)), 2),
            "cost_per_message": round(grand_cost / max(1, tracked_messages), 4),
            "cost_input": round(sum(day["cost_input"] for day in ordered_days), 2),
            "cost_cache_read": round(sum(day["cost_cache_read"] for day in ordered_days), 2),
            "cost_cache_write": round(sum(day["cost_cache_write"] for day in ordered_days), 2),
            "cost_output": round(sum(day["cost_output"] for day in ordered_days), 2),
            "cost_reasoning": round(sum(day["cost_reasoning"] for day in ordered_days), 2),
            "cache_savings_usd": round(cache_savings_usd, 2),
            "cache_savings_ratio": cache_savings_ratio,
            "tool_call_total": sum(combined_tool_counts.values()),
            "project_count": len(project_rollups),
            "avg_daily_burn": round(average_daily_burn, 2),
            "burn_rate_projection_30d": projected_total_30d,
        },
        "source_cards": source_cards,
        "days": ordered_days,
        "top_sessions": top_sessions,
        "tooling": {
            "ranking": tool_ranking,
            "tool_bigrams": tool_bigrams,
            "bigram_chord": bigram_chord,
            "total_tool_calls": sum(combined_tool_counts.values()),
        },
        "commands": {
            "summary": {
                "success_rate": round(_percent(successful_commands, total_commands), 3),
                "total_commands": total_commands,
            },
            "top_commands": top_commands,
            "daily_success": daily_command_success,
        },
        "projects": {
            "ranking": [
                {
                    "project": item["project"],
                    "sessions": item["sessions"],
                    "total_tokens": item["total_tokens"],
                    "cost": round(item["cost"], 4),
                    "tool_calls": item["tool_calls"],
                }
                for item in project_ranking
            ],
            "branch_activity": [{"branch": branch, "sessions": count} for branch, count in branch_activity.most_common(20)],
            "file_types": [{"extension": extension, "count": count} for extension, count in file_types.most_common(20)],
            "count": len(project_rollups),
        },
        "working_patterns": {
            "heatmap": heatmap_rows,
            "hourly_source_totals": hourly_rows,
            "hourly_tool_density": [{"hour": hour, "count": tool_calls_by_hour[hour]} for hour in range(24)],
            "daily_productivity": daily_productivity,
            "source_radar": [
                {
                    "name": card["source"],
                    "total_tokens": card["total"],
                    "cache_total": card["cache_read"] + card["cache_write"],
                    "output_total": card["output"] + card["reasoning"],
                    "sessions": card["sessions"],
                }
                for card in source_cards
                if card["token_capable"]
            ],
            "timeline": {
                "days": [
                    {
                        "date": day["date"],
                        "label": day["label"],
                        "total_tokens": day["total_tokens"],
                        "cumulative_tokens": day["cumulative_tokens"],
                    }
                    for day in ordered_days
                ],
                "peak_markers": peak_markers,
            },
        },
        "efficiency_metrics": {
            "daily": efficiency_daily,
            "summary": {
                "avg_reasoning_ratio": round(sum(day["reasoning_ratio"] for day in efficiency_daily) / len(efficiency_daily), 4)
                if efficiency_daily
                else 0.0,
                "avg_cache_hit_rate": round(sum(day["cache_hit_rate"] for day in efficiency_daily) / len(efficiency_daily), 4)
                if efficiency_daily
                else 0.0,
                "avg_tokens_per_message": round(sum(day["tokens_per_message"] for day in efficiency_daily) / len(efficiency_daily), 1)
                if efficiency_daily
                else 0.0,
            },
        },
        "session_deep_dive": {
            "duration_histogram": duration_histogram,
            "complexity_scatter": [
                {
                    "source": session["source"],
                    "session_id": session["session_id"],
                    "duration_minutes": session["minutes"],
                    "total_tokens": session["total"],
                    "cache_total": session["cache_read"] + session["cache_write"],
                    "tool_calls": session["tool_calls"],
                    "cost": session["cost"],
                }
                for session in complexity_scatter
            ],
            "latency_stats": latency_stats,
        },
        "trend_analysis": {
            "model_costs": model_costs,
            "token_sankey": token_sankey,
            "cost_sankey": cost_sankey,
            "burn_rate_30d": {
                "average_daily_cost": average_daily_burn,
                "projected_total_30d": projected_total_30d,
                "history": [
                    {"date": day["date"], "label": day["label"], "cost": day["cost"], "cumulative_cost": day["cost_cumulative"]}
                    for day in ordered_days
                ],
                "projection": projection,
            },
            "daily_cost_per_tool_call": daily_cost_per_tool_call,
            "model_radar": model_radar,
        },
        "story": {
            "narrative": story_narrative,
            "jokes": jokes,
            "source_notes": source_notes,
            "tempo_notes": tempo_notes,
            "narrative_en": story_narrative_en,
            "jokes_en": jokes_en,
            "source_notes_en": source_notes_en,
            "tempo_notes_en": tempo_notes_en,
        },
        "extended": {
            "turn_durations": {
                "stats": turn_duration_stats,
                "histogram": turn_dur_histogram,
                "daily": daily_turn_durations,
            },
            "task_events": task_stats,
            "cursor_codegen": cursor_codegen_data,
            "ai_contribution": ai_contribution_data,
            "claude_stats": claude_stats_data,
        },
    }
