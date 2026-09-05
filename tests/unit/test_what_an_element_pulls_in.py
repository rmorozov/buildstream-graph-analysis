"""UX-681: fan-in — what an element depends on, ranked.

`blast_radius` answers "what does changing this rebuild"; this is its
mirror. Read against `tests/fixtures/macro_micro`, which is example 06:
11 elements, 34 edges, one root.

**This file corrects its own item's Acceptance Test**, both halves,
and moves one of its Required Fix's columns. The corrections are what
the clauses below assert - see the task file's Outcome.
"""
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga.graph.edg import compute_reachability
from bga.graph.fan_in import compute_fan_in, immediate_dominator, top_fan_in
from bga.ingest.loader import load_all
from bga.ingest.models import STRUCTURAL_ELEMENT_KINDS

FIXTURE = REPO / "tests" / "fixtures" / "macro_micro" / "run"
PLANE2 = REPO / "tests" / "fixtures" / "macro_micro" / "plane2.json"


def _finding(finding_id: str) -> dict:
    """One published finding, from the list both renderers consume."""
    from bga.analyzer import BuildEfficiencyAnalyzer
    from bga.findings import compute_findings

    result = BuildEfficiencyAnalyzer().analyze(FIXTURE)
    return next(item for item in compute_findings(result)
                if item["id"] == finding_id)


def _join_row(uid: str) -> dict:
    """One `element_join` row, from the document the page reads."""
    import json

    from bga.analyzer import BuildEfficiencyAnalyzer
    from bga.report.json import build_document

    result = BuildEfficiencyAnalyzer().analyze(FIXTURE)
    result.plane2_report = json.loads(PLANE2.read_text(encoding="utf-8"))
    document = build_document(result)
    return next(row for row in document["element_join"]
                if row["element"] == uid)


@pytest.fixture(scope="module")
def rows():
    _context, graph, _trace = load_all(FIXTURE)
    kinds = {element.uid: (element.element_kind or "unknown")
             for element in graph.elements}
    return compute_fan_in(graph, kinds, STRUCTURAL_ELEMENT_KINDS)


class TestTheClosureIsNotTheEdgeList:

    def test_the_widest_gap_between_direct_and_transitive(self, rows):
        """`all.bst` names one dependency and pulls in ten - the case
        that tells a closure from an edge count.

        The item's own Acceptance Test named `lib-f` and `codegen`
        instead, and `codegen` is a **direct** dependency of `lib-f`: it
        is in the transitive set for free, so the clause could not fail
        under the mutation the item wrote for it.
        """
        assert rows["all.bst"]["direct_count"] == 1
        assert rows["all.bst"]["transitive_count"] == 10

    def test_a_transitive_only_upstream_is_named(self, rows):
        """The discriminating pair the fixture does offer: `lib-a` is in
        `lib-f`'s closure and not among its edges."""
        _context, graph, _trace = load_all(FIXTURE)
        direct = {edge.predecessor for edge in graph.dependencies
                  if edge.successor == "lib-f.bst"}
        assert "lib-a.bst" not in direct
        assert rows["lib-f.bst"]["direct_count"] == 4
        assert rows["lib-f.bst"]["transitive_count"] == 8

    def test_an_element_is_not_something_it_pulls_in(self, rows):
        """The count is `compute_reachability`'s set unmodified, so what
        holds it is that helper's own contract: no element's upstream
        closure contains itself.

        The first draft subtracted `{uid}` here and called that the
        guarantee. The subtraction was a no-op - the helper never
        includes self - so the clause passed whatever the helper did,
        which is a guard over a second rule that cannot be wrong.
        """
        _context, graph, _trace = load_all(FIXTURE)
        _downstream, upstream = compute_reachability(graph)
        assert [uid for uid in upstream if uid in upstream[uid]] == []
        assert rows["toolchain.bst"]["transitive_count"] == 0
        assert rows["toolchain.bst"]["direct_count"] == 0


class TestTheGateIsTheDominatorAndNotTheDependency:

    def test_the_gate_of_app_is_the_root_and_not_core(self, rows):
        """The item's Acceptance Test says "the dominator of app.bst is
        core.bst". It is not, and the graph says why: `app.bst` depends
        on `toolchain.bst` **directly**, so the path toolchain -> app
        never passes through `core.bst`. `core.bst` is a dependency of
        `app.bst`; a dominator is a different claim.
        """
        assert rows["app.bst"]["immediate_dominator"] == "toolchain.bst"
        _context, graph, _trace = load_all(FIXTURE)
        assert "core.bst" in {edge.predecessor for edge in graph.dependencies
                              if edge.successor == "app.bst"}

    def test_a_root_has_no_gate(self, rows):
        """`None`, not itself: an element does not wait on itself, and
        publishing its own name would make the column unreadable at the
        one place a reader looks for the top of the graph."""
        assert rows["toolchain.bst"]["immediate_dominator"] is None

    def test_the_gate_is_trivial_on_this_graph_and_that_is_recorded(
            self, rows):
        """Every element here gates on `toolchain.bst`, because it is
        the only root. Asserted rather than glossed: the column is
        correct and says almost nothing on a single-root graph, and a
        reader of this fixture should not conclude otherwise from a
        clause that only checked one element.
        """
        gates = {row["immediate_dominator"] for uid, row in rows.items()
                 if row["immediate_dominator"] is not None}
        assert gates == {"toolchain.bst", "app.bst"}, gates


class TestTheRankingKeepsTheBlastRules:

    def test_the_largest_fan_in_is_excluded_for_being_structural(
            self, rows):
        """`UX-76`, mirrored. `all.bst` has the widest closure in the
        graph and is a `stack`: a stack depends on everything *on
        purpose*, and "it pulls in ten things" is a fact about the graph
        rather than a task. Excluded from the ranking, never from the
        rows."""
        assert rows["all.bst"]["is_structural_kind"] is True
        assert rows["all.bst"]["transitive_count"] == max(
            row["transitive_count"] for row in rows.values())
        assert "all.bst" not in top_fan_in(rows)
        assert "all.bst" in rows

    def test_nothing_that_pulls_in_nothing_is_ranked(self):
        """`UX-474`, mirrored: an ordering over zeroes is not a
        ranking.

        On this fixture the rule is unfalsifiable, and the first draft
        of this clause asserted it there anyway: `toolchain.bst` is the
        only element with a zero closure and it sorts eleventh of
        eleven, so dropping the rule entirely left it out of the top
        five and the clause still passed. A graph of leaves is where
        the rule is the only thing keeping the ranking empty.
        """
        leaves = {f"m{index}.bst": {
            "direct_count": 0, "transitive_count": 0,
            "immediate_dominator": None, "element_kind": "manual",
            "is_structural_kind": False} for index in range(6)}
        assert top_fan_in(leaves) == []

    def test_the_ranking_is_by_closure_descending(self, rows):
        counts = [rows[uid]["transitive_count"] for uid in top_fan_in(rows)]
        assert counts == sorted(counts, reverse=True), counts
        assert top_fan_in(rows)[0] == "app.bst"


class TestTheReadShareIsOnTheJoinRowAndNotHere:
    """The item asks for "the share of those edges Plane 2 saw read" as
    a fan-in column. `ELEMENT_PLACEMENT_RULE` says otherwise, and the
    rule wins: `elements.fan_in` is a map every capture carries, and a
    Plane 2 column in it is null on every single-plane run. It is
    `element_join.dependency_read_share` instead.
    """

    def test_the_map_carries_no_plane_two_column(self, rows):
        assert set(rows["lib-f.bst"]) == {
            "direct_count", "transitive_count", "immediate_dominator",
            "element_kind", "is_structural_kind"}

    def test_the_share_is_of_what_plane_two_could_assess(self):
        """Not of the declared edge count. `app.bst` names eight
        dependencies and Plane 2 assessed eight, seven of them never
        opened - so 0.125. A dependency Plane 2 saw nothing of at all
        is uncovered and in neither list, and dividing by the edge
        count would have scored that gap as a finding."""
        row = _join_row("app.bst")
        assert row["assessed_dependencies"] == 8
        assert row["dependency_read_share"] == 0.125
        assert len(row["unused_dependencies"]) == 7

    def test_an_element_no_plane_two_row_names_has_no_share(self):
        """`toolchain.bst` is a root: it stages nothing from anything,
        so no `declared_vs_used` row names it and the field is absent.
        A 1.0 would say every edge was read, of an element with no
        edges."""
        row = _join_row("toolchain.bst")
        assert row.get("dependency_read_share") is None
        assert row.get("assessed_dependencies") is None

    def test_an_element_plane_two_measured_but_never_assessed_has_none(self):
        """The reachable case the fixture cannot produce, so the first
        draft's clause above did not reach it either: an element Plane 2
        **did** measure - it has CPU - whose every dependency was
        uncovered, so it is in the view with no `assessed` count. The
        branch is what keeps that a `None` rather than a division by
        zero or a 1.0; asserted here because `toolchain.bst` is absent
        from the view entirely and settles a different question.
        """
        from bga.correlate import _plane2_view

        view = _plane2_view({
            "cpu_time": {"per_element": {"lone.bst": {"cpu_us": 5}}},
            "declared_vs_used": {"used": [], "unused_candidates": []}})
        assert "lone.bst" in view
        assert view["lone.bst"].get("dependency_read_share") is None
        assert view["lone.bst"].get("assessed_dependencies") is None


class TestTheFindingFamilyMirrorsTheBlastOne:
    """Two members, not four - see `_fan_in_findings`' own docstring for
    why `fan-in-reach` and `fan-in-unread` would each restate something
    the report already says."""

    def test_the_ranking_carries_the_scale_and_the_right_verb(self):
        """`UX-259`'s rule, and the direction. The same decile sentence
        serves both families, and "reach 5 or fewer" is the wrong claim
        about a fan-in - these elements do not reach five, they are
        built on five."""
        finding = _finding("fan-in-ranking")
        assert finding["elements"][0] == "app.bst"
        assert "9 upstream, 8 named directly" in finding["detail"][0]
        assert "at or above p90 of this run" in finding["detail"][0]
        shape = finding["detail"][-1]
        assert "pull in 5 or fewer" in shape, shape
        assert "reach" not in shape, shape

    def test_the_widest_fan_in_is_named_as_shape_and_not_ranked(self):
        """`UX-76` again. `all.bst` pulls in ten of eleven elements and
        is the one row the ranking must not open with."""
        assert _finding("fan-in-structural")["elements"] == ["all.bst"]
        assert "all.bst" not in _finding("fan-in-ranking")["elements"]

    def test_each_member_names_its_reader(self):
        """`UX-372`: the ranking is the graph owner's "which fan-in is
        suspicious"; the stack is the recipe author's "and that one is
        not"."""
        assert _finding("fan-in-ranking")["reader"] == "graph-owner"
        assert _finding("fan-in-structural")["reader"] == "recipe-author"


class TestTheDominatorHelperOnItsOwn:
    """The cases the fixture's single root cannot produce."""

    def test_the_nearest_of_several_is_the_one_published(self):
        """`b` is dominated by `a`; `c` by both. The gate a developer
        waits on is `b`, the closest - `a` is true and further away."""
        dominators = {"a": {"a"}, "b": {"a", "b"}, "c": {"a", "b", "c"}}
        assert immediate_dominator(dominators, "c") == "b"
        assert immediate_dominator(dominators, "b") == "a"
        assert immediate_dominator(dominators, "a") is None


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
