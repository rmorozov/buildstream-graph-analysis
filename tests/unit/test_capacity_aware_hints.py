"""Tests for UX-35: `UX-04`'s next-step hints are constant strings chosen
by attribution category alone, consulting none of the capacity facts the
tool has. `RESOURCE_WAIT`'s says "try --capacity N with a higher N",
which a real run of `examples/06-macro-micro-optimization/optimized`
printed while already dispatching up to 16 potential concurrent processes
on a 4-core host - the opposite of the fix.

The verdict is *consumed*, never re-derived: two independently-derived
capacity formulas comparing the same real inputs is the divergence
`UX-17` was resolved to avoid.
"""
from bga.analyzer import BuildEfficiencyAnalyzer
from bga.ingest.models import AttributionCategory, RunContext
from bga.report._shared import (
    ATTRIBUTION_CATEGORY_HINTS, ATTRIBUTION_CATEGORY_HINTS_BY_KEY,
    resolve_attribution_hint,
)

_RESOURCE_WAIT = "resource_wait_us"


def _verdict(oversubscribed=False, checks_ran=True):
    return {
        "oversubscribed": oversubscribed,
        "undersubscribed": False,
        "checks_ran": checks_ran,
        "skipped_inputs": [] if checks_ran else ["native_max_jobs"],
    }


def test_an_oversubscribed_run_is_not_told_to_raise_capacity():
    hint = resolve_attribution_hint(_RESOURCE_WAIT, _verdict(oversubscribed=True))
    assert "already oversubscribed" in hint
    assert "higher N" not in hint


def test_an_under_provisioned_run_still_gets_the_original_advice():
    hint = resolve_attribution_hint(_RESOURCE_WAIT, _verdict())
    assert hint == ATTRIBUTION_CATEGORY_HINTS_BY_KEY[_RESOURCE_WAIT]
    assert "higher N" in hint


def test_a_run_whose_capacity_checks_did_not_run_says_so():
    """"The checks found nothing" and "the checks could not run" are
    different, and advice conditioned on the second as if it were the
    first is the failure this task is about."""
    hint = resolve_attribution_hint(_RESOURCE_WAIT, _verdict(checks_ran=False))
    assert "unconditioned" in hint
    assert "higher N" not in hint


def test_no_verdict_at_all_is_treated_as_unknown_not_as_fine():
    for verdict in (None, {}):
        hint = resolve_attribution_hint(_RESOURCE_WAIT, verdict)
        assert "unconditioned" in hint


def test_every_other_category_resolves_to_its_unchanged_static_hint():
    """Only RESOURCE_WAIT's *direction* depends on capacity; the other
    seven were re-read in the same pass and none of them advises a
    direction capacity could invert."""
    for category in AttributionCategory:
        key = f"{category.value.lower()}_us"
        if key == _RESOURCE_WAIT:
            continue
        for verdict in (None, _verdict(), _verdict(oversubscribed=True)):
            assert resolve_attribution_hint(key, verdict) == ATTRIBUTION_CATEGORY_HINTS[category]


def test_every_category_still_has_a_hint():
    """P4-02's own guard, re-asserted through the new resolver: a future
    category must not silently resolve to None."""
    for category in AttributionCategory:
        key = f"{category.value.lower()}_us"
        assert resolve_attribution_hint(key, _verdict()) is not None


# --- the verdict the resolver consumes -----------------------------------

def _analyzer(builders, native_max_jobs=None, host_cpu_count=None):
    analyzer = BuildEfficiencyAnalyzer()
    analyzer.run_context = RunContext(
        resource_capacities={"PROCESS": builders},
        native_max_jobs=native_max_jobs,
        host_cpu_count=host_cpu_count,
    )
    analyzer._check_process_oversubscription()
    return analyzer


def test_verdict_reports_oversubscription_from_the_real_check():
    """UX-09's measured-slower configuration on its real 4-core host."""
    verdict = _analyzer(8, 8, 4)._build_capacity_verdict()
    assert verdict["oversubscribed"] is True
    assert verdict["checks_ran"] is True


def test_verdict_reports_a_healthy_run_as_neither():
    """UX-09's measured-fastest configuration."""
    verdict = _analyzer(4, 4, 4)._build_capacity_verdict()
    assert verdict["oversubscribed"] is False
    assert verdict["undersubscribed"] is False
    assert verdict["checks_ran"] is True


def test_verdict_distinguishes_checks_that_could_not_run():
    verdict = _analyzer(4)._build_capacity_verdict()
    assert verdict["checks_ran"] is False
    assert "native_max_jobs" in verdict["skipped_inputs"]
    assert verdict["oversubscribed"] is False  # absence of evidence, not evidence
