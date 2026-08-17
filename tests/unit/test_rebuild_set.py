"""`tools/bst_rebuild_set.py`: the delete set that makes a bounded real
subgraph of a cached project actually rebuild.

The property under test is the one that makes the round-6 CI capture
work at all: BuildStream builds an element when *its own* artifact is
missing, so a delete set that is not upward-closed leaves cached
dependents in place and the build stops short of them. A set that
under-includes does not fail loudly - it silently produces a capture
with fewer built elements than intended, which is exactly the kind of
quiet wrongness the rest of this repository's fixtures exist to prevent.
"""
import json

import pytest

from tools.bst_rebuild_set import build_successors, rebuild_set


def _graph(uids, edges):
    return {
        "elements": [{"uid": uid} for uid in uids],
        "dependencies": [
            {"predecessor": p, "successor": s, "dependency_type": t}
            for p, s, t in edges
        ],
    }


CHAIN = _graph(
    ["a.bst", "b.bst", "c.bst", "d.bst"],
    [
        ("a.bst", "b.bst", "build"),
        ("b.bst", "c.bst", "build"),
        ("c.bst", "d.bst", "build"),
    ],
)


def test_cut_pulls_in_everything_above_it():
    assert rebuild_set(CHAIN, ["b.bst"]) == ["b.bst", "c.bst", "d.bst"]


def test_cut_does_not_pull_in_anything_below_it():
    """The whole point of building against a warm cache: the base stays
    cached and is never rebuilt."""
    assert "a.bst" not in rebuild_set(CHAIN, ["b.bst"])


def test_top_cut_is_just_itself():
    assert rebuild_set(CHAIN, ["d.bst"]) == ["d.bst"]


def test_multiple_cuts_are_unioned_and_deduplicated():
    assert rebuild_set(CHAIN, ["b.bst", "c.bst"]) == ["b.bst", "c.bst", "d.bst"]


def test_result_is_sorted():
    graph = _graph(
        ["z.bst", "m.bst", "a.bst"],
        [("z.bst", "m.bst", "build"), ("m.bst", "a.bst", "build")],
    )

    assert rebuild_set(graph, ["z.bst"]) == ["a.bst", "m.bst", "z.bst"]


def test_runtime_edges_do_not_propagate_a_rebuild():
    """`UX-52`'s rule applied to a second consumer: a runtime-only
    dependent does not need its dependency staged at build time, so
    deleting the dependency cannot force it to rebuild."""
    graph = _graph(
        ["lib.bst", "app.bst"], [("lib.bst", "app.bst", "runtime")]
    )

    assert rebuild_set(graph, ["lib.bst"]) == ["lib.bst"]


def test_runtime_dependent_still_propagates_via_its_own_build_edges():
    graph = _graph(
        ["lib.bst", "app.bst", "top.bst"],
        [
            ("lib.bst", "app.bst", "runtime"),
            ("app.bst", "top.bst", "build"),
        ],
    )

    assert rebuild_set(graph, ["app.bst"]) == ["app.bst", "top.bst"]


def test_diamond_is_not_double_counted():
    graph = _graph(
        ["base.bst", "left.bst", "right.bst", "top.bst"],
        [
            ("base.bst", "left.bst", "build"),
            ("base.bst", "right.bst", "build"),
            ("left.bst", "top.bst", "build"),
            ("right.bst", "top.bst", "build"),
        ],
    )

    assert rebuild_set(graph, ["base.bst"]) == [
        "base.bst",
        "left.bst",
        "right.bst",
        "top.bst",
    ]


def test_unknown_cut_is_an_error_not_an_empty_contribution():
    """A typo'd cut that contributed nothing would quietly shrink the
    captured subgraph with no signal at all."""
    with pytest.raises(KeyError) as excinfo:
        rebuild_set(CHAIN, ["b.bst", "typo.bst"])

    assert "typo.bst" in excinfo.value.args[0]


def test_build_successors_skips_runtime_edges_only():
    successors = build_successors(
        [
            {"predecessor": "a.bst", "successor": "b.bst", "dependency_type": "build"},
            {"predecessor": "a.bst", "successor": "c.bst", "dependency_type": "runtime"},
            {"predecessor": "a.bst", "successor": "d.bst", "dependency_type": "all"},
        ]
    )

    assert successors["a.bst"] == ["b.bst", "d.bst"]


def test_cli_prints_one_element_per_line(tmp_path, capsys):
    from tools.bst_rebuild_set import main

    graph_path = tmp_path / "graph.json"
    graph_path.write_text(json.dumps(CHAIN))

    argv = ["bst_rebuild_set.py", str(graph_path), "--cut", "c.bst"]
    import sys

    saved, sys.argv = sys.argv, argv
    try:
        assert main() == 0
    finally:
        sys.argv = saved

    assert capsys.readouterr().out.splitlines() == ["c.bst", "d.bst"]


def test_cli_reports_an_unknown_cut_and_fails(tmp_path, capsys):
    from tools.bst_rebuild_set import main

    graph_path = tmp_path / "graph.json"
    graph_path.write_text(json.dumps(CHAIN))

    argv = ["bst_rebuild_set.py", str(graph_path), "--cut", "nope.bst"]
    import sys

    saved, sys.argv = sys.argv, argv
    try:
        assert main() == 1
    finally:
        sys.argv = saved

    assert "nope.bst" in capsys.readouterr().err
