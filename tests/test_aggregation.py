"""Tests for aggregation utilities and context building."""

from datetime import datetime, timezone

import pytest

from agent_usage_atlas.aggregation._context import (
    _percent,
    _percentile,
    _round_money,
    build_context,
)
from agent_usage_atlas.aggregation.totals import compute as totals_compute
from agent_usage_atlas.aggregation.trends import _build_sankey
from agent_usage_atlas.models import UsageEvent

# ── _percent ──


class TestPercent:
    def test_normal(self):
        assert _percent(1, 4) == pytest.approx(0.25)

    def test_zero_denominator(self):
        assert _percent(10, 0) == 0.0

    def test_zero_numerator(self):
        assert _percent(0, 100) == 0.0


# ── _percentile ──


class TestPercentile:
    def test_median_odd(self):
        assert _percentile([1, 2, 3, 4, 5], 0.5) == 3

    def test_p0(self):
        assert _percentile([10, 20, 30], 0.0) == 10

    def test_p100(self):
        assert _percentile([10, 20, 30], 1.0) == 30

    def test_empty(self):
        assert _percentile([], 0.5) == 0.0


# ── _round_money ──


class TestRoundMoney:
    def test_rounds_to_two_decimals(self):
        assert _round_money(1.23456789) == 1.23

    def test_zero(self):
        assert _round_money(0.0) == 0.0


# ── build_context + totals.compute ──


def _make_events():
    """Create a small set of known events for aggregation testing."""
    base_ts = datetime(2026, 3, 10, 12, 0, 0, tzinfo=timezone.utc)
    return [
        UsageEvent(
            source="Claude",
            timestamp=base_ts,
            session_id="s1",
            model="claude-sonnet-4-6",
            uncached_input=1000,
            cache_read=500,
            output=200,
            activity_messages=1,
        ),
        UsageEvent(
            source="Claude",
            timestamp=base_ts,
            session_id="s1",
            model="claude-sonnet-4-6",
            uncached_input=2000,
            cache_read=1000,
            output=400,
            activity_messages=1,
        ),
    ]


class TestBuildContextAndTotals:
    def setup_method(self):
        self.events = _make_events()
        self.local_tz = timezone.utc
        self.start = datetime(2026, 3, 10, 0, 0, 0, tzinfo=timezone.utc)
        self.now = datetime(2026, 3, 10, 23, 59, 0, tzinfo=timezone.utc)

    def test_context_ordered_days_count(self):
        ctx = build_context(
            self.events,
            [],
            [],
            start_local=self.start,
            now_local=self.now,
            local_tz=self.local_tz,
        )
        assert len(ctx.ordered_days) == 1

    def test_totals_grand_total(self):
        ctx = build_context(
            self.events,
            [],
            [],
            start_local=self.start,
            now_local=self.now,
            local_tz=self.local_tz,
        )
        result = totals_compute(ctx)
        # total = (1000+500+200) + (2000+1000+400) = 5100
        assert result["grand_total"] == 5100

    def test_totals_grand_cost_positive(self):
        ctx = build_context(
            self.events,
            [],
            [],
            start_local=self.start,
            now_local=self.now,
            local_tz=self.local_tz,
        )
        result = totals_compute(ctx)
        assert result["grand_cost"] > 0

    def test_totals_cache_ratio(self):
        ctx = build_context(
            self.events,
            [],
            [],
            start_local=self.start,
            now_local=self.now,
            local_tz=self.local_tz,
        )
        result = totals_compute(ctx)
        # cache_read=1500, cache_write=0, total=5100
        # ratio = 1500 / 5100 ≈ 0.294
        assert 0.2 < result["cache_ratio"] < 0.4


# ── _build_sankey ──


class TestBuildSankey:
    def test_basic_structure(self):
        cards = [
            {"source": "Claude", "input": 100, "output": 50},
            {"source": "Codex", "input": 200, "output": 0},
        ]
        specs = [("input", "Input Tokens"), ("output", "Output Tokens")]
        result = _build_sankey(cards, specs)

        assert "nodes" in result
        assert "links" in result

    def test_node_count(self):
        cards = [{"source": "Claude", "x": 10}]
        specs = [("x", "X Label")]
        result = _build_sankey(cards, specs)
        # 1 source node + 1 bucket node
        assert len(result["nodes"]) == 2

    def test_zero_values_excluded(self):
        cards = [{"source": "Claude", "a": 0, "b": 5}]
        specs = [("a", "A"), ("b", "B")]
        result = _build_sankey(cards, specs)
        # Only "b" link should exist (value > 0)
        assert len(result["links"]) == 1
        assert result["links"][0]["target"] == "B"

    def test_link_values(self):
        cards = [{"source": "Claude", "cost": 42}]
        specs = [("cost", "Cost")]
        result = _build_sankey(cards, specs)
        assert result["links"][0]["value"] == 42
