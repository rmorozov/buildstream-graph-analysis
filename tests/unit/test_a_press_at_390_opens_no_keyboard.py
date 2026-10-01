"""UX-1229: "+N more" under a coarse pointer focuses the Elements heading, not the box.

A focused text box raises a touch device's on-screen keyboard over the
rows the press filtered to. Headless Chromium draws no keyboard, so the
guard reads the focused element: at 390x844 with touch emulated, the
Elements heading; without it, the filter box (`UX-1214`). Read on the
two-plane page (`gen-synthetic --seed 1 --store --layers 8 --width 14`).
"""

import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

_PRESS = r"""
(async () => {
  const turn = () => new Promise((done) => setTimeout(done, 300));
  location.hash = "#element-toolchain-bst";
  await turn();
  const more = document.querySelector("#element-toolchain-bst [data-list] a[data-more]");
  if (!more) return null;
  more.click();
  await turn();
  const active = document.activeElement;
  return {
    coarse: matchMedia("(pointer: coarse)").matches,
    heading: active === document.querySelector("#elements .section-head :is(h2, h3)"),
    box: active?.matches("#elements input.table-filter") ?? false,
    value: document.querySelector("#elements input.table-filter")?.value,
  };
})()
"""


@pytest.fixture(scope="module")
def uri(tmp_path_factory):
    import tools.bga_view as view

    into = tmp_path_factory.mktemp("ux1229")
    page = into / "report.html"
    view.export(str(pages.two_plane_run(into, pages.REVIEW_SHAPE)), str(page))
    return page.as_uri()


@needs_browser
@pytest.mark.parametrize("coarse", [True, False], ids=["coarse", "fine"])
def test_a_coarse_press_focuses_the_heading_and_a_fine_one_the_box(uri, coarse):
    with Browser(chrome) as browser:
        seen = browser.measure(uri, _PRESS, width=390, height=844, coarse=coarse)
    assert seen, "toolchain.bst's card has no +N more"
    assert seen["coarse"] is coarse, seen
    assert seen["value"] == "depends_on:toolchain.bst", seen
    assert (seen["heading"], seen["box"]) == ((True, False) if coarse else (False, True)), seen
