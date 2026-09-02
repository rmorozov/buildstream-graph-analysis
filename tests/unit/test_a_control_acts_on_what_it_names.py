"""UX-355: a control acts on the scope its label names, and says it fired.

Round 55 pressed every control class the page offers, on the page an
export produces, in the state a reader lands in. Ten of twelve did what
their label said. Two did not.

**"Expand all" expanded nothing.** The rail's pair was built on
`collapsible().all()`, which walks *sections*. `UX-347` moved the
document's fold to the *chapter*, and sections are default-open, so
from a fresh load `all(false)` set open what was already open:

```text
golden                                     height   chapters   sections
                                                       open    collapsed
landed                                      3,548        1/7            0
after clicking "Expand all"                 3,548        1/7            0
after opening each chapter by hand         13,844        7/7            0
```

Not a dead listener - `UX-194` forbids those and a guard checks for
them. The handler ran, and changed nothing. That is the same defect
with a passing guard, which is why this file measures the *effect* of a
press rather than the presence of a handler.

**"Copy 11 rows" acknowledged nothing.** Of four copy controls,
`copy-step`, `copy-sql` and `copy-view` change their own label on
success. `copy-rows` - 13 of them on `golden`, 23 on `macro_micro`, the
most numerous of the four - wrote to the clipboard and left no trace on
the page. A clipboard write is invisible by construction, so the
control has to say so itself.

The two clauses are one rule (styleguide §4c) and this file holds both:
a control's label names its scope, and every action is acknowledged
where the finger is.
"""
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

import pages    # noqa: E402
from browser import NO_BROWSER, Browser, find_chrome    # noqa: E402

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

#: Press the rail's pair and report the document's state at each step,
#: against opening every chapter by hand as the reference.
_FOLDS = """
(() => {
  // `UX-399`: this file's claim is that two routes reach the *same
  // document*, so it measures the fully laid-out one. With
  // `content-visibility: auto` on, `scrollHeight` is an estimate that
  // depends on which sections have been rendered, and the two routes
  // reported heights 264 px apart while opening exactly the same
  // sections. The clause that catches a real regression is the same
  // either way; what the estimate adds is a difference that is not one.
  """ + pages.FULL_LAYOUT_JS + """
  const state = () => ({
    height: document.documentElement.scrollHeight,
    open: document.querySelectorAll(
      'section.chapter[data-open="true"]').length,
    chapters: document.querySelectorAll("section.chapter").length,
    shownSections: [...document.querySelectorAll("section[data-section]")]
      .filter((s) => s.getBoundingClientRect().height > 0).length,
    sections: document.querySelectorAll("section[data-section]").length,
    collapsed: document.querySelectorAll(
      'section[data-section][data-collapsed="true"]').length,
    decisionOpen: document.querySelector('section.chapter[data-chapter="decide"]')
      ?.getAttribute("data-open") !== "false",
  });
  const rail = (text) => [...document.querySelectorAll("button")]
    .find((b) => new RegExp("^" + text, "i").test((b.textContent || "").trim()));

  const landed = state();
  rail("Expand all").click();
  const expanded = state();

  // The reference: what a reader gets by opening each chapter herself.
  rail("Collapse all").click();
  const collapsed = state();
  for (const b of document.querySelectorAll("button.chapter-open")) {
    if (b.getAttribute("aria-expanded") !== "true") b.click();
  }
  for (const b of document.querySelectorAll("button.collapse")) {
    if (b.getAttribute("aria-expanded") !== "true") b.click();
  }
  const byHand = state();

  rail("Collapse all").click();
  rail("Expand all").click();
  const roundTrip = state();

  return { landed, expanded, collapsed, byHand, roundTrip };
})()
"""

#: Press one rendered instance of every copy control and report whether
#: its own text moved. The *class* is the population: a fifth copy
#: control added later is covered without an edit here.
_COPIES = """
(() => {
  for (const box of document.querySelectorAll("section.chapter")) {
    box.setAttribute("data-open", "true");
  }
  const shown = (el) => el.getBoundingClientRect().height > 0;
  const classes = new Set();
  for (const button of document.querySelectorAll("button")) {
    for (const name of button.classList) {
      if (name.startsWith("copy")) classes.add(name);
    }
  }
  const out = [];
  for (const name of [...classes].sort()) {
    const all = [...document.querySelectorAll(`button.${name}`)];
    const button = all.find(shown);
    if (!button) { out.push({ name, total: all.length, verdict: "none rendered" });
                   continue; }
    const before = button.textContent;
    try { button.click(); } catch (error) {
      out.push({ name, total: all.length, before,
                 verdict: "THREW " + String(error).slice(0, 60) });
      continue;
    }
    out.push({ name, total: all.length, before, after: button.textContent,
               verdict: button.textContent === before ? "silent" : "says so" });
  }
  return out;
})()
"""


@pytest.fixture(scope="module")
def browser():
    with Browser(chrome) as opened:
        yield opened


@pytest.fixture(scope="module")
def booted(tmp_path_factory):
    return pages.pages(tmp_path_factory, "control")


@needs_browser
@pytest.mark.medium
@pytest.mark.parametrize("label", sorted(pages.FIXTURES))
class TestExpandAllExpandsWhatThePageFolds:
    def test_the_page_is_folded_when_the_reader_lands(
            self, browser, booted, label):
        """The precondition. If the page stopped folding, every clause
        below would pass while measuring nothing - `expanded` would
        equal `landed` because both are the whole document."""
        out = browser.measure(booted[label], _FOLDS, 1440, 900)
        landed = out["landed"]
        assert landed["chapters"] >= 6, landed
        assert landed["open"] == 1, landed
        assert landed["shownSections"] < landed["sections"], landed

    def test_one_press_opens_the_document(self, browser, booted, label):
        """The acceptance's first clause, against the reference a reader
        would reach by hand."""
        out = browser.measure(booted[label], _FOLDS, 1440, 900)
        expanded, by_hand = out["expanded"], out["byHand"]
        assert expanded["height"] == by_hand["height"], (
            f"{label}: \"Expand all\" reaches {expanded['height']}px; "
            f"opening every chapter by hand reaches {by_hand['height']}px")
        assert expanded["open"] == expanded["chapters"], expanded
        assert expanded["shownSections"] == expanded["sections"], expanded

    def test_the_pair_is_symmetric(self, browser, booted, label):
        """The rule, stated as the property it is: whatever "Collapse
        all" shuts, "Expand all" opens. Without this a fix that only
        opened the chapters would pass the clause above and still leave
        a reader who pressed Collapse first with a folded page."""
        out = browser.measure(booted[label], _FOLDS, 1440, 900)
        assert out["roundTrip"] == out["expanded"], (
            f"{label}: collapse-then-expand does not return to the "
            f"expanded page\n  expanded:  {out['expanded']}\n"
            f"  roundtrip: {out['roundTrip']}")

    def test_collapse_all_shuts_both_layers(self, browser, booted, label):
        """The other half of the symmetry, measured rather than assumed:
        the old "Collapse all" shut the sections of the one open chapter
        and left the other six folds exactly as they were."""
        out = browser.measure(booted[label], _FOLDS, 1440, 900)
        collapsed = out["collapsed"]
        assert collapsed["collapsed"] == collapsed["sections"], collapsed
        assert collapsed["open"] == 1, (
            f"{label}: {collapsed['open']} chapters are still open after "
            f"\"Collapse all\"")
        assert collapsed["height"] < out["expanded"]["height"], collapsed

    def test_the_decision_chapter_never_shuts(self, browser, booted, label):
        """`UX-347`'s rule, which this item must not trade away: the
        decision has no toggle, so a "Collapse all" that shut it would
        be a fold with no way back."""
        out = browser.measure(booted[label], _FOLDS, 1440, 900)
        for step, state in out.items():
            assert state["decisionOpen"], (label, step, state)


@needs_browser
@pytest.mark.medium
@pytest.mark.parametrize("label", sorted(pages.FIXTURES))
class TestEveryCopyControlSaysItFired:
    def test_the_population_is_the_class(self, browser, booted, label):
        """Four classes when this was written. Asserted so that a page
        that lost them - or a probe that stopped finding them - reddens
        here rather than passing an empty walk."""
        out = browser.measure(booted[label], _COPIES, 1440, 900)
        assert len(out) >= 4, out
        assert {"copy-rows", "copy-view"} <= {row["name"] for row in out}, out

    def test_no_copy_control_is_silent(self, browser, booted, label):
        """The acceptance's second clause. `copy-rows` was the one that
        said nothing, and it is the one on every table."""
        out = browser.measure(booted[label], _COPIES, 1440, 900)
        silent = [row for row in out if row["verdict"] == "silent"]
        assert silent == [], (
            f"{label}: copy control(s) that write to the clipboard and "
            f"leave no trace on the page: {silent}")

    def test_every_class_has_a_rendered_instance_to_press(
            self, browser, booted, label):
        """Otherwise the clause above is satisfied by a page where no
        copy control renders at all."""
        out = browser.measure(booted[label], _COPIES, 1440, 900)
        pressed = [row for row in out if row["verdict"] != "none rendered"]
        assert len(pressed) >= 3, out


@needs_browser
@pytest.mark.medium
class TestTheAcknowledgementGoesBackToWhatItSays:
    """`copy-rows`' label carries a live count - "Copy 11 rows" - which
    the filter, the threshold and the bound all move. So the restore has
    to recompute it rather than put back a string captured at build
    time, and this is the clause that says so."""

    _RESTORE = """
    (() => {
      for (const box of document.querySelectorAll("section.chapter")) {
        box.setAttribute("data-open", "true");
      }
      const button = [...document.querySelectorAll("button.copy-rows")]
        .find((b) => b.getBoundingClientRect().height > 0);
      if (!button) return { skipped: "no rendered copy-rows" };
      const before = button.textContent;
      button.click();
      const during = button.textContent;
      return new Promise((resolve) => setTimeout(() => resolve({
        before, during, after: button.textContent }), 1600));
    })()
    """

    @pytest.mark.parametrize("label", sorted(pages.FIXTURES))
    def test_the_label_comes_back(self, browser, booted, label):
        out = browser.measure(booted[label], self._RESTORE, 1440, 900)
        assert "skipped" not in out, out
        assert out["during"] != out["before"], out
        assert out["after"] == out["before"], (
            f"{label}: the label did not come back to the count it "
            f"carries: {out}")
        assert "row" in out["before"], out


#: `UX-534`: press the deepest Focus on the page, as a reader who
#: scrolled to it would.
#:
#: **Read the focus outcome before touching any other control.** A mark
#: click re-runs `refresh()`, which removes and rebuilds every transient
#: node - a handle taken before it measures zero, and the first version
#: of this drive reported "not in the viewport" against a working fix.
_FOCUS = """
(() => {
  for (const box of document.querySelectorAll("section.chapter")) {
    box.setAttribute("data-open", "true");
  }
  const deepest = [...document.querySelectorAll("button.focus-this")]
    .map((b) => ({ b, y: b.getBoundingClientRect().top + window.scrollY }))
    .sort((a, c) => c.y - a.y)[0];
  if (!deepest) return { skipped: "no focus-this button" };
  // `UX-228`'s baseline, and it has to be taken here: a snapshot after
  // any click is a snapshot `refresh()` has already stamped, which is
  // what made the first version of this clause pass a page whose
  // buttons were not born carrying their state.
  const report = document.getElementById("report");
  const pristine = report.innerHTML;
  deepest.b.scrollIntoView();          // the reader got here by scrolling
  const seen = (node) => {
    if (!node) return false;
    const box = node.getBoundingClientRect();
    return box.top < window.innerHeight && box.bottom > 0;
  };
  const before = { buttonY: Math.round(deepest.y),
                   scrollY: Math.round(window.scrollY),
                   pressed: deepest.b.getAttribute("aria-pressed") };
  deepest.b.click();
  const panel = document.querySelector("[data-role=focus-investigation]");
  const after = { scrollY: Math.round(window.scrollY),
                  pressed: deepest.b.getAttribute("aria-pressed"),
                  panelExists: !!panel,
                  panelInViewport: seen(panel),
                  barInViewport: seen(
                    document.querySelector("[data-role=focus-bar]")) };
  const mark = deepest.b.parentElement.querySelector("button.mark-this");
  const markBefore = mark.getAttribute("aria-pressed");
  mark.click();
  const markAfter = mark.getAttribute("aria-pressed");
  mark.click();                        // unmark
  deepest.b.click();                   // and unfocus
  return { before, after,
           mark: [markBefore, markAfter],
           restored: report.innerHTML === pristine };
})()
"""


@pytest.fixture(scope="module")
def pressed(browser, booted):
    """`{label: the drive's reading}` - one press per fixture, once."""
    return {label: browser.measure(booted[label], _FOCUS, 1440, 900)
            for label in sorted(pages.FIXTURES)}


@needs_browser
@pytest.mark.medium
@pytest.mark.parametrize("label", sorted(pages.FIXTURES))
class TestFocusAnswersWhereTheHandIs:
    """`UX-534`, and it is the rule the two classes above hold: the
    action is acknowledged where the finger is. Measured before the fix
    - the press moved the reader nowhere and marked nothing.

    ```text
    fixture        button y   scrollY after   panel seen   aria-pressed
    golden           23,934          23,577        false     absent
    macro_micro      34,305          33,967        false     absent
    ```

    After: scrollY 132 on both, the panel and the bar in the viewport,
    and `#report` 231,502 -> 235,403 -> 231,502 characters across a
    focus and an unfocus.
    """

    def test_the_investigation_is_in_the_viewport(self, pressed, label):
        """The item's Acceptance Test. The panel existed either way; what
        was missing is the reader ever arriving at it."""
        out = pressed[label]
        assert "skipped" not in out, out
        assert out["after"]["panelExists"], out
        assert out["before"]["buttonY"] > 10_000, (
            f"{label}: the button is at {out['before']['buttonY']} px - too "
            f"near the top for this to measure a journey")
        assert out["after"]["panelInViewport"], (
            f"{label}: Focus pressed at {out['before']['buttonY']} px left "
            f"the investigation out of the viewport, at scrollY "
            f"{out['after']['scrollY']}")

    def test_the_bar_that_clears_it_comes_too(self, pressed, label):
        """The way back is beside the answer, not where the click was."""
        assert pressed[label]["after"]["barInViewport"], (
            label, pressed[label]["after"])

    def test_the_focus_button_says_it_is_pressed(self, pressed, label):
        """`aria-pressed`, both because a toggle owes a screen reader one
        and because it is what a reader's eye checks."""
        out = pressed[label]
        assert out["before"]["pressed"] == "false", (label, out)
        assert out["after"]["pressed"] == "true", (label, out)

    def test_the_mark_controls_say_it_too(self, pressed, label):
        """The three beside it, which carried no state at all."""
        assert pressed[label]["mark"] == ["false", "true"], (
            label, pressed[label]["mark"])

    def test_unfocusing_still_restores_the_document(self, pressed, label):
        """`UX-228`'s invariant, which a state attribute is exactly the
        way to break: the button is born carrying `aria-pressed="false"`
        so that an unfocus writes back what was already there.

        `test_focus_is_an_investigation.py` holds the same claim over a
        synthetic root that has **no focus buttons in it**, so it cannot
        see this attribute either way. This one boots the page."""
        assert pressed[label]["restored"], (
            f"{label}: focus then unfocus left #report changed")


#: `UX-536`: three of the four controls the census found saying less
#: than they do, on the page an export produces.
#:
#: The Markdown box is driven from a **known** start - every box
#: unchecked - rather than from whatever the shared Chromium's
#: `localStorage` carries: `Browser(chrome)` reuses one profile across
#: fixtures, so a previous drive's preference is a state this would
#: otherwise inherit and read as a pass.
_SAYS = r"""
(() => {
  for (const box of document.querySelectorAll("section.chapter")) {
    box.setAttribute("data-open", "true");
  }
  const collapse = [...document.querySelectorAll("button.collapse")];
  const boxes = [...document.querySelectorAll("input.copy-markdown")];
  const promise = (box) => box.closest(".table-tools")
    ?.querySelector(".copy-rows")?.title ?? "";
  const named = (b) => (b.getAttribute("aria-label") || "").trim()
    || (b.textContent || "").replace(/[\u25b8\u25be\s]/g, "");
  const state = {
    collapse: collapse.length,
    unnamed: collapse.filter((b) => !named(b)).length,
    notButton: collapse.filter((b) => b.getAttribute("type") !== "button")
      .length,
    boxes: boxes.length,
    keys: (document.querySelector(".toc-steps [data-step-keys]") || {})
      .textContent ?? null,
    stepLabels: [...document.querySelectorAll(".toc-steps [data-step]")]
      .map((b) => b.getAttribute("aria-label")),
  };
  for (const box of boxes) box.checked = false;
  boxes[0].checked = true;
  boxes[0].dispatchEvent(new Event("change", { bubbles: true }));
  return { ...state,
           checkedAfterOneClick: boxes.filter((b) => b.checked).length,
           promisingMarkdown: boxes.filter(
             (b) => /as Markdown/.test(promise(b))).length };
})()
"""


@pytest.fixture(scope="module")
def census(browser, booted):
    """One drive per fixture, once."""
    return {label: browser.measure(booted[label], _SAYS, 1440, 900)
            for label in sorted(pages.FIXTURES)}


@needs_browser
@pytest.mark.medium
@pytest.mark.parametrize("label", sorted(pages.FIXTURES))
class TestTheControlsSayWhatTheyDo:
    """`UX-536`, three of its four. Measured before the fix:

    ```text
    fixture       collapse   unnamed   type!=button   boxes   1 click changes
    golden              46        46             46      14         1 of 14
    macro_micro         66        66             66      29         1 of 29
    accelerators   announced nowhere: no [ ] hint, and the labels read
                   "Previous section" / "Next section"
    ```
    """

    def test_no_collapse_button_is_unnamed(self, census, label):
        out = census[label]
        assert out["collapse"] > 20, out          # the walk found them
        assert out["unnamed"] == 0, (
            f"{label}: {out['unnamed']} of {out['collapse']} collapse "
            f"buttons have no accessible name")

    def test_no_collapse_button_is_a_submit(self, census, label):
        """`type` defaults to `submit`, which is a different control."""
        assert census[label]["notButton"] == 0, (
            f"{label}: {census[label]['notButton']} of "
            f"{census[label]['collapse']} default to type=submit")

    def test_one_preference_is_one_state(self, census, label):
        """One click on any Markdown box moves all of them - and moves
        what the copy buttons *promise*, which is the half a reader
        sees."""
        out = census[label]
        assert out["boxes"] > 10, out
        assert out["checkedAfterOneClick"] == out["boxes"], (
            f"{label}: one click checked {out['checkedAfterOneClick']} of "
            f"{out['boxes']} boxes")
        assert out["promisingMarkdown"] == out["boxes"], (
            f"{label}: {out['promisingMarkdown']} of {out['boxes']} copy "
            f"controls promise Markdown after the box was ticked")

    def test_the_accelerators_are_announced_where_they_act(
            self, census, label):
        """`[` and `]` step the rail and were written down nowhere."""
        out = census[label]
        assert out["keys"] and "[" in out["keys"] and "]" in out["keys"], (
            f"{label}: the step controls carry no accelerator hint: "
            f"{out['keys']!r}")
        labels = " ".join(filter(None, out["stepLabels"]))
        assert "[" in labels and "]" in labels, (
            f"{label}: neither step control names its key: "
            f"{out['stepLabels']}")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
