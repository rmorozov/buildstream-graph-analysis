"""Round 165's walk: the rail's "you are here" glyph is drawn inside its link and inside the rail.

The glyph is a `::before`; its left edge is derived from the computed style
the browser lays it out with. Chromium on `macro_micro` at 1440x900 (rail
column, `overflow: auto`) and 390x844 (the drawer, opened as a reader does).

Styleguide §3h.
"""

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

needs_browser = pytest.mark.skipif(find_chrome() is None, reason=NO_BROWSER)

_MARK = r"""
(async () => {
  const frames = async (n) => { for (let i = 0; i < n; i += 1) await new Promise((d) => requestAnimationFrame(d)); };
  const toc = document.querySelector(".toc");
  if (toc.getAttribute("data-folded") === "true") { document.querySelector(".toc-title").click(); await frames(10); }
  const opened = Boolean(document.querySelector("[data-toc][data-current]"));
  document.getElementById("findings")?.scrollIntoView();
  await frames(12);
  const a = document.querySelector("[data-toc][data-current]");
  if (!a) return { opened, mark: null };
  const before = getComputedStyle(a, "::before"), link = a.getBoundingClientRect(), rail = toc.getBoundingClientRect();
  const pad = parseFloat(getComputedStyle(a).paddingLeft);
  const x = (before.left === "auto" ? link.left + pad : link.left + parseFloat(before.left)) + parseFloat(before.marginLeft);
  return { opened, mark: { content: before.content, x, link: link.left, rail: rail.left + toc.clientLeft,
                           text: link.left + pad, width: parseFloat(before.fontSize) * 0.6 } };
})()
"""


@pytest.fixture(scope="module")
def marks(tmp_path_factory):
    uri = pages.export_uri(pages.FIXTURES["macro_micro"], tmp_path_factory.mktemp("mark"), "macro_micro.html")
    with Browser(find_chrome()) as browser:
        return {width: browser.measure(uri, _MARK, width, height) for width, height in ((1440, 900), (390, 844))}


@needs_browser
@pytest.mark.parametrize("width", [1440, 390])
def test_the_mark_is_inside_its_link_and_the_rail(marks, width):
    got = marks[width]
    mark = got["mark"]
    assert mark and mark["content"] not in ("none", "normal"), got
    assert mark["x"] >= mark["link"] - 0.5 and mark["x"] >= mark["rail"] - 0.5, got
    assert mark["x"] + mark["width"] <= mark["text"] + 0.5, got


@needs_browser
def test_the_opened_drawer_marks_where_the_reader_is(marks):
    assert marks[390]["opened"], marks[390]
