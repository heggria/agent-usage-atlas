# Agent Usage Atlas

Generate a rich, interactive HTML dashboard from your local AI coding agent logs.

一个从本地 AI 编程 Agent 日志生成可视化仪表盘的工具。

## Supported Agents

| Agent | Token Tracking | Tool Call Tracking | Session Meta |
|-------|:-:|:-:|:-:|
| [Codex CLI](https://github.com/openai/codex) | ✅ | ✅ | ✅ |
| [Claude Code](https://docs.anthropic.com/en/docs/claude-code) | ✅ | ✅ | ✅ |
| [Cursor](https://www.cursor.com/) | Activity only | — | — |

## Features

- **Token & cost breakdown** by source, model, day, and session
- **Tool call analytics** — ranking, bigram sequences, chord diagram
- **Working pattern heatmap** — hour × weekday activity distribution
- **Session deep-dive** — duration histogram, complexity scatter
- **Cost projection** — 30-day burn rate forecast
- **Cache efficiency** — hit rate tracking and savings estimate
- **Zero dependencies** — pure Python standard library

## Installation

```bash
# Clone and run directly
git clone https://github.com/anthropics/agent-usage-atlas.git
cd agent-usage-atlas
python generate.py

# Or install as a CLI tool
pip install .
agent-usage-atlas
```

## Usage

```bash
# Default: last 30 days, output to ./reports/dashboard.html
python generate.py

# Last 7 days
python generate.py --days 7

# Start live dashboard on localhost
agent-usage-atlas --serve --interval 5

# Open live dashboard directly after starting
agent-usage-atlas --serve --port 8765 --host 127.0.0.1 --interval 5 --open

# Custom start date
python generate.py --since 2026-03-01

# Custom output path and auto-open in browser
python generate.py --output /tmp/dashboard.html --open
```

### CLI Options

| Flag | Description | Default |
|------|-------------|---------|
| `--days N` | Include the last N days | `30` |
| `--since YYYY-MM-DD` | Custom start date (overrides `--days`) | — |
| `--output PATH` | Output HTML file path | `./reports/dashboard.html` |
| `--open` | Open in browser after generation | off |
| `--serve` | Start local web dashboard (default host `127.0.0.1`, port `8765`) instead of generating file | off |
| `--host` | Host for `--serve` mode | `127.0.0.1` |
| `--port` | Port for `--serve` mode | `8765` |
| `--interval` | SSE stream polling interval in seconds (server-side loop) for `--serve` mode | `5` |

## How It Works

The tool reads local log files that AI coding agents write to `~/.codex/`, `~/.claude/`, and `~/.cursor/`. All data stays local — nothing is sent to any server.

### Live mode endpoints

- `GET /api/dashboard?days=30` -> returns JSON payload (compat/debug endpoint)
- `GET /api/dashboard?since=2026-03-01` -> query window override
- `GET /api/dashboard/stream` -> SSE stream (default frontend consumer in serve mode)

## Screenshot

<!-- TODO: Add screenshot -->

## License

[MIT](LICENSE)
