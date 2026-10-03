"""UX-1221: Back after a link inside a card puts the card back at the offset it had.

Measured before, on the 1,202-element page: a card at -320, a dependency
link, Back: the card at 0 (1440 and 390); the pressed link 656 -> 976 at 390.

Styleguide §3c.
"""

import pytest

from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

#: Open CARD, scroll its top to OFFSET, press the card link LINK, then Back.
_CARD = r"""
(async () => {
  const wait = (ms) => new Promise((done) => setTimeout(done, ms));
  location.hash = CARD;
  await wait(1500);
  const card = document.getElementById(CARD);
  scrollBy(0, card.getBoundingClientRect().top - OFFSET);
  await wait(500);
  const before = card.getBoundingClientRect().top;
  card.querySelector(LINK).click();
  await wait(1500);
  const away = card.getBoundingClientRect().top;
  await new Promise((done) => {
    addEventListener("popstate", () => setTimeout(done, 1500), { once: true });
    history.back();
  });
  return { before, away, after: card.getBoundingClientRect().top };
})()
"""

CASES = {
    "dependency": ("element-layer12-mod030-bst", -320, "a[href^='#element-']"),
    "more": ("element-toolchain-bst", -516, "a[href^='#elements~']"),
}


@pytest.fixture(scope="module")
def big(tmp_path_factory):
    import tools.bga_view as view

    into = tmp_path_factory.mktemp("card-back")
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
@pytest.mark.parametrize("case", sorted(CASES))
def test_back_after_a_card_link_restores_the_card_offset(browser, big, case, width, height):
    card, offset, link = CASES[case]
    drive = _CARD.replace("CARD", f'"{card}"').replace("OFFSET", str(offset)).replace("LINK", f'"{link}"')
    got = browser.measure(big, drive, width=width, height=height)
    assert got["before"] < -200, got
    assert abs(got["away"] - got["before"]) > 1, got
    assert abs(got["after"] - got["before"]) <= 1, got
