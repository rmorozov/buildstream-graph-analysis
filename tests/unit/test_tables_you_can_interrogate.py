"""UX-205: tables you can interrogate.

Round 22 confirmed it: the tables sort (numeric-aware) and nothing else.
`UX-187` capped what the *text* report prints; the page renders every
row of every array unconditionally - the right default for a viewer, and
unusable without tools on it.

The rule holding all of it together is the same one `UX-201` established
and `UX-202` extended: **the comparison runs against the published
value.** A threshold typed as `> 5s` is parsed against `duration_us`
because the *column declares* it is a duration - and it is compared with
`data-raw`, never with the formatted cell text. Comparing "1.2s" to "5s"
as strings is the defect these guards exist to catch.
"""
import json
import os
import shutil
import subprocess

import pytest

node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")


def _node(script, timeout=120):
    result = subprocess.run([node, "--input-type=module", "-e", script],
                            capture_output=True, text=True, cwd=os.getcwd(),
                            timeout=timeout)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@needs_node
class TestTheThresholdParsesTheUnitTheColumnDeclares:
    @pytest.mark.parametrize("text,quantity,expected", [
        ("> 5s", "duration_us", {"op": ">", "value": 5_000_000}),
        ("5s", "duration_us", {"op": ">=", "value": 5_000_000}),
        ("<= 500ms", "duration_us", {"op": "<=", "value": 500_000}),
        # `UX-341` retired `seconds`, `megabytes`, `kilobytes` and
        # `percent` from the vocabulary, so no column can be declared in
        # one and these tables no longer carry four conversion sets to
        # filter a column that cannot exist.
        (">= 512mb", "bytes", {"op": ">=", "value": 536_870_912}),
        ("> 1gb", "bytes", {"op": ">", "value": 1_073_741_824}),
        ("< 50%", "share", {"op": "<", "value": 0.5}),
        ("> 10", "count", {"op": ">", "value": 10}),
    ])
    def test_it_parses(self, text, quantity, expected):
        out = _node(
            'const t = await import("./bga/viewer/tables.js");'
            f'console.log(JSON.stringify(t.parseThreshold({text!r}, {quantity!r})));')
        assert out == expected

    @pytest.mark.parametrize("text,quantity", [
        ("5q", "duration_us"),      # a unit nothing declares
        ("5mb", "duration_us"),     # a unit from the wrong quantity
        ("lots", "duration_us"),
        ("", "duration_us"),
    ])
    def test_what_it_will_not_parse_is_no_filter_at_all(self, text, quantity):
        """Not "hide everything". A threshold nobody can read must not
        silently empty the table."""
        out = _node(
            'const t = await import("./bga/viewer/tables.js");'
            f'console.log(JSON.stringify({{v: t.parseThreshold({text!r}, {quantity!r})}}));')
        assert out["v"] is None

    def test_a_bare_number_is_the_published_value(self):
        """`data-raw` is what the reader can see and what every other
        consumer of this JSON compares against."""
        out = _node(
            'const t = await import("./bga/viewer/tables.js");'
            'console.log(JSON.stringify(t.parseThreshold("> 5", "duration_us")));')
        assert out == {"op": ">", "value": 5}


@needs_node
class TestFilteringARenderedTable:
    def test_text_reduces_the_rows_and_the_badge_agrees(self):
        out = _node(_HARNESS.replace("__ACTIONS__", """
          const shown = tables.applyFilters(table, { text: "lib-b" });
          out.push({ shown, badge: tables.badgeText(shown, rows.length),
                     visible: visibleNames() });
        """))
        [result] = out
        assert result["shown"] == 1, result
        assert result["visible"] == ["lib-b.bst"]
        assert result["badge"] == "1 of 40"

    def test_a_threshold_compares_the_raw_value_not_the_rendered_string(self):
        """The mutation the acceptance names. `duration_us` renders as
        "1.2s"/"19.1s"; compared as *strings*, "5" sorts between them
        and the answer is wrong in both directions."""
        out = _node(_HARNESS.replace("__ACTIONS__", """
          const threshold = tables.parseThreshold("> 5s", "duration_us");
          const shown = tables.applyFilters(table, {
            thresholds: { duration_us: threshold } });
          out.push({ shown, visible: visibleNames(),
                     expected: rows.filter((r) => r.duration_us > 5e6).length });
        """))
        [result] = out
        assert result["shown"] == result["expected"]
        assert result["shown"] > 0, "the fixture has nothing above 5s"

    def test_text_and_threshold_are_both_applied(self):
        out = _node(_HARNESS.replace("__ACTIONS__", """
          const shown = tables.applyFilters(table, {
            text: "lib",
            thresholds: { duration_us: tables.parseThreshold("> 5s", "duration_us") } });
          out.push({ shown, visible: visibleNames(),
                     expected: rows.filter((r) => r.element_uid.includes("lib")
                                               && r.duration_us > 5e6).length });
        """))
        [result] = out
        assert result["shown"] == result["expected"]

    def test_clearing_the_filter_brings_every_row_back(self):
        out = _node(_HARNESS.replace("__ACTIONS__", """
          tables.applyFilters(table, { text: "lib-b" });
          const shown = tables.applyFilters(table, { text: "" });
          out.push({ shown, badge: tables.badgeText(shown, rows.length) });
        """))
        [result] = out
        assert result["shown"] == 40
        assert result["badge"] == "40 rows"

    def test_a_row_missing_the_column_a_threshold_names_is_hidden(self):
        """Rather than kept: "no value" does not pass "> 5s"."""
        out = _node(_HARNESS.replace("__ACTIONS__", """
          const shown = tables.applyFilters(table, {
            thresholds: { nothing_here: { op: ">", value: 0 } } });
          out.push({ shown });
        """))
        assert out[0]["shown"] == 0


@needs_node
class TestCopy:
    def test_a_copied_row_round_trips_and_equals_the_payload_row(self):
        out = _node(_HARNESS.replace("__ACTIONS__", """
          const tr = table.querySelectorAll("tbody tr")[3];
          out.push({ copied: tables.rowJson(tr, COLUMNS), row: rows[3] });
        """))
        [result] = out
        parsed = json.loads(result["copied"])
        for column, value in parsed.items():
            assert result["row"][column] == value, column

    def test_a_copied_cell_is_the_published_value_not_the_rendering(self):
        out = _node(_HARNESS.replace("__ACTIONS__", """
          const tr = table.querySelectorAll("tbody tr")[3];
          const cell = [...tr.children].find(
            (td) => td.getAttribute("data-column") === "duration_us");
          out.push({ copied: tables.cellText(cell), rendered: cell.textContent,
                     raw: rows[3].duration_us });
        """))
        [result] = out
        assert float(result["copied"]) == result["raw"]
        assert result["copied"] != result["rendered"], (
            "the copy is the formatted string, which does not paste into "
            "anything that computes")

    def test_a_browser_without_a_clipboard_is_not_an_error(self):
        """A page served over http on a non-localhost origin has no
        `navigator.clipboard`. Losing the copy is a nuisance; throwing
        would lose the report."""
        out = _node(
            'const t = await import("./bga/viewer/tables.js");'
            'const ok = await t.copy("x", { clipboard: null });'
            'const bad = await t.copy("x", { clipboard: { writeText() {'
            '  throw new Error("denied"); } } });'
            'console.log(JSON.stringify({ ok, bad }));')
        assert out == {"ok": False, "bad": False}


@needs_node
class TestTheScaleThatDemandedIt:
    """Item 4: virtualization *only* if measured slow. The measurement
    is the deliverable, and it is recorded in the task file."""

    def test_four_thousand_rows_render_and_filter_without_virtualization(self):
        out = _node(_BIG_HARNESS, timeout=180)
        # Not a performance assertion with a tight bound - a CI runner
        # is not a laptop. The ceiling is loose enough that only a
        # quadratic mistake trips it, which is what would actually
        # demand windowing.
        assert out["rows"] == 4000
        assert out["published"] == 4000
        assert out["shown"] == out["expected"]
        # `UX-526`: and the rows the filter did not keep left the
        # document rather than staying in it hidden.
        assert out["inDom"] == out["shown"], out
        assert out["render_ms"] < 5000, out
        assert out["filter_ms"] < 2000, out


_SHIM = """
globalThis._makeNode ??= (await import(process.env.BGA_DOM_SHIM)).makeNode;
globalThis._installDocument ??= (await import(process.env.BGA_DOM_SHIM)).installDocument;
function make(tag) {
  return _makeNode(tag);
}
_installDocument();
"""

_HARNESS = _SHIM + """
const app = await import("./tests/viewer.mjs");
const tables = await import("./bga/viewer/tables.js");

const COLUMNS = ["element_uid", "duration_us", "share_of_path"];
const rows = Array.from({ length: 40 }, (_, i) => ({
  element_uid: i === 7 ? "lib-b.bst" : `lib-${i}.bst`,
  duration_us: (i + 1) * 500000,
  share_of_path: (i + 1) / 100,
}));
const hint = { "bga:columns": [
  { key: "element_uid", title: "Element" },
  { key: "duration_us", title: "Duration", quantity: "duration_us" },
  { key: "share_of_path", title: "Share", quantity: "share" },
] };
const section = app.renderTable("critical_path_detail", rows, hint);
const table = section.children.find((c) => c.tagName === "table");
const visibleNames = () => table.querySelectorAll("tbody tr")
  .filter((tr) => !tr.hidden)
  .map((tr) => [...tr.children].find(
    (td) => td.getAttribute("data-column") === "element_uid").textContent);

const out = [];
__ACTIONS__
console.log(JSON.stringify(out));
"""

_BIG_HARNESS = _SHIM + """
const app = await import("./tests/viewer.mjs");
const tables = await import("./bga/viewer/tables.js");

const rows = Array.from({ length: 4000 }, (_, i) => ({
  element_uid: `element-${i}.bst`,
  duration_us: (i % 97) * 250000,
  share_of_path: (i % 97) / 100,
}));
const hint = { "bga:columns": [
  { key: "element_uid", title: "Element" },
  { key: "duration_us", title: "Duration", quantity: "duration_us" },
  { key: "share_of_path", title: "Share", quantity: "share" },
] };

let t0 = Date.now();
const section = app.renderTable("elements", rows, hint);
const render_ms = Date.now() - t0;
const table = section.children.find((c) => c.tagName === "table");
// The rows the render actually built. `UX-526` holds what the bound
// does not show out of the document, so the tbody is no longer the
// place to count them; `everyRow` is the built set, held and shown.
const rendered = tables.everyRow(table.querySelector("tbody")).length;

t0 = Date.now();
const shown = tables.applyFilters(table, {
  text: "element-1",
  thresholds: { duration_us: tables.parseThreshold("> 5s", "duration_us") } });
const filter_ms = Date.now() - t0;
const expected = rows.filter((r) => r.element_uid.includes("element-1")
                                 && r.duration_us > 5e6).length;

console.log(JSON.stringify({
  rows: rendered, inDom: table.querySelectorAll("tbody tr").length,
  published: Number(table.getAttribute("data-rows")),
  shown, expected, render_ms, filter_ms }));
"""


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
