"""Benchmark statistical analysis — stdlib only.

Pure-Python statistical engine for benchmarking analysis.  Provides bootstrap
confidence intervals, MAD-based outlier detection, warmup detection via linear
regression trend testing, and Welch's t-test for comparing benchmark runs.

Requires Python 3.10+.  Uses only ``statistics``, ``math``, and ``random``
from the standard library — no NumPy, no SciPy.

Public API
----------
- ``compute_stats``   — descriptive stats, bootstrap CI, MAD outlier detection
- ``detect_warmup``   — linear-regression warmup detection
- ``compare_runs``    — Welch's t-test + Cohen's d regression comparison

Internal helpers are prefixed with ``_`` and documented individually.
"""

from __future__ import annotations

import math
import random
import statistics
from dataclasses import dataclass
from typing import Sequence

# ── Public data classes ──────────────────────────────────────────────


@dataclass(frozen=True)
class BenchStats:
    """Computed statistics for a set of benchmark samples."""

    n: int
    mean: float
    median: float
    stddev: float
    mad: float  # Median Absolute Deviation
    q1: float
    q3: float
    iqr: float
    p90: float
    p99: float
    ci_lower: float  # 95% bootstrap CI lower
    ci_upper: float  # 95% bootstrap CI upper
    outlier_count: int  # MAD-based outlier count
    clean_samples: list[float]  # samples with outliers removed


@dataclass(frozen=True)
class RegressionResult:
    """Result of comparing two benchmark runs."""

    changed: bool  # statistically significant?
    direction: str  # "faster", "slower", "unchanged"
    pct_change: float  # percentage change (positive = slower)
    p_value: float  # Welch's t-test p-value
    cohens_d: float  # effect size
    effect_label: str  # "negligible", "small", "medium", "large"


@dataclass(frozen=True)
class WarmupResult:
    """Result of warmup detection."""

    warmup_end: int  # index where warmup ends (0 = no warmup detected)
    steady_samples: list[float]  # samples after warmup


# ── Percentile and MAD ───────────────────────────────────────────────


def _percentile(data: Sequence[float], p: float) -> float:
    """Compute the *p*-th percentile (0–100) using linear interpolation.

    Uses the ``C = 1`` interpolation method (same as NumPy's default).
    Returns the sole value for single-element sequences.

    Raises ``ValueError`` for empty sequences.
    """
    if not data:
        raise ValueError("percentile requires at least one data point")

    sorted_data = sorted(data)
    n = len(sorted_data)

    if n == 1:
        return sorted_data[0]

    # Map p (0–100) to a 0-based fractional index.
    idx = (p / 100.0) * (n - 1)
    lo = int(math.floor(idx))
    hi = int(math.ceil(idx))

    if lo == hi:
        return sorted_data[lo]

    frac = idx - lo
    return sorted_data[lo] * (1.0 - frac) + sorted_data[hi] * frac


def _mad(data: Sequence[float]) -> float:
    """Median Absolute Deviation.

    Returns 0.0 for sequences with fewer than 2 elements.
    """
    if len(data) < 2:
        return 0.0
    med = statistics.median(data)
    return statistics.median(abs(x - med) for x in data)


# ── Bootstrap confidence interval ───────────────────────────────────


def _bootstrap_ci(
    data: list[float],
    stat_fn,  # callable[[list[float]], float]
    ci_level: float,
    n_bootstrap: int,
) -> tuple[float, float]:
    """Bootstrap confidence interval using the percentile method.

    Resamples *data* with replacement *n_bootstrap* times, applies
    *stat_fn* to each resample, then returns the lower and upper
    percentiles of the bootstrap distribution corresponding to
    *ci_level*.

    Uses a local ``random.Random(42)`` for reproducibility without
    mutating global state.
    """
    if len(data) < 2:
        val = stat_fn(data) if data else 0.0
        return (val, val)

    rng = random.Random(42)
    boot_stats: list[float] = []
    for _ in range(n_bootstrap):
        resample = rng.choices(data, k=len(data))
        boot_stats.append(stat_fn(resample))

    boot_stats.sort()
    alpha = 1.0 - ci_level
    lo = _percentile(boot_stats, 100.0 * (alpha / 2.0))
    hi = _percentile(boot_stats, 100.0 * (1.0 - alpha / 2.0))
    return (lo, hi)


# ── t-distribution CDF (regularized incomplete beta function) ────────


def _ln_beta(a: float, b: float) -> float:
    """Log of the Beta function B(a, b) = Gamma(a)*Gamma(b) / Gamma(a+b)."""
    return math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)


def _betacf(a: float, b: float, x: float) -> float:
    """Evaluate the continued fraction for I_x(a, b) using the modified Lentz method.

    Reference: *Numerical Recipes*, 3rd ed., section 6.4.
    """
    max_iter = 200
    eps = 3.0e-12
    tiny = 1.0e-30

    qab = a + b
    qap = a + 1.0
    qam = a - 1.0

    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < tiny:
        d = tiny
    d = 1.0 / d
    h = d

    for m in range(1, max_iter + 1):
        m2 = 2 * m

        # Even step
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        h *= d * c

        # Odd step
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta

        if abs(delta - 1.0) < eps:
            return h

    return h  # best estimate if convergence not reached


def _regularized_beta(x: float, a: float, b: float) -> float:
    """Regularized incomplete beta function I_x(a, b).

    Equals the CDF of the Beta(a, b) distribution at *x*.
    Uses the symmetry relation for numerical stability when
    x > (a + 1) / (a + b + 2).
    """
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0

    ln_front = -_ln_beta(a, b) + a * math.log(x) + b * math.log(1.0 - x)
    front = math.exp(ln_front)

    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1.0 - x) / b


def _t_cdf(t: float, df: float) -> float:
    """CDF of Student's t-distribution with *df* degrees of freedom.

    Uses the identity  CDF(t, v) = 1 - 0.5 * I_x(v/2, 1/2)
    where x = v / (v + t**2).
    """
    if df <= 0:
        return 0.5
    x = df / (df + t * t)
    ib = _regularized_beta(x, df / 2.0, 0.5)
    cdf = 1.0 - 0.5 * ib
    if t < 0:
        cdf = 1.0 - cdf
    return cdf


# ── Welch's t-test ───────────────────────────────────────────────────


def _welch_t_test(a: Sequence[float], b: Sequence[float]) -> tuple[float, float]:
    """Welch's t-test returning ``(t_statistic, p_value)``.

    Uses the Welch-Satterthwaite approximation for degrees of freedom
    and approximates the p-value from the t-distribution using the
    regularized incomplete beta function.

    Returns ``(0.0, 1.0)`` when the test cannot be computed (e.g. n < 2
    or zero variance in both samples).
    """
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return (0.0, 1.0)

    mean_a = statistics.mean(a)
    mean_b = statistics.mean(b)
    var_a = statistics.variance(a)
    var_b = statistics.variance(b)

    denom_sq = var_a / na + var_b / nb
    if denom_sq <= 0.0:
        return (0.0, 1.0)

    t_stat = (mean_a - mean_b) / math.sqrt(denom_sq)

    # Welch-Satterthwaite degrees of freedom
    num = denom_sq * denom_sq
    den = (var_a / na) ** 2 / (na - 1) + (var_b / nb) ** 2 / (nb - 1)
    if den <= 0.0:
        return (0.0, 1.0)
    df = num / den

    # Two-tailed p-value
    p_value = 2.0 * (1.0 - _t_cdf(abs(t_stat), df))
    return (t_stat, p_value)


# ── Cohen's d ────────────────────────────────────────────────────────


def _cohens_d(a: Sequence[float], b: Sequence[float]) -> float:
    """Cohen's d effect size with pooled standard deviation.

    Positive when mean(a) > mean(b).
    Returns 0.0 when the pooled standard deviation is zero.
    """
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return 0.0

    mean_a = statistics.mean(a)
    mean_b = statistics.mean(b)
    var_a = statistics.variance(a)
    var_b = statistics.variance(b)

    pooled_var = ((na - 1) * var_a + (nb - 1) * var_b) / (na + nb - 2)
    if pooled_var <= 0.0:
        return 0.0

    return (mean_a - mean_b) / math.sqrt(pooled_var)


def _effect_label(d: float) -> str:
    """Classify Cohen's d magnitude into a human-readable label."""
    d_abs = abs(d)
    if d_abs < 0.2:
        return "negligible"
    if d_abs < 0.5:
        return "small"
    if d_abs < 0.8:
        return "medium"
    return "large"


# ── Simple linear regression ────────────────────────────────────────


def _slope(ys: Sequence[float]) -> float:
    """Slope of ``y = a + bx`` where x values are 0, 1, ..., n-1.

    Returns 0.0 for sequences shorter than 2.
    """
    n = len(ys)
    if n < 2:
        return 0.0

    x_mean = (n - 1) / 2.0
    y_mean = statistics.mean(ys)

    num = 0.0
    den = 0.0
    for i, y in enumerate(ys):
        dx = i - x_mean
        num += dx * (y - y_mean)
        den += dx * dx

    if den == 0.0:
        return 0.0
    return num / den


# ── Public API ───────────────────────────────────────────────────────


def compute_stats(
    samples: Sequence[float],
    ci_level: float = 0.95,
    n_bootstrap: int = 10_000,
) -> BenchStats:
    """Compute comprehensive statistics with bootstrap CI and MAD outlier detection.

    Parameters
    ----------
    samples : sequence of float
        Raw benchmark measurements.
    ci_level : float
        Confidence level for the bootstrap interval (default 0.95 = 95%).
    n_bootstrap : int
        Number of bootstrap resamples (default 10 000).

    Returns
    -------
    BenchStats
        Frozen dataclass with all computed fields.

    Raises
    ------
    ValueError
        If *samples* is empty.

    Edge cases
    ----------
    - **n = 1**: stddev, mad, iqr are 0; CI equals the sole value.
    - **n = 2**: bootstrap CI is computed; MAD may be 0.
    - **All identical**: stddev = 0, mad = 0, no outliers detected.
    """
    if not samples:
        raise ValueError("compute_stats requires at least one sample")

    data = list(samples)
    n = len(data)
    mean = statistics.mean(data)
    med = statistics.median(data)
    stddev = statistics.stdev(data) if n >= 2 else 0.0
    med_ad = _mad(data)

    # Quartiles
    if n >= 2:
        quartiles = statistics.quantiles(data, n=4, method="inclusive")
        q1, _q2, q3 = quartiles
    else:
        q1 = q3 = med

    iqr = q3 - q1
    p90 = _percentile(data, 90.0)
    p99 = _percentile(data, 99.0)

    # Bootstrap CI on the median
    ci_lower, ci_upper = _bootstrap_ci(data, statistics.median, ci_level, n_bootstrap)

    # MAD-based outlier detection
    # Consistency constant 1.4826 makes MAD a consistent estimator of
    # the standard deviation for normally distributed data.
    if med_ad > 0.0:
        threshold = 3.0 * med_ad * 1.4826
        clean = [x for x in data if abs(x - med) <= threshold]
        outlier_count = n - len(clean)
    else:
        # MAD == 0 means at least half the values equal the median.
        # Any value that differs from the median is an outlier (it is
        # infinitely many scaled-MADs away from the centre).
        clean = [x for x in data if x == med]
        outlier_count = n - len(clean)

    return BenchStats(
        n=n,
        mean=mean,
        median=med,
        stddev=stddev,
        mad=med_ad,
        q1=q1,
        q3=q3,
        iqr=iqr,
        p90=p90,
        p99=p99,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        outlier_count=outlier_count,
        clean_samples=clean,
    )


def detect_warmup(samples: Sequence[float], threshold: float = 0.05) -> WarmupResult:
    """Detect warmup using a linear regression trend test.

    Fits ``y = a + bx`` to *samples*.  If the normalised slope
    ``|slope * n / mean|`` exceeds *threshold*, the first sample is
    removed and the test is repeated until the slope becomes
    non-significant or half the samples have been consumed.

    Parameters
    ----------
    samples : sequence of float
        Ordered benchmark measurements (first = earliest).
    threshold : float
        Maximum tolerable normalised slope (default 0.05 = 5%).

    Returns
    -------
    WarmupResult
        ``warmup_end = 0`` when no warmup is detected.
    """
    data = list(samples)
    n = len(data)

    if n < 4:
        # Too few data points to detect warmup meaningfully.
        return WarmupResult(warmup_end=0, steady_samples=data)

    removed = 0
    max_remove = n // 2

    while removed < max_remove:
        window = data[removed:]
        m = statistics.mean(window)
        if m == 0.0:
            break
        b = _slope(window)
        normalised = abs(b * len(window) / m)
        if normalised <= threshold:
            break
        removed += 1

    if removed == 0:
        return WarmupResult(warmup_end=0, steady_samples=data)
    return WarmupResult(warmup_end=removed, steady_samples=data[removed:])


def compare_runs(
    baseline: Sequence[float],
    contender: Sequence[float],
    alpha: float = 0.05,
) -> RegressionResult:
    """Compare two sets of benchmark samples using Welch's t-test + Cohen's d.

    *baseline* is the reference run; *contender* is the new run.
    A positive ``pct_change`` means the contender is *slower* (higher
    values).  ``changed`` is ``True`` only when the p-value is below
    *alpha*.

    Parameters
    ----------
    baseline : sequence of float
        Reference benchmark samples.
    contender : sequence of float
        New benchmark samples to compare against the baseline.
    alpha : float
        Significance level (default 0.05).

    Returns
    -------
    RegressionResult
        ``changed=False`` and ``direction="unchanged"`` when the
        difference is not statistically significant, or when inputs
        are too small for meaningful comparison.
    """
    if len(baseline) < 2 or len(contender) < 2:
        return RegressionResult(
            changed=False,
            direction="unchanged",
            pct_change=0.0,
            p_value=1.0,
            cohens_d=0.0,
            effect_label="negligible",
        )

    t_stat, p_value = _welch_t_test(baseline, contender)
    d = _cohens_d(baseline, contender)

    mean_base = statistics.mean(baseline)
    mean_cont = statistics.mean(contender)

    if mean_base != 0.0:
        pct = ((mean_cont - mean_base) / abs(mean_base)) * 100.0
    else:
        pct = 0.0 if mean_cont == 0.0 else math.copysign(math.inf, mean_cont)

    significant = p_value < alpha

    if not significant:
        direction = "unchanged"
    elif mean_cont > mean_base:
        direction = "slower"
    elif mean_cont < mean_base:
        direction = "faster"
    else:
        direction = "unchanged"

    return RegressionResult(
        changed=significant,
        direction=direction,
        pct_change=pct,
        p_value=p_value,
        cohens_d=d,
        effect_label=_effect_label(d),
    )
