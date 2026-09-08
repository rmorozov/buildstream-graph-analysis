"""UX-638: Expand, then Expand again, and the reader is where they were.

Table focus hides every other section with `display: none`. Measured
served at 1440x900 on `macro_micro`, round 87:

```text
document height, before -> focused    42,936 -> 1,681 px
displacement after going back                  4,199 px  (4.7 screens)
button text after entering focus              "Expand"   (unchanged)
aria-pressed                                     null    (no state)
```

`test_the_fold_says_how_deep_it_goes.py` drives the same state and is
green on all of it: it clicks Expand **once**, goes back by the
breadcrumb, and compares a DOM dump. Scroll position is not in the DOM
and the shim has no layout, so this guard is a real browser and the
same button twice.
"""
import pathlib
import shutil
import sys
import threading
import time

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

FIXTURE = pages.FIXTURES["macro_micro"]

#: One reader, one table, two presses of the same button.
#:
#: The button chosen is the first one more than a screen below the fold,
#: because the defect is the clamp: a document that collapses to a
#: twenty-fifth of its height cannot hold an offset that large, and one
#: near the top would be restored by the clamp itself.
#: UX-795: the settle behind the last, flaky read below - two
#: animation frames agreeing on `(scrollY, top)`, bounded at 2s so a
#: page that never agrees still gets measured, and says so, rather
#: than a fixed wait that read the position mid-move on one runner.
_SETTLE_JS = """
  const settleReading = (get) => new Promise((resolve) => {
    const deadline = performance.now() + 2000;
    let prev = null;
    const frame = () => requestAnimationFrame(() => {
      const cur = get();
      const agree = prev !== null && cur[0] === prev[0] && cur[1] === prev[1];
      if (agree || performance.now() >= deadline) {
        resolve({ y: cur[0], top: cur[1], timedOut: !agree });
        return;
      }
      prev = cur;
      frame();
    });
    frame();
  });
"""

_TWO_PRESSES = """(async () => {
  const settle = () => new Promise((go) => setTimeout(go, 60));""" + _SETTLE_JS + """
  const height = () => document.documentElement.scrollHeight;
  // The rail's own "Expand all". Every `data-expand` on a fresh load is
  // inside a shut chapter and has no box at all, so without this the
  // walk below has 13 buttons and nothing to choose from.
  document.querySelector('nav.toc [data-all="false"]').click();
  await settle();
  const buttons = [...document.querySelectorAll("main [data-expand]")];
  const deep = buttons.find(
    (b) => b.getBoundingClientRect().top > window.innerHeight);
  if (!deep) return { found: false, buttons: buttons.length };

  // Where the reader put themselves: the button on screen, a third of
  // the way down, which is where it lands after reading to it.
  window.scrollTo(0, window.scrollY
    + deep.getBoundingClientRect().top - window.innerHeight / 3);
  await settle();
  const startY = window.scrollY;
  const startTop = Math.round(deep.getBoundingClientRect().top);
  const startHeight = height();
  const label = deep.textContent;
  const pressed = deep.getAttribute("aria-pressed");

  deep.click();
  await settle();
  const focused = document.querySelector("section[data-table-focus]");
  const focusedY = window.scrollY;
  const focusedHeight = height();
  const focusedTop = focused
    ? Math.round(focused.getBoundingClientRect().top) : null;
  const focusedLabel = deep.textContent;
  const focusedPressed = deep.getAttribute("aria-pressed");

  // The reader reads the table they opened - which is what focus is
  // for, and what makes this measurable. Chrome remembers the offset a
  // shrinking document clamped and puts it back when the document grows
  // again, so a probe that enters focus and leaves without scrolling
  // measures that restoration and passes on the unfixed page: 5,954 ->
  // 5,954 px against pristine `tablefocus.js`. One scroll inside focus
  // spends it - 5,954 -> 14,497 px, 9.5 screens.
  window.scrollTo(0, 400);
  await settle();
  const readAt = window.scrollY;

  deep.click();                       // the same button, a second time
  // UX-795: the read the CI flake was in - settled, not slept.
  const settled = await settleReading(
    () => [window.scrollY, Math.round(deep.getBoundingClientRect().top)]);
  return {
    found: true, buttons: buttons.length, label, pressed,
    startY, startTop, startHeight,
    focusedY, focusedHeight, focusedTop, focusedLabel, focusedPressed, readAt,
    stillFocused: Boolean(document.querySelector("section[data-table-focus]")),
    endY: settled.y, endHeight: height(),
    endTop: settled.top,
    endSettleTimedOut: settled.timedOut,
    endLabel: deep.textContent,
    endPressed: deep.getAttribute("aria-pressed"),
    viewport: window.innerHeight,
    // What "the top" is on this page: the sticky header's height, which
    // is what every anchor's `scroll-margin-top` already reads.
    head: parseFloat(getComputedStyle(document.body)
      .getPropertyValue("--head")) * parseFloat(
        getComputedStyle(document.documentElement).fontSize),
  };
})()"""


@pytest.fixture(scope="module")
def can_drive_a_page():
    if find_chrome() is None or shutil.which("node") is None:  # pragma: no cover
        pytest.skip(NO_BROWSER)


@pytest.fixture(scope="module")
def two_presses(tmp_path_factory, can_drive_a_page):
    """The page as `bga view` opens it - served, because that is where
    the displacement was measured and where the reader meets it."""
    from tools.bga_view import serve

    run = pages.snapshot_copy(FIXTURE, tmp_path_factory.mktemp("focus-scroll"))
    httpd, url = serve(str(run), port=0)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    time.sleep(0.3)
    try:
        with Browser(find_chrome()) as opened:
            yield opened.measure(url, _TWO_PRESSES, 1440, 900)
    finally:
        httpd.shutdown()


def _settle_note(two_presses):
    """UX-795: appended to a failing message, so a timed-out settle
    reads as one rather than as a fresh displacement."""
    if two_presses.get("endSettleTimedOut"):
        return " (the settle timed out)"
    return ""


@pytest.mark.skipif(find_chrome() is None, reason=NO_BROWSER)
class TestTheReaderComesBackToWhereTheyWere:
    def test_the_page_has_a_button_below_the_fold(self, two_presses):
        """Not vacuous: the whole defect is the clamp, and a button on
        the first screen has no offset to lose."""
        assert two_presses["found"], two_presses
        assert two_presses["startY"] > two_presses["viewport"], two_presses

    def test_focus_collapses_the_document(self, two_presses):
        """The mechanism, asserted so a page that stopped hiding
        sections cannot pass the clause below for free."""
        assert two_presses["focusedHeight"] * 4 < two_presses["startHeight"], (
            two_presses["startHeight"], two_presses["focusedHeight"])

    def test_the_reader_moved_inside_focus(self, two_presses):
        """The clause the two below stand on. Without it the browser's
        own restoration answers for the page - see the probe."""
        assert two_presses["readAt"] != two_presses["startY"], two_presses

    def test_going_back_restores_the_offset(self, two_presses):
        """Round 87 measured 4,199 px - 4.7 screens - of displacement;
        this probe measures 8,543 px. Within one viewport is the
        Acceptance Test's tolerance."""
        moved = abs(two_presses["endY"] - two_presses["startY"])
        assert moved <= two_presses["viewport"], (
            f"{moved}px of displacement, "
            f"{two_presses['startY']} -> {two_presses['endY']}"
            f"{_settle_note(two_presses)}")

    def test_the_table_is_back_on_the_same_screen(self, two_presses):
        """The offset is a number; this is the reading position. A page
        whose height is re-estimated on the way back can restore the
        first and lose the second."""
        moved = abs(two_presses["endTop"] - two_presses["startTop"])
        assert moved <= two_presses["viewport"], (
            f"the table moved {moved}px within the viewport, "
            f"{two_presses['startTop']} -> {two_presses['endTop']}"
            f"{_settle_note(two_presses)}")

    def test_entering_focus_scrolls_the_table_to_the_top(self, two_presses):
        """At the top, not merely on screen.

        Without the scroll the section lands wherever the collapse
        clamped the offset - measured at 405px from the top on this
        fixture, and it moves with where the reader was standing. The
        tolerance is the sticky header, which is where every anchor on
        this page already stops.
        """
        assert two_presses["focusedTop"] is not None, two_presses
        assert two_presses["head"] > 0, two_presses["head"]
        assert 0 <= two_presses["focusedTop"] <= two_presses["head"] + 16, (
            two_presses["focusedTop"], two_presses["head"])


@pytest.mark.skipif(find_chrome() is None, reason=NO_BROWSER)
class TestTheControlSaysWhichStateItIsIn:
    def test_the_second_press_collapses(self, two_presses):
        assert two_presses["stillFocused"] is False, two_presses

    def test_the_label_changes_when_focus_is_entered(self, two_presses):
        assert two_presses["label"].startswith("Expand"), two_presses["label"]
        assert two_presses["focusedLabel"].startswith("Collapse"), (
            two_presses["label"], two_presses["focusedLabel"])
        assert two_presses["endLabel"] == two_presses["label"], (
            two_presses["label"], two_presses["endLabel"])

    def test_the_button_says_it_is_pressed(self, two_presses):
        assert two_presses["pressed"] is None, two_presses["pressed"]
        assert two_presses["focusedPressed"] == "true", (
            two_presses["focusedPressed"])
        assert two_presses["endPressed"] is None, two_presses["endPressed"]


#: UX-795 Acceptance Test: `_TWO_PRESSES`, with a spacer reflow armed
#: (before either press) that lands after the second one and shrinks
#: away over the following 500ms - built from the fixture's own
#: source, not a copy, so the guard exercises the same `settleReading`
#: the fixture uses. Stepped by hand on every frame, not a CSS
#: transition: a transition's first frame reads back its *start*
#: value (the animation has not visibly begun), which coincided with
#: `settleReading`'s own first two frames and read as already
#: agreeing - a step means every frame differs from the last until the
#: spacer is actually gone. `overflow-anchor` is off so the browser
#: does not itself compensate the shift the spacer makes - the thing
#: under test. `insertAdjacentHTML`, not the node-building call:
#: `UX-264`'s shim census reads that as a second hand-built DOM, and
#: this is a real page in a real browser, with no shim in it at all.
_ARM_DELAYED_REFLOW = """
  document.documentElement.style.overflowAnchor = "none";
  let presses = 0;
  deep.addEventListener("click", () => {
    presses += 1;
    if (presses !== 2) return;
    requestAnimationFrame(() => {
      document.body.insertAdjacentHTML(
        "afterbegin", '<div id="ux795-spacer" style="height:3000px"></div>');
      const spacer = document.getElementById("ux795-spacer");
      const start = performance.now();
      const shrink = () => {
        const elapsed = performance.now() - start;
        const left = Math.max(0, 3000 * (1 - elapsed / 500));
        spacer.style.height = `${Math.round(left)}px`;
        if (elapsed < 500) requestAnimationFrame(shrink);
        else spacer.remove();
      };
      shrink();
    });
  });"""

_FIXED_SLEEP_READ = """await new Promise((resolve) => setTimeout(() => resolve({
    y: window.scrollY,
    top: Math.round(deep.getBoundingClientRect().top),
    timedOut: false,
  }), 60))"""


def _delayed_layout_script(use_settle):
    """The fixture's own script, with the reflow above armed and the
    final read either settled or the old fixed 60ms wait."""
    script = _TWO_PRESSES.replace(
        "if (!deep) return { found: false, buttons: buttons.length };",
        "if (!deep) return { found: false, buttons: buttons.length };"
        + _ARM_DELAYED_REFLOW)
    if not use_settle:
        script = script.replace(
            "await settleReading(\n"
            "    () => [window.scrollY, "
            "Math.round(deep.getBoundingClientRect().top)])",
            _FIXED_SLEEP_READ)
    return script


def _measure_delayed(tmp_path_factory, label, use_settle):
    """Serve `FIXTURE` fresh and measure `_delayed_layout_script`,
    exactly how `two_presses` serves and measures `_TWO_PRESSES`."""
    from tools.bga_view import serve

    run = pages.snapshot_copy(FIXTURE, tmp_path_factory.mktemp(label))
    httpd, url = serve(str(run), port=0)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    time.sleep(0.3)
    try:
        with Browser(find_chrome()) as opened:
            return opened.measure(
                url, _delayed_layout_script(use_settle), 1440, 900)
    finally:
        httpd.shutdown()


@pytest.mark.skipif(find_chrome() is None, reason=NO_BROWSER)
class TestTheSettleWaitsOutADelayedReflow:
    """UX-795: the Acceptance Test. A page whose layout is still
    delayed 500ms after the second press - the settled read waits it
    out; the fixed 60ms sleep it replaced does not."""

    def test_the_settled_read_passes(self, tmp_path_factory, can_drive_a_page):
        result = _measure_delayed(tmp_path_factory, "focus-scroll-settled", True)
        moved = abs(result["endTop"] - result["startTop"])
        assert result["endSettleTimedOut"] is False, result
        assert moved <= result["viewport"], (
            f"the table moved {moved}px within the viewport, "
            f"{result['startTop']} -> {result['endTop']}")

    def test_the_fixed_sleep_reds(self, tmp_path_factory, can_drive_a_page):
        result = _measure_delayed(tmp_path_factory, "focus-scroll-fixed", False)
        moved = abs(result["endTop"] - result["startTop"])
        assert moved > result["viewport"], (
            "the fixed 60ms sleep read the table settled - the "
            f"guard's delayed page did not exercise it: {result}")
