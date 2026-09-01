"""UX-467: the graph-shape findings, against shapes that offer nothing.

`FINDING_READERS` gives the graph-owner two findings and the
recipe-author four, and before `UX-464` a clone could produce one of
each. So the findings that answer *"what shape is my build, and what
does that tell me to do"* are the least exercised in the tool - which
is precisely the position `UX-120`'s merge candidate was in when it
turned out to have "fired only on synthetic unit-test input. Both real
captures it had ever seen produced the *negative* answer - which is the
correct answer for those projects, and is also exactly what an inert
detector produces."

Nothing distinguished "bga looked and there was nothing" from "bga
cannot see it", because no fixture was deliberately *fine*. This file
is that fixture set: for each structural finding, a shape it should
speak about and a shape it should stay quiet about.

Two things it found on its first run are **not** asserted here, because
`UX-467`'s Out of Scope keeps the fix separate from the detection:
`UX-474` (the blast ranking publishes an ordered list of zeros) and
`UX-475` (`mesh-graph` calls a linear chain a mesh). Each row carries
the pasted evidence and the clause that will close it. This file
asserts what holds today, so it cannot go quietly green over either.
"""
import contextlib
import io
import json

import pytest

from tests.fixtures import topologies as topo

SHAPE_FINDINGS = {"mesh-graph", "chain-graph", "graph-width",
                  "criticality", "blast-radius-ranking",
                  "blast-radius-structural"}


def _payload(tmp_path, topology, name):
    """One fixture's `analyze --format json`, through the shipped path."""
    from bga.cli import main

    run = topo.write_run_dir(tmp_path, topology, name=name)
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), \
            contextlib.redirect_stderr(io.StringIO()):
        main(["analyze", str(run), "--format", "json"])
    return json.loads(buffer.getvalue())


def _by_id(payload):
    return {f["id"]: f for f in payload["findings"]}


@pytest.fixture(scope="module")
def wide(tmp_path_factory):
    """T1: a shared base, six dependents, two longest paths near-tied."""
    return _payload(tmp_path_factory.mktemp("wide"),
                    topo.shared_base_wide(), "wide")


@pytest.fixture(scope="module")
def chain(tmp_path_factory):
    """The flattest graph there is: one path, no contest, no fan."""
    return _payload(tmp_path_factory.mktemp("chain"),
                    topo.linear_chain(n=5), "chain")


@pytest.fixture(scope="module")
def flat(tmp_path_factory):
    """Independent elements, capacity above demand: nothing waits on
    anything, so no shape question has an answer."""
    return _payload(tmp_path_factory.mktemp("flat"),
                    topo.ample_capacity(), "flat")


class TestTheConclusionFollowsFromThePublishedNumbers:
    """Not "did it fire" - whether what it says matches what it shows."""

    def test_criticality_publishes_a_contest_and_its_own_numbers(self, wide):
        """A criticality list is only worth reading if the probabilities
        discriminate. `_criticality_findings` drops a list where every
        entry scores 1.0 for exactly that reason, so where one *is*
        published its numbers must be fractional and ordered."""
        finding = _by_id(wide)["criticality"]
        published = finding["evidence"]["criticality_probability"]
        probabilities = [rec["probability"] for rec in published.values()]

        assert probabilities, published
        assert all(0.0 < p < 1.0 for p in probabilities), probabilities
        assert probabilities == sorted(probabilities, reverse=True)
        assert finding["elements"] == list(published)

    def test_the_structural_finding_names_only_structural_elements(self, wide):
        """`UX-76`/`UX-258`: a base image with a thousand dependents is a
        fact about the graph, not a task. The finding that reports it
        must name only elements that really are structural, and really
        do reach the graph - otherwise it is describing nothing."""
        finding = _by_id(wide)["blast-radius-structural"]
        radius = wide["elements"]["blast_radius"]

        assert finding["elements"]
        for uid in finding["elements"]:
            assert radius[uid]["is_structural_kind"], uid
            assert radius[uid]["downstream_count"] > 0, uid

    def test_the_ranking_shows_the_counts_the_payload_holds(self, wide):
        """Self-consistency, which is the half that holds today. Whether
        a ranking of *zeros* should be published at all is `UX-474`."""
        finding = _by_id(wide)["blast-radius-ranking"]
        radius = wide["elements"]["blast_radius"]

        for uid in finding["elements"]:
            assert uid in radius, uid
            assert f"{radius[uid]['downstream_count']} downstream" in \
                " ".join(finding["detail"])


class TestTheShapeThatOffersNothing:
    """The clauses that turn an inert detector red."""

    def test_a_single_path_produces_no_criticality_ranking(self, chain):
        """Every element of a chain is on the critical path with
        probability 1.0 however the durations are perturbed. A list that
        ranks nothing must not be published, and this is the shape that
        proves the drop rule is live rather than incidental."""
        assert "criticality" not in _by_id(chain)

    def test_a_chain_produces_no_blast_ranking(self, chain):
        """Blast radius answers "who depends on me", which is the right
        question when the *graph* constrains the build and not when the
        chain does (`UX-65`). A chain has real downstream counts and
        still must not be ranked by them.

        The gate is at the **call site** - `compute_findings` branches
        on `chain_bound` and only reaches `_ranking_findings` in the
        `else`. Written first as "`_ranking_findings` returns nothing
        on a chain-bound run", which is what its own first line
        appears to say; mutating that line changed nothing, because it
        is never reached with `chain_bound` true. Recorded in `UX-474`.
        """
        published = _by_id(chain)
        radius = chain["elements"]["blast_radius"]

        assert max(r["downstream_count"] for r in radius.values()) > 0, (
            "the chain has no downstream counts at all, so this clause "
            "would pass for the wrong reason")
        assert "blast-radius-ranking" not in published
        assert "blast-radius-structural" not in published

    def test_a_flat_capacity_ample_run_offers_no_blast_conclusion(self, flat):
        """Independent elements with no shared base: nothing reaches
        anything, so neither blast finding has a subject."""
        radius = flat["elements"]["blast_radius"]

        assert all(r["downstream_count"] == 0 for r in radius.values())
        assert "blast-radius-ranking" not in _by_id(flat)
        assert "blast-radius-structural" not in _by_id(flat)

    def test_the_shape_census_is_the_one_that_was_measured(self, wide, chain, flat):
        """The census this file exists to be, pinned.

        Written first as "no finding fires on all three shapes, except
        `mesh-graph`" - and that was wrong: `mesh-graph` fires on the
        chain **only**. Measured rather than assumed, the map is the one
        below, and every entry in it is a claim:

        - `criticality` speaks about the contested shape and the flat
          one (several independent tasks of similar length really do
          contest the longest path) and is silent on the chain;
        - both blast findings speak only about the shape with a base;
        - `mesh-graph` spoke only about the chain, which is the shape
          least like a mesh there is. That was `UX-475`, and it is
          fixed: the chain gets `chain-graph` and `mesh-graph` fires on
          none of these three. The negative is the point - none of
          these fixtures has two paths of equal length, so a mesh
          finding here would be the inert detector `UX-120` found.
          `TestTheChainAndTheMeshGetDifferentSentences` below carries
          the positive case.

        A change to this map is a change to what the tool says about
        shape, and should be read rather than re-recorded.
        """
        fired = {name: set() for name in SHAPE_FINDINGS}
        for label, payload in (("wide", wide), ("chain", chain), ("flat", flat)):
            for name in SHAPE_FINDINGS & set(_by_id(payload)):
                fired[name].add(label)

        assert fired == {
            "criticality": {"wide", "flat"},
            "blast-radius-ranking": {"wide"},
            "blast-radius-structural": {"wide"},
            "chain-graph": {"chain"},
            "mesh-graph": set(),
            # `UX-478`. The flat set is the negative case, and it is the
            # only one: with every element independent there is one
            # dependency stage, the widest stage is the whole graph and
            # the shape forbids nothing.
            "graph-width": {"wide", "chain"},
        }

    def test_no_shape_finding_speaks_about_every_shape(self, wide, chain, flat):
        """A finding that fires on a chain, a fan and a flat set is
        either about something other than shape or is not
        discriminating. None does - which is the property `UX-120`'s
        inert detector did not have."""
        for name in SHAPE_FINDINGS:
            fired = [label for label, payload
                     in (("wide", wide), ("chain", chain), ("flat", flat))
                     if name in _by_id(payload)]
            assert len(fired) < 3, f"{name} fires on every shape: {fired}"


class TestThePreconditionsTheFiledRowsRestOn:
    """`UX-474` and `UX-475` are rows, not fixes, so their evidence has
    to keep existing or the rows become unreproducible."""

    def test_the_only_element_with_reach_on_t1_is_structural(self, wide):
        """`UX-474`'s precondition: the ranking excludes structural
        elements, and on this shape that leaves only zeros to rank."""
        radius = wide["elements"]["blast_radius"]
        with_reach = [uid for uid, r in radius.items()
                      if r["downstream_count"] > 0]

        assert with_reach == ["toolchain.bst"]
        assert radius["toolchain.bst"]["is_structural_kind"]
        assert all(radius[uid]["downstream_count"] == 0
                   for uid in _by_id(wide)["blast-radius-ranking"]["elements"])

    def test_the_chain_is_not_called_a_mesh(self, chain):
        """`UX-475`, closed. This clause used to pin the defect - the
        finding was `mesh-graph`, its evidence was
        `{"zero_slack_share": 1.0}`, and its title said "mesh" about
        five elements on one path.

        `zero_slack_share` is still 1.0 and still 1.0 **by
        construction**: one path means no element can move. What is
        published beside it now is the count that tells the two shapes
        apart."""
        found = _by_id(chain)
        assert "mesh-graph" not in found, sorted(found)
        finding = found["chain-graph"]

        assert finding["evidence"] == {"zero_slack_share": 1.0,
                                       "zero_slack_off_path": 0}
        assert "mesh" not in finding["title"], finding["title"]
        assert "its own duration" in finding["title"], finding["title"]


@pytest.fixture(scope="module")
def mesh(tmp_path_factory):
    """`UX-475`: four predecessors of equal weight converging on one
    target - four chains, all the same length, none of which can be
    shortened alone. The shape the mesh sentence was written for."""
    return _payload(tmp_path_factory.mktemp("mesh"), topo.fan_in(), "mesh")


@pytest.fixture(scope="module")
def two_paths(tmp_path_factory):
    """The minimum mesh: `a -> {b, c} -> d`, `b` and `c` equal. One of
    the two is off whichever path is reported."""
    return _payload(tmp_path_factory.mktemp("two_paths"),
                    topo.diamond(), "two_paths")


class TestTheChainAndTheMeshGetDifferentSentences:
    """`UX-475`. Zero slack is necessary and not sufficient.

    On a single-path graph `zero_slack_share` is **1.0 by
    construction** - with one path no element has anywhere to move - so
    a mesh detector that reads only the share fires on the least
    mesh-like graph there is, and tells its reader the saving will be
    "capped by the next chain" when there is no next chain and the
    saving is exactly the element's own duration.

    The discriminator is not a second proxy for the same thing. An
    element with zero slack lies on *some* longest path; if it is not
    on the path this run reported, a second path of the same length
    exists, which is what "near-equal chains" means. So the count of
    zero-slack elements off the reported path is the thing itself.

    Measured across the factories, which is what says the split is a
    property of the shape rather than of one fixture:

    ```text
    linear_chain(5)                 share 1.000   off-path 0
    deep_unequal_predecessors       share 0.800   off-path 0
    a_build_that_pulls              share 1.000   off-path 0
    diamond                         share 1.000   off-path 1
    multiple_equal_predecessors     share 1.000   off-path 2
    fan_in / fan_out                share 1.000   off-path 3
    one_source_many_elements        share 1.000   off-path 3
    ```
    """

    def test_the_mesh_is_called_a_mesh(self, mesh):
        found = _by_id(mesh)
        assert "chain-graph" not in found, sorted(found)
        finding = found["mesh-graph"]
        assert "mesh of near-equal chains" in finding["title"]
        assert finding["evidence"]["zero_slack_off_path"] == 3, finding

    def test_two_equal_paths_are_already_a_mesh(self, two_paths):
        """One element off the reported path is one other chain, and the
        capping sentence is true of it. The floor is 1, not a share."""
        found = _by_id(two_paths)
        assert "chain-graph" not in found, sorted(found)
        assert found["mesh-graph"]["evidence"]["zero_slack_off_path"] == 1

    def test_the_two_shapes_agree_on_the_share_and_differ_on_the_count(
            self, mesh, chain):
        """The pair that carries the file. Both graphs report
        `zero_slack_share: 1.0` - the number the old detector read - and
        the tool now says opposite things about them."""
        mesh_finding = _by_id(mesh)["mesh-graph"]
        chain_finding = _by_id(chain)["chain-graph"]

        assert (mesh_finding["evidence"]["zero_slack_share"]
                == chain_finding["evidence"]["zero_slack_share"] == 1.0)
        assert mesh_finding["evidence"]["zero_slack_off_path"] > 0
        assert chain_finding["evidence"]["zero_slack_off_path"] == 0
        assert "capped by the next chain" in mesh_finding["title"]
        assert "its own duration" in chain_finding["title"]

    def test_both_go_to_the_graph_owner(self, mesh, chain):
        """`UX-478` is the row about that reader being absent; this
        keeps the split from costing it the one finding it had."""
        for payload, name in ((mesh, "mesh-graph"), (chain, "chain-graph")):
            reader = next((r for r in payload["readers"]
                           if r["id"] == "graph-owner"), None)
            assert reader is not None, [r["id"] for r in payload["readers"]]
            assert name in reader["findings"], reader


class TestTheGraphOwnerHasAFindingThatReadsNoDuration:
    """`UX-478`. R3's question is *"What does the shape of this graph
    make impossible?"*, and until this item every finding that reached
    that reader was a function of measured durations - `criticality`
    needs a contested path, `mesh-graph`/`chain-graph` read the slack
    the durations produce. So on `UX-468`'s six-element serial chain,
    the one project whose entire defect *is* the graph, the reader
    index dropped R3:

    ```text
    ['local-optimizer', 'recipe-author', 'ci-gatekeeper', 'capacity-operator']
    ```

    and the same graph with the per-element seconds tripled brought it
    back. A reader whose presence turns on how long the build took is
    not a reader about shape.

    `graph-width` reads `elements.unweighted_depth` and nothing else.
    """

    def test_the_same_graph_at_two_speeds_says_the_same_thing(
            self, tmp_path_factory):
        """The clause that carries the file. One graph, durations an
        order of magnitude apart - which is the pair that made `UX-478`
        reproducible - and the shape claim is identical.

        The diagnosis and the concentration table move; this does not.
        """
        seen = {}
        for label, us in (("slow", 30_000_000), ("fast", 1_000_000)):
            payload = _payload(tmp_path_factory.mktemp(f"speed_{label}"),
                               topo.linear_chain(n=5, duration_us=us),
                               f"speed_{label}")
            found = _by_id(payload)
            assert "graph-width" in found, sorted(found)
            seen[label] = found["graph-width"]["evidence"]
        assert seen["slow"] == seen["fast"] == {
            "element_count": 5, "dependency_stages": 5, "widest_stage": 1}, seen

    def test_it_names_the_ceiling_no_capacity_lifts(self, chain):
        finding = _by_id(chain)["graph-width"]
        assert "5 dependency stages" in finding["title"], finding["title"]
        assert "no more than 1" in finding["title"], finding["title"]
        assert finding["reader"] == "graph-owner", finding

    def test_the_flat_set_is_told_nothing(self, flat):
        """The negative case `UX-478` asked for. Every element
        independent: one stage, the widest stage is the whole graph, and
        a finding here would be describing the *absence* of a
        constraint as if it were one."""
        assert "graph-width" not in _by_id(flat), sorted(_by_id(flat))

    def test_the_wide_graph_names_its_own_ceiling(self, wide):
        """Not just "it fires on more than one shape": the number has to
        be this graph's, or the finding is a constant with a sentence
        around it."""
        finding = _by_id(wide)["graph-width"]
        assert finding["evidence"] == {
            "element_count": 7, "dependency_stages": 2, "widest_stage": 6}

    def test_the_graph_owner_is_offered_on_every_shape_that_has_one(
            self, wide, chain, flat, mesh):
        """The defect as the reader saw it. R3 is now offered on all
        four - three by `graph-width`, the flat set by `criticality`,
        which is the shape where a ceiling would be a lie."""
        for label, payload in (("wide", wide), ("chain", chain),
                               ("flat", flat), ("mesh", mesh)):
            ids = [r["id"] for r in payload["readers"]]
            assert "graph-owner" in ids, (label, ids)

    def test_the_stages_are_the_graph_and_not_the_measured_path(
            self, tmp_path_factory):
        """The clause a mutation asked for. Reading the critical path's
        length instead of the graph's depth passed every clause above,
        because on every other committed shape the two numbers are
        equal - the deepest chain is also the heaviest.

        `deep_unequal_predecessors(shallow_us=...)` separates them by
        construction: the graph is four stages deep and the critical
        path is two elements, because the shallow predecessor was made
        heavy enough to carry it.
        """
        payload = _payload(tmp_path_factory.mktemp("deep"),
                           topo.deep_unequal_predecessors(shallow_us=90_000),
                           "deep")
        path = [row["element_uid"] for row
                in _by_id(payload)["time-concentration"]["evidence"]["rows"]]
        assert path[:2] == ["shallow.bst", "target.bst"], path
        evidence = _by_id(payload)["graph-width"]["evidence"]
        assert evidence["dependency_stages"] == 4, evidence
        assert evidence["element_count"] == 5, evidence
