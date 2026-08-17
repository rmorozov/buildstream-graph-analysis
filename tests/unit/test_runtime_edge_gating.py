"""UX-52: `runtime`-only edges must not gate build scheduling.

`bga/graph/edg.py::build_element_graph`'s own docstring states the rule:
unfiltered for reachability (blast radius, leaf/deferrability, Part
24/25), `exclude_dependency_types={"runtime"}` for the gating chain
(critical path, slack, Part 14.1), because including a runtime edge there
"would inflate `T∞,observed` past what Part 14.1 itself claims it
certifies". `compute_critical_path` and `compute_slack` applied it;
`build_edg` - which feeds the entire structural plane - did not.

On a real `freedesktop-sdk` graph (85 elements, 502 dependencies, **27 of
them runtime**) that inflated the structural critical path from 28
elements to 32.

**No fixture in this repository contained a single runtime edge** before
this file, which is exactly why the defect survived four audit rounds
including a 1202-element scale probe. These tests exist as much to give
the suite that shape as to pin the behaviour.
"""
import networkx as nx

from bga.ingest.models import DependencyEdge, Element, Graph
from bga.structural.analyzer import build_edg


def _graph(edges):
    """`edges` is a list of (pred, succ, dependency_type)."""
    uids = sorted({u for e in edges for u in e[:2]})
    return Graph(
        elements=[Element(uid=u) for u in uids],
        dependencies=[
            DependencyEdge(predecessor=p, successor=s, dependency_type=t)
            for p, s, t in edges
        ],
    )


# a -> b -> c by build edges (a 3-element gating chain), plus a runtime
# edge c -> d that must not extend it.
MIXED = [
    ("a.bst", "b.bst", "build"),
    ("b.bst", "c.bst", "build"),
    ("c.bst", "d.bst", "runtime"),
]


def _longest_path(G):
    depth = {}
    for node in nx.topological_sort(G):
        depth[node] = max((depth[p] for p in G.predecessors(node)), default=-1) + 1
    return max(depth.values()) + 1 if depth else 0


def test_runtime_edge_is_excluded_from_the_gating_graph():
    edg = build_edg(_graph(MIXED))

    assert edg.G.has_edge("b.bst", "c.bst")
    assert not edg.G.has_edge("c.bst", "d.bst"), "runtime edge must not gate"


def test_runtime_edge_is_kept_in_the_full_graph():
    """Reachability must count it: `d.bst` really does depend on
    `c.bst`, just not at build time."""
    edg = build_edg(_graph(MIXED))

    assert edg.G_full.has_edge("c.bst", "d.bst")
    assert edg.G_full.number_of_edges() == 3
    assert edg.G.number_of_edges() == 2


def test_runtime_edge_does_not_extend_the_critical_path():
    """The measured symptom on the real project, in miniature: the
    gating chain is 3 elements and the unfiltered one is 4."""
    edg = build_edg(_graph(MIXED))

    assert _longest_path(edg.G) == 3
    assert _longest_path(edg.G_full) == 4


def test_a_pure_runtime_dependent_is_not_a_gating_successor():
    """An element reachable only by runtime edges is free to run at any
    time, so it must not appear downstream of anything in the gating
    graph."""
    edg = build_edg(_graph([("lib.bst", "app.bst", "runtime")]))

    assert edg.G.number_of_edges() == 0
    assert list(nx.descendants(edg.G, "lib.bst")) == []
    assert nx.descendants(edg.G_full, "lib.bst") == {"app.bst"}


def test_graphs_without_runtime_edges_are_identical():
    """Every pre-existing fixture is this case, which is why their output
    is unchanged by the split."""
    edg = build_edg(_graph([("a.bst", "b.bst", "build"), ("b.bst", "c.bst", "build")]))

    assert set(edg.G.edges()) == set(edg.G_full.edges())


def test_deferrability_uses_the_full_graph():
    """A leaf question is a reachability question: `c.bst` has a runtime
    dependent, so it is not a leaf even though the edge does not gate."""
    from bga.ingest.models import NormalizedTask, TaskKey, TaskKind
    from bga.structural.analyzer import StructuralAnalyzer

    edg = build_edg(_graph(MIXED))
    tasks = {
        uid: NormalizedTask(
            task_key=TaskKey(element_uid=uid, task_kind=TaskKind.BUILD, phase="EXECUTION"),
            ready_us=0, start_us=0, finish_us=1_000_000,
        )
        for uid in ("a.bst", "b.bst", "c.bst", "d.bst")
    }
    analyzer = StructuralAnalyzer(edg, tasks)

    result = analyzer.analyze_deferrability()
    leaves = set(result.deferrable_leaves) | set(result.non_deferrable_leaves)

    assert "d.bst" in leaves, "d.bst has no dependents at all - it is a leaf"
    assert "c.bst" not in leaves, "c.bst has a runtime dependent, so it is not"
