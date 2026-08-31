"""UX-440: two ranked element lists, and one of them is not a plan.

`analyze` publishes two orderings of elements:

| where | ranked by |
|---|---|
| `elements.top_blast_radius` | what a change to this element rebuilds |
| `optimization_horizon` | what fixing it saves, greedily, in sequence |

On both committed fixtures they agree wherever they overlap, which is
what made `UX-439` read them as one order with a bug in it, and what
led this item to ask for "a guard that they do not contradict each other
where they overlap".

**That guard would assert something false.** They are different
questions over different keys, and the agreement on the fixtures is a
property of those two graphs, not of the tool.
`topologies.blast_radius_disagrees_with_horizon` is an ordinary build -
a cheap common ancestor and one expensive leaf, the shape of any project
with a toolchain at the bottom - and on it the two invert:

```text
elements.top_blast_radius  ['hub.bst', 'heavy.bst', 'leaf0.bst', ...]
optimization_horizon       ['heavy.bst', 'hub.bst']
overlap ['heavy.bst', 'hub.bst']  tb ranks [1, 0]  oh ranks [0, 1]
```

So the first clause below pins the counterexample rather than the
agreement: a later round that reaches for "these two should match" meets
a build where matching would be wrong, instead of a fixture where it
happens to hold.

What is left to guard is what is actually true of each list on its own -
that each is ordered by the key its own sentence names - which is the
property `UX-439` established and the one a reordering breaks.
"""
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tests.fixtures import topologies as topo    # noqa: E402

FIXTURES = {"golden": REPO / "tests/fixtures/golden/mixed_task_kinds",
            "macro_micro": REPO / "tests/fixtures/macro_micro/run"}


def _rankings(signals):
    """`(top_blast_radius, optimization_horizon)` as two uid lists."""
    return (list(signals.get("top_blast_radius") or []),
            [step["element_uid"]
             for step in (signals.get("optimization_horizon") or [])])


def _fixture_signals(label):
    from bga.analyzer import BuildEfficiencyAnalyzer

    analyzer = BuildEfficiencyAnalyzer(run_diagnostics=True)
    return analyzer.analyze(FIXTURES[label]).signals


def _analysed(tmp_path):
    analyzer = topo.build_analyzer(
        tmp_path, topo.blast_radius_disagrees_with_horizon(),
        run_diagnostics=True)
    return analyzer.analyze().signals


class TestTheyAreTwoQuestions:

    def test_an_ordinary_build_inverts_them(self, tmp_path):
        """The counterexample, pinned.

        `hub` has the whole graph downstream and a 1s build; `heavy` has
        nothing downstream and a 100s build. Neither number is extreme
        and neither element is degenerate.
        """
        blast, horizon = _rankings(_analysed(tmp_path))
        assert "hub.bst" in blast and "heavy.bst" in blast, blast
        assert "hub.bst" in horizon and "heavy.bst" in horizon, horizon
        assert blast.index("hub.bst") < blast.index("heavy.bst"), (
            f"blast radius should lead with the element everything "
            f"depends on: {blast}")
        assert horizon.index("heavy.bst") < horizon.index("hub.bst"), (
            f"the horizon should lead with the element worth the most "
            f"to fix: {horizon}")

    def test_the_pair_the_lists_disagree_about_is_in_both(self, tmp_path):
        """Otherwise the clause above is about a non-overlap, and
        nothing is being compared."""
        blast, horizon = _rankings(_analysed(tmp_path))
        overlap = [uid for uid in horizon if uid in blast]
        assert len(overlap) >= 2, (
            f"the two lists share fewer than two elements, so no "
            f"disagreement between them is expressible: {overlap}")


class TestEachListIsOrderedByItsOwnKey:
    """`UX-439`'s property, per list, rather than between them."""

    @pytest.mark.parametrize("label", sorted(FIXTURES))
    def test_the_horizon_never_reports_a_step_worth_nothing(self, label):
        """Its own sentence says each entry is what the next fix is
        worth, so a zero or negative entry is a row that should not be
        there rather than a row in the wrong place."""
        result = _fixture_signals(label)
        horizon = result.get("optimization_horizon") or []
        assert horizon, f"{label}: no horizon to check"
        assert all(step["saving_us"] > 0 for step in horizon), horizon

    @pytest.mark.parametrize("label", sorted(FIXTURES))
    def test_the_horizons_cumulative_saving_only_grows(self, label):
        """A sequence whose cumulative total went down would mean a
        later fix undid an earlier one, which the projection cannot
        express - and is what an ordering bug here would look like."""
        totals = [step["cumulative_saving_us"]
                  for step in (_fixture_signals(label).get(
                      "optimization_horizon") or [])]
        assert totals == sorted(totals), totals

    def test_the_blast_ranking_is_ordered_by_what_it_says(self, tmp_path):
        """`blast_radius_ranked_by` names the key; the list must be in
        that key's order, descending."""
        signals = _analysed(tmp_path)
        blast = list(signals.get("top_blast_radius") or [])
        records = signals.get("blast_radius") or {}
        ranked_by = signals.get("blast_radius_ranked_by")
        assert ranked_by in ("measured-rebuild-time", "element-count"), ranked_by
        field = ("weighted_duration_us"
                 if ranked_by == "measured-rebuild-time" else "downstream_count")
        keys = [records[uid][field] for uid in blast if uid in records]
        assert len(keys) == len(blast), (blast, sorted(records))
        assert keys == sorted(keys, reverse=True), list(zip(blast, keys))


class TestEachSentenceSendsTheReaderToTheOther:
    """The half of the fix that is prose: a reader who meets one list
    and does not know the other exists reads a ranking as a plan.
    """

    def test_the_blast_ranking_names_the_horizon(self):
        from bga import schemas

        said = schemas.schema("analyze/v4")["properties"]["elements"][
            "properties"]["top_blast_radius"]["description"]
        assert "optimization_horizon" in said, said
        assert "disagree" in said, said

    def test_the_horizon_names_the_blast_ranking(self):
        from bga import schemas

        said = schemas.schema(
            "analyze/v4")["properties"]["optimization_horizon"]["description"]
        assert "top_blast_radius" in said, said
        assert "different order" in said, said
