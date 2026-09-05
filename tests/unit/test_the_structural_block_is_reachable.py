"""UX-283 and UX-290: the bottleneck block, reachable and described.

Reported: *"there is very useful bottleneck view, but it doesn't have
full info - only top findings and no way to go to detailed info."* The
data was all there; every way onward was not. Measured on the
1,202-element run when this was filed:

```text
links out of the entire `structural` section:  0
```

Not one. `choke_points` named nine elements and none was clickable;
`high_fanin_elements` was `[["app.bst", 8], …]` rendered as a flattened
tuple. `UX-277` made those cells tables, and this gives them what every
other element table has - and `UX-290` gives their columns names, since
a table whose headers read `#1` and `#2` is a table that says what
position a number sits at rather than what it measures.

Measured after, on both runs:

```text
                        links out   positional headers (#1, #2, C0, Key)
macro_micro (11)               33                                      0
synthetic  (1,202)             26                                      0
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

# The fields whose members `UX-290` describes, and the block each sits
# in. Named rather than swept: the claim is that *these* are described,
# and a sweep over whatever happens to be declared would pass on a
# schema that described nothing.
DESCRIBED = {
    "bottleneck": ("choke_points", "high_fanin_elements",
                   "high_fanout_elements"),
    "sensitivity": ("top_opportunities",),
    "batch_opportunities": ("serialized_pairs",),
}


@pytest.fixture(scope="module")
def payload():
    done = subprocess.run(
        ["python", "-m", "bga.cli", "analyze", str(RUN), "--format", "json"],
        capture_output=True, text=True, cwd=REPO, timeout=180)
    assert done.returncode == 0, done.stderr[-2000:]
    return json.loads(done.stdout)


_HARNESS = r"""
const shim = await import(process.env.BGA_DOM_SHIM);
globalThis._makeNode ??= shim.makeNode;
globalThis.Event ??= class { constructor(t, o = {}) { this.type = t; Object.assign(this, o); } };
shim.installDocument();
globalThis.window = { location: { hash: "", search: "" }, addEventListener() {},
                      matchMedia: () => ({ matches: false, addEventListener() {} }) };
const app = await import("%(app)s");
const { readFileSync } = await import("node:fs");
const root = shim.makeNode("div");
app.render(JSON.parse(readFileSync(%(payload)s, "utf8")),
           JSON.parse(readFileSync(%(schema)s, "utf8")), root);

// `UX-344`: `structural` was one section holding nine tables; the
// tables are sections of their own now, so "the block" is the set of
// them and the counts below are over all three the schema declares.
const BLOCKS = ["bottleneck", "sensitivity", "batch_opportunities"];
const sections = BLOCKS.flatMap(
  (name) => root.querySelectorAll(`section[data-section="${name}"]`));
const text = (n) => (n.textContent ?? "") + (n.children ?? []).map(text).join("");
const every = (selector) => sections.flatMap((s) => s.querySelectorAll(selector));
const heads = every("th");
console.log(JSON.stringify({
  links_out: sections.length ? every("a.inspect").length : -1,
  sortable: sections.length ? every('th[data-sortable="true"]').length : -1,
  headers: heads.map((h) => text(h).trim()),
  described: heads.filter((h) => h.getAttribute("title")).map(
    (h) => [text(h).trim(), h.getAttribute("title")]),
  element_columns: every("table[data-element-column]").map(
    (t) => t.getAttribute("data-table")),
}));
"""


def _structural(payload):
    import tempfile
    scratch = tempfile.mkdtemp()
    try:
        run = pathlib.Path(scratch, "payload.json")
        run.write_text(json.dumps(payload), encoding="utf-8")
        doc = pathlib.Path(scratch, "schema.json")
        doc.write_text(json.dumps(schemas.schema(schemas.ANALYZE)),
                       encoding="utf-8")
        script = _HARNESS % {
            "app": (REPO / "tests/viewer.mjs").as_uri(),
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


class TestTheSchemaDescribesItsTuples:
    def test_every_named_field_declares_its_members(self):
        properties = schemas.schema(schemas.ANALYZE)["properties"]
        missing = []
        for block, fields in DESCRIBED.items():
            inside = properties.get(block) or {}
            for field in fields:
                declared = ((inside.get("properties") or {}).get(field)
                            or {}).get(schemas.COLUMNS)
                if not declared:
                    missing.append(f"{block}.{field}")
        assert missing == [], f"undeclared: {missing}"

    def test_a_declared_column_says_what_it_is(self):
        """A title alone renames a position. `UX-201`'s promise is that
        a field gaining a *description* gains a tooltip, so a
        declaration with no description keeps the old defect wearing a
        better name."""
        properties = schemas.schema(schemas.ANALYZE)["properties"]
        bare = []
        for block, fields in DESCRIBED.items():
            inside = properties.get(block) or {}
            for field in fields:
                for column in (((inside.get("properties") or {}).get(field)
                                or {}).get(schemas.COLUMNS) or []):
                    if not column.get("title"):
                        bare.append(f"{block}.{field}.{column.get('key')}")
        assert bare == [], f"column(s) with no title: {bare}"

    def test_an_element_column_says_it_holds_elements(self):
        """What earns the row its Inspect, and the reason the section
        had zero links out of it: `UX-208`'s affordance is driven by the
        declaration, so an undeclared element column gets nothing."""
        properties = schemas.schema(schemas.ANALYZE)["properties"]
        for block, fields in DESCRIBED.items():
            inside = properties.get(block) or {}
            for field in fields:
                columns = (((inside.get("properties") or {}).get(field)
                            or {}).get(schemas.COLUMNS) or [])
                roles = [c.get("role") for c in columns]
                assert "element" in roles, f"{block}.{field} names no element"


@needs_node
class TestTheBlockIsReachable:
    def test_the_section_has_links_out_of_it(self, payload):
        drawn = _structural(payload)
        assert drawn["links_out"] > 0, (
            "the graph-shape sections still carry no route to an element")

    def test_every_element_table_in_it_carries_the_route(self, payload):
        """Not "some link exists somewhere" - each element table earns
        the same Inspect column every other one has."""
        drawn = _structural(payload)
        assert len(drawn["element_columns"]) >= 4, drawn["element_columns"]

    def test_the_choke_points_can_be_sorted(self, payload):
        drawn = _structural(payload)
        assert drawn["sortable"] > 0, "nothing in those sections sorts"

    def test_no_header_names_a_position(self, payload):
        """`UX-290`'s acceptance. `#1`, `#2`, `C0` and `Key` name where a
        value sits in a data structure rather than what it measures."""
        positional = [h for h in drawn_headers(payload)
                      if h in ("#1", "#2", "#3", "C0", "C1", "Key")]
        assert positional == [], f"positional header(s): {positional}"

    def test_a_described_column_carries_its_description(self, payload):
        """`UX-201`'s promise, made good for these fields: the schema's
        own sentence is the tooltip, with no page edit."""
        drawn = _structural(payload)
        titled = dict(drawn["described"])
        assert titled, "no column in those sections carries a tooltip"
        assert any("downstream" in text.lower() for text in titled.values()), (
            f"the choke-point column's sentence is not among {titled}")


def drawn_headers(payload):
    return list(_structural(payload)["headers"])


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
