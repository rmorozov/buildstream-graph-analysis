"""UX-44: slack must be real, and the improvement ranking must point at
the elements worth improving.

`_compute_all_slacks` returned `task.dur_us * 0.5` for every element,
under a docstring saying the full implementation "would use
forward/backward pass". Because that placeholder was the sole input to
`compute_sensitivity`, every published quantity became a function of
duration alone:

- the score `1 / (1 + 0.5 * duration)` is monotonically *decreasing* in
  duration, so "top improvement opportunity" meant "shortest element on
  the critical path";
- `best_case_speedup` came out ~2.0x for any graph whose critical path
  is a small share of total work, carrying no information;
- `total_improvable_time_us` summed slack, which is by definition the
  time whose elimination changes nothing.

The tests below are built on graphs where the right answer is known by
construction rather than by re-running the implementation.
"""
import networkx as nx

from bga.ingest.models import NormalizedTask, TaskKey, TaskKind
from bga.structural.analyzer import ElementDependencyGraph, StructuralAnalyzer


def _task(uid, dur_us):
    return NormalizedTask(
        task_key=TaskKey(element_uid=uid, task_kind=TaskKind.BUILD, phase="EXECUTION"),
        ready_us=0,
        start_us=0,
        finish_us=dur_us,
    )


def _analyzer(durations, edges):
    G = nx.DiGraph()
    for uid in durations:
        G.add_node(uid)
    for pred, succ in edges:
        G.add_edge(pred, succ)
    tasks = {uid: _task(uid, dur) for uid, dur in durations.items()}
    return StructuralAnalyzer(ElementDependencyGraph(G=G, predecessors={}, successors={}), tasks)


# --- real slack ---------------------------------------------------------

def test_critical_path_elements_have_exactly_zero_slack():
    """Two branches off a root: the 9s branch is critical, the 6s one
    has exactly 3s of float."""
    analyzer = _analyzer(
        {"r": 0, "a1": 5_000_000, "a2": 4_000_000, "b1": 3_000_000, "b2": 3_000_000, "sink": 0},
        [("r", "a1"), ("a1", "a2"), ("a2", "sink"),
         ("r", "b1"), ("b1", "b2"), ("b2", "sink")],
    )

    slacks = analyzer._compute_all_slacks()

    assert slacks["a1"] == 0.0 and slacks["a2"] == 0.0
    assert slacks["b1"] == 3_000_000.0 and slacks["b2"] == 3_000_000.0


def test_slack_is_not_half_the_duration():
    """The placeholder's signature: slack == duration * 0.5 for every
    element regardless of graph shape."""
    analyzer = _analyzer(
        {"a": 6_000_000, "b": 4_000_000}, [("a", "b")]
    )

    slacks = analyzer._compute_all_slacks()

    # A pure chain has no float anywhere. The placeholder said 3s and 2s.
    assert slacks == {"a": 0.0, "b": 0.0}


# --- the ranking --------------------------------------------------------

def test_longest_critical_element_ranks_first_not_last():
    """The inversion, minimally. Three chained elements of 6s/1s/3s: the
    6s one is the opportunity. The old formula ranked the 1s one top."""
    analyzer = _analyzer(
        {"big": 6_000_000, "small": 1_000_000, "mid": 3_000_000},
        [("big", "small"), ("small", "mid")],
    )

    ranked = [key for key, _, _ in analyzer.compute_sensitivity().top_opportunities]

    assert ranked == ["big", "mid", "small"]


def test_element_with_slack_is_not_an_opportunity_at_all():
    """`extra` runs alongside a chain twice its length. No amount of
    speeding it up moves the finish, so its score is 0 - not a small
    positive number that can outrank real work."""
    analyzer = _analyzer(
        {"a": 5_000_000, "b": 5_000_000, "extra": 1_000_000},
        [("a", "b")],
    )

    result = analyzer.compute_sensitivity()

    assert result.sensitivity_scores["extra"] == 0.0
    assert "extra" not in [key for key, _, _ in result.top_opportunities]


def test_saving_is_capped_where_the_next_path_becomes_critical():
    """`big` is 10s on a 12s critical path, but a parallel path is 9s -
    so shortening `big` can only buy 3s before that path takes over.
    Reporting its full 10s would overstate the payoff more than 3x.
    """
    analyzer = _analyzer(
        {"r": 0, "big": 10_000_000, "tail": 2_000_000, "par": 9_000_000, "sink": 0},
        [("r", "big"), ("big", "tail"), ("tail", "sink"),
         ("r", "par"), ("par", "sink")],
    )

    result = analyzer.compute_sensitivity()
    makespan = result.critical_path_us

    assert makespan == 12_000_000
    saving = result.sensitivity_scores["big"] * makespan
    assert round(saving) == 3_000_000


# --- the aggregates -----------------------------------------------------

def test_best_case_speedup_is_not_a_constant():
    """~2.0x for any graph was the old behaviour, on graphs of any
    shape. These three differ structurally and must score differently."""
    shapes = {
        # One long branch and one short: the short one binds.
        "uneven": ({"r": 0, "a": 8_000_000, "b": 2_000_000}, [("r", "a"), ("r", "b")]),
        # Same, with the two branches closer together - less to gain.
        "close": ({"r": 0, "a": 8_000_000, "b": 7_000_000}, [("r", "a"), ("r", "b")]),
        # A chain hanging off a wide base.
        "chain_over_base": (
            {"r": 0, "a": 5_000_000, "b": 5_000_000, "side": 3_000_000},
            [("r", "a"), ("a", "b"), ("r", "side")],
        ),
    }
    speedups = {
        name: _analyzer(durations, edges).compute_sensitivity().best_case_speedup
        for name, (durations, edges) in shapes.items()
    }

    assert len(set(speedups.values())) == len(speedups), speedups
    # Sanity: the graph with the most slack has the most to gain.
    assert speedups["uneven"] > speedups["close"]


def test_total_improvable_is_a_makespan_reduction_not_a_sum_of_slack():
    """The 9s critical branch can shed at most 3s before the 6s branch
    binds. Summing slack would have said 6s (two 3s-slack elements), on
    a graph whose finish cannot drop below 6s."""
    result = _analyzer(
        {"r": 0, "a1": 5_000_000, "a2": 4_000_000, "b1": 3_000_000, "b2": 3_000_000, "sink": 0},
        [("r", "a1"), ("a1", "a2"), ("a2", "sink"),
         ("r", "b1"), ("b1", "b2"), ("b2", "sink")],
    ).compute_sensitivity()

    assert result.critical_path_us == 9_000_000
    assert result.total_improvable_time_us == 3_000_000
    assert result.best_case_speedup == 9 / 6


def test_total_improvable_never_exceeds_the_critical_path():
    """The old quantity was a sum over work and routinely exceeded the
    build's own length - 2828s of "improvable time" on a 362s run."""
    for durations, edges in [
        ({"a": 6_000_000, "b": 4_000_000}, [("a", "b")]),
        ({"r": 0, "x": 5_000_000, "y": 5_000_000}, [("r", "x"), ("r", "y")]),
        ({"a": 1_000_000, "b": 2_000_000, "c": 3_000_000}, [("a", "b"), ("a", "c")]),
    ]:
        result = _analyzer(durations, edges).compute_sensitivity()
        assert 0 <= result.total_improvable_time_us <= result.critical_path_us


def test_pure_chain_reports_an_unbounded_ceiling_not_no_speedup():
    """No parallel path means nothing to bind: the whole critical path
    is improvable and the ratio is unbounded. Reporting a finite 1.0
    here would say "no speedup available", the opposite of the truth.
    """
    result = _analyzer(
        {"a": 3_000_000, "b": 3_000_000}, [("a", "b")]
    ).compute_sensitivity()

    assert result.critical_path_us == 6_000_000
    assert result.total_improvable_time_us == 6_000_000
    assert result.best_case_speedup is None


def test_unbounded_ceiling_renders_as_words_not_a_number(tmp_path):
    """End to end through a real run, not a stub: a linear chain has no
    parallel path, so the report must say so in words rather than print
    a number that means the opposite."""
    from bga.report.text import format_text
    from tests.fixtures import topologies

    analyzer = topologies.build_analyzer(tmp_path, topologies.linear_chain())
    output = format_text(analyzer.analyze())

    assert "unbounded (every element is on the critical path)" in output


def test_empty_graph_is_safe():
    result = _analyzer({}, []).compute_sensitivity()

    assert result.top_opportunities == []
    assert result.critical_path_us == 0
    assert result.total_improvable_time_us == 0
    # No graph means no ratio to report - the same "unknown" the pure
    # chain uses, rather than a fabricated 1.0.
    assert result.best_case_speedup is None
