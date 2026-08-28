"""UX-360: folding paid the distance, and nothing measured the volume.

Round 52's complaint was distance: twenty screens, the element table
6.8 screens down, the run identity 19.6. `UX-347` answered it with
chapters that fold, and the answer worked. Round 55 measured what the
answer cost:

```text
                    round 52      round 55 landed / opened
golden height      11,286 px       3,548 / 13,844
macro  height      18,148 px       5,588 / 24,689
golden words          3,448         5,034
macro  words          5,026         8,174
```

**The page a reader lands on is a third of what it was. The page in
total is a third bigger.** Distance was paid for with a fold, and the
volume behind the fold went unmeasured and grew — because nothing
measured it. `UX-347` bought a distance budget; "it is behind a
chapter" was a complete answer to any question about page weight.

The growth is not waste and this file does not claim it is. Round 53
and 54 built the shape channel, narrowed the table tools, moved the
schema's sentences behind a door and lifted two namespaces; round 56
landed the join's withheld fields, the provenance's rule and two new
shapes. Each was right. Together they are half again as much page, and
the round that adds the next thing needs a number to check itself
against.

**Two budgets, and they are a pair.** Landed distance is what `UX-347`
bought; total volume is what it cost. This file asserts both in one
guard so that a change trading one for the other has to say so — which
is the whole point, because the trade is exactly what happened and
nobody noticed for four rounds.

The bounds are set with headroom against the measurement below rather
than at it: a budget that reddens on the commit that lands it teaches
the next person to raise it rather than to think.
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

#: Measured on the finished page at 1440x900, round 56, exported from
#: the fixtures in place (`UX-359`):
#:
#: ```text
#:              landed    opened    words  controls  sections  svg
#: golden        3,501    14,493    5,279       409     6/43     8
#: macro_micro   5,564    28,213    9,879       659     6/58    18
#: ```
#:
#: The bounds carry roughly a fifth of headroom on the larger fixture.
#: Moving one is a filed reason, in the item that moves it, the way
#: `test_the_report_you_can_attach.py` records every size restatement.
#: Three of those happened in round 56 alone, which is what this file
#: exists to replace.
LANDED_HEIGHT_PX = 7_000
OPENED_HEIGHT_PX = 34_000
WORDS = 12_000
CONTROLS = 800

_LOOK = """
(() => {
  const state = () => {
    const main = document.querySelector("main") || document.body;
    return {
      height: document.documentElement.scrollHeight,
      // Words and controls are a fact about the **document**, not
      // about the fold: the chapters hide their sections with CSS, so
      // `textContent` reads them either way. That is why the volume
      // budget is one number rather than a landed and an opened one -
      // the volume is there from the first byte, and folding moved
      // only how far a reader scrolls past it.
      words: (main.textContent || "").trim().split(/\\s+/)
        .filter(Boolean).length,
      controls: document.querySelectorAll("button, input, select, a").length,
      sections: main.querySelectorAll("section[data-section]").length,
      shown: [...main.querySelectorAll("section[data-section]")]
        .filter((s) => s.getBoundingClientRect().height > 0).length,
    };
  };
  const landed = state();
  for (const box of document.querySelectorAll("section.chapter")) {
    box.setAttribute("data-open", "true");
  }
  return { landed, opened: state() };
})()
"""


@pytest.fixture(scope="module")
def browser():
    with Browser(chrome) as opened:
        yield opened


@pytest.fixture(scope="module")
def booted(tmp_path_factory):
    return pages.pages(tmp_path_factory, "volume")


@needs_browser
@pytest.mark.medium
@pytest.mark.parametrize("label", sorted(pages.FIXTURES))
class TestBothBudgetsAreBound:
    """One class, on purpose. `UX-347`'s distance budget lives in
    `test_the_chain_folds_and_clicks_are_counted.py` and is met; this
    holds it *beside* the volume it was paid for with, so a change that
    folds more to grow more reddens rather than passing two guards."""

    def test_the_landed_page_is_short(self, browser, booted, label):
        out = browser.measure(booted[label], _LOOK, 1440, 900)
        landed = out["landed"]
        assert landed["height"] <= LANDED_HEIGHT_PX, (
            f"{label}: the page a reader lands on is {landed['height']} px, "
            f"over the {LANDED_HEIGHT_PX} px budget")

    def test_the_whole_page_is_bounded_too(self, browser, booted, label):
        """The sibling `UX-347` did not have. A fold is not a licence:
        answering the distance budget says nothing about this one."""
        out = browser.measure(booted[label], _LOOK, 1440, 900)
        opened = out["opened"]
        assert opened["height"] <= OPENED_HEIGHT_PX, (
            f"{label}: the whole document is {opened['height']} px, over "
            f"the {OPENED_HEIGHT_PX} px budget - folding it further is not "
            f"an answer to this clause")
        assert opened["words"] <= WORDS, (
            f"{label}: {opened['words']} words, over the {WORDS} budget")
        assert opened["controls"] <= CONTROLS, (
            f"{label}: {opened['controls']} controls, over the {CONTROLS} "
            f"budget")

    def test_the_page_still_folds(self, browser, booted, label):
        """Without this, the landed clause is satisfied by a page that
        renders nothing, and the pair stops being a trade at all."""
        out = browser.measure(booted[label], _LOOK, 1440, 900)
        landed, opened = out["landed"], out["opened"]
        assert landed["shown"] < opened["shown"], (landed, opened)
        assert landed["height"] < opened["height"], (landed, opened)
        assert opened["sections"] >= 40, opened

    def test_the_budgets_are_not_slack(self, browser, booted, label):
        """A bound nothing can reach is not a bound. The larger fixture
        has to be within a factor of two of every budget, or the number
        was chosen to be safe rather than to be a limit."""
        out = browser.measure(booted[label], _LOOK, 1440, 900)
        if label != "macro_micro":
            pytest.skip("the bounds are set against the larger fixture")
        opened = out["opened"]
        for measured, bound, name in (
                (out["landed"]["height"], LANDED_HEIGHT_PX, "landed height"),
                (opened["height"], OPENED_HEIGHT_PX, "opened height"),
                (opened["words"], WORDS, "words"),
                (opened["controls"], CONTROLS, "controls")):
            assert measured * 2 > bound, (
                f"the {name} budget is {bound} and the page measures "
                f"{measured}; a bound with that much slack is a number "
                f"nobody will ever meet")


@needs_browser
@pytest.mark.medium
class TestTheBudgetIsWrittenWhereItIsRead:
    """§3e states the rule and this file holds it. The two have to agree
    on the numbers, or the guide is describing a different page - which
    is what `UX-352` was filed for one document over."""

    def test_the_style_guide_states_both_budgets(self):
        text = (REPO / "docs/design/styleguide.md").read_text(encoding="utf-8")
        section = text.split("## 3e.", 1)[1].split("\n## ", 1)[0]
        for number in (LANDED_HEIGHT_PX, OPENED_HEIGHT_PX, WORDS, CONTROLS):
            assert f"{number:,}" in section, (
                f"§3e does not state the {number:,} bound this file "
                f"asserts")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
