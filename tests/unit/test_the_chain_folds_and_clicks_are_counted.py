"""UX-319: the chain's listing folds, and navigation is priced.

Styleguide §3b, and `UX-187` reaching its third surface.

**The chain.** `UX-187` taught the text report to fold the chain's
middle; `UX-196` gave the drawn strip a fold at `PATH_HEAD = 6` /
`PATH_TAIL = 3`. The *listing* — `critical_path_detail`, lifted
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
sys.path.insert(0, str(REPO / "tests"))

from browser import NO_BROWSER, Browser, find_chrome
from pages import snapshot_copy

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)
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
globalThis._installDocument ??= (await import(process.env.BGA_DOM_SHIM)).installDocument;
_installDocument();
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
const { liftedCriticalPath } = await import("./tests/viewer.mjs");
const { PATH_HEAD, PATH_TAIL } = await import("./tests/viewer.mjs");
const rows = Array.from({ length: __LENGTH__ }, (_, i) => ({
  element_uid: `e${i}.bst`, duration_us: 1000 * (__LENGTH__ - i),
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
""".replace("__LENGTH__", str(length)))

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
        # `UX-337`: the listing is `liftedCriticalPath`, which moved to
        # `structured.js` with the rest of the table machinery. What
        # this asserts is that the listing *imports* the drawing's two
        # numbers rather than restating them, wherever the listing is.
        listing = (VIEWER / "structured.js").read_text(encoding="utf-8")
        assert re.search(r"export const PATH_HEAD = \d+;", views), (
            "the chain's fold numbers are not exported")
        assert "PATH_HEAD, PATH_TAIL } from \"./views.js\"" in listing, (
            "structured.js declares its own chain fold rather than importing "
            "the one the drawing uses")
        for name in ("app.js", "structured.js"):
            assert not re.search(
                r"const PATH_HEAD\s*=",
                (VIEWER / name).read_text(encoding="utf-8")), (
                f"a second copy of the chain's head count lives in {name}")


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
  overBudget: scored.filter((w) => w.cost > __CLICK_BUDGET__).map((w) => [w.key, w.cost]),
  histogram: scored.reduce((h, w) => {
    h[w.cost] = (h[w.cost] ?? 0) + 1; return h; }, {}),
  error: failure }));
""".replace("__CLICK_BUDGET__", str(CLICK_BUDGET))


def _boot(run_dir, tmp, narrow):
    run = snapshot_copy(run_dir, tmp)

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


# --------------------------------------------------------------------------
# 3. The distance, budgeted (UX-347).
# --------------------------------------------------------------------------
#
# Round 52 measured what §3b cannot see. Every walk above costs one
# click, and it cost one click because **almost nothing was folded**:
# 51 `details` on the page, 3 open, every *section* permanently
# expanded, and the document 22.7 screens. Zero clicks to `confidence`
# — and 18.3 screens of scroll past nineteen things nobody asked for.
#
# A click is directed: the reader names what they want and arrives. A
# screen of scroll is a search. §3b measured the first and nothing
# measured the second, so the design optimised exactly what was
# measured. The clauses below are the second currency, in the same
# file, so a change that spends one to buy the other reddens on the
# side it was paid from.
#
# The instrument is a real browser, because this is layout and the shim
# is not allowed to pretend it models layout (`UX-257`). The walk above
# stays where it is: it counts structure, which the shim can see.

#: The document a reader lands on, at 1440x900, in screens. Measured
#: after chapters fold: 4.1 (golden) and 6.6 (macro_micro), against
#: 11.6 and 22.7 before. The bound is 10 - one and a half times the
#: worst measured, which admits a run with more findings in the open
#: first chapter and reddens on a page that stops folding at all.
DOCUMENT_SCREENS = 10.0

#: How far the *last* chapter's question sits from the top. Measured
#: 3.8 and 6.3; a reader scanning the chapter list should not have to
#: scroll a screenful per chapter to read the next question.
CHAPTER_HEADING_SCREENS = 8.0

#: And inside a chapter, its first section under its own heading.
#: Measured 0.1 on every chapter of both fixtures: the heading, the
#: chapter's one-line answer, the control, the section.
CHAPTER_FIRST_SECTION_SCREENS = 0.5

_DISTANCE = r"""
(() => {
  const scr = (px) => Math.round(px / 900 * 10) / 10;
  // The eight destinations the round-52 census walked, by the
  // selectors it used - published in the failure message in both
  // currencies, which is the acceptance test's own clause.
  const targets = {
    "the verdict sentence": '[data-section="decision"] p',
    "what to fix first": '[data-section="decision"] a',
    "the element table": '[data-section="signals"] table',
    "the critical path list": '[data-section="critical_path_detail"]',
    "a Perfetto query": '[data-section="perfetto-questions"] code,'
                      + ' [data-section="perfetto-questions"] pre',
    "the memory envelope": '[data-section="capacity_recommendation"],'
                         + ' [data-section="occupancy"]',
    "confidence": '[data-section="confidence"]',
    "the run identity": '[data-section="run_instance"], [data-section="producer"]',
  };
  const reach = {};
  for (const [name, sel] of Object.entries(targets)) {
    const node = document.querySelector(sel);
    if (!node) { reach[name] = null; continue; }
    const box = node.closest("section.chapter");
    const folded = box?.getAttribute("data-open") === "false";
    // The rail entry, plus any content fold still shut around it. The
    // chapter is not a third click: its rail link opens it, which the
    // clause below clicks rather than assumes.
    let clicks = 1;
    for (let p = node; p; p = p.parentElement) {
      if (p.tagName === "DETAILS" && !p.open) clicks += 1;
    }
    if (box) box.setAttribute("data-open", "true");
    const top = node.getBoundingClientRect().top + window.scrollY;
    if (folded && box) box.setAttribute("data-open", "false");
    reach[name] = { clicks, screensDown: scr(top), behindFold: Boolean(folded) };
  }
  const chapters = [...document.querySelectorAll("section.chapter")].map((c) => {
    const open = c.getAttribute("data-open") !== "false";
    c.setAttribute("data-open", "true");
    const first = c.querySelector("[data-section]");
    const inside = first
      ? scr(first.getBoundingClientRect().top - c.getBoundingClientRect().top)
      : null;
    if (!open) c.setAttribute("data-open", "false");
    return {
      id: c.getAttribute("data-chapter"),
      open,
      answer: c.querySelector(".chapter-answer")?.innerText ?? null,
      control: c.querySelector(".chapter-open")?.innerText ?? null,
      sections: c.querySelectorAll("[data-section]").length,
      headingScr: scr(c.querySelector(".chapter-title")
        .getBoundingClientRect().top + window.scrollY),
      firstSectionScr: inside,
    };
  });
  return { documentScr: scr(document.documentElement.scrollHeight),
           chapters, reach };
})()
"""

_RAIL_OPENS = r"""
(() => {
  const out = [];
  for (const link of document.querySelectorAll("[data-toc]")) {
    const key = link.getAttribute("data-toc");
    const target = document.getElementById(key);
    if (!target) { out.push([key, "no section"]); continue; }
    const box = target.closest("section.chapter");
    if (!box) { out.push([key, "no chapter"]); continue; }
    box.setAttribute("data-open", "false");
    link.click();
    if (box.getAttribute("data-open") !== "true") out.push([key, "stayed shut"]);
    else if (target.getBoundingClientRect().height <= 0) out.push([key, "not drawn"]);
  }
  return out;
})()
"""


@needs_browser
@pytest.mark.medium
class TestTheDistanceIsBudgetedToo:
    def test_the_document_fits_the_budget(self, browser, exports):
        for page, url in exports.items():
            out = browser.measure(url, _DISTANCE, width=1440, height=900)
            assert out["documentScr"] <= DOCUMENT_SCREENS, (
                f"{page}: the document is {out['documentScr']} screens at "
                f"1440x900, against a budget of {DOCUMENT_SCREENS}. "
                f"{_walk(out)}")

    def test_every_chapter_question_is_within_reach(self, browser, exports):
        for page, url in exports.items():
            out = browser.measure(url, _DISTANCE, width=1440, height=900)
            far = [(c["id"], c["headingScr"]) for c in out["chapters"]
                   if c["headingScr"] > CHAPTER_HEADING_SCREENS]
            assert far == [], (
                f"{page}: a chapter's question is more than "
                f"{CHAPTER_HEADING_SCREENS} screens down: {far}. {_walk(out)}")

    def test_a_chapters_first_section_is_under_its_own_heading(
            self, browser, exports):
        for page, url in exports.items():
            out = browser.measure(url, _DISTANCE, width=1440, height=900)
            far = [(c["id"], c["firstSectionScr"]) for c in out["chapters"]
                   if (c["firstSectionScr"] or 0) > CHAPTER_FIRST_SECTION_SCREENS]
            assert far == [], (f"{page}: {far}")

    def test_only_the_first_chapter_is_open(self, browser, exports):
        """The decision stays open - a reader who has to open the
        verdict has been handed nothing at all - and everything else
        is one interaction away."""
        for page, url in exports.items():
            out = browser.measure(url, _DISTANCE, width=1440, height=900)
            opened = [c["id"] for c in out["chapters"] if c["open"]]
            assert opened == [out["chapters"][0]["id"]], (page, opened)
            assert out["chapters"][0]["id"] == "decide", out["chapters"][0]

    def test_every_folded_chapter_says_what_is_behind_it(self, browser, exports):
        """§3a.1 on this surface: the count before the click, and the
        chapter's own answer so the reader can decide not to click."""
        for page, url in exports.items():
            out = browser.measure(url, _DISTANCE, width=1440, height=900)
            for chapter in out["chapters"][1:]:
                assert chapter["control"], (page, chapter["id"], "no control")
                assert str(chapter["sections"]) in chapter["control"], (
                    page, chapter["id"], chapter["control"], chapter["sections"])
                assert chapter["answer"], (
                    f"{page}: chapter {chapter['id']} folds with no answer - "
                    f"a heading over nothing is worse than the scroll it saved")

    def test_the_rail_opens_the_fold_it_points_into(self, browser, exports):
        """The click model above prices a folded chapter at zero extra
        interactions. This is why: every rail entry, shut and clicked,
        opening the chapter that holds its target and leaving it drawn.
        A reveal that broke would make the walk a fiction."""
        for page, url in exports.items():
            broken = browser.measure(url, _RAIL_OPENS, width=1440, height=900)
            assert broken == [], (page, broken[:8])


def _walk(out):
    """The eight destinations, in clicks and in screens - published in
    the failure message so a bound that fires says what it cost."""
    rows = [f"{name}: {r['clicks']} click(s), {r['screensDown']} screens"
            + (" (behind a fold)" if r["behindFold"] else "")
            for name, r in out["reach"].items() if r]
    return "The walk: " + "; ".join(rows)


@pytest.fixture(scope="module")
def browser():
    with Browser(chrome) as opened:
        yield opened


@pytest.fixture(scope="module")
def exports(tmp_path_factory):
    import tools.bga_view as view

    made = {}
    for name, fixture in (("golden", GOLDEN), ("macro_micro", MACRO)):
        run = snapshot_copy(fixture, tmp_path_factory.mktemp(f"distance-{name}"))
        page = tmp_path_factory.mktemp(f"distance-page-{name}") / "report.html"
        view.export(str(run), str(page))
        made[name] = f"file://{page}"
    return made
