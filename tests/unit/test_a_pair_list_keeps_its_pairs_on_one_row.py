"""UX-1137: in every `dl.pairs`, each term sits on its value's row, left of it.

`UX-1021`'s block door is the `dl`'s first child; in a two-column grid it
took the first cell and pushed every pair one cell over, so a term sat
beside the previous value and its own value started the next row.
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

_MEASURE = r"""
(() => {
  for (const box of document.querySelectorAll("section.chapter")) {
    box.setAttribute("data-open", "true");
  }
  for (const fold of document.querySelectorAll("details")) fold.open = true;
  const split = [];
  let pairs = 0, doors = 0;
  for (const list of document.querySelectorAll("dl.pairs")) {
    if (list.querySelector(":scope > button.describe")) doors += 1;
    for (const term of list.querySelectorAll(":scope > dt")) {
      const value = term.nextElementSibling;
      if (!value || value.tagName !== "DD") continue;
      const t = term.getBoundingClientRect(), v = value.getBoundingClientRect();
      if (!t.height || !v.height) continue;
      pairs += 1;
      if (Math.abs(t.top - v.top) > 1 || t.left >= v.left) {
        split.push(term.getAttribute("data-key") || term.textContent.trim());
      }
    }
  }
  return { pairs, doors, split };
})()
"""


@pytest.fixture(scope="module", params=["golden", "macro_micro"])
def measured(request, tmp_path_factory):
    uri = pages.export_uri(pages.FIXTURES[request.param], tmp_path_factory.mktemp(f"u1137-{request.param}"))
    with Browser(chrome) as opened:
        result = opened.measure(uri, _MEASURE)
    result["label"] = request.param
    return result


@needs_browser
class TestPairsStayOnTheirRow:
    def test_the_page_has_pair_lists_with_doors(self, measured):
        assert measured["pairs"] > 0 and measured["doors"] > 0, measured

    def test_every_term_sits_beside_its_value(self, measured):
        assert measured["split"] == [], (measured["label"], len(measured["split"]), measured["split"][:5])
