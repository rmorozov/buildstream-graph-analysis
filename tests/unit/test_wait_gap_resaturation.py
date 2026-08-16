"""Tests for UX-19: two real, previously-documented gap shapes in
`_classify_wait_gap`'s composition of RESOURCE_WAIT/SCHEDULER_WAIT/
RETRY_WAIT/DEPENDENCY_WAIT sub-segments, independently reconfirmed by an
external review and traced back to `P1-30`/`P1-39`'s own explicit,
named deferrals:

1. Re-saturation within a gap's remainder: after a RESOURCE_WAIT prefix
   ends and the remainder is checked for SCHEDULER_WAIT, if the
   resource saturates *again* later within that same remainder, the
   old single point-check-plus-sweep couldn't detect it - that later
   portion fell through to whatever the remainder's classification
   ended up being (usually SCHEDULER_WAIT, since its own "evidence
   exists somewhere in this window" semantic doesn't distinguish a
   later re-saturation from a genuine scheduler-wait moment).
2. Retry gaps with no other real predecessor: `classify_resource_wait`/
   `classify_scheduler_wait` used to check `task.start_us <=
   task.ready_us` directly (the Part 7 "no predecessor" fallback's
   degenerate `ready_us == start_us`), ignoring whatever real,
   non-degenerate window `_classify_wait_gap` had actually been given
   (`retry_pred.finish_us` through `task.start_us`, already extended by
   `build_blame_chain` before calling it) - so genuine contention
   during a retry's sequencing gap could never be detected, and the
   whole gap defaulted to RETRY_WAIT regardless.

Both fixes must preserve every existing `P1-30`/`P1-31`/`P1-32`/`P1-39`
test's own behavior unchanged (see those test files - not duplicated
here) and I4 (Sigma attribution == H) exactly.
"""
import json

from bga import analyze_run
from bga.attribution.blame_chain import BlameChainAnalyzer
from bga.ingest.models import AttributionCategory, NormalizedTask, Resource, TaskKey, TaskKind


def _task(uid, ready_us, start_us, finish_us, resources=(Resource.PROCESS,), attempt=0, task_kind=TaskKind.BUILD):
    return NormalizedTask(
        task_key=TaskKey(uid, task_kind, "BUILD", attempt),
        ready_us=ready_us, start_us=start_us, finish_us=finish_us,
        resources=list(resources),
    )


# --- Fix 1: re-saturation within a gap's remainder ----------------------

def test_resource_wait_reports_a_second_segment_for_re_saturation():
    """waiting.bst is ready at 0, starts at 300: holder_a saturates
    PROCESS [0, 100) (capacity=1), genuinely free [100, 200) (no other
    task active, max_jobs=2 - real scheduler-wait evidence), then
    holder_b saturates PROCESS again [200, 300). Must produce
    RESOURCE_WAIT, SCHEDULER_WAIT, RESOURCE_WAIT in that order - not
    swallow the second RESOURCE_WAIT into an extended SCHEDULER_WAIT."""
    waiting = _task("waiting.bst", ready_us=0, start_us=300, finish_us=400)
    holder_a = _task("holder_a.bst", ready_us=0, start_us=0, finish_us=100)
    holder_b = _task("holder_b.bst", ready_us=0, start_us=200, finish_us=300)
    analyzer = BlameChainAnalyzer(
        normalized_tasks=[waiting, holder_a, holder_b],
        resource_capacity={Resource.PROCESS: 1},
        max_jobs=2,
    )

    segments, holder_info = analyzer._classify_wait_gap(waiting, 0, 300)

    assert segments == [
        (AttributionCategory.RESOURCE_WAIT, 0, 100),
        (AttributionCategory.SCHEDULER_WAIT, 100, 200),
        (AttributionCategory.RESOURCE_WAIT, 200, 300),
    ]
    # holder_info is the *first* RESOURCE_WAIT segment's info (interface
    # stability - see _classify_wait_gap's own docstring); every segment
    # is still present in `segments` regardless.
    assert holder_info["explained_us"] == 100
    assert holder_info["blocking_tasks"] == {"holder_a.bst|BUILD|BUILD|0": 1.0}


def test_single_saturation_cycle_is_unaffected_by_the_loop():
    """Regression guard: the exact P1-39 shape (one RESOURCE_WAIT prefix,
    one SCHEDULER_WAIT remainder, no re-saturation) must produce
    identical segments to before this fix - the loop must degenerate to
    the prior single-pass behavior when there's only one cycle."""
    waiting = _task("waiting.bst", ready_us=0, start_us=200, finish_us=300)
    holder_a = _task("holder_a.bst", ready_us=0, start_us=0, finish_us=100)
    holder_b = _task("holder_b.bst", ready_us=0, start_us=0, finish_us=100)
    analyzer = BlameChainAnalyzer(
        normalized_tasks=[waiting, holder_a, holder_b],
        resource_capacity={Resource.PROCESS: 2},
        max_jobs=2,
    )

    segments, holder_info = analyzer._classify_wait_gap(waiting, 0, 200)

    assert segments == [
        (AttributionCategory.RESOURCE_WAIT, 0, 100),
        (AttributionCategory.SCHEDULER_WAIT, 100, 200),
    ]
    assert holder_info["explained_us"] == 100


def test_end_to_end_re_saturation_produces_two_resource_wait_segments_and_identity_holds(tmp_path):
    """Full pipeline (analyze_run), the same re-saturation shape as
    test_resource_wait_reports_a_second_segment_for_re_saturation,
    confirming the fix reaches real attribution totals and I4 (Sigma ==
    H) still holds exactly - not just the direct _classify_wait_gap
    unit-level result."""
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    graph = {
        "elements": [
            {"uid": "trigger.bst", "requested_target": False},
            {"uid": "holder_a.bst", "requested_target": False},
            {"uid": "holder_b.bst", "requested_target": False},
            {"uid": "waiting.bst", "requested_target": True},
        ],
        "dependencies": [
            {"predecessor": "trigger.bst", "successor": "waiting.bst"},
        ],
    }
    trace = {
        "spans": [
            {"task_key": "trigger.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": 0,
             "resources": [], "primary_resource": None},
            {"task_key": "holder_a.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": 100,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
            {"task_key": "holder_b.bst|BUILD|BUILD|0", "ts_us": 200, "dur_us": 100,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
            {"task_key": "waiting.bst|BUILD|BUILD|0", "ts_us": 300, "dur_us": 100,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
        ],
        "phases": [],
    }
    run_context = {
        "trace_epsilon_us": 10, "wall_start_us": 0, "wall_end_us": 400,
        "resource_capacities": {"PROCESS": 1}, "max_jobs": 2,
    }
    (run_dir / "run-context.json").write_text(json.dumps(run_context))
    (run_dir / "graph.json").write_text(json.dumps(graph))
    (run_dir / "trace.json").write_text(json.dumps(trace))

    result = analyze_run(run_dir)
    h = result.occupancy["horizon_us"]

    total = sum(
        result.attribution.get(k, 0)
        for k in (
            "execution_on_chain_us", "dependency_wait_us", "resource_wait_us",
            "scheduler_wait_us", "idle_us", "retry_wait_us",
        )
    )
    assert result.attribution["resource_wait_us"] == 200  # both RESOURCE_WAIT segments, 100us each
    assert result.attribution["scheduler_wait_us"] == 100
    assert total == h
    assert not any(v.get("invariant") == "I4" for v in result.violations)


# --- Fix 2: retry gaps with no other real predecessor -------------------

def test_retry_gap_resource_contention_is_detected_not_swallowed_by_retry_wait():
    """attempt0 finishes at 50000. attempt1 (retry) is ready at 150000
    exactly (Part 7's degenerate "no predecessor" fallback,
    ready_us==start_us) - but build_blame_chain would extend the real
    gap_start to attempt0's own finish (50000), the same real window
    this test passes directly. holder.bst genuinely saturates PROCESS
    for the first half of that real window [50000, 100000) - must be
    detected as RESOURCE_WAIT, not swallowed into a RETRY_WAIT-only
    breakdown for the whole gap."""
    attempt0 = _task("a.bst", ready_us=0, start_us=0, finish_us=50000)
    attempt1 = _task("a.bst", ready_us=150000, start_us=150000, finish_us=200000, attempt=1)
    holder = _task("holder.bst", ready_us=0, start_us=50000, finish_us=100000)
    analyzer = BlameChainAnalyzer(
        normalized_tasks=[attempt0, attempt1, holder],
        resource_capacity={Resource.PROCESS: 1},
    )

    # Mirrors build_blame_chain's own retry-extension: gap_start is
    # retry_pred.finish_us (50000), not attempt1.ready_us (150000).
    segments, holder_info = analyzer._classify_wait_gap(attempt1, 50000, 150000)

    assert segments == [
        (AttributionCategory.RESOURCE_WAIT, 50000, 100000),
        (AttributionCategory.RETRY_WAIT, 100000, 150000),
    ]
    assert holder_info["explained_us"] == 50000
    assert holder_info["blocking_tasks"] == {"holder.bst|BUILD|BUILD|0": 1.0}


def test_retry_gap_without_contention_still_falls_back_to_retry_wait_entirely():
    """Regression guard: no holder task at all during the retry gap -
    must still produce the pre-fix behavior (the whole gap is
    RETRY_WAIT), confirming the fix distinguishes "genuine contention
    exists" from "nothing to detect", not just always splitting."""
    attempt0 = _task("a.bst", ready_us=0, start_us=0, finish_us=50000)
    attempt1 = _task("a.bst", ready_us=150000, start_us=150000, finish_us=200000, attempt=1)
    analyzer = BlameChainAnalyzer(
        normalized_tasks=[attempt0, attempt1],
        resource_capacity={Resource.PROCESS: 1},
    )

    segments, holder_info = analyzer._classify_wait_gap(attempt1, 50000, 150000)

    assert segments == [(AttributionCategory.RETRY_WAIT, 50000, 150000)]
    assert holder_info is None


def test_end_to_end_retry_gap_with_contention_and_identity_holds(tmp_path):
    """Full pipeline: a.bst's BUILD attempt 0 finishes at 50000; a real
    holder occupies PROCESS [50000, 100000); attempt 1 finally starts at
    150000. Must produce a real, non-zero resource_wait_us alongside
    retry_wait_us for the same element's retry gap, and I4 must still
    hold exactly."""
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    graph = {
        "elements": [
            {"uid": "holder.bst", "requested_target": False},
            {"uid": "a.bst", "requested_target": True},
        ],
        "dependencies": [],
    }
    trace = {
        "spans": [
            {"task_key": "a.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": 50000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
            {"task_key": "holder.bst|BUILD|BUILD|0", "ts_us": 50000, "dur_us": 50000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
            {"task_key": "a.bst|BUILD|BUILD|1", "ts_us": 150000, "dur_us": 50000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
        ],
        "phases": [],
    }
    run_context = {
        "trace_epsilon_us": 50000, "wall_start_us": 0, "wall_end_us": 200000,
        "resource_capacities": {"PROCESS": 1},
    }
    (run_dir / "run-context.json").write_text(json.dumps(run_context))
    (run_dir / "graph.json").write_text(json.dumps(graph))
    (run_dir / "trace.json").write_text(json.dumps(trace))

    result = analyze_run(run_dir)
    h = result.occupancy["horizon_us"]

    total = sum(
        result.attribution.get(k, 0)
        for k in (
            "execution_on_chain_us", "dependency_wait_us", "resource_wait_us",
            "scheduler_wait_us", "idle_us", "retry_wait_us",
        )
    )
    assert result.attribution["resource_wait_us"] == 50000
    assert result.attribution["retry_wait_us"] == 50000
    assert total == h
    assert not any(v.get("invariant") == "I4" for v in result.violations)
