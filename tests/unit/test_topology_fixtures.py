"""Acceptance test for P3-01 (shared synthetic topology fixture library).

Smoke-tests every factory in tests/fixtures/topologies.py: build it,
run a full analysis, confirm no exception. This is deliberately not
asserting on computed values - value assertions belong to the tasks
that actually consume these fixtures (P3-03 through P3-09, and various
P1-*/P2-* acceptance tests), per P3-01's own Out of Scope note.
"""
import pytest

from tests.fixtures import topologies as topo


FACTORIES = [
    ("linear_chain", lambda: topo.linear_chain()),
    ("linear_chain_n5", lambda: topo.linear_chain(n=5)),
    ("diamond", lambda: topo.diamond()),
    ("fan_in", lambda: topo.fan_in()),
    ("fan_out", lambda: topo.fan_out()),
    ("multiple_equal_predecessors", lambda: topo.multiple_equal_predecessors()),
    ("deep_unequal_predecessors", lambda: topo.deep_unequal_predecessors()),
    ("independent_branches", lambda: topo.independent_branches()),
    ("graph_with_terminal_and_nonterminal_tasks", lambda: topo.graph_with_terminal_and_nonterminal_tasks()),
]


@pytest.mark.parametrize("name,factory", FACTORIES, ids=[n for n, _ in FACTORIES])
def test_factory_produces_analyzable_input(tmp_path, name, factory):
    topology = factory()
    analyzer = topo.build_analyzer(tmp_path, topology, name=name)
    result = analyzer.analyze()

    assert result.floors is not None
    assert result.attribution is not None
    assert result.signals is not None


def test_duration_override_is_applied(tmp_path):
    run_context, graph, trace = topo.linear_chain(n=2, duration_us=10000, durations={"elem1.bst": 5000})
    spans_by_uid = {s["task_key"].split("|")[0]: s for s in trace["spans"]}
    assert spans_by_uid["elem0.bst"]["dur_us"] == 10000
    assert spans_by_uid["elem1.bst"]["dur_us"] == 5000


def test_multiple_equal_predecessors_are_a_genuine_tie():
    _, _, trace = topo.multiple_equal_predecessors()
    finishes = {}
    for span in trace["spans"]:
        uid = span["task_key"].split("|")[0]
        finishes[uid] = span["ts_us"] + span["dur_us"]
    assert finishes["shallow.bst"] == finishes["deep.bst"]


def test_deep_unequal_predecessors_are_not_a_tie():
    _, _, trace = topo.deep_unequal_predecessors()
    finishes = {}
    for span in trace["spans"]:
        uid = span["task_key"].split("|")[0]
        finishes[uid] = span["ts_us"] + span["dur_us"]
    assert finishes["shallow.bst"] != finishes["deep2.bst"]


def test_graph_with_terminal_and_nonterminal_tasks_marks_requested_target():
    _, graph, _ = topo.graph_with_terminal_and_nonterminal_tasks()
    requested = {e["uid"] for e in graph["elements"] if e["requested_target"]}
    assert requested == {"target.bst"}


def test_independent_branches_share_no_dependencies():
    _, graph, _ = topo.independent_branches(n=3)
    prefixes = {dep["predecessor"].split("_")[0] for dep in graph["dependencies"]}
    prefixes |= {dep["successor"].split("_")[0] for dep in graph["dependencies"]}
    # Every dependency edge must stay within a single branch prefix.
    for dep in graph["dependencies"]:
        assert dep["predecessor"].split("_")[0] == dep["successor"].split("_")[0]
