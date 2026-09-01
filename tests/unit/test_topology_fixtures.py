"""Acceptance test for P3-01 (shared synthetic topology fixture library).

Smoke-tests every factory in tests/fixtures/topologies.py: build it,
run a full analysis, confirm no exception. This is deliberately not
asserting on computed values - value assertions belong to the tasks
that actually consume these fixtures (P3-03 through P3-09, and various
P1-*/P2-* acceptance tests), per P3-01's own Out of Scope note.
"""
import pytest

from tests.fixtures import topologies as topo


FACTORIES = [
    ("linear_chain", lambda: topo.linear_chain()),
    ("linear_chain_n5", lambda: topo.linear_chain(n=5)),
    ("diamond", lambda: topo.diamond()),
    ("fan_in", lambda: topo.fan_in()),
    ("fan_out", lambda: topo.fan_out()),
    ("multiple_equal_predecessors", lambda: topo.multiple_equal_predecessors()),
    ("deep_unequal_predecessors", lambda: topo.deep_unequal_predecessors()),
    ("independent_branches", lambda: topo.independent_branches()),
    ("graph_with_terminal_and_nonterminal_tasks", lambda: topo.graph_with_terminal_and_nonterminal_tasks()),
    # UX-464's covering set.
    ("shared_base_wide", lambda: topo.shared_base_wide()),
    ("ample_capacity", lambda: topo.ample_capacity()),
    ("one_source_many_elements", lambda: topo.one_source_many_elements()[0]),
    ("same_build_twice_cold", lambda: topo.the_same_build_twice()[0]),
    ("same_build_twice_incremental", lambda: topo.the_same_build_twice()[1]),
]


@pytest.mark.parametrize("name,factory", FACTORIES, ids=[n for n, _ in FACTORIES])
def test_factory_produces_analyzable_input(tmp_path, name, factory):
    topology = factory()
    analyzer = topo.build_analyzer(tmp_path, topology, name=name)
    result = analyzer.analyze()

    assert result.floors is not None
    assert result.attribution is not None
    assert result.signals is not None


def test_duration_override_is_applied(tmp_path):
    run_context, graph, trace = topo.linear_chain(n=2, duration_us=10000, durations={"elem1.bst": 5000})
    spans_by_uid = {s["task_key"].split("|")[0]: s for s in trace["spans"]}
    assert spans_by_uid["elem0.bst"]["dur_us"] == 10000
    assert spans_by_uid["elem1.bst"]["dur_us"] == 5000


def test_multiple_equal_predecessors_are_a_genuine_tie():
    _, _, trace = topo.multiple_equal_predecessors()
    finishes = {}
    for span in trace["spans"]:
        uid = span["task_key"].split("|")[0]
        finishes[uid] = span["ts_us"] + span["dur_us"]
    assert finishes["shallow.bst"] == finishes["deep.bst"]


def test_deep_unequal_predecessors_are_not_a_tie():
    _, _, trace = topo.deep_unequal_predecessors()
    finishes = {}
    for span in trace["spans"]:
        uid = span["task_key"].split("|")[0]
        finishes[uid] = span["ts_us"] + span["dur_us"]
    assert finishes["shallow.bst"] != finishes["deep2.bst"]


def test_graph_with_terminal_and_nonterminal_tasks_marks_requested_target():
    _, graph, _ = topo.graph_with_terminal_and_nonterminal_tasks()
    requested = {e["uid"] for e in graph["elements"] if e["requested_target"]}
    assert requested == {"target.bst"}


def test_independent_branches_share_no_dependencies():
    _, graph, _ = topo.independent_branches(n=3)
    prefixes = {dep["predecessor"].split("_")[0] for dep in graph["dependencies"]}
    prefixes |= {dep["successor"].split("_")[0] for dep in graph["dependencies"]}
    # Every dependency edge must stay within a single branch prefix.
    for dep in graph["dependencies"]:
        assert dep["predecessor"].split("_")[0] == dep["successor"].split("_")[0]


# --- UX-464: each covering-set factory has the property its finding
# --- keys on. Not the finding itself - that is the census's answer and
# --- `UX-460`'s guard - but the shape, so a factory that stops being
# --- what its name says fails here rather than silently reducing the
# --- census by one.

def test_shared_base_wide_has_a_structural_base_and_a_near_tie():
    """Both properties `blast-radius-structural` and `criticality`
    stand on: the base is an `import`, and the two heaviest dependents
    are inside the sampler's perturbation of each other."""
    _rc, graph, trace = topo.shared_base_wide(tie_ratio=0.97)

    kinds = {e["uid"]: e.get("element_kind") for e in graph["elements"]}
    assert kinds["toolchain.bst"] == "import"
    assert {k for u, k in kinds.items() if u != "toolchain.bst"} == {"manual"}

    durations = sorted((s["dur_us"] for s in trace["spans"]
                        if not s["task_key"].startswith("toolchain")),
                       reverse=True)
    assert durations[1] / durations[0] == pytest.approx(0.97, abs=0.01)


def test_shared_base_wide_is_not_chain_bound():
    """`_ranking_findings` returns nothing on a chain-bound run, so a
    fixture whose wall-clock is its critical path reaches no blast
    finding however wide its fan is."""
    run_context, _graph, trace = topo.shared_base_wide()
    wall = run_context["wall_clock"]["end_us"]
    by_uid = {}
    for span in trace["spans"]:
        uid = span["task_key"].split("|")[0]
        by_uid[uid] = span["dur_us"]
    longest_path = by_uid["toolchain.bst"] + max(
        d for u, d in by_uid.items() if u != "toolchain.bst")

    assert longest_path / wall < 0.9, (
        f"critical path is {longest_path / wall:.0%} of wall-clock; at 90% "
        f"or more the run is chain-bound and the blast findings vanish")


def test_one_source_many_elements_puts_every_element_on_one_resource():
    _topology, inventory = topo.one_source_many_elements(elements=4)
    identities = {resource["identity"]
                  for resources in inventory["elements"].values()
                  for resource in resources}

    assert len(inventory["elements"]) == 4
    assert len(identities) == 1, identities


def test_ample_capacity_declares_more_capacity_than_it_uses():
    """The gate is that no wait category exists, which needs capacity
    strictly above the number of concurrent elements."""
    run_context, graph, _trace = topo.ample_capacity(elements=8, capacity=16)

    assert run_context["resource_capacities"]["PROCESS"] == 16
    assert len(graph["elements"]) == 8
    assert not graph["dependencies"], (
        "an edge would make an element wait, which is the category this "
        "fixture exists to have none of")


def test_the_same_build_twice_differs_only_in_the_skipped_count_and_the_spans():
    """One graph, two runs. If the graphs diverged the pair would be
    two builds rather than the same build twice, and a comparison over
    them would be measuring the wrong thing."""
    (cold_rc, cold_graph, cold_trace), (inc_rc, inc_graph, inc_trace) = \
        topo.the_same_build_twice(chain=4)

    assert cold_graph == inc_graph
    assert cold_rc["queue_summary"]["build"]["skipped"] == 0
    assert inc_rc["queue_summary"]["build"]["skipped"] == 3
    assert len(cold_trace["spans"]) == 4
    assert len(inc_trace["spans"]) == 1


def test_the_covering_set_writes_the_same_bytes_twice(tmp_path):
    """The captures are committed, so a regeneration that moved a byte
    would put a diff in front of a round that changed nothing."""
    first = {p.name: p.read_bytes()
             for run in topo.write_covering_set(tmp_path / "a")
             for p in sorted(run.iterdir())}
    second = {p.name: p.read_bytes()
              for run in topo.write_covering_set(tmp_path / "b")
              for p in sorted(run.iterdir())}

    assert first == second
    assert set(topo.covering_set()) == {
        "shared_base_wide", "ample_capacity", "one_source_many_elements",
        "same_build_twice_cold", "same_build_twice_incremental",
        "a_build_that_pulls",
        # `UX-474`. Added because stopping the blast ranking from
        # ordering zeros left it produced by nothing: the covering set
        # had no shape where a ranking by reach carries information.
        "a_chain_beside_a_crowd"}


def test_only_the_source_fixture_writes_an_inventory(tmp_path):
    """`sources.json` is optional and one factory has it. A second
    `sources.json` appearing means a factory grew a fourth file without
    saying so, and `shared-source-blast` would then be reachable from a
    fixture that is not about sources."""
    written = {run.parent.name: {p.name for p in run.iterdir()}
               for run in topo.write_covering_set(tmp_path)}
    with_sources = {name for name, files in written.items()
                    if "sources.json" in files}

    assert with_sources == {"one_source_many_elements"}, written
