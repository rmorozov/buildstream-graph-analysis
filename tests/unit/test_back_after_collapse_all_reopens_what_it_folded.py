"""UX-1219: Back after Collapse all reopens the sections it folded and lands where the reader was.

Measured before, on the 1,202-element page from y 3000: Collapse all, Back,
all 79 sections still collapsed; scrollY 333 at 1440 and 1110 at 390.
"""

import pytest

from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

#: HAND folded by hand first (written to the view query), so Back is told from re-opening everything.
_COLLAPSE = r"""
(async () => {
  const wait = (ms) => new Promise((done) => setTimeout(done, ms));
  const shut = () => [...document.querySelectorAll("[data-collapsed='true']")].map((s) => s.getAttribute("data-section")).sort();
  if (HAND) document.querySelector(`[data-collapse="${HAND}"]`).click();
  scrollTo(0, 3000);
  await wait(1000);
  const y = scrollY;
  const before = shut();
  document.querySelector("[data-all='true']").click();
  await wait(1500);
  const during = shut().length;
  await new Promise((done) => {
    addEventListener("popstate", () => setTimeout(done, 1500), { once: true });
    history.back();
  });
  return { y, before, during, after: shut(), back: scrollY };
})()
"""


@pytest.fixture(scope="module")
def big(tmp_path_factory):
    import tools.bga_view as view

    into = tmp_path_factory.mktemp("collapse-back")
    page = into / "page.html"
    view.export(str(pages.two_plane_run(into, ("--layers", "20", "--width", "60"))), str(page))
    return page.as_uri()


@pytest.fixture(scope="module")
def browser():
    if chrome is None:
        pytest.skip(NO_BROWSER)
    with Browser(chrome) as opened:
        yield opened


@needs_browser
@pytest.mark.parametrize("width,height", [(1440, 900), (390, 844)])
@pytest.mark.parametrize("hand", ["", "floors"])
def test_back_after_collapse_all_reopens_what_it_folded(browser, big, hand, width, height):
    got = browser.measure(big, _COLLAPSE.replace("HAND", f'"{hand}"'), width=width, height=height)
    assert got["before"] == ([hand] if hand else []), got
    assert got["during"] > 1, got
    assert got["after"] == got["before"], got
    assert abs(got["back"] - got["y"]) <= 1 and got["y"] == 3000, got
