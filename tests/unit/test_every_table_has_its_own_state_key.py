"""UX-292: a table's view state belongs to that table.

`UX-211` keys every table's view state by the table's own name —
`f.<table>` for its filter, `t.<table>.<column>` for a threshold,
`s.<table>` for the sort, `n.<table>` for the bound, `v.<table>` for
`UX-289`'s named view — so that "here is the report, filtered the way I
was reading it" is a link somebody can paste.

The key was the payload field the table was built from, and a *nested*
table is built from the cell it sits in. Every map table's cells are in
a column called `value`, so `renderStructured` named all of them
`value`. Measured on both runs before this landed:

```text
                    tables  distinct keys  repeated
macro_micro (11)        40             28  {"value": 13}
synthetic  (1,202)      38             26  {"value": 13}
```

**Thirteen tables answered to `f.value`.** A filter typed into one was
captured once and applied, on the other side of the link, to whichever
of the thirteen the loop reached first.

Not a regression: `UX-277` made these tables. Before it they were
stringified cells, which carried no state and so could not collide —
the affordance arrived without a name to hang it on.

After: every table on the page carries a distinct key, built from the
path it sits at plus the row it is nested in.

```text
macro_micro (11)        40             40  {}
synthetic  (1,202)      38             38  {}
```
"""
import json
import os
import pathlib
import shutil
import subprocess

import pytest

from bga import schemas

REPO = pathlib.Path(__file__).resolve().parents[2]
RUN = REPO / "tests/fixtures/macro_micro/run"
node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")


@pytest.fixture(scope="module")
def payload():
    done = subprocess.run(
        ["python", "-m", "bga.cli", "analyze", str(RUN), "--format", "json"],
        capture_output=True, text=True, cwd=REPO, timeout=180)
    assert done.returncode == 0, done.stderr[-2000:]
    return json.loads(done.stdout)


_HARNESS = r"""
globalThis._makeNode ??= (await import(process.env.BGA_DOM_SHIM)).makeNode;
const mk = (tag) => _makeNode(tag);
globalThis.Event ??= class { constructor(t, o = {}) { this.type = t; Object.assign(this, o); } };
globalThis.document = { createElement: mk, createElementNS: (_n, t) => mk(t),
                        getElementById: () => null, body: mk("body") };
globalThis.window = { location: { hash: "", search: "" }, addEventListener() {},
                      matchMedia: () => ({ matches: false, addEventListener() {} }) };
const app = await import("%(app)s");
const viewstate = await import("%(viewstate)s");
const { readFileSync } = await import("node:fs");
const root = mk("div");
app.render(JSON.parse(readFileSync(%(payload)s, "utf8")),
           JSON.parse(readFileSync(%(schema)s, "utf8")), root);

const tables = root.querySelectorAll("table[data-table]");
const keys = tables.map((t) => t.getAttribute("data-table"));

// Type a filter into one nested table and read the fragment back: the
// state must name *that* table, and applying the fragment to a fresh
// page must put it back in the same one.
// A `map-table` div holds its own tools and then its own table, and
// `querySelectorAll` walks in document order - so the first of each
// inside the div belongs to the div, not to anything nested deeper.
// The first draft guessed at the parent chain and typed into a
// different table's box entirely, which is what this measures.
let roundTrip = null;
for (const box of root.querySelectorAll("div.map-table")) {
  const table = box.querySelectorAll("table[data-table]")[0];
  const filter = box.querySelectorAll("input.table-filter")[0];
  if (!table || !filter) continue;
  const key = table.getAttribute("data-table");
  if (!key.includes(".")) continue;
  filter.value = "zzz-no-such-row";
  filter.dispatchEvent(new Event("input", { bubbles: true }));
  const captured = viewstate.captureView(root);
  roundTrip = { key, captured,
                names_the_table: captured.includes(`f.${key}=`) };
  break;
}
console.log(JSON.stringify({
  tables: keys.length,
  distinct: new Set(keys).size,
  keys,
  roundTrip,
}));
"""


def _page(payload):
    import tempfile
    scratch = tempfile.mkdtemp()
    try:
        run = pathlib.Path(scratch, "payload.json")
        run.write_text(json.dumps(payload), encoding="utf-8")
        doc = pathlib.Path(scratch, "schema.json")
        doc.write_text(json.dumps(schemas.schema(schemas.ANALYZE)),
                       encoding="utf-8")
        script = _HARNESS % {
            "app": (REPO / "bga/viewer/app.js").as_uri(),
            "viewstate": (REPO / "bga/viewer/viewstate.js").as_uri(),
            "payload": json.dumps(str(run)), "schema": json.dumps(str(doc))}
        done = subprocess.run([node, "--input-type=module", "-e", script],
                              capture_output=True, text=True, cwd=REPO,
                              timeout=120,
                              env={**os.environ, "BGA_DOM_SHIM":
                                   (REPO / "tests/dom_shim.mjs").as_uri()})
        assert done.returncode == 0, done.stderr[-3000:]
        return json.loads(done.stdout)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


@needs_node
class TestEveryTableIsAddressable:
    def test_no_two_tables_share_a_key(self, payload):
        drawn = _page(payload)
        seen, repeated = set(), {}
        for key in drawn["keys"]:
            if key in seen:
                repeated[key] = repeated.get(key, 1) + 1
            seen.add(key)
        assert repeated == {}, (
            f"{len(drawn['keys'])} tables, {drawn['distinct']} distinct keys; "
            f"table(s) sharing one: {repeated}")

    def test_the_page_really_has_nested_tables(self, payload):
        """The claim above is empty on a page with no nesting, and this
        run's nesting is exactly what made the keys collide. `UX-276`'s
        rule about a sweep that finds nothing versus one that looks
        nowhere, applied to a fixture."""
        drawn = _page(payload)
        nested = [key for key in drawn["keys"] if "." in key]
        assert len(nested) >= 5, (
            f"only {len(nested)} nested tables on this run; the fixture no "
            f"longer exercises what this guard is about")
        assert drawn["tables"] >= 20, drawn["tables"]

    def test_a_nested_table_is_named_by_where_it_sits(self, payload):
        """Not `value`. The key a reader sees in a pasted link should
        say which table it filtered."""
        drawn = _page(payload)
        assert "value" not in drawn["keys"], (
            "a table is still keyed by the generic column name it sits in")
        for key in drawn["keys"]:
            if "." in key:
                assert not key.endswith(".value"), key

    def test_the_state_names_the_table_it_was_typed_into(self, payload):
        """The whole point, end to end: filter a nested table, and the
        fragment carries that table's key rather than a name thirteen
        tables answer to."""
        drawn = _page(payload)
        trip = drawn["roundTrip"]
        assert trip, "no nested table carried a filter box to test with"
        assert trip["names_the_table"], (
            f"filtering `{trip['key']}` captured `{trip['captured']}`")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
