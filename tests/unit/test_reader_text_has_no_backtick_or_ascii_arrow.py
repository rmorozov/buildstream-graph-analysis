"""UX-1149: reader text holds no literal backtick and no `->`.

Inline code is `<code>`, an arrow is `→`, and a finding's detail line
leads with its sentence. Every finding is hydrated first, so text
inserted after boot is held to the same rule. A table cell is data.
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
(async () => {
  document.querySelectorAll("article.finding").forEach((a) => a._hydrate?.());
  await new Promise((done) => setTimeout(done, 50));
  const skip = "code, pre, kbd, samp, script, style, svg, textarea, select, option, td";
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const raw = [];
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    const parent = node.parentElement;
    if (!parent || parent.closest(skip)) continue;
    if (!/`|->/.test(node.data)) continue;
    raw.push(`${parent.tagName.toLowerCase()}@${parent.closest("[id]")?.id}: ${node.data.trim().slice(0, 80)}`);
  }
  const details = [...document.querySelectorAll("article.finding p.detail")];
  return {
    raw,
    leading: details.filter((p) => /^\s*(->|→)/.test(p.textContent)).length,
    details: details.length,
    code: document.querySelectorAll("#report code").length,
  };
})()
"""

_SYNTHETIC = ("--layers", "8", "--width", "14")


@pytest.fixture(scope="module", params=["golden", "macro_micro", "two_plane"])
def measured(request, tmp_path_factory):
    into = tmp_path_factory.mktemp(f"u1149-{request.param}")
    if request.param == "two_plane":
        uri = pages.in_place_uri(pages.two_plane_run(into, shape=_SYNTHETIC), into)
    else:
        uri = pages.export_uri(pages.FIXTURES[request.param], into)
    with Browser(chrome) as opened:
        result = {width: opened.measure(uri, _MEASURE, width=width) for width in (1440, 390)}
    return request.param, result


@needs_browser
class TestReaderText:
    def test_the_page_has_finding_details(self, measured):
        label, result = measured
        assert result[1440]["details"] > 0, label

    def test_no_text_node_holds_a_backtick_or_ascii_arrow(self, measured):
        label, result = measured
        for width, got in result.items():
            assert got["raw"] == [], (label, width, len(got["raw"]), got["raw"][:5])

    def test_a_detail_line_does_not_lead_with_an_arrow(self, measured):
        label, result = measured
        assert result[1440]["leading"] == 0, label
