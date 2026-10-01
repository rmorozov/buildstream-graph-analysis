"""UX-1220: at 390 the rail's jump box keeps the place read for Back, as the rail's links do (UX-1208).

Measured before, on the 1,202-element page: read at 6000, climb, open the
rail, jump to layer12/mod030 or Focus it from the box, Back: y 0.
"""

import pytest

from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

#: Read at 6000, climb in 400 px steps, open the rail, take the box's MODE result, Back, Forward.
_JUMP = r"""
(async () => {
  const wait = (ms) => new Promise((done) => setTimeout(done, ms));
  const rest = () => new Promise((done) => {
    addEventListener("scrollend", () => setTimeout(done, 100), { once: true });
    setTimeout(done, 1000);
  });
  const traverse = (go) => new Promise((done) => {
    addEventListener("popstate", () => setTimeout(done, 1500), { once: true });
    go();
  });
  // An entry of the page's own, so a Back that keeps no place stays on the page to be read.
  history.pushState(null, "", location.href);
  const length = history.length;
  scrollTo(0, 6000);
  await rest();
  const y = Math.round(scrollY);
  while (scrollY > 0) { scrollBy(0, -400); await rest(); }
  document.querySelector(".toc-title").click();
  await wait(300);
  const box = document.getElementById("jump");
  box.value = MODE === "binary" ? "lognormal-00" : "layer12/mod030";
  box.dispatchEvent(new Event("input"));
  await wait(200);
  const pick = { jump: '[data-jump="layer12/mod030.bst"]', focus: '[data-action="focus"]', binary: "[data-jump^='lognormal-']" };
  document.querySelector(`.jump-hits ${pick[MODE]}`).click();
  await wait(1500);
  const after = Math.round(scrollY);
  const pushed = history.length - length;
  await traverse(() => history.back());
  const back = Math.round(scrollY);
  const rail = document.querySelector(".toc").getAttribute("data-folded");
  await traverse(() => history.forward());
  const seen = (node) => {
    const r = node?.getBoundingClientRect();
    return Boolean(r) && r.bottom > 0 && r.top < innerHeight;
  };
  return { y, after, pushed, hash: location.hash, back, rail, forward: Math.round(scrollY),
           focus: document.getElementById("report").getAttribute("data-focus"),
           card: seen(document.getElementById("element-layer12-mod030-bst")),
           bar: seen(document.querySelector("[data-role=focus-bar]")) };
})()
"""


@pytest.fixture(scope="module")
def big(tmp_path_factory):
    import tools.bga_view as view

    into = tmp_path_factory.mktemp("jump-back")
    page = into / "page.html"
    view.export(str(pages.two_plane_run(into, ("--layers", "20", "--width", "60"))), str(page))
    return page.as_uri()


@pytest.fixture(scope="module")
def big_binaries(tmp_path_factory):
    import tools.bga_view as view

    into = tmp_path_factory.mktemp("jump-back-binaries")
    page = into / "page.html"
    shape = ("--workload", "binaries", "--layers", "20", "--width", "60")
    view.export(str(pages.two_plane_run(into, shape)), str(page))
    return page.as_uri()


@pytest.fixture(scope="module")
def browser():
    if chrome is None:
        pytest.skip(NO_BROWSER)
    with Browser(chrome) as opened:
        yield opened


@needs_browser
@pytest.mark.parametrize("mode", ["jump", "focus", "binary"])
def test_the_narrow_rail_jump_box_keeps_the_place_read(browser, big, big_binaries, mode):
    got = browser.measure(
        big_binaries if mode == "binary" else big, _JUMP.replace("MODE", f'"{mode}"'), width=390, height=844
    )
    assert got["y"] == 6000 and abs(got["back"] - got["y"]) <= 1, got
    assert got["rail"] == "true", got
    if mode == "binary":
        assert got["pushed"] == 1 and got["hash"].startswith("#by_binary"), got
    elif mode == "jump":
        assert got["card"], got
    else:
        assert got["focus"] == "layer12/mod030.bst" and got["bar"], got
        assert abs(got["forward"] - got["after"]) <= 1, got
