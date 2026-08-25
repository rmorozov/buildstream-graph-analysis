"""UX-50: an element has more than one task, and the structural analyzer
must not silently keep just one of them.

`bga/analyzer.py` built its element table with
`{t.task_key.element_uid: t for t in self.normalized_tasks}`. A real
BuildStream element has at least a FETCH and a BUILD, so that
comprehension kept whichever arrived *last*; when it was the FETCH, the
structural analyzer saw a zero-duration element. On a real capture the
build's two heaviest elements (`core.bst` at 9.0s, `codegen.bst` at 6.0s)
were both read as 0.00s, which dropped them from the improvement ranking
entirely and understated the critical path by 9 seconds.

It was data-order dependent - 0 of 11 elements affected on two real
captures, 2 of 11 on a third - which is exactly why it survived.

The cross-check that caught it is cheap and is pinned here as a test:
`sensitivity.critical_path_us` and `floors.t_infinity_observed` are the
same quantity computed two ways and must agree.
"""
import networkx as nx
import pytest

from bga.ingest.models import NormalizedTask, TaskKey, TaskKind
from bga.report.json import format_json
from bga.structural.analyzer import ElementDependencyGraph, StructuralAnalyzer
from tests.fixtures import topologies


def _task(uid, kind, dur_us):
    return NormalizedTask(
        task_key=TaskKey(element_uid=uid, task_kind=kind, phase="EXECUTION"),
        ready_us=0,
        start_us=0,
        finish_us=dur_us,
    )


def _analyzer(nodes, edges, tasks_by_uid, element_durations=None):
    G = nx.DiGraph()
    for node in nodes:
        G.add_node(node)
    for pred, succ in edges:
        G.add_edge(pred, succ)
    return StructuralAnalyzer(
        ElementDependencyGraph(G=G, predecessors={}, successors={}),
        tasks_by_uid,
        element_durations=element_durations,
    )


def test_fetch_winning_the_dict_no_longer_zeroes_the_element():
    """The exact real shape: `core` has a 9s BUILD and a 0s FETCH, and
    the FETCH is the one the caller's dict kept."""
    nodes, edges = ["core", "app"], [("core", "app")]
    # What the old comprehension produced.
    tasks = {
        "core": _task("core", TaskKind.FETCH, 0),
        "app": _task("app", TaskKind.BUILD, 2_000_000),
    }
    durations = {"core": 9_000_000, "app": 2_000_000}

    analyzer = _analyzer(nodes, edges, tasks, element_durations=durations)

    assert analyzer._longest_path_us() == 11_000_000


def test_without_summed_durations_the_defect_reproduces():
    """Pins the mechanism rather than trusting the description of it:
    the same graph, with the fallback path, is 9 seconds short."""
    nodes, edges = ["core", "app"], [("core", "app")]
    tasks = {
        "core": _task("core", TaskKind.FETCH, 0),
        "app": _task("app", TaskKind.BUILD, 2_000_000),
    }

    analyzer = _analyzer(nodes, edges, tasks, element_durations=None)

    assert analyzer._longest_path_us() == 2_000_000


def test_zeroed_element_is_excluded_from_the_ranking():
    """Why this mattered: a zero-duration element can never be an
    improvement opportunity, so the heaviest element in the build
    silently disappeared from the answer to "what should I optimize"."""
    nodes = ["core", "a", "b"]
    edges = [("core", "a"), ("core", "b")]
    tasks = {uid: _task(uid, TaskKind.FETCH, 0) for uid in nodes}
    durations = {"core": 9_000_000, "a": 1_000_000, "b": 1_000_000}

    ranked = [
        key for key, _, _ in
        _analyzer(nodes, edges, tasks, durations).compute_sensitivity().top_opportunities
    ]

    assert ranked and ranked[0] == "core"


def test_the_supplied_duration_map_wins_over_the_task_table():
    """The analyzer reads durations from the map it is handed, never
    from whichever task happened to land in `tasks_by_uid` - which is
    the whole of UX-50's fix.

    UX-53 later changed *how that map is built* (see
    `tests/unit/test_shared_element_durations.py`); this stays a test of
    the plumbing, and is deliberately given a value the task table alone
    could not produce.
    """
    nodes, edges = ["only"], []
    tasks = {"only": _task("only", TaskKind.BUILD, 3_000_000)}
    durations = {"only": 3_500_000}

    analyzer = _analyzer(nodes, edges, tasks, element_durations=durations)

    assert analyzer._durations()["only"] == 3_500_000


def test_element_absent_from_durations_contributes_zero():
    """A graph node with no recorded task at all - a structural element
    that ran no command - must stay at zero rather than raise."""
    nodes, edges = ["a", "structural"], [("a", "structural")]
    tasks = {"a": _task("a", TaskKind.BUILD, 1_000_000)}

    analyzer = _analyzer(nodes, edges, tasks, element_durations={"a": 1_000_000})

    assert analyzer._durations()["structural"] == 0
    assert analyzer._longest_path_us() == 1_000_000


# --- the cross-check that found this, pinned end to end ----------------

@pytest.mark.parametrize(
    "topology_name", ["diamond", "linear_chain", "fan_in", "fan_out", "independent_branches"]
)
def test_critical_path_us_agrees_with_t_infinity(tmp_path, topology_name):
    """Two independently-computed longest-weighted-path numbers for the
    same run. They disagreed by 9 seconds on a real capture, and either
    this assertion or the next would have caught it the day it was
    written."""
    import json

    topology = getattr(topologies, topology_name)()
    result = topologies.build_analyzer(tmp_path, topology).analyze()
    data = json.loads(format_json(result))

    assert (
        data["structural"]["sensitivity"]["critical_path_us"]
        == data["floors"]["t_infinity_observed"]
    )


@pytest.mark.parametrize(
    "topology_name", ["diamond", "linear_chain", "fan_in", "fan_out", "independent_branches"]
)
def test_critical_path_length_agrees_with_the_named_path(tmp_path, topology_name):
    import json

    topology = getattr(topologies, topology_name)()
    result = topologies.build_analyzer(tmp_path, topology).analyze()
    data = json.loads(format_json(result))

    assert data["structural"]["metrics"]["critical_path_length"] == len(
        [e["element_uid"] for e in data["signals"]["critical_path_detail"]]
    )
