"""UX-539: the two algorithms `UX-531` measured and left, and their bound.

`UX-531` cut three per-gap scans and stopped at two terms that were not
missed lookups. Under cProfile at 4,002 elements:

```text
                                        calls          cumulative
descendants / ancestors, once per node  4,001 + 4,002      16.2 s
_resource_saturation_intervals          per gap            28.2 s
```

Both became the same substitution - compute once over the whole run,
read per node or per gap - so what these guards read is `UX-531`'s unit,
the **count of walks**, not the seconds. A second measured on a machine
running three tracks is a second of noise (`UX-538`); a walk count is
not.

- Choke-point detection asked the graph for adjacency `O(V*(V+E))`
  times, once per node. It now asks `O(V+E)` times, from one bitset
  closure over the topological order.
- The gap sweep built every sub-interval of the window when both its
  callers break at the end of the leading run: 1,520,246 built at 4,002
  elements, 651,649 read.

The answers are guarded elsewhere and unchanged: `_reachability_counts`
against `nx.descendants`/`nx.ancestors` below, and the interval sweep
against `test_resource_saturation_timeline.py`'s naive transcription of
the algorithm it replaced.
"""
import pathlib
import sys

import networkx as nx
import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga.attribution.blame_chain import (AttributionCategory,    # noqa: E402
                                         BlameChainAnalyzer)
from bga.ingest.models import (NormalizedTask, Resource, TaskKey,  # noqa: E402
                               TaskKind)
from bga.structural.analyzer import (ElementDependencyGraph,     # noqa: E402
                                     StructuralAnalyzer)

PROCESS = Resource.PROCESS


class _CountingDiGraph(nx.DiGraph):
    """A graph that records how often anything asks it for adjacency.

    Not a count of `nx.descendants` calls - a later round could
    reintroduce the per-node walk by hand and that name would not
    appear. Every reachability walk, however written, has to come
    through one of these three.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.adjacency_queries = 0

    def successors(self, node):
        self.adjacency_queries += 1
        return super().successors(node)

    def predecessors(self, node):
        self.adjacency_queries += 1
        return super().predecessors(node)

    def neighbors(self, node):
        self.adjacency_queries += 1
        return super().neighbors(node)


def _diamond_chain(links, graph_class=_CountingDiGraph):
    """`links` diamonds in series: every join is a choke point, so the
    signal under test is non-empty at every size."""
    G = graph_class()
    G.add_node("root")
    previous = "root"
    for i in range(links):
        left, right, join = f"a{i}", f"b{i}", f"j{i}"
        G.add_edge(previous, left)
        G.add_edge(previous, right)
        G.add_edge(left, join)
        G.add_edge(right, join)
        previous = join
    return G


def _bottlenecks(G):
    analyzer = StructuralAnalyzer(ElementDependencyGraph(G=G), {})
    G.adjacency_queries = 0
    result = analyzer.analyze_bottlenecks()
    return result, G.adjacency_queries


class TestChokePointsQueryTheGraphOncePerEdge:
    """The bound, in `UX-531`'s unit. A walk per node is what made this
    `O(V*(V+E))`; a walk per run is what it costs now."""

    @pytest.mark.parametrize("links", [10, 20, 40])
    def test_the_queries_stay_within_a_multiple_of_the_graph(self, links):
        G = _diamond_chain(links)
        _result, queries = _bottlenecks(G)
        budget = 3 * (G.number_of_nodes() + G.number_of_edges())
        assert queries <= budget, (
            f"{links} diamonds: {queries} adjacency queries for "
            f"{G.number_of_nodes()} nodes and {G.number_of_edges()} edges "
            f"(budget {budget}) - the walk is following the nodes again")

    def test_doubling_the_graph_does_not_quadruple_the_queries(self):
        """The clause the one above cannot supply: a budget scaled by
        `V+E` still passes if the constant merely happens to fit."""
        small = _bottlenecks(_diamond_chain(20))[1]
        large = _bottlenecks(_diamond_chain(40))[1]
        assert large <= 2.5 * small, (
            f"20 diamonds took {small} queries and 40 took {large}")

    def test_the_queries_are_not_zero_and_the_signal_is_not_empty(self):
        """Non-vacuity: a bound met by doing nothing is not a bound."""
        result, queries = _bottlenecks(_diamond_chain(20))
        assert queries > 0
        # root plus one join per diamond, all mutually comparable.
        assert len(result.choke_points) == 21, result.choke_points


#: Shapes chosen for what a closure gets wrong: a node comparable to
#: everything, two components that reach nothing of each other, a node
#: with no edges at all, and a join that both branches reach.
REACHABILITY_SHAPES = [
    [("a", "b"), ("b", "c"), ("c", "d")],
    [("a", "b"), ("c", "d")],
    [("a", "b"), ("a", "c"), ("b", "d"), ("c", "d")],
    [],
]


class TestTheClosureAnswersWhatTheWalkAnswered:
    """The oracle. The bound above only says the work moved; this says
    the answer did not."""

    @pytest.mark.parametrize("edges", REACHABILITY_SHAPES)
    def test_counts_match_a_per_node_walk(self, edges):
        G = nx.DiGraph()
        G.add_nodes_from(["a", "b", "c", "d", "lonely"])
        G.add_edges_from(edges)
        analyzer = StructuralAnalyzer(ElementDependencyGraph(G=G), {})
        descendants, ancestors = analyzer._reachability_counts()
        for node in G.nodes():
            assert descendants[node] == len(nx.descendants(G, node)), node
            assert ancestors[node] == len(nx.ancestors(G, node)), node


class _CountingSlices(list):
    """A slice table that records every slice the gap sweep inspects."""

    def __init__(self, items):
        super().__init__(items)
        self.reads = 0

    def __getitem__(self, index):
        self.reads += 1
        return super().__getitem__(index)


def _task(uid, ready_us, start_us, finish_us):
    return NormalizedTask(
        task_key=TaskKey(element_uid=uid, task_kind=TaskKind.BUILD,
                         phase="EXECUTION"),
        ready_us=ready_us, start_us=start_us, finish_us=finish_us,
        resources=[PROCESS])


def _one_short_saturation_then_noise(tail):
    """A gap of 10,000us whose saturation is over by 10us, followed by
    `tail` further holders that change occupancy inside the window and
    that no caller ever reads."""
    tasks = [_task("w.bst", 0, 10000, 10006), _task("h.bst", 0, 0, 10)]
    for k in range(tail):
        base = 20 + k * 20
        tasks.append(_task(f"l{k}.bst", 0, base, base + 10))
    return tasks


def _slices_inspected(tail):
    tasks = _one_short_saturation_then_noise(tail)
    analyzer = BlameChainAnalyzer(
        tasks, resource_capacity={PROCESS: 1}, max_jobs=1)
    analyzer._build_resource_timelines()
    counters = []
    for timeline in analyzer._resource_timelines.values():
        counter = _CountingSlices(timeline.active_keys)
        object.__setattr__(timeline, "active_keys", counter)
        counters.append(counter)
    saturated, holder_info = analyzer.classify_resource_wait(
        tasks[0], {}, {PROCESS: 1}, 0, 10000)
    return sum(c.reads for c in counters), saturated, holder_info


class TestTheGapSweepStopsWhereItsCallersStop:
    """The second bound. Both callers break at the end of the leading
    run, so what follows it in the window is not built."""

    def test_the_tail_of_the_window_costs_nothing(self):
        few = _slices_inspected(5)[0]
        many = _slices_inspected(200)[0]
        assert few == many, (
            f"5 later change points inspected {few} slices and 200 "
            f"inspected {many} - the sweep is covering the window again")

    def test_the_count_is_a_small_constant(self):
        """The clause that keeps the one above from passing on a pair of
        equally-terrible numbers."""
        inspected = _slices_inspected(200)[0]
        assert 0 < inspected <= 6, inspected

    def test_the_answer_is_still_the_leading_run(self):
        """Non-vacuity: a sweep that stops early must stop in the right
        place. Saturation runs [0, 10) and nowhere else that is read."""
        _reads, saturated, holder_info = _slices_inspected(200)
        assert saturated is True
        assert holder_info["explained_us"] == 10
        assert list(holder_info["blocking_tasks"]) == [
            "h.bst|BUILD|EXECUTION|0"]


def _resaturating_gap(runs):
    """A wait gap holding `runs` separated saturated segments - `UX-19`'s
    re-saturation, the shape that reaches `_build_holder_info` more than
    once."""
    tasks = [_task("w.bst", 0, 10000, 10006)]
    for k in range(runs):
        base = k * 100
        tasks.append(_task(f"h{k}.bst", 0, base, base + 10))
    return tasks


class TestTheHolderMapIsBuiltOnlyForTheSegmentThatIsKept:
    """The third bound. `_classify_wait_gap` returns the *first*
    resource-wait segment's holder_info and drops every later one, so
    accumulating and sorting those was work with no reader - 40.5% of
    the builds at 1,202 elements and 47.5% at 4,002 (`UX-541`)."""

    def _built(self, runs):
        tasks = _resaturating_gap(runs)
        analyzer = BlameChainAnalyzer(
            tasks, resource_capacity={PROCESS: 1}, max_jobs=1)
        analyzer._build_resource_timelines()
        built = []
        real = analyzer._build_holder_info

        def counting(*args, **kwargs):
            built.append(args[1])
            return real(*args, **kwargs)

        analyzer._build_holder_info = counting
        segments, info = analyzer._classify_wait_gap(tasks[0], 0, 10000)
        resource = [s for s in segments
                    if s[0] is AttributionCategory.RESOURCE_WAIT]
        return built, resource, info

    def test_many_saturated_segments_build_one_holder_map(self):
        built, resource, _info = self._built(8)
        assert len(resource) > 1, (
            f"the fixture produced {len(resource)} resource-wait segments, "
            f"so it cannot tell the two behaviours apart")
        assert len(built) == 1, (
            f"{len(resource)} resource-wait segments built {len(built)} "
            f"holder maps; only the first is ever returned")

    def test_the_one_built_is_the_one_returned(self):
        """Non-vacuity: building none would satisfy nothing, and
        building the *last* would answer a different question."""
        built, _resource, info = self._built(8)
        assert info is not None
        assert built == [info["wait_start_us"]] == [0]
