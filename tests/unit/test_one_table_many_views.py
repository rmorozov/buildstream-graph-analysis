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

# `UX-338` landed and the exemption that stood here is gone. What it
# said, kept because the *reason* it was needed outlives it: `UX-329`
# made `bga analyze` attach the sibling `plane2.json`, which put
# `element_join` into this fixture's payload - and the page had drawn it
# as a second whole-population table since `UX-215`. That was never new;
# `bga view` has attached the sibling since `UX-203`, so every real
# viewer of a two-plane snapshot saw both tables. This guard could not
# see it because its fixture used to reach the page through `analyze`
# *without* Plane 2 - the one configuration a viewer never has.
#
# The fixture now carries the join (measured: `element_join present =
# True | rows = 11`), and the join is a *view* of the one element table
# rather than a table of its own, which is `UX-289`'s rule applied to
# the columns `UX-215` added.
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
                     "structural.sensitivity.top_opportunities (5)"]

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
                    ]
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


_JOIN_HARNESS = r"""
globalThis._makeNode ??= (await import(process.env.BGA_DOM_SHIM)).makeNode;
const mk = (tag) => _makeNode(tag);
globalThis.document = { createElement: mk, createElementNS: (_n, t) => mk(t),
                        getElementById: () => null, body: mk("body") };
globalThis.window = { location: { hash: "", search: "" }, addEventListener() {},
                      matchMedia: () => ({ matches: false, addEventListener() {} }) };
const app = await import("%s");

// Two elements, one Plane 1 signal each, and a join that carries a
// field of its own *and* one Plane 1 already owns.
// Enough Plane 1 signal for two views to survive without any Plane 2,
// so "the sandbox view is gone" is measured against a control that is
// still offering something rather than against a control that vanished.
const signals = {
  element_durations: { "a.bst": 10, "b.bst": 20 },
  slack: { "a.bst": 0, "b.bst": 5 },
  blast_radius: {
    "a.bst": { downstream_count: 1, is_leaf: false, risk_score: 2 },
    "b.bst": { downstream_count: 0, is_leaf: true, risk_score: 0 },
  },
  criticality_probability: {
    "a.bst": { observed_critical: true, probability: 0.9 },
    "b.bst": { observed_critical: false, probability: 0.1 },
  },
};
// All three columns `Plane 2 (sandbox)` requires, so the view is
// offered - plus one Plane 1 already owns, which it must not take.
const join = [
  { element: "a.bst", cores_busy: 0.5, requested_jobs: 2, peak_rss_kb: 100,
    downstream_count: 999 },   // `downstream_count` is Plane 1's
  { element: "b.bst", cores_busy: 0.8, requested_jobs: 4, peak_rss_kb: 200 },
  // An element Plane 1 never scheduled: the join "never introduces an
  // element", so this row has nowhere to land.
  { element: "ghost.bst", cores_busy: 0.9, requested_jobs: 1,
    peak_rss_kb: 50 },
];
const out = app.elementSignalTable(signals, undefined, join);

// And the same table built with **no** join at all, offered the same
// presets: `Plane 2 (sandbox)` must not be among them.
const presets = %s;
// `presetTable` hands back its own `select`, so the offered views are
// read from the control rather than hunted for in the tree.
const named = (built) => built
  ? (built.select.children ?? []).map((o) => (o.attrs ?? {}).value)
  : [];
const withJoin = app.presetTable("elements", out.rows, presets, out.hint,
                                 undefined, {});
const withoutJoin = app.presetTable(
  "elements", app.elementSignalTable(signals, undefined, null).rows,
  presets, out.hint, undefined, {});

console.log(JSON.stringify({
  elements: out.rows.map((r) => r.element).sort(),
  a: out.rows.find((r) => r.element === "a.bst"),
  joined: out.joined,
  offeredWithJoin: named(withJoin),
  offeredWithoutJoin: named(withoutJoin),
}));
"""


class TestTheJoinMergesWithoutOverwriting:
    """`UX-338`'s two boundary rules, driven directly.

    Neither is reachable on the committed fixture - its join carries no
    field Plane 1 also owns, and no element Plane 1 did not schedule -
    so a mutation to either left every clause in this file green.
    Found by mutation, held here on a payload built to reach them.
    """

    @staticmethod
    def _merge():
        script = _JOIN_HARNESS % ((REPO / "bga/viewer/app.js").as_uri(),
                                  json.dumps(_presets()))
        done = subprocess.run([node, "--input-type=module", "-e", script],
                              capture_output=True, text=True, cwd=REPO,
                              timeout=120,
                              env={**os.environ, "BGA_DOM_SHIM":
                                   (REPO / "tests/dom_shim.mjs").as_uri()})
        assert done.returncode == 0, done.stderr[-3000:]
        return json.loads(done.stdout)

    @needs_node
    def test_plane_one_wins_a_name_collision(self):
        """A join field shadowing an existing column would change what
        that column means without changing its heading - the reader sees
        `Rebuilds: 999` and has no way to know which plane said so."""
        assert self._merge()["a"]["downstream_count"] == 1, (
            "the join overwrote a Plane 1 column")

    @needs_node
    def test_the_join_introduces_no_element(self):
        """`views.js` states it as what the join *is*: the Plane 2 half
        of elements Plane 1 already put in play. A row for an element
        the schedule does not carry would make this table a population
        it does not claim to be."""
        assert self._merge()["elements"] == ["a.bst", "b.bst"], (
            "an element with no Plane 1 row joined the element table")

    @needs_node
    def test_the_plane_two_view_is_not_offered_without_plane_two(self):
        """`UX-194`'s dead-control rule, at the level of a view.

        Found while checking the work rather than by a clause: served
        without its `plane2.json`, the fixture offered `Plane 2
        (sandbox)` and drew two columns under a heading promising five.
        The preset declares its subject (`requires`) so the page can
        tell "this run has no Plane 2" from "this view is empty", and
        this is what holds the declaration - a mutation removing it
        left every other clause here green, because the committed
        fixture *has* Plane 2.
        """
        merged = self._merge()
        assert "Plane 2 (sandbox)" in merged["offeredWithJoin"], (
            "the view is not offered even where it can answer",
            merged["offeredWithJoin"])
        assert "Plane 2 (sandbox)" not in merged["offeredWithoutJoin"], (
            "a run with no Plane 2 is still offered the sandbox view",
            merged["offeredWithoutJoin"])
        assert merged["offeredWithoutJoin"], (
            "no view at all survived, so the assertion above passes for "
            "the wrong reason")

    @needs_node
    def test_the_columns_it_did_add_are_reported(self):
        """The merge says what it merged, so the section's own sentence
        counts signals rather than guessing."""
        assert self._merge()["joined"] == ["cores_busy", "requested_jobs",
                                           "peak_rss_kb"], self._merge()


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
