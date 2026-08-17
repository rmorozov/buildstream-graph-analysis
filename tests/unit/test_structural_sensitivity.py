"""P1-38: compute_sensitivity must not crash or produce out-of-range
scores for negative slack.

Found via real build data (examples/02-deep-chain-mixed-kinds's CI run),
not a hand-built fixture: `_compute_all_slacks()`'s simplified `dur_us *
0.5` estimate (bga/structural/analyzer.py:559-567) produced slack of
exactly -1,000,000us for one real element, the formula's
zero-denominator point. These tests inject negative slack directly (via
`_compute_all_slacks`, monkeypatched) rather than by constructing a
negative-duration `NormalizedTask` - that construction is now rejected
by `NormalizedTask.__post_init__` itself (P1-36), and this task is
scoped to `compute_sensitivity`'s own handling of whatever slack value
it's given, not to how a negative slack value could arise.
"""
import networkx as nx

from bga.ingest.models import NormalizedTask, TaskKey, TaskKind
from bga.structural.analyzer import ElementDependencyGraph, StructuralAnalyzer


def _make_task(elem_uid, start_us, finish_us):
    return NormalizedTask(
        task_key=TaskKey(element_uid=elem_uid, task_kind=TaskKind.BUILD, phase="EXECUTION"),
        ready_us=start_us,
        start_us=start_us,
        finish_us=finish_us,
    )


def _analyzer_for(tasks, edges):
    G = nx.DiGraph()
    for key in tasks:
        G.add_node(key)
    for pred, succ in edges:
        G.add_edge(pred, succ)
    edg = ElementDependencyGraph(G=G, predecessors={}, successors={})
    return StructuralAnalyzer(edg, tasks)


def test_compute_sensitivity_zero_denominator_slack_does_not_crash(monkeypatch):
    tasks = {
        "a": _make_task("a", start_us=0, finish_us=1_000_000),
        "b": _make_task("b", start_us=1_000_000, finish_us=2_000_000),
    }
    analyzer = _analyzer_for(tasks, edges=[("a", "b")])
    # The real value that reproduced the crash.
    monkeypatch.setattr(analyzer, "_compute_all_slacks", lambda: {"a": -1_000_000, "b": -1_000_000})

    result = analyzer.compute_sensitivity()

    for key, score, impact_pct in result.top_opportunities:
        assert score >= 0.0, f"{key} got negative sensitivity score {score}"


def test_compute_sensitivity_more_negative_slack_does_not_crash(monkeypatch):
    tasks = {
        "a": _make_task("a", start_us=0, finish_us=1_000_000),
        "b": _make_task("b", start_us=1_000_000, finish_us=2_000_000),
    }
    analyzer = _analyzer_for(tasks, edges=[("a", "b")])
    # Well past the zero-denominator point.
    monkeypatch.setattr(analyzer, "_compute_all_slacks", lambda: {"a": -2_000_000, "b": -2_000_000})

    result = analyzer.compute_sensitivity()

    for key, score, impact_pct in result.top_opportunities:
        assert score >= 0.0, f"{key} got negative sensitivity score {score}"


def test_compute_sensitivity_nonnegative_slack_unaffected():
    """Real, ordinary positive-duration tasks on a two-element chain.

    UX-44 replaced the scored quantity, so this no longer pins the old
    `1 / (1 + slack_s)` decay formula - that formula's only input was the
    `duration * 0.5` placeholder, and pinning it would pin the defect.
    What it pins now is the property the formula was reaching for and
    got backwards: both elements are on the critical path of a pure
    chain, so each one's saving is its entire duration, and the score is
    that saving as a fraction of the finish.
    """
    tasks = {
        "a": _make_task("a", start_us=0, finish_us=1_000_000),
        "b": _make_task("b", start_us=1_000_000, finish_us=2_000_000),
    }
    analyzer = _analyzer_for(tasks, edges=[("a", "b")])

    result = analyzer.compute_sensitivity()

    scores = {key: score for key, score, _ in result.top_opportunities}
    # 1s each on a 2s chain: halving either halves the build.
    assert scores["a"] == 0.5
    assert scores["b"] == 0.5
    assert result.critical_path_us == 2_000_000
