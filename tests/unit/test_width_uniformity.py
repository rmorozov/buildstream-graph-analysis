"""UX-49: `parallelism_efficiency` measured width uniformity, not
parallelism.

The formula is `mean_width / max_width` - how close each level is to the
widest one. That is maximized by the *worst* possible graph: a pure
serial chain scores a perfect 1.000, because every level is exactly as
wide as the widest. Adding parallelism to any graph can only lower it,
since it raises `max_width` faster than `mean_width`. On the real
`examples/06` pair the optimized fan-out scored 0.367 against the chained
baseline's 0.550 - the better graph scoring worse, the same failure mode
`UX-27` found in `efficiency_score`.

**Renamed rather than redefined.** The obvious alternative was to make
the field mean "how parallel is this build", but that question already
has a published answer in `mean_width` (equivalently
`StructuralMetrics.avg_parallelism`), which discriminates correctly on
the same pair: 1.1 chained against 2.2 fanned out. Redefining would have
left two names for one number. The formula computes a real, distinct
shape signal; only its name was wrong.

These tests pin both halves of that decision: the renamed field keeps its
uniformity semantics, and the field that answers the parallelism question
is checked to actually answer it.
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


def _profile(nodes, edges):
    G = nx.DiGraph()
    for node in nodes:
        G.add_node(node)
    for pred, succ in edges:
        G.add_edge(pred, succ)
    analyzer = StructuralAnalyzer(
        ElementDependencyGraph(G=G, predecessors={}, successors={}),
        {node: _task(node) for node in nodes},
    )
    return analyzer.compute_parallelism_profile()


CHAIN = (["a", "b", "c", "d"], [("a", "b"), ("b", "c"), ("c", "d")])
FAN_OUT = (["r", "x", "y", "z"], [("r", "x"), ("r", "y"), ("r", "z")])

# examples/06 in miniature: six libraries chained, versus fanned out off
# `core`. This is the pair the project exists to demonstrate.
_LIBS = [f"lib-{c}" for c in "abcdef"]
CHAINED = (
    ["core", *_LIBS, "app"],
    [("core", _LIBS[0])]
    + [(_LIBS[i], _LIBS[i + 1]) for i in range(len(_LIBS) - 1)]
    + [(_LIBS[-1], "app")],
)
FANNED = (
    ["core", *_LIBS, "app"],
    [("core", lib) for lib in _LIBS] + [(lib, "app") for lib in _LIBS],
)


def test_field_is_named_for_what_it_computes():
    profile = _profile(*FAN_OUT)

    assert not hasattr(profile, "parallelism_efficiency")
    assert profile.width_uniformity == profile.mean_width / profile.max_width


def test_serial_chain_is_perfectly_uniform_and_that_is_now_correct():
    """A chain scoring 1.000 was the bug under the old name and is the
    right answer under the new one: every level really is exactly as wide
    as the widest."""
    assert _profile(*CHAIN).width_uniformity == 1.0


def test_fan_out_is_less_uniform_than_a_chain():
    assert _profile(*FAN_OUT).width_uniformity < _profile(*CHAIN).width_uniformity


def test_uniformity_is_low_when_the_graph_has_a_narrow_waist():
    """The signal's actual use: peak parallelism not sustained across
    depth. Wide, then a single choke point, then wide again."""
    nodes = ["r", "a1", "a2", "a3", "waist", "b1", "b2", "b3"]
    edges = [("r", n) for n in ("a1", "a2", "a3")]
    edges += [(n, "waist") for n in ("a1", "a2", "a3")]
    edges += [("waist", n) for n in ("b1", "b2", "b3")]

    profile = _profile(nodes, edges)

    assert profile.max_width == 3
    assert profile.width_uniformity < 0.7


# --- the question the rename did NOT answer, and where it lives --------

def test_mean_width_is_what_answers_how_parallel_this_build_is():
    """The reason this was renamed rather than redefined. `mean_width`
    is average parallelism - elements over depth - and it moves the right
    way across the real macro optimization, where `width_uniformity`
    moves the wrong way."""
    chained = _profile(*CHAINED)
    fanned = _profile(*FANNED)

    # The parallelism answer: fanning out doubles average width.
    assert fanned.mean_width > chained.mean_width
    assert fanned.max_width > chained.max_width

    # And uniformity genuinely does move the other way, which is exactly
    # why it must not be called an efficiency.
    assert fanned.width_uniformity < chained.width_uniformity


def test_metrics_avg_parallelism_agrees_with_mean_width():
    """Two published fields, one number - checked so a future change to
    either cannot silently make them disagree."""
    G = nx.DiGraph()
    for pred, succ in FANNED[1]:
        G.add_edge(pred, succ)
    analyzer = StructuralAnalyzer(
        ElementDependencyGraph(G=G, predecessors={}, successors={}),
        {node: _task(node) for node in FANNED[0]},
    )

    assert analyzer.compute_structural_metrics().avg_parallelism == (
        analyzer.compute_parallelism_profile().mean_width
    )


def test_report_shows_the_discriminating_number(tmp_path):
    """`Parallelism Profile` printed only min and max, so the one number
    that separates the two graphs was invisible in the text report."""
    from bga.report.text import format_text
    from tests.fixtures import topologies

    analyzer = topologies.build_analyzer(tmp_path, topologies.diamond())
    output = format_text(analyzer.analyze())

    assert "Parallelism Profile: min=" in output
    assert "avg=" in output


def test_empty_graph_is_safe():
    assert _profile([], []).width_uniformity == 0.0
