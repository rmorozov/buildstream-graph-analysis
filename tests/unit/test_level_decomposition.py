"""UX-41: the level decomposition must use *longest* path from a root.

It was a BFS with first-visit-wins, i.e. shortest distance from a root.
That collapses every element under a common base element into a single
level - and a base element every other element depends on is the normal
shape of a real BuildStream project, so the collapse was the common case
rather than an edge case.

The tests below are written against the two shapes that actually
distinguish the two algorithms:

- `common_base` reproduces the real defect. BFS puts every module at
  distance 1 from the root; longest-path puts them at their true depth.
  This is `toolchain.bst` + layers, in miniature.
- a pure chain and a pure fan-out are shapes where BFS and longest-path
  *agree*, pinned here so a future rewrite cannot "fix" the common-base
  case by breaking the cases that were already right.

The strongest of these is the agreement test: `max_depth` and the level
count are the same computation keyed two ways, and having them disagree
in one report block was the user-visible face of this bug.
"""
import networkx as nx
import pytest

from bga.ingest.models import NormalizedTask, TaskKey, TaskKind
from bga.structural.analyzer import ElementDependencyGraph, StructuralAnalyzer


def _make_task(elem_uid, start_us=0, finish_us=1_000_000):
    return NormalizedTask(
        task_key=TaskKey(element_uid=elem_uid, task_kind=TaskKind.BUILD, phase="EXECUTION"),
        ready_us=start_us,
        start_us=start_us,
        finish_us=finish_us,
    )


def _analyzer_for(nodes, edges):
    G = nx.DiGraph()
    for node in nodes:
        G.add_node(node)
    for pred, succ in edges:
        G.add_edge(pred, succ)
    tasks = {node: _make_task(node) for node in nodes}
    edg = ElementDependencyGraph(G=G, predecessors={}, successors={})
    return StructuralAnalyzer(edg, tasks)


def _common_base(layers, width):
    """`toolchain.bst` -> every module, plus layer-to-layer chains.

    Every module depends directly on the base *and* on its predecessor in
    the previous layer - which is what makes BFS and longest-path
    disagree, and is exactly how a real BuildStream project is shaped.
    """
    nodes = ["base"]
    edges = []
    for layer in range(layers):
        for index in range(width):
            uid = f"L{layer}M{index}"
            nodes.append(uid)
            edges.append(("base", uid))
            if layer > 0:
                edges.append((f"L{layer - 1}M{index}", uid))
    return nodes, edges


def test_common_base_does_not_collapse_every_element_into_one_level():
    """The real defect: 4 layers of 3, all hanging off one base element."""
    analyzer = _analyzer_for(*_common_base(layers=4, width=3))

    levels = analyzer._compute_level_decomposition()
    widths = [len(levels[level]) for level in sorted(levels)]

    # 5 levels: the base, then one per layer. BFS reported 2: [1, 12].
    assert widths == [1, 3, 3, 3, 3]


def test_level_count_agrees_with_max_depth():
    """The contradiction a reader could see: `max_depth: 13` printed
    beside `levels: [0, 1, 2]` for the same graph."""
    analyzer = _analyzer_for(*_common_base(layers=4, width=3))

    metrics = analyzer.compute_structural_metrics()
    levels = analyzer._compute_level_decomposition()

    assert metrics.max_depth == max(levels) == 4


def test_parallelism_profile_reports_the_real_maximum_width():
    """`max_width` is the user-visible face of this (`Parallelism
    Profile: max=Nx`). Under BFS it read as the element *count*."""
    analyzer = _analyzer_for(*_common_base(layers=4, width=3))

    profile = analyzer.compute_parallelism_profile()

    assert profile.max_width == 3, "a 3-wide graph must not report width 12"
    assert profile.min_width == 1
    assert len(profile.levels) == 5


@pytest.mark.parametrize(
    "nodes,edges,expected_widths",
    [
        # A pure chain: every level has exactly one element.
        (["a", "b", "c", "d"], [("a", "b"), ("b", "c"), ("c", "d")], [1, 1, 1, 1]),
        # A pure fan-out: BFS and longest-path agree, and must keep agreeing.
        (["r", "x", "y", "z"], [("r", "x"), ("r", "y"), ("r", "z")], [1, 3]),
        # A diamond: the join is at depth 2 by both measures.
        (["a", "b", "c", "d"], [("a", "b"), ("a", "c"), ("b", "d"), ("c", "d")], [1, 2, 1]),
    ],
    ids=["chain", "fan_out", "diamond"],
)
def test_shapes_where_bfs_was_already_correct_are_unchanged(nodes, edges, expected_widths):
    analyzer = _analyzer_for(nodes, edges)

    levels = analyzer._compute_level_decomposition()

    assert [len(levels[level]) for level in sorted(levels)] == expected_widths


def test_direct_and_indirect_edge_to_the_same_root_takes_the_longer_path():
    """The minimal case, and the one `compute_structural_metrics`'s own
    comment already warned about for `max_depth`: `d` is reachable from
    `a` in one hop and in three. Its level is 3, not 1."""
    analyzer = _analyzer_for(
        ["a", "b", "c", "d"],
        [("a", "b"), ("b", "c"), ("c", "d"), ("a", "d")],
    )

    levels = analyzer._compute_level_decomposition()

    assert "d" in levels[3]
    assert all("d" not in levels[level] for level in levels if level != 3)


def test_empty_graph_decomposes_to_no_levels():
    analyzer = _analyzer_for([], [])

    assert analyzer._compute_level_decomposition() == {}
