"""UX-1074: one bitset closure per graph, shared by every reachability
reader.

Before: `compute_reachability` built two `dict[str, set[str]]` (Part 5.3)
from scratch on every call - O(V*(V+E)) time, O(V^2) memory - and
`analyze_graph`, `compute_downstream_count`, `fan_in.compute_fan_in`,
`batching.compute_batch_opportunities` and
`serialization_points.detect_large_serialization_points` each called it
independently: five rebuilds of the same closure per analysis.

After: one bitset closure per `Graph` object (cached on the graph, the
same trick `UX-539` used per `StructuralAnalyzer`), decoded into a real
`set` only for the uid a caller actually reads (`ReachabilitySets`)
- a reader that only counts never decodes at all.

`_reference_reachability` below is the old algorithm, verbatim, kept as
ground truth rather than a golden file. The 5,002-element scale reading
is a measurement, in the task file's Outcome - too slow for a guard
that runs every suite; this file stays under `~15s` at 1,202.
"""
import random
import tracemalloc
from collections import deque
from unittest import mock

import pytest

from bga.graph import edg
from bga.ingest.loader import load_graph
from bga.ingest.models import DependencyEdge, Element, Graph
from tests.fixtures import topologies
from tools.gen_synthetic_scale_run import build_graph as _synth_build_graph


def _reference_reachability(graph):
    """Pre-UX-1074 `compute_reachability`: one python `set` per element."""
    _, successors = edg.build_element_graph(graph)
    predecessors, _ = edg.build_element_graph(graph)
    reachable_downstream: dict = {}
    reachable_upstream: dict = {}
    in_degree, _ = edg.compute_in_out_degree(graph)
    topo_order = []
    queue = deque([uid for uid, deg in in_degree.items() if deg == 0])
    temp_in_degree = dict(in_degree)
    while queue:
        current = queue.popleft()
        topo_order.append(current)
        for succ in successors.get(current, []):
            temp_in_degree[succ] -= 1
            if temp_in_degree[succ] == 0:
                queue.append(succ)
    for elem_uid in reversed(topo_order):
        reachable = set()
        for succ in successors.get(elem_uid, []):
            reachable.add(succ)
            reachable.update(reachable_downstream.get(succ, set()))
        reachable_downstream[elem_uid] = reachable
    for elem_uid in topo_order:
        reachable = set()
        for pred in predecessors.get(elem_uid, []):
            reachable.add(pred)
            reachable.update(reachable_upstream.get(pred, set()))
        reachable_upstream[elem_uid] = reachable
    for elem in graph.elements:
        reachable_downstream.setdefault(elem.uid, set())
        reachable_upstream.setdefault(elem.uid, set())
    return reachable_downstream, reachable_upstream


def _graph_from_topology(tmp_path, topology, name):
    run_dir = topologies.write_run_dir(tmp_path, topology, name=name)
    return load_graph(run_dir / "graph.json")


def _cycle_and_disconnected_graph():
    """A 3-cycle (`compute_reachability` tolerates one; the graph
    functions that require a DAG are never called here) plus one
    element with no edges at all."""
    return Graph(
        elements=[Element(uid=u) for u in ("a.bst", "b.bst", "c.bst", "isolated.bst")],
        dependencies=[
            DependencyEdge(predecessor="a.bst", successor="b.bst"),
            DependencyEdge(predecessor="b.bst", successor="c.bst"),
            DependencyEdge(predecessor="c.bst", successor="a.bst"),
        ],
    )


def _synth_graph(layers, width, seed):
    rng = random.Random(seed)
    elements, dependencies = _synth_build_graph(layers, width, rng)
    return Graph(
        elements=[Element(uid=e["uid"], cache_key=e.get("cache_key"),
                           requested_target=e.get("requested_target", False),
                           element_kind=e.get("element_kind"))
                  for e in elements],
        dependencies=[DependencyEdge(predecessor=d["predecessor"], successor=d["successor"],
                                      dependency_type=d.get("dependency_type", "build"))
                      for d in dependencies],
    )


INPUT_CLASSES = {
    "chain": lambda tmp_path: _graph_from_topology(tmp_path, topologies.linear_chain(n=14), "chain"),
    "wide_layer": lambda tmp_path: _graph_from_topology(tmp_path, topologies.shared_base_wide(), "wide"),
    "diamond": lambda tmp_path: _graph_from_topology(tmp_path, topologies.diamond(), "diamond"),
    "disconnected": lambda tmp_path: _graph_from_topology(
        tmp_path, topologies.independent_branches(n=3), "disc"),
    "cycle_and_disconnected": lambda tmp_path: _cycle_and_disconnected_graph(),
}


@pytest.mark.parametrize("name", sorted(INPUT_CLASSES))
def test_the_bitset_closure_matches_the_old_set_closure(tmp_path, name):
    graph = INPUT_CLASSES[name](tmp_path)

    ref_down, ref_up = _reference_reachability(graph)
    new_down, new_up = edg.compute_reachability(graph)

    for uid in ref_down:
        assert new_down[uid] == ref_down[uid], f"downstream({uid})"
        assert new_up[uid] == ref_up[uid], f"upstream({uid})"
    assert edg.compute_downstream_count(graph) == {
        uid: len(s) for uid, s in ref_down.items()
    }


def test_matches_at_1202_elements():
    """The scale the Decomposition names - `gen-synthetic --layers 20
    --width 60 --seed 1`."""
    graph = _synth_graph(layers=20, width=60, seed=1)
    assert len(graph.elements) == 1202

    ref_down, ref_up = _reference_reachability(graph)
    new_down, new_up = edg.compute_reachability(graph)

    assert edg.compute_downstream_count(graph) == {uid: len(s) for uid, s in ref_down.items()}
    for uid in list(ref_down)[::97]:
        assert new_down[uid] == ref_down[uid]
        assert new_up[uid] == ref_up[uid]


def test_the_closure_is_a_bitset_not_a_python_set_per_element():
    """The Acceptance Test's memory clause, guarded: the closure build
    itself must peak well under the old per-element `set` closure it
    replaces - not just be called once (`test_one_graph_shares_one_
    closure_build` alone passes a cache wrapped around the old
    algorithm just as well).

    50% of the reference is generous headroom over the measured ~2%
    (900 KB against 45.9 MB, tracemalloc, at 1,202 elements) - tight
    enough that reverting `_build_reachability_closure`'s body to
    `_reference_reachability`'s per-element sets (while keeping the
    cache) reds this, in well under 2s.

    Mutation: replace `_build_reachability_closure`'s body with
    `_reference_reachability`'s and this reds - bitset peak stops being
    under half the set-based peak (measured: same call, ~100% of it).
    """
    graph_for_reference = _synth_graph(layers=20, width=60, seed=1)
    graph_for_bitset = _synth_graph(layers=20, width=60, seed=1)

    tracemalloc.start()
    _reference_reachability(graph_for_reference)
    _, reference_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    tracemalloc.start()
    edg._build_reachability_closure(graph_for_bitset)
    _, bitset_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert bitset_peak < reference_peak * 0.5, (
        f"bitset build peaked at {bitset_peak} bytes, not under half "
        f"the set-based reference's {reference_peak} bytes"
    )


def test_one_graph_shares_one_closure_build():
    """UX-1074's call-count guard: `analyze_graph` reads reachability
    twice (`compute_reachability`, `compute_downstream_count`) and
    `compute_fan_in` reads it again, on the same `Graph` - the bitset
    closure itself must be built once, not per reader.

    Mutation: drop `_reachability_closure`'s cache check (call
    `_build_reachability_closure` unconditionally) and this reds -
    `build_count` goes from 1 to 3.
    """
    from bga.graph.edg import analyze_graph
    from bga.graph.fan_in import compute_fan_in

    graph = _synth_graph(layers=6, width=12, seed=1)
    tasks = []  # analyze_graph tolerates an empty task list

    real_build = edg._build_reachability_closure
    with mock.patch.object(edg, "_build_reachability_closure", wraps=real_build) as spy:
        analyze_graph(graph, tasks)
        compute_fan_in(graph, {}, set())

    assert spy.call_count == 1, spy.call_count
