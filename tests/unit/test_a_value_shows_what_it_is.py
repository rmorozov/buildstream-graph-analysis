"""UX-267: a nested value is drawn by its shape, not dumped as JSON.

Reported: *"tables where the left column contains a JSON object name
and the right column is a collapsed value object, and when expanded it
shows the internals as a string — it looks quite ugly … you need to
click on every object to open it"*.

One branch of `app.js` was responsible for four separate complaints:

```js
cell = el("details", {}, el("summary", {}, "object"),
          el("pre", {}, JSON.stringify(value, null, 2)));
```

`typeof value === "object"` is true for arrays too, so this produced a
summary saying `object`, raw JSON behind it, arrays read as JSON, and
nothing searchable, sortable or bounded.

Measured on a served 44-element run, in Chrome 141:

```text
                          before    after
opaque "object" cells         34        0
characters of <pre>       32,393        0
document                13.8 scr  13.7 scr
sections                      34       34
```

**The fold was never the defect** - a summary reading `object` was. A
spike that replaced folds with open tables removed the same JSON and
took the document to 35.5 screens; row-bounding got 32.3, a bounded
height 20.8. Folding with a real label costs nothing.

**Why the spike did not land the first time**, and the whole fix the
second: `renderTable` returns a `<section data-section=…>`, which is
right for a view and wrong for a *cell*. Calling it for nested maps put
twenty-two sections inside table cells, and `nav.js` finds sections at
any depth - the contents listed `summary` twice, because `summary` is
both a map key and the run's own section. `buildTable` is the same
builder without the section; `renderTable` is `buildTable` in a
section.
"""
import json
import os
import pathlib
import shutil
import subprocess

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")
APP = (REPO / "bga/viewer/app.js").read_text(encoding="utf-8")

_HARNESS = """
globalThis._makeNode ??= (await import(process.env.BGA_DOM_SHIM)).makeNode;
globalThis.document = { createElement: _makeNode,
                        createElementNS: (_n, t) => _makeNode(t),
                        getElementById: () => null };
const app = await import("./bga/viewer/app.js");
const drawn = app.renderStructured(%s, %s, {}, undefined);

const text = (n) => {
  if (!n) return "";
  return (n.children ?? []).length
    ? (n.children).map(text).join("") : (n.textContent ?? "");
};
const find = (n, p, out = []) => {
  if (!n) return out;
  if (p(n)) out.push(n);
  (n.children ?? []).forEach((c) => find(c, p, out));
  return out;
};
console.log(JSON.stringify({
  tag: drawn.tagName,
  className: drawn.className,
  text: text(drawn),
  summary: find(drawn, (n) => n.tagName === "summary").map(text),
  tables: find(drawn, (n) => n.tagName === "table").length,
  rows: find(drawn, (n) => n.tagName === "tr").length,
  sections: find(drawn, (n) => n.attrs?.["data-section"] !== undefined).length,
  bounded: find(drawn, (n) => n.attrs?.["data-bounded"] === "map").length,
  pre: find(drawn, (n) => n.tagName === "pre").length,
}));
"""


def _draw(key, value):
    script = _HARNESS % (json.dumps(key), json.dumps(value))
    done = subprocess.run([node, "--input-type=module", "-e", script],
                          capture_output=True, text=True, cwd=REPO, timeout=60,
                          env={**os.environ, "BGA_DOM_SHIM":
                               (REPO / "tests/dom_shim.mjs").as_uri()})
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


@needs_node
class TestNothingIsCalledObject:
    def test_a_wide_map_folds_behind_its_own_name(self):
        drawn = _draw("blast_radius", {f"e{i}.bst": i for i in range(44)})
        assert drawn["tag"] == "details", drawn
        assert drawn["summary"] == ["Blast radius · 44 entries"], drawn

    def test_no_shape_renders_raw_json(self):
        """The `<pre>` is the thing being removed; a guard on the label
        alone would pass a page that still dumps JSON under it."""
        for key, value in (("m", {f"k{i}": i for i in range(20)}),
                           ("a", list(range(30))),
                           ("r", {f"k{i}": {"a": i} for i in range(12)})):
            assert _draw(key, value)["pre"] == 0, key

    def test_a_map_is_a_table_a_reader_can_search(self):
        drawn = _draw("slack", {f"e{i}.bst": i * 10 for i in range(44)})
        assert drawn["tables"] == 1, drawn
        assert drawn["rows"] >= 44, drawn
        assert drawn["bounded"] == 1, "the table is not height-bounded"


class TestThePageActuallyUsesIt:
    """The guard the first draft of this file did not have.

    Every test above drives `renderStructured` directly, so restoring
    the original `<details><summary>object</summary><pre>` at the *call
    site* left all of them green - the mutation that reinstates the
    reported defect was not discriminating. What follows pins the
    wiring, which is the half a reader actually meets.
    """

    def _cell_branch(self):
        branch = APP.split('} else if (value !== null && typeof value === "object") {', 1)
        assert len(branch) == 2, "the object branch is gone from the cell renderer"
        return branch[1].split("} else if", 1)[0]

    def test_the_object_cell_goes_through_the_renderer(self):
        assert "renderStructured(" in self._cell_branch(), (
            "an object cell no longer renders through renderStructured, so "
            "every measurement in this file describes a function the page "
            "does not call (UX-267)")

    def test_no_cell_is_built_from_stringified_json(self):
        """The defect in one line, banned where it lived."""
        assert "JSON.stringify" not in self._cell_branch(), (
            "a cell is built from raw JSON again")

    def test_the_page_has_no_summary_reading_object(self):
        """`el("summary", {}, "object")` is the exact reported label."""
        assert 'el("summary", {}, "object")' not in APP, (
            'a summary literally reading "object" is back')


@needs_node
class TestSmallThingsNeedNoClick:
    def test_a_small_object_is_one_line(self):
        drawn = _draw("shape", {"average_depth": 3, "peak_depth": 9})
        assert drawn["tag"] == "span", drawn
        assert drawn["className"] == "inline-object", drawn
        assert "Average depth" in drawn["text"] and "Peak depth" in drawn["text"]

    def test_a_short_array_is_one_line(self):
        drawn = _draw("kinds", ["import", "stack", "cmake"])
        assert drawn["tag"] == "span"
        assert drawn["text"] == "import, stack, cmake", drawn

    def test_an_empty_value_says_none_rather_than_nothing(self):
        for value in ({}, []):
            assert _draw("x", value)["text"] == "none", value

    def test_the_boundary_is_a_named_constant(self):
        """A magic 4 in the middle of a renderer is a decision nobody
        can find. `UX-262`'s `TABLE_OPENS_BOUNDED_ABOVE` is the
        precedent."""
        assert "export const OBJECT_INLINE_FIELDS" in APP
        assert "export const ARRAY_INLINE_ITEMS" in APP

    def test_an_object_one_past_the_bound_folds(self):
        """The bound is a decision, so both sides of it are checked."""
        small = _draw("x", {f"k{i}": i for i in range(4)})
        big = _draw("x", {f"k{i}": i for i in range(5)})
        assert small["tag"] == "span" and big["tag"] == "details", (small, big)


@needs_node
class TestACellIsNeverASection:
    """The defect that stopped the first attempt. `nav.js` finds
    sections with `querySelectorAll` at any depth, so a section inside
    a table cell becomes a phantom entry in the table of contents -
    measured: 22 of them, and `summary` listed twice."""

    def test_no_drawn_value_contains_a_section(self):
        for key, value in (("summary", {f"k{i}": i for i in range(20)}),
                           ("rows", [{"a": 1, "b": 2}] * 12),
                           ("nums", list(range(30)))):
            assert _draw(key, value)["sections"] == 0, key

    def test_the_builder_and_the_view_are_separate_functions(self):
        assert "export function buildTable(" in APP
        assert "export function renderTable(" in APP
        builder = APP.split("export function buildTable(", 1)[1]
        builder = builder.split("\nexport function ", 1)[0]
        assert 'data-section' not in builder, (
            "buildTable emits a section again, so every cell that uses it "
            "puts a phantom entry in the table of contents (UX-267)")

    def test_the_renderer_uses_the_builder(self):
        renderer = APP.split("export function renderStructured(", 1)[1]
        renderer = renderer.split("\nexport function ", 1)[0]
        assert "renderTable(" not in renderer, (
            "renderStructured calls renderTable, which wraps its result in a "
            "section - use buildTable")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
