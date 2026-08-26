"""UX-319: the chain's listing folds, and navigation is priced.

Styleguide §3b, and `UX-187` reaching its third surface.

**The chain.** `UX-187` taught the text report to fold the chain's
middle; `UX-196` gave the drawn strip a fold at `PATH_HEAD = 6` /
`PATH_TAIL = 3`. The *listing* — `signals.critical_path_detail`, lifted
into its own section — rendered whole, and "occupies a lot of space".

`UX-262`'s Top-N was not the answer waiting to be applied: it is a
**rank** bound, and the twenty-five longest steps of a hundred-step
chain are not the chain. A path's meaning is its order, so the listing
folds head-and-tail by the same two numbers the drawing uses — one
chain, one elision, two surfaces.

**The clicks.** Round 38 answered forty-eight fragments with chapters
and nobody has since measured what a traversal costs. §3b sets the
budget — any section's content within **two interactions** of its rail
entry — and this file is the walk. The model, and every term in it is
read off the booted page rather than assumed:

```text
cost(section) = (the rail is folded ? 1 : 0)      # narrow only
              + 1                                  # its rail link
              + (it starts collapsed ? 1 : 0)      # expand it
```

A section with no rail link at all is unreachable and reported as such
rather than scored.

Measured, on the two committed exports:

```text
                       wide (rail open)   narrow (rail folded)
golden      28 sections        1                    2
macro_micro 37 sections        1                    2
unreachable                    0                    0
```

Both within budget before this item and after it — which is the honest
answer, and the reason the walk is the deliverable rather than a fix.
What it buys is that the *next* structure change cannot quietly spend a
third click: the guard reddens before a reader meets it.
"""
import json
import os
import re
import shutil
import subprocess
import sys
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

#: §3b's budget: open the chapter, open the section. A third click in
#: the common path is a structure change that has to be argued for.
CLICK_BUDGET = 2


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
# 1. The chain's listing folds, by the chain's own numbers.
# --------------------------------------------------------------------------

@needs_node
class TestTheChainsListingFolds:
    """Driven through `liftedCriticalPath`, which is the function that
    builds this section, on a chain long enough to fold.

    Neither committed fixture is: both publish a **ten**-element chain,
    and `PATH_HEAD + PATH_TAIL + 1` is exactly ten, so the real pages
    render whole and correctly so. Stated rather than left as a silent
    gap - "no fold on the golden page" is a property of the fixture, not
    evidence the fold is absent.
    """

    def _chain(self, length):
        return _js("""
const { liftedCriticalPath } = await import("./bga/viewer/app.js");
const { PATH_HEAD, PATH_TAIL } = await import("./bga/viewer/views.js");
const rows = Array.from({ length: %d }, (_, i) => ({
  element_uid: `e${i}.bst`, duration_us: 1000 * (%d - i),
  share_of_path: 0.05 }));
const section = liftedCriticalPath({ critical_path_detail: rows }, undefined);
const body = all(section, (n) => n.tagName === "tbody")[0];
const trs = body.children;
const button = all(section, (n) =>
  String(n.className ?? "").includes("fold-more"))[0] ?? null;
const shown = () => trs.filter((r) => r.hidden !== true)
  .filter((r) => !r.attrs["data-fold-rows"]).length;
const before = shown();
if (button) button.click();
console.log(JSON.stringify({
  head: PATH_HEAD, tail: PATH_TAIL,
  rows: trs.filter((r) => !r.attrs["data-fold-rows"]).length,
  shownBefore: before, shownAfter: shown(),
  foldedAt: trs.findIndex((r) => r.attrs["data-fold-rows"]),
  folded: button ? Number(button.attrs["data-folded"]) : null,
  label: button ? text(button) : null,
  title: button ? button.attrs.title : null,
}));
""" % (length, length))

    def test_a_long_chain_shows_its_head_and_its_tail(self):
        out = self._chain(20)
        assert out["rows"] == 20
        assert out["shownBefore"] == out["head"] + out["tail"], out
        assert out["folded"] == 20 - out["head"] - out["tail"], out

    def test_the_fold_sits_between_the_two_ends(self):
        """Not at the bottom: the middle is what was elided, so the
        control stands where the middle was."""
        out = self._chain(20)
        assert out["foldedAt"] == out["head"], out

    def test_it_says_how_many_and_out_of_how_many(self):
        """§3a.1's rule on this surface: the count is visible before the
        click, and the denominator with it - `UX-208`'s point that a
        reader who cannot see the total cannot tell a fold from a short
        chain."""
        out = self._chain(20)
        assert out["label"] == "+11 more elements (20 in all)", out["label"]
        assert out["title"] == (
            "Show the 11 elements between the first 6 and the last 3")

    def test_opening_it_shows_every_element(self):
        out = self._chain(20)
        assert out["shownAfter"] == 20, out

    @pytest.mark.parametrize("length", [1, 5, 9, 10])
    def test_a_chain_that_would_hide_one_row_or_none_does_not_fold(self, length):
        """`head + tail + 1` is the threshold: below it the fold would
        hide fewer rows than the control it adds costs."""
        out = self._chain(length)
        assert out["folded"] is None, (length, out)
        assert out["shownBefore"] == length, (length, out)

    def test_the_two_surfaces_fold_by_one_pair_of_numbers(self):
        """The drawn strip and the listing are the same chain. Two
        elisions of one path would be two paths, so the numbers are
        exported from where the drawing declares them and imported
        where the listing uses them - asserted from the source, because
        a second copy would agree today and drift tomorrow."""
        views = (VIEWER / "views.js").read_text(encoding="utf-8")
        app = (VIEWER / "app.js").read_text(encoding="utf-8")
        assert re.search(r"export const PATH_HEAD = \d+;", views), (
            "the chain's fold numbers are not exported")
        assert "PATH_HEAD, PATH_TAIL } from \"./views.js\"" in app, (
            "app.js declares its own chain fold rather than importing the "
            "one the drawing uses")
        assert not re.search(r"const PATH_HEAD\s*=", app), (
            "a second copy of the chain's head count lives in app.js")


# --------------------------------------------------------------------------
# 2. The clicks, counted.
# --------------------------------------------------------------------------

def _probe_source():
    source = (REPO / "tests/unit/test_a_report_you_can_navigate.py").read_text()
    return source.split('_PROBE = r"""', 1)[1].rsplit('"""', 1)[0]


# `matchMedia` is what `foldOnNarrow` asks the window for, and the shim
# has no window. Supplying it is how the narrow case gets measured at
# all: without it the rail is never folded here and the walk reports the
# wide cost twice.
_NARROW = """
globalThis.__narrow = process.env.NARROW === "1";
"""

_TAIL = r"""
const all = (n, pred, out = []) => {
  if (pred(n)) out.push(n);
  for (const c of n.children ?? []) all(c, pred, out);
  return out;
};
const root = named["report"] ?? body;
const nav = all(body, (n) => n.tagName === "nav"
  && String(n.className ?? "").includes("toc"))[0] ?? null;
const railFolded = nav?.attrs?.["data-folded"] === "true";
const links = nav ? all(nav, (n) => n.attrs?.["data-toc"]) : [];
const chapters = nav ? all(nav, (n) => n.attrs?.["data-toc-chapter"]) : [];
const linked = new Set(links.map((n) => n.attrs["data-toc"]));
const walked = all(root, (n) => n.attrs?.["data-section"]).map((s) => {
  const key = s.attrs["data-section"];
  const collapsed = s.attrs["data-collapsed"] === "true";
  if (!linked.has(key)) return { key, cost: null, why: "no rail entry" };
  // The rail's fold is one interaction, and only where it is folded.
  // Clicking the entry is the second. A section the reader has to
  // expand costs a third, which is what the budget refuses.
  return { key, collapsed,
           cost: (railFolded ? 1 : 0) + 1 + (collapsed ? 1 : 0) };
});
const scored = walked.filter((w) => w.cost !== null);
console.log(JSON.stringify({
  railFolded, chapters: chapters.length, sections: walked.length,
  unreachable: walked.filter((w) => w.cost === null).map((w) => w.key),
  worst: scored.length ? Math.max(...scored.map((w) => w.cost)) : 0,
  overBudget: scored.filter((w) => w.cost > %d).map((w) => [w.key, w.cost]),
  histogram: scored.reduce((h, w) => {
    h[w.cost] = (h[w.cost] ?? 0) + 1; return h; }, {}),
  error: failure }));
""" % CLICK_BUDGET


def _boot(run_dir, tmp, narrow):
    run = tmp / "run"
    shutil.copytree(run_dir, run)
    (run / "expected_output.json").unlink(missing_ok=True)

    import tools.bga_view as view

    page = tmp / "report.html"
    view.export(str(run), str(page))
    html = page.read_text(encoding="utf-8")
    module = tmp / "inline.mjs"
    module.write_text(
        re.search(r'<script type="module">(.*?)</script>', html, re.S).group(1),
        encoding="utf-8")
    head = _probe_source().split("const report =", 1)[0]
    # The window the rail asks about its width. Inserted into the probe
    # rather than into the page: this is the *harness* standing in for a
    # viewport, which is exactly what `UX-257` says the shim may not
    # pretend to be - so it models one API and nothing else.
    head = head.replace(
        'globalThis.fetch = async () => { throw new Error("no network here"); };',
        'globalThis.fetch = async () => { throw new Error("no network here"); };\n'
        'globalThis.document.defaultView = {\n'
        '  matchMedia: () => ({ matches: process.env.NARROW === "1",\n'
        '                       addEventListener: () => {} }),\n'
        '};')
    probe = tmp / "probe.mjs"
    probe.write_text(head + _TAIL, encoding="utf-8")
    result = subprocess.run(
        [node, str(probe)], capture_output=True, text=True, cwd=REPO,
        timeout=180,
        env=dict(os.environ, PAGE=str(page), MOD=str(module),
                 PROTOCOL="file:", BGA_DOM_SHIM=SHIM,
                 NARROW="1" if narrow else "0"))
    assert result.returncode == 0, result.stderr[-4000:]
    out = json.loads(result.stdout)
    assert out["error"] is None, out["error"]
    return out


@pytest.fixture(scope="module")
def walks(tmp_path_factory):
    found = {}
    for name, run in (("golden", GOLDEN), ("macro_micro", MACRO)):
        for narrow in (False, True):
            found[(name, narrow)] = _boot(
                run, tmp_path_factory.mktemp(f"{name}-{narrow}"), narrow)
    return found


@needs_node
@pytest.mark.medium
class TestTheClicksAreCounted:
    def test_the_rail_state_is_what_the_width_says(self, walks):
        """The instrument first. A walk that measured the wide cost
        twice and called it "both viewports" would be green and worth
        nothing - which is the failure mode `UX-213` named."""
        for (page, narrow), out in walks.items():
            assert out["railFolded"] is narrow, (page, narrow, out["railFolded"])

    def test_every_section_has_a_way_in(self, walks):
        for (page, narrow), out in walks.items():
            assert out["unreachable"] == [], (page, narrow, out["unreachable"])
            assert out["sections"] > 20, (page, out["sections"])

    def test_no_path_costs_more_than_the_budget(self, walks):
        for (page, narrow), out in walks.items():
            assert out["overBudget"] == [], (page, narrow, out["overBudget"])
            assert out["worst"] <= CLICK_BUDGET, (page, narrow, out)

    def test_the_measured_worst_is_the_one_this_file_records(self, walks):
        """The numbers in the docstring, held to the page. A budget
        nobody can fail is not a budget; these say where the slack
        actually is."""
        expected = {("golden", False): 1, ("golden", True): 2,
                    ("macro_micro", False): 1, ("macro_micro", True): 2}
        measured = {key: out["worst"] for key, out in walks.items()}
        assert measured == expected, measured
