"""UX-639: the rail, while a table is focused, is not a live control.

Table focus hides every section with `display: none` and leaves the
rail drawn, styled and clickable over sections that have no box.
Measured served at 1440x900 on `macro_micro`, round 87:

```text
rail links whose target has a client rect
  before focus                 87
  while a table is focused      7
  after leaving focus          87
```

`nav.js` has no idea focus exists, and this item declines to teach it:
focus is entered in one place, so the rail's state is set there. What
the reader gets is `pointer-events: none` plus a visible dimming, so
the clause below hit-tests every rail link rather than reading the
attribute that should cause it.
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

#: The rail in three states, hit-tested rather than read.
#:
#: `elementFromPoint` is the browser's own answer to "what does a click
#: here reach". Reading `data-focus-inert` would pass on a marked rail
#: whose stylesheet rule was deleted, which is half of this fix.
_RAIL = """(async () => {
  const settle = () => new Promise((go) => setTimeout(go, 60));
  document.querySelector('nav.toc [data-all="false"]').click();
  await settle();
  const nav = document.querySelector("nav.toc");
  const laid = (n) => {
    const r = n?.getBoundingClientRect?.();
    return Boolean(r && r.width > 0 && r.height > 0);
  };
  const look = () => {
    const box = nav.getBoundingClientRect();
    const links = [...nav.querySelectorAll("[data-toc]")];
    let reachable = 0, onScreen = 0, targets = 0, outOfFocus = 0;
    const focus = document.querySelector("section[data-table-focus]");
    for (const link of links) {
      const target = document.getElementById(
        link.getAttribute("data-toc"));
      if (laid(target)) {
        targets += 1;
        if (!focus || !focus.contains(target)) outOfFocus += 1;
      }
      const r = link.getBoundingClientRect();
      const x = r.left + r.width / 2, y = r.top + r.height / 2;
      if (r.width <= 0 || r.height <= 0) continue;
      if (y < box.top || y > box.bottom) continue;
      if (y < 0 || y > window.innerHeight || x < 0 || x > window.innerWidth) {
        continue;
      }
      onScreen += 1;
      const hit = document.elementFromPoint(x, y);
      if (hit && (hit === link || link.contains(hit))) reachable += 1;
    }
    return { links: links.length, onScreen, reachable, targets, outOfFocus,
             inert: nav.getAttribute("data-focus-inert") };
  };

  const before = look();
  const buttons = [...document.querySelectorAll("main [data-expand]")];
  const deep = buttons.find(
    (b) => b.getBoundingClientRect().top > window.innerHeight);
  window.scrollTo(0, window.scrollY
    + deep.getBoundingClientRect().top - window.innerHeight / 3);
  await settle();
  deep.click();
  await settle();
  const during = look();
  deep.click();
  await settle();
  return { before, during, after: look() };
})()"""


@pytest.fixture(scope="module")
def can_drive_a_page():
    if find_chrome() is None or shutil.which("node") is None:  # pragma: no cover
        pytest.skip(NO_BROWSER)


@pytest.fixture(scope="module")
def rail(tmp_path_factory, can_drive_a_page):
    """Served, because that is where the count was measured."""
    from tools.bga_view import serve

    run = pages.snapshot_copy(FIXTURE, tmp_path_factory.mktemp("rail-inert"))
    httpd, url = serve(str(run), port=0)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    time.sleep(0.3)
    try:
        with Browser(find_chrome()) as opened:
            yield opened.measure(url, _RAIL, 1440, 900)
    finally:
        httpd.shutdown()


@pytest.mark.skipif(find_chrome() is None, reason=NO_BROWSER)
class TestTheRailIsLiveWhenThereIsNoFocus:
    def test_the_rail_is_worth_hit_testing(self, rail):
        """Not vacuous: a rail with no link on screen would make every
        clause below true for free."""
        assert rail["before"]["onScreen"] >= 10, rail["before"]

    def test_every_rail_link_on_screen_is_clickable(self, rail):
        assert rail["before"]["reachable"] == rail["before"]["onScreen"], (
            rail["before"])
        assert rail["before"]["inert"] is None, rail["before"]


@pytest.mark.skipif(find_chrome() is None, reason=NO_BROWSER)
class TestFocusMakesTheRailInert:
    def test_the_rail_carries_the_state(self, rail):
        assert rail["during"]["inert"] == "true", rail["during"]

    def test_no_rail_link_is_clickable(self, rail):
        """The reader's only way out is the breadcrumb, and the rail
        stops offering itself as one."""
        assert rail["during"]["reachable"] == 0, rail["during"]

    def test_the_links_are_still_drawn(self, rail):
        """Inert, not gone. Hiding the rail says the report is gone
        rather than that the breadcrumb is the way back.

        The count on screen is not held equal across the three states:
        `.toc-sub` opens the section being read and shuts the others, so
        the rail's own visible set moves with the reading position.
        """
        assert rail["during"]["links"] == rail["before"]["links"], (
            rail["before"], rail["during"])
        assert rail["during"]["onScreen"] >= 10, rail["during"]

    def test_no_rail_link_leads_out_of_the_focused_table(self, rail):
        """The measurement this item was filed on: 80 of 87 links point
        at a section with no box. The ones that still resolve are the
        ones inside focus, and there is no third kind."""
        assert rail["during"]["outOfFocus"] == 0, rail["during"]
        assert rail["during"]["targets"] < rail["before"]["targets"], (
            rail["before"], rail["during"])


@pytest.mark.skipif(find_chrome() is None, reason=NO_BROWSER)
class TestLeavingFocusGivesTheRailBack:
    def test_the_state_is_cleared(self, rail):
        assert rail["after"]["inert"] is None, rail["after"]

    def test_every_link_is_clickable_again(self, rail):
        assert rail["after"]["onScreen"] >= 10, rail["after"]
        assert rail["after"]["reachable"] == rail["after"]["onScreen"], (
            rail["after"])
        assert rail["after"]["targets"] == rail["before"]["targets"], (
            rail["before"], rail["after"])
