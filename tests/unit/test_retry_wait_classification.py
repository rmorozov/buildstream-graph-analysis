"""Tests for P1-30 (fixed): RETRY_WAIT (Part 11.1's "delay caused by retry
sequencing") had zero implementation anywhere - `TaskAttribution.retry_wait_us`
and `reconciled['RETRY_WAIT']` were structurally always 0 regardless of
whether a run actually contained retried tasks.

A retry attempt (Part 5.2's `attempt` field > 0) cannot have started before
the prior attempt of the same `element_uid|task_kind|phase` finished, but
`graph.json`'s dependency edges (Part 32.2) have no way to express this -
they're between elements, not between attempts of one task. `_retry_predecessor`
recovers this real, evidenced relationship directly from the trace's own
`attempt` field, and `_classify_wait_gap`'s fallback (previously always
DEPENDENCY_WAIT) now defaults to RETRY_WAIT for any task identified as a
retry, following the same "real classifier, wired into the actual
segment-construction path" pattern P1-01/P1-02/P1-20 established for
RESOURCE_WAIT/SCHEDULER_WAIT.
"""
import json

from bga import analyze_run
from bga.attribution.blame_chain import BlameChainAnalyzer
from bga.ingest.models import AttributionCategory, NormalizedTask, TaskKey, TaskKind


def _task(uid, task_kind, phase, attempt, ready_us, start_us, finish_us, resources=None):
    return NormalizedTask(
        task_key=TaskKey(element_uid=uid, task_kind=task_kind, phase=phase, attempt=attempt),
        ready_us=ready_us,
        start_us=start_us,
        finish_us=finish_us,
        resources=resources or [],
    )


def _analyzer(tasks):
    return BlameChainAnalyzer(normalized_tasks=tasks)


# --- _retry_predecessor: direct unit tests -----------------------------

def test_retry_predecessor_found_for_second_attempt():
    attempt0 = _task("a.bst", TaskKind.BUILD, "BUILD", 0, 0, 0, 100000)
    attempt1 = _task("a.bst", TaskKind.BUILD, "BUILD", 1, 100000, 150000, 200000)
    analyzer = _analyzer([attempt0, attempt1])

    pred = analyzer._retry_predecessor(attempt1)

    assert pred is attempt0


def test_retry_predecessor_none_for_first_attempt():
    attempt0 = _task("a.bst", TaskKind.BUILD, "BUILD", 0, 0, 0, 100000)
    analyzer = _analyzer([attempt0])

    assert analyzer._retry_predecessor(attempt0) is None


def test_retry_predecessor_none_when_no_prior_attempt_recorded():
    """attempt=1 present but attempt=0 was never captured in the trace -
    no predecessor to identify, must not fabricate one."""
    attempt1 = _task("a.bst", TaskKind.BUILD, "BUILD", 1, 100000, 150000, 200000)
    analyzer = _analyzer([attempt1])

    assert analyzer._retry_predecessor(attempt1) is None


def test_retry_predecessor_ignores_different_task_kind_or_phase():
    """A same-element, same-attempt-number task of a *different* task_kind
    or phase is not a retry predecessor - retries are scoped to the exact
    same element_uid|task_kind|phase (Part 5.2)."""
    fetch0 = _task("a.bst", TaskKind.FETCH, "FETCH", 0, 0, 0, 50000)
    build1 = _task("a.bst", TaskKind.BUILD, "BUILD", 1, 50000, 60000, 100000)
    analyzer = _analyzer([fetch0, build1])

    assert analyzer._retry_predecessor(build1) is None


def test_retry_predecessor_picks_the_immediately_preceding_attempt():
    """Three attempts (0, 1, 2) - attempt 2's retry predecessor is attempt
    1 (the immediately preceding one), not attempt 0."""
    attempt0 = _task("a.bst", TaskKind.BUILD, "BUILD", 0, 0, 0, 100000)
    attempt1 = _task("a.bst", TaskKind.BUILD, "BUILD", 1, 100000, 100000, 200000)
    attempt2 = _task("a.bst", TaskKind.BUILD, "BUILD", 2, 200000, 250000, 300000)
    analyzer = _analyzer([attempt0, attempt1, attempt2])

    assert analyzer._retry_predecessor(attempt2) is attempt1


# --- _classify_wait_gap: fallback classification -----------------------

def test_wait_gap_for_retry_task_defaults_to_retry_wait_not_dependency_wait():
    attempt0 = _task("a.bst", TaskKind.BUILD, "BUILD", 0, 0, 0, 100000)
    attempt1 = _task("a.bst", TaskKind.BUILD, "BUILD", 1, 100000, 150000, 200000)
    analyzer = _analyzer([attempt0, attempt1])

    segments, _holder_info = analyzer._classify_wait_gap(attempt1, 100000, 150000)

    assert segments == [(AttributionCategory.RETRY_WAIT, 100000, 150000)]


def test_wait_gap_for_non_retry_task_still_defaults_to_dependency_wait():
    """Regression: a task with no retry predecessor must be unaffected -
    the existing DEPENDENCY_WAIT fallback stays exactly as before."""
    task = _task("a.bst", TaskKind.BUILD, "BUILD", 0, 0, 50000, 100000)
    analyzer = _analyzer([task])

    segments, _holder_info = analyzer._classify_wait_gap(task, 0, 50000)

    assert segments == [(AttributionCategory.DEPENDENCY_WAIT, 0, 50000)]


# --- End-to-end: full pipeline via analyze_run --------------------------

def _write_run_dir(tmp_path, run_context, elements, dependencies, spans):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    graph = {
        "elements": [
            {"uid": uid, "requested_target": is_target}
            for uid, is_target in elements
        ],
        "dependencies": [
            {"predecessor": pred, "successor": succ} for pred, succ in dependencies
        ],
    }
    trace = {"spans": spans, "phases": []}
    (run_dir / "run-context.json").write_text(json.dumps(run_context))
    (run_dir / "graph.json").write_text(json.dumps(graph))
    (run_dir / "trace.json").write_text(json.dumps(trace))
    return run_dir


def _attribution_total(result):
    return sum(
        result.attribution.get(k, 0)
        for k in (
            "execution_on_chain_us", "dependency_wait_us", "resource_wait_us",
            "scheduler_wait_us", "idle_us", "retry_wait_us",
        )
    )


def test_end_to_end_retry_gap_produces_nonzero_retry_wait_and_identity_holds(tmp_path):
    """The task file's own acceptance test scenario: a.bst's BUILD attempt
    0 finishes at 100000, then a gap, then attempt 1 starts at 150000 and
    finishes at 200000. No cross-element dependency is involved - the only
    reason attempt 1 didn't start immediately at 100000 is that it's a
    retry of attempt 0. Must produce a nonzero retry_wait_us reflecting
    exactly that 50000us gap, and the I4 identity (Sigma == H) must
    continue to hold exactly.
    """
    run_dir = _write_run_dir(
        tmp_path,
        run_context={
            "trace_epsilon_us": 50000, "wall_start_us": 0, "wall_end_us": 200000,
        },
        elements=[("a.bst", True)],
        dependencies=[],
        spans=[
            {"task_key": "a.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": 100000},
            {"task_key": "a.bst|BUILD|BUILD|1", "ts_us": 150000, "dur_us": 50000},
        ],
    )
    result = analyze_run(run_dir)
    h = result.occupancy["horizon_us"]

    assert result.attribution["retry_wait_us"] == 50000
    assert result.attribution["dependency_wait_us"] == 0
    assert _attribution_total(result) == h
    assert not any(v.get("invariant") == "I4" for v in result.violations)


def test_end_to_end_no_retries_produces_zero_retry_wait(tmp_path):
    """Regression: a run with no retried tasks at all (every task at
    attempt 0, the overwhelming common case) must be entirely unaffected -
    retry_wait_us stays exactly 0, same as before this fix."""
    run_dir = _write_run_dir(
        tmp_path,
        run_context={
            "trace_epsilon_us": 50000, "wall_start_us": 0, "wall_end_us": 100000,
        },
        elements=[("a.bst", False), ("b.bst", True)],
        dependencies=[("a.bst", "b.bst")],
        spans=[
            {"task_key": "a.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": 50000},
            {"task_key": "b.bst|BUILD|BUILD|0", "ts_us": 50000, "dur_us": 50000},
        ],
    )
    result = analyze_run(run_dir)
    h = result.occupancy["horizon_us"]

    assert result.attribution["retry_wait_us"] == 0
    assert _attribution_total(result) == h


def test_end_to_end_retry_attempt_execution_itself_appears_on_chain(tmp_path):
    """The discarded attempt 0's own execution time is real, recognized
    work (Part 11: EXECUTION_ON_CHAIN is "execution interval belonging to
    a task on the measured dependency blame chain") - once the walk
    follows the retry-predecessor link, attempt 0's 100000us of execution
    must be accounted for as EXECUTION_ON_CHAIN, not silently dropped.
    """
    run_dir = _write_run_dir(
        tmp_path,
        run_context={
            "trace_epsilon_us": 50000, "wall_start_us": 0, "wall_end_us": 200000,
        },
        elements=[("a.bst", True)],
        dependencies=[],
        spans=[
            {"task_key": "a.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": 100000},
            {"task_key": "a.bst|BUILD|BUILD|1", "ts_us": 150000, "dur_us": 50000},
        ],
    )
    result = analyze_run(run_dir)

    assert result.attribution["execution_on_chain_us"] == 150000
