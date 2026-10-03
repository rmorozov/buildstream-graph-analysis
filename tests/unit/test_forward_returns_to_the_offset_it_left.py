"""UX-998 (round 169, walk seed 4): Forward after two Back steps puts the anchor where it was left.

Styleguide §4c: a traversal returns the reader to the place they read.
Walk seed 4 read `scrollY` 8218 vs 7952; measured on `macro_micro`, the
anchor holds to 0.4 px while `scrollY` moves 337 px (1440) and
260 px (390): a later entry opened content above it. No drift.
"""

import pytest

from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

#: Press rail link A, read 400 px into it, press B; Back, Back, Forward.
_DRIVE = r"""
(async () => {
  const wait = (ms) => new Promise((done) => setTimeout(done, ms));
  const pop = (go) => new Promise((done) => {
    addEventListener("popstate", () => setTimeout(done, 1200), { once: true });
    go();
  });
  await wait(800);
  const top = () => document.getElementById(A.slice(1)).getBoundingClientRect().top;
  const press = (href) => document.querySelector(`nav.toc a[href='${href}']`).click();
  press(A);
  await wait(900);
  scrollBy(0, 400);
  await wait(1500);
  const left = { y: scrollY, at: top() };
  press(B);
  await wait(900);
  await pop(() => history.back());
  await pop(() => history.back());
  await pop(() => history.forward());
  return { left, forward: { y: scrollY, at: top() } };
})()
"""


@pytest.fixture(scope="module")
def page(tmp_path_factory):
    return pages.export_uri(pages.FIXTURES["macro_micro"], tmp_path_factory.mktemp("forward"))


@pytest.fixture(scope="module")
def browser():
    if chrome is None:
        pytest.skip(NO_BROWSER)
    with Browser(chrome) as opened:
        yield opened


#: Measured fresh: scrollY moved 337 px (1440) and 260 px (390); the anchor held to 0.4 px.
CASES = {
    "1440": ("#latent_heavies", "#elements", 1440, 900),
    "390": ("#element_join_coverage", "#restructuring--edges", 390, 844),
}


@needs_browser
@pytest.mark.parametrize("case", sorted(CASES))
def test_forward_puts_the_anchor_back_at_its_offset(browser, page, case):
    a, b, width, height = CASES[case]
    drive = (
        _DRIVE.replace("A.slice", f'"{a}".slice')
        .replace("press(A)", f'press("{a}")')
        .replace("press(B)", f'press("{b}")')
    )
    got = browser.measure(page, drive, width=width, height=height)
    # The layout above the anchor changed, so a restored scrollY alone would land elsewhere.
    assert abs(got["forward"]["y"] - got["left"]["y"]) > 100, got
    assert abs(got["forward"]["at"] - got["left"]["at"]) <= 2, got
