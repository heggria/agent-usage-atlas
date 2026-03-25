"""Model usage breakdown command."""

from __future__ import annotations

import re

from ..cli import build_dashboard_payload
from ..models import fmt_int, fmt_usd
from ._ansi import _c, bold, cyan, dim, green, yellow

# ── Subcommand registration ───────────────────────────────────────────


def add_parser(subparsers):
    parser = subparsers.add_parser(
        "models",
        help="Show model usage breakdown (cost, tokens, messages)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=15,
        help="Number of models to show (default: 15)",
    )
    parser.set_defaults(func=run)
    return parser


# ── Helpers ───────────────────────────────────────────────────────────

_BAR_WIDTH = 20


def _cost_bar(fraction: float) -> str:
    """Return a █-based proportion bar (max _BAR_WIDTH chars) + percentage."""
    fraction = max(0.0, min(1.0, fraction))
    filled = round(fraction * _BAR_WIDTH)
    bar = "█" * filled + "░" * (_BAR_WIDTH - filled)
    pct = fraction * 100
    return f"{bar} {pct:5.1f}%"


def _model_family(model: str) -> str:
    """Group model name by splitting at the last '-' before a digit."""
    # e.g. claude-sonnet-4-6 → claude-sonnet, gpt-5 → gpt, o3-mini → o3
    m = re.match(r"^(.*?)-\d", model)
    if m:
        # strip trailing '-' that may remain
        return m.group(1).rstrip("-")
    return model


def _cost_per_1k_out(cost: float, output_tokens: int) -> str:
    """Cost per 1 K output tokens, or '-' when output is zero."""
    if output_tokens <= 0:
        return "-"
    rate = cost / (output_tokens / 1000)
    return f"${rate:.4f}"


# ── Command implementation ────────────────────────────────────────────


def run(args) -> None:
    try:
        dashboard = build_dashboard_payload(days=args.days, since=args.since)
    except ValueError as exc:
        raise SystemExit(f"Invalid --since date format: {exc}") from exc

    model_costs: list[dict] = dashboard.get("trend_analysis", {}).get("model_costs", [])
    totals: dict = dashboard.get("totals", {})

    top_n = args.top

    # ── Header ────────────────────────────────────────────────────
    if args.since:
        header = f"Model Usage -- since {args.since}"
    else:
        header = f"Model Usage -- last {args.days} days"
    print(bold(header))
    print()

    if not model_costs:
        print("  No model usage data found.")
        return

    # ── Compute grand total cost for percentage column ────────────
    grand_cost = totals.get("grand_cost", 0.0)
    if grand_cost <= 0:
        grand_cost = sum(m["cost"] for m in model_costs) or 1.0

    # ── Table ─────────────────────────────────────────────────────
    rows = model_costs[:top_n]
    if not rows:
        print("  No model usage data to display (--top must be >= 1).")
        return

    # Column headers
    hdr_rank = "#"
    hdr_model = "Model"
    hdr_cost = "Cost"
    hdr_msgs = "Messages"
    hdr_input = "Input Tokens"
    hdr_output = "Output Tokens"
    hdr_cache = "Cache Tokens"
    hdr_eff = "$/1K out"
    hdr_bar = "Share" + " " * (_BAR_WIDTH - 5) + "  %"  # align with bar width

    # Determine column widths from data
    w_rank = max(len(hdr_rank), len(str(len(rows))))
    w_model = max(len(hdr_model), *(len(r["model"]) for r in rows))
    w_cost = max(len(hdr_cost), *(len(fmt_usd(r["cost"])) for r in rows))
    w_msgs = max(len(hdr_msgs), *(len(fmt_int(r["messages"])) for r in rows))
    w_input = max(len(hdr_input), *(len(fmt_int(r["input_tokens"])) for r in rows))
    w_output = max(len(hdr_output), *(len(fmt_int(r["output_tokens"])) for r in rows))
    w_cache = max(len(hdr_cache), *(len(fmt_int(r["cache_tokens"])) for r in rows))
    w_eff = max(len(hdr_eff), max(len(_cost_per_1k_out(r["cost"], r["output_tokens"])) for r in rows))
    w_bar = _BAR_WIDTH + 7  # "█…░ NNN.N%"

    def _fmt_row(rank, model, cost, msgs, inp, out, cache, eff, bar) -> str:
        return (
            f"{rank:>{w_rank}} | "
            f"{model:<{w_model}} | "
            f"{cost:>{w_cost}} | "
            f"{msgs:>{w_msgs}} | "
            f"{inp:>{w_input}} | "
            f"{out:>{w_output}} | "
            f"{cache:>{w_cache}} | "
            f"{eff:>{w_eff}} | "
            f"{bar}"
        )

    # Print header row
    header_line = _fmt_row(hdr_rank, hdr_model, hdr_cost, hdr_msgs, hdr_input, hdr_output, hdr_cache, hdr_eff, hdr_bar)
    print(bold(cyan(header_line)))

    # Separator
    sep_parts = [
        "-" * (w_rank + 1), "-" * (w_model + 2), "-" * (w_cost + 2),
        "-" * (w_msgs + 2), "-" * (w_input + 2), "-" * (w_output + 2),
        "-" * (w_cache + 2), "-" * (w_eff + 2), "-" * (w_bar + 1),
    ]
    print("+".join(sep_parts))

    # Data rows
    for i, row in enumerate(rows, 1):
        fraction = (row["cost"] / grand_cost) if grand_cost else 0.0
        eff = _cost_per_1k_out(row["cost"], row["output_tokens"])
        bar = _cost_bar(fraction)
        line = _fmt_row(
            str(i),
            row["model"],
            fmt_usd(row["cost"]),
            fmt_int(row["messages"]),
            fmt_int(row["input_tokens"]),
            fmt_int(row["output_tokens"]),
            fmt_int(row["cache_tokens"]),
            eff,
            bar,
        )
        if i == 1:
            print(bold(green(line)))
        elif i <= 3:
            print(yellow(line))
        else:
            print(dim(line) if i > 10 else _c("37", line))

    # ── Input/Output ratio footer ─────────────────────────────────
    total_input = sum(r["input_tokens"] for r in model_costs)
    total_output = sum(r["output_tokens"] for r in model_costs)
    if total_output > 0:
        ratio = total_input / total_output
        print()
        in_s, out_s = fmt_int(total_input), fmt_int(total_output)
        print(dim(f"  Input : Output ratio  {ratio:.1f} : 1  ({in_s} in / {out_s} out)"))

    # ── By-Family summary ─────────────────────────────────────────
    family_cost: dict[str, float] = {}
    family_out: dict[str, int] = {}
    for m in model_costs:
        fam = _model_family(m["model"])
        family_cost[fam] = family_cost.get(fam, 0.0) + m["cost"]
        family_out[fam] = family_out.get(fam, 0) + m["output_tokens"]

    sorted_families = sorted(family_cost.items(), key=lambda x: x[1], reverse=True)

    print()
    print(bold("By Family"))
    w_fam = max((len(f) for f, _ in sorted_families), default=6)
    for fam, fc in sorted_families:
        frac = fc / grand_cost if grand_cost else 0.0
        bar = _cost_bar(frac)
        eff = _cost_per_1k_out(fc, family_out.get(fam, 0))
        print(f"  {fam:<{w_fam}}  {fmt_usd(fc):>9}  {eff:>9}  {bar}")

    # ── Summary ───────────────────────────────────────────────────
    total_models = len(model_costs)
    top_model_pct = (rows[0]["cost"] / grand_cost * 100) if grand_cost and rows else 0.0

    print()
    print(bold("Summary"))
    print(f"  Total models used : {fmt_int(total_models)}")
    print(f"  Grand total cost  : {fmt_usd(grand_cost)}")
    print(f"  Top model share   : {top_model_pct:.1f}% ({rows[0]['model']})" if rows else "  Top model share   : -")
