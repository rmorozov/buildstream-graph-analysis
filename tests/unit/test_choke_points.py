"""UX-43: a choke point must be a real serialization point, not
`in_degree >= 2 and out_degree >= 2`.

That placeholder flagged 606 of 1202 elements (50.4%) on a realistically
shaped graph, because "has two parents and two children" is the common
case in any layered build. A signal that fires on half the graph is not
a signal.

The definition that shipped: an element nothing else can overlap with -
every other element is either strictly upstream or strictly downstream,
so when it runs, it runs alone. The tests below pin that on shapes where
the answer is obvious, and pin the two properties the placeholder failed:
it must not fire on ordinary layered structure, and it must tell the
`examples/06` baseline apart from its `optimized/` variant.
"""
import networkx as nx

from bga.ingest.models import NormalizedTask, TaskKey, TaskKind
from bga.structural.analyzer import ElementDependencyGraph, StructuralAnalyzer


def _task(uid):
    return NormalizedTask(
        task_key=TaskKey(element_uid=uid, task_kind=TaskKind.BUILD, phase="EXECUTION"),
        ready_us=0,
        start_us=0,
        finish_us=1_000_000,
    )


def _analyzer(nodes, edges):
    G = nx.DiGraph()
    for node in nodes:
        G.add_node(node)
    for pred, succ in edges:
        G.add_edge(pred, succ)
    tasks = {node: _task(node) for node in nodes}
    return StructuralAnalyzer(ElementDependencyGraph(G=G, predecessors={}, successors={}), tasks)


def _choke_points(nodes, edges):
    return _analyzer(nodes, edges).analyze_bottlenecks().choke_points


def test_chain_is_all_choke_points():
    """Every element of a pure chain runs alone - that is what a chain
    is - and all of them are correctly reported."""
    assert _choke_points(
        ["a", "b", "c"], [("a", "b"), ("b", "c")]
    ) == ["a", "b", "c"]


def test_diamond_identifies_the_waist_and_not_the_parallel_pair():
    """`b` and `c` can run at the same time, so neither is a choke
    point. `a` and `d` are the real funnels."""
    assert _choke_points(
        ["a", "b", "c", "d"],
        [("a", "b"), ("a", "c"), ("b", "d"), ("c", "d")],
    ) == ["a", "d"]


def test_element_running_alongside_another_is_not_a_choke_point():
    """The `examples/06` case in miniature: `core` looks like a
    bottleneck by degree, but `codegen` genuinely overlaps it."""
    choke = _choke_points(
        ["toolchain", "core", "codegen", "lib", "app"],
        [("toolchain", "core"), ("toolchain", "codegen"),
         ("core", "lib"), ("codegen", "lib"), ("lib", "app")],
    )

    assert "core" not in choke and "codegen" not in choke
    assert choke == ["toolchain", "lib", "app"]


def test_layered_graph_does_not_flag_half_of_itself():
    """The scale defect, in miniature. Every module has two parents and
    two children - the placeholder's exact trigger - but each layer runs
    concurrently, so only the shared base and sink are choke points."""
    nodes = ["base"]
    edges = []
    for layer in range(3):
        for index in range(4):
            uid = f"L{layer}M{index}"
            nodes.append(uid)
            edges.append(("base", uid))
            if layer > 0:
                edges.append((f"L{layer - 1}M{index}", uid))
                edges.append((f"L{layer - 1}M{(index + 1) % 4}", uid))
    nodes.append("all")
    for index in range(4):
        edges.append((f"L2M{index}", "all"))

    choke = _choke_points(nodes, edges)

    assert choke == ["base", "all"]
    assert len(choke) / len(nodes) < 0.2, "must not flag a large fraction of the graph"


def test_serialized_chain_is_found_and_disappears_when_it_is_removed():
    """The property that makes this signal worth reporting: it tells the
    two `examples/06` variants apart. Baseline chains six libraries;
    `optimized/` fans them out off `core`, changing nothing else.
    """
    libs = [f"lib-{c}" for c in "abcdef"]
    nodes = ["toolchain", "core", "codegen", *libs, "app", "all"]
    # Mirrors the real project: every lib declares core, codegen and
    # toolchain (the over-declared `codegen` dep is UX-46's subject and
    # is present in both variants, so it is not what moves this result).
    common = [("toolchain", "core"), ("toolchain", "codegen")]
    common += [(dep, lib) for lib in libs for dep in ("core", "codegen")]
    common += [("app", "all")]

    chained = _choke_points(
        nodes,
        common
        + [(libs[i], libs[i + 1]) for i in range(len(libs) - 1)]
        + [(libs[-1], "app")],
    )
    fanned = _choke_points(nodes, common + [(lib, "app") for lib in libs])

    # Baseline: the six chained libraries are each a serialization point.
    assert [lib for lib in libs if lib in chained] == libs
    # optimized/: fanning them out removes all six, and nothing else
    # about the project changed.
    assert [lib for lib in libs if lib in fanned] == []
    # `core` and `codegen` both hang off `toolchain` and neither depends
    # on the other, so they overlap and neither is a choke point either.
    # This reproduces the real `optimized/` capture exactly.
    assert fanned == ["toolchain", "app", "all"]


def test_impact_is_populated_and_ranks_the_list():
    nodes, edges = ["a", "b", "c"], [("a", "b"), ("b", "c")]
    result = _analyzer(nodes, edges).analyze_bottlenecks()

    assert result.choke_point_impact == {"a": 2, "b": 1, "c": 0}
    assert result.choke_points == ["a", "b", "c"], "ranked by descendants, most first"


def test_fully_independent_elements_have_no_choke_points():
    assert _choke_points(["x", "y", "z"], []) == []


def test_single_element_graph_is_trivially_a_choke_point():
    assert _choke_points(["only"], []) == ["only"]
