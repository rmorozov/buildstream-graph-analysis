"""UX-397: the Perfetto handoff sat outside the pinned rail.

The user proposed pinning the handoff into the left pane. Measured on
the round-63 export, it was a header ornament:

```text
handoff button              y = 137 px   (header, scrolls away)
rail                        already position: sticky
page height                 9,316 px
```

The decision to open the trace is almost never made on the first
screen - it is made at a finding, four or five screens down, by which
time the button is 9,000 px behind the reader. `UX-368` put a query on
each finding for exactly that reason; the button that opens the trace
to run it did not follow.

**The whole group moves, not the button.** `UX-282`'s rule is that the
fallback is not below the button that fails and `UX-317`'s is that a
control's explanation lives with the control, so `#actions-group` -
button, fallback and download, one node - is what is relocated. Both
rules then hold by construction rather than by a second clause.

**At the head of the rail, not its foot.** The rail scrolls on its own
axis (`max-height: 100vh`), so the first version appended the group
after 66 entries and measured it 1,697 px below the viewport with the
document scrolled to its end - the header's defect moved one column
left. Found by driving it.

The other half of the filing - whether to adopt a table library - was
decided in round 65 as `UX-398`: no library, with the price in
styleguide §6b. Nothing here reopens it.
"""
import pathlib
import sys
import threading
import time

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tests import pages                                       # noqa: E402
from tests.browser import NO_BROWSER, Browser, find_chrome     # noqa: E402

#: Scroll to the end of the document and ask where the handoff is.
_AT_THE_BOTTOM = """(async () => {
  const settle = () => new Promise((go) => setTimeout(go, 300));
  const group = document.getElementById("actions-group");
  if (!group) return { found: false };
  window.scrollTo({ top: document.body.scrollHeight, behavior: "instant" });
  await settle();
  const box = group.getBoundingClientRect();
  const rail = document.querySelector("nav.toc");
  return {
    found: true,
    inRail: Boolean(group.closest("nav.toc")),
    inHeader: Boolean(group.closest("header")),
    top: box.top,
    height: window.innerHeight,
    inViewport: box.top >= 0 && box.top < window.innerHeight,
    scrolled: window.scrollY,
    pageHeight: document.body.scrollHeight,
    railPosition: getComputedStyle(rail).position,
    // `UX-282`: the fallback and the download are inside the same
    // node, so they travelled with the button rather than being left
    // under the heading it used to sit beneath.
    carries: ["actions", "actions-fallback", "actions-download"].filter(
      (id) => group.querySelector(`#${id}`)),
    // Above the chapters, so the rail's own scroll never hides it -
    // and beside the jump box, which is where the filing asked for
    // it. Measured as a position among the rail's children rather
    // than as "the next sibling is a chapter": the jump box sits
    // between them, and the first version of this clause said the
    // placement was wrong when it was the clause that was.
    railOrder: [...document.querySelector("nav.toc").children].map(
      (n) => n.className || n.tagName),
  };
})()"""

#: Served, where the button is not hidden: an export has no server
#: behind the trace, so `UX-194`'s rule keeps the control undrawn
#: there and only a served page can be asked whether it opens.
_SERVED = """(() => {
  const group = document.getElementById("actions-group");
  const button = document.getElementById("perfetto");
  return {
    inRail: Boolean(group?.closest("nav.toc")),
    offered: Boolean(button) && !document.getElementById("actions").hidden,
    label: button?.textContent ?? "",
  };
})()"""


@pytest.fixture(scope="module")
def at_the_bottom(tmp_path_factory):
    if find_chrome() is None:
        pytest.skip(NO_BROWSER)
    uri = pages.export_uri(pages.FIXTURES["macro_micro"],
                           tmp_path_factory.mktemp("handoff"))
    with Browser(find_chrome()) as browser:
        return browser.measure(uri, _AT_THE_BOTTOM, 1440, 900)


@pytest.fixture(scope="module")
def served(tmp_path_factory):
    """The same page with a server behind it, so the button is drawn."""
    if find_chrome() is None:
        pytest.skip(NO_BROWSER)
    from tools.bga_view import payloads, serve

    # `UX-358`'s two-plane snapshot, not `macro_micro`: the button is
    # offered only where a timeline could exist, and that is the one
    # committed capture whose trace carries both planes. Asking
    # `macro_micro` gives a page with the control correctly undrawn,
    # which measures `UX-194` rather than this item.
    into = tmp_path_factory.mktemp("handoff-served")
    run = pages.two_plane_snapshot(into)
    httpd, url = serve(str(run), port=0, documents=dict(payloads(str(run))))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    time.sleep(0.3)
    try:
        with Browser(find_chrome()) as browser:
            return browser.measure(url, _SERVED, 1440, 900)
    finally:
        httpd.shutdown()


@pytest.mark.skipif(find_chrome() is None, reason=NO_BROWSER)
class TestItIsReachableFromTheLastScreen:
    def test_the_handoff_is_in_the_rail(self, at_the_bottom):
        assert at_the_bottom["found"], "the handoff group is gone entirely"
        assert at_the_bottom["inRail"], "it is outside the pinned rail again"
        assert not at_the_bottom["inHeader"]
        assert at_the_bottom["railPosition"] == "sticky"

    def test_it_is_still_on_screen_at_the_bottom_of_the_report(
            self, at_the_bottom):
        """The Falsification, as written.

        Nine thousand pixels down, the control that opens the trace is
        where it was at the top.
        """
        assert at_the_bottom["pageHeight"] > 4 * at_the_bottom["height"], (
            "the fixture's page is no longer long enough for this to mean "
            "anything")
        assert at_the_bottom["scrolled"] > 0
        assert at_the_bottom["inViewport"], (
            f"the handoff is {at_the_bottom['top']:.0f} px from the top of a "
            f"{at_the_bottom['height']} px viewport with the document "
            f"scrolled to its end")

    def test_it_sits_above_the_chapters(self, at_the_bottom):
        """The rail scrolls on its own axis.

        Appended after 66 entries the group is reachable only after
        scrolling the rail, which is the header's defect moved one
        column left - measured at 1,697 px below the viewport before
        this.
        """
        order = at_the_bottom["railOrder"]
        assert "actions-group" in order, order
        first_chapter = next(
            (at for at, name in enumerate(order) if "toc-rail" in name), None)
        assert first_chapter is not None, order
        assert order.index("actions-group") < first_chapter, order

    def test_the_fallback_travelled_with_it(self, at_the_bottom):
        """`UX-282`: the fallback is not below the button that fails."""
        assert at_the_bottom["carries"] == [
            "actions", "actions-fallback", "actions-download"], (
            at_the_bottom["carries"])


@pytest.mark.skipif(find_chrome() is None, reason=NO_BROWSER)
class TestServedItStillOpensTheTrace:
    """An export draws no button - there is no server behind the trace,
    and `UX-194`'s rule is that an affordance whose precondition is
    absent is not drawn as a dead one. So "and still opens the trace"
    is asked of the page that has one."""

    def test_the_button_is_offered_and_in_the_rail(self, served):
        assert served["inRail"], served
        assert served["offered"], (
            "the served page no longer offers the handoff at all, so its "
            "position is not what this file is measuring")
        assert "Perfetto" in served["label"], served["label"]
