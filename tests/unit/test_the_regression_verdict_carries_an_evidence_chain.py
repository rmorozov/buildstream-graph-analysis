"""UX-593: why did you call this REGRESSED.

`UX-229` gave every `analyze/v5` claim a chain - evidence refs, the rule
that fired, the query that deepens it - and a comparison carries one of
them: `candidate_diagnosis.provenance`, the *candidate run's* diagnosis.
Measured on `main` before this item, on a pair that regresses +9.5%:

    bga compare, verdict REGRESSED
      the CI comment's only <details> is "Why the candidate looks
      like this" - CHAIN_BOUND_RATIO, over the candidate's own analyze
      document
      the text report prints the band and the culprits as two
      unconnected blocks and no rule at all
      compare/v2's 28 keys carry no record for the verdict

So the line a contributor argues with - the one at the top of the
comment - published no grounds: not the baseline it was measured
against, not the band or rule it crossed, not which elements crossed it.

The chain is one object, built in `bga/compare.py`, whose every
`evidence[].path` walks `compare/v2` itself. That is what makes it
evidence rather than prose: the guards below re-resolve every path
against the payload and compare the quoted value to what is there, which
is the half a resolve-only check cannot see.
"""
import argparse
import json

import pytest

from bga import provenance, schemas
from bga.compare import (
    DEFAULT_BAND_K,
    VERDICT_CULPRITS_CITED,
    compare_runs,
    verdict_provenance,
)
from bga.report.ci_comment import render_ci_comment
from bga.report.text import format_compare_text


def _span(uid, ts, dur):
    return {"task_key": f"{uid}|BUILD|BUILD|0", "ts_us": ts, "dur_us": dur,
            "resources": ["PROCESS"], "primary_resource": "PROCESS"}


def _run(directory, durations, end, deps=()):
    """One run: `durations` is `{uid: dur_us}`, `end` the wall clock.

    The wall clock is written explicitly because the band is derived
    from `run-context.json` alone (`UX-296`) and the verdict is judged
    on it - so a fixture that only moved element durations would move
    the culprits without moving the verdict they explain.
    """
    directory.mkdir(parents=True)
    (directory / "run-context.json").write_text(json.dumps({
        "trace_epsilon_us": 1000, "max_jobs": 2,
        "resource_capacities": {"PROCESS": 2},
        "wall_clock": {"start_us": 0, "end_us": end}}))
    (directory / "graph.json").write_text(json.dumps({
        "elements": [{"uid": uid} for uid in durations],
        "dependencies": [{"predecessor": a, "successor": b} for a, b in deps]}))
    (directory / "trace.json").write_text(json.dumps({
        "spans": [_span(uid, i * 100_000, dur)
                  for i, (uid, dur) in enumerate(durations.items())],
        "phases": []}))
    return directory


BEFORE = {"big.bst": 10_000, "mid.bst": 10_000, "small.bst": 10_000,
          "saver.bst": 40_000, "tiny.bst": 20_000}
AFTER = {"big.bst": 70_000, "mid.bst": 40_000, "small.bst": 20_000,
         "saver.bst": 10_000, "tiny.bst": 60_000}


@pytest.fixture
def regressed(tmp_path):
    """+9.5% on the wall clock, with four elements grown and one shrunk.

    More than one element in the grown group on purpose: `UX-221`'s
    outcome records a ranking mutation that could not fail against a
    fixture with one row per group.
    """
    return compare_runs(_run(tmp_path / "baseline", BEFORE, 420_000),
                        _run(tmp_path / "candidate", AFTER, 460_000))


@pytest.fixture
def banded(tmp_path):
    """The same regression, judged against a five-run baseline set whose
    own spread is wider than the fixed rule - so `DEFAULT_BAND_K`, not
    `_SIGNIFICANCE_PCT`, is the constant the verdict fired on."""
    baseline = _run(tmp_path / "baseline", BEFORE, 435_000)
    others = [_run(tmp_path / f"b{n}", BEFORE, end) for n, end in
              enumerate((425_000, 430_000, 440_000, 445_000))]
    candidate = _run(tmp_path / "candidate", AFTER, 460_000)
    return compare_runs(baseline, candidate,
                        baseline_runs=[baseline, *others])


@pytest.fixture
def widened(tmp_path):
    """A baseline set of near-identical runs. `compute_band` collapses
    to a near-point and `widen_band` widens it to the fixed percentage -
    after which the number the verdict was judged against is
    `_SIGNIFICANCE_PCT` and the band's own `k` is not the rule at all.
    """
    baseline = _run(tmp_path / "baseline", BEFORE, 435_000)
    others = [_run(tmp_path / f"b{n}", BEFORE, end) for n, end in
              enumerate((435_000, 435_001, 434_999))]
    candidate = _run(tmp_path / "candidate", AFTER, 460_000)
    return compare_runs(baseline, candidate,
                        baseline_runs=[baseline, *others])


def _paths(record):
    return [entry["path"] for entry in record["evidence"]]


def _args():
    return argparse.Namespace(
        fail_on_regression=False, fail_on_efficiency_regression=False,
        min_efficiency=None, fail_on_inefficient_additions=False,
        max_addition_stretch=None, regression_threshold=None)


class TestTheVerdictNamesWhatItJudged:

    def test_the_fixture_actually_regresses(self, regressed):
        """A chain guard on a comparison that came out `improved` would
        assert about a sentence nobody disputes."""
        assert regressed.verdict_kind == "regressed"

    def test_it_cites_the_baseline_it_compared_against(self, regressed):
        record = verdict_provenance(regressed)

        assert "baseline_run_id" in _paths(record)
        assert "baseline.total_duration_us" in _paths(record)
        assert "candidate.total_duration_us" in _paths(record)

    def test_it_cites_the_band_it_used(self, banded):
        record = verdict_provenance(banded)

        assert banded.baseline_band is not None
        assert {"baseline_band.n", "baseline_band.low_us",
                "baseline_band.high_us"} <= set(_paths(record))

    def test_and_omits_the_band_paths_when_there_was_no_band(self, regressed):
        """`UX-249`'s rule about absence: a reference resolving to
        nothing reads as a published field, and this run has no band."""
        assert regressed.baseline_band is None
        assert not [p for p in _paths(verdict_provenance(regressed))
                    if p.startswith("baseline_band")]


class TestTheCulpritsAreInTheChain:
    """The acceptance test's own mutation: drop the culprits and this
    class is what reddens."""

    def test_the_elements_that_crossed_are_cited_by_uid(self, regressed):
        record = verdict_provenance(regressed)
        cited = [p for p in _paths(record) if "element_uid=" in p]

        assert [p.split("element_uid=")[1].split("]")[0] for p in cited] == [
            "big.bst", "tiny.bst", "mid.bst", "small.bst"]

    def test_and_by_how_much(self, regressed):
        record = verdict_provenance(regressed)
        by_path = {e["path"]: e["value"] for e in record["evidence"]}

        assert by_path[
            "element_deltas.rows[element_uid=big.bst].delta_us"] == 60_000
        assert by_path[
            "element_deltas.rows[element_uid=tiny.bst].delta_us"] == 40_000

    def test_the_element_that_shrank_is_not_a_culprit(self, regressed):
        """`saver.bst` moved 30ms - more than two of the cited four -
        and moved the other way. A chain ranked on bare magnitude would
        name it as a reason the build got slower."""
        assert "saver.bst" not in str(_paths(verdict_provenance(regressed)))

    def test_how_many_crossed_is_cited_rather_than_counted(self, regressed):
        """Five names of a stated number, not five of an unknown one."""
        record = verdict_provenance(regressed)
        by_path = {e["path"]: e["value"] for e in record["evidence"]}

        assert by_path["element_deltas.counts.grew"] == 4

    def test_the_citation_is_capped_and_the_count_says_by_how_much(
            self, tmp_path):
        before = {f"e{n}.bst": 10_000 for n in range(12)}
        after = {uid: 10_000 + 1_000 * n for n, uid in enumerate(before)}
        comparison = compare_runs(
            _run(tmp_path / "baseline", before, 1_110_000),
            _run(tmp_path / "candidate", after, 1_200_000))
        record = verdict_provenance(comparison)
        by_path = {e["path"]: e["value"] for e in record["evidence"]}

        cited = [p for p in _paths(record) if "element_uid=" in p]
        assert len(cited) == VERDICT_CULPRITS_CITED
        assert by_path["element_deltas.counts.grew"] == 11


class TestEveryReferenceResolvesInTheDocumentItNames:
    """`UX-229`'s round trip, one document over. A record whose paths
    dangle is documentation; a record whose paths resolve to the wrong
    numbers is worse, so both halves are checked."""

    @pytest.mark.parametrize("name", ["regressed", "banded", "widened"])
    def test_the_paths_walk_compare_v2_and_quote_it_correctly(
            self, name, request):
        comparison = request.getfixturevalue(name)
        document = comparison.to_dict()
        record = verdict_provenance(comparison)

        assert record["document"] == schemas.COMPARE
        for entry in record["evidence"]:
            resolved = provenance.resolve(document, entry["path"])
            assert resolved is not provenance.UNRESOLVED, entry["path"]
            assert resolved == entry["value"], entry["path"]

    def test_a_refusal_publishes_no_chain(self, tmp_path):
        """`not_comparable` states its own reason and no band
        arithmetic ran behind it, so there is nothing to publish - and a
        record built anyway would quote a verdict that was withheld."""
        baseline = _run(tmp_path / "baseline", BEFORE, 420_000)
        comparison = compare_runs(
            baseline, _run(tmp_path / "candidate", AFTER, 460_000))
        comparison.verdict_kind = "not_comparable"

        assert verdict_provenance(comparison) is None


class TestTheRuleIsReadLiveRatherThanCopied:
    """`UX-229`'s lesson: every assertion about a threshold passes
    against a literal, because the literal is what the constant holds
    today. Only moving the constant tells a citation from a copy."""

    def test_moving_the_band_width_moves_the_published_rule(
            self, tmp_path, monkeypatch):
        baseline = _run(tmp_path / "baseline", BEFORE, 435_000)
        others = [_run(tmp_path / f"b{n}", BEFORE, end) for n, end in
                  enumerate((425_000, 430_000, 440_000, 445_000))]
        candidate = _run(tmp_path / "candidate", AFTER, 460_000)

        def rule(k):
            comparison = compare_runs(baseline, candidate,
                                      baseline_runs=[baseline, *others],
                                      band_k=k)
            return verdict_provenance(comparison)["rule"]

        assert rule(DEFAULT_BAND_K)["name"] == "DEFAULT_BAND_K"
        assert rule(DEFAULT_BAND_K)["threshold"] == DEFAULT_BAND_K
        assert rule(1.5)["threshold"] == 1.5
        assert "1.5x scaled MAD" in rule(1.5)["sentence"]

    def test_a_widened_band_names_the_rule_that_actually_fired(
            self, widened):
        """The case a copied constant gets wrong. The band is derived,
        comes out narrower than the fixed percentage, and `widen_band`
        replaces it - after which `DEFAULT_BAND_K` is not what the
        candidate was judged against."""
        record = verdict_provenance(widened)

        assert widened.baseline_band["widened_to_fixed_pct"] is True
        assert record["rule"]["name"] == "_SIGNIFICANCE_PCT"
        assert "widened" in record["rule"]["sentence"]

    def test_moving_the_fixed_percentage_moves_the_comment(
            self, tmp_path, monkeypatch):
        from bga import compare as compare_mod

        baseline = _run(tmp_path / "baseline", BEFORE, 420_000)
        candidate = _run(tmp_path / "candidate", AFTER, 460_000)

        def comment():
            return render_ci_comment(
                compare_runs(baseline, candidate), _args())

        assert "`_SIGNIFICANCE_PCT` = `1`" in comment()
        monkeypatch.setattr(compare_mod, "_SIGNIFICANCE_PCT", 7)
        moved = comment()
        assert "`_SIGNIFICANCE_PCT` = `7`" in moved
        assert "`_SIGNIFICANCE_PCT` = `1`" not in moved


class TestTheSurfacesQuoteTheRecordAndInventNothing:

    def test_the_ci_comment_publishes_every_reference(self, banded):
        record = verdict_provenance(banded)
        comment = render_ci_comment(banded, _args())

        assert record["rule"]["sentence"] in comment
        assert (f"`{record['rule']['name']}` = "
                f"`{record['rule']['threshold']}`") in comment
        for entry in record["evidence"]:
            assert f"`{entry['path']}` = {entry['value']}" in comment

    def test_the_fold_keeps_the_sidebar_short(self, banded):
        """A `<details>` is one line until a reviewer opens it, which is
        the property the comment's budget is really about."""
        comment = render_ci_comment(banded, _args())
        opened = comment.index("<details><summary>Why the verdict")
        closed = comment.index("</details>", opened)

        assert record_between(comment, opened, closed)

    def test_the_terminal_words_the_same_sentence(self, regressed):
        """One object, two surfaces. A renderer wording its own
        sentence is how `bga` came to explain one claim three ways
        before `UX-229`."""
        record = verdict_provenance(regressed)
        text = format_compare_text(regressed)

        assert f"Why: {record['rule']['sentence']}" in text
        assert (f"Rule: {record['rule']['name']} = "
                f"{record['rule']['threshold']}") in text

    def test_the_terminal_prints_no_raw_field_path(self, regressed):
        """`UX-121`'s rule holds for this surface too: the text report
        prints values under human labels, and a `total_duration_us`
        beside a number rendered in seconds is the confusion it
        measured. The paths live in the CI comment, which prints them
        as paths."""
        text = format_compare_text(regressed)

        assert "_us " not in text and "_us\n" not in text


def record_between(comment, opened, closed):
    """The chain's sentence really is inside the fold, not beside it."""
    return comment.index("The candidate is", opened) < closed
