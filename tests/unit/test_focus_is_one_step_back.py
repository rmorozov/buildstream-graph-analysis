"""UX-1222: Focus pushes an entry, so Back returns the unfocused page at the card Focus was pressed on.

Measured before, on the 1,202-element page: a card landed at y 28,301,
Focus, Back: no entry pushed, y 0 (1440 and 390).
"""

import pytest

from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

#: The card's viewport top, not scrollY: the folds' estimates move the document under it (UX-1171).
_FOCUS = r"""
(async () => {
  const wait = (ms) => new Promise((done) => setTimeout(done, ms));
  const id = "element-layer12-mod030-bst";
  location.hash = id;
  await wait(1500);
  const card = document.getElementById(id);
  const top = card.getBoundingClientRect().top;
  const length = history.length;
  card.querySelector("[data-focus-element]").click();
  await wait(1500);
  const focused = document.querySelector("[data-focus]")?.getAttribute("data-focus");
  const pushed = history.length - length;
  await new Promise((done) => {
    addEventListener("popstate", () => setTimeout(done, 1500), { once: true });
    history.back();
  });
  return { y: scrollY, top, focused, pushed, after: card.getBoundingClientRect().top,
           cleared: !document.querySelector("[data-focus]"), hash: location.hash };
})()
"""


@pytest.fixture(scope="module")
def big(tmp_path_factory):
    import tools.bga_view as view

    into = tmp_path_factory.mktemp("focus-back")
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
def test_focus_is_one_step_back(browser, big, width, height):
    got = browser.measure(big, _FOCUS, width=width, height=height)
    assert got["focused"] == "layer12/mod030.bst" and got["pushed"] == 1, got
    assert got["cleared"] and got["hash"] == "#element-layer12-mod030-bst", got
    assert got["y"] > 20000 and abs(got["after"] - got["top"]) <= 1, got
