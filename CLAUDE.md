# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

Agent Usage Atlas (v0.3.1) generates an interactive HTML dashboard from local AI coding agent logs (~/.codex/, ~/.claude/, ~/.cursor/, Hermit kernel). It parses JSONL log files and SQLite databases, aggregates token/cost/tool-call data, and renders an HTML dashboard with ECharts visualizations. Requires Python >= 3.10. Zero external runtime dependencies — stdlib only.

## Commands

```bash
# Generate static dashboard (reads local agent logs)
python -m agent_usage_atlas

# Generate with custom date range
python -m agent_usage_atlas --days 7
python -m agent_usage_atlas --since 2026-03-01

# Start live dashboard server (SSE-based auto-refresh)
python -m agent_usage_atlas --serve --interval 5 --open

# Start MCP stdio server (for use as an MCP tool provider)
python -m agent_usage_atlas mcp

# Install as CLI tool
pip install .
agent-usage-atlas
```

Dev tooling is configured in `pyproject.toml` via optional dependencies (`pip install .[dev]`): `pytest>=8.0`, `ruff>=0.9`, `mypy>=1.10`. Ruff is set to `line-length = 120` targeting Python 3.10. There is no build step beyond `pip install .`.

## Architecture

The pipeline is strictly linear: **parse → aggregate → render**. All source lives under `src/agent_usage_atlas/` (standard src layout).

- **`cli.py`** — CLI entry point and orchestrator (was `generate.py`). `build_dashboard_payload()` is the core function that drives both static generation and the live server. Returns a dict consumed by both `build_html()` and the JSON API.

- **`parsers/`** — Parser package with four parallel parser families, each producing `UsageEvent`, `ToolCall`, `SessionMeta`, and/or `UserMessage` lists:
  - `__init__.py` — Orchestrator. `parse_all()` runs all four parsers concurrently via `ThreadPoolExecutor` (max 5 workers), merges results into a single `ParseResult`, and tracks whether any data changed via `all_caches_hit()`. Uses a fixed 90-day parse window so result caches survive user-initiated date range switches.
  - `_base.py` — Shared parser infrastructure: thread-safe JSONL file reader with LRU cache (`_read_json_lines()`), two-tier result caching (file-signature-based `result_cache_get/set` to skip re-parsing when files are unchanged, plus a rescan interval to avoid repeated `rglob`), timestamp parsing (`_ts()` supporting ISO 8601, Unix epochs, and git-style dates), and safe integer coercion (`_si()`).
  - `codex.py` — Codex log parser. Uses cumulative-delta token counting (subtracts previous snapshot from current to derive per-event usage).
  - `claude.py` — Claude Code log parser. Reads `~/.claude/projects/**/*.jsonl`. Deduplicates events by `(session_id, message_id)`, keeping the highest token counts. Per-file incremental cache avoids re-parsing unchanged files. Also parses `stats-cache.json` for daily activity summaries.
  - `cursor.py` — Cursor log parser. Tracks activity message counts only (no per-token granularity).
  - `hermit.py` — Hermit agent log parser. Reads SQLite databases (`state.db`) and session JSON files from `~/.hermit/`, `~/.hermit-test/`, and `~/.hermit-dev/`. Parses conversations (token totals), receipts (tool call actions mapped via `_ACTION_MAP`), tasks (session metadata), and user messages. Scans archived/backup DB copies and supplements DB events with cache token data from session JSONs. Cross-home deduplication prevents double-counting when multiple Hermit directories track the same API calls.

- **`models.py`** — Core data classes and pricing logic. Eight dataclasses: `UsageEvent` (token counts + auto-calculated cost), `ToolCall`, `SessionMeta`, `TurnDuration`, `TaskEvent`, `CodeGenRecord`, `UserMessage`, `ScoredCommit`, plus a `ParseResult` container that aggregates lists of all types with a `merge()` method. Pricing uses a `PricingTier` NamedTuple `(input, cache_read, cache_write, output, reasoning)` per-1M-tokens. The `_P` dict is built by `_build_pricing()`: loads bundled `data/pricing.json`, merges user overrides from `~/.config/agent-usage-atlas/pricing.json`, falls back to `_FALLBACK_P` on error. `_gp()` resolves a model name to a `PricingTier` via prefix matching (longest match wins with word-boundary check, then substring fallback) using `_P_SORTED`. Also provides formatting helpers: `fmt_int()`, `fmt_usd()`, `fmt_short()`.

- **`aggregation/`** — Aggregation package. `__init__.py` exposes the top-level `aggregate()` function, which calls `build_context()` to perform a single pass over events and tool_calls, producing a shared `AggContext` dataclass (`_context.py`). `AggContext` holds all precomputed rollups (source, daily, session, hourly/heatmap, tool, model indexes, grand totals, active sessions) and is passed read-only to each submodule's `compute()` function:
  - `_context.py` — `AggContext` dataclass and `build_context()` single-pass builder. Also provides utility functions (`_round_money`, `_percent`, `_percentile`) and constants (`SOURCE_ORDER`, `WEEKDAYS`).
  - `totals.py` — source rollups and summary cards
  - `daily.py` — daily cost/token rollups
  - `sessions.py` — session rollups and deep-dive analysis
  - `tooling.py` — tool bigrams, chord diagram data, and command stats
  - `patterns.py` — working-hour heatmaps and usage patterns
  - `trends.py` — trend analysis, efficiency metrics, and token burn projections
  - `story.py` — narrative text generation (in Chinese)
  - `prompts.py` — prompt quality analysis and vague-prompt detection
  - `insights.py` — behavioral insights engine with 12 rule-based detectors (marathon sessions, model mismatch, low cache rate, vague prompt waste, tool-heavy sessions, off-hours usage, budget alerts, single-source dominance, command failure rate, context growth, CUSUM cost-anomaly detection, model efficiency ranking); returns severity-tagged suggestions in Chinese and English
  - `projects.py` — project-level rollups: top-20 project ranking by total tokens (with session count, cost, tool calls), top-20 git branch activity, file type distribution, and project count
  - `extended.py` — extended/supplementary metrics

- **`builder.py`** — `build_html()` returns a complete self-contained HTML string. Reads separate source files from `frontend/` and assembles them at build time via placeholder substitution (`__CSS__`, `__JS__`, `__DATA__`, `__POLL_MS__`). JS files are concatenated in dependency order: `lib/` → `components/` → `charts/` → `sections/`.

- **`frontend/`** — Frontend source directory (not served directly; assembled into a single HTML string by `builder.py`):
  - `index.html` — HTML skeleton with `__CSS__` and `__JS__` placeholders. Uses `zh-CN` locale.
  - `styles/main.css` — All CSS including dark/light themes, responsive breakpoints, animations.
  - `lib/` — Shared JS infrastructure loaded first:
    - `store.js` — Global state: dashboard data (`__DATA__`), range/date filters with localStorage persistence, live-mode flags, ETag-based change detection via `setDashboard()`.
    - `sse.js` — SSE client (`startSseDashboard()`) with automatic polling fallback, toast notifications, and connection status badge.
    - `utils.js` — Formatters (`fmtUSD`, `fmtShort`, `fmtInt`, `fmtPct`), theme-aware color palettes (`C` proxy for dark/light), HTML escaping, number transition animations (`animateNum()`).
    - `i18n.js` — Translation strings and `t()` helper (zh-CN / en locale).
    - `charts.js`, `chart-factories.js` — Shared ECharts configuration helpers and chart initialization utilities.
  - `components/` — DOM-rendering modules: `Hero.js`, `SourceCards.js`, `CostCards.js`, `Story.js`, `SessionTable.js`, `VaguePrompts.js`, `ExpensivePrompts.js`, `InsightCards.js`.
  - `charts/` — 30+ individual ECharts chart modules (one per chart).
  - `sections/main.js` — Dashboard boot, render orchestration, section collapse/expand, lazy chart loading, quick-nav.

- **`renderers/`** — Output renderers: `html.py`, `csv_out.py`, `json_out.py` for different export formats.

- **`commands/`** — CLI subcommands registered via `add_parser(subparsers)` pattern:
  - `generate.py` — Default subcommand: build static HTML dashboard.
  - `serve.py` — Start the live SSE-based dashboard server.
  - `export.py` — Export dashboard data in CSV or JSON format.
  - `billing.py` — Cost/billing analysis subcommand.
  - `mcp.py` — **MCP (Model Context Protocol) stdio server**. Invoked via `agent-usage-atlas mcp`. Reads JSON-RPC requests from stdin, writes responses to stdout. Implements the MCP protocol (`initialize`, `tools/list`, `tools/call`, `ping`). Exposes four tools that query the dashboard payload via `build_dashboard_payload()`:
    - `get_daily_stats` — Daily token/cost stats for recent N days.
    - `get_cost_summary` — Total cost breakdown by source and model.
    - `get_session_stats` — Top sessions ranked by cost.
    - `get_model_usage` — Token and cost breakdown by model.

- **`server.py`** — `ThreadingHTTPServer`-based live server with five routes: `/` (HTML), `/api/dashboard` (JSON with ETag/304), `/api/dashboard/stream` (SSE), `/health` (status check), and `/favicon.ico` (204). Payloads are served from an LRU cache (max 8 entries) keyed by `(days, since)` and invalidated by a file-signature check (mtime, size, count across all log files; file list rescanned every 30 s). A background daemon thread (`_bg_precompute`) proactively refreshes the cache on a timer. SSE streams are capped at 10 concurrent connections (503 on overflow) and send heartbeats every 15 s. Single-instance enforcement via file lock (`~/.cache/agent-usage-atlas/server.lock`) with automatic stale-process cleanup and port reclamation via `lsof`. JSON and SSE endpoints accept `days`, `since`, and `interval` query parameters.

## Key Design Decisions

- The dashboard payload dict is the single contract between backend and frontend. Every chart reads from this same structure.
- All timestamps are converted to local timezone for display; parsing happens in UTC.
- The frontend lives in `frontend/` as separate HTML, JS, and CSS files. `builder.py` assembles them into the final self-contained HTML output. External CDN deps: ECharts and FontAwesome.
- Narrative/story text in `aggregation/story.py` is in Chinese.
- `AggContext` (in `aggregation/_context.py`) is populated once via a single pass over all events and tool_calls, then shared read-only across all aggregation submodules. This avoids redundant recomputation of rollups and grand totals.
