"""UX-277: the rule reaches `<td>`, not only `<dd>`.

`UX-267` built `renderStructured` - inline / bounded table / fold,
chosen by width - and wired it into `renderPairs`, which draws `<dd>`
cells. It was never wired into `buildTable`, which draws **every `<td>`
in the report**. So the rule governed one cell type and stopped dead at
the other, and the leaf that drew the other was:

```js
Array.isArray(raw) ? raw.join(", ")
  : (raw && typeof raw === "object") ? JSON.stringify(raw)
  : ...
```

Measured on the 1,202-element synthetic run in Chrome 141, before and
after:

```text
                                   before     after
raw-JSON cells                          6         0
joined-array cells over 60 chars       11         0
"[object Object]" cells                 1         0
widest cell, text                  14,300     4,409
widest cell, *visible*             14,300       152
cells over 200 visible characters       6         0
document                         18.8 scr  18.8 scr
```

The visible figure is the one that matters and the one a naive guard
gets wrong: `textContent` includes the body of a **closed** `<details>`,
so a folded cell still reads as 4,409 characters to `querySelector`.
What the reader sees is the summary, and after the fix the widest is
152 characters - inside `CELL_TEXT_CAP`.

Three stringifications were wrong in three different ways, and the
third is the one worth naming: an array of objects reached
`Array.prototype.toString` and rendered `[object Object], [object
Object]`, which carries strictly less information than the JSON it was
meant to improve on.
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
# `UX-337`: `app.js` was one file when these clauses were written. The
# formatters and the schema-hint readers moved to `format.js`, and the
# machinery that turns a value into an interrogable table moved to
# `structured.js` - unchanged, in a commit that was a move. These
# clauses are about what the viewer declares, not about which file
# declares it, so they read all three; pointing them at `app.js` alone
# would have quietly stopped seeing the constants they defend.
APP_MODULES = ("app.js", "format.js", "structured.js")
APP = "\n".join((REPO / "bga/viewer" / _name).read_text(encoding="utf-8")
                for _name in APP_MODULES)

# Values that reach a cell in the real report, each the shape of a
# defect the round measured.
SHAPES = {
    "leaves_detail": {f"e{i}.bst": {"element_kind": "stack",
                                    "is_structural_kind": True,
                                    "is_potentially_deferrable": False}
                      for i in range(40)},
    "high_fanin_elements": [[f"e{i}.bst", 8 - i % 5] for i in range(12)],
    "rule": {"name": "CHAIN_BOUND_RATIO", "threshold": 0.9,
             "comparison": ">=", "observed_path": "headline.chain_share",
             "sentence": "the chain binds"},
    "leaves": [f"layer10/mod{i:03d}.bst" for i in range(60)],
    "objects": [{"a": 1, "b": 2}, {"a": 3, "b": 4}, {"a": 5, "b": 6}],
}

_HARNESS = """
globalThis._makeNode ??= (await import(process.env.BGA_DOM_SHIM)).makeNode;
globalThis.document = { createElement: _makeNode,
                        createElementNS: (_n, t) => _makeNode(t),
                        getElementById: () => null };
const app = await import("./tests/viewer.mjs");
const rows = %s;
const built = app.buildTable("probe", rows, {}, undefined);

const text = (n) => {
  if (!n) return "";
  return (n.children ?? []).length
    ? (n.children).map(text).join("") : (n.textContent ?? "");
};
// What a reader sees: a closed <details> shows its summary only.
const visible = (n) => {
  if (!n) return "";
  if (n.tagName === "details" && !(n.attrs ?? {}).open) {
    const s = (n.children ?? []).find((c) => c.tagName === "summary");
    return s ? text(s) : "";
  }
  return (n.children ?? []).length
    ? (n.children).map(visible).join("") : (n.textContent ?? "");
};
const find = (n, p, out = []) => {
  if (!n) return out;
  if (p(n)) out.push(n);
  (n.children ?? []).forEach((c) => find(c, p, out));
  return out;
};
const cells = find(built.table, (n) => n.tagName === "td");
console.log(JSON.stringify({
  cells: cells.length,
  text: cells.map(text),
  visible: cells.map(visible),
  raw: cells.map((c) => (c.attrs ?? {})["data-raw"] ?? null),
  // How deeply tables nest, not how many there are: `find` recurses,
  // so a nested table's own cells are in `cells` too and a sum
  // double-counts them. The first draft of this guard did exactly that
  // and reported 3 nested tables where there are 2.
  table_depth: (function depth(n) {
    const kids = (n.children ?? []).map(depth);
    const below = kids.length ? Math.max(...kids) : 0;
    return below + (n.tagName === "table" ? 1 : 0);
  })(built.table) - 1,
  folds_in_cells: cells.reduce(
      (n, c) => n + find(c, (x) => x.tagName === "details").length, 0),
  sections_in_cells: cells.reduce(
      (n, c) => n + find(c, (x) => (x.attrs ?? {})["data-section"] !== undefined).length, 0),
  pre_in_cells: cells.reduce(
      (n, c) => n + find(c, (x) => x.tagName === "pre").length, 0),
}));
"""


def _cells(rows):
    script = _HARNESS % json.dumps(rows)
    done = subprocess.run([node, "--input-type=module", "-e", script],
                          capture_output=True, text=True, cwd=REPO, timeout=60,
                          env={**os.environ, "BGA_DOM_SHIM":
                               (REPO / "tests/dom_shim.mjs").as_uri()})
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


@needs_node
class TestNoCellStringifiesItsOwnStructure:
    @pytest.mark.parametrize("name", sorted(SHAPES))
    def test_no_cell_renders_raw_json(self, name):
        """The defect, per shape. A `{`-then-`}` cell is `JSON.stringify`
        reaching the reader."""
        drawn = _cells([{"key": name, "value": SHAPES[name]}])
        dumped = [t for t in drawn["text"]
                  if t.strip().startswith(("{\"", "[{"))]
        assert dumped == [], (
            f"{name}: cell(s) still rendering raw JSON: "
            f"{[d[:80] for d in dumped]}")

    @pytest.mark.parametrize("name", sorted(SHAPES))
    def test_no_cell_says_object_object(self, name):
        """`Array.prototype.toString` over objects, which carries less
        than the JSON it replaced."""
        drawn = _cells([{"key": name, "value": SHAPES[name]}])
        assert not any("[object Object]" in t for t in drawn["text"]), name

    @pytest.mark.parametrize("name", sorted(SHAPES))
    def test_what_the_reader_sees_is_bounded(self, name):
        """Visible text, not `textContent`: a closed fold still *holds*
        its body, and a guard that counted it would fail a correctly
        folded cell and pass an unfolded short one."""
        drawn = _cells([{"key": name, "value": SHAPES[name]}])
        cap = int(APP.split("CELL_TEXT_CAP = ")[1].split(";")[0])
        over = [v[:60] for v in drawn["visible"] if len(v) > cap]
        assert over == [], f"{name}: visible cell text over {cap}: {over}"


@needs_node
class TestTheCellStaysACell:
    def test_no_section_appears_inside_a_cell(self):
        """`UX-267`'s reason for `buildTable` existing at all: `nav.js`
        finds sections at any depth, so one in a cell is a phantom entry
        in the table of contents."""
        for name, value in SHAPES.items():
            drawn = _cells([{"key": name, "value": value}])
            assert drawn["sections_in_cells"] == 0, name

    def test_no_pre_appears_inside_a_cell(self):
        for name, value in SHAPES.items():
            drawn = _cells([{"key": name, "value": value}])
            assert drawn["pre_in_cells"] == 0, name

    def test_data_raw_still_carries_the_unrendered_value(self):
        """Sorting, filtering and `Copy shown rows` read `data-raw`. If
        it started carrying markup they would silently change what they
        compare and what they copy."""
        drawn = _cells([{"key": "rule", "value": SHAPES["rule"]}])
        raws = [r for r in drawn["raw"] if r]
        assert any(r.startswith("{") and "CHAIN_BOUND_RATIO" in r
                   for r in raws), raws
        assert not any("<" in r for r in raws), raws


@needs_node
class TestTheNestingIsBounded:
    # The bound this guard defends, written here rather than read from
    # the module. The first draft read `CELL_NEST_LIMIT` out of
    # `app.js` and asserted the measured depth against it - so raising
    # the constant raised the bar with it and the mutation passed. A
    # guard that checks the code against itself checks nothing; the
    # number it defends has to be stated somewhere the code cannot move.
    NESTING_BOUND = 2

    def test_a_cell_does_not_nest_tables_without_end(self):
        """A cell may hold a table whose cells hold one more, and no
        further. The document is seven levels deep, and seven nested
        tables is seven sets of column headers for one value."""
        deep = {"a": {"b": {"c": {"d": {"e": {"f": {"g": 1, "h": 2}}}}}}}
        drawn = _cells([{"key": "deep", "value": deep}])
        assert drawn["table_depth"] <= self.NESTING_BOUND, (
            f"tables nest {drawn['table_depth']} deep inside a cell, against "
            f"a bound of {self.NESTING_BOUND}")

    def test_the_module_still_declares_the_bound_this_guard_defends(self):
        """And the other direction, so the two cannot drift silently:
        moving `CELL_NEST_LIMIT` is a decision, and it reddens here
        until the guard is updated to match it deliberately."""
        declared = int(APP.split("CELL_NEST_LIMIT = ")[1].split(";")[0])
        assert declared == self.NESTING_BOUND, (
            f"app.js declares CELL_NEST_LIMIT = {declared} and this guard "
            f"defends {self.NESTING_BOUND}. If the bound moved on purpose, "
            f"move it here too and say why in the task file.")

    def test_the_limit_still_shows_what_is_behind_it(self):
        """Bounded is not hidden: past the limit the value folds with
        its label and count, so the reader knows something is there."""
        deep = {"a": {"b": {"c": {"d": {"e": 1}}}}}
        drawn = _cells([{"key": "deep", "value": deep}])
        assert drawn["folds_in_cells"] >= 1
        assert any(v.strip() for v in drawn["visible"]), drawn["visible"]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
