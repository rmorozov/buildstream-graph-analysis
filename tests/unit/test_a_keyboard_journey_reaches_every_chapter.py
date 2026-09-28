"""UX-1016 (styleguide §6e.8): one focus ring, and a keyboard alone
reaches every chapter.

Measured on `main` before this: `button:focus-visible` was the only
rule in `style.css` (`:root`'s dark palette aside) - a link, an
`<input>`, a `<select>` and a `<summary>` fell back to the browser's own
outline, invisible against this page's dark surface in the one browser
sampled. `Enter` on a fold control and `Escape` out of table focus were
never exercised by a guard: nothing here drove a real `Tab` before this
file, because `Runtime.evaluate` cannot move focus the way a keyboard
does - `cdp.mjs --journey` (added by this item) drives CDP's `Input`
domain instead, the only channel a script has onto that.

Two things `cdp.mjs` needed that a plain `Runtime.evaluate` measurement
never did: `Emulation.setFocusEmulationEnabled` (a target this process
never clicked into has no real window focus, so neither `Tab` nor
`Enter` do anything), and `Enter`'s `text`/`unmodifiedText` fields (CDP's
`rawKeyDown` - the type used for a shortcut like Ctrl+C - does not run
a button's native "Enter activates the focused control", measured empty
without them on this Chromium).
"""
import pathlib
import re
import sys
import threading
import time

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

import pages
from browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

VIEWER = REPO / "bga" / "viewer"


# --------------------------------------------------------------------------
# 1. The rule, read once and asserted against reverting to `button` alone.
# --------------------------------------------------------------------------

class TestOneFocusVisibleRuleCoversEveryFocusableClass:
    """The Acceptance Test's own mutation: "scope the ring back to
    `button`, and the link stop reds" - held here on the source, and
    again on real elements below (`TestEveryStopShowsTheSameRing`)."""

    def _rule(self):
        css = (VIEWER / "style.css").read_text(encoding="utf-8")
        match = re.search(
            r"([^\n{]*:focus-visible[^{]*)\{([^}]*outline[^}]*)\}", css)
        assert match, "no :focus-visible rule with an outline in style.css"
        return match.group(1), match.group(2)

    def test_the_selector_names_every_focusable_class(self):
        selector, _ = self._rule()
        classes = {part.strip().split(":focus-visible")[0]
                   for part in selector.split(",")}
        assert classes == {"a", "button", "input", "select", "summary",
                           "[tabindex]"}, classes

    def test_only_one_rule_sets_the_ring(self):
        """Two rules that could disagree is the defect a single
        selector list exists to rule out."""
        css = (VIEWER / "style.css").read_text(encoding="utf-8")
        assert len(re.findall(r":focus-visible[^{]*\{[^}]*outline",
                              css)) == 1, css


# --------------------------------------------------------------------------
# 2. The chapter order this file's journey is measured against - read off
#    the booted rail, never restated (`test_the_order_the_page_has`'s
#    rule). `chapters.js`'s own `CHAPTERS` table names every chapter the
#    *schema* could produce; a comparison-less run (this fixture) never
#    builds "compare" at all, so the rail - what actually rendered - is
#    the order, not the table.
# --------------------------------------------------------------------------

_RAIL_ORDER = r"""
(() => [...document.querySelectorAll('li[data-chapter]')]
   .map((li) => li.getAttribute('data-chapter')))()
"""

MACRO = REPO / "tests" / "fixtures" / "macro_micro" / "run"

_READ_ACTIVE = r"""
(() => {
  const a = document.activeElement;
  if (!a) return null;
  const cs = getComputedStyle(a);
  const id = a.getAttribute("data-toc-chapter");
  const box = id && document.querySelector(`section.chapter[data-chapter="${id}"]`);
  return { tag: a.tagName, chapterOpen: id,
           expanded: box ? box.getAttribute("data-open") : null,
           outlineStyle: cs.outlineStyle, outlineWidth: cs.outlineWidth,
           visible: a.matches(":focus-visible") };
})()
"""


#: Every walk starts at the document's top: `scrollspy`'s landing
#: `scrollIntoView` moves Chrome's sequential-focus starting point to the
#: marked link, so an unanchored first `Tab` skips what sits above it.
_START_AT_THE_TOP = [{"wait": 100}, {"read": (
    '(() => { const b = document.body; b.setAttribute("tabindex", "-1"); '
    'b.focus({preventScroll: true}); b.removeAttribute("tabindex"); '
    'return null; })()')}]


#: A generous, named cap on how many `Tab`s from the top it takes to
#: pass a skip link and the rail's own top-level links and reach the
#: last chapter's fold control - not the smallest that passes, since the
#: property under test is "reachable at all", not a tuned offset.
TAB_CAP = 40


@pytest.fixture(scope="module")
def journey(tmp_path_factory):
    """`Tab` from a fresh load, up to `TAB_CAP` times - the rail's own
    mirrored fold control reaches every chapter before the document's
    own body does (`nav.js`), which is still "reaches every chapter's
    fold" and not a second control this item invented."""
    into = tmp_path_factory.mktemp("u1016")
    uri = pages.export_uri(MACRO, into)
    with Browser(chrome) as browser:
        ids = browser.measure(uri, _RAIL_ORDER, 1440, 900)
        steps = list(_START_AT_THE_TOP)
        for _ in range(TAB_CAP):
            steps.append({"key": "Tab"})
            steps.append({"read": _READ_ACTIVE})
        return ids, browser.journey(uri, steps, 1440, 900)[1:]


@needs_browser
class TestTabFromTheTopReachesEveryChapter:
    def test_the_stops_are_every_chapters_rail_row_in_order(self, journey):
        ids, trace = journey
        stops = [row["chapterOpen"] for row in trace if row["chapterOpen"]]
        assert stops == ids, (stops, ids)

    def test_every_fold_stop_shows_the_same_computed_ring(self, journey):
        _, trace = journey
        folds = [row for row in trace if row["chapterOpen"]]
        assert folds, trace
        for row in folds:
            assert row["visible"], row
            assert row["outlineStyle"] == "solid", row
            assert row["outlineWidth"] == "2px", row


# --------------------------------------------------------------------------
# 2b. `UX-1054`: no `_START_AT_THE_TOP` reset - a fresh load's own first
#    `Tab`, unassisted. `scrollspy`'s landing mark used to move Chrome's
#    focus starting point to the rail; this is what a real reader's
#    first keypress does without a body-focus workaround.
# --------------------------------------------------------------------------

#: The first laid-out focusable in document order, read before any key is
#: pressed - independent of what `activeElement` happens to be (`BODY`,
#: on a fresh load, tells a reader nothing about where `Tab` will land).
_FIRST_FOCUSABLE = r"""
(() => {
  const laid = (el) => {
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  };
  const first = [...document.querySelectorAll(
      'a[href], button, input, select, textarea, summary, [tabindex]')]
    .filter((el) => !el.disabled && el.getAttribute('tabindex') !== '-1'
                    && laid(el))[0];
  if (!first) return null;
  return { tag: first.tagName, cls: first.className,
           dataToc: first.getAttribute('data-toc') };
})()
"""

_READ_ACTIVE_STOP = r"""
(() => {
  const a = document.activeElement;
  if (!a) return null;
  return { tag: a.tagName, cls: a.className,
           dataToc: a.getAttribute("data-toc"),
           chapterOpen: a.getAttribute("data-toc-chapter") };
})()
"""


@pytest.fixture(scope="module")
def fresh_journey(tmp_path_factory):
    """No `_START_AT_THE_TOP`: whatever a fresh load's own first `Tab`
    reaches, unassisted."""
    into = tmp_path_factory.mktemp("u1054")
    uri = pages.export_uri(MACRO, into)
    with Browser(chrome) as browser:
        ids = browser.measure(uri, _RAIL_ORDER, 1440, 900)
        steps = [{"wait": 100}, {"read": _FIRST_FOCUSABLE}]
        for _ in range(TAB_CAP):
            steps.append({"key": "Tab"})
            steps.append({"read": _READ_ACTIVE_STOP})
        trace = browser.journey(uri, steps, 1440, 900)
        return ids, trace[0], trace[1:]


@needs_browser
class TestTheFirstTabFromAFreshLoadStartsAtTheTop:
    def test_the_first_tab_lands_on_the_first_focusable_in_document_order(
            self, fresh_journey):
        ids, first_focusable, trace = fresh_journey
        assert ids, "no chapters on the rail - nothing to walk"
        first_stop = {k: trace[0][k] for k in ("tag", "cls", "dataToc")}
        assert first_stop == first_focusable, (
            f"the first Tab landed on {first_stop}, not the first "
            f"focusable in document order, {first_focusable}")

    def test_a_forward_walk_reaches_every_chapter_decide_first(
            self, fresh_journey):
        ids, _, trace = fresh_journey
        stops = [row["chapterOpen"] for row in trace if row["chapterOpen"]]
        assert stops == ids, (stops, ids)
        assert stops[0] == "decide", stops


@needs_browser
class TestEnterOpensTheFoldEnterReached:
    def test_enter_on_a_reached_fold_opens_its_chapter(self, journey,
                                                       tmp_path_factory):
        """`journey`'s own trace already located every fold's `Tab`
        count; this presses one `Enter` where the first one lands, in a
        fresh journey over exactly that many `Tab`s plus one."""
        ids, trace = journey
        at = next(i for i, row in enumerate(trace)
                  if row["chapterOpen"] and row["expanded"] == "false")
        into = tmp_path_factory.mktemp("u1016-enter")
        uri = pages.export_uri(MACRO, into)
        with Browser(chrome) as browser:
            steps = list(_START_AT_THE_TOP)
            for _ in range(at + 1):
                steps.append({"key": "Tab"})
            steps.append({"read": _READ_ACTIVE})
            steps.append({"key": "Enter"})
            steps.append({"read": _READ_ACTIVE})
            before, after = browser.journey(uri, steps, 1440, 900)[1:]
        assert len(ids) > 1, ids
        assert before["chapterOpen"] == trace[at]["chapterOpen"], before
        assert before["expanded"] == "false", before
        assert after["expanded"] == "true", after


# --------------------------------------------------------------------------
# 3. Every focusable *class* the rule names shows the ring for real -
#    the mutation's own clause, driven rather than argued from the CSS.
# --------------------------------------------------------------------------

@needs_browser
class TestEveryFocusableClassShowsTheRingForReal:
    """`a`, `button`, `summary` are found inside the first ~40 stops on
    the landed page; `input` and `select` need the decision panel's own
    controls, found inside the first 130 (measured on `macro_micro`,
    booted). A generous, named cap rather than the smallest that
    passes: the property under test is "somewhere in reach", not a
    tuned offset that the next section added would silently move past."""

    CAP = 150

    def test_a_button_input_select_and_summary_all_ring(self, tmp_path_factory):
        into = tmp_path_factory.mktemp("u1016-ring")
        uri = pages.export_uri(MACRO, into)
        steps = list(_START_AT_THE_TOP)
        for _ in range(self.CAP):
            steps.append({"key": "Tab"})
            steps.append({"read": _READ_ACTIVE})
        with Browser(chrome) as browser:
            trace = browser.journey(uri, steps, 1440, 900)[1:]
        by_tag = {}
        for row in trace:
            if row and row["visible"]:
                by_tag.setdefault(row["tag"], row)
        missing = {"A", "BUTTON", "INPUT", "SELECT", "SUMMARY"} - set(by_tag)
        assert not missing, (missing, sorted(by_tag))
        for tag, row in by_tag.items():
            assert row["outlineStyle"] == "solid", (tag, row)
            assert row["outlineWidth"] == "2px", (tag, row)


# --------------------------------------------------------------------------
# 4. Escape leaves table focus, and gives the keyboard back to the
#    control that opened it - `tablefocus.js`'s own state, not a proxy.
# --------------------------------------------------------------------------

#: `expand-table` controls need `served()` (`structured.js`) - not a
#: property of the keyboard journey, so opening every chapter here is a
#: script `click()` on each `button.chapter-open`, once, to reach the
#: precondition; `TestEnterOpensTheFoldEnterReached` is what already
#: holds "opens it with Enter" as its own claim.
_OPEN_EVERY_CHAPTER = (
    '(() => { for (const b of document.querySelectorAll('
    '"button.chapter-open")) b.click(); return null; })()')

_READ_EXPAND = r"""
(() => {
  const a = document.activeElement;
  return { tag: a && a.tagName,
           expand: a && a.getAttribute && a.getAttribute("data-expand"),
           tf: document.getElementById("report")
                 .getAttribute("data-table-focused") };
})()
"""


@pytest.fixture(scope="module")
def served_url(tmp_path_factory):
    from tools.bga_view import serve

    run = pages.snapshot_copy(MACRO, tmp_path_factory.mktemp("u1016-serve"))
    httpd, url = serve(str(run), port=0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.3)
    try:
        yield url
    finally:
        httpd.shutdown()
        httpd.server_close()


@needs_browser
class TestEscapeLeavesTableFocusAndReturnsFocus:
    #: Generous and named: every chapter open, how many `Tab`s from the
    #: top it takes to reach *some* `data-expand` control - measured at
    #: 272 on `macro_micro`, served, every chapter open.
    CAP = 400

    def test_escape_leaves_and_returns_focus_to_the_opener(self, served_url):
        with Browser(chrome) as browser:
            steps = [{"read": _OPEN_EVERY_CHAPTER}, *_START_AT_THE_TOP]
            for _ in range(self.CAP):
                steps.append({"key": "Tab"})
                steps.append({"read": _READ_EXPAND})
            trace = browser.journey(served_url, steps, 1440, 900)[2:]
        at = next((i for i, row in enumerate(trace) if row["expand"]), None)
        assert at is not None, "no data-expand control reached in " \
            f"{self.CAP} tabs with every chapter open"
        opener_path = trace[at]["expand"]

        with Browser(chrome) as browser:
            steps = [{"read": _OPEN_EVERY_CHAPTER}, *_START_AT_THE_TOP]
            for _ in range(at + 1):
                steps.append({"key": "Tab"})
            steps.append({"read": _READ_EXPAND})
            steps.append({"key": "Enter"})
            steps.append({"read": _READ_EXPAND})
            steps.append({"key": "Escape"})
            steps.append({"read": _READ_EXPAND})
            before, entered, after = browser.journey(
                served_url, steps, 1440, 900)[2:]
        assert before["expand"] == opener_path, before
        assert entered["tf"] == opener_path, entered
        assert after["tf"] is None, after
        assert after["expand"] == opener_path, (
            "Escape did not return focus to the control that opened "
            f"table focus: {after}")
