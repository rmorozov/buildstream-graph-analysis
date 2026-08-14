"""P3-09: per-module unit tests for bga/graph/edg.py.

Depth/reachability/dominators/critical-path/slack on small hand-built
graphs with exact, hand-computed expected values - not just "key
exists" checks (that class of check is exactly what missed the M6
`max_depth: 0` / `num_elements: 6` bugs, per docs/tasks/P1-18.md).
"""
import pytest

from bga.exceptions import AnalysisError
from bga.graph.edg import (
    compute_critical_path,
    compute_dominators,
    compute_in_out_degree,
    compute_reachability,
    compute_slack,
    compute_unweighted_depth,
)
from bga.ingest.models import DependencyEdge, Element, Graph


def _diamond():
    """A -> {B, C} -> D."""
    return Graph(
        elements=[Element("A"), Element("B"), Element("C"), Element("D")],
        dependencies=[
            DependencyEdge("A", "B"), DependencyEdge("A", "C"),
            DependencyEdge("B", "D"), DependencyEdge("C", "D"),
        ],
    )


def _linear_chain(n=3):
    uids = [chr(ord("A") + i) for i in range(n)]
    return Graph(
        elements=[Element(uid) for uid in uids],
        dependencies=[DependencyEdge(uids[i - 1], uids[i]) for i in range(1, n)],
    )


def _cycle():
    return Graph(
        elements=[Element("A"), Element("B"), Element("C")],
        dependencies=[
            DependencyEdge("A", "B"), DependencyEdge("B", "C"), DependencyEdge("C", "A"),
        ],
    )


# --- Depth ---

def test_diamond_depth():
    depth = compute_unweighted_depth(_diamond())
    assert depth == {"A": 0, "B": 1, "C": 1, "D": 2}


def test_linear_chain_depth():
    depth = compute_unweighted_depth(_linear_chain(4))
    assert depth == {"A": 0, "B": 1, "C": 2, "D": 3}


def test_cycle_raises_analysis_error():
    with pytest.raises(AnalysisError):
        compute_unweighted_depth(_cycle())


# --- In/out degree ---

def test_diamond_in_out_degree():
    in_deg, out_deg = compute_in_out_degree(_diamond())
    assert in_deg == {"A": 0, "B": 1, "C": 1, "D": 2}
    assert out_deg == {"A": 2, "B": 1, "C": 1, "D": 0}


# --- Reachability ---

def test_diamond_reachability():
    downstream, upstream = compute_reachability(_diamond())
    assert downstream["A"] == {"B", "C", "D"}
    assert downstream["B"] == {"D"}
    assert downstream["C"] == {"D"}
    assert downstream["D"] == set()
    assert upstream["D"] == {"A", "B", "C"}
    assert upstream["B"] == {"A"}
    assert upstream["A"] == set()


# --- Dominators ---

def test_diamond_dominators():
    """D has two disjoint paths from A (via B, via C), so only A and D
    itself dominate D - neither B nor C alone does."""
    dom = compute_dominators(_diamond())
    assert dom["A"] == {"A"}
    assert dom["B"] == {"A", "B"}
    assert dom["C"] == {"A", "C"}
    assert dom["D"] == {"A", "D"}


def test_linear_chain_dominators():
    """Every element on a single path dominates everything after it."""
    dom = compute_dominators(_linear_chain(3))
    assert dom["A"] == {"A"}
    assert dom["B"] == {"A", "B"}
    assert dom["C"] == {"A", "B", "C"}


# --- Critical path ---

def test_diamond_critical_path_picks_longer_branch():
    """B (50us) is far longer than C (10us) - the critical path must
    route through B, not C, even though both connect A to D."""
    durations = {"A": 10, "B": 50, "C": 10, "D": 5}
    length, path = compute_critical_path(_diamond(), durations)
    assert length == 65  # A(10) + B(50) + D(5)
    assert path == ["A", "B", "D"]


def test_linear_chain_critical_path_is_the_full_chain():
    durations = {"A": 10, "B": 20, "C": 30}
    length, path = compute_critical_path(_linear_chain(3), durations)
    assert length == 60
    assert path == ["A", "B", "C"]


# --- Slack ---

def test_diamond_slack_zero_on_critical_path_nonzero_off_it():
    """Hand-computed: A/B/D are on the (B-routed) critical path and
    have zero slack; C has 40us of slack (60us via B vs 20us via C -
    C could run up to 40us later without delaying D)."""
    durations = {"A": 10, "B": 50, "C": 10, "D": 5}
    length, _ = compute_critical_path(_diamond(), durations)
    slack = compute_slack(_diamond(), durations, length)
    assert slack["A"] == 0
    assert slack["B"] == 0
    assert slack["D"] == 0
    assert slack["C"] == 40


def test_linear_chain_has_zero_slack_everywhere():
    """A single path has no alternative routing - nothing can be
    delayed without delaying the end."""
    durations = {"A": 10, "B": 20, "C": 30}
    length, _ = compute_critical_path(_linear_chain(3), durations)
    slack = compute_slack(_linear_chain(3), durations, length)
    assert slack == {"A": 0, "B": 0, "C": 0}
