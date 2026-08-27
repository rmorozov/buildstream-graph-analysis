"""UX-318: a fold announces its depth, and a nested table can be opened.

Styleguide §3a, from three field observations that turned out to be one
mechanism:

```text
"tables nest several levels deep and it is unknown for user
 how deep rabbit hole is"                                   -> §3a.1
"the resource blast table became scrollable, but nested
 doesn't work if I try to look through all rows"            -> §3a.3
"a separate button to enlarge table to occupy more space"   -> §3a.3
```

Ground truth before the fix, read off the two committed exports and the
stylesheet:

```text
fold summaries          "Provenance · 7 entries"   - width, never depth
main .map-table         max-height: 20rem; overflow-y: auto
main table              display: block; overflow-x: auto
```

Those last two are the field defect exactly: a `.map-table` inside a
`<td>` of a table that is itself inside a `.map-table` is a scroll
container inside a scroll container, and the inner one takes the wheel
while the outer one never moves. §3a abolishes the nesting rather than
tuning it - a table scrolls only when it is the widest thing on screen,
and the way to make it that is `Expand`.

**Focus is a section, not an overlay.** Round 24 declined the element
drawer with an argument that still holds: overlay machinery is the one
part of this page that does not survive an export, a print,
`filter: grayscale` or a pasted anchor. So the acceptance's hardest
clause is the one below that asserts the document is **byte-identical**
after going back, and the second hardest is that the export carries no
focus machinery at all.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")
VIEWER = REPO / "bga" / "viewer"
SHIM = str(REPO / "tests" / "dom_shim.mjs")
GOLDEN = REPO / "tests" / "fixtures" / "golden" / "mixed_task_kinds"
MACRO = REPO / "tests" / "fixtures" / "macro_micro" / "run"


def _js(body):
    source = """
globalThis._makeNode ??= (await import(process.env.BGA_DOM_SHIM)).makeNode;
globalThis.document = { createElement: _makeNode,
                        createElementNS: (_n, t) => _makeNode(t),
                        getElementById: () => null, querySelector: () => null };
globalThis.location = { protocol: "file:", href: "http://x/" };
globalThis.window = { localStorage: { getItem: () => null, setItem: () => {} } };
globalThis.CSS = { escape: (s) => s };
globalThis.Event = class { constructor(t) { this.type = t; } };
const all = (n, pred, out = []) => {
  if (pred(n)) out.push(n);
  for (const c of n.children ?? []) all(c, pred, out);
  return out;
};
const text = (n) => !n ? "" : ((n.children ?? []).length
  ? (n._text ?? "") + n.children.map(text).join("") : (n._text ?? ""));
""" + body
    result = subprocess.run(
        [node, "--input-type=module", "-e", source],
        capture_output=True, text=True, cwd=REPO, timeout=90,
        env=dict(os.environ, BGA_DOM_SHIM=SHIM))
    assert result.returncode == 0, result.stderr[-3000:]
    return json.loads(result.stdout)


# --------------------------------------------------------------------------
# 1. Counting, and what it counts.
# --------------------------------------------------------------------------

@needs_node
class TestTheDepthIsCounted:
    """`shapeOf` is the whole of §3a.1's arithmetic, and §3a is careful
    that it is arithmetic: counting is not analysis. Known answers, so a
    change to the walk has to change these."""

    @pytest.mark.parametrize("value,expected", [
        ([1, 2, 3], {"levels": 1, "rows": 3}),
        ([{"a": 1}, {"a": 2}], {"levels": 2, "rows": 2}),
        ({"x": [{"y": [1]}]}, {"levels": 4, "rows": 1}),
        ({}, {"levels": 1, "rows": 0}),
        (7, {"levels": 0, "rows": 0}),
        (None, {"levels": 0, "rows": 0}),
    ])
    def test_known_shapes(self, value, expected):
        out = _js("""
const { shapeOf } = await import("./bga/viewer/shapes.js");
console.log(JSON.stringify(shapeOf(%s)));
""" % json.dumps(value))
        assert out == expected

    def test_the_sentence_is_the_numbers(self):
        out = _js("""
const { depthSentence } = await import("./bga/viewer/shapes.js");
console.log(JSON.stringify([depthSentence([1, 2, 3]), depthSentence([{a: 1}]),
                            depthSentence({x: {y: {z: 1}}})]));
""")
        assert out == ["1 level, 3 rows", "2 levels, 1 row", "3 levels, 1 row"]


# --------------------------------------------------------------------------
# 2. No scroll container inside another.
# --------------------------------------------------------------------------

def _parse(css):
    """`[(selector, {property: value})]` in source order, comments gone."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    out = []
    for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        selector = " ".join(match.group(1).split())
        decls = {}
        for part in match.group(2).split(";"):
            if ":" in part:
                name, value = part.split(":", 1)
                decls[name.strip()] = value.strip()
        out.append((selector, decls))
    return out


def _merge(rules, selector):
    """The declarations `selector` ends up with. Later rules win."""
    merged = {}
    for candidate, decls in rules:
        if candidate == selector:
            merged.update(decls)
    return merged


def _rules():
    return _parse((VIEWER / "style.css").read_text(encoding="utf-8"))


def cascade(selector):
    """Every rule for `selector`, merged the way a browser merges them.

    `UX-332`. Both scroll clauses below used to stop at the **first**
    matching rule, and round 45's verification proved what that lets
    through: a second `main .map-table { overflow-y: auto }` appended
    later in the sheet restores the nested scrollbox, **wins the
    cascade in a real browser**, and left all twenty-one clauses in
    this file green - verified live before the fix.

    Later wins, because these selectors are textually identical and so
    have identical specificity; source order is the whole tiebreak.
    That is the narrow rule this needs and the whole of what it
    implements - `UX-332` declines a CSS cascade engine, and a guard
    that compared *different* selectors would need one.

    Returns `None` when the sheet has no such rule at all, which is a
    different fact from "a rule with nothing in it".
    """
    merged, seen = {}, False
    for candidate, decls in _rules():
        if candidate != selector:
            continue
        seen = True
        merged.update(decls)
    return merged if seen else None


class TestNestedScrollboxesAreGone:
    """§3a.3, and the defect it deletes rather than decorates."""

    def test_the_map_table_no_longer_scrolls_on_its_own(self):
        """Against the cascade's winner, not the first rule written.

        `UX-318`'s own log said "a second route to a nested scrollbox
        would redden too". It did not: this is that route, inverted
        into the guard.
        """
        decls = cascade("main .map-table")
        assert decls is not None, "no `main .map-table` rule at all"
        assert "max-height" not in decls and "overflow-y" not in decls, (
            "the nested scrollbox is back: a `.map-table` with its own "
            f"vertical scroll is the field defect ({decls})")

    def test_a_later_rule_is_the_one_that_counts(self):
        """The mechanism, on a sheet this test builds.

        Held separately from the clause above because that one passes
        whether or not the merge happens - there *is* only one
        `main .map-table` rule today. This one fails the moment the
        merge stops merging, and it is the round-45 evasion in the form
        a guard can keep.
        """
        css = ("main .map-table { overflow-y: visible; }\n"
               "main .other { color: red; }\n"
               "main .map-table { overflow-y: auto; max-height: 20rem; }\n")
        assert _merge(_parse(css), "main .map-table") == {
            "overflow-y": "auto", "max-height": "20rem"}, (
            "the first rule won, so an appended scroll rule is invisible - "
            "which is exactly how round 45 restored the scrollbox with "
            "every clause green")

    def test_only_the_outermost_table_scrolls(self):
        rule = cascade("main table table")
        assert rule, (
            "nothing stops a table inside a table's cell from having its "
            "own sideways scroll - the second box in the chain")
        assert rule.get("overflow") == "visible", rule


@needs_node
@pytest.mark.medium
class TestTheBootedPageHasOneScrollBoxPerChain:
    def test_no_scroll_container_sits_inside_another(self, booted):
        for page, out in booted.items():
            assert out["scrollChains"], f"{page} found no scroll container"
            worst = max(out["scrollChains"])
            assert worst <= 1, (
                f"{page}: a scroll container is {worst} deep inside another "
                f"- the wheel goes to the inner one and the outer never "
                f"moves. Chains: {out['scrollChains']}")


# --------------------------------------------------------------------------
# 3. Every fold on the real pages says how deep it goes.
# --------------------------------------------------------------------------

def _shape_of(value):
    """`shapeOf`, in Python, so the walk checks the page against the
    payload rather than against a second reading of the page."""
    if not isinstance(value, (dict, list)):
        return {"levels": 0, "rows": 0}
    members = value if isinstance(value, list) else list(value.values())
    deepest = 0
    for member in members:
        deepest = max(deepest, _shape_of(member)["levels"])
    return {"levels": 1 + deepest, "rows": len(members)}


def _resolve(payload, path):
    """The value a `data-fold-path` names, or `None` for one this
    payload does not have (a fold built from a nested row's key)."""
    at = payload
    for part in path.split("."):
        if isinstance(at, dict) and part in at:
            at = at[part]
        else:
            return None
    return at


@needs_node
@pytest.mark.medium
class TestEveryFoldStatesItsDepth:
    """§3a.1: "A cell that folds deeper content states what is below it
    - '2 levels, 34 rows' - before any click." The unknown-depth rabbit
    hole is the defect; the count is the fix."""

    def test_every_fold_carries_both_numbers(self, booted):
        for page, out in booted.items():
            assert out["folds"], f"{page} has no folds to check"
            for fold in out["folds"]:
                assert fold["levels"] and fold["rows"] is not None, (page, fold)
                assert int(fold["levels"]) >= 1, (page, fold)

    def test_the_summary_says_what_the_attributes_say(self, booted):
        """The sentence and the numbers are one claim; a drift between
        them is a fold that lies to the reader in prose."""
        for page, out in booted.items():
            for fold in out["folds"]:
                levels, rows = int(fold["levels"]), int(fold["rows"])
                want = (f"{levels} level{'' if levels == 1 else 's'}, "
                        f"{rows} row{'' if rows == 1 else 's'}")
                assert want in fold["summary"], (page, want, fold["summary"])

    def test_the_numbers_are_the_folded_value_s_actual_shape(self, booted):
        """The walk the acceptance names. Not "a fold has numbers" - the
        numbers are `shapeOf` of the value in the payload, recomputed
        here from the published JSON."""
        checked = 0
        for page, out in booted.items():
            payload = out["payload"]
            for fold in out["folds"]:
                path = fold["path"]
                if not path:
                    continue
                value = _resolve(payload, path)
                if value is None:
                    continue
                want = _shape_of(value)
                assert int(fold["levels"]) == want["levels"], (page, path, fold)
                assert int(fold["rows"]) == want["rows"], (page, path, fold)
                checked += 1
        assert checked >= 10, (
            f"only {checked} folds resolved against the payload - the walk "
            f"is checking almost nothing")


# --------------------------------------------------------------------------
# 4. Focus: opening, going back, and the fragment.
# --------------------------------------------------------------------------

@needs_node
@pytest.mark.medium
class TestANestedTableOpensInFocus:
    def test_the_export_offers_no_focus_machinery(self, booted):
        """§3a and the acceptance both: the export renders folds with
        counts and nothing else. A file somebody scrolls, prints and
        attaches has nothing to rearrange."""
        for page, out in booted.items():
            assert out["expands"] == [], (
                f"{page}'s export carries {len(out['expands'])} expand "
                f"controls")

    def test_a_served_page_offers_it_on_the_nested_tables(self, served):
        for page, out in served.items():
            assert out["expands"], f"{page} offered no expand control"
            # Nested, not every fold: a section's own table has the
            # column to itself already.
            assert all("." in path for path in out["expands"]), out["expands"]

    def test_opening_gives_the_table_the_column_and_a_way_back(self, served):
        for page, out in served.items():
            opened = out["opened"]
            assert opened["focused"] == opened["which"], (page, opened)
            assert opened["hasTable"] >= 1, (page, opened)
            assert opened["crumb"].startswith("← "), (page, opened)
            assert opened["crumb"] != "← the report", (
                f"{page}: the breadcrumb does not name the section it came "
                f"from ({opened['crumb']})")
            # The rest of the report stands behind it - every section,
            # except the one that *is* the thing expanded.
            assert opened["behind"] == opened["sections"] - opened["inFocus"], (
                page, opened)

    def test_no_row_of_the_opened_table_is_inside_a_scrollbox(self, served):
        """The field defect, inverted into the guard: the reason a
        nested table could not be read through was that its rows were in
        a box inside a box. In focus there is one container, and it is
        the page."""
        for page, out in served.items():
            assert out["opened"]["chainsInFocus"] == [] or max(
                out["opened"]["chainsInFocus"]) <= 1, (page, out["opened"])

    def test_going_back_leaves_the_document_byte_identical(self, served):
        """The round-24 argument, made checkable. An overlay could not
        promise this; a section that moves a node and puts it back can,
        and "we put it back" is not a measurement."""
        for page, out in served.items():
            assert out["restored"], (
                f"{page}: the document differs after going back - focus "
                f"left something behind")
            assert out["stillFocused"] is None, page
            assert out["behindAfter"] == 0, page

    def test_the_open_table_travels_in_the_fragment(self, served):
        """`UX-211`'s rule: what I am looking at is a link. Read off the
        page's own `location`, because `wireViewState` is the only
        writer of the hash and this has to be the hash a reader would
        copy - not a second call to `captureView`."""
        for page, out in served.items():
            assert f"tf={out['opened']['which']}" in out["captured"], (
                page, out["captured"])
            assert "tf=" not in out["afterHash"], (
                f"{page}: going back left the table in the link "
                f"({out['afterHash']})")

    def test_a_pasted_link_opens_the_table_again(self):
        """The other direction, in one module instance. It cannot be
        done on the exported page: the export inlines every module into
        one script, so importing `viewstate.js` beside it makes a second
        registry and a green that means nothing."""
        out = _js("""
const { applyView, captureView } = await import("./bga/viewer/viewstate.js");
const { registerFocusTarget, forgetFocusTargets }
  = await import("./bga/viewer/tablefocus.js");
forgetFocusTargets();
const root = _makeNode("div");
const section = _makeNode("section");
section.setAttribute("data-section", "signals");
const box = _makeNode("div");
const table = _makeNode("table");
table.setAttribute("data-table", "signals.deps");
box.append(table);
section.append(box);
root.append(section);
registerFocusTarget("signals.deps",
                    { label: "Deps", breadcrumb: "Signals", node: box });
const applied = applyView(root, "tf=signals.deps");
const opened = root.attrs["data-table-focused"] ?? null;
const captured = captureView(root);
// And a path this document does not have: applied in silence, not a throw.
const stranger = applyView(root, "tf=nothing.here");
console.log(JSON.stringify({
  applied, opened, captured,
  behind: section.attrs["data-behind-focus"] ?? null,
  strangerOpened: root.attrs["data-table-focused"] ?? null,
  strangerApplied: stranger }));
""")
        assert out["applied"] == ["tf:signals.deps"], out
        assert out["opened"] == "signals.deps"
        assert "tf=signals.deps" in out["captured"]
        # The table left the section, so the section stands behind - that
        # is the whole point of the state. What must *not* happen is a
        # section standing behind a focus it contains, which is the case
        # below.
        assert out["behind"] == "true", out
        # A `tf` for a table this run does not have applies **nothing**
        # and leaves what was open alone - `applyView`'s own rule for a
        # preset the run does not offer, which is the same shape: a link
        # from one report opening another applies what it can, in
        # silence, and never throws.
        assert out["strangerOpened"] == "signals.deps", out
        assert "tf:" not in " ".join(out["strangerApplied"]), out

    def test_a_whole_section_can_be_the_thing_expanded(self):
        """A capped *top-level* table is its section, and hiding every
        `section[data-section]` would then hide the thing the reader
        asked to see. Measured rather than reasoned about: the first
        draft did exactly that."""
        out = _js("""
const { enterTableFocus, registerFocusTarget, leaveTableFocus,
        forgetFocusTargets } = await import("./bga/viewer/tablefocus.js");
forgetFocusTargets();
const root = _makeNode("div");
const mine = _makeNode("section");
mine.setAttribute("data-section", "floors");
const other = _makeNode("section");
other.setAttribute("data-section", "signals");
root.append(mine); root.append(other);
registerFocusTarget("floors", { label: "Floors", breadcrumb: "the report",
                                node: mine });
enterTableFocus(root, "floors");
const opened = { mine: mine.attrs["data-behind-focus"] ?? null,
                 other: other.attrs["data-behind-focus"] ?? null };
leaveTableFocus(root);
console.log(JSON.stringify({ opened,
  after: { mine: mine.attrs["data-behind-focus"] ?? null,
           other: other.attrs["data-behind-focus"] ?? null },
  focused: root.attrs["data-table-focused"] ?? null }));
""")
        assert out["opened"] == {"mine": None, "other": "true"}, out
        assert out["after"] == {"mine": None, "other": None}, out
        assert out["focused"] is None


# --------------------------------------------------------------------------
# The harness.
# --------------------------------------------------------------------------

def _probe_source():
    source = (REPO / "tests/unit/test_a_report_you_can_navigate.py").read_text()
    return source.split('_PROBE = r"""', 1)[1].rsplit('"""', 1)[0]


# Which selectors are scroll containers, read from the stylesheet rather
# than listed here: a rule that grows a new `overflow` has to show up in
# the chain count, not sit outside a hand-written list.
_HELPERS = r"""
const all = (n, pred, out = []) => {
  if (pred(n)) out.push(n);
  for (const c of n.children ?? []) all(c, pred, out);
  return out;
};
const text = (n) => !n ? "" : ((n.children ?? []).length
  ? (n._text ?? "") + n.children.map(text).join("") : (n._text ?? ""));
const dump = (n) => { if (!n) return "";
  const a = Object.entries(n.attrs ?? {}).sort().map(([k, v]) => `${k}=${v}`).join(" ");
  return `<${n.tagName} ${a}>${n._text ?? ""}`
    + (n.children ?? []).map(dump).join("") + `</${n.tagName}>`; };
// A scroll box, as the stylesheet defines one for *tables*: `main table`
// (unless it is a table inside a table, which the sheet turns off) and
// `main .map-table` if it ever gets its scroll back.
const scrolls = (n) => {
  const klass = String(n.className || n.attrs?.class || "").split(" ");
  if (klass.includes("map-table")) return MAP_TABLE_SCROLLS;
  if (n.tagName !== "table") return false;
  let at = n._parent;
  while (at) { if (at.tagName === "table") return false; at = at._parent; }
  return true;
};
const chains = (root) => {
  const depths = [];
  (function walk(n, above) {
    const here = scrolls(n) ? above + 1 : above;
    if (scrolls(n)) depths.push(here);
    for (const c of n.children ?? []) walk(c, here);
  })(root, 0);
  return depths;
};
const folds = (root) => all(root, (n) => n.tagName === "details"
    && String(n.className || "").includes("map"))
  .map((n) => ({ levels: n.attrs["data-levels"], rows: n.attrs["data-rows"],
                 path: n.attrs["data-fold-path"] ?? null,
                 summary: text(n.children[0]).trim() }));
"""

_TAIL = r"""
const root = named["report"] ?? body;
const expands = all(root, (n) => n.attrs?.["data-expand"])
  .map((n) => n.attrs["data-expand"]);
const out = { folds: folds(root), expands, scrollChains: chains(root),
              payload: JSON.parse(blocks["report"] ?? "{}"),
              error: failure };
console.log(JSON.stringify(out));
"""

# The fragment is read off `location`, not by importing `viewstate.js`
# here: the export inlines every module into one script, so a second
# import would be a **second module instance** with its own focus
# registry - green against a copy of the page rather than the page. The
# hash is what the page itself wrote through `wireViewState`, which is
# the only writer (`UX-211`).
_SERVED_TAIL = r"""
const root = named["report"] ?? body;
const expands = all(root, (n) => n.attrs?.["data-expand"])
  .map((n) => n.attrs["data-expand"]);
const before = dump(root);
const button = all(root, (n) => n.attrs?.["data-expand"])[0];
const which = button.attrs["data-expand"];
button.click();
const section = all(root, (n) => n.attrs?.["data-table-focus"])[0] ?? null;
const back = all(root, (n) => n.attrs?.["data-focus-back"])[0] ?? null;
const opened = {
  which, focused: root.attrs["data-table-focused"] ?? null,
  crumb: back ? text(back) : null,
  heading: section ? text(section.children[1]) : null,
  hasTable: section ? all(section, (n) => n.tagName === "table").length : 0,
  behind: all(root, (n) => n.attrs?.["data-behind-focus"] === "true").length,
  sections: all(root, (n) => n.attrs?.["data-section"]).length,
  inFocus: section ? all(section, (n) => n.attrs?.["data-section"]).length : 0,
  chainsInFocus: section ? chains(section) : [],
};
const captured = String(location.hash ?? "");
back.click();
const after = dump(root);
const afterHash = String(location.hash ?? "");
console.log(JSON.stringify({
  expands, opened, captured, afterHash, restored: before === after,
  stillFocused: root.attrs["data-table-focused"] ?? null,
  behindAfter: all(root, (n) => n.attrs?.["data-behind-focus"] === "true").length,
  error: failure }));
"""


def _boot(run_dir, tmp, protocol, tail, extra_helpers=""):
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
    probe.write_text(
        _probe_source().split("const report =", 1)[0]
        + extra_helpers + _HELPERS + tail, encoding="utf-8")
    result = subprocess.run(
        [node, str(probe)], capture_output=True, text=True, cwd=REPO,
        timeout=180,
        env=dict(os.environ, PAGE=str(page), MOD=str(module),
                 PROTOCOL=protocol, BGA_DOM_SHIM=SHIM,
                 VIEWSTATE=str(VIEWER / "viewstate.js")))
    assert result.returncode == 0, result.stderr[-4000:]
    out = json.loads(result.stdout)
    assert out["error"] is None, out["error"]
    return out


# `main .map-table` is expected to have **no** scroll of its own after
# this item; the probe reads that from the sheet so the chain walk fails
# if the rule comes back rather than quietly counting one box fewer.
def _map_table_scrolls():
    # UX-332: the cascade's winner, not the first rule. This feeds the
    # *booted* walk, so a first-match read here meant the browser saw a
    # scrollbox while the walk was told there was none - the two halves
    # of the round-45 evasion, and this is the half that made the live
    # page and the guard disagree.
    decls = cascade("main .map-table") or {}
    return "overflow-y" in decls or "max-height" in decls


def _pages(protocol, tail):
    helpers = f"const MAP_TABLE_SCROLLS = {str(_map_table_scrolls()).lower()};\n"
    pages = {}
    for name, run in (("golden", GOLDEN), ("macro_micro", MACRO)):
        tmp = Path(tempfile.mkdtemp())
        try:
            pages[name] = _boot(run, tmp, protocol, tail, helpers)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    return pages


@pytest.fixture(scope="module")
def booted():
    return _pages("file:", _TAIL)


@pytest.fixture(scope="module")
def served():
    return _pages("http:", _SERVED_TAIL)
