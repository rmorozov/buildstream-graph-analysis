"""UX-202: "why is my build slow", answered at the top.

Two pieces, and one rule holding both together: **no viewer
arithmetic.** Every number the overview shows is read from a published
field. A gap the JSON does not carry enters `analyze/v1` first, where
the text renderer, CI and every external consumer get it too — which is
Direction 7's rule, and what makes the waterfall a *reading* of the
report rather than a second opinion about it.

Two fields entered the payload for this, both additive (`UX-190`'s
rule, so no version bump): `confidence.band` — already derived by
`findings.py` for its own headline, and a viewer computing "is 0.87
high?" would be a second copy of the thresholds — and
`run_instance.incomplete_reason`, the one `UX-185` accessor published
rather than left for a consumer to re-derive from `build_outcome`.
"""
import contextlib
import io
import json
import os
import re
import shutil
import subprocess

import pytest

from bga import schemas

GOLDEN = "tests/fixtures/golden/mixed_task_kinds"
REAL = "examples/06-macro-micro-optimization/.bga/runs/20260821T170127Z/run"
node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")


def _report(run=GOLDEN):
    from bga.cli import main

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        main(["analyze", run, "--format", "json"])
    return json.loads(buffer.getvalue())


def _render(fn, payload):
    script = _HARNESS % (fn, json.dumps(payload))
    result = subprocess.run([node, "--input-type=module", "-e", script],
                            capture_output=True, text=True, cwd=os.getcwd(),
                            timeout=60)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def _dig(payload, path):
    """`attribution.idle_us` -> the value, or KeyError."""
    node_ = payload
    for part in path.split("."):
        node_ = node_[part]
    return node_


@needs_node
class TestTheOverviewReadsRatherThanComputes:
    """The acceptance's centrepiece: every rendered number equals a
    field in `report.json`, byte for byte."""

    @pytest.mark.parametrize("run", [GOLDEN,
                                     pytest.param(REAL, marks=pytest.mark.skipif(
                                         not os.path.isdir(REAL),
                                         reason="no real capture in this tree"))])
    def test_every_number_is_a_published_field(self, run):
        payload = _report(run)
        out = _render("renderOverview", payload)
        assert out["bars"], "the overview rendered nothing"
        for bar in out["bars"]:
            field = bar["field"]
            assert field, bar
            published = _dig(payload, field)
            assert float(bar["raw"]) == float(published), (
                f"{field}: rendered {bar['raw']}, payload says {published}")

    def test_it_shows_the_total_and_the_gaps_and_the_floors(self):
        out = _render("renderOverview", _report())
        fields = {bar["field"] for bar in out["bars"]}
        assert "total_duration_us" in fields
        assert any(f.startswith("attribution.") for f in fields), fields
        assert any(f.startswith("floors.") for f in fields), fields

    def test_each_segment_points_at_the_section_that_explains_it(self):
        out = _render("renderOverview", _report())
        for bar in out["bars"]:
            if bar["field"].startswith("attribution."):
                assert bar["link"] == "attribution", bar
            if bar["field"].startswith("floors."):
                assert bar["link"] == "floors", bar

    def test_a_payload_without_attribution_renders_nothing(self):
        """Rather than an overview of one bar that implies the rest is
        zero."""
        out = _render("renderOverview",
                      {"schema": schemas.ANALYZE, "total_duration_us": 10})
        assert out["rendered"] is False


@needs_node
class TestTheEvidenceHeader:
    def test_it_states_what_the_capture_supports(self):
        out = _render("renderEvidence", _report())
        fields = {row["field"] for row in out["rows"]}
        assert "confidence.primary" in fields, fields

    def test_the_band_comes_from_the_payload_not_from_a_threshold_here(self):
        payload = _report()
        assert payload["confidence"]["band"], "the payload carries no band"
        out = _render("renderEvidence", payload)
        shown = [r for r in out["rows"] if r["field"] == "confidence.primary"][0]
        assert payload["confidence"]["band"] in shown["value"], shown

    @pytest.mark.parametrize("reason", ["failed", "interrupted", "suspended"])
    def test_each_incompleteness_gets_the_banner(self, reason):
        """`UX-207`: from `renderVerdict`, now the only place a refusal
        is drawn."""
        payload = _report()
        payload["run_instance"]["incomplete_reason"] = reason
        out = _render("renderVerdict", payload)
        assert out["incomplete"] == reason, out
        assert out["banner"], "the run says nothing about not being a measurement"

    @pytest.mark.parametrize("reason", ["failed", "interrupted", "suspended"])
    def test_the_refusal_is_drawn_exactly_once(self, reason):
        """`UX-207`'s named defect: the same claim rendered twice, once
        by `renderVerdict` and once by `renderEvidence`, in different
        words. Measured at two `data-incomplete` nodes on an interrupted
        fixture before this."""
        payload = _report()
        payload["run_instance"]["incomplete_reason"] = reason
        banners = (_render("renderVerdict", payload)["incomplete_count"]
                   + _render("renderEvidence", payload)["incomplete_count"])
        assert banners == 1, (
            f"{banners} refusal banners for one run - a reader meets the "
            f"same sentence twice and wonders which is the answer")

    def test_plane2_coverage_is_stated_when_plane_2_was_there(self):
        """The Required Fix asks for `stream_coverage` in this header.
        It lives in the Plane 2 report, so it had to reach `analyze/v1`
        first - the same additive route the band took."""
        payload = _report()
        payload["plane2_coverage"] = {"processes": 813, "opens_coverage": 1.0}
        out = _render("renderEvidence", payload)
        shown = [r for r in out["rows"]
                 if r["field"] == "plane2_coverage.processes"]
        assert shown, out["rows"]
        assert "813" in shown[0]["value"], shown

    def test_no_plane_2_report_means_no_coverage_row(self):
        """Rather than a 0% row, which claims the hook saw nothing when
        the truth is that nobody looked."""
        out = _render("renderEvidence", _report())
        assert not [r for r in out["rows"]
                    if r["field"].startswith("plane2_coverage")]

    def test_a_finished_run_gets_no_banner(self):
        out = _render("renderVerdict", _report())
        assert out["incomplete"] is None
        assert not out["banner"]

    def test_every_reason_python_can_publish_has_a_sentence_here(self):
        """`incomplete_reason` is `UX-185`'s one accessor so a consumer
        cannot handle one reason and forget the others. This page is a
        consumer: a fourth reason added there without a sentence here
        would render `This run is <reason>.` and explain nothing."""
        import ast
        import inspect

        from bga.ingest.models import RunContext

        import textwrap

        tree = ast.parse(textwrap.dedent(
            inspect.getsource(RunContext.incomplete_reason.fget)))
        published = {n.value.value for n in ast.walk(tree)
                     if isinstance(n, ast.Return)
                     and isinstance(n.value, ast.Constant)
                     and isinstance(n.value.value, str)}
        assert published, "could not read the reasons out of the accessor"

        source = open("bga/viewer/views.js").read()
        block = source.split("export const INCOMPLETE = {", 1)[1].split("};", 1)[0]
        described = set(re.findall(r"^\s*(\w+):", block, re.M))
        assert published <= described, (
            f"published but never explained on the page: {published - described}")

    def test_the_three_sentences_agree_with_the_python_side(self):
        out = _render("renderVerdict", {
            "schema": schemas.ANALYZE,
            "run_instance": {"incomplete_reason": "suspended"},
            "confidence": {"primary": 0.9},
        })
        from bga import suspend

        # Not a string compare of the whole sentence - the CLI's carries
        # a measured duration this page does not have - but the claim
        # both make must be the same one.
        assert "not measurements" in out["banner"]
        assert "not measurements" in suspend.describe({"suspended_seconds": 900})


class TestTheTwoFieldsEnteredTheSchema:
    def test_confidence_band_is_published_and_declared(self):
        payload = _report()
        assert payload["confidence"]["band"] in ("high", "medium", "low")
        declared = schemas.schema(schemas.ANALYZE)["properties"]["confidence"]
        assert "band" in declared["properties"]

    def test_the_band_is_the_one_findings_uses(self):
        """A second copy of the thresholds is the defect this avoids."""
        from bga.findings import confidence_band

        payload = _report()
        assert payload["confidence"]["band"] == \
            confidence_band(payload["confidence"]["primary"])

    def test_plane2_coverage_is_published_and_declared(self, tmp_path):
        """Through `bga view`, which finds the sibling report the store
        wrote beside the run.

        `UX-213`: this used to run only where the real capture lived, so
        the whole Plane 2 half of the evidence header was guarded on one
        machine. The store's *shape* is what matters here - a `run/`
        directory with `plane2.json` beside it - and that is cheap to
        build, so the guard now assembles one from the golden fixture
        rather than waiting for a 595 KB capture nobody committed.
        """
        from tools.bga_view import payloads

        snapshot = tmp_path / "20260101T000000Z"
        shutil.copytree(GOLDEN, snapshot / "run")
        (snapshot / "plane2.json").write_text(json.dumps({
            "by_element": {},
            "stream_coverage": {"processes": 7, "opens_coverage": 1.0,
                                "by_coverage": {"hook-only": 7},
                                "cpu_disagreement_count": 0},
        }))

        served = payloads(str(snapshot / "run"))["report.json"]
        coverage = served.get("plane2_coverage")
        assert coverage, "bga view served no Plane 2 coverage for a run that has one"
        assert coverage["processes"] == 7
        assert "plane2_coverage" in schemas.schema(schemas.ANALYZE)["properties"]

    @pytest.mark.skipif(not os.path.isdir(REAL), reason="no real capture here")
    def test_plane2_coverage_on_the_real_capture(self):
        """The same property against a capture with 813 real processes,
        where one exists. Extra coverage, never the only coverage."""
        from tools.bga_view import payloads

        coverage = payloads(REAL)["report.json"].get("plane2_coverage")
        assert coverage and coverage["processes"] > 0

    def test_a_run_without_plane_2_publishes_no_coverage(self):
        assert "plane2_coverage" not in _report(), (
            "absence is the claim: 'not looked at' is not 'looked at and "
            "saw nothing'")

    def test_incomplete_reason_is_published_when_there_is_one(self, tmp_path):
        run = tmp_path / "run"
        shutil.copytree(GOLDEN, run)
        os.remove(run / "expected_output.json")
        context = json.loads((run / "run-context.json").read_text())
        context["build_outcome"] = {"interrupted": True}
        (run / "run-context.json").write_text(json.dumps(context))

        payload = _report(str(run))
        assert payload["run_instance"]["incomplete_reason"] == "interrupted"

    def test_a_finished_run_publishes_no_reason(self):
        assert "incomplete_reason" not in _report()["run_instance"], (
            "absence is the claim; a key saying 'None' is a different one")


_HARNESS = r"""
function make(tag) {
  return {
    tagName: tag, nodeType: 1, attrs: {}, children: [], textContent: "",
    className: "",
    setAttribute(k, v) { this.attrs[k] = String(v); },
    getAttribute(k) { return this.attrs[k] ?? null; },
    append(...xs) { for (const x of xs) { if (x == null) continue;
      typeof x === "string" ? this.textContent += x : this.children.push(x); } },
  };
}
// `app.js` boots itself when `#report` exists; it must not here.
globalThis.document = { createElement: make, createElementNS: (_n, t) => make(t),
                        getElementById: () => null };

const views = await import("./bga/viewer/views.js");
const app = await import("./bga/viewer/app.js");
// `UX-207` moved the refusal banner out of the evidence header and into
// `renderVerdict`, which returns a *list* of banners - so the harness
// drives either module, and the banner *count* is what one of these
// tests is now about.
const name = "%s";
const payload = %s;
const produced = name === "renderVerdict"
  ? app.renderVerdict(payload) : [views[name](payload)];
const node = produced.length === 1
  ? produced[0] : { children: produced.filter(Boolean) };

const bars = [], rows = [];
let incomplete = null, banner = "", incompleteCount = 0;
(function walk(n) {
  if (!n) return;
  const classes = (x) => String(x.className ?? "").split(/\s+/);
  if (classes(n).includes("wf-row")) {
    const value = (function find(x) {
      if (classes(x).includes("wf-value")) return x;
      for (const c of x.children) { const r = find(c); if (r) return r; }
      return null;
    })(n);
    bars.push({ field: n.attrs["data-field"] ?? null,
                link: n.attrs["data-section-link"] ?? null,
                raw: value ? value.attrs["data-raw"] : null });
  }
  if (n.attrs && n.tagName === "dd" && n.attrs["data-field"]) {
    rows.push({ field: n.attrs["data-field"], value: n.textContent });
  }
  if (n.attrs && n.attrs["data-incomplete"]) {
    incomplete = n.attrs["data-incomplete"];
    // The sentence lives in a child `<p>` now, not on the banner node
    // itself, so the text is gathered from the subtree. Reading only
    // `n.textContent` reported an empty banner for a banner that was
    // rendering perfectly well.
    banner = (function text(x) {
      return (x.textContent ?? "")
        + (x.children ?? []).map(text).join(" ");
    })(n).trim();
    incompleteCount += 1;
  }
  (n.children ?? []).forEach(walk);
})(node);

console.log(JSON.stringify({
  rendered: Boolean(node), bars, rows, incomplete, banner,
  incomplete_count: incompleteCount,
}));
"""


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
