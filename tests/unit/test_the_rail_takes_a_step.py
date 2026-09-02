"""UX-393: nothing moved to the next section, or back to the top.

The user asked whether there is an easy way to reach the next section
when it is off-screen. Counted on the round-63 export:

```text
page height                     9,316 px   (7.4 screens at 1,260 px)
rail entries                          77
controls matching next/prev/top        1
```

The one control was an ordinary link to `#next_steps` inside a
sentence. A reader working through the findings in order had to move
the pointer to the rail, find the entry after the one they were on
among seventy-seven, and click it - for every section.

**In the rail, not a banner.** `UX-347`'s distance budget measures
scroll distance to *content*, and a 60px chrome bar makes every
measurement on every screen worse. The rail is already sticky and
already beside the reading column, so three buttons at its head cost
that column nothing - which the volume and distance guards assert
independently.

**The order is the rail's**, which is `UX-235`'s declared order. And
"here" is `UX-399`'s `data-current` mark, so the two controls cannot
disagree about where the reader is: one writes the mark, the other
reads it.

**The mark is asynchronous, and that is this item's one real trap.**
`IntersectionObserver` fires on a later task and the scroll it watches
is smooth, so a stepper that read the mark on every press moved once
and then stood still - measured in Chrome, six presses of Next and six
times `decision`. The cursor below is what fixes it, and
`test_two_presses_move_two_sections` is what would catch it coming
back.
"""
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tests import pages                                       # noqa: E402
from tests.browser import NO_BROWSER, Browser, find_chrome     # noqa: E402

#: Walking the whole order and back, in one load. The hash rather than
#: the mark: a rail link sets it synchronously, and the mark is what
#: this item had to stop depending on.
_WALK = """(() => {
  const bar = document.querySelector("nav.toc .toc-steps");
  if (!bar) return { found: false };
  const press = (name, times = 1) => {
    const button = bar.querySelector(`[data-step="${name}"]`);
    const seen = [];
    for (let i = 0; i < times; i++) { button.click(); seen.push(location.hash); }
    return seen;
  };
  const order = [...document.querySelectorAll("nav.toc [data-toc]")]
    .map((a) => "#" + a.getAttribute("data-toc"));
  const forward = press("next", 6);
  const back = press("previous", 2);
  press("next", order.length + 20);
  const stopped = location.hash;
  return { found: true, order, forward, back, stopped,
           labels: [...bar.querySelectorAll("button")].map(
             (b) => b.getAttribute("data-step")) };
})()"""

#: The scroll half, which needs the browser's own asynchrony: a smooth
#: scroll and a `scroll` event both land on a later task.
_TOP = """(async () => {
  const settle = () => new Promise((go) => setTimeout(go, 350));
  const bar = document.querySelector("nav.toc .toc-steps");
  const top = bar.querySelector('[data-step="top"]');
  const atRest = top.hidden;
  window.scrollTo({ top: 4000, behavior: "instant" });
  await settle();
  const whenDown = top.hidden;
  top.click();
  // Smooth, so poll rather than guess a duration: a fixed wait either
  // flakes on a slow machine or costs every run the slowest one.
  for (let i = 0; i < 40 && window.scrollY > 0; i++) await settle();
  return { atRest, whenDown, scrollAfter: window.scrollY };
})()"""

#: `]` and `[`, and the rule that they are ignored while typing.
_KEYS = """(() => {
  const send = (key, target) => (target ?? document).dispatchEvent(
    new KeyboardEvent("keydown", { key, bubbles: true }));
  send("]"); send("]");
  const afterTwo = location.hash;
  send("[");
  const afterBack = location.hash;
  const box = document.getElementById("jump");
  box.focus();
  send("]", box);
  return { afterTwo, afterBack, whileTyping: location.hash };
})()"""


@pytest.fixture(scope="module")
def uri(tmp_path_factory):
    if find_chrome() is None:
        pytest.skip(NO_BROWSER)
    return pages.export_uri(pages.FIXTURES["macro_micro"],
                            tmp_path_factory.mktemp("stepper"))


@pytest.fixture(scope="module")
def walked(uri):
    with Browser(find_chrome()) as browser:
        return browser.measure(uri, _WALK, 1440, 900)


@pytest.mark.skipif(find_chrome() is None, reason=NO_BROWSER)
class TestTheStepFollowsTheDeclaredOrder:
    def test_the_rail_has_the_three_controls(self, walked):
        assert walked["found"], "the rail has no step controls"
        assert walked["labels"] == ["top", "previous", "next"], walked["labels"]

    def test_next_walks_the_order_the_page_declares(self, walked):
        """Not the DOM's accident - `UX-235`'s order, via the rail."""
        assert walked["order"][:7] == ["#decision", "#readers", "#evidence",
                                       "#overview", "#findings", "#headline",
                                       "#next_steps"], walked["order"][:7]
        assert walked["forward"] == walked["order"][1:7], walked["forward"]

    def test_two_presses_move_two_sections(self, walked):
        """The trap this item is really about.

        Reading `data-current` on every press means reading a mark an
        `IntersectionObserver` has not written yet, so the second press
        repeats the first. Six presses, six distinct sections.
        """
        assert len(set(walked["forward"])) == 6, walked["forward"]

    def test_previous_walks_back(self, walked):
        assert walked["back"] == ["#headline", "#findings"], walked["back"]

    def test_next_past_the_end_stops(self, walked):
        """Clamped, not wrapped.

        A reader who has reached the end of a report has not asked to
        start it again - and the Falsification asks for exactly this.
        """
        assert walked["stopped"] == walked["order"][-1], (
            walked["stopped"], walked["order"][-1])


@pytest.mark.skipif(find_chrome() is None, reason=NO_BROWSER)
class TestBackToTheTop:
    def test_it_appears_only_once_there_is_a_top_to_go_back_to(self, uri):
        """A control that does nothing is the dead affordance `UX-194`
        ruled out, so it is hidden above the first screen and shown
        below it."""
        with Browser(find_chrome()) as browser:
            seen = browser.measure(uri, _TOP, 1440, 900)
        assert seen["atRest"] is True, "it is offered before there is a top"
        assert seen["whenDown"] is False, "it stays hidden past the fold"
        assert seen["scrollAfter"] == 0, seen["scrollAfter"]


#: `UX-535`: every rail entry's label names one destination.
#:
#: Read off the rendered rail rather than off the schema: the entries
#: come from three builders - the chapter tables, `viewEntries` for a
#: section's presets and `subsections` for its folds - and a guard that
#: read any one of them could not see a collision between two.
_LABELS = """
(() => {
  const rail = document.querySelector("nav.rail") || document.querySelector("nav");
  const byLabel = {};
  for (const a of rail.querySelectorAll("a")) {
    (byLabel[a.textContent.trim()] ??= []).push(a.getAttribute("href"));
  }
  return { entries: Object.values(byLabel).reduce((n, h) => n + h.length, 0),
           collisions: Object.entries(byLabel)
             .filter(([, hrefs]) => new Set(hrefs).size > 1) };
})()
"""


@pytest.fixture(scope="module")
def labels(tmp_path_factory):
    """The rail's labels on both committed fixtures, one browser."""
    if find_chrome() is None:
        pytest.skip(NO_BROWSER)
    booted = pages.pages(tmp_path_factory, "rail-labels")
    with Browser(find_chrome()) as browser:
        return {label: browser.measure(uri, _LABELS, 1440, 900)
                for label, uri in booted.items()}


@pytest.mark.skipif(find_chrome() is None, reason=NO_BROWSER)
@pytest.mark.parametrize("label", sorted(pages.FIXTURES))
class TestARailEntryNamesOneDestination:
    """`UX-535`. Measured before the fix - one label, two hrefs, on both
    fixtures:

    ```text
    Latent heavies   #latent_heavies
    Latent heavies   #elements~v.elements=Latent%20heavies
    ```

    A section and an `elements` preset of the same name. `UX-289`'s
    design keeps both drawings; what a reader cannot do is tell the two
    rail entries apart, and the preset's option already carries the
    count that would.
    """

    def test_no_label_points_two_ways(self, labels, label):
        out = labels[label]
        assert out["collisions"] == [], (
            f"{label}: {len(out['collisions'])} rail label(s) on more than "
            f"one destination, of {out['entries']}: {out['collisions']}")

    def test_the_rail_was_actually_read(self, labels, label):
        """So an empty rail cannot pass the clause above."""
        assert labels[label]["entries"] > 20, labels[label]


@pytest.mark.skipif(find_chrome() is None, reason=NO_BROWSER)
class TestTheKeyboardReaches(object):
    """`UX-223` established the page has a keyboard reader."""

    def test_the_bracket_keys_step(self, uri):
        with Browser(find_chrome()) as browser:
            seen = browser.measure(uri, _KEYS, 1440, 900)
        # Two presses of `]` from the top: `#readers`, then `#evidence`.
        assert seen["afterTwo"] == "#evidence", seen
        assert seen["afterBack"] == "#readers", seen

    def test_they_are_ignored_while_typing(self, uri):
        """`]` is a character somebody may be typing into the palette,
        and losing it there is worse than the shortcut is worth."""
        with Browser(find_chrome()) as browser:
            seen = browser.measure(uri, _KEYS, 1440, 900)
        assert seen["whileTyping"] == seen["afterBack"], seen
