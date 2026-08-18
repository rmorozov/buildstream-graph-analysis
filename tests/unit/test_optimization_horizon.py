"""UX-74: one ~60-minute capture used to yield exactly one finding.

On round 9's real `freedesktop-sdk` capture 77% of elements have zero
slack, so the chain re-forms the moment anything shrinks and the *second*
thing to fix cost another full build to discover. Everything these tests
cover is a longest-path recompute over data the tool already holds -
0.40 ms each, 17 ms for the whole projection.
"""
from bga.graph.edg import (
    compute_joint_saving,
    compute_latent_heavies,
    compute_optimization_horizon,
)
from bga.ingest.models import DependencyEdge, Element, Graph


def _chain_with_a_latent_branch():
    """A -> B -> C is the chain; L hangs off A on its own branch.

    L is heavy (40) but shorter than the B+C tail (60), so it is worth
    nothing to fix today - and becomes binding the moment B is fixed.
    """
    return Graph(
        elements=[Element("A"), Element("B"), Element("C"), Element("L")],
        dependencies=[
            DependencyEdge("A", "B"), DependencyEdge("B", "C"),
            DependencyEdge("A", "L"),
        ],
    )


_CHAIN_DURATIONS = {"A": 100, "B": 50, "C": 10, "L": 40}


def test_the_horizon_names_what_becomes_binding_after_each_fix():
    horizon = compute_optimization_horizon(
        _chain_with_a_latent_branch(), _CHAIN_DURATIONS
    )

    assert [step["element_uid"] for step in horizon[:2]] == ["A", "B"]
    assert horizon[0]["saving_us"] == 100
    assert horizon[0]["cumulative_saving_us"] == 100
    # Zeroing B leaves max(C, L) = 40 hanging off a free A, so the finish
    # drops from 60 to 40 - B is worth 20, not its own 50.
    assert horizon[1]["saving_us"] == 20


def test_a_latent_element_is_named_when_it_enters_the_frontier():
    """`L` is on no critical path today. On the real capture the
    equivalent is `git-minimal.bst`, the **4th heaviest element in the
    build**, which appears in no ranking the tool produces."""
    horizon = compute_optimization_horizon(
        _chain_with_a_latent_branch(), _CHAIN_DURATIONS
    )

    assert "L" in horizon[1]["entering"]


def test_savings_add_along_a_chain():
    """Two links of one chain: shortening both shortens the chain by
    both. `UX-20` refuses to group these, which is backwards."""
    graph = Graph(
        elements=[Element("A"), Element("B")],
        dependencies=[DependencyEdge("A", "B")],
    )
    durations = {"A": 100, "B": 50}

    assert compute_joint_saving(graph, durations, ["A", "B"]) == 150
    assert compute_joint_saving(graph, durations, ["A"]) == 100
    assert compute_joint_saving(graph, durations, ["B"]) == 50


def test_savings_do_not_add_across_parallel_branches():
    """Two independent branches: the shorter one was never binding, so
    fixing it buys nothing until the longer one is gone. `UX-20` would
    group exactly these."""
    graph = Graph(
        elements=[Element("R"), Element("X"), Element("Y")],
        dependencies=[DependencyEdge("R", "X"), DependencyEdge("R", "Y")],
    )
    durations = {"R": 0, "X": 100, "Y": 60}

    assert compute_joint_saving(graph, durations, ["X"]) == 40
    assert compute_joint_saving(graph, durations, ["Y"]) == 0
    # 40 + 0 individually; 100 together - neither the sum nor a maximum,
    # which is exactly why it has to be simulated rather than derived.
    assert compute_joint_saving(graph, durations, ["X", "Y"]) == 100


def test_latent_heavies_are_off_path_and_above_the_rounding_floor():
    latent = compute_latent_heavies(
        {"A": 100, "B": 50, "L": 40, "tiny": 1},
        critical_path=["A", "B"],
        total_us=1000,
    )

    assert [entry["element_uid"] for entry in latent] == ["L"]
    assert latent[0]["duration_us"] == 40


def test_structural_elements_are_never_a_step_or_a_latent_heavy():
    """`UX-34`: a `stack` has no build commands to make faster, so "fix
    it" is not a thing a reader can do."""
    graph = Graph(
        elements=[Element("A"), Element("S"), Element("B")],
        dependencies=[DependencyEdge("A", "S"), DependencyEdge("S", "B")],
    )
    durations = {"A": 100, "S": 90, "B": 10}

    horizon = compute_optimization_horizon(graph, durations, excluded={"S"})
    assert "S" not in [step["element_uid"] for step in horizon]

    latent = compute_latent_heavies(
        {"A": 100, "S": 90}, critical_path=["A"], total_us=1000, excluded={"S"},
    )
    assert latent == []


def test_the_horizon_is_bounded():
    graph = Graph(
        elements=[Element(f"e{i}") for i in range(20)],
        dependencies=[DependencyEdge(f"e{i - 1}", f"e{i}") for i in range(1, 20)],
    )
    durations = {f"e{i}": 100 - i for i in range(20)}

    assert len(compute_optimization_horizon(graph, durations)) == 5
    assert len(compute_optimization_horizon(graph, durations, steps=2)) == 2
