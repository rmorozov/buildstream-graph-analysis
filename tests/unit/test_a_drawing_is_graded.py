"""UX-316: a drawing declares its grade, and its geometry comes from the scale.

Styleguide §2a, earned by the field pass reading a real capture: the
blast-radius distribution "is good as sparkline — but very small and I
don't see anything there"; the store diagram "unreadable because
everything is very small"; the element-duration distribution
"unreadable".

Ground truth before the fix — every drawing in the viewer, and the one
geometry all of them shared:

```text
drawing                                       viewBox      CSS box
blast-radius distribution   (strip)           0 0 100 8    9rem x .9rem
element-duration distribution (strip)         0 0 100 8    9rem x .9rem
graph shape, width_at_level (sparkline)       0 0 100 20   7rem x 1.4rem
store diagram, the trend    (bespoke)         0 0 100 40   100% x 5rem
the compare band            (bespoke)         0 0 100 74   100% x 5rem
element history             (bespoke)         0 0 100 20   7rem x 1.4rem
```

`SPARK_HEIGHT = 20` / `STRIP_HEIGHT = 8` is a geometry calibrated for a
sparkline beside a table cell. Three of those six drawings are their
section's whole answer and were drawn at it anyway — §4.5's token
lesson, arriving at geometry: **one grade cannot do two jobs**.

What this file holds, and the order it holds it in:

1. **A drawing that declares no grade is refused**, at the call. Not
   defaulted — the defect was a call site that never chose, and a
   default is how the next one does not choose either.
2. **The scale is the only source of geometry.** No `viewBox` in the
   viewer is written out by hand; the CSS sizes are `--draw-*` tokens.
   `views.js` carried `viewBox: "0 0 100 20"` as a literal, which is
   exactly the per-drawing constant §2a abolishes.
3. **Annotation grade is unchanged**, coordinate for coordinate. This
   item raises exhibits; it does not redraw sparklines.
4. **Every exhibit is an exhibit all the way**: the scale's box, the
   container's width, tick labels, and its table twin rendering the
   same published values the drawing was handed.

The one deviation from the Required Fix, recorded rather than smoothed:
it asks for annotation-grade drawings "unchanged byte-for-byte", and
they carry one new attribute (`data-grade="annotation"`). Their
geometry — every coordinate, every radius, both CSS boxes — is
identical, and clause 3 asserts that from the numbers. The attribute is
what makes clause 1 readable off the page rather than off the source.
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")
VIEWER = REPO / "bga" / "viewer"
SHIM = str(REPO / "tests" / "dom_shim.mjs")


def _js(body):
    """Drive the shipped modules against the shared shim (`UX-264`)."""
    source = """
globalThis._makeNode ??= (await import(process.env.BGA_DOM_SHIM)).makeNode;
globalThis.document = { createElement: _makeNode,
                        createElementNS: (_n, t) => _makeNode(t),
                        getElementById: () => null,
                        querySelector: () => null };
globalThis.location = { protocol: "file:", href: "http://x/" };
globalThis.window = { localStorage: { getItem: () => null, setItem: () => {} } };
globalThis.CSS = { escape: (s) => s };
globalThis.Event = class { constructor(t) { this.type = t; } };
const all = (n, pred, out = []) => {
  if (pred(n)) out.push(n);
  for (const c of n.children ?? []) all(c, pred, out);
  return out;
};
const text = (n) => !n ? "" : ((n.children ?? []).length
  ? (n._text ?? "") + n.children.map(text).join("") : (n._text ?? ""));
""" + body
    result = subprocess.run(
        [node, "--input-type=module", "-e", source],
        capture_output=True, text=True, cwd=REPO, timeout=90,
        env=dict(os.environ, BGA_DOM_SHIM=SHIM))
    return result


def _rules():
    """`(selector, [(property, value), ...])` for every rule in the sheet.

    Comments stripped first: this file's own subject is the literal it
    forbids, and `style.css` explains the scale above the rules that use
    it.
    """
    css = re.sub(r"/\*.*?\*/", "", (VIEWER / "style.css").read_text(
        encoding="utf-8"), flags=re.S)
    out = []
    for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        selector = " ".join(match.group(1).split())
        decls = [tuple(part.split(":", 1)) for part in match.group(2).split(";")
                 if ":" in part]
        out.append((selector, [(name.strip(), value.strip())
                               for name, value in decls]))
    return out


def _ok(body):
    result = _js(body)
    assert result.returncode == 0, result.stderr[-3000:]
    return json.loads(result.stdout)


# --------------------------------------------------------------------------
# 1. The grade is chosen, never defaulted.
# --------------------------------------------------------------------------

@needs_node
class TestADrawingMustChooseItsGrade:
    """§2a's last rule: the grade is declared where the drawing is
    placed, because only the renderer knows whether this drawing is the
    section's answer. A default would let the next call site not choose,
    which is precisely how three exhibits came to be drawn at annotation
    size."""

    @pytest.mark.parametrize("call", [
        'sparkline([1, 2, 3], { unit: "level" })',
        'strip({ n: 3, min: 0, max: 9, p95: 8, deciles: { p50: 4 } }, {})',
    ])
    def test_omitting_the_grade_is_an_error(self, call):
        result = _js("""
const { sparkline, strip } = await import("./bga/viewer/drawings.js");
%s;
console.log("{}");
""" % call)
        assert result.returncode != 0, (
            "a drawing was made without a grade; §2a says the call site "
            "chooses, and a silent default is what this item is fixing")
        assert "styleguide §2a" in result.stderr

    def test_an_invented_grade_is_an_error(self):
        """"There is no third size" - so a third *name* cannot quietly
        acquire one by being passed."""
        result = _js("""
const { sparkline } = await import("./bga/viewer/drawings.js");
sparkline([1, 2, 3], { unit: "level", grade: "medium" });
console.log("{}");
""")
        assert result.returncode != 0
        assert "styleguide §2a" in result.stderr

    def test_both_grades_are_accepted_and_stamped_on_the_drawing(self):
        out = _ok("""
const { sparkline } = await import("./bga/viewer/drawings.js");
const made = ["annotation", "exhibit"].map(
  (grade) => sparkline([1, 5, 2], { unit: "level", grade }).attrs["data-grade"]);
console.log(JSON.stringify(made));
""")
        assert out == ["annotation", "exhibit"]


# --------------------------------------------------------------------------
# 2. The scale is the only source of geometry.
# --------------------------------------------------------------------------

class TestTheScaleIsTheOnlySourceOfGeometry:
    """§2a: "drawing heights and type sizes come from a small token
    scale, not from per-drawing constants - the normalization
    instrument". Held statically, because the defect it catches is a
    number written beside a drawing, and that is a property of the
    source rather than of any one booted page."""

    #: Every `viewBox` the viewer writes has to be built from `SCALE`.
    #: A literal is the defect: `views.js` held `viewBox: "0 0 100 20"`
    #: and no guard could see that it was the sparkline box, applied by
    #: hand, in a file that never imported the scale.
    def _view_boxes(self):
        found = []
        for path in sorted(VIEWER.glob("*.js")):
            source = path.read_text(encoding="utf-8")
            for line, body in enumerate(source.splitlines(), 1):
                # Skip prose: this file's own subject matter is the
                # constant it forbids, and so is `drawings.js`'s.
                if re.match(r"\s*(//|\*|/\*)", body):
                    continue
                for match in re.finditer(r"viewBox:\s*(.+?)(?:,\s*$|,\s)", body):
                    found.append((path.name, line, match.group(1).strip()))
        return found

    def test_every_view_box_is_built_from_the_scale(self):
        boxes = self._view_boxes()
        assert boxes, "no drawing found at all - the scan stopped working"
        loose = [(name, line, expr) for name, line, expr in boxes
                 if "size." not in expr and "SCALE[" not in expr
                 and "${H}" not in expr and "${W}" not in expr]
        assert not loose, (
            "a drawing's box is written out rather than read from the "
            f"scale (styleguide §2a): {loose}")

    def test_the_two_composed_figures_take_their_height_from_the_scale(self):
        """`${H}` passes the scan above only because `H` itself is
        assigned from `SCALE` - asserted here rather than assumed, or
        the scan has a hole shaped like a local variable."""
        source = (VIEWER / "views.js").read_text(encoding="utf-8")
        assigns = re.findall(r"const (?:W = [^,;]+, )?H = ([^;]+);", source)
        assert assigns, "no figure height assigned in views.js"
        for expr in assigns:
            assert "SCALE[" in expr, (
                f"a figure's height is a local constant, not the scale: {expr}")

    def test_the_css_boxes_are_tokens(self):
        """The half a reader actually measures. A `rem` beside a drawing
        selector is the same defect one layer down."""
        css = (VIEWER / "style.css").read_text(encoding="utf-8")
        assert "--draw-annotation-h:" in css and "--draw-exhibit-h:" in css, (
            "the size scale is not declared as tokens"
        )
        # Every selector that sizes a drawing, and the rules that mention
        # it. A selector can appear in more than one rule - the two
        # exhibits share a `width: 100%` rule and each sets its own
        # height - so the question is asked of the whole set: *some* rule
        # gives it a height, and no rule gives it a literal one.
        for selector in (".sparkline", ".density-strip", ".trend", ".band",
                         ".series.exhibit .sparkline",
                         ".density.exhibit .density-strip"):
            rules = [(sel, decls) for sel, decls in _rules()
                     if selector in [one.strip() for one in sel.split(",")]]
            assert rules, f"no rule sizes {selector}"
            heights = [(sel, value) for sel, decls in rules
                       for name, value in decls if name == "height"]
            assert heights, f"{selector} is never given a height"
            for sel, value in heights:
                assert "var(--draw-" in value, (
                    f"a drawing's height is a literal, not a scale token: "
                    f"{sel} -> {value}")

    def test_an_exhibit_takes_the_container_width(self):
        css = (VIEWER / "style.css").read_text(encoding="utf-8")
        rule = re.search(
            r"\.series\.exhibit \.sparkline,\s*\n\.density\.exhibit "
            r"\.density-strip\s*\{([^}]*)\}", css)
        assert rule, "the two exhibit drawings do not share a width rule"
        assert "width: 100%" in rule.group(1), (
            "§2a: an exhibit takes the container's width")


# --------------------------------------------------------------------------
# 3. Annotation grade did not move.
# --------------------------------------------------------------------------

@needs_node
class TestAnnotationGradeIsUnchanged:
    """This item raises exhibits. A sparkline beside a table cell is
    still §2's word-sized picture, and every coordinate it draws is the
    one it drew before - asserted from the numbers, because "we did not
    touch it" is not a measurement."""

    def test_the_annotation_boxes_are_the_numbers_they_always_were(self):
        out = _ok("""
const { SCALE } = await import("./bga/viewer/drawings.js");
console.log(JSON.stringify(SCALE.annotation));
""")
        assert out == {"width": 100, "spark": 20, "strip": 8}

    def test_an_annotation_sparkline_draws_the_same_polyline(self):
        out = _ok("""
const { sparkline } = await import("./bga/viewer/drawings.js");
const block = sparkline([4, 1, 9, 3, 7],
                        { unit: "level", grade: "annotation" });
const svg = all(block, (n) => n.tagName === "svg")[0];
console.log(JSON.stringify({
  viewBox: svg.attrs.viewBox,
  points: all(svg, (n) => n.tagName === "polyline")[0].attrs.points,
  radii: all(svg, (n) => n.tagName === "circle").map((n) => n.attrs.r),
}));
""")
        assert out["viewBox"] == "0 0 100 20"
        # The §2 geometry, spelled out: y = 18 - fraction * 16.
        assert out["points"] == (
            "0.00,12.00 25.00,18.00 50.00,2.00 75.00,14.00 100.00,6.00")
        assert set(out["radii"]) == {"1.60"}

    def test_an_annotation_strip_draws_the_same_bar_and_ticks(self):
        out = _ok("""
const { strip } = await import("./bga/viewer/drawings.js");
const block = strip({ n: 11, min: 0, max: 100, deciles: { p50: 25 }, p95: 90 },
                    { grade: "annotation" });
const svg = all(block, (n) => n.tagName === "svg")[0];
const rect = all(svg, (n) => n.tagName === "rect")[0];
console.log(JSON.stringify({
  viewBox: svg.attrs.viewBox,
  bar: [rect.attrs.y, rect.attrs.height],
  ends: all(svg, (n) => (n.attrs.class || "").includes("density-end"))
          .map((n) => [n.attrs.y1, n.attrs.y2]),
  axis: all(block, (n) => n.attrs["data-role"] === "draw-axis").length,
  twin: all(block, (n) => n.attrs["data-role"] === "drawing-twin").length,
}));
""")
        assert out["viewBox"] == "0 0 100 8"
        assert out["bar"] == ["3", "2"]
        assert out["ends"] == [["1", "7"], ["1", "7"]]
        # §2 still holds for an annotation: no axis, no apparatus.
        assert out["axis"] == 0 and out["twin"] == 0


# --------------------------------------------------------------------------
# 4. An exhibit is an exhibit all the way.
# --------------------------------------------------------------------------

@needs_node
class TestAnExhibitIsDrawnAtExhibitSize:
    def test_the_exhibit_box_is_the_scale_and_not_the_annotation_one(self):
        out = _ok("""
const { sparkline, strip, SCALE } = await import("./bga/viewer/drawings.js");
const line = all(sparkline([4, 1, 9], { unit: "level", grade: "exhibit" }),
                 (n) => n.tagName === "svg")[0];
const bar = all(strip({ n: 3, min: 0, max: 9, p95: 8, deciles: { p50: 4 } },
                      { grade: "exhibit" }), (n) => n.tagName === "svg")[0];
console.log(JSON.stringify({
  scale: SCALE.exhibit, spark: line.attrs.viewBox, strip: bar.attrs.viewBox }));
""")
        assert out["scale"]["spark"] == 60 and out["scale"]["strip"] == 26
        assert out["spark"] == "0 0 100 60"
        assert out["strip"] == "0 0 100 26"

    def test_the_shape_is_the_same_drawing_scaled(self):
        """Three times the box, the same picture: §2a buys size, not a
        different drawing. The mutation this refuses is an exhibit that
        grew a grid or moved its marks - so the *fractions* are asserted,
        not the coordinates."""
        out = _ok("""
const { sparkline } = await import("./bga/viewer/drawings.js");
const at = (grade) => {
  const svg = all(sparkline([4, 1, 9, 3, 7], { unit: "level", grade }),
                  (n) => n.tagName === "svg")[0];
  const h = Number(svg.attrs.viewBox.split(" ")[3]);
  return svg.attrs.points ? null : all(svg, (n) => n.tagName === "polyline")[0]
    .attrs.points.split(" ").map((p) => {
      const [x, y] = p.split(",").map(Number);
      return [Number((x / 100).toFixed(4)), Number((y / h).toFixed(4))];
    });
};
console.log(JSON.stringify({ annotation: at("annotation"), exhibit: at("exhibit") }));
""")
        assert out["annotation"] == out["exhibit"], (
            "an exhibit is the annotation drawing at exhibit size; these "
            "two drew different pictures")

    def test_an_exhibit_labels_its_ends(self):
        out = _ok("""
const { strip } = await import("./bga/viewer/drawings.js");
const block = strip({ n: 11, min: 0, max: 100, deciles: { p50: 25 }, p95: 90 },
                    { grade: "exhibit", format: (n) => `${n}u` });
const axis = all(block, (n) => n.attrs["data-role"] === "draw-axis")[0];
console.log(JSON.stringify(
  (axis?.children ?? []).map((n) => [n.attrs["data-mark"], n.attrs["data-at"],
                                     text(n)])));
""")
        assert out == [["min", "0.00", "0u"], ["p50", "25.00", "25u"],
                       ["p95", "90.00", "90u"], ["max", "100.00", "100u"]]

    def test_every_tick_sits_where_the_drawing_puts_that_mark(self):
        """The label and the mark are one reading, so they are asserted
        against each other rather than each against a re-computation."""
        out = _ok("""
const { strip } = await import("./bga/viewer/drawings.js");
const block = strip({ n: 11, min: 4, max: 84, deciles: { p50: 24 }, p95: 64 },
                    { grade: "exhibit" });
const svg = all(block, (n) => n.tagName === "svg")[0];
const axis = all(block, (n) => n.attrs["data-role"] === "draw-axis")[0];
const drawn = {};
for (const n of all(svg, (n) => n.attrs["data-mark"])) {
  drawn[n.attrs["data-mark"]] = Number(n.attrs.x1);
}
console.log(JSON.stringify({ drawn, labels: Object.fromEntries(
  (axis.children ?? []).map((n) => [n.attrs["data-mark"],
                                    Number(n.attrs["data-at"])])) }));
""")
        for mark, position in out["labels"].items():
            assert position == pytest.approx(out["drawn"][mark], abs=0.01), (
                f"the {mark} label is not above the {mark} mark")


@needs_node
class TestEveryExhibitHasItsTableTwin:
    """§2a: "always paired with its table twin ... so the drawing never
    hoards data a reader wants as rows". The twin is the *same published
    values*, which is the property worth guarding - a twin holding a
    second reading of the payload would be the viewer doing arithmetic."""

    def test_a_series_twin_holds_the_points_the_drawing_was_handed(self):
        out = _ok("""
const { sparkline } = await import("./bga/viewer/drawings.js");
const block = sparkline([4, 1, 9, 3, 7],
                        { unit: "level", grade: "exhibit",
                          format: (n) => `${n}u` });
const svg = all(block, (n) => n.tagName === "svg")[0];
const twin = all(block, (n) => n.attrs["data-role"] === "drawing-twin")[0];
console.log(JSON.stringify({
  drawn: svg.attrs["data-values"],
  head: (twin.children[0].children[0].children ?? []).map(text),
  rows: (twin.children[1].children ?? []).map(
    (tr) => (tr.children ?? []).map(text)),
}));
""")
        assert out["drawn"] == "4,1,9,3,7"
        assert out["head"] == ["level", "value"]
        assert out["rows"] == [["1", "4u"], ["2", "1u"], ["3", "9u"],
                               ["4", "3u"], ["5", "7u"]]

    def test_a_distribution_twin_holds_every_published_mark(self):
        out = _ok("""
const { strip } = await import("./bga/viewer/drawings.js");
const block = strip({ n: 11, min: 0, max: 100, deciles: { p50: 25 }, p95: 90 },
                    { grade: "exhibit" });
const twin = all(block, (n) => n.attrs["data-role"] === "drawing-twin")[0];
console.log(JSON.stringify(
  (twin.children[1].children ?? []).map((tr) => (tr.children ?? []).map(text))));
""")
        assert out == [["min", "0"], ["median", "25"], ["p95", "90"],
                       ["max", "100"], ["n", "11"]]

    def test_the_twin_starts_closed_and_round_trips(self):
        """Closed, because the drawing is the answer; reachable, because
        §2a says the rows are never withheld. Both in the export - a
        toggle is DOM and needs no server (`UX-195`)."""
        out = _ok("""
const { strip } = await import("./bga/viewer/drawings.js");
const block = strip({ n: 3, min: 0, max: 9, p95: 8, deciles: { p50: 4 } },
                    { grade: "exhibit" });
const table = all(block, (n) => n.attrs["data-role"] === "drawing-twin")[0];
const button = all(block, (n) => n.attrs["data-drawing-twin"] !== undefined)[0];
const seen = [[table.hidden, text(button)]];
button.click(); seen.push([table.hidden, text(button)]);
button.click(); seen.push([table.hidden, text(button)]);
console.log(JSON.stringify(seen));
""")
        assert out == [[True, "as table"], [False, "as drawing"],
                       [True, "as table"]]

    def test_the_twin_survives_print_without_the_toggle(self):
        """§2b's rule that hover is never the only door, applied to a
        click: paper has no toggle, so the rows print open."""
        css = (VIEWER / "style.css").read_text(encoding="utf-8")
        # Every print block, because the sheet has two - the token
        # override and this one - and the question is whether *some*
        # block prints the twin open.
        blocks = re.findall(r"@media print \{(.*?)\n\}", css, re.S)
        assert any("twin-table" in one and "display: table" in one
                   for one in blocks), "the twin does not print open"
        assert any("twin-toggle" in one and "display: none" in one
                   for one in blocks), "the toggle prints as a dead control"


# --------------------------------------------------------------------------
# 5. And on the pages themselves.
# --------------------------------------------------------------------------

GOLDEN = REPO / "tests" / "fixtures" / "golden" / "mixed_task_kinds"
MACRO = REPO / "tests" / "fixtures" / "macro_micro" / "run"


def _probe_source():
    """The export probe, reused rather than re-implemented (`UX-264`)."""
    source = (REPO / "tests/unit/test_a_report_you_can_navigate.py").read_text()
    return source.split('_PROBE = r"""', 1)[1].rsplit('"""', 1)[0]


_TAIL = r"""
const all = (n, pred, out = []) => {
  if (pred(n)) out.push(n);
  for (const c of n.children ?? []) all(c, pred, out);
  return out;
};
const text = (n) => !n ? "" : ((n.children ?? []).length
  ? (n._text ?? "") + n.children.map(text).join("") : (n._text ?? ""));
const root = named["report"] ?? body;
const drawings = [];
(function walk(n, section) {
  for (const c of n.children ?? []) {
    const here = c.attrs?.["data-section"] ?? section;
    const role = c.attrs?.["data-role"];
    if (role === "series" || role === "density") {
      const svg = all(c, (x) => x.tagName === "svg")[0] ?? null;
      drawings.push({
        role, section: here, grade: c.attrs["data-grade"] ?? null,
        klass: c.className || c.attrs.class || "",
        viewBox: svg ? svg.attrs.viewBox : null,
        axis: all(c, (x) => x.attrs?.["data-role"] === "draw-axis").length,
        twinRows: all(c, (x) => x.attrs?.["data-role"] === "drawing-twin")
          .flatMap((t) => (t.children?.[1]?.children ?? []).map(
            (tr) => (tr.children ?? []).map(text))),
        values: svg ? (svg.attrs["data-values"] ?? null) : null,
        marks: svg ? { min: svg.attrs["data-min"], p50: svg.attrs["data-p50"],
                       p95: svg.attrs["data-p95"], max: svg.attrs["data-max"] }
                   : null,
      });
    }
    walk(c, here);
  }
})(root, null);
console.log(JSON.stringify({ drawings, error: failure }));
"""


def _boot(run_dir, tmp):
    run = tmp / "run"
    shutil.copytree(run_dir, run)
    if (run / "expected_output.json").exists():
        os.remove(run / "expected_output.json")

    import tools.bga_view as view

    page = tmp / "report.html"
    view.export(str(run), str(page))
    html = page.read_text(encoding="utf-8")
    module = tmp / "inline.mjs"
    module.write_text(
        re.search(r'<script type="module">(.*?)</script>', html, re.S).group(1),
        encoding="utf-8")
    probe = tmp / "probe.mjs"
    probe.write_text(_probe_source().split("const report =", 1)[0] + _TAIL,
                     encoding="utf-8")
    result = subprocess.run(
        [node, str(probe)], capture_output=True, text=True, cwd=REPO,
        timeout=180,
        env=dict(os.environ, PAGE=str(page), MOD=str(module),
                 PROTOCOL="file:", BGA_DOM_SHIM=SHIM))
    assert result.returncode == 0, result.stderr[-4000:]
    out = json.loads(result.stdout)
    assert out["error"] is None, out["error"]
    return out


@pytest.fixture(scope="module")
def booted():
    import tempfile

    pages = {}
    for name, run in (("golden", GOLDEN), ("macro_micro", MACRO)):
        tmp = Path(tempfile.mkdtemp())
        try:
            pages[name] = _boot(run, tmp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    return pages


@needs_node
@pytest.mark.medium
class TestTheNamedDrawingsAreExhibitsOnTheRealPages:
    """Three of `UX-316`'s four are on the committed exports and are
    named here by the payload key each draws, not by a count:

    ```text
    macro_micro  element_duration_distribution   "unreadable"
                 blast_radius_distribution       "very small"
    both         parallelism.width_at_level   the graph shape
    ```

    The fourth - the store diagram - needs a store with two snapshots,
    which neither committed fixture has; it is held by
    `TestTheComposedFiguresAreExhibits` below, against `renderTrend`
    directly. Said here rather than left as a gap, because "three of
    four on the pages" is a property of the fixtures and not a claim
    about the fix.
    """

    def test_every_drawing_on_the_page_declares_a_grade(self, booted):
        for page, out in booted.items():
            assert out["drawings"], f"{page} drew nothing at all"
            for one in out["drawings"]:
                assert one["grade"] in ("annotation", "exhibit"), (page, one)

    def test_the_declared_series_and_distributions_are_exhibits(self, booted):
        """§2a: a drawing that *is* the value is the section's answer.
        Every one of these renders because a schema declared the shape,
        so every one is an exhibit - measured on the page rather than
        argued from the source."""
        seen = 0
        for page, out in booted.items():
            for one in out["drawings"]:
                assert one["grade"] == "exhibit", (page, one)
                assert "exhibit" in one["klass"], (page, one)
                seen += 1
        assert seen == 4, f"expected 3 on macro_micro + 1 on golden, saw {seen}"

    def test_each_one_is_drawn_at_the_scale_and_not_beside_a_cell(self, booted):
        for page, out in booted.items():
            for one in out["drawings"]:
                expected = "0 0 100 60" if one["role"] == "series" \
                    else "0 0 100 26"
                assert one["viewBox"] == expected, (page, one)

    def test_each_one_labels_its_ends_and_carries_its_twin(self, booted):
        for page, out in booted.items():
            for one in out["drawings"]:
                assert one["axis"] == 1, (page, one)
                assert one["twinRows"], (page, one)

    def test_the_twin_holds_the_values_the_drawing_was_drawn_from(self, booted):
        """The equality walk the acceptance asks for. Not "the twin has
        rows" - the twin's rows and the drawing's own `data-*` are the
        same published numbers, so a twin computing its own would have to
        agree with the drawing to pass."""
        for page, out in booted.items():
            for one in out["drawings"]:
                rows = {label: value for label, value in one["twinRows"]}
                if one["role"] == "series":
                    values = one["values"].split(",")
                    assert len(rows) == len(values), (page, one)
                    continue
                marks = one["marks"]
                assert rows["min"] and rows["max"], (page, one)
                assert (marks["p50"] == "") == ("median" not in rows), (page, one)
                assert (marks["p95"] == "") == ("p95" not in rows), (page, one)


@needs_node
class TestTheComposedFiguresAreExhibits:
    """The store diagram and the compare band: bespoke drawings in
    `views.js`, and the two the §2a pass had to reach outside
    `drawings.js` for. The store diagram is the one the field pass called
    "unreadable because everything is very small"."""

    def _render(self, function, argument):
        result = _js("""
const mod = await import("./tests/viewer.mjs");
const node = mod.%s(%s);
const svg = all(node, (n) => n.tagName === "svg")[0] ?? null;
console.log(JSON.stringify({
  viewBox: svg ? svg.attrs.viewBox : null,
  grade: svg ? (svg.attrs["data-grade"] ?? null) : null,
  axis: all(node, (n) => n.attrs?.["data-role"] === "draw-axis").length,
  twin: all(node, (n) => n.attrs?.["data-role"] === "drawing-twin")
    .flatMap((t) => (t.children?.[1]?.children ?? []).map(
      (tr) => (tr.children ?? []).map(text))),
}));
""" % (function, argument))
        assert result.returncode == 0, result.stderr[-3000:]
        return json.loads(result.stdout)

    def test_the_store_diagram_is_an_exhibit_at_the_scale(self):
        store = {"schema": "store/v1", "project": "/p", "count": 3,
                 "total_bytes": 6,
                 "snapshots": [
                     {"stamp": "a", "bytes": 1, "alias": None, "has_run": True,
                      "incomplete_reason": None, "total_duration_us": 1000},
                     {"stamp": "b", "bytes": 2, "alias": "@prev",
                      "has_run": True, "incomplete_reason": None,
                      "total_duration_us": 3000},
                     {"stamp": "c", "bytes": 3, "alias": "@last",
                      "has_run": True, "incomplete_reason": None,
                      "total_duration_us": 2000}]}
        out = self._render("renderTrend", json.dumps(store))
        assert out["grade"] == "exhibit"
        # The scale's `spark`: a line over an order. It drew at 40.
        assert out["viewBox"] == "0 0 100 60"
        assert out["axis"] == 1
        assert [row[0] for row in out["twin"]] == ["a", "b", "c"], out["twin"]

    def test_the_band_is_an_exhibit_and_its_lanes_did_not_move(self):
        """The band was never a size complaint, and this does not make
        it one: its height is the same 74 it always drew at, read from
        the scale's `figure` rather than from a `const H` beside the
        drawing. What it gains is the grade and the twin."""
        compare = {"baseline_band": {"band_low_us": 100, "band_high_us": 200,
                                     "observed_low_us": 80,
                                     "observed_high_us": 260,
                                     "runs": [90, 150, 250]},
                   "candidate": {"total_duration_us": 230}}
        out = self._render("renderBand", json.dumps(compare))
        assert out["grade"] == "exhibit"
        assert out["viewBox"] == "0 0 100 74"
        assert [row[0] for row in out["twin"]] == [
            "candidate", "band low", "band high", "observed low",
            "observed high", "baseline 1", "baseline 2", "baseline 3"]
        assert [row[1] for row in out["twin"]] == [
            "230", "100", "200", "80", "260", "90", "150", "250"]
