"""UX-439: when the blast-radius key ties, the order is still total.

Two elements with the same downstream *set* have the same
`downstream_count` and the same `downstream_weighted_duration_us` by
construction. `examples/06` has exactly that pair - every `lib-*.bst`
declares a build dependency on both `core.bst` and `codegen.bst` - so
the tie is permanent rather than unlucky, and before this the winner
fell to whatever `sort` did with equal keys.

That is not stable across machines. CI ranked `codegen.bst` first where
this tree ranked `core.bst`, and the two published rankings disagreed
about the same pair inside one `analyze.json`.

**These clauses tie on purpose.** The journey test asserts `core.bst`
against a real build and so passes or fails on the coin; this one
builds the tie directly, which is what makes it able to fail for the
right reason.
"""
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga.diagnostics.analyzer import BlastRadiusResult, order_blast_radius


def ranked(results, durations):
    """**The production ordering itself**, not a restatement of it.

    Written the other way first - a local copy of the key, linked to the
    module only by a source grep - and two of the four mutations passed
    against it: removing the uid key left `x.element_uid` in the
    duration lookup, so the grep still found it, and un-totalling the
    fallback branch was invisible for the same reason. A guard that
    reimplements what it guards tests its own copy.
    """
    ordered = list(results)
    order_blast_radius(ordered, durations)
    return [r.element_uid for r in ordered]


def tied_pair(first_on_path=True, second_on_path=False):
    """`core.bst` and `codegen.bst`, tied on every published key."""
    return [
        BlastRadiusResult("core.bst", 8, 15_500_000, False, first_on_path, True),
        BlastRadiusResult("codegen.bst", 8, 15_500_000, False, second_on_path, True),
    ]


class TestATieIsBrokenByWhatTheBuildWaitsFor:
    def test_the_critical_path_element_ranks_first(self):
        order = ranked(tied_pair(), {"core.bst": 10_000_000,
                                     "codegen.bst": 3_000_000})
        assert order[0] == "core.bst", (
            f"tied on count and weighted duration, and the element the "
            f"build waits for did not rank first: {order}")

    def test_the_input_order_does_not_decide_it(self):
        """The defect, reproduced: reversing the input must not reverse
        the answer. Stable-sort-on-a-tie is exactly what did."""
        durations = {"core.bst": 10_000_000, "codegen.bst": 3_000_000}
        forward = ranked(tied_pair(), durations)
        backward = ranked(list(reversed(tied_pair())), durations)
        assert forward == backward, (
            f"the order depends on the input order: {forward} vs {backward}")

    def test_the_uid_is_the_last_word(self):
        """Two elements alike in everything still have one order."""
        pair = [
            BlastRadiusResult("b.bst", 4, 1_000, False, True, True),
            BlastRadiusResult("a.bst", 4, 1_000, False, True, True),
        ]
        durations = {"a.bst": 500, "b.bst": 500}
        assert ranked(pair, durations) == ["a.bst", "b.bst"]
        assert ranked(list(reversed(pair)), durations) == ["a.bst", "b.bst"]

    @pytest.mark.parametrize("weighted", [15_500_000, 0])
    def test_both_branches_are_total(self, weighted):
        """The measured branch and the count-only fallback both order
        equals - the fallback runs on a fully cached build, which is the
        one people profile most."""
        pair = [
            BlastRadiusResult("core.bst", 8, weighted, False, True, True),
            BlastRadiusResult("codegen.bst", 8, weighted, False, False, True),
        ]
        durations = {} if not weighted else {"core.bst": 10_000_000}
        forward = ranked(pair, durations)
        assert forward == ranked(list(reversed(pair)), durations), forward
        assert forward[0] == "core.bst", forward


class TestTheRankingCodeIsTheOneThatShips:
    def test_compute_blast_radius_uses_this_function(self):
        """The ordering has one home, so these clauses cannot pass while
        the shipped path ties by chance."""
        source = (REPO / "bga/diagnostics/analyzer.py").read_text(
            encoding="utf-8")
        assert "order_blast_radius(results, element_durations)" in source, (
            "compute_blast_radius no longer calls order_blast_radius, so "
            "every clause in this file is measuring something the tool "
            "does not run")
