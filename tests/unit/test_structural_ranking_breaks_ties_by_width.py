"""UX-1005 track C (Ruslan): `structural_ranking` derives a synthetic
slack from `bst show` deps alone, for a capture with no `--plan` -
level from the bottom (longest dependent chain to a target, in hops),
ties broken by declared width (`notparallel` yields to a wider
sibling). Shaped on `examples/13-mixed-graph`: `giant.bst` and 24
`narrow-*.bst` elements depend only on `toolchain.bst` and sit at the
same level, so deps alone never separates them - the tie-break is what
does. Mutation: dropping the tie-break (rank by level alone)."""
from tools.bst_native_build_tracer import structural_ranking


def _mixed_graph_shape():
    kinds = {"toolchain.bst": "cmake", "giant.bst": "cmake", "all.bst": "stack"}
    deps = {"toolchain.bst": [], "giant.bst": ["toolchain.bst"],
           "all.bst": ["giant.bst"], "narrow-01.bst": ["toolchain.bst"]}
    kinds["narrow-01.bst"] = "cmake"
    deps["all.bst"].append("narrow-01.bst")
    notparallel = {"narrow-01.bst": True}
    return kinds, deps, notparallel


def test_the_deepest_dependency_ranks_first():
    kinds, deps, notparallel = _mixed_graph_shape()
    ranking = structural_ranking(kinds, deps, notparallel)
    assert ranking["toolchain.bst"] < ranking["giant.bst"] < ranking["all.bst"]


def test_a_notparallel_sibling_at_the_same_level_yields_to_a_wider_one():
    kinds, deps, notparallel = _mixed_graph_shape()
    ranking = structural_ranking(kinds, deps, notparallel)
    assert ranking["giant.bst"] < ranking["narrow-01.bst"], (
        "same level (both depend only on toolchain.bst) - the wide "
        "giant must still be admitted first, since the notparallel "
        "narrow element can only ever use its own one slot")
