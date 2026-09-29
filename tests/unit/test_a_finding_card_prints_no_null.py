"""UX-1136: no text node on the page reads `null` or `undefined`.

A finding card's hydrate passed `null` children to the native
`append`, which prints them as the text "null" - two to three per card
on both fixtures. `el` skips a null child; the native call does not.
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
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const stray = [];
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    const text = node.textContent.trim();
    if (!/^(null|undefined|NaN|\[object Object\])$/.test(text)) continue;
    const parent = node.parentElement;
    if (parent.closest("script, code, pre")) continue;
    stray.push(`${parent.tagName.toLowerCase()}#${parent.id} ${text}`);
  }
  return { stray, findings: document.querySelectorAll("article.finding").length };
})()
"""


@pytest.fixture(scope="module", params=["golden", "macro_micro"])
def measured(request, tmp_path_factory):
    uri = pages.export_uri(pages.FIXTURES[request.param], tmp_path_factory.mktemp(f"u1136-{request.param}"))
    with Browser(chrome) as opened:
        result = opened.measure(uri, _MEASURE)
    result["label"] = request.param
    return result


@needs_browser
class TestNoNullText:
    def test_the_page_has_findings(self, measured):
        assert measured["findings"] > 0, measured["label"]

    def test_no_text_node_reads_null(self, measured):
        assert measured["stray"] == [], (measured["label"], measured["stray"][:5])
