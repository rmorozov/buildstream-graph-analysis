"""UX-532 + UX-526: two row selectors, merged into one, over both claims.

Round 80 ran the two as parallel tracks and each gave `tables.js` a row
selector. `UX-532`'s reads the table's **own** rows, because a cell can
hold a whole table and `querySelectorAll("tr")` counted the nested rows
as the outer table's - 660 over 60. `UX-526`'s reads **every** row, held
or shown, because a row past the bound now leaves the document and a
strip labelled "across all 1,202 rows" drawn from 25 is the wrong
population.

Neither track could see the other's claim, and their two families
(`ownRows`/`ownCells`, `everyRow`/`columnCells`) each break the other's:
descending finds the nested rows, and reading the tbody's children misses
the held ones. The merge is one family that answers both, and this file
is where that is checked - the shape neither track had a fixture for.
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

#: A tbody with `OUTER` own rows, each holding a nested table of
#: `INNER` rows, then bounded to `SHOWN` of them. Built by hand rather
#: than through `renderTable`: the claim is about the selectors, and a
#: fixture that goes through the whole builder cannot say which of the
#: two readings produced a number.
OUTER, INNER, SHOWN = 12, 5, 4

_PROBE = r"""
const shim = await import(process.env.BGA_DOM_SHIM);
shim.installDocument();
const t = await import(process.env.BGA_TABLES);
const OUTER = __OUTER__, INNER = __INNER__, SHOWN = __SHOWN__;

const el = (tag, attrs = {}, ...kids) => {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  for (const kid of kids) node.append(kid);
  return node;
};

const table = el("table");
const body = el("tbody");
table.append(body);
for (let i = 0; i < OUTER; i++) {
  const cell = el("td", { "data-column": "size", "data-raw": String(i) });
  const inner = el("table");
  const innerBody = el("tbody");
  inner.append(innerBody);
  for (let j = 0; j < INNER; j++) {
    innerBody.append(el("tr", {},
      el("td", { "data-column": "size", "data-raw": "999" })));
  }
  cell.append(inner);
  body.append(el("tr", {}, cell));
}

const out = {};
out.beforeTheBound = {
  everyRow: t.everyRow(body).length,
  ownRows: t.ownRows(table).length,
  columnCells: t.columnCells(table, "size").length,
  nestedRaw: t.columnCells(table, "size").map((td) =>
    td.getAttribute("data-raw")).filter((v) => v === "999").length,
};
// The bound, by the same door the page uses.
t.applyFilters(table, { top: { n: SHOWN, column: "size" } });
out.attached = [...body.children].filter(
  (n) => String(n.tagName).toLowerCase() === "tr").length;
out.afterTheBound = {
  everyRow: t.everyRow(body).length,
  ownRows: t.ownRows(table).length,
  columnCells: t.columnCells(table, "size").length,
  nestedRaw: t.columnCells(table, "size").map((td) =>
    td.getAttribute("data-raw")).filter((v) => v === "999").length,
};
console.log(JSON.stringify(out));
""".replace("__OUTER__", str(OUTER)).replace("__INNER__", str(INNER)).replace("__SHOWN__", str(SHOWN))


@pytest.fixture(scope="module")
def probed():
    done = subprocess.run(
        [node, "--input-type=module", "-e", _PROBE],
        capture_output=True, text=True, cwd=REPO, timeout=120,
        env={**os.environ,
             "BGA_DOM_SHIM": (REPO / "tests/dom_shim.mjs").as_uri(),
             "BGA_TABLES": (REPO / "bga/viewer/tables.js").as_uri()})
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


@needs_node
@pytest.mark.small
class TestOneSelectorAnswersBothClaims:

    def test_the_nested_rows_are_never_this_tables_rows(self, probed):
        """`UX-532`. `querySelectorAll` would read
        OUTER * (1 + INNER) here."""
        assert probed["beforeTheBound"]["everyRow"] == OUTER, probed
        assert probed["beforeTheBound"]["ownRows"] == OUTER, probed

    def test_a_nested_cell_is_never_this_tables_cell(self, probed):
        """The same claim through the column door: `999` is the nested
        tables' value and no reading of this column may contain it."""
        assert probed["beforeTheBound"]["nestedRaw"] == 0, probed
        assert probed["afterTheBound"]["nestedRaw"] == 0, probed

    def test_the_bound_takes_the_rows_out_of_the_document(self, probed):
        """`UX-526`'s mechanism, stated so the next clause means
        something: the tbody really does hold only the shown rows."""
        assert probed["attached"] == SHOWN, probed

    def test_every_row_survives_the_bound(self, probed):
        """`UX-526`. A reading that walked the tbody's children would
        say SHOWN here, which is the wrong-population defect."""
        assert probed["afterTheBound"]["everyRow"] == OUTER, probed
        assert probed["afterTheBound"]["ownRows"] == OUTER, probed

    def test_a_column_reads_every_row_after_the_bound(self, probed):
        """The two together: over every own row, and no nested one."""
        assert probed["afterTheBound"]["columnCells"] == OUTER, probed
        assert probed["beforeTheBound"]["columnCells"] == OUTER, probed


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
