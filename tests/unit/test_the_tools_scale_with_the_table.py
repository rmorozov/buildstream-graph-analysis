"""UX-349: apparatus a table did not need, on every table.

The report carries a lot of controls. Measured on a real boot when this
was worked:

```text
                buttons  inputs  selects  links   total
golden              257      48        9    123     437
macro_micro         341      81       19    222     663
```

Most of the inputs were one thing: a threshold filter per quantity
column, and a search box per table, given to every table whatever its
length.

```text
                tables   of which <=12 rows and filtered
golden              13                    12
macro_micro         22                    21
```

Twelve of golden's thirteen tables are short enough to read at a glance
and carried a filter row anyway. On the eleven-row element table that
is five inputs above eleven rows, and one of them sat under a boolean
column with the placeholder `> 10`.

The three rules this file holds:

- **filters appear when the table is long enough to need them** - the
  row cap §3 already sets, the same number that decides whether a
  table opens bounded, because it is the same question;
- **a column with one distinct value is stated once and not drawn** -
  `false` eleven times under `Is leaf` is a fact about the table, not
  a column;
- **a threshold box goes only where the column holds numbers** - `> 10`
  under a boolean is the tell of a quantity that was *guessed* rather
  than declared.

Sorting is deliberately untouched: it costs one header affordance at
any length and helps at every one, so there is nothing for a threshold
to scale.
"""
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

from browser import NO_BROWSER, Browser, find_chrome    # noqa: E402

FIXTURES = {"golden": REPO / "tests/fixtures/golden/mixed_task_kinds",
            "macro_micro": REPO / "tests/fixtures/macro_micro/run"}
chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)


def _row_cap():
    """The bound, read from the module that sets it.

    Not repeated here: `UX-349` made the filter row's threshold *the*
    row cap rather than a second number, and a guard carrying its own
    40 would pass a round that moved the rule.
    """
    source = (REPO / "bga/viewer/structured.js").read_text(encoding="utf-8")
    found = re.search(r"TABLE_OPENS_BOUNDED_ABOVE\s*=\s*(\d+)", source)
    assert found, "structured.js no longer names the row cap"
    return int(found.group(1))


_LOOK = """
(() => {
  for (const box of document.querySelectorAll("section.chapter")) {
    box.setAttribute("data-open", "true");
  }
  const tables = [...document.querySelectorAll("table[data-table]")].map((t) => {
    const scope = t.parentElement?.parentElement ?? t.parentElement;
    const rows = t.querySelectorAll("tbody tr").length;
    const columns = [...t.querySelectorAll("th[data-column]")]
      .map((h) => h.getAttribute("data-column"));
    const uniform = [];
    for (const column of columns) {
      const cells = [...t.querySelectorAll(`td[data-column="${column}"]`)]
        .map((td) => td.textContent);
      if (cells.length > 3 && new Set(cells).size === 1) {
        uniform.push([column, cells[0]]);
      }
    }
    const thresholds = [...t.querySelectorAll("input.th-filter")].map((i) => {
      const column = i.getAttribute("data-column");
      const cells = [...t.querySelectorAll(`td[data-column="${column}"]`)]
        .map((td) => td.getAttribute("data-raw"));
      return { column, placeholder: i.placeholder,
               numeric: cells.some((raw) => Number.isFinite(Number(raw))) };
    });
    return {
      table: t.getAttribute("data-table"), rows, uniform, thresholds,
      search: scope?.querySelectorAll("input.table-filter").length ?? 0,
      sortable: t.querySelectorAll("th[aria-sort]").length
        + t.querySelectorAll("th[data-column]").length,
      note: (scope?.querySelector('[data-role="uniform-columns"]')
        ?.textContent || "").trim(),
    };
  });
  return {
    tables,
    buttons: document.querySelectorAll("button").length,
    inputs: document.querySelectorAll("input").length,
    selects: document.querySelectorAll("select").length,
    links: document.querySelectorAll("a").length,
  };
})()
"""


node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")

#: A long table with a boolean column beside a duration one. Long,
#: because a short one has no filter row at all now - which is why the
#: page-level clause below cannot see this rule any more, and why this
#: one drives the renderer directly.
_MIXED = """
const app = await import("./tests/viewer.mjs");
const rows = Array.from({ length: 48 }, (_, i) => ({
  element_uid: `e${i}.bst`, duration_us: 1000 + i, is_leaf: i %% 2 === 0,
  kind: "cmake",
}));
const hint = { "bga:columns": [
  { key: "element_uid", title: "Element", role: "element" },
  { key: "duration_us", title: "Duration", quantity: "duration_us" },
  // `count`, exactly as the element-join builder hands it over: that
  // path ends `?? guessQuantity(name) ?? "count"`, so a boolean column
  // arrives declared a count and earns a `> 10` box. Written out here
  // rather than left to the guess, because `guessQuantity("is_leaf")`
  // is null - it is the *join's* fallback that produces the defect.
  { key: "is_leaf", title: "Is leaf", quantity: "count" },
  { key: "kind", title: "Kind" } ] };
const root = make("div");
root.append(app.renderTable("elements", rows, hint));
const table = root.querySelectorAll("table[data-table]")[0];
console.log(JSON.stringify({
  thresholds: root.querySelectorAll("input.th-filter").map(
    (i) => i.getAttribute("data-column")),
  search: root.querySelectorAll("input.table-filter").length,
  columns: table.querySelectorAll("th[data-column]").map(
    (h) => h.getAttribute("data-column")),
  note: (root.querySelectorAll('[data-role="uniform-columns"]')[0]
    ?.textContent ?? ""),
}));
"""


_SHIM = """
globalThis._makeNode ??= (await import(process.env.BGA_DOM_SHIM)).makeNode;
function make(tag) {
  const node = _makeNode(tag);
  node.open = false;
  return node;
}
globalThis.Event = class { constructor(type) { this.type = type; } };
globalThis.document = { createElement: make, createElementNS: (_n, t) => make(t),
                        getElementById: () => null };
"""


def _mixed_table():
    done = subprocess.run(
        [node, "--input-type=module", "-e", _SHIM + (_MIXED % ())],
        capture_output=True, text=True, cwd=REPO, timeout=120,
        env={**os.environ,
             "BGA_DOM_SHIM": (REPO / "tests/dom_shim.mjs").as_uri()})
    assert done.returncode == 0, done.stderr[-2000:]
    return json.loads(done.stdout)


@needs_node
class TestAThresholdBoxNeedsANumber:
    """Driven directly, because the page cannot show it any more.

    With filters gated to the row cap, neither fixture has a threshold
    box at all - so the page-level clause below is 0 of 0 there, and a
    mutation that put a box back over a boolean column passed it. This
    is the case the item was filed on (`> 10` under `Is leaf`), on a
    table long enough to have the tools.
    """

    def test_a_boolean_column_gets_no_threshold(self):
        out = _mixed_table()
        assert out["search"] == 1, out
        assert "duration_us" in out["thresholds"], out
        assert "is_leaf" not in out["thresholds"], (
            "a boolean column carries a numeric threshold box; its "
            "quantity was guessed `count`, never declared")

    def test_the_uniform_column_is_stated_and_gone(self):
        """The same table proves the second rule: `kind` is `cmake` in
        all forty-eight rows, `is_leaf` alternates and stays."""
        out = _mixed_table()
        assert "kind" not in out["columns"], out["columns"]
        assert "is_leaf" in out["columns"], out["columns"]
        assert "Kind cmake" in out["note"], out["note"]


@pytest.fixture(scope="module")
def browser():
    with Browser(chrome) as opened:
        yield opened


@pytest.fixture(scope="module")
def pages(tmp_path_factory):
    import tools.bga_view as view

    made = {}
    for name, fixture in FIXTURES.items():
        run = tmp_path_factory.mktemp(f"tools-{name}") / "run"
        shutil.copytree(fixture, run)
        (run / "expected_output.json").unlink(missing_ok=True)
        page = tmp_path_factory.mktemp(f"tools-page-{name}") / "report.html"
        view.export(str(run), str(page))
        made[name] = page.as_uri()
    return made


@needs_browser
@pytest.mark.medium
@pytest.mark.parametrize("label", sorted(FIXTURES))
class TestAFilterAppearsWhereItHelps:
    def test_no_table_under_the_cap_carries_a_filter(
            self, browser, pages, label):
        """The acceptance's first clause."""
        cap = _row_cap()
        out = browser.measure(pages[label], _LOOK, 1440, 900)
        bad = [t for t in out["tables"]
               if t["rows"] <= cap and (t["search"] or t["thresholds"])]
        assert bad == [], (
            f"{label}: {len(bad)} table(s) at or under {cap} rows carry "
            f"filters: "
            + ", ".join(f"{t['table']} ({t['rows']} rows, {t['search']} "
                        f"search + {len(t['thresholds'])} thresholds)"
                        for t in bad[:6]))

    def test_the_population_is_the_page(self, browser, pages, label):
        """A page with no tables passes the clause above forever, and a
        page where every table happens to be long would too. Both
        fixtures are short-table pages, which is exactly why the
        finding was about them."""
        out = browser.measure(pages[label], _LOOK, 1440, 900)
        assert len(out["tables"]) >= 10, len(out["tables"])
        short = [t for t in out["tables"] if t["rows"] <= _row_cap()]
        assert len(short) >= 10, (
            f"{label}: only {len(short)} short tables - this page no longer "
            f"exercises the rule")

    def test_sorting_survives(self, browser, pages, label):
        """Explicitly out of scope, and worth asserting: the fix is a
        threshold on *filters*, not a general stripping of the header."""
        out = browser.measure(pages[label], _LOOK, 1440, 900)
        assert all(t["sortable"] for t in out["tables"]), (
            [t["table"] for t in out["tables"] if not t["sortable"]])


@needs_browser
@pytest.mark.medium
@pytest.mark.parametrize("label", sorted(FIXTURES))
class TestAColumnThatNeverVariesIsASentence:
    def test_no_rendered_column_repeats_itself(self, browser, pages, label):
        """The acceptance's second clause. Over more than three rows,
        because two rows that agree are a coincidence rather than a
        fact about a population - `UX-226`'s floor, applied to width."""
        out = browser.measure(pages[label], _LOOK, 1440, 900)
        bad = [(t["table"], column, value)
               for t in out["tables"] for column, value in t["uniform"]]
        assert bad == [], (
            f"{label}: {len(bad)} column(s) with one distinct value over "
            f"more than three rows: {bad[:6]}")

    def test_what_was_removed_is_said(self, browser, pages, label):
        """Removed is not the same as hidden. A column that goes must
        leave its fact behind, or the reader has lost something the
        payload published."""
        out = browser.measure(pages[label], _LOOK, 1440, 900)
        noted = [t for t in out["tables"] if t["note"]]
        assert noted, (
            f"{label}: no table states a uniform column - both fixtures "
            f"had one when this was measured, so the walk has broken")
        for table in noted:
            assert table["note"].startswith("All "), table
            assert table["note"].endswith("."), table


@needs_browser
@pytest.mark.medium
@pytest.mark.parametrize("label", sorted(FIXTURES))
class TestAThresholdGoesWhereANumberIs:
    def test_every_threshold_box_sits_over_numbers(
            self, browser, pages, label):
        """The acceptance's third clause. `> 10` under a boolean was
        the tell: the column's quantity was `count` by the fallback in
        `columnSpecs`, never declared, and the box read the guess."""
        out = browser.measure(pages[label], _LOOK, 1440, 900)
        bad = [(t["table"], box["column"], box["placeholder"])
               for t in out["tables"] for box in t["thresholds"]
               if not box["numeric"]]
        assert bad == [], (
            f"{label}: threshold box over a column with no numbers: {bad}")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
