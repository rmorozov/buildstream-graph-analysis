"""UX-302: raw JSON on the page is a defect unless it is deliberate.

The rule is the user's, and round 41's style guide
(`docs/design/styleguide.md` §1) turned it into a dispatch table:
published shape (+ hint) on the left, the one control that may render
it on the right. `UX-267` and `UX-277` had already emptied the page of
the wall of `<pre>`; what was missing was the law - the mapping in one
function every render path asks, the deliberate escapes *named*, and a
guard that reads the booted page rather than the source.

**What the booted pages measure**, walking every element's own text for
JSON-shaped content (`{` then a quote, or `[` then a brace):

```text
                    nodes  with text  sections  toggles  raw-JSON text
golden               2082        1174        28       15              0
macro_micro          3497        1972        37       17              0
```

and, with `renderStructured`'s object-map branch mutated to return
`<pre>{JSON.stringify(value)}</pre>` - the acceptance test's mutation:

```text
golden                  1310         832                   12
macro_micro             1933        1261                   17
```

So the walk discriminates: it is not reporting zero because it looks at
nothing. That mattered - the first draft of it *did* look at nothing.
It walked `body`, and the report root is `getElementById("report")`,
which the probe's `document` hands back **detached** from `body`; the
mutation left it at zero and the instrument would have been declared a
pass. What fixed it is the same discipline `UX-235` wrote down: the
guard reads the document the page actually assembles.

**The two deliberate sites**, and nothing else:

- `UX-277`'s labeled fold - `<p class="full-text">` inside
  `<details class="map">`, reached past the nesting cap or (new here)
  by a shape §1 does not cover. Worth recording that neither committed
  fixture reaches it: the fold's raw JSON is unexercised by the golden
  and `macro_micro` pages, so the walk's "0 inside" is an absence of
  deep nesting, not evidence the allowlist works. The allowlist is
  exercised by the probe payload in `TestAShapeTheGuideDoesNotCover`.
- `UX-302`'s "view as JSON" toggle, under `data-raw-json`. 15 of
  golden's 28 sections get one and 17 of `macro_micro`'s 37; the other
  13 and 20 are the ones the page *composes* - `decision`, `overview`,
  `evidence`, `horizon`, `whatif`, the drawn critical path, and one
  per element - which have no single payload slice to show, and get no
  control rather than a control showing the wrong thing.
"""
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")
REPO = Path(__file__).resolve().parents[2]
GOLDEN = REPO / "tests" / "fixtures" / "golden" / "mixed_task_kinds"
MACRO = REPO / "tests" / "fixtures" / "macro_micro" / "run"
VIEWER = REPO / "bga" / "viewer"


def _probe_source():
    """The export probe, reused rather than re-implemented (`UX-264`)."""
    source = (REPO / "tests/unit/test_a_report_you_can_navigate.py").read_text()
    return source.split('_PROBE = r"""', 1)[1].rsplit('"""', 1)[0]


# Everything after this line in the probe builds *its* answer; the tail
# below builds ours, over the same booted document.
_TAIL = r"""
const root = named["report"] ?? body;

// A section, serialised - deep enough that a stray empty wrapper shows.
// `textContent` alone would not: an empty `<div>` contributes nothing
// to it, and an empty wrapper left behind by a toggle is exactly the
// residue this has to catch.
function dump(n) {
  if (!n || n.nodeType === 3) return String(n?.textContent ?? "");
  const attrs = Object.entries(n.attrs ?? {}).sort()
    .map(([k, v]) => `${k}=${v}`).join(" ");
  return `<${n.tagName} ${attrs}>${n._text ?? ""}`
    + (n.children ?? []).map(dump).join("") + `</${n.tagName}>`;
}

// Every element's *own* text, with the chain that holds it - so the
// allowlist is a question about ancestors rather than about the text.
// Compact *and* pretty-printed: the fold stringifies without
// indent and the toggle with, and both are raw JSON on the page.
const RAW_JSON = /\{\s*"|\[\s*\{/;
function allowed(chain) {
  return chain.some((n) => n.attrs?.["data-raw-json"] !== undefined
                        || (n.attrs?.class || "").includes("full-text"));
}
function sweep() {
  const leaks = [];
  let nodes = 0, texted = 0;
  (function walk(n, chain) {
    nodes += 1;
    const here = [...chain, n];
    if (n._text) {
      texted += 1;
      if (RAW_JSON.test(n._text)) {
        leaks.push({ tag: n.tagName, allowed: allowed(here),
                     text: String(n._text).slice(0, 200) });
      }
    }
    for (const c of n.children ?? []) walk(c, here);
  })(root, []);
  return { leaks, nodes, texted };
}

// Closed: what the reader first sees.
const { leaks, nodes, texted } = sweep();

const toggles = [];
(function find(n) {
  for (const c of n.children ?? []) {
    if (c.attrs?.["data-json-toggle"]) toggles.push(c);
    find(c);
  }
})(root);

// And open: every "view as JSON" showing. This is the sweep that
// exercises the *allowlist* rather than an empty page - with all of
// them open the document is full of raw JSON, and every byte of it has
// to be under `data-raw-json` or the walk is reporting zero because
// there was nothing to find.
for (const button of toggles) button.click();
const opened = sweep();
for (const button of toggles) button.click();
const closedAgain = sweep();

// The round trip: shown, hidden, and the section byte-identical to how
// it started.
let trip = null;
if (toggles.length) {
  const button = toggles[0];
  const section = (function up(n) {
    return !n ? null : n.tagName === "section" ? n : up(n._parent);
  })(button);
  const before = dump(section);
  button.click();
  const opened = dump(section);
  button.click();
  const after = dump(section);
  const box = (function findBox(n) {
    for (const c of n.children ?? []) {
      if (c.attrs?.["data-raw-json"]) return c;
      const hit = findBox(c);
      if (hit) return hit;
    }
    return null;
  })(section);
  trip = { key: button.attrs["data-json-toggle"],
           restored: before === after,
           grew: opened.length > before.length,
           parses: (() => {
             button.click();
             const shown = (function findPre(n) {
               for (const c of n.children ?? []) {
                 if (c.attrs?.["data-raw-json"]) return c.textContent;
                 const hit = findPre(c);
                 if (hit) return hit;
               }
               return null;
             })(section);
             let ok = false;
             try { JSON.parse(shown); ok = true; } catch (e) { ok = false; }
             button.click();
             return ok;
           })(),
           residue: box !== null };
}

const sections = [];
(function count(n) {
  for (const c of n.children ?? []) {
    if (c.attrs?.["data-section"]) sections.push(c.attrs["data-section"]);
    count(c);
  }
})(root);

console.log(JSON.stringify({
  leaks, nodes, texted, sections, opened, closedAgain,
  toggles: toggles.map((b) => b.attrs["data-json-toggle"]), trip,
  error: failure,
}));
"""


def _boot(run_dir, tmp):
    """Export the run, boot the exported page, and report what it holds."""
    run = tmp / "run"
    shutil.copytree(run_dir, run)
    if (run / "expected_output.json").exists():
        os.remove(run / "expected_output.json")

    import tools.bga_view as view

    page = tmp / "report.html"
    view.export(str(run), str(page))
    html = page.read_text(encoding="utf-8")
    module = tmp / "inline.mjs"
    module.write_text(
        re.search(r'<script type="module">(.*?)</script>', html, re.S).group(1),
        encoding="utf-8")
    probe = tmp / "probe.mjs"
    probe.write_text(_probe_source().split("const report =", 1)[0] + _TAIL,
                     encoding="utf-8")
    result = subprocess.run(
        [node, str(probe)], capture_output=True, text=True, cwd=REPO,
        timeout=180,
        # `file:`, because the export is the mode that has no server -
        # the toggle is the issue-pasting affordance and it must work
        # for the person the report was *sent* to.
        env=dict(os.environ, PAGE=str(page), MOD=str(module),
                 PROTOCOL="file:"))
    assert result.returncode == 0, result.stderr[-4000:]
    out = json.loads(result.stdout)
    assert out["error"] is None, out["error"]
    return out


@pytest.fixture(scope="module")
def booted():
    pages = {}
    for name, run in (("golden", GOLDEN), ("macro_micro", MACRO)):
        tmp = Path(tempfile.mkdtemp())
        try:
            pages[name] = _boot(run, tmp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    return pages


@needs_node
@pytest.mark.medium
class TestNoRawJsonOutsideTheTwoControls:
    """The acceptance test's first clause, on both booted pages."""

    @pytest.mark.parametrize("page", ["golden", "macro_micro"])
    def test_no_unlabeled_raw_json_text(self, booted, page):
        leaks = [leak for leak in booted[page]["leaks"] if not leak["allowed"]]
        assert not leaks, (
            f"{page}: {len(leaks)} raw-JSON text nodes outside the labeled "
            f"fold and the JSON toggle: "
            + "; ".join(f"<{leak['tag']}> {leak['text'][:80]!r}"
                        for leak in leaks[:5]))

    @pytest.mark.parametrize("page", ["golden", "macro_micro"])
    def test_with_every_toggle_open_it_is_all_labeled(self, booted, page):
        """The clause that exercises the allowlist.

        Closed, the page holds no raw JSON at all - so the first clause
        would pass even if the allowlist forgave nothing, and it did:
        removing `data-raw-json` from the toggle's box left the whole
        file green. With every toggle open the document is *full* of
        raw JSON, and all of it must be under that attribute.
        """
        opened = booted[page]["opened"]
        assert opened["leaks"], (
            "no raw JSON with every toggle open - the toggles did not "
            "open, and this clause is asserting nothing")
        loose = [leak for leak in opened["leaks"] if not leak["allowed"]]
        assert not loose, (
            f"{page}: {len(loose)} of {len(opened['leaks'])} raw-JSON text "
            f"nodes are outside `data-raw-json`: "
            + "; ".join(f"<{leak['tag']}> {leak['text'][:60]!r}"
                        for leak in loose[:3]))

    @pytest.mark.parametrize("page", ["golden", "macro_micro"])
    def test_closing_them_all_puts_the_page_back(self, booted, page):
        """Round-trip over *every* section, not just the first."""
        again = booted[page]["closedAgain"]
        assert not [leak for leak in again["leaks"] if not leak["allowed"]]
        assert again["nodes"] == booted[page]["nodes"], (
            f"{page}: {again['nodes']} nodes after closing every toggle, "
            f"{booted[page]['nodes']} before")

    @pytest.mark.parametrize("page,least_nodes,least_texted",
                             [("golden", 1500, 800),
                              ("macro_micro", 2500, 1400)])
    def test_the_walk_looked_at_the_document(
            self, booted, page, least_nodes, least_texted):
        """A zero from an instrument that read nothing is not a zero.

        The first draft walked `body` and reached 0 nodes of the report,
        so the mutation that fills the page with `<pre>{…}` left it
        green. These floors are the measured counts less a margin;
        they exist so that a future change which detaches the report
        from the walk fails here rather than passing everywhere.
        """
        out = booted[page]
        assert out["nodes"] >= least_nodes, out["nodes"]
        assert out["texted"] >= least_texted, out["texted"]


@needs_node
@pytest.mark.medium
class TestTheToggleRoundTrips:
    """The second clause: shown, hidden, document unchanged."""

    @pytest.mark.parametrize("page", ["golden", "macro_micro"])
    def test_sections_offer_the_toggle(self, booted, page):
        out = booted[page]
        assert len(out["toggles"]) >= 12, out["toggles"]
        # Every toggle names a section that is really in the document.
        assert set(out["toggles"]) <= set(out["sections"]), (
            set(out["toggles"]) - set(out["sections"]))

    @pytest.mark.parametrize("page", ["golden", "macro_micro"])
    def test_shown_then_hidden_leaves_the_section_as_it_was(self, booted, page):
        trip = booted[page]["trip"]
        assert trip is not None, "no toggle to drive"
        assert trip["grew"], "showing the JSON changed nothing"
        assert trip["restored"], (
            f"{page}: hiding the JSON did not restore section "
            f"{trip['key']!r} to its serialised form")
        assert not trip["residue"], "an empty wrapper was left behind"

    @pytest.mark.parametrize("page", ["golden", "macro_micro"])
    def test_what_it_shows_parses(self, booted, page):
        """It is the issue-pasting affordance: what it shows must be
        JSON that parses, not a rendering of one."""
        assert booted[page]["trip"]["parses"]


# The classifier, driven directly - no DOM, because `shapes.js` imports
# nothing and takes no document.
_CLASSIFY = """
const s = await import("%s/bga/viewer/shapes.js");
const caps = { nestLimit: 2, inlineFields: 4, inlineItems: 6 };
const answer = {};
for (const [name, [value, opts]] of Object.entries(%s)) {
  answer[name] = s.classify(value, { ...caps, ...(opts ?? {}) });
}
console.log(JSON.stringify({ answer, controls: s.CONTROLS }));
"""


def _classify(cases):
    result = subprocess.run(
        [node, "--input-type=module", "-e",
         _CLASSIFY % (REPO, json.dumps(cases))],
        capture_output=True, text=True, cwd=REPO, timeout=60)
    assert result.returncode == 0, result.stderr[-3000:]
    return json.loads(result.stdout)


@needs_node
class TestEveryRowOfTheTableHasAControl:
    """§1 is a table; `classify` is that table, and this is the table
    read back. A row that loses its control - or gains a second one -
    reddens here rather than in whichever section happened to hold that
    shape."""

    def test_each_shape_gets_its_declared_control(self):
        out = _classify({
            "short scalar array": [[1, 2, 3], None],
            "long scalar array": [list(range(9)), None],
            "array of objects": [[{"a": 1}, {"a": 2}], None],
            "array of pairs": [[["a", 1], ["b", 2]], None],
            "declared tuple": [[["a", 1]],
                               {"columns": [{"key": "name"},
                                            {"key": "count"}]}],
            "small keyed object": [{"a": 1, "b": 2}, None],
            "object map": [{f"e{i}.bst": {"n": i} for i in range(5)}, None],
            "severity list": [[{"severity": "high"}], {"severity": True}],
            "past the nesting cap": [{"a": {"b": {"c": 1}}}, {"depth": 2}],
        })
        controls = out["controls"]
        assert out["answer"] == {
            "short scalar array": controls["INLINE_LIST"],
            "long scalar array": controls["FOLDED_LIST"],
            "array of objects": controls["TABLE"],
            "array of pairs": controls["TUPLE_TABLE"],
            "declared tuple": controls["TABLE"],
            "small keyed object": controls["INLINE_OBJECT"],
            "object map": controls["MAP_TABLE"],
            "severity list": controls["FINDINGS"],
            "past the nesting cap": controls["FOLD"],
        }

    def test_a_mixed_array_is_unmapped(self):
        """The shape §1 has no row for, and the one the code used to
        improvise: `[{...}, 2]` reached `Array.prototype.toString` at
        section level and rendered `[object Object], 2` - strictly less
        than the JSON it replaced (`UX-277` found the same leaf in a
        table cell)."""
        out = _classify({
            "mixed": [[{"a": 1}, 2], None],
            "objects and arrays": [[{"a": 1}, ["b", 2]], None],
        })
        assert out["answer"] == {"mixed": None, "objects and arrays": None}


@needs_node
class TestAShapeTheGuideDoesNotCover:
    """The fourth clause: an unmapped shape lands in the fold *and*
    trips the dev-mode console check. Both halves, because either alone
    is a defect - a silent fold hides the design gap, and a warning with
    nothing rendered hides the value."""

    _PROBE = """
globalThis._makeNode ??= (await import(process.env.BGA_DOM_SHIM)).makeNode;
globalThis.document = { createElement: _makeNode,
                        createElementNS: (_n, t) => _makeNode(t),
                        getElementById: () => null };
const warnings = [];
globalThis.console = { ...console, warn: (m) => warnings.push(String(m)) };
const app = await import("./tests/viewer.mjs");
const shapes = await import("./bga/viewer/shapes.js");

// A payload key whose value is a mixed array. §1 has no row for it.
const cell = app.renderStructured("odd_shape", [{ a: 1 }, 2, "three"]);
const section = app.renderSection("odd_shape", [{ a: 1 }, 2, "three"]);

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
  cellTag: cell.tagName,
  cellSummary: text(find(cell, (n) => n.tagName === "summary")),
  cellFolded: Boolean(find(cell, (n) => (n.attrs.class || "").includes("full-text"))),
  sectionFolded: Boolean(find(section, (n) => (n.attrs.class || "").includes("full-text"))),
  warnings,
  noted: shapes.unmappedShapes(),
}));
"""

    @classmethod
    @pytest.fixture(scope="class")
    def probed(cls):
        result = subprocess.run(
            [node, "--input-type=module", "-e", cls._PROBE],
            capture_output=True, text=True, cwd=REPO, timeout=60,
            env=dict(os.environ,
                     BGA_DOM_SHIM=str(REPO / "tests" / "dom_shim.mjs")))
        assert result.returncode == 0, result.stderr[-3000:]
        return json.loads(result.stdout)

    def test_it_lands_in_the_labeled_fold(self, probed):
        assert probed["cellTag"] == "details"
        assert probed["cellFolded"], "no labeled fold body"
        assert "Odd shape" in probed["cellSummary"], probed["cellSummary"]
        # `UX-318`: the fold's count is now its shape - levels as well
        # as rows - so the reader knows the depth before the click.
        assert "2 levels, 3 rows" in probed["cellSummary"], probed["cellSummary"]

    def test_the_section_folds_it_too(self, probed):
        """Section level, not only cell level. This is where the
        improvisation was worst: the old branch rendered the whole
        array through `Array.prototype.toString`."""
        assert probed["sectionFolded"]

    def test_the_dev_check_says_which_path(self, probed):
        assert probed["warnings"], "unmapped shape rendered silently"
        message = probed["warnings"][0]
        assert "odd_shape" in message, message
        assert "styleguide" in message, message
        assert [note["where"] for note in probed["noted"]].count("odd_shape") >= 1


class TestStringifyIsAllowlisted:
    """`JSON.stringify` in the viewer, site by site.

    Not a count - a count passes when one site is deleted and another
    added. Every occurrence is resolved to the function that holds it
    and matched against this table, so a new one in a new function
    reddens and has to be argued for here.
    """

    ALLOWED = {
        # The published value on the cell, for filters, thresholds and
        # the copy path to read. An *attribute*, so it is never a text
        # node and never reaches the reader as text (`UX-205`).
        ("structured.js", "buildTable"): "data-raw",
        # `UX-277`'s labeled fold: §1's first deliberate site.
        ("structured.js", "renderStructured"): "the labeled fold",
        # `UX-302`'s toggle: §1's second.
        ("rawjson.js", "sectionJson"): "the view-as-JSON toggle",
        # The clipboard, which is not the page.
        ("tables.js", "rowJson"): "copy row",
        # `localStorage`, which is not the page either.
        ("nav.js", "writeCollapsed"): "remembered collapse state",
    }

    def _sites(self):
        found = []
        for path in sorted(VIEWER.glob("*.js")):
            lines = path.read_text(encoding="utf-8").splitlines()
            holder = "<file>"
            for line in lines:
                match = re.match(
                    r"^(?:export\s+)?(?:async\s+)?function\s+(\w+)", line)
                if match:
                    holder = match.group(1)
                if "JSON.stringify" not in line:
                    continue
                if line.lstrip().startswith(("//", "*")):
                    continue    # a comment naming it, not a call
                found.append((path.name, holder, line.strip()))
        return found

    def test_every_site_is_one_of_the_five(self):
        unexpected = [site for site in self._sites()
                      if (site[0], site[1]) not in self.ALLOWED]
        assert not unexpected, (
            "JSON.stringify outside the allowlist - a new rendering path "
            "must be argued for in styleguide.md §1 first:\n"
            + "\n".join(f"  {name}:{holder}: {line}"
                        for name, holder, line in unexpected))

    def test_the_allowlist_has_no_dead_entries(self):
        """The other direction: an allowlisted site that no longer
        exists is a stale permission, and stale permissions are how an
        allowlist stops meaning anything."""
        live = {(name, holder) for name, holder, _ in self._sites()}
        assert not (set(self.ALLOWED) - live), set(self.ALLOWED) - live


class TestTheGuideAndTheCodeAgree:
    """§1 is the authority; `shapes.js` is its implementation. If the
    guide gains a row and the code does not, the mapping is a document
    again rather than a law."""

    def test_every_control_the_module_names_is_in_the_guide(self):
        guide = (REPO / "docs/design/styleguide.md").read_text(encoding="utf-8")
        # Backticks out: the guide writes "inline `code` list" and the
        # module writes the name, and the difference is markup rather
        # than disagreement.
        section = guide.split("## 1.", 1)[1].split("\n## ", 1)[0]
        section = section.replace("`", "")
        source = (VIEWER / "shapes.js").read_text(encoding="utf-8")
        names = re.findall(r'^\s+\w+: "([^"]+)"', source, re.M)
        assert len(names) >= 8, names
        missing = [name for name in names if name not in section]
        assert not missing, (
            f"controls named in shapes.js but not in styleguide.md §1: "
            f"{missing}")

    def test_the_guide_points_at_the_module(self):
        guide = (REPO / "docs/design/styleguide.md").read_text(encoding="utf-8")
        assert "shapes.js" in guide, (
            "§1 must name the module that implements it, or the next "
            "reader has to find it")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
