"""Tests for parser base utilities: _ts() and _si()."""

from datetime import datetime, timezone

from agent_usage_atlas.parsers._base import _si, _ts

# ── _ts() timestamp parsing ──


class TestTs:
    def test_iso_with_z(self):
        result = _ts("2026-01-15T10:30:00Z")
        assert result == datetime(2026, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

    def test_iso_with_offset(self):
        result = _ts("2026-01-15T10:30:00+08:00")
        assert result is not None
        assert result.utcoffset().total_seconds() == 8 * 3600

    def test_iso_no_tz(self):
        result = _ts("2026-01-15T10:30:00")
        assert result is not None
        assert result.year == 2026

    def test_none_input(self):
        assert _ts(None) is None

    def test_empty_string(self):
        assert _ts("") is None


# ── _si() safe integer conversion ──


class TestSi:
    def test_int_passthrough(self):
        assert _si(42) == 42

    def test_string_number(self):
        assert _si("123") == 123

    def test_none_returns_zero(self):
        assert _si(None) == 0

    def test_zero(self):
        assert _si(0) == 0

    def test_float_truncates(self):
        assert _si(3.9) == 3

    def test_empty_string(self):
        # int("" or 0) -> int(0) -> 0
        assert _si("") == 0
