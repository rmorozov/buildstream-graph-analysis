"""UX-641: `parallelism.levels` published the row number.

Measured on round 87's three-plane run, before this item:

```text
levels          [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
width_at_level  [1, 2, 1, 1, 1, 1, 1, 1, 1, 1]
levels == list(range(len(width_at_level)))   True
```

One row per level now, each naming its width and its members - the set
`_compute_level_decomposition` already returned and `compute_parallelism_profile`
discarded one line later.

Two traps, one clause each, both measured on the 1,202-element
synthetic run (`bga gen-synthetic --seed 1`):

* the members are the **gating** graph's (`UX-52`), not
  `elements.unweighted_depth`'s. Per-level difference between the two
  at that scale: `[0,-2,0,0,0,0,0,0,+1,0,0,0,+1,0]`.
* one level there holds **102** uids, against 1-2 on both committed
  fixtures, so the cell is bounded head-and-tail by `UX-319`'s two
  numbers.
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

from bga import schemas    # noqa: E402
from bga.schemas import COLUMNS    # noqa: E402

FIXTURES = {
    "golden": REPO / "tests/fixtures/golden/mixed_task_kinds",
    "macro_micro": REPO / "tests/fixtures/macro_micro/run",
}
node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")


def _analyze(run):
    done = subprocess.run(
        [sys.executable, "-m", "bga.cli", "analyze", str(run),
         "--format", "json"],
        capture_output=True, text=True, cwd=str(REPO), timeout=300,
        env={**os.environ, "PYTHONPATH": str(REPO)})
    assert done.returncode == 0, done.stderr[-2000:]
    return json.loads(done.stdout)


@pytest.fixture(scope="module")
def documents():
    return {label: _analyze(run) for label, run in FIXTURES.items()}


@pytest.mark.parametrize("label", sorted(FIXTURES))
class TestTheKeyIsNotTheRowNumber:
    def test_it_is_not_the_identity_function(self, documents, label):
        """The defect itself: a key whose every value is its own index
        carries one fact, and the sentence beside the sparkline already
        prints it."""
        levels = documents[label]["parallelism"]["levels"]
        assert levels, f"{label}: no levels at all"
        assert levels != list(range(len(levels))), (
            f"{label}: `parallelism.levels` is `list(range({len(levels)}))` "
            f"again - the row number, published")

    def test_every_level_names_its_members(self, documents, label):
        """Not just a width: *which* elements. The width is redundant
        with `len(elements)` on purpose - it is the column a reader
        sorts and filters the table by."""
        levels = documents[label]["parallelism"]["levels"]
        for row in levels:
            assert set(row) >= {"level", "width", "elements"}, row
            assert isinstance(row["elements"], list) and row["elements"], row
            assert row["width"] == len(row["elements"]), row
            assert row["elements"] == sorted(row["elements"]), (
                f"{label}: level {row['level']} is not sorted, so the "
                f"document is not byte-stable across processes")

    def test_the_levels_are_the_depths_in_order(self, documents, label):
        levels = documents[label]["parallelism"]["levels"]
        assert [row["level"] for row in levels] == sorted(
            row["level"] for row in levels)
        assert levels[0]["level"] == 0

    def test_the_widths_agree_with_the_series_beside_them(self, documents,
                                                          label):
        """`width_at_level` is the sparkline's series and stays. Two
        spellings of one number are allowed to coexist only while they
        agree - `UX-535`'s rule is that they must not diverge."""
        block = documents[label]["parallelism"]
        assert [row["width"] for row in block["levels"]] \
            == block["width_at_level"]

    def test_the_members_are_every_element_once(self, documents, label):
        """A decomposition partitions. A uid in two levels, or missing
        from all of them, is a decomposition that is not one."""
        levels = documents[label]["parallelism"]["levels"]
        members = [uid for row in levels for uid in row["elements"]]
        assert len(members) == len(set(members)), f"{label}: a uid twice"
        population = set(documents[label]["elements"]["unweighted_depth"])
        assert set(members) == population, (
            f"{label}: {sorted(set(members) ^ population)[:6]} is in one "
            f"population and not the other")


class TestTheMembersComeFromTheGatingGraph:
    """Trap one. `elements.unweighted_depth` is the **full** graph -
    `compute_unweighted_depth` calls `build_element_graph` with no
    exclusion - while `parallelism` runs on the gating graph, `runtime`
    edges removed (`UX-52`). Sourcing the members from the published
    depth map would be one line of code and wrong on every project with
    a runtime edge.

    The topology below is `test_runtime_edge_gating.py`'s `MIXED` with
    a second build edge, so the two graphs put `d.bst` on different
    levels: full graph level 3 (behind the runtime edge from `c.bst`),
    gating graph level 1 (behind `a.bst` only).
    """

    @staticmethod
    @pytest.fixture(scope="class")
    def document(tmp_path_factory):
        from bga import BuildEfficiencyAnalyzer
        from bga.report.json import format_json
        from fixtures.topologies import _build, _dependency, _element, _span
        from fixtures.topologies import write_run_dir

        uids = ["a.bst", "b.bst", "c.bst", "d.bst"]
        topology = _build(
            elements=[_element(u, requested_target=(u == "c.bst"))
                      for u in uids],
            dependencies=[
                _dependency("a.bst", "b.bst"),
                _dependency("b.bst", "c.bst"),
                _dependency("a.bst", "d.bst"),
                # The one edge the two graphs disagree about.
                _dependency("c.bst", "d.bst", dependency_type="runtime"),
            ],
            spans=[_span(u, at * 10_000, 10_000)
                   for at, u in enumerate(uids)],
            wall_end_us=40_000)
        run = write_run_dir(tmp_path_factory.mktemp("gating"), topology)
        analyzer = BuildEfficiencyAnalyzer(run)
        return json.loads(format_json(analyzer.analyze(run))), run

    def test_the_two_graphs_really_disagree_here(self, document):
        """The clause that makes the two below discriminate, and it
        reads the *fixture* rather than the published document - a
        wrong implementation must not be able to satisfy it.

        `d.bst` is level 1 on the gating graph and level 3 on the full
        one, and a guard built on a topology where they agree would
        pass whatever the analyzer sourced its members from.
        """
        import networkx as nx
        from bga.ingest.loader import load_all
        from bga.structural.analyzer import build_edg

        _document, run = document
        _context, graph, _trace = load_all(pathlib.Path(run))
        edg = build_edg(graph)

        def depths(G):
            found = {}
            for node in nx.topological_sort(G):
                found[node] = max(
                    (found[p] for p in G.predecessors(node)), default=-1) + 1
            return found

        assert depths(edg.G)["d.bst"] == 1, depths(edg.G)
        assert depths(edg.G_full)["d.bst"] == 3, depths(edg.G_full)

    def test_the_members_are_the_gating_graphs(self, document):
        from bga.structural.analyzer import build_edg
        from bga.ingest.loader import load_all
        from bga.structural.analyzer import StructuralAnalyzer

        document, run = document
        _context, graph, _trace = load_all(pathlib.Path(run))
        analyzer = StructuralAnalyzer(build_edg(graph), {})
        want = {level: sorted(uids) for level, uids
                in analyzer._compute_level_decomposition().items()}
        got = {row["level"]: row["elements"]
               for row in document["parallelism"]["levels"]}
        assert got == want, (
            "the published membership is not `_compute_level_decomposition`'s")

    def test_the_members_are_not_the_unweighted_depth_map(self, document):
        """The mutation this clause exists for: sourcing from
        `elements.unweighted_depth`, which is the full graph."""
        import collections

        document, _run = document
        by_depth = collections.defaultdict(list)
        for uid, depth in document["elements"]["unweighted_depth"].items():
            by_depth[depth].append(uid)
        wrong = {level: sorted(uids) for level, uids in by_depth.items()}
        got = {row["level"]: row["elements"]
               for row in document["parallelism"]["levels"]}
        assert got != wrong, (
            "the members are `elements.unweighted_depth` grouped by depth - "
            "the full graph, runtime edges and all")


class TestTheSchemaSaysWhatTheKeyHolds:
    def test_it_no_longer_carries_the_width_series_description(self):
        """`schemas.py:2006` gave `levels` the sentence belonging to
        `width_at_level` - "How many elements sit at this level of the
        graph" - which is not what the key held even before this item."""
        block = schemas.schema(schemas.ANALYZE)["properties"]["parallelism"]
        levels = block["properties"]["levels"]
        width = block["properties"]["width_at_level"]
        assert "How many elements" not in levels["description"], levels
        # The sentence belongs to a count, and there is exactly one
        # count under `levels`: the `width` column.
        carriers = [spec["key"] for spec in levels[COLUMNS]
                    if "How many elements sit at this level"
                    in spec.get("description", "")]
        assert carriers == ["width"], carriers
        assert "How many elements sit at each" in width["description"]

    def test_it_declares_the_three_columns(self):
        block = schemas.schema(schemas.ANALYZE)["properties"]["parallelism"]
        columns = block["properties"]["levels"][COLUMNS]
        assert [spec["key"] for spec in columns] \
            == ["level", "width", "elements"], columns
        for spec in columns:
            assert spec.get("description"), spec

    def test_the_shape_change_bumped_the_document(self):
        """A published key changing shape is a break (§3.7). The old id
        has to be *readable*, which is what `SUPERSEDED` says."""
        assert "analyze/v5" in schemas.SUPERSEDED
        assert schemas.ANALYZE not in schemas.SUPERSEDED
        for label, run in FIXTURES.items():
            assert _analyze(run)["schema"] == schemas.ANALYZE, label


_CELL_PROBE = r"""
globalThis._installDocument ??= (await import(process.env.BGA_DOM_SHIM)).installDocument;
_installDocument();
const app = await import("./tests/viewer.mjs");
const rows = %s;
const built = app.buildTable("levels", rows, %s, undefined);
const find = (n, p, out = []) => {
  if (!n) return out;
  if (p(n)) out.push(n);
  (n.children ?? []).forEach((c) => find(c, p, out));
  return out;
};
const text = (n) => !n ? "" : ((n.children ?? []).length
  ? n.children.map(text).join("") : (n.textContent ?? ""));
const cells = find(built.table,
  (n) => n.tagName === "td" && (n.attrs ?? {})["data-column"] === "elements");
const uids = (s) => s.split(",").map((x) => x.trim()).filter(Boolean);
console.log(JSON.stringify(cells.map((cell) => {
  const box = find(cell, (n) => (n.attrs ?? {})["data-bounded"] === "list")[0];
  const table = find(cell, (n) => n.tagName === "table")[0];
  const control = find(cell, (n) => n.tagName === "button"
    && String(n.className || "").includes("fold-more"))[0];
  const rows = table
    ? find(table, (n) => n.tagName === "tr" && n._parent?.tagName === "tbody")
    : [];
  return {
    published: box ? Number(box.attrs["data-items"]) : null,
    shown: box
      ? uids(text(find(box, (n) => String(n.className || "") === "list-head")[0])
             + text(find(box, (n) => String(n.className || "") === "list-tail")[0])).length
      : (table ? rows.length : null),
    tables: table ? 1 : 0,
    filters: find(cell, (n) => String(n.className || "").includes("table-filter")).length,
    nodes: find(cell, () => true).length,
    control: control ? text(control).trim() : null,
    inline: (box || table) ? null : text(cell).trim(),
  };
})));
"""


def _cells(rows, hint=None):
    script = _CELL_PROBE % (json.dumps(rows), json.dumps(hint or {}))
    done = subprocess.run([node, "--input-type=module", "-e", script],
                          capture_output=True, text=True, cwd=str(REPO),
                          timeout=120,
                          env={**os.environ, "BGA_DOM_SHIM":
                               (REPO / "tests/dom_shim.mjs").as_uri()})
    assert done.returncode == 0, done.stderr[-2000:]
    return json.loads(done.stdout)


@needs_node
class TestTheCellIsBounded:
    """Trap two. Both committed fixtures put 1-2 uids on a level and
    say nothing about this; the 1,202-element run puts 102 on one.

    The bound this guard defends, written here rather than read from
    the module - a guard that reads the constant it checks moves with
    it and checks nothing (`test_a_table_cell_obeys_the_value_rule.py`'s
    own note).
    """

    HEAD, TAIL = 6, 3

    def _members(self, n, at=1):
        return [{"level": at, "width": n,
                 "elements": [f"layer{at:02d}/mod{i:03d}.bst"
                              for i in range(n)]}]

    def test_a_hundred_and_two_members_show_head_and_tail(self):
        [cell] = _cells(self._members(102))
        assert cell["published"] == 102
        assert cell["shown"] == self.HEAD + self.TAIL, (
            f"the cell holds {cell['shown']} of 102 uids, against a bound "
            f"of {self.HEAD} + {self.TAIL}")

    def test_the_cell_does_not_build_a_table_for_them(self):
        """The DOM cost is what made this a defect rather than a taste:
        a 102-row interrogable table inside a `<td>`, twelve times over,
        took the 1,202-element page to 11,068 elements against a budget
        of 5,500 - and gave a 14-row table a filter input by being
        nested inside it."""
        [cell] = _cells(self._members(102))
        assert cell["tables"] == 0, cell
        assert cell["filters"] == 0, cell
        assert cell["nodes"] < 40, cell["nodes"]

    def test_the_control_says_how_many_are_behind_it(self):
        """§3a.1: the count is visible before the click, and it names
        what is behind it."""
        [cell] = _cells(self._members(102))
        assert cell["control"] == "+93 more elements (102 in all)", cell

    def test_a_level_the_fixtures_size_is_not_folded_at_all(self):
        """1-2 uids inline, no fold, no nested table - the shape both
        committed fixtures actually publish."""
        for n in (1, 2):
            [cell] = _cells(self._members(n))
            assert cell["tables"] == 0 and cell["control"] is None, cell
            assert cell["inline"], cell

    def test_the_bound_does_not_move_with_the_population(self):
        """A bound that grew with `n` would be no bound. Three
        magnitudes, one answer."""
        shown = [_cells(self._members(n))[0]["shown"] for n in (41, 102, 400)]
        assert shown == [self.HEAD + self.TAIL] * 3, shown

    def test_a_cell_the_row_bound_already_reached_is_left_alone(self):
        """The threshold is `TABLE_OPENS_BOUNDED_ABOVE`'s, so this
        *replaces* the row bound where it applied rather than adding a
        second one. At 40 and below the cell shows every member, which
        is what `producer.contracts` (25 ids) and
        `optimization_horizon[].entering` (12) do today and keep doing.
        """
        [cell] = _cells(self._members(40))
        assert cell["published"] is None and cell["control"] is None, cell
        assert cell["tables"] == 1 and cell["shown"] == 40, cell
