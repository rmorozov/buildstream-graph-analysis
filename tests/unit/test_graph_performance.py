"""Regression tests for P1-16: O(N+E) graph algorithms, not O(N*E)/O(N^2).

Three spots were fixed:
1. `bga/graph/edg.py::compute_unweighted_depth`/`compute_weighted_depth`/
   `compute_dominators` each rescanned the full flat `graph.dependencies`
   list inside their topological-sort loop instead of using the
   `successors` adjacency list `build_element_graph` already builds -
   fixed to do a single O(N+E) traversal.
2. `bga/attribution/blame_chain.py::_build_dependency_graph` matched
   finish times via a nested O(N) rescan per task (O(N^2) overall) -
   fixed to group tasks by finish time once (O(N)), then O(1) lookup
   per task.
3. `bga/analyzer.py`'s `explicit_predecessors` construction was already
   O(tasks+E) (fixed earlier by P1-19, which also fixed its one-task-
   per-element assumption) - confirmed still correct, no further change.

This file covers item 1's correctness angle (multi-task-per-element
predecessor mapping, via P1-19's fix) plus an informal but real
performance check across items 1 and 2.
"""
import json
import sys

from bga import analyze_run
from bga.attribution.blame_chain import BlameChainAnalyzer
from bga.graph.edg import compute_unweighted_depth, compute_weighted_depth
from bga.ingest.loader import load_all
from bga.normalize.timestamps import normalize_trace


def _linear_chain_run_dir(tmp_path, n, epsilon_us=1000, dur_us=1000):
    """N elements in a straight dependency chain e0 -> e1 -> ... -> e{n-1},
    each a single-task-kind BUILD element. Enough to exercise the
    topological-sort loops in compute_unweighted_depth/compute_weighted_depth/
    compute_dominators and _build_dependency_graph's finish-time grouping
    at scale.
    """
    run_dir = tmp_path / "run"
    run_dir.mkdir(parents=True)
    elements = [{"uid": f"e{i}.bst", "requested_target": (i == n - 1)} for i in range(n)]
    dependencies = [
        {"predecessor": f"e{i}.bst", "successor": f"e{i + 1}.bst"} for i in range(n - 1)
    ]
    spans = [
        {"task_key": f"e{i}.bst|BUILD|BUILD|0", "ts_us": i * dur_us, "dur_us": dur_us,
         "resources": ["PROCESS"], "primary_resource": "PROCESS"}
        for i in range(n)
    ]
    run_context = {
        "trace_epsilon_us": epsilon_us, "wall_start_us": 0, "wall_end_us": n * dur_us + dur_us,
        "max_jobs": 1, "resource_capacities": {"PROCESS": 1},
    }
    graph = {"elements": elements, "dependencies": dependencies}
    trace = {"spans": spans, "phases": []}
    (run_dir / "run-context.json").write_text(json.dumps(run_context))
    (run_dir / "graph.json").write_text(json.dumps(graph))
    (run_dir / "trace.json").write_text(json.dumps(trace))
    return run_dir


def test_multi_task_kind_element_predecessors_correctly_distinguished(tmp_path):
    """a.bst has both a FETCH task and a BUILD task; b.bst depends on
    a.bst. Both of b.bst's own tasks must gate on a.bst's BUILD finishing
    (the real dependency-completion signal), not get mismapped by an
    assumption that each element has only one task.
    """
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    run_context = {
        "trace_epsilon_us": 1000, "wall_start_us": 0, "wall_end_us": 100000,
        "max_jobs": 1, "resource_capacities": {"PROCESS": 1, "DOWNLOAD": 1},
    }
    graph = {
        "elements": [{"uid": "a.bst"}, {"uid": "b.bst", "requested_target": True}],
        "dependencies": [{"predecessor": "a.bst", "successor": "b.bst"}],
    }
    trace = {
        "spans": [
            {"task_key": "a.bst|FETCH|FETCH|0", "ts_us": 0, "dur_us": 5000,
             "resources": ["DOWNLOAD"], "primary_resource": "DOWNLOAD"},
            {"task_key": "a.bst|BUILD|BUILD|0", "ts_us": 5000, "dur_us": 5000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
            {"task_key": "b.bst|BUILD|BUILD|0", "ts_us": 10000, "dur_us": 5000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
        ],
        "phases": [],
    }
    (run_dir / "run-context.json").write_text(json.dumps(run_context))
    (run_dir / "graph.json").write_text(json.dumps(graph))
    (run_dir / "trace.json").write_text(json.dumps(trace))

    result = analyze_run(run_dir)
    h = result.occupancy["horizon_us"]
    total = sum(
        result.attribution.get(k, 0) for k in (
            "execution_on_chain_us", "dependency_wait_us", "resource_wait_us",
            "scheduler_wait_us", "idle_us", "retry_wait_us",
        )
    )
    # If b.bst's task had been mismapped to depend on a.bst's FETCH task
    # instead of its BUILD task, the blame chain would misattribute
    # b.bst's wait and I4 would not hold exactly.
    assert total == h


#: The modules whose work the claim is about. A line event outside them
#: is somebody else's cost and is not counted.
_MEASURED = ("bga/graph/edg.py", "bga/attribution/blame_chain.py")


def _steps_taken(run_dir):
    """`{module: line events}` for one run of the three named functions.

    `UX-731`: the count, not the clock. The predecessor timed a 1.7 ms
    window under `-n auto` on a box whose load average was 3.25, so one
    scheduler preemption inside that window moved the quotient and the
    guard reddened on a green tree. A line event is work the interpreter
    actually did: it is identical run to run and on any machine, so what
    else the box is doing cannot reach it.

    Loading and normalising happen outside the trace, as the timed
    version kept them outside the clock.
    """
    rc, g, tr = load_all(run_dir)
    tasks, _ = normalize_trace(tr, g, rc.trace_epsilon_us)
    durations = {t.task_key.element_uid: t.dur_us for t in tasks}

    steps = dict.fromkeys(_MEASURED, 0)

    def _count(frame, event, _arg):
        where = next((one for one in _MEASURED
                      if frame.f_code.co_filename.endswith(one)), None)
        if where is None:
            return None
        if event != "call":
            steps[where] += 1
        return _count

    sys.settrace(_count)
    try:
        compute_unweighted_depth(g)
        compute_weighted_depth(g, durations)
        BlameChainAnalyzer(tasks)  # runs _build_dependency_graph
    finally:
        sys.settrace(None)
    return steps


class TestTheThreeFunctionsScaleSubquadratically:
    """P1-16's claim, on the instrument that reads it.

    The three functions are `compute_unweighted_depth`,
    `compute_weighted_depth` (`bga/graph/edg.py`) and
    `_build_dependency_graph` (via constructing a `BlameChainAnalyzer`).
    O(N^2) does ~16x the work at 4x the size; O(N+E) does ~4x. The
    threshold stays 10x, unmoved from the timed version - `UX-731`
    replaced the instrument and deliberately did not touch the claim.

    Deliberately does NOT cover the full `analyze_graph()`/`analyze_run()`
    pipeline: end-to-end cost is dominated by two functions P1-16 never
    named - `compute_reachability`'s full-set materialization (inherently
    ~O(N^2) output size on a chain) and `compute_dominators`' naive
    fixed-point dataflow - plus an O(N^2) hotspot in diagnostics'
    ready-queue metrics. Real, distinct, and held by P1-21.

    The timed version's own history, kept because it is why the
    threshold is 10x and not 8x: a single-sample, 8x version produced a
    false positive on GitHub Actions (P4-06) at 9.0x, plausible noise
    for a sub-50 ms window on a shared VM. min-of-repeats raised the
    floor and did not remove it; counting does.
    """

    SMALL, LARGE = 500, 2000
    BOUND = 10.0

    @staticmethod
    def _both(tmp_path):
        return (_steps_taken(_linear_chain_run_dir(tmp_path / "small", 500)),
                _steps_taken(_linear_chain_run_dir(tmp_path / "large", 2000)))

    def test_four_times_the_graph_is_not_sixteen_times_the_work(self, tmp_path):
        small, large = self._both(tmp_path)
        done, grew = sum(small.values()), sum(large.values())
        ratio = grew / done
        assert ratio < self.BOUND, (
            f"4x the graph took {ratio:.2f}x the steps ({done} -> {grew}) - "
            f"looks quadratic, not O(N+E). Per module: "
            f"{ {k: (small[k], large[k]) for k in _MEASURED} }")

    def test_every_measured_module_is_reached(self, tmp_path):
        """The vacuity floor. A module that moves, or a filename the
        suffix match stops recognising, leaves both counts at 0 and the
        ratio undefined - which must red rather than read as linear."""
        small, large = self._both(tmp_path)
        silent = [one for one in _MEASURED if not small[one] or not large[one]]
        assert not silent, (
            f"the trace reached no line of {silent}, so the ratio above is "
            f"not about them", small, large)

    def test_the_count_does_not_move_between_runs(self, tmp_path):
        """What the timed version could not claim, and the whole reason
        for the swap: the reading is a property of the code, not of the
        machine. If this ever reds, the instrument has become a proxy
        again and the ratio clause's margin means nothing."""
        first = _steps_taken(_linear_chain_run_dir(tmp_path / "one", 500))
        again = _steps_taken(_linear_chain_run_dir(tmp_path / "two", 500))
        assert first == again, (
            "two runs of the same graph counted different work", first, again)
