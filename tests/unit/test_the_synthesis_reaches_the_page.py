"""UX-407: the finding that *is* the answer stayed at the terminal.

Round 64 walked example 06 against its `optimized/` answer key. The one
output that names the entire key in a paragraph is correlate's
restructuring synthesis:

```text
Restructuring opportunity: 18 declared build edge(s) among 8
element(s) were measured never-read, and they chain those elements
along the critical path: ...
    Replaying this run with those edges removed - same durations,
    same capacity - finishes in 19.1s against 43.2s: 24.1s
```

A grep of the round's export found zero hits for "Replaying this run".
The page carried the per-element crumbs (`unused_dependencies`, "opened
no file staged by 3 declared build dependencies"), so a reader had to
open seven element folds and re-do the aggregation the tool had already
done, projection and all.

**The filing's first Required Fix bullet was already satisfied.**
"Publish the restructuring synthesis as a keyed finding in the correlate
contract" describes what `correlate/v2` has published since `UX-82`:

```console
$ bga correlate tests/fixtures/macro_micro/run --format json | \
    python3 -c 'import json,sys; print(list(json.load(sys.stdin)["restructuring"][0]))'
['id', 'severity', 'elements', 'edges', 'projection']
```

The gap is one door further along: `bga view` renders `analyze/v4` and
embeds no correlate document, so the key existed on a surface the page
never reads. What this item adds is the same finding in the analyze
document - from the join that already runs there, in the same shape,
under one declaration - and the section that draws it.

Two renderings had to be fixed for the page to say what the terminal
says, and both are in `TestTheUnitsSurviveTheCell`.
"""
import json
import os
import pathlib
import re
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga import schemas                                       # noqa: E402
from tests import pages                                       # noqa: E402
from tests.browser import NO_BROWSER, Browser, find_chrome     # noqa: E402

FIXTURE = REPO / "tests/fixtures/macro_micro/run"
node = __import__("shutil").which("node")


def _cli(*args):
    done = subprocess.run(
        [sys.executable, "-m", "bga.cli", *args],
        capture_output=True, text=True, cwd=REPO, timeout=180,
        env=dict(os.environ, PYTHONPATH=str(REPO)))
    assert done.returncode == 0, done.stderr[-3000:]
    return done.stdout


@pytest.fixture(scope="module")
def analyzed():
    return json.loads(_cli("analyze", str(FIXTURE), "--format", "json"))


@pytest.fixture(scope="module")
def spoken():
    """What `bga correlate` prints. The surface that already had it."""
    return _cli("correlate", str(FIXTURE))


class TestTheContractCarriesItOnBothSurfaces:
    def test_analyze_declares_it(self):
        node = schemas.schema(schemas.ANALYZE)["properties"].get("restructuring")
        assert node, (
            "`analyze/v4` does not declare the synthesis, so `bga view` - "
            "which renders that document and embeds no other - has nothing "
            "to draw")
        assert node[schemas.RAIL] == "act"

    def test_one_declaration_serves_both_contracts(self):
        """Not two that agree today.

        `UX-408`, one item earlier in this round, is what a second copy
        costs: a caption and a description that described each other's
        opposite for as long as both existed.
        """
        analyze = schemas.schema(schemas.ANALYZE)["properties"]["restructuring"]
        correlate = schemas.schema(
            schemas.CORRELATE)["properties"]["restructuring"]
        assert analyze == correlate
        source = (REPO / "bga/schemas.py").read_text(encoding="utf-8")
        assert source.count("_RESTRUCTURING_HINT = {") == 1
        assert source.count('"restructuring": _RESTRUCTURING_HINT') == 2

    def test_the_edges_are_declared_as_a_table(self):
        """`UX-290`'s tuple rule needs the columns, or it draws `#1`/`#2`.

        An edge is `["core.bst", "app.bst"]` - a positional pair the
        page cannot name without being told, and `Staged by` /
        `Never read by` is the whole content of the row.
        """
        node = schemas.schema(schemas.ANALYZE)["properties"]["restructuring"]
        columns = node["items"]["properties"]["edges"][schemas.COLUMNS]
        assert [spec["key"] for spec in columns] == ["from", "to"]
        assert all(spec.get("role") == "element" for spec in columns), (
            "without `role: element` the two ends of an edge are strings "
            "rather than elements a reader can open (`UX-208`)")


class TestTheDocumentTheViewerReads:
    def test_analyze_carries_the_synthesis(self, analyzed):
        assert analyzed.get("restructuring"), (
            "the analyze document has no restructuring key, so the page "
            "renders the crumbs and not the conclusion")

    def test_it_carries_the_replay_rather_than_a_null(self, analyzed):
        """The join needs the tasks and the run context to replay.

        Called without them - which is how `bga/report/json.py` called
        it - the finding still arrives, with `projection: null`. The
        prize is the whole reason the synthesis outranks the five rows
        it is drawn from, so a null projection is the defect wearing
        the fix's clothes.
        """
        projection = analyzed["restructuring"][0]["projection"]
        assert projection, "the finding reached the document unprojected"
        assert projection["saving_us"] > 0
        assert (projection["replayed_baseline_us"]
                - projection["projected_us"] == projection["saving_us"])

    def test_the_two_documents_publish_one_finding(self, analyzed):
        correlated = json.loads(
            _cli("correlate", str(FIXTURE), "--format", "json"))
        assert analyzed["restructuring"] == correlated["restructuring"], (
            "two documents disagreeing about one finding is worse than "
            "one document not having it")


@pytest.fixture(scope="module")
def seen(tmp_path_factory):
    if find_chrome() is None:
        pytest.skip(NO_BROWSER)
    look = """(() => {
          const s = document.querySelector(
            'section[data-section="restructuring"]');
          if (!s) return { found: false };
          // By its own state key, not by walking the section's tables:
          // the edge table is *inside* a cell of the section's table,
          // so `querySelectorAll("table")` finds the outer one first
          // and its header row carries the nested headings too.
          const edges = s.querySelector(
            'table[data-table="restructuring.0.edges"]');
          return {
            found: true,
            rail: s.getAttribute("data-rail"),
            // The cells of one column, not `tbody tr`: the table
            // machinery keeps an empty-state row for the filter.
            edgeRows: edges
              ? edges.querySelectorAll('tbody td[data-column="from"]').length
              : 0,
            headers: edges
              ? [...edges.querySelectorAll("th")].map(
                  (h) => (h.textContent || "").trim())
              : [],
            text: (s.textContent || "").replace(/\\s+/g, " "),
            // The strip is drawn by `interrogable`, around the table
            // rather than inside `renderStructured`, so only a real
            // page can be asked whether it is there.
            projectionDensity: [...document.querySelectorAll(
              '[data-fold-path="restructuring.0.projection"] .density')]
              .map((d) => (d.textContent || "").replace(/\\s+/g, " ")),
            foldPaths: [...s.querySelectorAll("details[data-fold-path]")]
              .map((d) => d.getAttribute("data-fold-path")),
          };
        })()"""
    into = tmp_path_factory.mktemp("synthesis")
    uri = pages.export_uri(pages.FIXTURES["macro_micro"], into)
    with Browser(find_chrome()) as browser:
        return browser.measure(uri, look, 1440, 900)


@pytest.mark.skipif(find_chrome() is None, reason=NO_BROWSER)
class TestOnThePage:
    """The acceptance test, on the committed fixture that has a chain."""

    def test_the_section_is_on_the_page(self, seen):
        assert seen["found"], (
            "the export has no restructuring section - the state this "
            "item was filed in, where a grep of the round's page found "
            "zero hits for the synthesis")
        assert seen["rail"] == "act"

    def test_the_edges_render_as_a_named_table(self, seen):
        assert seen["edgeRows"] == 18, seen["edgeRows"]
        assert "Staged by" in seen["headers"] and "Never read by" in seen[
            "headers"], seen["headers"]

    def test_the_page_prints_the_terminal_s_triple(self, seen, spoken):
        """The acceptance test's own clause.

        Not "the page has three numbers" - the *same* three, rendered
        the same way, read out of the paragraph the terminal prints so
        that a change to either surface has to move both.
        """
        line = next(row for row in spoken.splitlines()
                    if "Replaying this run" in row)
        triple = re.findall(r"(\d+\.\d+)s", line)
        assert len(triple) == 3, line
        projected, baseline, saving = triple
        for number in (baseline, projected, saving):
            assert f"{number} s" in seen["text"], (
                f"the page does not print {number} s; the terminal's line "
                f"is {line.strip()!r}")

    def test_the_projection_draws_no_distribution(self, seen):
        """`mapTable` invented `count` for every map without one.

        Right for `{element: duration_us}`, where one quantity does
        describe the column; on a record it drew a density strip
        reading `19050000 -> 43200000 across 3 rows` - three numbers
        that are neither one measure nor a distribution, in the unit no
        schema declared.
        """
        assert seen["projectionDensity"] == [], seen["projectionDensity"]

    def test_its_three_folds_are_three_state_keys(self, seen):
        """`UX-292`, from the other side.

        One row here holds three structural cells - the elements, the
        edges and the projection - and they opened and filtered as one
        key until this item, because the path was the row's.
        """
        assert len(seen["foldPaths"]) == len(set(seen["foldPaths"])), (
            seen["foldPaths"])


_RECORD = """
globalThis._makeNode ??= (await import(process.env.BGA_DOM_SHIM)).makeNode;
globalThis.document = { createElement: _makeNode,
                        createElementNS: (_n, t) => _makeNode(t),
                        getElementById: () => null };
const viewer = await import("./tests/viewer.mjs");

// A **record**: a node whose members are named in `properties`, each
// with its own unit. `projection` is one; a map keyed by element uid
// is not, and the two must not render the same way.
//
// Four members, one of them structural - which is `projection`'s own
// shape and is load-bearing here. The first draft had three scalars,
// so `classify` returned `definition list` and the probe exercised
// `inlineObject` instead of the table this item changed: both of its
// clauses stayed green under the mutations that reintroduce the
// defect. Found by running them.
const RECORD = { type: "object", properties: {
  replayed_baseline_us: { "bga:quantity": "duration_us" },
  projected_us: { "bga:quantity": "duration_us" },
  peak_rss_bytes: { "bga:quantity": "bytes" },
  capacities: { additionalProperties: { "bga:quantity": "count" } },
} };
const MAP = { type: "object",
              additionalProperties: { "bga:quantity": "duration_us" } };

const text = (n) => !n ? "" : ((n.children ?? []).length
  ? (n._text ?? "") + n.children.map(text).join("") : (n._text ?? ""));
const find = (n, pred) => {
  if (!n) return null;
  if (pred(n)) return n;
  for (const c of n.children ?? []) { const hit = find(c, pred); if (hit) return hit; }
  return null;
};
console.log = (...a) => process.stdout.write(a.join(" ") + "\\n");
console.log(JSON.stringify({
  record: text(viewer.renderStructured("projection", {
    replayed_baseline_us: 43200000, projected_us: 19050000,
    peak_rss_bytes: 2097152, capacities: { PROCESS: 4 },
  }, {}, RECORD, 1, "p")),
  map: text(viewer.renderStructured("wall_clock_share_us", {
    "a.bst": 2300000, "b.bst": 4600000, "c.bst": 900000,
  }, {}, MAP, 1, "m")),
}));
"""


@pytest.fixture(scope="module")
def drawn():
    if node is None:
        pytest.skip("node is not installed")
    done = subprocess.run(
        [node, "--input-type=module", "-e", _RECORD],
        capture_output=True, text=True, cwd=REPO, timeout=60,
        env=dict(os.environ,
                 BGA_DOM_SHIM=str(REPO / "tests" / "dom_shim.mjs")))
    assert done.returncode == 0, done.stderr[-3000:]
    return json.loads(done.stdout)


@pytest.mark.skipif(node is None, reason="node is not installed")
class TestTheUnitsSurviveTheCell:
    """The two renderings that had to change, driven rather than read.

    Both are older than this item and neither had a value that showed
    them until `projection` arrived: a **record** - a schema node whose
    members are named in `properties`, each with its own unit - nested
    in a table cell.
    """

    def test_each_member_renders_in_its_own_unit(self, drawn):
        """`UX-290` resolved the schema node here and left the unit.

        The lookup moved to the row's key; the rendering kept reading
        `spec.quantity`, which is the *column's* - and a map table's
        column is called `value`. So `43200000` printed beside a
        terminal saying `43.2s`.
        """
        assert "43.2 s" in drawn["record"], drawn["record"]
        assert "19.1 s" in drawn["record"], drawn["record"]
        assert "2.0 MiB" in drawn["record"], (
            "a record's members do not share one unit, and the bytes "
            "field is what a single column quantity would have flattened")
        assert "43200000" not in drawn["record"]

    def test_a_real_map_is_untouched(self, drawn):
        """The other half of the branch, so the fix is not a blanket.

        A map keyed by data has one quantity for its whole value
        column, `UX-262` needs it declared for the `Top N` bound, and
        that path is unchanged.
        """
        assert "2.3 s" in drawn["map"] and "4.6 s" in drawn["map"], drawn["map"]
