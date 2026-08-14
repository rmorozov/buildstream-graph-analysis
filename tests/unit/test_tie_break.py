"""P3-04: dependency-blame tie-break tests (Part 7.1).

Tie-breaking rules, in order:
1. greatest normalized finish time
2. greatest longest-path-to-source depth
3. smallest task key (lexicographic)

Out-degree is never used (v8's rule, explicitly superseded).

`BlameChainAnalyzer.select_dependency_blame` implements this and is a
pure function of its arguments (it never reads `self`), so it's tested
directly here rather than through a full pipeline run - except for the
"adding an unrelated graph node must not change the result" case, which
is meaningfully only a full-pipeline claim and uses
`tests/fixtures/topologies.py::multiple_equal_predecessors`.
"""
from bga.attribution.blame_chain import BlameChainAnalyzer
from tests.fixtures import topologies as topo


def _analyzer():
    # select_dependency_blame doesn't touch self at all - an
    # analyzer with no tasks is a valid, cheap host for it.
    return BlameChainAnalyzer(normalized_tasks=[])


def test_greatest_finish_time_wins_when_depths_differ():
    a = _analyzer()
    winner = a.select_dependency_blame(
        "t", ["early.bst", "late.bst"],
        task_finish_times={"early.bst": 10000, "late.bst": 20000},
        task_depths={"early.bst": 5, "late.bst": 1},
    )
    assert winner == "late.bst"


def test_greatest_depth_wins_on_finish_time_tie():
    a = _analyzer()
    winner = a.select_dependency_blame(
        "t", ["shallow.bst", "deep.bst"],
        task_finish_times={"shallow.bst": 20000, "deep.bst": 20000},
        task_depths={"shallow.bst": 1, "deep.bst": 3},
    )
    assert winner == "deep.bst"


def test_smallest_task_key_wins_when_finish_and_depth_both_tie():
    a = _analyzer()
    winner = a.select_dependency_blame(
        "t", ["zzz.bst", "aaa.bst", "mmm.bst"],
        task_finish_times={"zzz.bst": 20000, "aaa.bst": 20000, "mmm.bst": 20000},
        task_depths={"zzz.bst": 2, "aaa.bst": 2, "mmm.bst": 2},
    )
    assert winner == "aaa.bst"


def test_out_degree_is_never_used_as_a_tiebreaker():
    """Construct a case where an out-degree-based rule ("more successors
    wins") would pick a different winner than the spec's actual rule
    (smallest key on a full tie) - assert the spec's rule wins.
    `select_dependency_blame`'s signature itself proves this structurally
    (out-degree isn't even a parameter it can see), but this pins the
    observable behavior too.
    """
    a = _analyzer()
    # "zzz_hub.bst" would win under an out-degree rule (more successors,
    # encoded here only in the naming/intent - the function has no way
    # to know or use it); "aaa_leaf.bst" must win on key ordering alone,
    # since it sorts first lexicographically despite "losing" on any
    # hypothetical out-degree comparison.
    winner = a.select_dependency_blame(
        "t", ["zzz_hub.bst", "aaa_leaf.bst"],
        task_finish_times={"zzz_hub.bst": 20000, "aaa_leaf.bst": 20000},
        task_depths={"zzz_hub.bst": 2, "aaa_leaf.bst": 2},
    )
    assert winner == "aaa_leaf.bst"


def test_single_predecessor_is_trivially_selected():
    a = _analyzer()
    winner = a.select_dependency_blame(
        "t", ["only.bst"], task_finish_times={"only.bst": 1000}, task_depths={"only.bst": 1},
    )
    assert winner == "only.bst"


def test_no_predecessors_returns_none():
    a = _analyzer()
    assert a.select_dependency_blame("t", [], {}, {}) is None


# --- Full-pipeline regression: adding an unrelated node must not change
# the tie-break winner (spec explicitly calls this out). ---

def _tied_predecessor_and_winner(tmp_path, topology, name):
    analyzer = topo.build_analyzer(tmp_path, topology, name=name)
    result = analyzer.analyze()
    blame_chain = [str(node.task_key) for node in analyzer._blame_chain]
    # multiple_equal_predecessors: shallow.bst (depth 1) and deep.bst
    # (depth 2) tie in finish time - deep.bst must win per rule 2.
    return blame_chain


def test_unrelated_graph_node_does_not_change_tie_break_winner(tmp_path):
    run_context, graph, trace = topo.multiple_equal_predecessors()
    baseline_chain = _tied_predecessor_and_winner(
        tmp_path, (run_context, graph, trace), name="baseline",
    )
    assert "deep.bst|BUILD|BUILD|0" in baseline_chain
    assert "shallow.bst|BUILD|BUILD|0" not in baseline_chain

    # Add a fully disconnected, unrelated element+task elsewhere in the
    # graph and re-run - the winner must be unchanged.
    graph_with_extra = {
        "elements": graph["elements"] + [{"uid": "unrelated.bst", "cache_key": None, "requested_target": False}],
        "dependencies": graph["dependencies"],
    }
    trace_with_extra = {
        "spans": trace["spans"] + [
            {"task_key": "unrelated.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": 5000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"}
        ],
        "phases": [],
    }
    extended_chain = _tied_predecessor_and_winner(
        tmp_path, (run_context, graph_with_extra, trace_with_extra), name="extended",
    )
    assert "deep.bst|BUILD|BUILD|0" in extended_chain
    assert "shallow.bst|BUILD|BUILD|0" not in extended_chain
