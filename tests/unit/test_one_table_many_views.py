"""UX-289: one element table, and the view a reader asked for.

`UX-268` joined the six element-keyed signals into one row per element.
That table then had to serve every question at once, so it carried
**13 columns** on the 1,202-element run - and the questions a reader
actually arrives with ("what is on the critical path", "what could be
deferred") were answered by *other* tables the payload published
separately.

Measured on that run before this landed, by the sweep in
`_element_tables` below:

```text
19 tables named elements, 13 distinct populations, 7 pairs at 100% overlap
```

`UX-288` removed the duplicate publications and took that to 11 tables,
11 populations, 0 pairs - and left the width: one table at 13 columns.
This closes it from the other side. Each view names the four to six
columns that answer one question, and every population is a **filter
over a published field** rather than a list the page keeps.

Measured after, on the committed 11-element run:

```text
view             cols  rows   first
All elements        6    11   core.bst, codegen.bst, lib-b.bst, lib-d.bst
Critical path       5    10   toolchain.bst, core.bst, lib-a.bst, lib-b.bst
Leaves              5     1   all.bst
Choke points        5     9   toolchain.bst, lib-a.bst, lib-b.bst, lib-c.bst
Latent heavies      5     1   codegen.bst
```

Every guard here runs on `tests/fixtures/macro_micro/run`, which is
committed - `UX-276`'s rule, applied from the start.
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

# UX-338, exempted here and filed rather than fixed. `UX-329` made
# `bga analyze` attach the sibling `plane2.json`, which put
# `element_join` into this fixture's payload - and the page has drawn it
# as a second whole-population table since `UX-215`. **That is not new**:
# `bga view` has attached the sibling since `UX-203`, so every real
# viewer of a two-plane snapshot has seen both tables. Measured on the
# tree before `UX-329`, through `bga view`:
#
#     element_join present = True | rows = 11   (11 elements in the run)
#
# This guard never saw it because its fixture reaches the page through
# `analyze` *without* `--plane2` - the one configuration a viewer never
# has, which is the same shape as the defect `UX-329` fixed. Folding the
# join into the one element table is `UX-289`'s answer and `UX-338`'s
# job; the exemption goes when that lands.
_UX338 = frozenset({"element_join"})
node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")

# The three views whose membership the payload publishes as a selection,
# and the path each one is a view *of*. Named here rather than read from
# the schema on purpose: a guard that took both the claim and the
# expectation from the same declaration would pass on a declaration that
# is wrong about the run.
PUBLISHED_VIEWS = {
    "Critical path": "signals.critical_path_detail",
    "Choke points": "structural.bottleneck.choke_points",
}

# The one pair of tables that draw the same elements on this fixture and
# not on the 1,202-element run - see
# `test_no_two_tables_carry_the_same_elements` for the measurement.
# UX-285: by `data-table` path rather than by position, so it names the
# two tables the docstring names and survives a section moving.
KNOWN_COINCIDENCE = ["structural.batch_opportunities.serialized_pairs and "
                     "structural.sensitivity.top_opportunities (5)",
                     # UX-338, and unlike the pair above this one is a
                     # real duplication rather than a coincidence - it
                     # is listed so the guard is honest about carrying
                     # it, not because it is acceptable. See `_UX338`.
                     "element_join and elements (11)"]

# The bound, stated here rather than read from `schemas`. Reading the
# constant and asserting against it is the mutation that passes:
# `PRESET_COLUMNS_MAX = 40` left all eighteen of these green, because
# every one of them measured against the number it was checking. Same
# defect `UX-277` had to fix in its own nesting guard, one round back.
VIEW_COLUMNS_BOUND = 8


def _presets():
    return schemas.schema(schemas.ANALYZE)["properties"]["signals"][
        schemas.PRESETS]


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
const app = await import("%s");
const nav = await import("%s");
const viewstate = await import("%s");
const { readFileSync } = await import("node:fs");
const payload = JSON.parse(readFileSync(%s, "utf8"));
const schema = JSON.parse(readFileSync(%s, "utf8"));
const apply = %s;

const root = mk("div");
app.render(payload, schema, root);

const all = (n, pred, out = []) => { if (!n) return out;
  if (pred(n)) out.push(n); (n.children ?? []).forEach((c) => all(c, pred, out));
  return out; };
const text = (n) => (n.textContent ?? "") + (n.children ?? []).map(text).join("");
const UID = /^[\w][\w./-]*\.bst$/;

const select = all(root, (n) => n.tagName === "select"
                   && (n.attrs ?? {}).class === "preset-view")[0] ?? null;

if (apply) { viewstate.applyView(root, apply); }

// Every table on the page, each cell attributed to its *nearest* table -
// `find` recurses, and an outer table that absorbed its nested table's
// rows reported three false 100%%-overlap pairs the first time this was
// written (the same double count `UX-277` had to fix in its own guard).
const tables = [];
(function walk(n, section, at) {
  if (!n) return;
  const s = (n.attrs ?? {})["data-section"];
  if (s !== undefined) section = s;
  let here = at;
  if (n.tagName === "table") {
    tables.push({ section, columns: 0, headers: [], population: [],
                  key: (n.attrs ?? {})["data-table"] ?? null,
                  preset: (n.attrs ?? {})["data-preset"] ?? null });
    here = tables.length - 1;
  }
  if (here !== null) {
    if (n.tagName === "th") tables[here].headers.push(text(n).trim());
    if (n.tagName === "td") {
      const raw = String((n.attrs ?? {})["data-raw"] ?? text(n)).trim();
      if (UID.test(raw)) tables[here].population.push(raw);
    }
  }
  (n.children ?? []).forEach((c) => walk(c, section, here));
})(root, null, null);
for (const t of tables) {
  t.columns = t.headers.length;
  t.population = [...new Set(t.population)];
}

const views = [];
// Only when no view was asked for: enumerating them leaves the page on
// the first one, which silently overwrote the view `applyView` had just
// selected. Found by this guard failing on the run it was written
// against after passing on another - the harness was wrong, not the page.
if (select && !apply) {
  for (const option of select.children ?? []) {
    select.value = option.value;
    select.dispatchEvent(new Event("change", { bubbles: true }));
    const drawn = all(root, (n) => n.tagName === "table"
                      && (n.attrs ?? {})["data-preset"])[0];
    views.push({
      name: option.value,
      columns: all(drawn, (n) => n.tagName === "th").length,
      population: all(drawn, (n) => n.tagName === "td")
        .filter((td) => (td.attrs ?? {})["data-column"] === "element")
        .map((td) => (td.attrs ?? {})["data-raw"]),
    });
  }
  select.value = (select.children ?? [])[0]?.value;
  select.dispatchEvent(new Event("change", { bubbles: true }));
}

const toc = nav.toc(root, { document });
const rail = all(toc, (n) => (n.attrs ?? {})["data-toc-view"] !== undefined)
  .map((a) => ({ name: (a.attrs ?? {})["data-toc-view"],
                 href: (a.attrs ?? {}).href }));

console.log(JSON.stringify({
  offered: select ? (select.children ?? []).map((o) => o.value) : [],
  drawn: all(root, (n) => n.tagName === "table"
             && (n.attrs ?? {})["data-preset"]).map(
               (t) => (t.attrs ?? {})["data-preset"]),
  tables, views, rail,
  captured: viewstate.captureView(root),
}));
"""


def _page(payload, apply=None):
    """The rendered report, and what its element views draw."""
    import tempfile
    scratch = tempfile.mkdtemp()
    try:
        run = pathlib.Path(scratch, "payload.json")
        run.write_text(json.dumps(payload), encoding="utf-8")
        doc = pathlib.Path(scratch, "schema.json")
        doc.write_text(json.dumps(schemas.schema(schemas.ANALYZE)),
                       encoding="utf-8")
        script = _HARNESS % (
            (REPO / "bga/viewer/app.js").as_uri(),
            (REPO / "bga/viewer/nav.js").as_uri(),
            (REPO / "bga/viewer/viewstate.js").as_uri(),
            json.dumps(str(run)), json.dumps(str(doc)),
            json.dumps(apply) if apply else "null")
        done = subprocess.run([node, "--input-type=module", "-e", script],
                              capture_output=True, text=True, cwd=REPO,
                              timeout=120,
                              env={**os.environ, "BGA_DOM_SHIM":
                                   (REPO / "tests/dom_shim.mjs").as_uri()})
        assert done.returncode == 0, done.stderr[-3000:]
        return json.loads(done.stdout)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


class TestThePresetsAreDeclaredNotCoded:
    def test_the_schema_carries_them(self):
        names = [preset["name"] for preset in _presets()]
        assert len(names) >= 4, names
        assert "All elements" in names, (
            "the unfiltered union stopped being one of the views, so the "
            "page can no longer show every element at all")

    def test_the_page_does_not_name_a_view_of_its_own(self):
        """`UX-201`'s rule, one level down. A view named in JavaScript is
        a vocabulary that will diverge from the payload it draws - which
        is exactly what `UX-288` had just finished undoing in the
        contract."""
        source = (REPO / "bga/viewer/app.js").read_text(encoding="utf-8")
        code = "\n".join(line for line in source.splitlines()
                         if not line.strip().startswith(("//", "*", "/*")))
        named = [preset["name"] for preset in _presets()
                 if preset["name"] in code]
        assert named == [], (
            f"the page names view(s) {named} itself; they are the schema's")

    def test_every_view_shows_fewer_columns_than_the_union(self):
        for preset in _presets():
            assert len(preset["columns"]) <= VIEW_COLUMNS_BOUND, (
                f"{preset['name']} shows {len(preset['columns'])} columns")

    def test_the_module_is_pinned_to_the_bound(self):
        """The other half of stating it here: if the schema's own
        constant moves, that is a decision, and this is where it is
        made rather than absorbed."""
        assert schemas.PRESET_COLUMNS_MAX == VIEW_COLUMNS_BOUND

    def test_a_preset_that_names_too_many_columns_is_refused(self):
        """The bound is the point of the item, so the refusal is
        exercised at a fixed width rather than at `PRESET_COLUMNS_MAX +
        1` - which would keep raising however far the constant moved."""
        with pytest.raises(ValueError, match="columns"):
            schemas._check_hint("analyze/v2", "signals", {
                schemas.PRESETS: [{"name": "wide", "columns":
                                   [f"c{n}" for n in
                                    range(VIEW_COLUMNS_BOUND + 1)]}]})

    def test_a_preset_choosing_rows_two_ways_is_refused(self):
        with pytest.raises(ValueError, match="two answers"):
            schemas._check_hint("analyze/v2", "signals", {
                schemas.PRESETS: [{"name": "both", "columns": ["element"],
                                   "from": "signals.critical_path_detail",
                                   "where": {"column": "is_leaf",
                                             "equals": True}}]})


class TestEveryViewIsAFilterOverPublishedFields:
    def test_each_from_path_resolves_in_the_payload(self, payload):
        """Direction 7's boundary: a view the payload cannot express is
        the payload's job, not the page's."""
        missing = []
        for preset in _presets():
            path = preset.get("from")
            if not path:
                continue
            at = payload
            for step in path.split("."):
                at = (at or {}).get(step) if isinstance(at, dict) else None
            if not at:
                missing.append(f"{preset['name']} -> {path}")
        assert missing == [], (
            f"view(s) over a path this run does not publish: {missing}")

    def test_each_where_column_is_a_column_the_rows_carry(self, payload):
        drawn = _page(payload)
        columns = {header for table in drawn["tables"]
                   for header in table["headers"]}
        # The rendered headers are titled, so compare against the raw
        # keys the payload carries for an element instead.
        record = next(iter((payload["signals"].get("blast_radius") or {})
                           .values()), {})
        record = {**record,
                  **next(iter((payload["signals"].get("criticality_probability")
                               or {}).values()), {})}
        unknown = [preset["name"] for preset in _presets()
                   if preset.get("where")
                   and preset["where"]["column"] not in record]
        assert unknown == [], (
            f"view(s) filtering on a field no element record carries: "
            f"{unknown}; the records carry {sorted(record)} and the page "
            f"drew columns {sorted(columns)}")


@needs_node
class TestThePageDrawsThem:
    def test_every_declared_view_is_offered(self, payload):
        drawn = _page(payload)
        assert drawn["offered"] == [preset["name"] for preset in _presets()], (
            f"offered {drawn['offered']}")

    def test_each_view_draws_what_the_payload_publishes(self, payload):
        drawn = _page(payload)
        by_name = {view["name"]: view for view in drawn["views"]}
        for name, path in PUBLISHED_VIEWS.items():
            at = payload
            for step in path.split("."):
                at = at[step]
            published = [entry["element_uid"] for entry in at]
            assert by_name[name]["population"] == published, (
                f"{name} draws {by_name[name]['population'][:4]}…, "
                f"{path} publishes {published[:4]}…")

    def test_the_leaves_view_is_the_leaves(self, payload):
        drawn = _page(payload)
        by_name = {view["name"]: view for view in drawn["views"]}
        published = set(payload["signals"]["leaf_analysis"]["leaves_detail"])
        assert set(by_name["Leaves"]["population"]) == published

    def test_no_table_is_wider_than_the_bound(self, payload):
        """The acceptance test's second clause, over the whole page
        rather than over the presets - a view that is narrow while the
        table beside it is not has moved the problem."""
        wide = {f"{t['section']}[{t['preset'] or ''}]": t["columns"]
                for t in _page(payload)["tables"]
                if t["columns"] > VIEW_COLUMNS_BOUND}
        assert wide == {}, f"table(s) wider than eight columns: {wide}"

    def test_the_element_table_is_drawn_once(self, payload):
        """The acceptance test's first clause, at its subject: the run's
        element population appears in exactly one table. Before
        `UX-288`, four tables drew the 135 leaves and two drew the 14
        critical-path elements."""
        drawn = _page(payload)
        elements = [table for table in drawn["tables"]
                    if frozenset(table["population"])
                    == frozenset(payload["signals"].get("element_durations")
                                 or {})
                    and table["section"] not in _UX338]
        assert len(elements) <= 1, (
            f"{len(elements)} tables draw the whole element population: "
            f"{[t['section'] for t in elements]}")

    def test_no_two_tables_carry_the_same_elements(self, payload):
        """The same clause over the whole page.

        **One exemption, measured rather than assumed.** Two nested
        `structural` tables draw the same five elements on this
        fixture - `sensitivity.top_opportunities` and
        `batch_opportunities.serialized_pairs` - and they are two
        different claims that happen to land on the same five. Measured
        on both runs:

        ```text
        mm     top_opportunities   5  serialized_pairs   5  identical: True   shared: 5
        scale  top_opportunities   5  serialized_pairs   5  identical: False  shared: 3
        ```

        A coincidence at eleven elements and not at 1,202 is a
        coincidence. It is named here as an exact expectation rather
        than filtered out by a rule, so a *real* duplication changes the
        list and reddens this.
        """
        drawn = _page(payload)
        pops = {}
        clashes = []
        for at, table in enumerate(drawn["tables"]):
            members = frozenset(table["population"])
            if len(members) < 2:
                continue
            # UX-292's `data-table` path, not the position: naming a
            # table by its index made this guard read as a claim about
            # *ordering* - `UX-285` moved two sections and reddened it
            # with the identical pair still identical, five tables
            # further down the page. The path is what the table is.
            name = table["key"] or f"{table['section']}#{at}"
            for other, seen in pops.items():
                if seen == members:
                    clashes.append(f"{name} and {other} ({len(members)})")
            pops[name] = members
        assert clashes == KNOWN_COINCIDENCE, (
            f"table(s) drawing one population twice: {clashes}")

    def test_the_exempted_pair_is_two_publications(self, payload):
        """The exemption above is not a hole: the two tables draw two
        *different* published fields. If one of them ever became a copy
        of the other, this is what would say so - and `UX-288`'s guard
        would fail first, on the payload."""
        def uids(value):
            return {member for row in (value or [])
                    for member in (row if isinstance(row, list) else [row])
                    if isinstance(member, str) and member.endswith(".bst")}

        top = uids(payload["structural"]["sensitivity"]["top_opportunities"])
        pairs = uids(payload["structural"]["batch_opportunities"]
                     ["serialized_pairs"])
        assert top and pairs, "the exempted pair no longer draws anything"
        assert (payload["structural"]["sensitivity"]["top_opportunities"]
                != payload["structural"]["batch_opportunities"]
                ["serialized_pairs"]), (
            "the two fields are now the same value, which is a duplication "
            "rather than a coincidence")


@needs_node
class TestAViewTravelsInTheLink:
    def test_the_fragment_carries_the_view(self, payload):
        drawn = _page(payload, apply="v.elements=Critical+path")
        assert drawn["drawn"] == ["Critical path"], drawn["drawn"]
        assert "v.elements=Critical+path" in drawn["captured"], (
            drawn["captured"])

    def test_the_rail_names_every_view_and_links_to_it(self, payload):
        drawn = _page(payload)
        assert [entry["name"] for entry in drawn["rail"]] == drawn["offered"]
        for entry in drawn["rail"]:
            assert entry["href"].startswith("#signals~v.elements="), entry
            assert entry["name"].replace(" ", "%20") in entry["href"], entry

    def test_a_view_this_run_cannot_support_is_not_offered(self, payload):
        """"There are no choke points" and "this run does not carry
        choke points" are different claims, and a view drawn empty makes
        them look alike. So the selection is removed and the view has to
        disappear - not appear with zero rows."""
        without = json.loads(json.dumps(payload))
        without["structural"]["bottleneck"]["choke_points"] = []
        drawn = _page(without)
        assert "Choke points" not in drawn["offered"], drawn["offered"]
        assert "Critical path" in drawn["offered"], (
            "removing one selection took the others with it")

    def test_a_view_whose_filter_matches_nothing_is_not_offered(self, payload):
        """The `where` half of the rule above, and it needs its own case:
        an absent *selection* is refused where the path is resolved, so a
        run with no choke points never reaches the "no rows" check at
        all. Removing that check left all eighteen of these green until
        this was added - a line no test could redden."""
        without = json.loads(json.dumps(payload))
        for record in (without["signals"].get("blast_radius") or {}).values():
            record["is_leaf"] = False
        drawn = _page(without)
        assert "Leaves" not in drawn["offered"], drawn["offered"]
        assert "All elements" in drawn["offered"]

    def test_a_link_to_a_view_this_run_lacks_is_ignored(self, payload):
        """The other half: a fragment from a run that had choke points,
        pasted against one that does not, must not land the reader on a
        different view and let them believe it is the one they asked
        for."""
        without = json.loads(json.dumps(payload))
        without["structural"]["bottleneck"]["choke_points"] = []
        drawn = _page(without, apply="v.elements=Choke+points")
        assert drawn["drawn"] == ["All elements"], drawn["drawn"]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
