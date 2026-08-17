"""UX-59: judge a candidate against the baseline's measured noise, not a
constant.

`_SIGNIFICANCE_PCT = 1` is one number applied to runs of wildly different
size. Seven real repeated builds of one unchanged `examples/06` commit -
six of them the same shape - measured 26.30s … 27.66s, a standard
deviation of **1.8% of the mean**. The fixed rule puts **3 of those 6
identical runs outside the band**, and comparing the fastest against the
slowest reports `REGRESSED (+5.2%)` for a commit in which nothing
changed.

The band shape was chosen by measurement rather than by assertion. At
n=6 the distribution is very nearly symmetric, so skew is *not* the
argument for the median and MAD; robustness to one contaminated baseline
run is. Replacing the slowest run with a 45s outlier widens a mean±3σ
band from 3.00s to 40.64s - at which point it misses a real +15%
regression - while the median±3·MAD band is unchanged and still catches
it.
"""
import pytest

from bga.compare import (
    DEFAULT_BAND_K,
    MIN_BASELINE_RUNS,
    ComparisonResult,
    compute_band,
)

# The six real same-shape runs, in microseconds.
REAL = [26.30e6, 26.91e6, 27.06e6, 27.28e6, 27.51e6, 27.66e6]


def test_the_band_is_derived_from_the_real_spread():
    band = compute_band(REAL)

    assert band["n"] == 6
    assert band["median_us"] == pytest.approx(27.17e6, rel=1e-3)
    assert band["low_us"] < min(REAL) and band["high_us"] > max(REAL)


def test_every_run_of_the_unchanged_commit_falls_inside_it():
    """The property that matters: a band built from a commit's own runs
    must not flag that commit's other runs."""
    band = compute_band(REAL)

    assert all(band["low_us"] <= x <= band["high_us"] for x in REAL)


def test_the_fixed_rule_would_have_flagged_half_of_them():
    """Pinned as the motivation, so the band's value is a measured
    contrast rather than a claim."""
    median = 27.17e6
    outside = [x for x in REAL if abs(x - median) > median * 0.01]

    assert len(outside) == 3


def test_a_real_regression_is_still_caught():
    band = compute_band(REAL)
    regressed = 27.17e6 * 1.15

    assert regressed > band["high_us"]


def test_one_contaminated_baseline_run_does_not_widen_the_band():
    """The actual argument for the median and MAD over the mean and
    standard deviation - not skew, which at this n is negligible."""
    contaminated = REAL[:-1] + [45.0e6]

    clean = compute_band(REAL)
    dirty = compute_band(contaminated)
    width_clean = clean["high_us"] - clean["low_us"]
    width_dirty = dirty["high_us"] - dirty["low_us"]

    assert width_dirty == pytest.approx(width_clean, rel=0.35)
    # ... and a real regression is still outside it.
    assert 27.17e6 * 1.15 > dirty["high_us"]


def test_too_few_runs_yields_no_band():
    """Below the minimum a 'band' restates one or two numbers; the fixed
    percentage is the more honest rule there."""
    assert compute_band(REAL[: MIN_BASELINE_RUNS - 1]) is None
    assert compute_band(REAL[:MIN_BASELINE_RUNS]) is not None


def test_k_widens_the_band():
    narrow = compute_band(REAL, k=1.0)
    wide = compute_band(REAL, k=DEFAULT_BAND_K)

    assert (wide["high_us"] - wide["low_us"]) > (narrow["high_us"] - narrow["low_us"])


def test_identical_baseline_runs_yield_a_zero_width_band():
    """A degenerate input the caller must handle: every run identical
    gives MAD 0, and a band of zero width would make any delta
    significant. `compute_band` reports it rather than inventing a floor
    it has no basis for."""
    band = compute_band([10.0e6] * 5)

    assert band["scaled_mad_us"] == 0
    assert band["low_us"] == band["high_us"]


# --- the verdict, end to end -------------------------------------------


def _compare(baseline_us, candidate_us, band):
    from bga.compare import _compare_results

    class _R:
        def __init__(self, total):
            self.run_id = "r"
            self.total_duration_us = total
            self.floors = {}
            self.confidence = {"primary": 1.0, "run_mode": "incremental"}
            self.attribution = {}
            self.violations = []

    return _compare_results(_R(baseline_us), _R(candidate_us), [], [], baseline_band=band)


def test_a_within_noise_delta_is_no_significant_change():
    """The real pair: 26.30s vs 27.66s, same commit, +5.2%."""
    result = _compare(26.30e6, 27.66e6, compute_band(REAL))

    assert result.verdict == "no significant change"
    assert result.baseline_band is not None


def test_the_same_delta_without_a_band_is_called_a_regression():
    """What the tool does today, kept as the contrast."""
    result = _compare(26.30e6, 27.66e6, None)

    assert result.verdict == "regressed"


def test_a_real_regression_still_regresses_with_a_band():
    result = _compare(26.30e6, 27.17e6 * 1.15, compute_band(REAL))

    assert result.verdict == "regressed"


def test_a_degenerate_band_is_widened_to_the_fixed_rule():
    """Otherwise a set of near-identical baseline runs would make every
    subsequent comparison significant."""
    result = _compare(10.0e6, 10.02e6, compute_band([10.0e6] * 5))

    assert result.baseline_band["widened_to_fixed_pct"] is True
    assert result.verdict == "no significant change"


def test_the_band_is_serialized_for_ci_consumers():
    result = _compare(26.30e6, 27.66e6, compute_band(REAL))

    assert result.to_dict()["baseline_band"]["n"] == 6


def test_a_comparison_without_a_band_serializes_none():
    assert ComparisonResult(
        baseline_run_id="a", candidate_run_id="b",
        baseline_metrics={}, candidate_metrics={}, deltas={},
        baseline_confidence=1.0, candidate_confidence=1.0,
        attribution_deltas={}, verdict="improved", low_confidence=False,
    ).to_dict()["baseline_band"] is None
