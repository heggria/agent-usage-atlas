"""Tests for benchmark_stats.py: statistical engine for benchmark analysis."""

import statistics

import pytest

from agent_usage_atlas.benchmark_stats import (
    BenchStats,
    RegressionResult,
    WarmupResult,
    _bootstrap_ci,
    _cohens_d,
    _mad,
    _percentile,
    _welch_t_test,
    compare_runs,
    compute_stats,
    detect_warmup,
)

# ── _mad() ───────────────────────────────────────────────────────────


class TestMad:
    def test_normal_data(self):
        # Median of [1,2,3,4,5] = 3; deviations = [2,1,0,1,2]
        # statistics.median of deviations = 1
        assert _mad([1, 2, 3, 4, 5]) == pytest.approx(1.0)

    def test_all_same(self):
        assert _mad([5, 5, 5]) == pytest.approx(0.0)

    def test_single_element(self):
        assert _mad([42]) == pytest.approx(0.0)

    def test_two_elements(self):
        # Median of [1,3] = 2; deviations = [1,1]; median = 1
        assert _mad([1, 3]) == pytest.approx(1.0)

    def test_already_sorted(self):
        assert _mad([10, 20, 30]) == pytest.approx(10.0)

    def test_unsorted_input(self):
        assert _mad([5, 1, 3]) == _mad([1, 3, 5])


# ── _percentile() ────────────────────────────────────────────────────


class TestPercentile:
    def test_p50_odd_count(self):
        assert _percentile([1, 2, 3, 4, 5], 50) == pytest.approx(3.0)

    def test_p0_is_min(self):
        assert _percentile([10, 20, 30, 40], 0) == pytest.approx(10.0)

    def test_p100_is_max(self):
        assert _percentile([10, 20, 30, 40], 100) == pytest.approx(40.0)

    def test_p25_known_quartile(self):
        # For [1,2,3,4,5]: k = 0.25 * 4 = 1.0 -> exact index 1 -> value 2
        assert _percentile([1, 2, 3, 4, 5], 25) == pytest.approx(2.0)

    def test_p75_known_quartile(self):
        # For [1,2,3,4,5]: k = 0.75 * 4 = 3.0 -> exact index 3 -> value 4
        assert _percentile([1, 2, 3, 4, 5], 75) == pytest.approx(4.0)

    def test_single_element(self):
        assert _percentile([99], 50) == pytest.approx(99.0)

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="at least one data point"):
            _percentile([], 50)

    def test_interpolation(self):
        # For [1,2,3,4]: k = 0.5 * 3 = 1.5 -> interpolate between index 1 and 2
        # value = 2 * 0.5 + 3 * 0.5 = 2.5
        assert _percentile([1, 2, 3, 4], 50) == pytest.approx(2.5)

    def test_unsorted_input_gets_sorted(self):
        assert _percentile([5, 1, 3], 50) == pytest.approx(3.0)


# ── compute_stats() ──────────────────────────────────────────────────


class TestComputeStats:
    def test_basic_all_fields_populated(self):
        samples = [float(i) for i in range(1, 11)]  # [1..10]
        stats = compute_stats(samples, n_bootstrap=500)
        assert stats.n == 10
        assert stats.median == pytest.approx(5.5)
        assert stats.mean == pytest.approx(5.5)
        assert stats.stddev > 0
        assert stats.mad > 0
        assert stats.p90 > 0
        assert stats.p99 > 0
        assert isinstance(stats.clean_samples, list)

    def test_outlier_detection(self):
        samples = [1.0, 1.0, 1.0, 1.0, 1.0, 100.0]
        stats = compute_stats(samples, n_bootstrap=500)
        assert stats.outlier_count >= 1

    def test_ci_contains_median(self):
        samples = [2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
        stats = compute_stats(samples, n_bootstrap=500)
        assert stats.ci_lower <= stats.median <= stats.ci_upper

    def test_mad_positive_for_varied_data(self):
        stats = compute_stats([1.0, 5.0, 10.0, 15.0, 20.0], n_bootstrap=500)
        assert stats.mad > 0

    def test_mad_zero_for_constant_data(self):
        stats = compute_stats([7.0, 7.0, 7.0, 7.0], n_bootstrap=500)
        assert stats.mad == pytest.approx(0.0)

    def test_p90_ge_median(self):
        stats = compute_stats([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0], n_bootstrap=500)
        assert stats.p90 >= stats.median

    def test_p99_ge_p90(self):
        stats = compute_stats([float(x) for x in range(1, 101)], n_bootstrap=500)
        assert stats.p99 >= stats.p90

    def test_clean_samples_fewer_when_outliers(self):
        samples = [1.0, 1.0, 1.0, 1.0, 1.0, 100.0]
        stats = compute_stats(samples, n_bootstrap=500)
        assert len(stats.clean_samples) < len(samples)

    def test_edge_n2(self):
        stats = compute_stats([3.0, 7.0], n_bootstrap=500)
        assert stats.n == 2
        assert stats.median == pytest.approx(5.0)
        assert stats.mean == pytest.approx(5.0)
        assert stats.stddev > 0

    def test_edge_n1_no_crash(self):
        stats = compute_stats([42.0], n_bootstrap=500)
        assert stats.n == 1
        assert stats.median == pytest.approx(42.0)
        assert stats.mean == pytest.approx(42.0)
        assert stats.stddev == pytest.approx(0.0)
        assert stats.mad == pytest.approx(0.0)

    def test_edge_empty_raises(self):
        with pytest.raises(ValueError, match="at least one sample"):
            compute_stats([])

    def test_returns_bench_stats_type(self):
        stats = compute_stats([1.0, 2.0, 3.0], n_bootstrap=500)
        assert isinstance(stats, BenchStats)

    def test_clean_samples_is_list(self):
        stats = compute_stats([1.0, 2.0, 3.0], n_bootstrap=500)
        assert isinstance(stats.clean_samples, list)

    def test_ci_reasonable_width(self):
        """CI should not be degenerate for non-trivial data."""
        samples = [float(x) for x in range(1, 21)]
        stats = compute_stats(samples, n_bootstrap=500)
        assert stats.ci_upper > stats.ci_lower

    def test_iqr_equals_q3_minus_q1(self):
        stats = compute_stats([1.0, 2.0, 3.0, 4.0, 5.0], n_bootstrap=500)
        assert stats.iqr == pytest.approx(stats.q3 - stats.q1)

    def test_q1_le_median_le_q3(self):
        stats = compute_stats([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0], n_bootstrap=500)
        assert stats.q1 <= stats.median <= stats.q3


# ── detect_warmup() ──────────────────────────────────────────────────


class TestDetectWarmup:
    def test_no_warmup_stable_data(self):
        result = detect_warmup([5.0, 5.1, 4.9, 5.0, 5.1])
        assert result.warmup_end == 0
        assert len(result.steady_samples) == 5

    def test_clear_warmup(self):
        samples = [20.0, 15.0, 10.0, 5.0, 5.0, 5.0, 5.0, 5.0]
        result = detect_warmup(samples)
        assert result.warmup_end > 0
        assert len(result.steady_samples) < len(samples)

    def test_all_decreasing_no_crash(self):
        samples = [100.0, 80.0, 60.0, 40.0, 20.0, 10.0, 5.0]
        result = detect_warmup(samples)
        assert isinstance(result, WarmupResult)
        assert isinstance(result.steady_samples, list)

    def test_short_sequence_no_crash(self):
        result = detect_warmup([1.0, 2.0, 3.0])
        assert isinstance(result, WarmupResult)
        # n < 4 -> warmup_end=0
        assert result.warmup_end == 0

    def test_steady_samples_are_tail(self):
        """steady_samples should be a suffix of the original samples."""
        samples = [20.0, 15.0, 10.0, 5.0, 5.0, 5.0, 5.0, 5.0]
        result = detect_warmup(samples)
        expected_tail = samples[result.warmup_end :]
        assert result.steady_samples == expected_tail

    def test_constant_data_no_warmup(self):
        result = detect_warmup([3.0] * 10)
        assert result.warmup_end == 0
        assert len(result.steady_samples) == 10

    def test_returns_warmup_result_type(self):
        result = detect_warmup([1.0, 2.0, 3.0, 4.0, 5.0])
        assert isinstance(result, WarmupResult)

    def test_single_element(self):
        result = detect_warmup([42.0])
        assert result.warmup_end == 0
        assert result.steady_samples == [42.0]


# ── _welch_t_test() ──────────────────────────────────────────────────


class TestWelchTTest:
    def test_same_distributions_high_p(self):
        a = [5.0, 5.1, 4.9, 5.0, 5.1, 5.0, 4.9, 5.1]
        b = [5.0, 4.9, 5.1, 5.0, 5.0, 5.1, 4.9, 5.0]
        _t, p = _welch_t_test(a, b)
        assert p > 0.05

    def test_very_different_distributions_low_p(self):
        a = [1.0, 1.1, 0.9]
        b = [100.0, 100.1, 99.9]
        _t, p = _welch_t_test(a, b)
        assert p < 0.01

    def test_identical_data_p_one(self):
        a = [5.0, 5.0, 5.0]
        b = [5.0, 5.0, 5.0]
        _t, p = _welch_t_test(a, b)
        assert p == pytest.approx(1.0)

    def test_p_value_between_zero_and_one(self):
        a = [1.0, 2.0, 3.0, 4.0]
        b = [3.0, 4.0, 5.0, 6.0]
        _t, p = _welch_t_test(a, b)
        assert 0.0 <= p <= 1.0

    def test_too_few_samples_returns_one(self):
        # Need at least 2 samples per group
        t, p = _welch_t_test([1.0], [2.0])
        assert t == pytest.approx(0.0)
        assert p == pytest.approx(1.0)

    def test_returns_t_and_p(self):
        """_welch_t_test returns a (t_statistic, p_value) tuple."""
        result = _welch_t_test([1.0, 2.0, 3.0], [4.0, 5.0, 6.0])
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_t_stat_sign(self):
        """t-stat should be negative when mean(a) < mean(b)."""
        a = [1.0, 2.0, 3.0]
        b = [10.0, 11.0, 12.0]
        t, _p = _welch_t_test(a, b)
        assert t < 0


# ── _cohens_d() ──────────────────────────────────────────────────────


class TestCohensD:
    def test_same_data_d_zero(self):
        data = [5.0, 5.1, 4.9, 5.0]
        d = _cohens_d(data, data)
        assert d == pytest.approx(0.0, abs=0.01)

    def test_large_effect(self):
        a = [10.0, 10.5, 9.5, 10.0]
        b = [1.0, 1.5, 0.5, 1.0]
        d = _cohens_d(a, b)
        assert d > 0.8

    def test_direction_a_greater(self):
        a = [10.0, 11.0, 12.0, 13.0]
        b = [1.0, 2.0, 3.0, 4.0]
        d = _cohens_d(a, b)
        assert d > 0

    def test_direction_b_greater(self):
        a = [1.0, 2.0, 3.0, 4.0]
        b = [10.0, 11.0, 12.0, 13.0]
        d = _cohens_d(a, b)
        assert d < 0

    def test_small_effect_range(self):
        # Construct groups with a small but nonzero effect
        a = [5.0, 5.5, 6.0, 5.2, 5.8]
        b = [4.5, 5.0, 5.5, 4.7, 5.3]
        d = _cohens_d(a, b)
        assert 0.0 < abs(d) < 2.0  # sanity: not zero, not astronomically large

    def test_too_few_samples_returns_zero(self):
        assert _cohens_d([1.0], [2.0]) == pytest.approx(0.0)

    def test_zero_variance_both_groups(self):
        # Both groups have zero variance and same mean -> pooled_var=0 -> d=0
        assert _cohens_d([5.0, 5.0], [5.0, 5.0]) == pytest.approx(0.0)


# ── compare_runs() ───────────────────────────────────────────────────


class TestCompareRuns:
    def test_no_change_similar_distributions(self):
        baseline = [5.0, 5.1, 4.9, 5.0, 5.1, 5.0, 4.9, 5.1, 5.0, 5.0]
        contender = [5.0, 4.9, 5.1, 5.0, 5.0, 5.1, 4.9, 5.0, 5.1, 5.0]
        result = compare_runs(baseline, contender)
        assert result.changed is False
        assert result.direction == "unchanged"

    def test_regression_fast_baseline_slow_contender(self):
        baseline = [5.0, 5.1, 4.9, 5.0, 5.1, 5.0, 4.9, 5.1, 5.0, 5.0]
        contender = [50.0, 51.0, 49.0, 50.0, 51.0, 50.0, 49.0, 51.0, 50.0, 50.0]
        result = compare_runs(baseline, contender)
        assert result.changed is True
        assert result.direction == "slower"
        assert result.pct_change > 0

    def test_improvement_slow_baseline_fast_contender(self):
        baseline = [50.0, 51.0, 49.0, 50.0, 51.0, 50.0, 49.0, 51.0, 50.0, 50.0]
        contender = [5.0, 5.1, 4.9, 5.0, 5.1, 5.0, 4.9, 5.1, 5.0, 5.0]
        result = compare_runs(baseline, contender)
        assert result.changed is True
        assert result.direction == "faster"
        assert result.pct_change < 0

    def test_effect_label_negligible(self):
        # Very similar distributions -> negligible effect
        a = [10.0, 10.01, 9.99, 10.0, 10.01, 9.99, 10.0, 10.01, 9.99, 10.0]
        b = [10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0]
        result = compare_runs(a, b)
        assert result.effect_label == "negligible"

    def test_effect_label_large(self):
        a = [1.0, 1.1, 0.9, 1.0, 1.1, 0.9, 1.0, 1.1, 0.9, 1.0]
        b = [100.0, 100.1, 99.9, 100.0, 100.1, 99.9, 100.0, 100.1, 99.9, 100.0]
        result = compare_runs(a, b)
        assert result.effect_label == "large"

    def test_returns_regression_result_type(self):
        result = compare_runs([1.0, 2.0, 3.0], [4.0, 5.0, 6.0])
        assert isinstance(result, RegressionResult)

    def test_p_value_in_range(self):
        result = compare_runs([1.0, 2.0, 3.0, 4.0], [5.0, 6.0, 7.0, 8.0])
        assert 0.0 <= result.p_value <= 1.0

    def test_pct_change_sign_matches_direction(self):
        """When changed, pct_change sign should be consistent with direction."""
        baseline = [5.0, 5.1, 4.9, 5.0, 5.1, 5.0, 4.9, 5.1, 5.0, 5.0]
        contender = [50.0, 50.1, 49.9, 50.0, 50.1, 50.0, 49.9, 50.1, 50.0, 50.0]
        result = compare_runs(baseline, contender)
        if result.direction == "slower":
            assert result.pct_change > 0
        elif result.direction == "faster":
            assert result.pct_change < 0

    def test_effect_labels_cover_all_sizes(self):
        """Verify that all four effect labels can be produced."""
        labels_seen: set[str] = set()

        # negligible: nearly identical
        r = compare_runs(
            [10.0, 10.001, 9.999] * 5,
            [10.0, 10.0, 10.0] * 5,
        )
        labels_seen.add(r.effect_label)

        # small: slight difference with overlapping distributions
        r = compare_runs(
            [10.0, 10.5, 11.0, 10.2, 10.8] * 3,
            [11.0, 11.5, 12.0, 11.2, 11.8] * 3,
        )
        labels_seen.add(r.effect_label)

        # large: completely separated
        r = compare_runs(
            [1.0, 1.1, 0.9, 1.0, 1.1] * 3,
            [100.0, 100.1, 99.9, 100.0, 100.1] * 3,
        )
        labels_seen.add(r.effect_label)

        assert "negligible" in labels_seen
        assert "large" in labels_seen

    def test_too_few_samples_unchanged(self):
        result = compare_runs([5.0], [10.0])
        assert result.changed is False
        assert result.direction == "unchanged"
        assert result.p_value == pytest.approx(1.0)


# ── _bootstrap_ci() ──────────────────────────────────────────────────


class TestBootstrapCi:
    def test_ci_width_decreases_with_more_data(self):
        # Same distribution (uniform 1-5), but more samples -> tighter CI
        small = [1.0, 2.0, 3.0, 4.0, 5.0]
        large = [
            1.0,
            1.5,
            2.0,
            2.5,
            3.0,
            3.5,
            4.0,
            4.5,
            5.0,
            1.0,
            1.5,
            2.0,
            2.5,
            3.0,
            3.5,
            4.0,
            4.5,
            5.0,
            1.0,
            1.5,
            2.0,
            2.5,
            3.0,
            3.5,
            4.0,
            4.5,
            5.0,
            1.0,
            1.5,
            2.0,
            2.5,
            3.0,
            3.5,
            4.0,
            4.5,
            5.0,
        ]
        lo_s, hi_s = _bootstrap_ci(small, statistics.median, 0.95, 500)
        lo_l, hi_l = _bootstrap_ci(large, statistics.median, 0.95, 500)
        width_small = hi_s - lo_s
        width_large = hi_l - lo_l
        assert width_large < width_small

    def test_ci_contains_true_median(self):
        data = [float(x) for x in range(1, 21)]
        lo, hi = _bootstrap_ci(data, statistics.median, 0.95, 1000)
        true_median = statistics.median(data)
        assert lo <= true_median <= hi

    def test_reproducibility_same_seed(self):
        """Bootstrap CI uses fixed seed=42 internally, so results are deterministic."""
        data = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]
        ci_a = _bootstrap_ci(data, statistics.median, 0.95, 500)
        ci_b = _bootstrap_ci(data, statistics.median, 0.95, 500)
        assert ci_a[0] == pytest.approx(ci_b[0])
        assert ci_a[1] == pytest.approx(ci_b[1])

    def test_single_element(self):
        lo, hi = _bootstrap_ci([42.0], statistics.median, 0.95, 500)
        assert lo == pytest.approx(42.0)
        assert hi == pytest.approx(42.0)

    def test_constant_data_degenerate_ci(self):
        lo, hi = _bootstrap_ci([5.0, 5.0, 5.0, 5.0, 5.0], statistics.median, 0.95, 500)
        assert lo == pytest.approx(5.0)
        assert hi == pytest.approx(5.0)

    def test_ci_bounds_order(self):
        data = [1.0, 3.0, 5.0, 7.0, 9.0, 11.0, 13.0, 15.0]
        lo, hi = _bootstrap_ci(data, statistics.median, 0.95, 500)
        assert lo <= hi

    def test_empty_data(self):
        lo, hi = _bootstrap_ci([], statistics.median, 0.95, 500)
        assert lo == pytest.approx(0.0)
        assert hi == pytest.approx(0.0)
