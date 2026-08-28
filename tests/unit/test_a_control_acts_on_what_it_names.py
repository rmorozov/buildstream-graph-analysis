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


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
