"""UX-303: a value that *is* a shape draws as its shape first.

Styleguide §2, from the user's second and fourth asks. Before this the
viewer had **one** drawing of a series — the element-history sparkline
`UX-226` built — and no density strip anywhere, so a table longer than
a screen gave no sense of its distribution until somebody scrolled it.

Two hints join the vocabulary and two controls answer them:

```text
bga:series        an ordered numeric array; the value names the unit
                  of one step, because the sentence has to say it
bga:distribution  an object publishing percentiles; the value names
                  the key holding the sample count, which is the only
                  thing this repository's two distribution shapes
                  disagree on
```

What the booted exports draw with them today:

```text
golden       parallelism.width_at_level
             "3 levels, 2 → 1, peak 2 at level 1."
macro_micro  parallelism.width_at_level
             "10 levels, 1 → 1, peak 2 at level 2."
             element_duration_distribution
             "0 ms → 19.1 s, median 3.1 s, p95 19.1 s — n=11."
             blast_radius_distribution
             "0 → 10, median 5, p95 10 — n=11."
```

Neither committed fixture has a table over the 40-row bound, so the
column strip is exercised by a built table here rather than by a
booted page — stated because "no strip on the golden page" is a
property of the fixture, not evidence the strip works.

**The boundary that decides what a self-built strip may say** (§2, and
the reason `columnStrip` is a separate function rather than a flag on
`strip`): a strip built from a table column's own `data-raw` values is
a reading of published values in the way sorting is — but it **prints
no derived number**. Its labels are the smallest and largest *rows*
and a count of rows; the p50 and p95 ticks are positions and nothing
else. A percentile worth printing enters the payload first.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")
GOLDEN = REPO / "tests" / "fixtures" / "golden" / "mixed_task_kinds"
MACRO = REPO / "tests" / "fixtures" / "macro_micro" / "run"
SHIM = str(REPO / "tests" / "dom_shim.mjs")


def _js(body, protocol="file:"):
    """Run a snippet against the shared shim and parse what it printed."""
    source = """
globalThis._makeNode ??= (await import(process.env.BGA_DOM_SHIM)).makeNode;
globalThis.document = { createElement: _makeNode,
                        createElementNS: (_n, t) => _makeNode(t),
                        getElementById: () => null };
globalThis.location = { protocol: process.env.PROTOCOL, href: "http://x/" };
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
        env=dict(os.environ, BGA_DOM_SHIM=SHIM, PROTOCOL=protocol))
    assert result.returncode == 0, result.stderr[-3000:]
    return json.loads(result.stdout)


@needs_node
class TestASparklineDrawsWhatItWasGiven:
    """`UX-213`'s lesson applied at birth: the geometry is asserted
    from the values the drawing was handed, and a drawing that ignored
    them would have to produce the same coordinates to pass."""

    def _drawn(self, values):
        return _js("""
const { sparkline } = await import("./bga/viewer/drawings.js");
const block = sparkline(%s, { unit: "level", grade: "annotation" });
const svg = all(block, (n) => n.tagName === "svg")[0] ?? null;
const line = svg && all(svg, (n) => n.tagName === "polyline")[0];
console.log(JSON.stringify({
  drawn: block.attrs["data-drawn"],
  points: block.attrs["data-points"],
  values: svg ? svg.attrs["data-values"] : null,
  polyline: line ? line.attrs.points : null,
  marks: svg ? all(svg, (n) => n.attrs["data-mark"]).map(
    (n) => [n.attrs["data-mark"], n.attrs["data-value"], n.attrs.cx, n.attrs.cy]) : [],
  sentence: text(all(block,
    (n) => n.attrs["data-role"] === "series-sentence")[0]),
}));
""" % json.dumps(values))

    def test_each_point_lands_where_its_value_puts_it(self):
        values = [4, 1, 9, 3, 7]
        out = self._drawn(values)
        assert out["drawn"] == "true"
        assert out["values"] == "4,1,9,3,7"
        drawn = [tuple(float(n) for n in pair.split(","))
                 for pair in out["polyline"].split()]
        low, high = min(values), max(values)
        for index, (x, y) in enumerate(drawn):
            assert x == pytest.approx(index / (len(values) - 1) * 100, abs=0.01)
            expected = 18 - ((values[index] - low) / (high - low)) * 16
            assert y == pytest.approx(expected, abs=0.01), (
                f"point {index} (value {values[index]}) is at y={y}, and its "
                f"value puts it at {expected}")

    def test_the_geometry_is_not_uniform(self):
        """The mutation the acceptance test names. A drawing that
        ignored its values would put every point on one line, and the
        clause above would still pass if the expectation were computed
        the same wrong way — so this asserts the *variation* directly.
        """
        out = self._drawn([4, 1, 9, 3, 7])
        ys = {pair.split(",")[1] for pair in out["polyline"].split()}
        assert len(ys) == 5, f"five distinct values, {len(ys)} distinct heights"

    def test_the_three_marks_are_the_ends_and_the_peak(self):
        out = self._drawn([4, 1, 9, 3, 7])
        assert [mark[0] for mark in out["marks"]] == ["first", "last", "peak"]
        assert [mark[1] for mark in out["marks"]] == ["4", "7", "9"]

    def test_the_sentence_names_the_unit_and_the_peak(self):
        out = self._drawn([4, 1, 9, 3, 7])
        assert out["sentence"] == "5 levels, 4 → 7, peak 9 at level 3."

    @pytest.mark.parametrize("values,expected_points", [([5, 9], "2"), ([5], "1")])
    def test_under_three_points_is_a_sentence_and_no_drawing(
            self, values, expected_points):
        """`UX-226`'s rule, now global: two points joined by a line
        claim a trend two points cannot support."""
        out = self._drawn(values)
        assert out["drawn"] == "false"
        assert out["points"] == expected_points
        assert out["polyline"] is None, "a drawing was made anyway"
        assert out["sentence"]

    def test_a_flat_series_sits_on_the_middle_line(self):
        """Not on the floor: a series of identical values is not "all
        at zero", and drawing it there is a claim about the data."""
        out = self._drawn([7, 7, 7, 7])
        ys = {pair.split(",")[1] for pair in out["polyline"].split()}
        assert ys == {"10.00"}


@needs_node
class TestAPublishedStripPrintsWhatWasPublished:
    def _drawn(self, distribution, count_key="n"):
        return _js("""
const { strip } = await import("./bga/viewer/drawings.js");
const block = strip(%s, { countKey: %s, grade: "annotation" });
const svg = all(block, (n) => n.tagName === "svg")[0] ?? null;
console.log(JSON.stringify({
  drawn: block.attrs["data-drawn"], n: block.attrs["data-n"],
  printed: svg ? svg.attrs["data-printed"] : null,
  attrs: svg ? { min: svg.attrs["data-min"], max: svg.attrs["data-max"],
                 p50: svg.attrs["data-p50"], p95: svg.attrs["data-p95"] } : null,
  ticks: svg ? all(svg, (n) => n.attrs["data-mark"]).map(
    (n) => [n.attrs["data-mark"], n.attrs["data-value"], n.attrs.x1]) : [],
  sentence: text(all(block,
    (n) => n.attrs["data-role"] === "density-sentence")[0]),
}));
""" % (json.dumps(distribution), json.dumps(count_key)))

    def test_every_tick_sits_where_its_value_puts_it(self):
        shape = {"n": 11, "min": 0, "max": 100,
                 "deciles": {"p50": 25}, "p95": 90}
        out = self._drawn(shape)
        placed = {mark: (value, float(x)) for mark, value, x in out["ticks"]}
        assert placed["p50"] == ("25", pytest.approx(25.0, abs=0.01))
        assert placed["p95"] == ("90", pytest.approx(90.0, abs=0.01))
        assert placed["min"][1] == pytest.approx(0.0, abs=0.01)
        assert placed["max"][1] == pytest.approx(100.0, abs=0.01)

    def test_n_is_always_printed(self):
        """§2's rule: a strip without its population is a picture of an
        opinion."""
        out = self._drawn({"n": 11, "min": 0, "max": 100,
                           "deciles": {"p50": 25}, "p95": 90})
        assert out["n"] == "11"
        assert "n=11" in out["sentence"], out["sentence"]

    def test_it_reads_the_store_aggregate_shape_too(self):
        """One control, two published shapes — which is what naming the
        count key in the hint buys."""
        out = self._drawn({"samples": 30, "min": 1, "median": 4, "p95": 9,
                           "max": 10}, count_key="samples")
        assert out["drawn"] == "true"
        assert out["n"] == "30"
        placed = {mark: value for mark, value, _ in out["ticks"]}
        assert placed["p50"] == "4"

    def test_a_shape_with_no_ends_states_the_absence(self):
        out = self._drawn({"n": 0, "min": None, "max": None})
        assert out["drawn"] == "false"
        assert "No distribution" in out["sentence"]


@needs_node
class TestASelfBuiltStripPrintsNoDerivedNumber:
    """§2's boundary. The strip is a reading of published values, like
    sorting; the moment it prints a percentile it has computed one, and
    the no-arithmetic line moves."""

    def _drawn(self, values):
        return _js("""
const { columnStrip } = await import("./bga/viewer/drawings.js");
const block = columnStrip(%s, { grade: "annotation" });
const svg = all(block, (n) => n.tagName === "svg")[0] ?? null;
console.log(JSON.stringify({
  drawn: block.attrs["data-drawn"], n: block.attrs["data-n"],
  printed: svg ? svg.attrs["data-printed"] : null,
  ticks: svg ? all(svg, (n) => n.attrs["data-mark"]).map(
    (n) => [n.attrs["data-mark"], n.attrs["data-value"], n.attrs.x1]) : [],
  sentence: text(all(block,
    (n) => n.attrs["data-role"] === "density-sentence")[0]),
}));
""" % json.dumps(values))

    def test_the_ticks_exist_as_geometry(self):
        out = self._drawn([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        placed = {mark: (value, float(x)) for mark, value, x in out["ticks"]}
        # Nearest-rank, the rule `store_aggregate.percentile` uses.
        assert placed["p50"][0] == "5"
        assert placed["p95"][0] == "10"
        assert out["printed"] == "rows"

    def test_no_printed_number_is_a_percentile(self):
        """The clause the acceptance test asks for: every number in the
        sentence is an actual row value or a count of rows."""
        values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        out = self._drawn(values)
        printed = [int(n) for n in re.findall(r"\d+", out["sentence"])]
        allowed = set(values) | {len(values)}
        assert set(printed) <= allowed, (
            f"{sorted(set(printed) - allowed)} is neither a row value nor a "
            f"row count: {out['sentence']!r}")
        # And the derived ticks are *not* in it, which is the half a
        # subset check alone would not catch if p50 happened to be a
        # row value that is also printed. 5 is a row value and is the
        # p50; it must appear only if it is an end, and it is not.
        assert "median" not in out["sentence"]
        assert "p95" not in out["sentence"]

    def test_the_ends_and_the_count_are_named(self):
        out = self._drawn([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        assert out["sentence"] == "1 → 10 across 10 rows."

    def test_too_few_rows_is_a_sentence(self):
        out = self._drawn([4, 9])
        assert out["drawn"] == "false"
        assert "too few" in out["sentence"]


_TABLE = """
const app = await import("./tests/viewer.mjs");
const rows = Array.from({ length: %d }, (_, i) => (
  { element_uid: `e${i}.bst`, duration_us: (i + 1) * 1000 }));
const { table, tools } = app.buildTable("probe", rows, { "bga:columns": [
  { key: "element_uid", title: "Element" },
  { key: "duration_us", title: "Duration", quantity: "duration_us" }] });
const strip = all(tools, (n) => n.attrs["data-role"] === "density")[0] ?? null;
"""


@needs_node
class TestALongTableWearsItsShape:
    def test_a_table_past_the_bound_gets_a_strip(self):
        out = _js(_TABLE % 60 + """
console.log(JSON.stringify({
  present: Boolean(strip), column: strip?.attrs["data-column"] ?? null,
  n: strip?.attrs["data-n"] ?? null,
  interactive: strip?.attrs["data-interactive"] ?? null,
  sentence: strip ? text(all(strip,
    (n) => n.attrs["data-role"] === "density-sentence")[0]) : null,
}));
""")
        assert out["present"], "no strip on a 60-row table"
        assert out["column"] == "duration_us"
        assert out["n"] == "60"
        assert out["sentence"] == "1 ms → 60 ms across 60 rows."

    def test_a_short_table_gets_none(self):
        """The bound is `TABLE_OPENS_BOUNDED_ABOVE`, the same one that
        decides whether the table opens bounded — a strip on a table a
        reader can see whole is apparatus for nothing."""
        out = _js(_TABLE % 12 + """
console.log(JSON.stringify({ present: Boolean(strip) }));
""")
        assert not out["present"]

    def test_the_export_strip_is_static(self):
        """`UX-194`'s rule: an affordance whose precondition is absent
        is not shown as a dead one. The *shape* still renders — it is
        the point — and only the click is withheld."""
        out = _js(_TABLE % 60 + """
console.log(JSON.stringify({
  interactive: strip?.attrs["data-interactive"] ?? null,
  listeners: (all(strip, (n) => n.tagName === "svg")[0]?.listeners?.click ?? []).length,
}));
""", protocol="file:")
        assert out["interactive"] == "false"
        assert out["listeners"] == 0

    def test_clicking_the_strip_sets_the_threshold_filter(self):
        """The acceptance test's third clause. Served, a click on the
        strip sets the same state the threshold input sets — and to an
        **actual row value**, never to the position the click landed
        on, which would be a derived number entering through a mouse.
        """
        out = _js(_TABLE % 60 + """
const svg = all(strip, (n) => n.tagName === "svg")[0];
svg.clientWidth = 100;
// Half way along the range: values run 1000..60000, so the midpoint
// is 30500 and the nearest row value is 30000 or 31000.
svg.listeners.click[0]({ currentTarget: svg, offsetX: 50 });
const input = all(table, (n) =>
  (n.attrs.class || "").includes("th-filter"))[0];
const shown = all(table, (n) => n.tagName === "tr" && !n.hidden
                                && n.attrs["data-element"]).length;
console.log(JSON.stringify({
  interactive: strip.attrs["data-interactive"],
  value: input?.value ?? null, shown,
}));
""", protocol="http:")
        assert out["interactive"] == "true"
        assert out["value"] is not None, "the click set no threshold"
        threshold = int(re.search(r"(\d+)", out["value"]).group(1))
        assert threshold % 1000 == 0 and 1000 <= threshold <= 60000, (
            f"{threshold} is not one of the table's published values")
        assert out["shown"] < 60, (
            f"the threshold filtered nothing: {out['shown']} rows still shown")


class TestTheHintsAreDeclaredWhereTheyBelong:
    def test_the_vocabulary_names_both(self):
        from bga import schemas

        assert schemas.SERIES == "bga:series"
        assert schemas.DISTRIBUTION == "bga:distribution"
        assert schemas.SERIES_MIN_POINTS == 3

    def test_the_published_series_and_distributions_carry_them(self):
        """Declared on the payloads that qualify, so the drawing costs
        no viewer edit when a schema addition brings another
        (`UX-193`'s property, which is why the mapping is by shape)."""
        from bga import schemas

        # `UX-344`: the two distributions and `parallelism` are keys of
        # the document, where they were members of two namespaces.
        analyze = schemas.schema(schemas.ANALYZE)["properties"]
        for name in ("element_duration_distribution",
                     "blast_radius_distribution"):
            assert analyze[name][schemas.DISTRIBUTION] == "n", name
            assert schemas.QUANTITY in analyze[name], name
        width = (analyze["parallelism"]["properties"]["width_at_level"])
        assert width[schemas.SERIES] == "level"

        aggregate = schemas.schema(schemas.STORE_AGGREGATE)["properties"]
        duration = aggregate["blended"]["properties"]["duration_us"]
        assert duration[schemas.DISTRIBUTION] == "samples", (
            "the store aggregate counts in `samples`, and the hint is "
            "what lets one control read both shapes")

    def test_the_two_thresholds_agree(self):
        """`SERIES_MIN_POINTS` is declared twice — once for the pipeline
        and once for the page — and two copies of a threshold is how a
        threshold drifts (`UX-273`)."""
        from bga import schemas

        source = (REPO / "bga/viewer/drawings.js").read_text(encoding="utf-8")
        declared = int(re.search(
            r"export const SERIES_MIN_POINTS = (\d+);", source).group(1))
        assert declared == schemas.SERIES_MIN_POINTS


def _probe_source():
    source = (REPO / "tests/unit/test_a_report_you_can_navigate.py").read_text()
    return source.split('_PROBE = r"""', 1)[1].rsplit('"""', 1)[0]


_BOOT_TAIL = r"""
const root = named["report"] ?? body;
const all = (n, pred, out = []) => {
  if (pred(n)) out.push(n);
  for (const c of n.children ?? []) all(c, pred, out);
  return out;
};
const text = (n) => !n ? "" : ((n.children ?? []).length
  ? (n._text ?? "") + n.children.map(text).join("") : (n._text ?? ""));
console.log(JSON.stringify({
  error: failure,
  series: all(root, (n) => n.attrs?.["data-role"] === "series").map(
    (n) => ({ drawn: n.attrs["data-drawn"], unit: n.attrs["data-unit"],
              sentence: text(all(n,
                (x) => x.attrs["data-role"] === "series-sentence")[0]) })),
  density: all(root, (n) => n.attrs?.["data-role"] === "density").map(
    (n) => ({ drawn: n.attrs["data-drawn"], n: n.attrs["data-n"],
              sentence: text(all(n,
                (x) => x.attrs["data-role"] === "density-sentence")[0]) })),
}));
"""


@needs_node
@pytest.mark.medium
class TestTheRealPagesDrawThem:
    """And they draw on a booted export, from the payloads a real run
    publishes — not only in a harness."""

    @pytest.fixture(scope="module")
    def booted(self):
        pages = {}
        for name, run in (("golden", GOLDEN), ("macro_micro", MACRO)):
            tmp = Path(tempfile.mkdtemp())
            try:
                target = tmp / "run"
                shutil.copytree(run, target)
                if (target / "expected_output.json").exists():
                    os.remove(target / "expected_output.json")

                import tools.bga_view as view

                page = tmp / "report.html"
                view.export(str(target), str(page))
                html = page.read_text(encoding="utf-8")
                module = tmp / "inline.mjs"
                module.write_text(re.search(
                    r'<script type="module">(.*?)</script>', html, re.S).group(1),
                    encoding="utf-8")
                probe = tmp / "probe.mjs"
                probe.write_text(
                    _probe_source().split("const report =", 1)[0] + _BOOT_TAIL,
                    encoding="utf-8")
                result = subprocess.run(
                    [node, str(probe)], capture_output=True, text=True,
                    cwd=REPO, timeout=180,
                    env=dict(os.environ, PAGE=str(page), MOD=str(module),
                             PROTOCOL="file:", BGA_DOM_SHIM=SHIM))
                assert result.returncode == 0, result.stderr[-4000:]
                out = json.loads(result.stdout)
                assert out["error"] is None, out["error"]
                pages[name] = out
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
        return pages

    @pytest.mark.parametrize("page", ["golden", "macro_micro"])
    def test_the_width_series_is_drawn(self, booted, page):
        series = booted[page]["series"]
        assert series, f"{page}: no series drawn"
        assert all(one["unit"] == "level" for one in series), series
        assert all(one["drawn"] == "true" for one in series), series

    def test_the_two_populations_draw_in_their_units(self, booted):
        """`macro_micro` publishes both; `golden` has four elements and
        is under the sample floor, so it publishes neither - an absence
        of payload, not of control."""
        sentences = [one["sentence"] for one in booted["macro_micro"]["density"]]
        assert len(sentences) == 2, sentences
        assert "0 ms → 19.1 s, median 3.1 s, p95 19.1 s — n=11." in sentences
        assert "0 → 10, median 5, p95 10 — n=11." in sentences
        assert not booted["golden"]["density"]

    @pytest.mark.parametrize("page", ["golden", "macro_micro"])
    def test_every_drawing_states_its_population(self, booted, page):
        for one in booted[page]["density"]:
            assert one["n"], one
            assert f"n={one['n']}" in one["sentence"], one


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
