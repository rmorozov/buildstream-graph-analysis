"""Tests for P2-10: ready queue depth (Part 21) is defined as
"dependency-ready AND resource-ready AND not currently executing", but
`_estimate_ready_count` previously only checked dependency-readiness -
the `resource_capacities` parameter `compute_ready_queue_metrics` accepts
was never actually consulted, so the metric could never distinguish
"nothing was ready" from "work was ready but resource-starved".
"""
from bga.diagnostics.analyzer import DiagnosticsAnalyzer
from bga.ingest.models import NormalizedTask, Resource, TaskKey, TaskKind


def _task(uid, ready_us, start_us, finish_us, resources=None):
    return NormalizedTask(
        task_key=TaskKey(element_uid=uid, task_kind=TaskKind.BUILD, phase="BUILD", attempt=0),
        ready_us=ready_us,
        start_us=start_us,
        finish_us=finish_us,
        resources=resources or [],
    )


def _analyzer(tasks):
    return DiagnosticsAnalyzer(normalized_tasks=tasks, graph_analysis={})


def test_ready_but_resource_starved_task_not_counted():
    """capacity=1: task A occupies the only PROCESS slot during [0, 100).
    Task B is dependency-ready at t=0 but doesn't actually start until
    t=150 - during [0, 100), B is resource-starved (genuinely blocked by
    A, not by an idle scheduler) and must not count toward ready queue
    depth; once the slot frees at t=100, B is undispatched-but-ready and
    should count."""
    holder = _task("a.bst", ready_us=0, start_us=0, finish_us=100, resources=[Resource.PROCESS])
    waiting = _task("b.bst", ready_us=0, start_us=150, finish_us=200, resources=[Resource.PROCESS])
    da = _analyzer([holder, waiting])

    during_saturation = da._estimate_ready_count(50, set(), {"PROCESS": 1})
    after_slot_frees = da._estimate_ready_count(120, set(), {"PROCESS": 1})

    assert during_saturation == 0
    assert after_slot_frees == 1


def test_no_capacity_data_falls_back_to_dependency_readiness_only():
    """Same shape as above, but no resource_capacities supplied at all -
    unchanged, dependency-readiness-only behavior (backward compatible;
    absence of capacity data is not evidence of unavailability)."""
    holder = _task("a.bst", ready_us=0, start_us=0, finish_us=100, resources=[Resource.PROCESS])
    waiting = _task("b.bst", ready_us=0, start_us=150, finish_us=200, resources=[Resource.PROCESS])
    da = _analyzer([holder, waiting])

    assert da._estimate_ready_count(50, set()) == 1
    assert da._estimate_ready_count(50, set(), None) == 1
    assert da._estimate_ready_count(50, set(), {}) == 1


def test_unknown_resource_capacity_not_fabricated_as_unavailable():
    """resource_capacities is provided but doesn't mention the resource
    `waiting` requires - falls through as resource-ready (absence of
    capacity data is not evidence of unavailability), matching
    _resource_available_at's own documented discipline."""
    holder = _task("a.bst", ready_us=0, start_us=0, finish_us=100, resources=[Resource.DOWNLOAD])
    waiting = _task("b.bst", ready_us=0, start_us=150, finish_us=200, resources=[Resource.DOWNLOAD])
    da = _analyzer([holder, waiting])

    assert da._estimate_ready_count(50, set(), {"PROCESS": 1}) == 1


def test_task_with_no_resources_always_counts_once_dependency_ready():
    waiting = _task("b.bst", ready_us=0, start_us=150, finish_us=200, resources=[])
    da = _analyzer([waiting])

    assert da._estimate_ready_count(50, set(), {"PROCESS": 1}) == 1


def test_multiple_ready_tasks_only_resource_ready_ones_counted():
    """capacity=1: holder occupies PROCESS during [0, 100). Two other
    tasks are dependency-ready at t=0: waiting_process (needs PROCESS,
    starved until 100) and waiting_download (needs DOWNLOAD, never
    contended) - only the latter counts during [0, 100)."""
    holder = _task("a.bst", ready_us=0, start_us=0, finish_us=100, resources=[Resource.PROCESS])
    waiting_process = _task("b.bst", ready_us=0, start_us=150, finish_us=200, resources=[Resource.PROCESS])
    waiting_download = _task("c.bst", ready_us=0, start_us=150, finish_us=200, resources=[Resource.DOWNLOAD])
    da = _analyzer([holder, waiting_process, waiting_download])

    count = da._estimate_ready_count(50, set(), {"PROCESS": 1, "DOWNLOAD": 1})

    assert count == 1
