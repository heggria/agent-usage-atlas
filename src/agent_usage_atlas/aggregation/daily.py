"""Daily rollup computation."""

from __future__ import annotations

from ._context import AggContext


def compute(ctx: AggContext) -> list[dict]:
    return ctx.ordered_days
