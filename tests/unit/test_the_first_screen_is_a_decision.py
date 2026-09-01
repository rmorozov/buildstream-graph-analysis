"""UX-207: the first screen is a decision, the rest is evidence.

The round-23 review's verdict, confirmed against `boot()`: the viewer
was report-shaped rather than investigation-shaped. Fourteen sections at
one visual level, with the answer the product is framed around — *what
should I fix first, and what is it worth* — already in the payload and
rendering mid-list.

**The rule this is built under is Direction 7's, and it is the reason
the block is Python:** a viewer that derives the diagnosis is a second
analyzer, free to disagree with the text report and the CI gate about
the same build. So the diagnosis, the ratio it came from, the
opportunity split and the ranked actions are decided in `findings.py`
and published as `headline`; the panel reads fields.

Two committed fixtures answer *differently*, which is what makes them
worth having: `a_chain_beside_a_crowd` is `scheduler_bound` at 0.571
and the golden run is `chain_bound` at 1.000. A guard that only ever
saw one branch would not be guarding the branch.

**`UX-477` moved which fixture is which, and the reason is the point.**
The scheduler-bound case used to be the golden run at 0.875 — a verdict
it only had because `chain_share`'s denominator was wall-clock, and
wall-clock carries BuildStream's own ~2.5ms startup. Four back-to-back
tasks are not scheduler-bound; they are a chain with a head in front of
them. So the branch is exercised by a graph that really is
scheduler-bound.

**`UX-474` moved it again, one fixture along, for a related reason.**
It was `shared_base_wide`, and that run's `top_actions` came from the
blast-radius ranking — a ranking of three elements whose blast radius
was zero, which is the defect `UX-474` closed. With the ranking
silent there, the run has no actions at all and this clause had
nothing to read: a guard standing on a published defect. It now reads
`a_chain_beside_a_crowd`, `UX-474`'s own T7 — a four-element chain
whose reach really is 3, 2, 1, 0, beside a crowd of independent work
that puts wall-clock several times above the path.
"""
import contextlib
import io
import json
import os
import shutil
import subprocess
import tempfile

import pytest

from bga import schemas
from bga.findings import (CHAIN_BOUND_RATIO, DIAGNOSES, DIAGNOSIS_CHAIN_BOUND,
                          DIAGNOSIS_INCONCLUSIVE, DIAGNOSIS_SCHEDULER_BOUND)

GOLDEN = "tests/fixtures/golden/mixed_task_kinds"
# `UX-477`: a committed capture whose *graph* is scheduler-bound, rather
# than one whose verdict came from the startup in its denominator.
# `UX-474`: and one whose actions are a ranking of something, rather
# than of three zeros - see the note above.
SCHEDULED = "tests/fixtures/a_chain_beside_a_crowd/run"
REAL = "examples/06-macro-micro-optimization/.bga/runs/20260821T170127Z/run"
node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")

# `UX-213`'s rule, applied from the start here: the committed fixture is
# never marked, so every guard below runs on a fresh clone.
_needs_real = pytest.mark.skipif(not os.path.isdir(REAL),
                                 reason="no real capture here")
RUNS = [
    pytest.param(GOLDEN, DIAGNOSIS_CHAIN_BOUND, id="committed"),
    pytest.param(SCHEDULED, DIAGNOSIS_SCHEDULER_BOUND, id="scheduler-bound"),
    pytest.param(REAL, DIAGNOSIS_CHAIN_BOUND, id="real-capture",
                 marks=_needs_real),
]


def _report(run=GOLDEN):
    from bga.cli import main

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        main(["analyze", run, "--format", "json"])
    return json.loads(buffer.getvalue())


def _text(run=GOLDEN):
    from bga.cli import main

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        main(["analyze", run])
    return buffer.getvalue()


def _render(payload, timeout=120):
    scratch = tempfile.mkdtemp()
    path = os.path.join(scratch, "payload.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle)
    try:
        result = subprocess.run(
            [node, "--input-type=module", "-e",
             _HARNESS % json.dumps(path)],
            capture_output=True, text=True, cwd=os.getcwd(), timeout=timeout)
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


class TestTheDiagnosisIsDecidedOnce:
    """It existed since `UX-65` as a local `bool` inside
    `compute_findings`, and reached the outside world only as the clause
    " - this build is chain-bound, not scheduler-bound" glued onto one
    finding's title. A consumer wanting to *branch* on it had to
    string-match a sentence."""

    @pytest.mark.parametrize("run,expected", RUNS)
    def test_the_payload_names_the_constraint(self, run, expected):
        headline = _report(run)["headline"]
        assert headline["diagnosis"] == expected
        assert headline["diagnosis"] in DIAGNOSES

    @pytest.mark.parametrize("run,expected", RUNS)
    def test_the_ratio_it_was_decided_by_is_published_too(self, run, expected):
        """Not just the verdict - the number, so a reader can see how
        close to the threshold this run sat."""
        headline = _report(run)["headline"]
        assert headline["chain_bound_share"] == CHAIN_BOUND_RATIO
        ratio = headline["chain_share"]
        if expected == DIAGNOSIS_CHAIN_BOUND:
            assert ratio >= CHAIN_BOUND_RATIO, ratio
        else:
            assert ratio < CHAIN_BOUND_RATIO, ratio

    @pytest.mark.parametrize("run,expected", RUNS)
    def test_the_ratio_is_the_published_floors_over_the_published_horizon(
            self, run, expected):
        """The one arithmetic claim, checked against its own inputs -
        so nobody can quietly change what the diagnosis is a ratio
        *of*.

        `UX-477`: the denominator is the **task horizon**, and every
        term of it is published - `total_duration_us` minus the two
        untracked spans the attribution already names. Recomputed from
        those three fields rather than read from one, so a change to
        the denominator has to change this line too."""
        payload = _report(run)
        attribution = payload["attribution"]
        horizon = (payload["total_duration_us"]
                   - attribution["untracked_head_us"]
                   - attribution["untracked_tail_us"])
        expected_ratio = payload["floors"]["t_infinity_observed"] / horizon
        assert payload["headline"]["chain_share"] == pytest.approx(expected_ratio)
        assert payload["headline"]["chain_share_of"] == "task_horizon"

    @pytest.mark.parametrize("run,expected", RUNS)
    def test_the_head_is_out_of_the_denominator(self, run, expected):
        """The defect `UX-477` is about, stated as its own clause: a
        share taken against wall-clock is a share against a span that
        carries BuildStream's startup, which the same report calls "not
        a scheduling issue". Where a run has a head at all, the two
        answers must differ - and if they ever agree on a run that has
        one, the subtraction has stopped happening."""
        payload = _report(run)
        head = payload["attribution"]["untracked_head_us"]
        tail = payload["attribution"]["untracked_tail_us"]
        against_wall = (payload["floors"]["t_infinity_observed"]
                        / payload["total_duration_us"])
        if head + tail == 0:
            assert payload["headline"]["chain_share"] == pytest.approx(against_wall)
        else:
            assert payload["headline"]["chain_share"] > against_wall, (
                head, tail, payload["headline"]["chain_share"], against_wall)

    def test_the_findings_read_the_same_decision(self):
        """`compute_findings` used to recompute the ratio itself. Two
        copies of one threshold is how the report and the headline come
        to disagree about a build."""
        import ast
        import inspect

        from bga import findings

        source = inspect.getsource(findings.compute_findings)
        tree = ast.parse(source.lstrip())
        calls = {n.func.id for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        assert "diagnose" in calls, (
            "compute_findings decides chain-boundness on its own again")
        assert "CHAIN_BOUND_RATIO" not in source, (
            "the threshold is compared in two places again")

    def test_a_run_with_no_durations_is_inconclusive_not_guessed(self):
        from bga.findings import diagnose

        class Empty:
            floors = {}
            total_duration_us = 0

        answer = diagnose(Empty())
        assert answer["diagnosis"] == DIAGNOSIS_INCONCLUSIVE
        assert answer["chain_share"] is None
        assert "did not record" in answer["sentence"]


class TestTheOpportunityIsPublishedNotSubtracted:
    @pytest.mark.parametrize("run,expected", RUNS)
    def test_the_scheduling_gap_is_a_field(self, run, expected):
        """The Required Fix's words: "not left as a subtraction for the
        page to do"."""
        payload = _report(run)
        gap = payload["headline"]["scheduling_gap_us"]
        assert gap == (payload["total_duration_us"]
                       - payload["floors"]["t_infinity_observed"])
        assert gap >= 0

    @pytest.mark.parametrize("run,expected", RUNS)
    def test_certified_headroom_comes_from_floors(self, run, expected):
        payload = _report(run)
        assert (payload["headline"]["certified_headroom_us"]
                == payload["floors"]["certified_headroom"])


class TestTheActionsAreReferencesNotCopies:
    @pytest.mark.parametrize("run,expected", RUNS)
    def test_every_action_names_a_finding_that_exists(self, run, expected):
        payload = _report(run)
        ids = {f["id"] for f in payload["findings"]}
        actions = payload["headline"]["top_actions"]
        assert actions, "nothing to do, on a run with findings"
        for action in actions:
            assert action["finding_id"] in ids, action

    @pytest.mark.parametrize("run,expected", RUNS)
    def test_the_actions_are_at_most_three(self, run, expected):
        """A decision, not a backlog - the rest of the ranking is a
        section away."""
        assert len(_report(run)["headline"]["top_actions"]) <= 3

    def test_a_chain_bound_run_ranks_by_realizable_saving(self):
        if not os.path.isdir(REAL):
            pytest.skip("no real capture here")
        actions = _report(REAL)["headline"]["top_actions"]
        savings = [a["saving_us"] for a in actions]
        assert savings == sorted(savings, reverse=True), savings
        assert all(a["finding_id"] == "time-concentration" for a in actions)

    def test_a_scheduler_bound_run_ranks_by_who_depends_on_it(self):
        """The other branch, and the reason it is a different question:
        blast radius answers "who depends on me", which matters when the
        graph is the constraint rather than the chain.

        Read on `SCHEDULED` rather than on the golden run since
        `UX-477` - the golden run's four back-to-back tasks are a chain,
        and only the startup in the old denominator made it look like
        anything else."""
        actions = _report(SCHEDULED)["headline"]["top_actions"]
        assert all(a["finding_id"] == "blast-radius-ranking" for a in actions)
        counts = [a["downstream_count"] for a in actions]
        assert counts == sorted(counts, reverse=True), counts

    def test_a_saving_nobody_projected_is_absent_rather_than_zero(self):
        for action in _report(SCHEDULED)["headline"]["top_actions"]:
            assert "saving_us" not in action, (
                "a zero saving claims a projection that was never made")


class TestOneVocabularyAcrossTheRenderers:
    @pytest.mark.parametrize("run,expected", RUNS)
    def test_the_text_report_prints_the_published_sentence(self, run, expected):
        """The acceptance: "The text renderer prints the same diagnosis
        sentence from the same field"."""
        payload = _report(run)
        assert payload["headline"]["sentence"] in _text(run)

    def test_the_schema_declares_the_block_and_its_enum(self):
        declared = schemas.schema(schemas.ANALYZE)["properties"]["headline"]
        assert declared["properties"]["diagnosis"]["enum"] == list(DIAGNOSES)
        assert declared["properties"]["scheduling_gap_us"]["bga:quantity"] \
            == "duration_us"

    def test_the_enum_is_the_tuple_the_pipeline_emits(self):
        """`UX-201`'s rule about closed sets: the published enum and the
        values produced are one object, not two lists that agree today."""
        import re

        source = open("bga/schemas.py", encoding="utf-8").read()
        assert "from .findings import DIAGNOSES" in source
        assert not re.search(r'"enum":\s*\[\s*"chain_bound"', source), (
            "the enum is spelled out again instead of imported")

    def test_headline_is_in_the_full_key_list(self):
        assert "headline" in schemas.ANALYZE_FULL_KEYS
        assert set(schemas.ANALYZE_FULL_KEYS) <= set(_report())


@needs_node
class TestThePanel:
    @pytest.mark.parametrize("run,expected", RUNS)
    def test_it_shows_the_published_diagnosis_and_actions(self, run, expected):
        payload = _report(run)
        out = _render(payload)
        assert out["decision"]["diagnosis"] == expected
        assert out["decision"]["sentence"] == payload["headline"]["sentence"]
        assert ([a["element"] for a in out["decision"]["actions"]]
                == [a["element_uid"] for a in payload["headline"]["top_actions"]])

    @pytest.mark.parametrize("run,expected", RUNS)
    def test_every_number_in_it_is_a_published_field(self, run, expected):
        """`UX-202`'s rule, extended to the panel: `data-raw` against the
        payload, no exceptions."""
        payload = _report(run)
        out = _render(payload)
        for key, raw in out["decision"]["values"].items():
            assert float(raw) == float(payload["headline"][key]), key
        for shown, published in zip(out["decision"]["actions"],
                                    payload["headline"]["top_actions"]):
            if shown["worth"] is None:
                continue
            field = shown["worth_field"]
            assert float(shown["worth"]) == float(published[field]), shown

    def test_it_reads_the_diagnosis_rather_than_deriving_it(self):
        """The discriminating case, built rather than assumed.

        Mutating the panel to recompute `t_infinity / total` did *not*
        redden anything at first - on both fixtures the recomputation
        agrees with the published answer, so a deriving page and a
        reading page are indistinguishable. They are only telling apart
        on a payload where the two disagree, which is what this is: the
        floors say 0.95 (chain-bound by any threshold) and the published
        diagnosis says `scheduler_bound`.

        A reading page shows what was published. A second analyzer
        overrules the pipeline - which is the whole failure mode
        Direction 7's rule exists to prevent, and it would ship silently
        without this fixture.
        """
        out = _render({
            "schema": schemas.ANALYZE,
            "total_duration_us": 1000,
            "floors": {"t_infinity_observed": 950, "certified_headroom": 0},
            "headline": {"diagnosis": DIAGNOSIS_SCHEDULER_BOUND,
                         "chain_share": 0.95, "chain_bound_share": 0.9,
                         "sentence": "The pipeline said scheduler-bound.",
                         "top_actions": []},
        })
        assert out["decision"]["diagnosis"] == DIAGNOSIS_SCHEDULER_BOUND, (
            "the page recomputed the diagnosis and overruled the pipeline")
        assert out["decision"]["sentence"] == "The pipeline said scheduler-bound."

    def test_no_headline_means_no_panel(self):
        """The acceptance's mutation: strip `headline` → panel absent,
        page otherwise intact."""
        payload = _report()
        payload.pop("headline")
        out = _render(payload)
        assert out["decision"] is None
        # Everything else still rendered - this is a missing panel, not
        # a broken page.
        assert out["overview"] is True

    def test_the_decision_comes_before_the_evidence(self):
        """"First screen = decision, everything else = evidence" - as
        DOM order, which is the only form of it a reader experiences."""
        out = _render(_report())
        order = out["order"]
        assert order.index("decision") < order.index("evidence"), order
        assert order.index("evidence") < order.index("overview"), order


@needs_node
class TestTheEvidenceHeaderCompresses:
    def test_it_leads_with_one_status_line(self):
        out = _render(_report())
        assert out["status_line"], "the header says nothing at a glance"
        assert "confidence" in out["status_line"]

    def test_the_numbers_move_behind_a_details(self):
        """Six rows at the top of a page for values that matter only
        when they are alarming."""
        out = _render(_report())
        assert out["evidence_dl_in_details"] is True

    def test_the_status_line_reads_the_published_band(self):
        """Not a threshold the page applies to `primary` itself - that
        would be the second copy of the thresholds `UX-202` removed."""
        line = _render({"schema": schemas.ANALYZE,
                        "confidence": {"primary": 0.87, "band": "low"}})
        assert "low confidence" in line["status_line"], line["status_line"]
        # 0.87 would read "high" to anyone applying a threshold here;
        # the published band says low, and the band wins.
        assert "high" not in line["status_line"]

    def test_a_run_with_no_plane_2_says_so_rather_than_staying_silent(self):
        line = _render(_report())
        assert "Plane 2 not captured" in line["status_line"]


@needs_node
class TestTheOverviewCompacts:
    def test_the_tail_folds_and_nothing_is_summed(self):
        """The house adjustment to the review's sketch: **no
        viewer-summed "Other" row.** A grouped figure would be a number
        the pipeline never published."""
        run = REAL if os.path.isdir(REAL) else GOLDEN
        payload = _report(run)
        out = _render(payload)
        assert out["overview_folded"] >= 0, out
        for field in out["bar_fields"]:
            # The property, not a prefix: every bar names a path that
            # *resolves in the payload*. A summed "Other" row could not -
            # which is precisely why this is the check.
            node = payload
            for part in field.split("."):
                assert part in node, (
                    f"{field} does not resolve in the payload - a bar the "
                    f"page invented is exactly what this forbids")
                node = node[part]
            assert isinstance(node, (int, float)), field

    def test_every_bar_still_names_the_field_it_read(self):
        out = _render(_report())
        assert out["bar_fields"], "the overview drew nothing"


_HARNESS = """
globalThis._makeNode ??= (await import(process.env.BGA_DOM_SHIM)).makeNode;

function make(tag) {
  const node = _makeNode(tag);
  return node;
}
globalThis.document = { createElement: make, createElementNS: (_n, t) => make(t),
                        getElementById: () => null };

const views = await import("./tests/viewer.mjs");
const { readFileSync } = await import("node:fs");
const payload = JSON.parse(readFileSync(%s, "utf8"));

const text = (n) => (n.textContent ?? "")
  + (n.children ?? []).map(text).join(" ");
function find(root, pred) {
  let hit = null;
  (function walk(n) { if (!n || hit) return;
    if (pred(n)) { hit = n; return; }
    (n.children ?? []).forEach(walk); })(root);
  return hit;
}
function all(root, pred) {
  const found = [];
  (function walk(n) { if (!n) return;
    if (pred(n)) found.push(n);
    (n.children ?? []).forEach(walk); })(root);
  return found;
}

const panel = views.renderDecision(payload);
let decision = null;
if (panel) {
  const values = {};
  // UX-227 put a "why this one" fold inside each action row, and its
  // rows carry `data-field` too - as *paths* into the payload rather
  // than as `headline.` keys. Those are checked against their own
  // paths in UX-227's file; what this asserts is the panel's own
  // headline numbers, so the fold is walked past rather than merged in.
  const inFold = new Set();
  for (const fold of all(panel, (n) => n.className === "why-ranked")) {
    (function mark(n) { if (!n) return; inFold.add(n);
      (n.children ?? []).forEach(mark); })(fold);
  }
  for (const dd of all(panel, (n) => n.tagName === "dd"
                                    && n.attrs["data-field"]
                                    && !inFold.has(n))) {
    values[dd.attrs["data-field"].replace("headline.", "")] = dd.attrs["data-raw"];
  }
  decision = {
    diagnosis: panel.attrs["data-diagnosis"],
    sentence: (find(panel, (n) => n.className === "diagnosis") ?? {}).textContent,
    values,
    actions: all(panel, (n) => n.className === "action").map((n) => {
      const worth = find(n, (x) => (x.className ?? "").startsWith("worth"));
      return { element: n.attrs["data-element"],
               finding: n.attrs["data-finding"],
               worth: worth ? worth.attrs["data-raw"] : null,
               worth_field: worth ? worth.attrs["data-field"] : null };
    }),
  };
}

const evidence = views.renderEvidence(payload);
const overview = views.renderOverview(payload);
const status = evidence && find(evidence, (n) => n.className === "status-line");
const fold = evidence && find(evidence, (n) => n.tagName === "details");
const tail = overview && find(overview, (n) => n.className === "overview-tail");

console.log(JSON.stringify({
  decision,
  overview: Boolean(overview),
  order: [panel && "decision", evidence && "evidence", overview && "overview"]
    .filter(Boolean),
  status_line: status ? status.textContent : "",
  evidence_dl_in_details: Boolean(fold && find(fold, (n) => n.tagName === "dl")),
  overview_folded: tail ? Number(tail.attrs["data-folded"]) : 0,
  bar_fields: overview
    ? all(overview, (n) => n.className === "wf-row")
        .map((n) => n.attrs["data-field"]) : [],
}));
"""


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
