"""Tests for UX-39: `--fail-on-regression` gates on `total_duration_us`
alone at a 1% threshold, so it fires on noise, cannot allow legitimately
added work, and is blind to the regression that matters.

The requirement, in a build owner's own words: *adding work is allowed;
adding work inefficiently is not.* Wall-clock cannot express that,
because it moves for both.

Thresholds here are pinned to real measured evidence: three repeat
captures of an unchanged project on one real runner spread 1.0pp of
occupancy (and 7.4% of wall-clock - more than seven times the duration
gate's own default, which is why that gate fires on noise).
"""
from bga.compare import (
    ComparisonResult, _EFFICIENCY_DROP_PP, efficiency_below_floor,
    efficiency_regression_exceeds_threshold,
)


def _comparison(baseline_occupancy, candidate_occupancy):
    """Only the fields the efficiency gate reads - the rest of
    ComparisonResult is exercised by tests/unit/test_compare.py."""
    baseline = {"occupancy_ratio": baseline_occupancy, "total_duration_us": 26_000_000}
    candidate = {"occupancy_ratio": candidate_occupancy, "total_duration_us": 26_000_000}
    deltas = {
        k: (None if candidate[k] is None or baseline[k] is None else candidate[k] - baseline[k])
        for k in baseline
    }
    return ComparisonResult(
        baseline_run_id="b", candidate_run_id="c",
        baseline_metrics=baseline, candidate_metrics=candidate, deltas=deltas,
        baseline_confidence=1.0, candidate_confidence=1.0,
        attribution_deltas={}, verdict="no significant change", low_confidence=False,
    )


# --- the real measured cases ---------------------------------------------

def test_real_macro_micro_regression_fires():
    """The real pair: a well-shaped build reverted to a chained one.
    63.0% -> 27.8% occupancy."""
    assert efficiency_regression_exceeds_threshold(_comparison(0.630, 0.278))


def test_real_oversubscription_regression_fires():
    """Same source, same graph, `--builders 8 --max-jobs 8` on 4 cores
    instead of 4x4: 63.0% -> 48.6%."""
    assert efficiency_regression_exceeds_threshold(_comparison(0.630, 0.486))


def test_real_run_to_run_noise_does_not_fire():
    """Three repeat captures of an *unchanged* project measured 60.0%,
    59.9% and 59.0% - the widest of those pairs must pass."""
    assert not efficiency_regression_exceeds_threshold(_comparison(0.600, 0.590))


def test_the_default_leaves_real_headroom_over_the_measured_noise():
    """1.0pp measured spread against a 5.0pp default. Pinned so a future
    change to either has to confront the ratio deliberately."""
    assert _EFFICIENCY_DROP_PP >= 3.0
    assert not efficiency_regression_exceeds_threshold(_comparison(0.600, 0.600 - 0.01))


# --- the property the gate exists for -------------------------------------

def test_well_parallelized_added_work_does_not_fire():
    """Real measurement: two more fan-out libraries added to the same
    project took wall-clock from 25.98s to 26.64s (+2.5%, which the
    duration gate fails on) while occupancy *rose* 60.0% -> 73.8%.
    Adding work is allowed; adding it badly is not."""
    assert not efficiency_regression_exceeds_threshold(_comparison(0.600, 0.738))


def test_serialized_added_work_does_fire():
    """The same amount of new work, chained instead of fanned out."""
    assert efficiency_regression_exceeds_threshold(_comparison(0.600, 0.480))


# --- knobs and edges ------------------------------------------------------

def test_an_explicit_threshold_overrides_the_default():
    assert efficiency_regression_exceeds_threshold(_comparison(0.600, 0.590), max_drop_pp=0.5)
    assert not efficiency_regression_exceeds_threshold(_comparison(0.630, 0.486), max_drop_pp=20.0)


def test_an_improvement_never_fires():
    assert not efficiency_regression_exceeds_threshold(_comparison(0.278, 0.630))


def test_a_missing_metric_never_fabricates_a_verdict():
    assert not efficiency_regression_exceeds_threshold(_comparison(None, 0.400))
    assert not efficiency_regression_exceeds_threshold(_comparison(0.600, None))


# --- the absolute floor ---------------------------------------------------

def test_the_floor_is_a_property_of_the_candidate_alone():
    """No baseline is consulted - which is what makes it usable on a
    first run, and what stops a slow drift no single delta ever trips."""
    assert efficiency_below_floor(_comparison(0.900, 0.486), min_efficiency=0.55)
    assert not efficiency_below_floor(_comparison(0.100, 0.630), min_efficiency=0.55)


def test_the_floor_is_off_unless_declared():
    """No default: what counts as acceptable is a statement about a
    specific project, not a universal constant."""
    assert not efficiency_below_floor(_comparison(0.900, 0.100))


def test_the_floor_never_fabricates_a_verdict_either():
    assert not efficiency_below_floor(_comparison(0.600, None), min_efficiency=0.55)
