"""UX-221: `bga compare` says the build got slower; this says because of what.

The round-24 review estimated a culprit strip as "mostly rendering, if
the compare report already contains per-element deltas". Measured on
`main` before anything changed, with a fixture carrying one element that
grew, one that shrank, one that appeared and one that disappeared:

    slow.bst   10000 -> 30000   appears in compare/v1: no
    fast.bst   20000 ->  5000   appears in compare/v1: no
    gone.bst    8000 -> absent  appears in compare/v1: yes
    added.bst  absent ->  9000  appears in compare/v1: yes

So the task file's "no element appears in `compare/v1` anywhere" is not
quite right, and the truth is sharper: `element_diff` has covered
**appearance and removal** since UX-79 - the two cases the task file
predicted a naive join would drop - and the two it does not cover are
the ones the question is actually about. An element present in both runs
whose duration tripled was nowhere in the document.

Payload item first, deliberately. A viewer differencing two element
tables would be a second comparison, disagreeing with `bga compare` the
moment either changed; UX-214 is the round's evidence for that cost.
"""
import json
import os
import shutil
import subprocess

import pytest

from bga import schemas
from bga.compare import compare_runs
from bga.report.text import ELEMENT_DELTAS_SHOWN, format_compare_text

node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")

_RUN_CONTEXT = {
    "trace_epsilon_us": 1000, "wall_start_us": 0, "wall_end_us": 400000,
    "max_jobs": 2, "resource_capacities": {"PROCESS": 2},
}


def _span(uid, ts, dur):
    return {"task_key": f"{uid}|BUILD|BUILD|0", "ts_us": ts, "dur_us": dur,
            "resources": ["PROCESS"], "primary_resource": "PROCESS"}


def _run(directory, elements, spans, dependencies):
    directory.mkdir(parents=True)
    (directory / "run-context.json").write_text(json.dumps(_RUN_CONTEXT))
    (directory / "graph.json").write_text(json.dumps({
        "elements": [{"uid": uid} for uid in elements],
        "dependencies": dependencies}))
    (directory / "trace.json").write_text(json.dumps(
        {"spans": spans, "phases": []}))
    return directory


@pytest.fixture
def four_cases(tmp_path):
    """The acceptance test's fixture: one element grew, one shrank, one
    appeared and one disappeared - the four cases in one comparison."""
    edge = [{"predecessor": "slow.bst", "successor": "fast.bst"}]
    baseline = _run(
        tmp_path / "baseline", ["slow.bst", "fast.bst", "gone.bst"],
        [_span("slow.bst", 0, 10000), _span("fast.bst", 10000, 20000),
         _span("gone.bst", 30000, 8000)], edge)
    candidate = _run(
        tmp_path / "candidate", ["slow.bst", "fast.bst", "added.bst"],
        [_span("slow.bst", 0, 30000), _span("fast.bst", 30000, 5000),
         _span("added.bst", 35000, 9000)], edge)
    return compare_runs(baseline, candidate)


@pytest.fixture
def three_regressions(tmp_path):
    """Three elements that grew by different amounts, and two that shrank.

    The four-case fixture puts exactly one element in each group, and an
    ordering guard over a one-element list cannot fail - the first draft
    of the ranking mutation below passed against it for that reason. A
    group has to hold more than one row before its order means anything.
    """
    names = ["big.bst", "mid.bst", "small.bst", "saver.bst", "tiny.bst"]
    before = [10000, 10000, 10000, 40000, 20000]
    after = [70000, 40000, 20000, 10000, 15000]   # +60k +30k +10k -30k -5k
    baseline = _run(tmp_path / "baseline", names,
                    [_span(n, i * 100000, d)
                     for i, (n, d) in enumerate(zip(names, before))], [])
    candidate = _run(tmp_path / "candidate", names,
                     [_span(n, i * 100000, d)
                      for i, (n, d) in enumerate(zip(names, after))], [])
    return compare_runs(baseline, candidate)


def _row(comparison, uid):
    for row in comparison.element_deltas["rows"]:
        if row["element_uid"] == uid:
            return row
    raise AssertionError(f"{uid} is not in element_deltas")


class TestAllFourCasesAreInThePayload:

    def test_the_element_that_grew_carries_a_positive_delta(self, four_cases):
        row = _row(four_cases, "slow.bst")
        assert (row["baseline_us"], row["candidate_us"]) == (10000, 30000)
        assert row["delta_us"] == 20000
        assert row["presence"] == "both"

    def test_the_element_that_shrank_carries_a_negative_delta(self, four_cases):
        row = _row(four_cases, "fast.bst")
        assert (row["baseline_us"], row["candidate_us"]) == (20000, 5000)
        assert row["delta_us"] == -15000

    def test_an_appeared_element_has_no_delta_at_all(self, four_cases):
        row = _row(four_cases, "added.bst")
        assert row["presence"] == "appeared"
        assert row["baseline_us"] is None
        assert row["delta_us"] is None, (
            "a delta from zero would rank a new element against elements "
            "that actually changed")

    def test_a_disappeared_element_is_not_an_improvement(self, four_cases):
        """The failure the appeared/disappeared split exists to prevent."""
        row = _row(four_cases, "gone.bst")
        assert row["presence"] == "disappeared"
        assert row["delta_us"] is None
        assert row["verdict_kind"] == "not_comparable"
        assert row["verdict_kind"] != "improved"

    def test_the_counts_state_the_shape_of_the_change(self, four_cases):
        assert four_cases.element_deltas["counts"] == {
            "grew": 1, "shrank": 1, "unchanged": 0,
            "appeared": 1, "disappeared": 1}


class TestTheRankingIsThePayloadsOwn:

    def test_ranked_by_absolute_delta(self, four_cases):
        measurable = [row["element_uid"]
                      for row in four_cases.element_deltas["rows"]
                      if row["delta_us"] is not None]
        assert measurable == ["slow.bst", "fast.bst"]

    def test_rows_without_a_delta_sort_after_the_ones_with_one(self, four_cases):
        uids = [row["element_uid"] for row in four_cases.element_deltas["rows"]]
        assert uids.index("slow.bst") < uids.index("added.bst")
        assert uids.index("fast.bst") < uids.index("gone.bst")

    def test_the_ranking_says_what_it_ranked_by(self, four_cases):
        assert four_cases.element_deltas["ranked_by"] == "absolute-duration-delta"


class TestTheVerdictVocabularyIsTheClosedOne:

    def test_every_row_uses_a_declared_kind(self, four_cases):
        for row in four_cases.element_deltas["rows"]:
            assert row["verdict_kind"] in schemas.VERDICT_KINDS, row

    def test_a_row_is_never_coloured_as_a_regression_inside_the_runs_noise(
            self, tmp_path):
        """Clause 3, on a run that really does come out `within_observed_range`.

        The first draft of this guard built a fixture that landed on
        `no_significant_change` and skipped - which would have left
        clause 3 unchecked while looking checked. The band is what makes
        the case: a tight cluster of baselines plus one far outlier
        keeps the scaled MAD small while stretching the observed extent,
        so the disputed region between them is non-empty and a candidate
        can sit in it.
        """
        edge = [{"predecessor": "a.bst", "successor": "b.bst"}]
        baselines = [
            _run(tmp_path / f"base{i}", ["a.bst", "b.bst"],
                 [_span("a.bst", 0, dur), _span("b.bst", dur, 10000)], edge)
            for i, dur in enumerate((10000, 10000, 10000, 10000, 20000))
        ]
        candidate = _run(
            tmp_path / "cand", ["a.bst", "b.bst"],
            [_span("a.bst", 0, 15000), _span("b.bst", 15000, 10000)], edge)
        comparison = compare_runs(baselines[0], candidate,
                                  baseline_runs=baselines)
        assert comparison.verdict_kind == "within_observed_range", (
            "the fixture must reach the disputed region for this to test "
            f"anything; it reached {comparison.verdict_kind}")
        rows = comparison.element_deltas["rows"]
        assert {row["verdict_kind"] for row in rows} == {"within_observed_range"}
        # a.bst genuinely grew by 5ms. The number is a measurement and
        # still publishes; it is the *judgement* that defers to the run.
        grew = _row(comparison, "a.bst")
        assert grew["delta_us"] == 5000
        assert grew["verdict_kind"] != "regressed"

    def test_a_run_that_calls_no_significant_change_colours_nothing_either(
            self, tmp_path):
        """The same rule on the other verdict that declines to call it.

        A report that says "no significant change" and then paints five
        elements red is arguing with itself, and the run verdict is the
        one with a band behind it.
        """
        # 0.5% apart: below the 1% significance threshold, and above the
        # fixture's 1ms trace epsilon so the difference actually survives
        # into the durations. A first draft used 200us and measured a
        # delta of 0 - the epsilon had swallowed it.
        baseline = _run(tmp_path / "b", ["a.bst"], [_span("a.bst", 0, 1000000)], [])
        candidate = _run(tmp_path / "c", ["a.bst"], [_span("a.bst", 0, 1005000)], [])
        comparison = compare_runs(baseline, candidate)
        assert comparison.verdict_kind == "no_significant_change", (
            comparison.verdict_kind)
        row = _row(comparison, "a.bst")
        assert row["delta_us"] == 5000
        assert row["verdict_kind"] == "no_significant_change"

    def test_the_payload_says_the_rows_are_not_banded(self, four_cases):
        assert four_cases.element_deltas["banded"] is False


class TestThePayloadIsDeclared:

    def test_compare_declares_element_deltas(self):
        assert "element_deltas" in schemas.schema(schemas.COMPARE)["properties"]

    def test_element_diff_is_declared_too(self):
        """Emitted since UX-79 and declared by nothing until now."""
        assert "element_diff" in schemas.schema(schemas.COMPARE)["properties"]

    def test_the_rows_declare_an_element_column(self):
        rows = (schemas.schema(schemas.COMPARE)["properties"]["element_deltas"]
                ["properties"]["rows"])
        roles = [column.get("role") for column in rows[schemas.COLUMNS]]
        assert "element" in roles

    def test_the_verdict_column_carries_the_marker_vocabulary(self):
        item = (schemas.schema(schemas.COMPARE)["properties"]["element_deltas"]
                ["properties"]["rows"]["items"]["properties"]["verdict_kind"])
        assert item[schemas.MARKERS] == schemas.VERDICT_MARKERS
        assert item["enum"] == list(schemas.VERDICT_KINDS)


class TestTheTextReportNamesWhatItLeftOut:

    def test_the_culprits_appear_under_the_verdict(self, four_cases):
        text = format_compare_text(four_cases)
        assert "Which Elements Changed:" in text
        assert text.index("Verdict:") < text.index("Which Elements Changed:")

    def test_a_disappeared_element_is_not_rendered_as_a_saving(self, four_cases):
        text = format_compare_text(four_cases)
        line = next(l for l in text.splitlines() if "gone.bst" in l)
        assert "disappeared" in line and "no delta" in line
        assert "-" not in line.split("gone.bst")[1].split("(")[0]

    def test_the_cap_is_named_rather_than_silent(self, tmp_path):
        """UX-187: the text caps, the payload does not."""
        count = ELEMENT_DELTAS_SHOWN + 5
        names = [f"e{i:02d}.bst" for i in range(count)]
        baseline = _run(tmp_path / "b", names,
                        [_span(n, i * 1000, 1000) for i, n in enumerate(names)], [])
        candidate = _run(tmp_path / "c", names,
                         [_span(n, i * 1000, 1000 + (i + 1) * 500)
                          for i, n in enumerate(names)], [])
        comparison = compare_runs(baseline, candidate)
        assert len(comparison.element_deltas["rows"]) == count
        text = format_compare_text(comparison)
        assert f"and {count - ELEMENT_DELTAS_SHOWN} more" in text

    def test_the_json_is_never_truncated(self, tmp_path):
        count = ELEMENT_DELTAS_SHOWN + 5
        names = [f"e{i:02d}.bst" for i in range(count)]
        baseline = _run(tmp_path / "b", names,
                        [_span(n, i * 1000, 1000) for i, n in enumerate(names)], [])
        candidate = _run(tmp_path / "c", names,
                         [_span(n, i * 1000, 2000) for i, n in enumerate(names)], [])
        payload = compare_runs(baseline, candidate).to_dict()
        assert len(payload["element_deltas"]["rows"]) == count


# The shim the other viewer guards use: a tree of plain objects with
# `attrs`, walked rather than queried. Text nodes carry `attrs` too -
# every walker here reads it, and a bare `{}` turns a missing-attribute
# question into a TypeError three frames deep.
_SHIM = """
globalThis._makeNode ??= (await import(process.env.BGA_DOM_SHIM)).makeNode;
globalThis._installDocument ??= (await import(process.env.BGA_DOM_SHIM)).installDocument;

function make(tag) {
  const node = _makeNode(tag);
  return node;
}
_installDocument();
const all = (n, p, f = []) => { if (!n) return f; if (p(n)) f.push(n);
  (n.children ?? []).forEach((c) => all(c, p, f)); return f; };
const text = (n) => (n.children ?? []).reduce(
  (acc, c) => acc + text(c), n.textContent ?? "");
"""


@needs_node
class TestTheStripReadsThePayload:

    @staticmethod
    def _render(comparison):
        script = _SHIM + '''
          const { renderCulprits } = await import("./tests/viewer.mjs");
          const section = renderCulprits(%s);
          const items = all(section, (n) => n.tagName === "li").map((li) => {
            const link = all(li, (n) => n.tagName === "a")[0];
            return {
              element: li.attrs["data-element"],
              verdict: li.attrs["data-verdict-kind"],
              presence: li.attrs["data-presence"],
              delta: li.attrs["data-delta-us"] ?? null,
              group: null,
              href: link.href ?? link.attrs.href ?? "",
              text: text(li),
            };
          });
          const groups = all(section, (n) => n.attrs["data-group"]).map(
            (n) => [n.attrs["data-group"],
                    all(n, (m) => m.tagName === "li")
                      .map((m) => m.attrs["data-element"])]);
          const caveat = all(section,
            (n) => n.attrs["data-role"] === "not-banded")[0];
          console.log(JSON.stringify({
            items, groups, caveat: text(caveat),
            section: section.attrs["data-section"],
          }));
        ''' % json.dumps(comparison.to_dict())
        result = subprocess.run([node, "--input-type=module", "-e", script],
                                capture_output=True, text=True,
                                cwd=os.getcwd(), timeout=60)
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)

    def test_the_strip_orders_as_the_payload_ranked(self, three_regressions):
        """Clause 4's mutation: a page sorting by its own computed delta
        would be a second comparison.

        Asserted on a fixture with three rows in one group, because the
        four-case fixture has one row per group and no ordering
        assertion over a single row can ever fail.
        """
        out = self._render(three_regressions)
        by_group = dict(out["groups"])
        assert by_group["worse"] == ["big.bst", "mid.bst", "small.bst"]
        assert by_group["better"] == ["saver.bst", "tiny.bst"]

    def test_the_rendered_order_is_the_payloads_order(self, three_regressions):
        """Stated against the payload rather than a literal, so the two
        cannot be edited apart."""
        out = self._render(three_regressions)
        ranked = [row["element_uid"]
                  for row in three_regressions.element_deltas["rows"]
                  if row["delta_us"] is not None]
        rendered = [item["element"] for item in out["items"]]
        # Each group keeps the payload's relative order.
        worse = [uid for uid in ranked if uid in dict(out["groups"])["worse"]]
        assert [u for u in rendered if u in worse] == worse

    def test_every_element_links_to_its_section(self, four_cases):
        out = self._render(four_cases)
        assert out["items"], "no rows rendered"
        for item in out["items"]:
            assert item["href"].startswith("#element-"), item

    def test_a_disappeared_element_is_not_shown_as_an_improvement(self, four_cases):
        out = self._render(four_cases)
        gone = next(i for i in out["items"] if i["element"] == "gone.bst")
        assert gone["presence"] == "disappeared"
        assert gone["verdict"] == "not_comparable"
        assert gone["delta"] is None
        assert "no delta to compare" in gone["text"]

    def test_the_strip_says_the_rows_are_not_banded(self, four_cases):
        out = self._render(four_cases)
        assert "not judged against a noise band" in out["caveat"]

    def test_the_shown_figures_are_the_payloads_own(self, four_cases):
        """Nothing in the page subtracts anything."""
        out = self._render(four_cases)
        slow = next(i for i in out["items"] if i["element"] == "slow.bst")
        assert slow["delta"] == str(_row(four_cases, "slow.bst")["delta_us"])

    def test_a_comparison_with_no_deltas_renders_nothing(self):
        script = _SHIM + '''
          const { renderCulprits } = await import("./tests/viewer.mjs");
          console.log(JSON.stringify({
            empty: renderCulprits({}) === null,
            noRows: renderCulprits({element_deltas: {rows: []}}) === null,
          }));
        '''
        result = subprocess.run([node, "--input-type=module", "-e", script],
                                capture_output=True, text=True,
                                cwd=os.getcwd(), timeout=60)
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout) == {"empty": True, "noRows": True}
