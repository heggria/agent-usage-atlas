# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

Agent Usage Atlas generates an interactive HTML dashboard from local AI coding agent logs (~/.codex/, ~/.claude/, ~/.cursor/). It parses JSONL log files and SQLite databases, aggregates token/cost/tool-call data, and renders a single-file HTML dashboard with ECharts visualizations. Zero external Python dependencies — stdlib only.

## Commands

```bash
# Generate static dashboard (reads local agent logs)
python -m agent_usage_atlas

# Generate with custom date range
python -m agent_usage_atlas --days 7
python -m agent_usage_atlas --since 2026-03-01

# Start live dashboard server (SSE-based auto-refresh)
python -m agent_usage_atlas --serve --interval 5 --open

# Install as CLI tool
pip install .
agent-usage-atlas
```

There are no tests, no linter config, and no build step beyond `pip install .`.

## Architecture

The pipeline is strictly linear: **parse → aggregate → render**. All source lives under `src/agent_usage_atlas/` (standard src layout).

- **`cli.py`** — CLI entry point and orchestrator (was `generate.py`). `build_dashboard_payload()` is the core function that drives both static generation and the live server. Returns a dict consumed by both `build_html()` and the JSON API.

- **`parsers.py`** — Three parallel parser families (Codex, Claude, Cursor), each producing `UsageEvent`, `ToolCall`, and/or `SessionMeta` lists. Codex uses cumulative-delta token counting (subtracts previous snapshot). Claude deduplicates by (session_id, message_id). Cursor only tracks activity message counts (no token granularity).

- **`models.py`** — `UsageEvent`, `ToolCall`, `SessionMeta` dataclasses. Contains model pricing table (`_P` dict) and cost calculation logic. `_gp()` does fuzzy model name matching to pricing tiers. Pricing is per-1M-tokens as `(input, cache_read, cache_write, output, reasoning)`.

- **`aggregation.py`** — `aggregate()` takes parsed data and produces the full dashboard payload dict. Computes source rollups, daily rollups, session rollups, tool bigrams, chord diagram data, Sankey flows, burn rate projections, heatmaps, and narrative text (in Chinese).

- **`template.py`** — `build_html()` returns a complete self-contained HTML string. The entire frontend (CSS, JS, ECharts charts) lives as a Python string in `_template()`. Data is injected via `__DATA__` / `__POLL_MS__` placeholder replacement. The HTML uses `zh-CN` locale with Chinese UI text.

- **`server.py`** — stdlib `http.server` based live server. Three endpoints: `/` (HTML), `/api/dashboard` (JSON with ETag), `/api/dashboard/stream` (SSE). The SSE loop re-runs the full parse→aggregate pipeline each cycle, only sending data when the ETag changes.

## Key Design Decisions

- The dashboard payload dict is the single contract between backend and frontend. Every chart reads from this same structure.
- All timestamps are converted to local timezone for display; parsing happens in UTC.
- `template.py` is intentionally one giant string — the HTML file must be fully self-contained (no local asset files). External CDN deps: ECharts and FontAwesome.
- Narrative/story text in `aggregation.py` is in Chinese.
