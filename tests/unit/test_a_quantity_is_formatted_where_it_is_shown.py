"""UX-1140: a quantity on the page is formatted, and its unit is spaced.

The decision panel's Why pairs and every provenance value go through
the element card's formatter; a number in reader prose is not glued to
`s`/`ms`. Every finding and fold is opened first, so text inserted
after boot is held too. `data-raw` keeps the published number.
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
  document.querySelectorAll("details").forEach((d) => { d.open = true; });
  await new Promise((done) => setTimeout(done, 50));
  const skip = "code, pre, kbd, samp, script, style, svg, textarea, select, option, td";
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const raw = [], glued = [];
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    const parent = node.parentElement;
    if (!parent || parent.closest(skip)) continue;
    const where = `${parent.tagName.toLowerCase()}@${parent.closest("[id]")?.id}: ${node.data.trim().slice(0, 80)}`;
    if (/\d+\.\d{5,}/.test(node.data)) raw.push(where);
    if (/(?<![\w.])\d+(?:\.\d+)?(?:ms|s)(?=$|[\s,;:)\]]|\.(?:\s|$))/.test(node.data)) glued.push(where);
  }
  const values = [...document.querySelectorAll(
    "#decision dl.why-facts > dd, dl.evidence-refs > dd")];
  return {
    raw, glued, values: values.length,
    // A formatted value still carries the published number beside it.
    kept: values.filter((dd) => dd.hasAttribute("data-raw")).length,
  };
})()
"""

_SYNTHETIC = ("--layers", "8", "--width", "14")


@pytest.fixture(scope="module", params=["golden", "macro_micro", "two_plane"])
def measured(request, tmp_path_factory):
    into = tmp_path_factory.mktemp(f"u1140-{request.param}")
    if request.param == "two_plane":
        uri = pages.in_place_uri(pages.two_plane_run(into, shape=_SYNTHETIC), into)
    else:
        uri = pages.export_uri(pages.FIXTURES[request.param], into)
    with Browser(chrome) as opened:
        result = {width: opened.measure(uri, _MEASURE, width=width) for width in (1440, 390)}
    return request.param, result


@needs_browser
class TestQuantities:
    def test_the_page_draws_values_to_format(self, measured):
        label, result = measured
        got = result[1440]
        assert got["values"] > 0, label
        assert got["kept"] == got["values"], label

    def test_no_text_node_prints_a_raw_float(self, measured):
        label, result = measured
        for width, got in result.items():
            assert got["raw"] == [], (label, width, len(got["raw"]), got["raw"][:5])

    def test_no_number_is_glued_to_its_unit(self, measured):
        label, result = measured
        for width, got in result.items():
            assert got["glued"] == [], (label, width, len(got["glued"]), got["glued"][:5])
