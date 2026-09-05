"""UX-681: fan-in — what an element depends on, ranked.

`blast_radius` answers "what does changing this rebuild"; this is its
mirror. Read against `tests/fixtures/macro_micro`, which is example 06:
11 elements, 34 edges, one root.

**This file corrects its own item's Acceptance Test.** Both halves were
wrong, and the corrections are what the clauses below assert - see the
task file's Outcome for the measurement.
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

    def test_nothing_that_pulls_in_nothing_is_ranked(self, rows):
        """`UX-474`, mirrored: an ordering over zeroes is not a
        ranking."""
        assert "toolchain.bst" not in top_fan_in(rows)

    def test_the_ranking_is_by_closure_descending(self, rows):
        counts = [rows[uid]["transitive_count"] for uid in top_fan_in(rows)]
        assert counts == sorted(counts, reverse=True), counts
        assert top_fan_in(rows)[0] == "app.bst"


class TestTheReadShareSaysWhetherAnybodyLooked:

    def test_no_plane_two_publishes_none_and_not_one(self, rows):
        """"Every edge was read" and "nobody looked" are different
        claims. Without a Plane 2 report the share is `None`; a 1.0
        would say the opposite of what is known."""
        assert rows["lib-f.bst"]["read_share"] is None
        assert rows["lib-f.bst"]["unread_count"] is None

    def test_a_never_read_edge_lowers_the_share(self):
        """`UX-407`'s list, joined. `lib-f` names four dependencies; one
        never read makes the share 0.75."""
        _context, graph, _trace = load_all(FIXTURE)
        kinds = {element.uid: (element.element_kind or "unknown")
                 for element in graph.elements}
        joined = compute_fan_in(graph, kinds, STRUCTURAL_ELEMENT_KINDS,
                                unread={"lib-f.bst": ["codegen.bst"]})
        assert joined["lib-f.bst"]["unread_count"] == 1
        assert joined["lib-f.bst"]["read_share"] == 0.75

    def test_an_unread_name_that_is_not_an_edge_is_not_counted(self):
        """Plane 2 names an element this one does not depend on - a
        stale report, or a name from another run. Counting it would push
        the share below zero on a small element."""
        _context, graph, _trace = load_all(FIXTURE)
        kinds = {element.uid: (element.element_kind or "unknown")
                 for element in graph.elements}
        joined = compute_fan_in(graph, kinds, STRUCTURAL_ELEMENT_KINDS,
                                unread={"codegen.bst": ["lib-f.bst"]})
        assert joined["codegen.bst"]["unread_count"] == 0
        assert joined["codegen.bst"]["read_share"] == 1.0


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
