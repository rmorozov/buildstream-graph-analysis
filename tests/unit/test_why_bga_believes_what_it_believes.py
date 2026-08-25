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
        for action in synthetic["headline"]["top_actions"]:
            assert action.get("provenance"), action

    def test_a_dangling_path_is_published_as_unresolved_not_dropped(self):
        """"We could not read it" and "there was nothing there" are
        different claims, and the record has to keep them apart."""
        record = provenance.record({"id": "confidence"}, "confidence",
                                   "finding", {"confidence": {}})
        assert [e["resolved"] for e in record["evidence"]] == [False, False, False]
        assert provenance.unresolved_references(
            {"findings": [{"id": "confidence", "provenance": record}]})


class TestTheRuleIsTheLiveConstant:
    def test_the_diagnosis_record_names_the_ratio_and_the_threshold(self, golden):
        record = golden["headline"]["provenance"]
        assert record["rule"]["name"] == "CHAIN_BOUND_RATIO"
        assert record["rule"]["threshold"] == 0.9
        assert record["rule"]["observed_path"] == "headline.chain_ratio"
        cited = [e["path"] for e in record["evidence"]]
        assert "headline.chain_ratio" in cited
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

        before = analyse()["headline"]["provenance"]["rule"]
        monkeypatch.setattr(findings_mod, "CHAIN_BOUND_RATIO", 0.5)
        after = analyse()["headline"]["provenance"]["rule"]
        assert before["threshold"] == 0.9 and after["threshold"] == 0.5
        # And the comparison flips with it: 0.875 is below 0.9 and above
        # 0.5, so the same run is diagnosed the other way.
        assert before["comparison"] == "<" and after["comparison"] == ">="


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
            "mesh-graph", "finding", {"signals": {"zero_slack_share": 0.62}})
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
    restating things."""

    def test_the_action_carries_a_path_not_a_second_copy(self, golden):
        for action in golden["headline"]["top_actions"]:
            record = action["provenance"]
            assert record["see"] == (
                f"findings[id={action['finding_id']}].provenance")
            assert "rule" not in record and "evidence" not in record

    def test_the_path_it_names_resolves_to_the_findings_record(self, golden):
        for action in golden["headline"]["top_actions"]:
            pointed = provenance.resolve(golden, action["provenance"]["see"])
            assert pointed is not provenance.UNRESOLVED
            assert pointed["claim"] == action["finding_id"]
            assert pointed["rule"]["sentence"]

    def test_a_pointer_that_dangles_is_reported(self):
        record = provenance.reference({"findings": []}, "no-such-finding")
        assert record["resolved"] is False
        assert provenance.unresolved_references(
            {"headline": {"provenance": {}, "top_actions": [
                {"provenance": record}]}})


@pytest.fixture(scope="module")
def comparison():
    from pathlib import Path

    from bga.compare import compare_runs

    return compare_runs(Path(GOLDEN), Path(GOLDEN))


class TestTheComparisonCitesTheCandidatesChain:
    def test_the_comparison_publishes_the_candidates_diagnosis(self, comparison):
        record = comparison.to_dict()["candidate_diagnosis"]
        assert record["diagnosis"] == "scheduler_bound"
        assert record["provenance"]["rule"]["name"] == "CHAIN_BOUND_RATIO"

    def test_it_says_which_document_its_paths_walk(self, comparison, golden):
        """A record that travels needs to name where its paths resolve.
        These are into the candidate run's `analyze/v2`, not into the
        comparison quoting it - and following them against the wrong
        document is the failure this field exists to prevent."""
        record = comparison.to_dict()["candidate_diagnosis"]["provenance"]
        assert record["document"] == "analyze/v2"
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
        document = {"signals": {"latent_heavies": [{"duration_us": 7}]}}
        assert provenance.resolve(
            document, "signals.latent_heavies[0].duration_us") == 7

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
        for line in provenance.render(golden["headline"]["provenance"]):
            assert line in explained, line
        for finding in golden["findings"]:
            for line in provenance.render(finding["provenance"]):
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
        record = golden["headline"]["provenance"]
        out = self._render(record)
        published = {str(record["rule"]["sentence"]), str(record["rule"]["name"]),
                     str(record["rule"]["threshold"]),
                     str(record["rule"]["module"]), "Why"}
        for entry in record["evidence"]:
            published.add(str(entry["path"]))
            published.add(str(entry["value"]))
        def accounted(text):
            if text in published:
                return True
            # The rule line is `NAME = threshold (module)` - three
            # published fields with punctuation between them, which is
            # layout rather than a fourth claim.
            words = [w.strip("()") for w in text.split()]
            return all(w in published or w == "=" for w in words)

        unaccounted = [text for text in out["text"]
                       if text and not accounted(text)]
        assert unaccounted == [], (
            f"the page shows text no field of the record holds: {unaccounted}")

    def test_the_reference_paths_and_values_are_the_records_own(self, golden):
        record = golden["headline"]["provenance"]
        out = self._render(record)
        assert out["paths"] == [e["path"] for e in record["evidence"]]
        assert out["raw"] == [str(e["value"]) for e in record["evidence"]]

    def test_the_threshold_is_carried_not_recomputed(self, golden):
        out = self._render(golden["headline"]["provenance"])
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

function make(tag) {
  const node = _makeNode(tag);
  return node;
}
globalThis.document = { createElement: make, createElementNS: (_n, t) => make(t),
                        getElementById: () => null };
const views = await import("./bga/viewer/views.js");
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
