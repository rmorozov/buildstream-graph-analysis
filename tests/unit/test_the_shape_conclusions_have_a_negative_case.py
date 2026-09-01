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

SHAPE_FINDINGS = {"mesh-graph", "criticality",
                  "blast-radius-ranking", "blast-radius-structural"}


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
        - `mesh-graph` speaks only about the chain, which is the shape
          least like a mesh there is. That is `UX-475`.

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
            "mesh-graph": {"chain"},
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

    def test_mesh_graph_reads_a_zero_slack_share(self, chain):
        """`UX-475`'s precondition: the finding's evidence is
        `zero_slack_share`, and on a single path that is 1.0 by
        construction - one path means no element can move."""
        finding = _by_id(chain)["mesh-graph"]

        assert finding["evidence"] == {"zero_slack_share": 1.0}
        assert "mesh" in finding["title"]
