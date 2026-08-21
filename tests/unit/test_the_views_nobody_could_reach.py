"""UX-203: the views that were guarded, green, and unreachable.

Round 22's verification of the viewer landing found three gaps that no
log carried. All three were reproduced before anything was changed:

1. `renderBand(analyze)` returns **null** for every real report - the
   function needs `baseline_band` and `candidate.total_duration_us`,
   which only a *compare* document has, and `bga view` served only the
   analyze document. `UX-196`'s headline view had never rendered
   outside its own harness.
2. The trend's y-axis was `r.bytes`, so "is this project drifting" was
   answered by disk usage. No test asserted what the axis plotted -
   the guard described the drawing without checking what was drawn.
3. CI's packaging job ran `--help` for every alias and never served a
   page, so the class that shipped "broken in every installed shape"
   was guarded by assertions about configuration.

   Ground-truthing the filing's proposed mutation for (3) refuted it:
   emptying `package-data`'s `bga` entry - with `build/` cleared, and
   even with `include-package-data = false` - still ships all seven
   viewer files, because this setuptools includes files under a package
   directory anyway. The step is falsified against a mutation that
   *does* break an installed viewer: the checkout-relative `ASSET_DIR`,
   which is one of the three defects that actually shipped.

What is guarded here is reachability, not arithmetic - the drawings
themselves are `UX-196`'s and already tested.
"""
import json
import os
import shutil
import subprocess

import pytest

from bga import schemas

GOLDEN = "tests/fixtures/golden/mixed_task_kinds"
node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")


def _store(tmp_path, count):
    """A project whose store holds `count` analysable snapshots."""
    (tmp_path / "project.conf").write_text("name: p\nmin-version: 2.0\n")
    stamps = [f"2026010{n}T000000Z" for n in range(1, count + 1)]
    for stamp in stamps:
        run = tmp_path / ".bga" / "runs" / stamp / "run"
        run.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(GOLDEN, run)
        os.remove(run / "expected_output.json")
    return tmp_path, [str(tmp_path / ".bga" / "runs" / s / "run") for s in stamps]


class TestTheBandIsReachable:
    def test_a_compare_document_is_served(self, tmp_path):
        from tools.bga_view import payloads

        _, runs = _store(tmp_path, 2)
        served = payloads(runs[-1])
        assert "compare.json" in served, (
            "only the analyze document is served, so renderBand has "
            "nothing to draw from - the reported gap")
        assert served["compare.json"]["schema"] == schemas.COMPARE

    def test_the_document_carries_a_band_when_the_store_can_supply_one(
            self, tmp_path):
        """Serving *a* comparison is not enough, and this is the subtler
        half: a pairwise compare has no `baseline_band` at all, because
        a band needs `compare.MIN_BASELINE_RUNS` samples. The store is
        where they come from."""
        from bga.compare import MIN_BASELINE_RUNS
        from tools.bga_view import payloads

        _, runs = _store(tmp_path, MIN_BASELINE_RUNS + 2)
        compare = payloads(runs[-1])["compare.json"]
        assert compare["baseline_band"], (
            "no band, so renderBand still returns null - serving the "
            "comparison alone would have fixed nothing visible")

    def test_a_store_too_small_for_a_band_says_so_instead(self, tmp_path):
        """Not an error and not a blank: `baseline_band_shortfall` is
        the answer, and it names what is missing."""
        from tools.bga_view import payloads

        _, runs = _store(tmp_path, 2)
        compare = payloads(runs[-1])["compare.json"]
        assert compare["baseline_band"] is None
        assert compare["baseline_band_shortfall"], compare.get("verdict")

    def test_the_first_run_in_a_store_has_nothing_to_compare_against(
            self, tmp_path):
        from tools.bga_view import payloads

        _, runs = _store(tmp_path, 3)
        assert "compare.json" not in payloads(runs[0])

    def test_an_explicit_baseline_wins(self, tmp_path):
        from tools.bga_view import payloads

        _, runs = _store(tmp_path, 3)
        served = payloads(runs[-1], baseline=runs[0])
        assert served["compare.json"]["baseline_run_id"] is not None

    @needs_node
    def test_render_band_finally_returns_a_drawing(self, tmp_path):
        """The whole point, end to end: the payload `bga view` really
        serves, through the renderer that really ships."""
        from bga.compare import MIN_BASELINE_RUNS
        from tools.bga_view import payloads

        _, runs = _store(tmp_path, MIN_BASELINE_RUNS + 2)
        compare = payloads(runs[-1])["compare.json"]

        out = _render("renderBand", compare)
        assert out["rendered"], (
            "renderBand still returns null for what the server serves")
        assert out["attrs"]["data-where"]

    @needs_node
    def test_it_still_returns_nothing_for_an_analyze_document(self, tmp_path):
        """The original defect, pinned: handing it the report is what
        the page used to do, and it must stay visibly wrong rather than
        drawing something meaningless."""
        from tools.bga_view import payloads

        _, runs = _store(tmp_path, 2)
        out = _render("renderBand", payloads(runs[-1])["report.json"])
        assert not out["rendered"]

    def test_the_page_asks_for_the_compare_document(self):
        source = open("bga/viewer/app.js", encoding="utf-8").read()
        assert 'load("compare"' in source, (
            "the page never fetches it, so serving it changes nothing")
        assert "renderBand(payload)" not in source, (
            "renderBand is being handed the analyze document again")


class TestTheTrendPlotsWhatItPromised:
    def test_the_store_rows_carry_duration(self, tmp_path):
        from tools.bga_snapshot import store_listing

        project, _ = _store(tmp_path, 3)
        rows = store_listing(str(project))["snapshots"]
        assert all(r["total_duration_us"] is not None for r in rows), rows

    def test_the_rows_carry_a_verdict_once_a_band_exists(self, tmp_path):
        from bga.compare import MIN_BASELINE_RUNS
        from tools.bga_snapshot import store_listing

        project, _ = _store(tmp_path, MIN_BASELINE_RUNS + 2)
        rows = store_listing(str(project))["snapshots"]
        assert rows[0]["verdict_kind"] is None, "nothing to judge the first against"
        assert rows[-1]["verdict_kind"] in ("improved", "regressed", "within_band")

    def test_an_incomplete_run_gets_no_verdict(self, tmp_path):
        """`UX-156`/`157`/`185`: a run that did not finish is not a
        measurement, so it cannot be inside or outside anything."""
        from tools.bga_snapshot import _mark_verdicts

        rows = [{"total_duration_us": 10, "incomplete_reason": None},
                {"total_duration_us": 10, "incomplete_reason": None},
                {"total_duration_us": 10, "incomplete_reason": None},
                {"total_duration_us": 999, "incomplete_reason": "interrupted"}]
        _mark_verdicts(rows)
        assert rows[-1]["verdict_kind"] is None

    def test_the_cache_hit_rate_comes_from_the_build_queue(self, tmp_path):
        from tools.bga_snapshot import _run_measurements

        snapshot = tmp_path / "snap"
        run = snapshot / "run"
        shutil.copytree(GOLDEN, run)
        context = json.loads((run / "run-context.json").read_text())
        context["queue_summary"] = {"build": {"processed": 3, "skipped": 7,
                                              "failed": 0}}
        (run / "run-context.json").write_text(json.dumps(context))
        assert _run_measurements(str(snapshot))["cache_hit_rate"] == 0.7

    def test_a_capture_with_no_queue_summary_says_nothing(self, tmp_path):
        from tools.bga_snapshot import _run_measurements

        snapshot = tmp_path / "snap"
        shutil.copytree(GOLDEN, snapshot / "run")
        assert "cache_hit_rate" not in _run_measurements(str(snapshot))

    def test_the_schema_puts_duration_before_size(self):
        columns = schemas.schema(schemas.STORE)["properties"]["snapshots"][
            schemas.COLUMNS]
        assert columns.index("total_duration_us") < columns.index("bytes"), (
            "size is still leading the row, which is the narrowing")

    @needs_node
    def test_the_y_axis_is_duration_not_size(self, tmp_path):
        """The guard that was missing. The old tests asserted that a
        trend was drawn and never what it plotted, which is how the
        narrowing survived a round.

        Discriminating by construction: duration and size move in
        *opposite* directions across these rows, so a chart of one is
        upside down against a chart of the other.
        """
        rows = [
            {"stamp": "a", "bytes": 300, "total_duration_us": 100,
             "alias": None, "incomplete_reason": None, "verdict_kind": None,
             "cache_hit_rate": None},
            {"stamp": "b", "bytes": 200, "total_duration_us": 200,
             "alias": None, "incomplete_reason": None, "verdict_kind": None,
             "cache_hit_rate": None},
            {"stamp": "c", "bytes": 100, "total_duration_us": 300,
             "alias": "@last", "incomplete_reason": None,
             "verdict_kind": "regressed", "cache_hit_rate": 0.5},
        ]
        out = _render("renderTrend", {"schema": schemas.STORE, "project": "/p",
                                      "count": 3, "total_bytes": 600,
                                      "snapshots": rows})
        ys = [float(p["cy"]) for p in out["points"] if "cy" in p]
        assert len(ys) == 3, out
        # y grows downward, so a rising duration means a falling y.
        assert ys[0] > ys[1] > ys[2], (
            f"y went {ys} - the axis is following size, not duration")

    @needs_node
    def test_the_verdict_colours_the_point(self, tmp_path):
        rows = [{"stamp": s, "bytes": 1, "total_duration_us": d, "alias": None,
                 "incomplete_reason": None, "verdict_kind": v,
                 "cache_hit_rate": None}
                for s, d, v in (("a", 10, None), ("b", 20, "regressed"))]
        out = _render("renderTrend", {"schema": schemas.STORE, "project": "/p",
                                      "count": 2, "total_bytes": 2,
                                      "snapshots": rows})
        assert any("verdict-regressed" in (p.get("class") or "")
                   for p in out["points"]), out["points"]

    @needs_node
    def test_size_survives_in_the_tooltip(self, tmp_path):
        """Demoted, not deleted: the store warning is about disk, and
        the number should still be reachable."""
        rows = [{"stamp": "a", "bytes": 5 * 1024 * 1024,
                 "total_duration_us": 10, "alias": None,
                 "incomplete_reason": None, "verdict_kind": None,
                 "cache_hit_rate": None},
                {"stamp": "b", "bytes": 1024, "total_duration_us": 20,
                 "alias": None, "incomplete_reason": None,
                 "verdict_kind": None, "cache_hit_rate": None}]
        out = _render("renderTrend", {"schema": schemas.STORE, "project": "/p",
                                      "count": 2, "total_bytes": 1,
                                      "snapshots": rows})
        assert "5.0 MiB" in out["text"], out["text"]


class TestCiRunsTheInstalledViewer:
    def test_the_packaging_job_serves_a_page_from_the_wheel(self):
        import yaml

        workflow = yaml.safe_load(open(".github/workflows/ci.yml",
                                       encoding="utf-8"))
        job = workflow["jobs"]["packaging"]
        steps = "\n".join(str(step.get("run", "")) for step in job["steps"])
        assert "bga view" in steps, (
            "the packaging loop stops at --help, so no CI step ever serves "
            "an asset from an installed wheel - which is the exact class "
            "that shipped broken")
        for wanted in ("report.json", "app.js"):
            assert wanted in steps, f"the job never fetches {wanted}"


def _render(fn, payload):
    script = _HARNESS % (fn, json.dumps(payload))
    result = subprocess.run([node, "--input-type=module", "-e", script],
                            capture_output=True, text=True, cwd=os.getcwd(),
                            timeout=60)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


# Enough SVG-aware DOM to run the real renderers.
_HARNESS = """
function make(tag) {
  return {
    tagName: tag, nodeType: 1, attrs: {}, children: [], textContent: "",
    className: "",
    setAttribute(k, v) { this.attrs[k] = String(v); },
    getAttribute(k) { return this.attrs[k] ?? null; },
    append(...xs) {
      for (const x of xs) {
        if (x === null || x === undefined) continue;
        if (typeof x === "string") this.textContent += x;
        else this.children.push(x);
      }
    },
    addEventListener() {}, querySelector() { return null; },
    querySelectorAll() { return []; },
  };
}
globalThis.document = { createElement: make, createElementNS: (_ns, t) => make(t) };

const views = await import("./bga/viewer/views.js");
const node = views["%s"](%s);

const points = [];
let text = "";
(function walk(n) {
  if (!n) return;
  text += " " + (n.textContent ?? "");
  if (n.className) n.attrs.class = n.attrs.class ?? n.className;
  if ((n.attrs.class ?? "").includes("trend-point")) points.push(n.attrs);
  (n.children ?? []).forEach(walk);
})(node);

const firstWithWhere = (function find(n) {
  if (!n) return null;
  if (n.attrs && n.attrs["data-where"]) return n.attrs;
  for (const c of (n.children ?? [])) { const r = find(c); if (r) return r; }
  return null;
})(node);

console.log(JSON.stringify({
  rendered: Boolean(node), points, text, attrs: firstWithWhere ?? {},
}));
"""


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
