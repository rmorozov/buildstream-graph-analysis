"""UX-479: reach is published whichever way the build is bound.

One `chain_bound` gate used to sit in front of every claim
`_ranking_findings` makes, and `compute_findings` branched on the same
value and called it only in the `else`. So a build whose critical path
was its whole duration published **no** blast-radius finding for any
element someone owns - and a build gated by one fat shared base is
exactly the shape that comes out chain-bound.

`UX-468`'s planted project is the case that found it. Its whole defect
is `base.bst`, a build dependency of six apps costing 21.0s of a 22.0s
critical path, and the recipe-author - whose published question is
*"Is my element a problem, and what does changing it cost?"* - was
shown `latent-heavies`, which is about three *other* elements and says
they are worth nothing to fix.

The pair of clauses that carries this file is
`test_the_chain_bound_run_names_the_base` and
`test_the_same_graph_below_capacity_ranks_instead`: one graph, two lane
counts, and the finding that fires switches. A single-shape guard could
not tell "reach is published on a chain" from "reach is published
always", and the ranking `UX-65` argued for is still gated.
"""
import contextlib
import io
import json

import pytest

from tests.fixtures import topologies as topo

DEPENDENTS = 6


def _payload(tmp_path, topology, name):
    """One topology's `analyze --diagnostics`, through the shipped CLI."""
    from bga.cli import main

    run = topo.write_run_dir(tmp_path, topology, name=name)
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), \
            contextlib.redirect_stderr(io.StringIO()):
        main(["analyze", str(run), "--format", "json", "--diagnostics"])
    return json.loads(buffer.getvalue())


def _by_id(payload):
    return {f["id"]: f for f in payload["findings"]}


def _reader(payload, reader_id):
    return next(r for r in payload["readers"] if r["id"] == reader_id)


@pytest.fixture(scope="module")
def at_capacity(tmp_path_factory):
    """`UX-468`'s shape: one fat base six elements depend on, and lanes
    enough for all six, so nothing queues and the chain is the run.

    `base_kind` is *not* `import` - the planted project's base is a
    `compose` someone wrote and edits, so `UX-258`'s structural rule
    does not apply to it and it is an element with an owner.
    """
    return _payload(tmp_path_factory.mktemp("at_capacity"),
                    topo.shared_base_wide(dependents=DEPENDENTS,
                                          lanes=DEPENDENTS,
                                          base_kind="manual"),
                    "at_capacity")


@pytest.fixture(scope="module")
def below_capacity(tmp_path_factory):
    """The same graph, two lanes: four of the six dependents wait for a
    lane rather than for the base, so the scheduler binds the run."""
    return _payload(tmp_path_factory.mktemp("below_capacity"),
                    topo.shared_base_wide(dependents=DEPENDENTS,
                                          lanes=2,
                                          base_kind="manual"),
                    "below_capacity")


class TestTheFixturesAreTheTwoShapesTheyClaim:
    """`CLAUDE.md`'s standing trap: a guard whose setup another gate
    already excludes passes whatever the gate under test does. Both
    clauses below turn on the diagnosis, so the diagnosis is asserted
    first and separately - if a later round retunes `CHAIN_BOUND_RATIO`
    or the denominator (`UX-477` moved it once already) these reddens
    instead of the file going quietly green.
    """

    def test_at_capacity_is_chain_bound(self, at_capacity):
        assert at_capacity["headline"]["diagnosis"] == "chain_bound", (
            at_capacity["headline"])

    def test_below_capacity_is_scheduler_bound(self, below_capacity):
        assert below_capacity["headline"]["diagnosis"] == "scheduler_bound", (
            below_capacity["headline"])

    def test_both_graphs_carry_one_element_with_six_dependents(
            self, at_capacity, below_capacity):
        """Same graph, different lane count - so any difference in the
        findings below is the diagnosis and not the shape."""
        for payload in (at_capacity, below_capacity):
            radius = payload["elements"]["blast_radius"]
            reaching = {uid: entry["downstream_count"]
                        for uid, entry in radius.items()
                        if entry.get("downstream_count")}
            assert reaching == {"toolchain.bst": DEPENDENTS}, reaching


class TestTheChainBoundRunPublishesTheReach:

    def test_the_chain_bound_run_names_the_base(self, at_capacity):
        """The clause `UX-479` says reddens today. It did:
        `['execution-bound', 'time-concentration',
        'blast-radius-structural', 'joint-saving', ...]` - no finding
        about any element with a dependent."""
        found = _by_id(at_capacity)
        assert "blast-radius-reach" in found, sorted(found)
        finding = found["blast-radius-reach"]
        assert finding["elements"] == ["toolchain.bst"], finding["elements"]
        assert "toolchain.bst" in finding["title"]
        assert f"{DEPENDENTS} downstream" in finding["title"], finding["title"]

    def test_the_recipe_author_leads_with_it(self, at_capacity):
        """Not "the payload contains it" - `UX-372`'s rule is that a
        finding nothing surfaces is not published. Before this the
        reader led with `latent-heavies`."""
        reader = _reader(at_capacity, "recipe-author")
        assert reader["leads_with"] == "blast-radius-reach", reader

    def test_the_reach_names_no_element_with_nothing_downstream(
            self, at_capacity):
        """`UX-474`'s defect - an ordered list every row of which reads
        "0 downstream elements" - is one this finding is born without,
        because it selects on the count rather than truncating a
        pre-sorted list. Asserted rather than assumed."""
        radius = at_capacity["elements"]["blast_radius"]
        named = _by_id(at_capacity)["blast-radius-reach"]["elements"]
        assert named, named
        for uid in named:
            assert radius[uid]["downstream_count"] > 0, (uid, radius[uid])

    def test_the_ranking_stays_gated_on_the_chain(self, at_capacity):
        """`UX-65` argued the gate this file removes from two of three
        claims: *which element to shorten first* is the graph's
        question. On a chain `time-concentration` already orders the
        same names, which is `UX-76`'s one-table rule."""
        found = _by_id(at_capacity)
        assert "blast-radius-ranking" not in found, sorted(found)
        assert "time-concentration" in found, sorted(found)


class TestTheSameGraphBelowCapacity:

    def test_the_same_graph_below_capacity_ranks_instead(self,
                                                         below_capacity):
        """The other half of the pair. Same elements, same dependencies,
        same durations; only `max_jobs` moved."""
        found = _by_id(below_capacity)
        assert "blast-radius-ranking" in found, sorted(found)
        assert "blast-radius-reach" not in found, sorted(found)

    def test_the_structural_report_does_not_turn_on_the_diagnosis(
            self, tmp_path_factory):
        """The third claim `UX-479` ungated. *"These reach most of the
        graph by design"* is a fact about the graph's shape; which way
        this particular run was bound has nothing to do with it, and
        gating it on that was never argued for anywhere.

        Built here with `base_kind="import"` - the covering set's own
        default - at both lane counts, because the two fixtures above
        deliberately have no structural element at all.
        """
        seen = {}
        for label, lanes in (("chain", DEPENDENTS), ("sched", 2)):
            payload = _payload(tmp_path_factory.mktemp(f"struct_{label}"),
                               topo.shared_base_wide(dependents=DEPENDENTS,
                                                     lanes=lanes),
                               f"struct_{label}")
            found = _by_id(payload)
            seen[payload["headline"]["diagnosis"]] = (
                "blast-radius-structural" in found)
        assert seen == {"chain_bound": True, "scheduler_bound": True}, seen

    def test_the_structural_base_is_never_the_reach(self, tmp_path_factory):
        """`UX-258`'s split has to survive on the arm this row opened:
        an `import` with six dependents is reported, never named as the
        thing to change. The one element with a dependent here is
        structural, so `blast-radius-reach` has nothing to say.
        """
        payload = _payload(tmp_path_factory.mktemp("struct_only"),
                           topo.shared_base_wide(dependents=DEPENDENTS,
                                                 lanes=DEPENDENTS),
                           "struct_only")
        assert payload["headline"]["diagnosis"] == "chain_bound", (
            payload["headline"])
        found = _by_id(payload)
        assert "blast-radius-reach" not in found, sorted(found)
        assert found["blast-radius-structural"]["elements"] == [
            "toolchain.bst"]
