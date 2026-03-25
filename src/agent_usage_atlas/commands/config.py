"""Configuration inspector -- pricing, log paths, cache status, version."""

from __future__ import annotations

import os
import time
from pathlib import Path

from ._ansi import bold, cyan, dim, green, red, yellow

# ── Subcommand registration ────────────────────────────────────────────


def add_parser(subparsers):
    parser = subparsers.add_parser(
        "config",
        help="Show configuration: pricing, log paths, cache status, version",
    )
    parser.add_argument(
        "--pricing",
        action="store_true",
        help="Show model pricing table",
    )
    parser.add_argument(
        "--paths",
        action="store_true",
        help="Show log file paths and sizes",
    )
    parser.add_argument(
        "--cache",
        action="store_true",
        help="Show cache status",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Show version info",
    )
    parser.add_argument(
        "--health",
        action="store_true",
        help="Show system health check (log dirs, cache freshness, server lock)",
    )
    parser.set_defaults(func=run)
    return parser


# ── Helpers ─────────────────────────────────────────────────────────────


def _fmt_bytes(n: int) -> str:
    """Format byte count to human-readable size."""
    if n >= 1 << 30:
        return f"{n / (1 << 30):.1f} GB"
    if n >= 1 << 20:
        return f"{n / (1 << 20):.1f} MB"
    if n >= 1 << 10:
        return f"{n / (1 << 10):.1f} KB"
    return f"{n} B"


def _count_files(directory: Path) -> tuple[int, int]:
    """Count files and total size under a directory. Returns (count, total_bytes)."""
    count = 0
    total = 0
    try:
        for root, _dirs, files in os.walk(directory):
            for f in files:
                fp = Path(root) / f
                try:
                    total += fp.stat().st_size
                    count += 1
                except OSError:
                    pass
    except OSError:
        pass
    return count, total


def _section_header(title: str) -> None:
    print()
    print(bold(cyan(f"-- {title} " + "-" * max(0, 60 - len(title) - 4))))


def _path_indicator(path: Path) -> str:
    """Return a colored status symbol for a path."""
    if not path.exists():
        return red("✗")
    if path.is_dir():
        count, _ = _count_files(path)
        if count == 0:
            return yellow("⚠")
        return green("✓")
    # File
    try:
        if path.stat().st_size == 0:
            return yellow("⚠")
    except OSError:
        pass
    return green("✓")


def _size_bar(size: int, max_size: int, width: int = 12) -> str:
    """Render a proportional bar for size relative to max_size."""
    if max_size == 0:
        filled = 0
    else:
        filled = round(width * size / max_size)
    filled = max(0, min(width, filled))
    bar = "█" * filled + dim("░" * (width - filled))
    return f"[{bar}]"


# ── Section renderers ──────────────────────────────────────────────────

# Ordered list of all subcommands with brief descriptions (for --version display)
_SUBCOMMANDS: list[tuple[str, str]] = [
    ("generate", "Generate a static HTML dashboard (default command)"),
    ("serve", "Start a live dashboard server with SSE updates"),
    ("export", "Export dashboard data as JSON, CSV, TSV, NDJSON, or Prometheus"),
    ("summary", "Show a quick terminal summary of agent usage metrics"),
    ("today", "Show today's total token and cost consumption (midnight to now)"),
    ("sessions", "List and filter sessions from agent usage logs"),
    ("trends", "Show trend analysis and efficiency metrics"),
    ("insights", "Show behavioral insights and optimization recommendations"),
    ("projects", "Show project-level usage statistics"),
    ("models", "Show model usage breakdown (cost, tokens, messages)"),
    ("tools", "Show tool usage statistics"),
    ("billing", "Show cost for recent billing windows (5h rolling)"),
    ("watch", "Show rolling consumption for the last N minutes (live refresh)"),
    ("benchmark", "Benchmark the parse-aggregate-render pipeline"),
    ("mcp", "Start an MCP server exposing dashboard data as tools"),
    ("config", "Show configuration: pricing, log paths, cache status, version"),
]


def _show_version() -> None:
    import sys

    from .. import __version__

    _section_header("Version")
    print(f"  Agent Usage Atlas  {green(__version__)}")
    print(f"  Python             {sys.version.split()[0]}")
    print(f"  Platform           {sys.platform}")

    print()
    print(f"  {bold('Available subcommands:')}")
    name_w = max(len(name) for name, _ in _SUBCOMMANDS)
    for name, desc in _SUBCOMMANDS:
        print(f"    {cyan(name.ljust(name_w))}  {dim(desc)}")


def _show_pricing() -> None:
    from ..models import _build_pricing

    _section_header("Model Pricing (per 1M tokens)")

    pricing = _build_pricing()
    # Sort by input price descending, take top 20
    sorted_models = sorted(pricing.items(), key=lambda kv: kv[1].input, reverse=True)[:20]

    if not sorted_models:
        print(f"  No pricing data available.")
        return

    # ── Group models by identical pricing tier ──────────────────────────
    # Build tier -> [model names] mapping, preserving sort order
    tier_groups: dict[tuple, list[str]] = {}
    for name, tier in sorted_models:
        key = (tier.input, tier.cache_read, tier.cache_write, tier.output, tier.reasoning)
        tier_groups.setdefault(key, []).append(name)

    # Assign tier labels (Tier 1 = most expensive input)
    tier_keys = list(tier_groups.keys())
    tier_label: dict[tuple, str] = {k: f"Tier {i + 1}" for i, k in enumerate(tier_keys)}

    # Find most cost-effective tier by output price (lowest output cost per token)
    best_key = min(tier_keys, key=lambda k: k[3])  # k[3] = output price
    best_label = tier_label[best_key]

    # Column headers
    hdr_model = "Model"
    hdr_tier = "Tier"
    hdr_input = "Input"
    hdr_cache_r = "Cache Read"
    hdr_cache_w = "Cache Write"
    hdr_output = "Output"
    hdr_reason = "Reasoning"

    # Determine model column width
    model_w = max(len(hdr_model), *(len(name) for name, _ in sorted_models))

    def _price(val: float) -> str:
        return f"${val:.2f}" if val < 100 else f"${val:.0f}"

    header = (
        f"  {dim(hdr_model.ljust(model_w))} | "
        f"{dim(hdr_tier.ljust(6))} | "
        f"{dim(hdr_input.rjust(8))} | "
        f"{dim(hdr_cache_r.rjust(10))} | "
        f"{dim(hdr_cache_w.rjust(11))} | "
        f"{dim(hdr_output.rjust(8))} | "
        f"{dim(hdr_reason.rjust(9))}"
    )
    separator = f"  {'-' * model_w}-+{'-' * 8}+{'-' * 10}+{'-' * 12}+{'-' * 13}+{'-' * 10}+{'-' * 11}"

    print(header)
    print(dim(separator))

    prev_tier_key: tuple | None = None
    for name, tier in sorted_models:
        key = (tier.input, tier.cache_read, tier.cache_write, tier.output, tier.reasoning)
        label = tier_label[key]

        # Print tier separator line when tier changes
        if key != prev_tier_key and prev_tier_key is not None:
            print(dim(f"  {'·' * (model_w + 82)}"))
        prev_tier_key = key

        # Highlight the best-value tier's output column
        output_str = _price(tier.output).rjust(8)
        if key == best_key:
            output_str = green(output_str)

        label_col = cyan(label.ljust(6)) if key == best_key else dim(label.ljust(6))

        print(
            f"  {name.ljust(model_w)} | "
            f"{label_col} | "
            f"{_price(tier.input).rjust(8)} | "
            f"{_price(tier.cache_read).rjust(10)} | "
            f"{_price(tier.cache_write).rjust(11)} | "
            f"{output_str} | "
            f"{_price(tier.reasoning).rjust(9)}"
        )

    print()
    print(f"  {cyan('Best value per output token:')} {bold(best_label)} "
          f"({', '.join(tier_groups[best_key])})  "
          f"— ${best_key[3]:.2f}/M output tokens")

    user_override = Path.home() / ".config" / "agent-usage-atlas" / "pricing.json"
    print()
    if user_override.is_file():
        print(f"  {green('✓')} User override loaded: {user_override}")
    else:
        print(f"  {dim('No user override at:')} {user_override}")


def _show_paths() -> None:
    _section_header("Log Paths")

    log_dirs: list[tuple[str, Path]] = [
        ("Codex", Path.home() / ".codex"),
        ("Claude", Path.home() / ".claude" / "projects"),
        ("Cursor", Path.home() / ".cursor"),
        ("Hermit", Path.home() / ".hermit"),
    ]

    name_w = max(len(name) for name, _ in log_dirs)

    # Pre-scan all sizes to compute the relative bar scale
    dir_stats: list[tuple[str, Path, bool, int, int]] = []
    for name, path in log_dirs:
        exists = path.is_dir()
        if exists:
            count, size = _count_files(path)
        else:
            count, size = 0, 0
        dir_stats.append((name, path, exists, count, size))

    max_size = max((size for _, _, exists, _, size in dir_stats if exists), default=1) or 1

    for name, path, exists, count, size in dir_stats:
        # Derive indicator from already-collected stats to avoid a second directory walk
        if not exists:
            indicator = red("✗")
        elif count == 0:
            indicator = yellow("⚠")
        else:
            indicator = green("✓")
        if exists and count > 0:
            bar = _size_bar(size, max_size)
            detail = f"{count:>6} files   {_fmt_bytes(size):>10}  {bar}"
        elif exists:
            bar = _size_bar(0, max_size)
            detail = f"{'0':>6} files   {'0 B':>10}  {bar}  {yellow('(empty)')}"
        else:
            detail = dim("directory not found")

        print(f"  {indicator} {name.ljust(name_w)}  {str(path).ljust(40)}  {detail}")

    # User pricing override path
    user_pricing = Path.home() / ".config" / "agent-usage-atlas" / "pricing.json"
    pricing_indicator = _path_indicator(user_pricing)
    pricing_status = green("exists") if user_pricing.is_file() else dim("not found")
    print()
    print(f"  {pricing_indicator} {dim('Pricing override:')}  {user_pricing}  [{pricing_status}]")


def _show_cache() -> None:
    from ..parsers._base import _JSONL_CACHE, _RESULT_CACHE

    _section_header("Cache Status")

    # In-memory caches
    jsonl_count = len(_JSONL_CACHE)
    result_count = len(_RESULT_CACHE)

    print(f"  JSONL file cache     {bold(str(jsonl_count)):>6} entries")
    print(f"  Result cache         {bold(str(result_count)):>6} entries")

    # Disk cache directory
    disk_cache_dir = Path.home() / ".cache" / "agent-usage-atlas"
    if disk_cache_dir.is_dir():
        count, size = _count_files(disk_cache_dir)
        print(f"  Disk cache dir       {count:>6} files    {_fmt_bytes(size):>10}  ({disk_cache_dir})")
    else:
        print(f"  Disk cache dir       {dim('not created')}  ({disk_cache_dir})")

    # Server lock file
    lock_path = disk_cache_dir / "server.lock"
    if lock_path.is_file():
        try:
            pid = lock_path.read_text(encoding="utf-8").strip()
            print(f"  Server lock          {yellow('locked')}  (PID {pid})")
        except OSError:
            print(f"  Server lock          {yellow('locked')}  (unreadable)")
    else:
        print(f"  Server lock          {green('free')}")


# ── Health check ────────────────────────────────────────────────────────

# Threshold for "unusually large" directory: 500 MB
_LARGE_DIR_THRESHOLD = 500 * (1 << 20)

# How stale (seconds) a disk cache entry must be to be flagged
_CACHE_STALE_SECONDS = 3600  # 1 hour


def _show_health() -> None:
    _section_header("System Health")

    issues: list[str] = []
    ok_count = 0

    # ── Log directory checks ───────────────────────────────────────────
    log_dirs: list[tuple[str, Path]] = [
        ("Codex (~/.codex)", Path.home() / ".codex"),
        ("Claude (~/.claude/projects)", Path.home() / ".claude" / "projects"),
        ("Cursor (~/.cursor)", Path.home() / ".cursor"),
        ("Hermit (~/.hermit)", Path.home() / ".hermit"),
    ]

    print(f"  {bold('Log directories:')}")
    for label, path in log_dirs:
        if not path.exists():
            sym = red("✗")
            msg = f"{sym} {label}  {dim('not found')}"
        else:
            count, size = _count_files(path)
            if count == 0:
                sym = yellow("⚠")
                msg = f"{sym} {label}  {yellow('exists but empty')}"
                issues.append(f"{label} exists but contains no files")
            elif size > _LARGE_DIR_THRESHOLD:
                sym = yellow("⚠")
                msg = f"{sym} {label}  {_fmt_bytes(size)}  {yellow('(unusually large)')}"
                issues.append(f"{label} is unusually large ({_fmt_bytes(size)})")
                ok_count += 1
            else:
                sym = green("✓")
                msg = f"{sym} {label}  {count} files, {_fmt_bytes(size)}"
                ok_count += 1
        print(f"    {msg}")

    # ── Disk cache freshness ───────────────────────────────────────────
    print()
    print(f"  {bold('Cache freshness:')}")
    disk_cache_dir = Path.home() / ".cache" / "agent-usage-atlas"
    if not disk_cache_dir.is_dir():
        print(f"    {dim('✗')} Disk cache directory does not exist yet")
    else:
        now = time.time()
        try:
            cache_files = list(disk_cache_dir.iterdir())
        except OSError:
            print(f"    {yellow('⚠')} Cache directory exists but could not be read")
            issues.append("Cache directory is unreadable")
            cache_files = None
        stale_files: list[Path] = []
        for cf in (cache_files or []):
            try:
                age = now - cf.stat().st_mtime
                if age > _CACHE_STALE_SECONDS:
                    stale_files.append(cf)
            except OSError:
                pass

        if cache_files is None:
            pass  # directory was unreadable; warning already printed above
        elif stale_files:
            sym = yellow("⚠")
            print(f"    {sym} {len(stale_files)} cache file(s) older than 1 hour")
            issues.append(f"{len(stale_files)} stale cache file(s) in {disk_cache_dir}")
        else:
            sym = green("✓")
            total = len(cache_files)
            print(f"    {sym} {total} cache file(s), all fresh (< 1 hour old)")
            ok_count += 1

    # ── Server lock ────────────────────────────────────────────────────
    print()
    print(f"  {bold('Server lock:')}")
    lock_path = disk_cache_dir / "server.lock"
    if lock_path.is_file():
        try:
            pid_str = lock_path.read_text(encoding="utf-8").strip()
            # Check if the PID is actually running
            pid_alive = False
            if pid_str.isdigit():
                try:
                    os.kill(int(pid_str), 0)
                    pid_alive = True
                except (OSError, ProcessLookupError):
                    pass
            if pid_alive:
                print(f"    {yellow('⚠')} Lock held by PID {pid_str}  {yellow('(live server running)')}")
                issues.append(f"Server lock held by live process PID {pid_str}")
            else:
                msg = f"Lock file for PID {pid_str}, process not running"
                print(f"    {yellow('⚠')} {msg}  {dim('(stale lock)')}")
                issues.append(f"Stale server lock for PID {pid_str}")
        except OSError:
            print(f"    {yellow('⚠')} Lock file present but unreadable")
            issues.append("Server lock file is unreadable")
    else:
        print(f"    {green('✓')} No server lock — server is not running")
        ok_count += 1

    # ── Summary ────────────────────────────────────────────────────────
    print()
    if not issues:
        print(f"  {green(bold('All checks passed.'))}  {ok_count} item(s) OK.")
    else:
        print(f"  {yellow(bold(f'{len(issues)} issue(s) found:'))}")
        for issue in issues:
            print(f"    {yellow('·')} {issue}")


# ── Main entry point ───────────────────────────────────────────────────


def run(args) -> None:
    show_all = not (args.pricing or args.paths or args.cache or args.version or args.health)

    if show_all or args.version:
        _show_version()
    if show_all or args.pricing:
        _show_pricing()
    if show_all or args.paths:
        _show_paths()
    if show_all or args.cache:
        _show_cache()
    if args.health:
        _show_health()

    print()
