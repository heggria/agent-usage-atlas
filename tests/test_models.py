"""Tests for models.py: pricing lookup, cost calculation, formatting helpers."""

from datetime import datetime, timezone

import pytest

from agent_usage_atlas.models import _P, UsageEvent, _gp, fmt_int, fmt_short, fmt_usd

# ── _gp() fuzzy model matching ──


class TestGp:
    def test_exact_prefix_match(self):
        tier = _gp("claude-sonnet-4-6-20260301")
        assert tier == _P["claude-sonnet-4-6"]

    def test_exact_key(self):
        assert _gp("claude-opus-4-1") == _P["claude-opus-4-1"]

    def test_substring_fallback(self):
        # "claude-3-5-sonnet" should match via substring for e.g. "some-claude-3-5-sonnet-variant"
        tier = _gp("x-claude-3-5-sonnet-y")
        assert tier == _P["claude-3-5-sonnet"]

    def test_unknown_model_returns_default(self):
        tier = _gp("totally-unknown-model-xyz")
        # Default fallback is _S (Sonnet pricing)
        assert tier.input == 3

    def test_case_insensitive(self):
        assert _gp("Claude-Opus-4-1") == _P["claude-opus-4-1"]


# ── UsageEvent.cost / cost_breakdown ──


def _make_event(**kwargs):
    defaults = dict(
        source="Claude",
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        session_id="s1",
        model="claude-sonnet-4-6",
    )
    defaults.update(kwargs)
    return UsageEvent(**defaults)


class TestUsageEventCost:
    def test_zero_tokens_zero_cost(self):
        e = _make_event()
        assert e.cost == 0.0
        assert e.total == 0

    def test_known_cost(self):
        # Sonnet pricing: input=$3/1M, output=$15/1M
        e = _make_event(uncached_input=1_000_000, output=1_000_000)
        assert e.cost == pytest.approx(3.0 + 15.0)

    def test_cost_breakdown_keys(self):
        e = _make_event(uncached_input=100, cache_read=200, output=300)
        bd = e.cost_breakdown
        assert set(bd.keys()) == {"input", "cache_read", "cache_write", "output", "reasoning", "cache_read_full"}

    def test_cost_breakdown_values(self):
        # Sonnet: input=3, cache_read=0.3, output=15 per 1M
        e = _make_event(uncached_input=1_000_000, cache_read=1_000_000, output=1_000_000)
        bd = e.cost_breakdown
        assert bd["input"] == pytest.approx(3.0)
        assert bd["cache_read"] == pytest.approx(0.3)
        assert bd["output"] == pytest.approx(15.0)
        # cache_read_full uses input price for saved calculation
        assert bd["cache_read_full"] == pytest.approx(3.0)

    def test_total_property(self):
        e = _make_event(uncached_input=10, cache_read=20, cache_write=30, output=40, reasoning=50)
        assert e.total == 150


# ── Formatting helpers ──


class TestFmtUsd:
    def test_large_value(self):
        assert fmt_usd(1500) == "$1,500"

    def test_medium_value(self):
        assert fmt_usd(12.345) == "$12.35"

    def test_small_value(self):
        assert fmt_usd(0.0042) == "$0.0042"

    def test_boundary_one(self):
        assert fmt_usd(1.0) == "$1.00"


class TestFmtShort:
    def test_billions(self):
        assert fmt_short(2_500_000_000) == "2.50B"

    def test_millions(self):
        assert fmt_short(1_234_567) == "1.23M"

    def test_thousands(self):
        assert fmt_short(4_567) == "4.6K"

    def test_small(self):
        assert fmt_short(42) == "42"

    def test_zero(self):
        assert fmt_short(0) == "0"


class TestFmtInt:
    def test_basic(self):
        assert fmt_int(1234567) == "1,234,567"

    def test_small(self):
        assert fmt_int(42) == "42"
