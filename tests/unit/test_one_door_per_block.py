"""UX-1021 (styleguide §6e.4): one `?` door per block.

Measured on `main` at `98ab850`: 191 doors in 39 blocks on
`macro_micro`, 127 in 29 on `golden` - a described value drew its own
door rather than the block sharing one. `attachBlockDoor` (`format.js`)
builds one marker per block that opens every collected `.description`
in place; a block's own selector is the styleguide's own census one
(`dl, table, section[data-section], ul, ol`, nearest ancestor first).
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
  const blockOf = (node) => node.closest("dl, table, section[data-section], ul, ol");
  const counts = new Map();
  for (const door of document.querySelectorAll("button.describe")) {
    const block = blockOf(door);
    const key = block ? (block.getAttribute("data-section")
                         || block.tagName + "#" + [...document.querySelectorAll(
                            block.tagName)].indexOf(block)) : "(no block)";
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }
  return { doors: document.querySelectorAll("button.describe").length,
           perBlock: Object.fromEntries(counts) };
})()
"""


@pytest.fixture(scope="module", params=["golden", "macro_micro"])
def measured(request, tmp_path_factory):
    uri = pages.export_uri(pages.FIXTURES[request.param],
                           tmp_path_factory.mktemp(f"u1021-{request.param}"))
    with Browser(chrome) as opened:
        result = opened.measure(uri, _MEASURE)
    result["label"] = request.param
    return result


@needs_browser
class TestOneDoorPerBlock:
    def test_the_page_has_doors(self, measured):
        assert measured["doors"] > 0, measured["label"]

    def test_at_most_one_door_per_block(self, measured):
        over = {block: count for block, count in measured["perBlock"].items()
               if count > 1}
        assert over == {}, (measured["label"], over)
