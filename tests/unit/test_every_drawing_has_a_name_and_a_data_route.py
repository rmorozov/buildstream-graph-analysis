"""UX-1017 (styleguide §6e.9, Rule 9): every drawing has an accessible
name and a route to its numbers.

Measured on `main` at `98ab850`, booted (Chromium, both fixtures):
20 of 23 `svg[role=img]` on `macro_micro` and 8 of 11 on `golden` carried
neither `aria-label` nor a `<title>` - a screen reader hears "image" for
a density strip or a sparkline, and nothing names the numbers it drew.

`nameDrawing` (`drawings.js`) is the one place a drawing's name and
route are set, from both grades' own sentence: `aria-label` is the
sentence a sighted reader already gets, and `aria-details` points at the
node that carries every mark that sentence names - the table twin where
one is drawn (exhibit grade), the sentence span itself otherwise. The
two composed figures `views.js` draws directly (the compare band, the
store trend) always carry a twin, so their route is always it.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))
from pages import snapshot_copy

node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")
VIEWER = REPO / "bga" / "viewer"
SHIM = str(REPO / "tests" / "dom_shim.mjs")


def _js(body):
    source = (
        """
globalThis._makeNode ??= (await import(process.env.BGA_DOM_SHIM)).makeNode;
globalThis._installDocument ??= (await import(process.env.BGA_DOM_SHIM)).installDocument;
_installDocument();
globalThis.document.createElementNS = (ns, tag) => globalThis.document.createElement(tag);
const all = (n, pred, out = []) => {
  if (pred(n)) out.push(n);
  for (const c of n.children ?? []) all(c, pred, out);
  return out;
};
const text = (n) => !n ? "" : ((n.children ?? []).length
  ? (n._text ?? "") + n.children.map(text).join("") : (n._text ?? ""));
"""
        + body
    )
    result = subprocess.run(
        [node, "--input-type=module", "-e", source],
        capture_output=True,
        text=True,
        cwd=REPO,
        timeout=90,
        env=dict(os.environ, BGA_DOM_SHIM=SHIM),
    )
    return result


def _ok(body):
    result = _js(body)
    assert result.returncode == 0, result.stderr[-3000:]
    return json.loads(result.stdout)


#: A drawing's own claim: the `svg[role=img]`'s `aria-label` equals the
#: sentence beside it, and `aria-details` resolves to a node **inside
#: the same block** carrying every mark the sentence names.
_READ_NAME_AND_ROUTE = r"""
const svg = all(block, (n) => n.attrs.role === "img")[0];
const sentence = all(block, (n) => n.attrs["data-role"] === "density-sentence"
                                 || n.attrs["data-role"] === "series-sentence")[0];
const route = all(block, (n) => n.attrs.id === svg.attrs["aria-details"])[0];
console.log(JSON.stringify({
  label: svg.attrs["aria-label"] ?? null,
  sentenceText: sentence ? text(sentence) : null,
  routeFound: Boolean(route),
  routeIsTwin: Boolean(route && all(route, (n) => n.attrs["data-role"] === "drawing-twin").length),
}));
"""


@needs_node
class TestEveryDrawingsBuilderNamesAndRoutesIt:
    """One call per shape, both grades - `drawings.js`'s five builders."""

    @pytest.mark.parametrize(
        "call,grade",
        [
            ('sparkline([4, 1, 9, 3, 7], { unit: "level", grade: "GRADE" })', "annotation"),
            ('sparkline([4, 1, 9, 3, 7], { unit: "level", grade: "GRADE" })', "exhibit"),
            ('strip({ n: 11, min: 0, max: 100, deciles: { p50: 25 }, p95: 90 }, { grade: "GRADE" })', "annotation"),
            ('strip({ n: 11, min: 0, max: 100, deciles: { p50: 25 }, p95: 90 }, { grade: "GRADE" })', "exhibit"),
            ('columnStrip([3, 1, 9, 4, 2, 8, 5], { grade: "GRADE" })', "annotation"),
            (
                'decomposition([{ key: "a", label: "a", value: 3 }, '
                '{ key: "b", label: "b", value: 1 }], '
                '{ total: 4, grade: "GRADE" })',
                "annotation",
            ),
            (
                'decomposition([{ key: "a", label: "a", value: 3 }, '
                '{ key: "b", label: "b", value: 1 }], '
                '{ total: 4, grade: "GRADE" })',
                "exhibit",
            ),
            (
                'interval([{ key: "a", label: "a", value: 0.3 }, '
                '{ key: "b", label: "b", value: 0.8 }], { grade: "GRADE" })',
                "annotation",
            ),
            (
                'interval([{ key: "a", label: "a", value: 0.3 }, '
                '{ key: "b", label: "b", value: 0.8 }], { grade: "GRADE" })',
                "exhibit",
            ),
        ],
    )
    def test_the_name_is_the_sentence_and_the_route_resolves(self, call, grade):
        out = _ok(f"""
const mod = await import("./bga/viewer/drawings.js");
const block = mod.{call.replace("GRADE", grade)};
{_READ_NAME_AND_ROUTE}
""")
        assert out["label"], (call, grade, out)
        assert out["label"] == out["sentenceText"], (call, grade, out)
        assert out["routeFound"], (call, grade, out)
        assert out["routeIsTwin"] == (grade == "exhibit"), (call, grade, out)


#: Review #295: an ID resolving is not every plotted value being
#: reachable through it. `svg`'s own `data-value`/`data-values`
#: attributes are the drawn marks (`UX-213`'s rule: a guard reads what
#: was drawn, never a second computation of it); every one of them must
#: turn up in the route's accessible text - `aria-label` where the
#: route carries one (never counted words, `UX-360`), its rendered text
#: otherwise (a table twin).
_READ_VALUE_COVERAGE = r"""
const svg = all(block, (n) => n.attrs.role === "img")[0];
const route = all(block, (n) => n.attrs.id === svg.attrs["aria-details"])[0];
const routeText = (route.attrs["aria-label"] ?? "") + " " + text(route);
const values = new Set();
if (svg.attrs["data-values"]) {
  for (const v of svg.attrs["data-values"].split(",")) values.add(v);
}
for (const n of all(svg, () => true)) {
  if (n.attrs && n.attrs["data-value"] !== undefined) values.add(n.attrs["data-value"]);
  if (n.attrs && n.attrs["data-raw"] !== undefined) values.add(n.attrs["data-raw"]);
}
console.log(JSON.stringify({
  values: [...values],
  missing: [...values].filter((v) => !routeText.includes(v)),
  routeText,
}));
"""


@needs_node
class TestEveryPlottedValueReachesTheRoute:
    """Review #295's finding, generalised past the sparkline it named:
    `sparkline` and `strip` both draw more marks than their sentence
    keeps (`stripTicks` drops labels that would collide), so the route
    has to carry the full set even where the sentence does not."""

    @pytest.mark.parametrize(
        "call,grade",
        [
            ('sparkline([4, 1, 9, 3, 7], { unit: "level", grade: "GRADE" })', "annotation"),
            ('sparkline([4, 1, 9, 3, 7], { unit: "level", grade: "GRADE" })', "exhibit"),
            # A payload with nine deciles present: `stripTicks` keeps only
            # the labels that fit, so the sentence (built from `labelled`)
            # drops several of them even though `stripSvg` still ticks them.
            (
                'strip({ n: 11, min: 0, max: 100, '
                'deciles: { p10: 5, p20: 12, p30: 18, p40: 22, p50: 25, p60: 40, '
                'p70: 55, p80: 70, p90: 85 }, p95: 90, p99: 97 }, '
                '{ grade: "GRADE" })',
                "annotation",
            ),
            (
                'strip({ n: 11, min: 0, max: 100, '
                'deciles: { p10: 5, p20: 12, p30: 18, p40: 22, p50: 25, p60: 40, '
                'p70: 55, p80: 70, p90: 85 }, p95: 90, p99: 97 }, '
                '{ grade: "GRADE" })',
                "exhibit",
            ),
            (
                'decomposition([{ key: "a", label: "a", value: 3 }, '
                '{ key: "b", label: "b", value: 1 }], '
                '{ total: 4, grade: "GRADE" })',
                "annotation",
            ),
            (
                'interval([{ key: "a", label: "a", value: 0.3 }, '
                '{ key: "b", label: "b", value: 0.8 }], { grade: "GRADE" })',
                "annotation",
            ),
        ],
    )
    def test_every_drawn_mark_is_in_the_route(self, call, grade):
        out = _ok(f"""
const mod = await import("./bga/viewer/drawings.js");
const block = mod.{call.replace("GRADE", grade)};
{_READ_VALUE_COVERAGE}
""")
        assert out["values"], (call, grade, out)
        assert not out["missing"], (call, grade, out)


@needs_node
class TestElementHistorysSparklineNamesAndRoutesItself:
    """`element.js`'s own inline sparkline - annotation grade only, so
    it draws no twin. Review #295: its route used to be the sentence,
    which names only the first and last run; the route is now a hidden
    node naming every run, so a middle point stays reachable."""

    def test_a_history_with_points_is_named_and_routed_to_every_run(self):
        store = {
            "schema": "store/v1",
            "snapshots": [
                {
                    "stamp": "a",
                    "verdict_kind": None,
                    "elements": [{"element_uid": "elt", "duration_us": 1_000_000, "on_critical_path": True}],
                },
                {
                    "stamp": "b",
                    "verdict_kind": None,
                    "elements": [{"element_uid": "elt", "duration_us": 5_000_000, "on_critical_path": True}],
                },
                {
                    "stamp": "c",
                    "verdict_kind": "regressed",
                    "elements": [{"element_uid": "elt", "duration_us": 2_000_000, "on_critical_path": False}],
                },
            ],
        }
        out = _ok(f"""
const mod = await import("./tests/viewer.mjs");
const block = mod.renderElementHistory({json.dumps(store)}, "elt", null);
const svg = all(block, (n) => n.attrs.role === "img")[0];
const sentence = all(block, (n) => n.attrs["data-role"] === "history-sentence")[0];
const route = all(block, (n) => n.attrs.id === svg.attrs["aria-details"])[0];
console.log(JSON.stringify({{
  label: svg.attrs["aria-label"] ?? null,
  sentenceText: sentence ? text(sentence) : null,
  routeIsSentence: route === sentence,
  routeLabel: route ? route.attrs["aria-label"] ?? null : null,
  routeHidden: Boolean(route && route.hidden),
}}));
""")
        assert out["label"], out
        assert out["label"] == out["sentenceText"], out
        assert not out["routeIsSentence"], out
        assert out["routeHidden"], out
        # The middle run (5,000 µs, stamp "b") is not in the sentence -
        # only its first/last are - but it must be in the route.
        assert "b" in out["routeLabel"] and "5.0 s" in out["routeLabel"], out
        assert "b" not in out["sentenceText"], out


@needs_node
class TestTheTwoComposedFiguresAlwaysHaveATwinAsTheirRoute:
    """`views.js`'s `renderBand`/`renderTrend` - the two the Required
    Fix's table says had "none today", so this row draws one for each.
    Both always carry a twin, exhibit-only in name alone."""

    def test_the_band_names_itself_and_routes_to_its_twin(self):
        compare = {
            "baseline_band": {
                "band_low_us": 100,
                "band_high_us": 200,
                "observed_low_us": 80,
                "observed_high_us": 260,
                "runs": [90, 150, 250],
            },
            "candidate": {"total_duration_us": 230},
        }
        out = _ok(f"""
const mod = await import("./tests/viewer.mjs");
const block = mod.renderBand({json.dumps(compare)});
const svg = all(block, (n) => n.attrs.role === "img")[0];
const caption = all(block, (n) => n.attrs.class === "muted"
                                && n.tagName === "p")[0];
const route = all(block, (n) => n.attrs.id === svg.attrs["aria-details"])[0];
console.log(JSON.stringify({{
  label: svg.attrs["aria-label"] ?? null,
  captionText: caption ? text(caption) : null,
  routeIsTwin: Boolean(route && all(route, (n) => n.attrs["data-role"] === "drawing-twin").length),
}}));
""")
        assert out["label"], out
        assert out["label"] == out["captionText"], out
        assert out["routeIsTwin"], out

    def test_the_store_trend_names_itself_and_routes_to_its_twin(self):
        store = {
            "schema": "store/v1",
            "project": "/p",
            "count": 3,
            "total_bytes": 6,
            "snapshots": [
                {
                    "stamp": "a",
                    "bytes": 1,
                    "alias": None,
                    "has_run": True,
                    "incomplete_reason": None,
                    "total_duration_us": 1000,
                },
                {
                    "stamp": "b",
                    "bytes": 2,
                    "alias": "@prev",
                    "has_run": True,
                    "incomplete_reason": None,
                    "total_duration_us": 3000,
                },
                {
                    "stamp": "c",
                    "bytes": 3,
                    "alias": "@last",
                    "has_run": True,
                    "incomplete_reason": None,
                    "total_duration_us": 2000,
                },
            ],
        }
        out = _ok(f"""
const mod = await import("./tests/viewer.mjs");
const block = mod.renderTrend({json.dumps(store)});
const svg = all(block, (n) => n.attrs.role === "img")[0];
const caption = all(block, (n) => (n.attrs.class || "").includes("muted")
                                && n.tagName === "p"
                                && !(n.attrs.class || "").includes("trend-distribution"))[0];
const route = all(block, (n) => n.attrs.id === svg.attrs["aria-details"])[0];
console.log(JSON.stringify({{
  label: svg.attrs["aria-label"] ?? null,
  captionText: caption ? text(caption) : null,
  routeIsTwin: Boolean(route && all(route, (n) => n.attrs["data-role"] === "drawing-twin").length),
}}));
""")
        assert out["label"], out
        assert out["label"] == out["captionText"], out
        assert out["routeIsTwin"], out


# --------------------------------------------------------------------------
# On the real pages: every `svg[role=img]` in the export names itself and
# resolves a route - both fixtures, the acceptance test's own claim.
# --------------------------------------------------------------------------

GOLDEN = REPO / "tests" / "fixtures" / "golden" / "mixed_task_kinds"
MACRO = REPO / "tests" / "fixtures" / "macro_micro" / "run"


def _probe_source():
    source = (REPO / "tests/unit/test_a_report_you_can_navigate.py").read_text()
    return source.split('_PROBE = r"""', 1)[1].rsplit('"""', 1)[0]


_TAIL = r"""
const all = (n, pred, out = []) => {
  if (pred(n)) out.push(n);
  for (const c of n.children ?? []) all(c, pred, out);
  return out;
};
const root = named["report"] ?? body;
const drawings = all(root, (n) => n.attrs?.role === "img"
                                && n.tagName === "svg").map((svg) => {
  const details = svg.attrs["aria-details"];
  const route = details
    ? all(root, (n) => n.attrs?.id === details)[0] : null;
  return {
    dataRole: svg.attrs["data-role"] ?? null,
    label: svg.attrs["aria-label"] ?? null,
    hasRoute: Boolean(route),
  };
});
console.log(JSON.stringify({ drawings, error: failure }));
"""


def _boot(run_dir, tmp):
    run = snapshot_copy(run_dir, tmp)

    import tools.bga_view as view

    page = tmp / "report.html"
    view.export(str(run), str(page))
    html = page.read_text(encoding="utf-8")
    module = tmp / "inline.mjs"
    module.write_text(view.inflated_module(html), encoding="utf-8")
    probe = tmp / "probe.mjs"
    probe.write_text(_probe_source().split("const report =", 1)[0] + _TAIL, encoding="utf-8")
    result = subprocess.run(
        [node, str(probe)],
        capture_output=True,
        text=True,
        cwd=REPO,
        timeout=180,
        env=dict(os.environ, PAGE=str(page), MOD=str(module), PROTOCOL="file:", BGA_DOM_SHIM=SHIM),
    )
    assert result.returncode == 0, result.stderr[-4000:]
    out = json.loads(result.stdout)
    assert out["error"] is None, out["error"]
    return out


@pytest.fixture(scope="module")
def booted():
    import shutil as _shutil
    import tempfile

    pages = {}
    for name, run in (("golden", GOLDEN), ("macro_micro", MACRO)):
        tmp = Path(tempfile.mkdtemp())
        try:
            pages[name] = _boot(run, tmp)
        finally:
            _shutil.rmtree(tmp, ignore_errors=True)
    return pages


@needs_node
@pytest.mark.medium
class TestEveryDrawingOnTheRealPagesIsNamedAndRouted:
    def test_every_drawing_carries_a_non_empty_name(self, booted):
        for page, out in booted.items():
            assert out["drawings"], f"{page} drew nothing at all"
            unnamed = [d for d in out["drawings"] if not d["label"]]
            assert not unnamed, (page, unnamed)

    def test_every_drawing_carries_a_resolvable_route(self, booted):
        for page, out in booted.items():
            unrouted = [d for d in out["drawings"] if not d["hasRoute"]]
            assert not unrouted, (page, unrouted)
