"""UX-70: rank by what optimizing an element would actually save.

Share of the critical path answers *what is the chain made of*. It does
not answer *what happens if I change it*, because it holds the rest of
the graph fixed — and on a real `freedesktop-sdk` capture **97 of 126
elements have zero slack**, so the rest of the graph does not stay fixed.

Measured there, `components/python3.bst` was ranked **third most worth
optimizing** at 17.7% of the critical path, and making it instant saves
**114s of 3610s — 3.2%**. A user could spend a week on it and recover a
minute. The other three top elements were worth 78–100% of their
duration, so the failure is specific to graph shape rather than uniform.
"""
from bga.ingest.models import DependencyEdge, Element, Graph
from bga.graph.edg import compute_realizable_savings


def _graph(edges, elements=None):
    uids = elements or sorted({u for e in edges for u in e})
    return Graph(
        elements=[Element(uid=u) for u in uids],
        dependencies=[
            DependencyEdge(predecessor=p, successor=s, dependency_type="build")
            for p, s in edges
        ],
    )


def test_a_chain_element_is_worth_its_whole_duration():
    """Nothing runs in parallel with it, so all of its time is on the
    binding path - the `cmake-stage1.bst` case."""
    graph = _graph([("a.bst", "b.bst"), ("b.bst", "c.bst")])
    durations = {"a.bst": 10, "b.bst": 100, "c.bst": 10}

    savings = compute_realizable_savings(graph, durations, ["b.bst"])

    assert savings["b.bst"] == 100


def test_an_element_masked_by_a_near_tie_chain_is_worth_far_less():
    """The `python3.bst` case, in miniature. `slow.bst` takes 100 but a
    parallel chain takes 90, so eliminating it recovers only 10."""
    graph = _graph([
        ("root.bst", "slow.bst"), ("root.bst", "parallel.bst"),
        ("slow.bst", "sink.bst"), ("parallel.bst", "sink.bst"),
    ])
    durations = {"root.bst": 0, "slow.bst": 100, "parallel.bst": 90, "sink.bst": 0}

    savings = compute_realizable_savings(graph, durations, ["slow.bst"])

    assert savings["slow.bst"] == 10


def test_the_saving_is_never_negative():
    """Zeroing a duration can only shorten or leave the path; a negative
    would mean the longest-path computation disagreed with itself."""
    graph = _graph([("a.bst", "b.bst")])

    savings = compute_realizable_savings(graph, {"a.bst": 5, "b.bst": 5}, ["a.bst"])

    assert savings["a.bst"] >= 0


def test_a_zero_duration_element_is_not_evaluated():
    """Structural elements and cached ones have nothing to optimize, and
    reporting a 0 saving for them would read as a measured finding."""
    graph = _graph([("a.bst", "b.bst")])

    savings = compute_realizable_savings(graph, {"a.bst": 0, "b.bst": 5}, ["a.bst"])

    assert "a.bst" not in savings


def test_the_candidate_list_is_bounded():
    """Each candidate costs one longest-path recomputation, so an
    unbounded sweep would be a surprising cost inside `analyze`."""
    from bga.graph.edg import REALIZABLE_SAVING_CANDIDATES

    edges = [(f"e{i}.bst", f"e{i+1}.bst") for i in range(40)]
    graph = _graph(edges)
    durations = {f"e{i}.bst": 10 for i in range(41)}

    savings = compute_realizable_savings(
        graph, durations, [f"e{i}.bst" for i in range(41)]
    )

    assert len(savings) == REALIZABLE_SAVING_CANDIDATES


def test_no_candidates_costs_nothing():
    assert compute_realizable_savings(_graph([("a.bst", "b.bst")]), {}, []) == {}


# --- what the report does with it ---------------------------------------


def test_the_ranking_prefers_realizable_saving_over_duration():
    """The real inversion: `doxygen` is shorter than `python3` but worth
    4.5x more, and must therefore rank above it."""
    from bga.findings import heaviest_on_path

    class _R:
        signals = {"critical_path_detail": [
            {"element_uid": "python3.bst", "duration_us": 639_800_000,
             "share_of_path": 0.177, "is_structural_kind": False,
             "realizable_saving_us": 114_100_000},
            {"element_uid": "doxygen.bst", "duration_us": 513_500_000,
             "share_of_path": 0.142, "is_structural_kind": False,
             "realizable_saving_us": 513_500_000},
        ]}

    assert [d["element_uid"] for d in heaviest_on_path(_R())] == [
        "doxygen.bst", "python3.bst",
    ]


def test_an_unevaluated_element_falls_back_to_duration():
    """`None` means not evaluated - it must not sort to the bottom as if
    it were worth nothing."""
    from bga.findings import heaviest_on_path

    class _R:
        signals = {"critical_path_detail": [
            {"element_uid": "small.bst", "duration_us": 10, "share_of_path": 0.1,
             "is_structural_kind": False, "realizable_saving_us": 5},
            {"element_uid": "big.bst", "duration_us": 1000, "share_of_path": 0.9,
             "is_structural_kind": False, "realizable_saving_us": None},
        ]}

    assert [d["element_uid"] for d in heaviest_on_path(_R())][0] == "big.bst"
