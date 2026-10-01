"""UX-1251: in a decomposition each label sits on its own line under its segment's start.

No two `.draw-tick` boxes of a decomposition intersect, at 390 and 1440, for
a 2%, a 9.8% and an 88% part, and on the golden and macro_micro pages.
"""

import pathlib
import sys
import threading
import time

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

WIDTHS = (390, 1440)

_HITS = r"""
const hits = (axis) => {
  const boxes = [...axis.querySelectorAll(".draw-tick")]
    .filter((t) => t.getClientRects().length).map((t) => [t.textContent, t.getBoundingClientRect()]);
  const out = [];
  boxes.forEach(([a, r], i) => boxes.slice(i + 1).forEach(([b, s]) => {
    if (r.left < s.right - 0.5 && s.left < r.right - 0.5 && r.top < s.bottom - 0.5 && s.top < r.bottom - 0.5)
      out.push(`${a} / ${b}`);
  }));
  return { hits: out, ticks: boxes.length };
};
"""

_CONSTRUCTED = (
    """
(async () => {
  const mod = await import("./drawings.js");"""
    + _HITS
    + """
  const out = [];
  for (const parts of [
    [["chain", 9.8], ["gap", 90.2]],
    [["chain", 2], ["gap", 10], ["rest", 88]],
    [["a", 5], ["b", 7], ["c", 88]],
  ]) {
    const wrap = mod.decomposition(
      parts.map(([key, value]) => ({ key, value, label: `Segment ${key} named long`})),
      { grade: "exhibit", total: 100, format: (v) => `${v} min`, doc: document });
    document.body.append(wrap);
    out.push(hits(wrap.querySelector(".draw-axis")));
  }
  return out;
})()
"""
)

_PAGE = (
    "(() => {"
    + _HITS
    + """
  return [...document.querySelectorAll(".decomposition .draw-axis")].map(hits);
})()
"""
)


@pytest.fixture(scope="module")
def browser():
    with Browser(chrome) as opened:
        yield opened


@pytest.fixture(scope="module")
def served_url(tmp_path_factory):
    from tools.bga_view import serve

    run = pages.snapshot_copy(pages.FIXTURES["macro_micro"], tmp_path_factory.mktemp("u1251"))
    httpd, url = serve(str(run), port=0)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    time.sleep(0.3)
    try:
        yield url
    finally:
        httpd.shutdown()
        httpd.server_close()


@needs_browser
class TestASegmentLabelNeverOverprintsItsNeighbour:
    @pytest.mark.parametrize("width", WIDTHS)
    def test_constructed_parts_never_intersect(self, browser, served_url, width):
        out = browser.measure(served_url, _CONSTRUCTED, width, 900)
        assert [o["ticks"] for o in out] == [2, 3, 3], out
        assert [o["hits"] for o in out] == [[], [], []], out

    @pytest.mark.parametrize("label", ["golden", "macro_micro"])
    @pytest.mark.parametrize("width", WIDTHS)
    def test_a_page_s_floors_never_intersect(self, browser, tmp_path_factory, label, width):
        uri = pages.export_uri(pages.FIXTURES[label], tmp_path_factory.mktemp(f"u1251-{label}-{width}"))
        out = browser.measure(uri, _PAGE, width, 900)
        assert out, "no decomposition on the page"
        assert [o["hits"] for o in out] == [[] for _ in out], out
