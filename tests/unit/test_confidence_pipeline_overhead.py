"""Tests for UX-40: real captures landed at ~0.69 confidence ("medium")
because BuildStream's own measured startup counted against
`attribution_score`, and `bga compare --fail-on-regression` fails *open*
below 0.8 - so the CI gate was silently off on exactly the small, fast
projects most likely to run it.

The interaction is systematic, not incidental: UX-10 deliberately made
`total_duration_us` prefer real wall-clock so startup would stop being
invisible, and the shorter the build, the larger BuildStream's fixed
startup is as a fraction of it.
"""
from bga.ingest.models import Element, Graph, NormalizedTask, RunContext, TaskKey, TaskKind
from bga.validation.invariants import compute_confidence


def _task(uid, start_us, finish_us):
    return NormalizedTask(
        task_key=TaskKey(uid, TaskKind.BUILD, "BUILD", 0),
        ready_us=start_us, start_us=start_us, finish_us=finish_us,
    )


def _confidence(untracked_head_us, pipeline_overhead=None):
    graph = Graph(elements=[Element(uid="a.bst")])
    tasks = [_task("a.bst", 0, 7_000_000)]
    run_context = RunContext(
        resource_capacities={"PROCESS": 1},
        pipeline_overhead=pipeline_overhead or [],
    )
    confidence, _violations = compute_confidence(
        normalized_tasks=tasks,
        run_context=run_context,
        trace=None,
        graph=graph,
        violations=[],
        attribution_segments=[],
        graph_analysis={"critical_path": ["a.bst"], "dominators": {"a.bst": []}},
        attribution={
            "untracked_head_us": untracked_head_us,
            "untracked_tail_us": 0,
            "execution_on_chain_us": 7_000_000,
        },
        floors={},
    )
    return confidence


_REAL_OVERHEAD = [
    {"phase": "Loading elements", "elapsed_us": 2_000},
    {"phase": "Resolving elements", "elapsed_us": 1_887_000},
    {"phase": "Initializing remote caches", "elapsed_us": 0},
    {"phase": "Query cache", "elapsed_us": 0},
]


def test_explained_startup_no_longer_drags_confidence_down():
    """The real shape of a real capture: a ~3.2s untracked head on a
    ~10s build, most of it BuildStream resolving elements."""
    without = _confidence(3_170_000)
    with_overhead = _confidence(3_170_000, _REAL_OVERHEAD)
    assert with_overhead["attribution_score"] > without["attribution_score"]
    assert with_overhead["explained_untracked_us"] == 1_889_000


def test_attribution_score_crosses_the_gate_threshold():
    """The consequence that matters: `attribution_score` was the single
    sub-score dragging real captures under the 0.8 bar that
    `bga compare --fail-on-regression` fails open below, and it crosses
    back over it. (`primary` is a `min()` over four sub-scores, and this
    hermetic fixture carries no run identity, so its own provenance
    score gates it separately - that is a different, real gate and not
    what this task is about. Confirmed against a real capture instead:
    examples/05-cmake-cpp-toolchain went 0.694 -> 0.869 primary.)"""
    from bga.report.text import _CONFIDENCE_HIGH

    assert _confidence(3_170_000)["attribution_score"] < _CONFIDENCE_HIGH
    assert _confidence(3_170_000, _REAL_OVERHEAD)["attribution_score"] >= _CONFIDENCE_HIGH


def test_genuinely_unexplained_untracked_time_still_counts_in_full():
    """Only the explained portion is forgiven - this is not a blanket
    exemption for untracked time."""
    result = _confidence(3_170_000, _REAL_OVERHEAD)
    unexplained = 3_170_000 - 1_889_000
    horizon = 7_000_000 + 3_170_000
    assert result["attribution_score"] == 1.0 - (unexplained / horizon)


def test_overhead_larger_than_the_untracked_head_cannot_over_credit():
    """Pipeline phases can overlap tracked task time, so the sum can
    exceed the untracked head. Crediting more than the head existed
    would inflate the score above what was actually measured."""
    result = _confidence(
        500_000, [{"phase": "Resolving elements", "elapsed_us": 5_000_000}],
    )
    assert result["explained_untracked_us"] == 500_000
    assert result["attribution_score"] == 1.0


def test_no_pipeline_overhead_recorded_changes_nothing():
    assert _confidence(3_170_000, [])["explained_untracked_us"] == 0
