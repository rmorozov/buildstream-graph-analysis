"""UX-229: why bga believes what it believes.

Direction 8's anchor. Round 24 found the relationship layer computed and
unpublished; this is the same defect one level up, over the conclusions
rather than the facts. The headline says `scheduler_bound`, and the
fields that decided it, the threshold they were compared against and the
query that deepens them travelled nowhere.

What is asserted here is the chain, not the prose: every reference
resolves inside the same document, every quoted value equals the field
it cites, the rule's threshold is the live constant, and the two
renderers print the object rather than each wording it.
"""
import json
import os
import shutil
import subprocess
import sys

import pytest

from bga import provenance
from bga.report.json import build_document

GOLDEN = "tests/fixtures/golden/mixed_task_kinds"

node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")


def _bga(args):
    result = subprocess.run(
        [sys.executable, "-c",
         "from bga.cli import main; raise SystemExit(main(%r))" % (args,)],
        capture_output=True, text=True, cwd=os.getcwd())
    assert result.returncode == 0, result.stderr
    return result.stdout


@pytest.fixture(scope="module")
def golden():
    return json.loads(_bga(["analyze", GOLDEN, "--format", "json"]))


@pytest.fixture(scope="module")
def synthetic(tmp_path_factory):
    """The 1,202-element run the acceptance names, beside the eleven-
    element one. Different diagnosis, different findings, same contract -
    which is the only way to tell a chain that resolves from one that
    happens to resolve on the fixture it was written against."""
    out = tmp_path_factory.mktemp("big") / "run"
    _bga(["gen-synthetic", str(out), "--seed", "1"])
    return json.loads(_bga(["analyze", str(out), "--format", "json"]))


class TestTheReferencesResolve:
    @pytest.mark.parametrize("run", ["golden", "synthetic"])
    def test_no_reference_dangles(self, run, request):
        document = request.getfixturevalue(run)
        assert provenance.unresolved_references(document) == []

    @pytest.mark.parametrize("run", ["golden", "synthetic"])
    def test_every_quoted_value_equals_the_field_it_cites(self, run, request):
        """The half that a resolve-only check cannot see: a record built
        against one document and shipped inside another would still
        resolve, and would quote the wrong number."""
        document = request.getfixturevalue(run)
        wrong = []
        for _claim, record in provenance.claims(document):
            for entry in record.get("evidence") or []:
                live = provenance.resolve(document, entry["path"])
                if live is provenance.UNRESOLVED or live != entry["value"]:
                    wrong.append(
                        f"{record['claim']}: {entry['path']} quoted "
                        f"{entry['value']!r}, document holds {live!r}")
        assert wrong == [], wrong

    def test_every_claim_in_the_document_carries_one(self, synthetic):
        explained = {record["claim"] for _c, record in provenance.claims(synthetic)}
        for finding in synthetic["findings"]:
            assert finding["id"] in explained, finding["id"]
        assert "diagnosis" in explained
        # `UX-344`: a top action's chain is the finding's, reached by
        # the `finding_id` it already carries - there is no second
        # record beside the id, and no `see` path spelling it out.
        for action in synthetic["headline"]["top_actions"]:
            assert "provenance" not in action, action
            assert action["finding_id"] in explained, action

    def test_a_dangling_path_is_published_as_unresolved_not_dropped(self):
        """"We could not read it" and "there was nothing there" are
        different claims, and the record has to keep them apart."""
        record = provenance.record({"id": "confidence"}, "confidence",
                                   "finding", {"confidence": {}})
        assert [e["resolved"] for e in record["evidence"]] == [False, False, False]
        assert provenance.unresolved_references(
            {"findings": [{"id": "confidence"}], "provenance": [record]})


class TestTheRuleIsTheLiveConstant:
    def test_the_diagnosis_record_names_the_ratio_and_the_threshold(self, golden):
        record = provenance.for_claim(golden, "diagnosis")
        assert record["rule"]["name"] == "CHAIN_BOUND_RATIO"
        assert record["rule"]["threshold"] == 0.9
        assert record["rule"]["observed_path"] == "headline.chain_share"
        cited = [e["path"] for e in record["evidence"]]
        assert "headline.chain_share" in cited
        assert "floors.t_infinity_observed" in cited

    def test_moving_the_threshold_moves_the_published_record(self, monkeypatch):
        """The acceptance's mutation, as a test rather than as a manual
        step: a record that copied `0.9` beside the constant would pass
        every other guard here and be documentation, not evidence."""
        from pathlib import Path

        from bga import findings as findings_mod
        from bga.analyzer import BuildEfficiencyAnalyzer

        def analyse():
            analyzer = BuildEfficiencyAnalyzer()
            analyzer.load(Path(GOLDEN))
            return build_document(analyzer.analyze(Path(GOLDEN)))

        before = provenance.for_claim(analyse(), "diagnosis")["rule"]
        monkeypatch.setattr(findings_mod, "CHAIN_BOUND_RATIO", 1.5)
        after = provenance.for_claim(analyse(), "diagnosis")["rule"]
        assert before["threshold"] == 0.9 and after["threshold"] == 1.5
        # And the comparison flips with it. The moved threshold is 1.5
        # rather than `UX-229`'s original 0.5 because `UX-477` changed
        # what the ratio is a share *of*: against the task horizon this
        # run reads 1.000, so 0.5 no longer straddles it and a mutation
        # to 0.5 would not flip anything - which is the mutation not
        # discriminating, not the guard passing.
        assert before["comparison"] == ">=" and after["comparison"] == "<"


class TestTheTableCoversTheFindings:
    def _finding_ids(self):
        import re
        source = open("bga/findings.py", encoding="utf-8").read()
        return set(re.findall(r"_finding\(\s*\n?\s*'([a-z0-9-]+)'", source))

    def test_every_finding_the_pipeline_emits_can_be_explained(self):
        missing = sorted(self._finding_ids() - set(provenance.claim_ids()))
        assert missing == [], (
            f"finding(s) with no provenance entry: {missing} - they would "
            f"publish a record with no rule and no evidence")

    def test_the_table_names_no_finding_that_does_not_exist(self):
        """The other direction: a renamed finding leaves its entry
        behind, and the entry then explains nothing forever."""
        stale = sorted(set(provenance.claim_ids())
                       - self._finding_ids() - {"diagnosis"})
        assert stale == [], f"provenance entries for no such finding: {stale}"

    def test_the_mesh_threshold_is_named_rather_than_a_literal(self):
        """A rule whose threshold has no name cannot be published as
        one. This was a bare `>= 0.5` inside the finding it gates."""
        from bga import findings as findings_mod

        assert findings_mod.MESH_ZERO_SLACK_SHARE == 0.5
        record = provenance.record(
            {"id": "mesh-graph", "evidence": {"zero_slack_share": 0.62}},
            "mesh-graph", "finding", {"elements": {"zero_slack_share": 0.62}})
        assert record["rule"]["name"] == "MESH_ZERO_SLACK_SHARE"
        assert record["rule"]["threshold"] == 0.5

    def test_a_claim_drawn_from_unpublished_fields_says_so(self):
        """`memory_envelope` is computed, is what its finding asserts,
        and reaches no consumer of this document. Naming it is the
        honest shape - silence would read as no gap.

        `capacity_recommendation` was the other one until `UX-275`
        published it; it is checked below instead, from the other
        direction."""
        record = provenance.record(
            {"id": "memory-envelope"}, "memory-envelope", "finding", {})
        assert record["unpublished_inputs"]

    def test_a_claim_whose_fields_were_published_cites_them(self):
        """`UX-275`. The gap closing has to be visible here, or the
        label outlives the defect: a chain that still says "computed,
        not published" about a field a consumer can now read is a lie
        that reads as candour."""
        payload = {"capacity_recommendation": {
            "builders": 4,
            "binding_constraint": "graph",
            "recommended_builders": 2,
            "cores_busy": 1.6}}
        record = provenance.record({"id": "capacity-recommendation"},
                                   "capacity-recommendation", "finding",
                                   payload)
        assert record["unpublished_inputs"] == []
        cited = {entry["path"]: entry for entry in record["evidence"]}
        assert cited["capacity_recommendation.binding_constraint"]["value"] \
            == "graph"
        assert cited["capacity_recommendation.recommended_builders"][
            "resolved"], cited
        assert all(entry["resolved"] for entry in record["evidence"]), record


class TestATopActionPointsRatherThanCopies:
    """`_top_actions` is references-not-copies by construction - its
    `finding_id` is where the reasoning lives. The first draft of the
    provenance module copied the whole record into each action, which
    restated one chain four times in a document whose subject is not
    restating things.

    `UX-344` removed the last of that: the action used to carry a third
    spelling of the reference - a `see` path into the finding's *copy*
    of the record - and now carries only the id, which resolves into the
    one published list."""

    def test_the_action_carries_an_id_and_nothing_else(self, golden):
        for action in golden["headline"]["top_actions"]:
            assert "provenance" not in action, action
            assert action["finding_id"]

    def test_the_id_it_names_resolves_to_the_published_record(self, golden):
        for action in golden["headline"]["top_actions"]:
            pointed = provenance.for_claim(golden, action["finding_id"])
            assert pointed is not None, action
            assert pointed["claim"] == action["finding_id"]
            assert pointed["rule"]["sentence"]

    def test_a_pointer_that_dangles_is_reported(self):
        assert provenance.unresolved_references(
            {"provenance": [], "headline": {"top_actions": [
                {"finding_id": "no-such-finding"}]}})


@pytest.fixture(scope="module")
def comparison():
    from pathlib import Path

    from bga.compare import compare_runs

    return compare_runs(Path(GOLDEN), Path(GOLDEN))


class TestTheComparisonCitesTheCandidatesChain:
    def test_the_comparison_publishes_the_candidates_diagnosis(self, comparison):
        record = comparison.to_dict()["candidate_diagnosis"]
        # `chain_bound` since `UX-477`: four back-to-back tasks are a
        # chain, and the old `scheduler_bound` came from BuildStream's
        # startup sitting in the denominator.
        assert record["diagnosis"] == "chain_bound"
        assert record["provenance"]["rule"]["name"] == "CHAIN_BOUND_RATIO"

    def test_it_says_which_document_its_paths_walk(self, comparison, golden):
        """A record that travels needs to name where its paths resolve.
        These are into the candidate run's `analyze/v5`, not into the
        comparison quoting it - and following them against the wrong
        document is the failure this field exists to prevent."""
        record = comparison.to_dict()["candidate_diagnosis"]["provenance"]
        assert record["document"] == "analyze/v5"
        for entry in record["evidence"]:
            assert provenance.resolve(comparison.to_dict(),
                                      entry["path"]) is provenance.UNRESOLVED
            assert provenance.resolve(golden, entry["path"]) == entry["value"]

    def test_the_ci_comment_quotes_the_record_and_invents_nothing(
            self, comparison):
        import argparse

        from bga.report.ci_comment import render_ci_comment

        comment = render_ci_comment(comparison, argparse.Namespace(
            fail_on_regression=False, max_addition_stretch=None,
            min_efficiency=None, fail_on_efficiency_regression=False,
            fail_on_cache_regression=False, fail_on_low_confidence=False))
        record = comparison.to_dict()["candidate_diagnosis"]["provenance"]
        assert record["rule"]["sentence"] in comment
        assert f"`{record['rule']['name']}` = `{record['rule']['threshold']}`" \
            in comment
        for entry in record["evidence"]:
            assert f"`{entry['path']}` | {entry['value']}" in comment

    def test_moving_the_threshold_moves_what_the_comment_prints(
            self, tmp_path, monkeypatch):
        """A literal `0.9` in the comment passes every assertion above,
        because 0.9 is what the constant holds today. Only moving the
        constant tells a citation from a copy - the same reason the
        analyze-side mutation test exists, and the reason this one was
        written after a mutation that failed to discriminate.
        """
        import argparse
        from pathlib import Path

        from bga import findings as findings_mod
        from bga.compare import compare_runs
        from bga.report.ci_comment import render_ci_comment

        def comment():
            result = compare_runs(Path(GOLDEN), Path(GOLDEN))
            return render_ci_comment(result, argparse.Namespace(
                fail_on_regression=False, max_addition_stretch=None,
                min_efficiency=None, fail_on_efficiency_regression=False,
                fail_on_cache_regression=False, fail_on_low_confidence=False))

        assert "`CHAIN_BOUND_RATIO` = `0.9`" in comment()
        monkeypatch.setattr(findings_mod, "CHAIN_BOUND_RATIO", 0.42)
        moved = comment()
        assert "`CHAIN_BOUND_RATIO` = `0.42`" in moved
        assert "`0.9`" not in moved

    def test_the_block_is_folded_so_the_sidebar_stays_short(self, comparison):
        import argparse

        from bga.report.ci_comment import render_ci_comment

        comment = render_ci_comment(comparison, argparse.Namespace(
            fail_on_regression=False, max_addition_stretch=None,
            min_efficiency=None, fail_on_efficiency_regression=False,
            fail_on_cache_regression=False, fail_on_low_confidence=False))
        opened = comment.index("<details><summary>Why the candidate")
        closed = comment.index("</details>", opened)
        assert comment.index(
            "The critical path is", opened) < closed


class TestThePathGrammar:
    def test_a_list_entry_is_selected_by_key_not_by_position(self):
        """`violations` order is not a contract. `[0]` would be correct
        until the day a second violation is prepended."""
        document = {"violations": [{"type": "clock_skew"},
                                   {"type": "build_failed", "failed_count": 4}]}
        assert provenance.resolve(
            document, "violations[type=build_failed].failed_count") == 4

    def test_an_index_walks_a_list(self):
        document = {"latent_heavies": [{"duration_us": 7}]}
        assert provenance.resolve(
            document, "latent_heavies[0].duration_us") == 7

    def test_a_missing_key_is_unresolved_and_not_none(self):
        assert provenance.resolve({"a": {"b": None}}, "a.b") is None
        assert provenance.resolve({"a": {}}, "a.b") is provenance.UNRESOLVED


class TestBothRenderersReadTheSameObject:
    def test_the_terminal_prints_the_chain_only_when_asked(self):
        plain = _bga(["analyze", GOLDEN])
        assert "why:" not in plain and "rule:" not in plain

    def test_the_terminal_prints_the_published_record_verbatim(self, golden):
        """Not "prints something similar": the exact lines
        `provenance.render` produces from the document's own record."""
        explained = _bga(["analyze", GOLDEN, "--explain"])
        for record in golden["provenance"]:
            for line in provenance.render(record):
                assert line in explained, line

    def test_the_chain_appears_under_the_claim_it_explains(self):
        explained = _bga(["analyze", GOLDEN, "--explain"]).splitlines()
        titles = [i for i, line in enumerate(explained)
                  if line.startswith("  Confidence: ")]
        assert titles, explained[:40]
        assert explained[titles[0] + 1].strip().startswith("why:")


@needs_node
class TestThePageDrawsTheObject:
    def _render(self, record):
        script = _HARNESS.replace("__RECORD__", json.dumps(record))
        result = subprocess.run([node, "--input-type=module", "-e", script],
                                capture_output=True, text=True,
                                cwd=os.getcwd(), timeout=60)
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)

    def test_every_string_it_shows_comes_from_the_record(self, golden):
        """`UX-207`'s rule, at the claim level: a page that worded the
        comparison itself would be a second explanation of one claim,
        and the first thing it would do is disagree with the terminal.
        """
        record = provenance.for_claim(golden, "diagnosis")
        out = self._render(record)
        published = {str(record["rule"]["sentence"]), str(record["rule"]["name"]),
                     str(record["rule"]["threshold"]),
                     str(record["rule"]["module"]),
                     # `UX-357`: three more the block draws, and each is
                     # a field of the same record rather than a reading
                     # of it.
                     str(record["rule"].get("observed_path")),
                     str(record["rule"].get("comparison")),
                     str(record.get("document")),
                     str(record.get("claim"))}
        for entry in record["evidence"]:
            published.add(str(entry["path"]))
            published.add(str(entry["value"]))
            # Python and JavaScript disagree about how to spell a whole
            # float: `str(1.0)` is "1.0" and `String(1.0)` is "1". The
            # claim here is that the page shows no *value* the record
            # does not hold, and 1 and 1.0 are one value - so the
            # renderer's own spelling of each number is admitted, and
            # nothing else is. Reachable since `UX-477` made a
            # `chain_share` of exactly 1.000 ordinary; before that no
            # evidence value on this fixture was ever whole.
            value = entry["value"]
            if isinstance(value, float) and value.is_integer():
                published.add(str(int(value)))

        # Layout, named one string at a time rather than allowed by a
        # pattern. `UX-357` put the depth count on the summary (§3a.1)
        # and a lead in front of the document; both are apparatus - the
        # count is a fact about the record's own shape, not about the
        # build - and neither may grow into a sentence without being
        # written down here.
        layout = {"Why", " in ", "Paths resolve against ",
                  "No named threshold; computed in ",
                  f"1 level, {len(record['evidence'])} "
                  f"row{'' if len(record['evidence']) == 1 else 's'}"}

        def accounted(text):
            if text in published or text in layout:
                return True
            if text.strip() in layout or text.strip() in published:
                return True
            # The rule line is `NAME observed comparison threshold` -
            # published fields with punctuation between them, which is
            # layout rather than a further claim.
            words = [w.strip("()") for w in text.split()]
            return all(w in published or w == "=" for w in words)

        unaccounted = [text for text in out["text"]
                       if text and not accounted(text)]
        assert unaccounted == [], (
            f"the page shows text no field of the record holds: {unaccounted}")

    def test_the_reference_paths_and_values_are_the_records_own(self, golden):
        """Compared as *values*, not as spellings. Python writes a whole
        float `1.0` and JavaScript writes it `1`; a guard that demanded
        the page reproduce `str()` would be asserting Python's number
        formatting about a page written in another language. What must
        hold is that the page shows the record's own number and not a
        rounding or a re-derivation of it - so each raw cell is parsed
        back and compared numerically where the record holds a number,
        and compared exactly where it does not.

        `UX-477` is what made this reachable: a `chain_share` of exactly
        1.000 is ordinary against the task horizon, and no evidence
        value on this fixture had ever been whole before."""
        record = provenance.for_claim(golden, "diagnosis")
        out = self._render(record)
        assert out["paths"] == [e["path"] for e in record["evidence"]]
        assert len(out["raw"]) == len(record["evidence"])
        for shown, entry in zip(out["raw"], record["evidence"]):
            value = entry["value"]
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                assert float(shown) == value, (shown, value)
            else:
                assert shown == str(value), (shown, value)

    def test_the_threshold_is_carried_not_recomputed(self, golden):
        out = self._render(provenance.for_claim(golden, "diagnosis"))
        assert out["threshold"] == "0.9"
        assert out["rule"] == "CHAIN_BOUND_RATIO"

    def test_an_unresolved_reference_says_so_rather_than_blank(self):
        record = provenance.record({"id": "confidence"}, "confidence",
                                   "finding", {})
        out = self._render(record)
        assert "unresolved" in out["text"]

    def test_a_payload_without_provenance_draws_nothing(self):
        assert self._render(None)["rendered"] is False


_HARNESS = """
globalThis._makeNode ??= (await import(process.env.BGA_DOM_SHIM)).makeNode;
globalThis._installDocument ??= (await import(process.env.BGA_DOM_SHIM)).installDocument;

function make(tag) {
  const node = _makeNode(tag);
  return node;
}
_installDocument();
const views = await import("./tests/viewer.mjs");
const node = views.renderProvenance(__RECORD__);
const text = [], paths = [], raw = [];
(function walk(n) {
  if (!n) return;
  // Leaves only. A container's `textContent` is the concatenation of
  // its descendants - true in a browser and now true here - so
  // collecting every node counted each string again inside every
  // ancestor, and the "text no field holds" check compared the page
  // against a sentence nobody wrote (`UX-264`).
  if (!(n.children ?? []).length && n.textContent) text.push(n.textContent);
  if (n.attrs["data-path"] !== undefined) paths.push(n.attrs["data-path"]);
  if (n.attrs["data-raw"] !== undefined) raw.push(n.attrs["data-raw"]);
  (n.children ?? []).forEach(walk);
})(node);
console.log(JSON.stringify({
  rendered: node !== null,
  text, paths, raw,
  rule: node?.children?.find((c) => c.attrs["data-rule"])?.attrs["data-rule"] ?? null,
  threshold: node?.children?.find((c) => c.attrs["data-threshold"])
               ?.attrs["data-threshold"] ?? null,
}));
"""


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
