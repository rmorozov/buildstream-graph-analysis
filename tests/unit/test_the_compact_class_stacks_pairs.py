"""UX-1145 (styleguide §6e.10): at 390x844 a term stacks above its value,
a reader's chip is one line, and sticky chrome is under 12% of the viewport.
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

WIDTH, HEIGHT = 390, 844
#: One line of `--font-small`, px; a chip broken inside a name is two.
ONE_LINE = 30
#: Share of the viewport the pinned chrome may hold.
CHROME_SHARE = 0.12

_MEASURE = r"""
(async () => {
  const shown = (n) => { const r = n.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const narrow = [];
  let pairs = 0;
  for (const term of document.querySelectorAll("dl.pairs > dt")) {
    const value = term.nextElementSibling;
    if (!value || value.tagName !== "DD" || !shown(term) || !shown(value)) continue;
    pairs += 1;
    const t = term.getBoundingClientRect().width, v = value.getBoundingClientRect().width;
    if (v < t - 0.5) narrow.push([term.textContent.trim().slice(0, 30), Math.round(t), Math.round(v)]);
  }
  const chips = [...document.querySelectorAll(".reader-tag > .reader-chip")].filter(shown);
  const tall = chips.filter((c) => c.getBoundingClientRect().height > %(line)d)
    .map((c) => [c.textContent.trim(), Math.round(c.getBoundingClientRect().height)]);
  window.scrollTo(0, 3000);
  await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
  let pinned = 0;
  const pins = [];
  for (const n of document.querySelectorAll("body > *")) {
    const cs = getComputedStyle(n);
    if (cs.position !== "sticky" && cs.position !== "fixed") continue;
    const r = n.getBoundingClientRect();
    if (!r.height || r.bottom <= 0 || Math.abs(r.top - (parseFloat(cs.top) || 0)) > 1) continue;
    pinned += r.height;
    pins.push([n.tagName.toLowerCase() + (n.className ? "." + n.className : ""), Math.round(r.height)]);
  }
  return { pairs, narrow, chips: chips.length, tall, pinned, pins, scrolled: window.scrollY };
})()
""".replace("%(line)d", str(ONE_LINE))


def _two_plane(into):
    import tools.bga_view as view

    run = pages.two_plane_run(into, shape=("--layers", "8", "--width", "14"), name="both")
    page = pathlib.Path(into) / "both.html"
    view.export(str(run), str(page))
    return page.as_uri()


@pytest.fixture(scope="module", params=["golden", "macro_micro", "two_plane"])
def measured(request, tmp_path_factory):
    into = tmp_path_factory.mktemp(f"u1145-{request.param}")
    two = request.param == "two_plane"
    uri = _two_plane(into) if two else pages.export_uri(pages.FIXTURES[request.param], into)
    with Browser(chrome) as opened:
        result = opened.measure(uri, _MEASURE, width=WIDTH, height=HEIGHT)
    result["label"] = request.param
    return result


@needs_browser
class TestTheCompactClass:
    def test_the_page_has_pairs_and_scrolls(self, measured):
        assert measured["pairs"] > 0 and measured["scrolled"] > 0, measured

    def test_no_value_is_narrower_than_its_term(self, measured):
        assert not measured["narrow"], measured

    def test_a_reader_chip_is_one_line(self, measured):
        assert not measured["tall"], measured

    def test_sticky_chrome_is_under_its_share(self, measured):
        assert measured["pinned"] < CHROME_SHARE * HEIGHT, measured

    def test_each_reader_is_its_own_chip(self, measured):
        assert measured["chips"] > 0, measured
