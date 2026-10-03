"""UX-1140: a quantity on the page is formatted, and its unit is spaced.

The decision panel's Why pairs and every provenance value go through
the element card's formatter; a number in reader prose is not glued to
`s`/`ms`. Every finding and fold is opened first, so text inserted
after boot is held too. `data-raw` keeps the published number.

Styleguide §4g.
"""

import pathlib
import re
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
  const raw = [], glued = [], bare = [], secs = [], grouped = [];
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    const parent = node.parentElement;
    if (!parent || parent.closest(skip)) continue;
    const where = `${parent.tagName.toLowerCase()}@${parent.closest("[id]")?.id}: ${node.data.trim().slice(0, 80)}`;
    if (/\d+\.\d{5,}/.test(node.data)) raw.push(where);
    if (/(?<![\w.])\d+(?:\.\d+)?(?:ms|s)(?=$|[\s,;:)\]]|\.(?:\s|$))/.test(node.data)) glued.push(where);
    // `UX-1252`: a count of four or more digits carries its separator; a prose duration is the row's format.
    if (/(?<![\w.,:\/#@-])\d{4,}(?![-\w]|[.,:]\d)/.test(node.data)) bare.push(where);
    if (/(?<![\w.,])\d{1,3}(?:,\d{3})+(?![\d.])/.test(node.data)) grouped.push(where);
    if (/(?<![\w.])\d+\.\d\d s\b/.test(node.data)) secs.push(where);
  }
  const values = [...document.querySelectorAll(
    "#decision dl.why-facts > dd, dl.evidence-refs > dd")];
  const cards = [...document.querySelectorAll("article.finding")].map((a) => ({
    title: a.querySelector("p.title")?.textContent ?? "",
    // the value node only: a dd also carries its description
    pairs: [...a.querySelectorAll("dl.pairs dd")].map(
      (dd) => dd.firstChild?.textContent ?? ""),
  }));
  return {
    raw, glued, bare, secs, grouped, cards, values: values.length,
    // A formatted value still carries the published number beside it.
    kept: values.filter((dd) => dd.hasAttribute("data-raw")).length,
  };
})()
"""

_QUANTITY = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?) ?(ms|s|min|h|%)(?![\w%])")


# A share spelled as a bare 0..1 fraction ("Confidence: 1.00").
_FRACTION = re.compile(r"(?<![\w.])(0\.\d\d|1\.00)(?![\w.%])")


def _disagreements(cards):
    """A title quantity and a pair quantity of one unit and one value, spelled two ways."""
    found = []
    for card in cards:
        pairs = [
            (m.group(0), float(m.group(1)), m.group(2)) for text in card["pairs"] for m in _QUANTITY.finditer(text)
        ]
        for m in _QUANTITY.finditer(card["title"]):
            spelled, value, unit = m.group(0), float(m.group(1)), m.group(2)
            for other, seen, seen_unit in pairs:
                near = abs(value - seen) <= 0.02 * max(abs(seen), 1e-9)
                if unit == seen_unit and near and spelled != other:
                    found.append((card["title"][:60], spelled, other))
        for m in _FRACTION.finditer(card["title"]):
            for other, seen, unit in pairs:
                if unit == "%" and abs(float(m.group(1)) * 100 - seen) <= 0.6:
                    found.append((card["title"][:60], m.group(0), other))
    return found


_SYNTHETIC = ("--layers", "8", "--width", "14")


#: `UX-1252`: 1,200 elements, the smallest seeded shape whose blast ranking reaches four digits.
_COUNTED = ("--layers", "40", "--width", "30", "--builders", "4")


@pytest.fixture(scope="module", params=["golden", "macro_micro", "two_plane", "counted"])
def measured(request, tmp_path_factory):
    into = tmp_path_factory.mktemp(f"u1140-{request.param}")
    if request.param == "two_plane":
        uri = pages.in_place_uri(pages.two_plane_run(into, shape=_SYNTHETIC), into)
    elif request.param == "counted":
        uri = pages.export_uri(pages.scale_run(into, shape=_COUNTED), into)
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

    def test_no_count_lacks_its_separator(self, measured):
        label, result = measured
        for width, got in result.items():
            assert got["bare"] == [], (label, width, len(got["bare"]), got["bare"][:5])
            if label == "counted":
                assert got["grouped"], (label, width)

    def test_no_prose_duration_is_raw_seconds(self, measured):
        label, result = measured
        for width, got in result.items():
            assert got["secs"] == [], (label, width, got["secs"][:5])

    def test_a_title_quantity_reads_as_its_pair(self, measured):
        label, result = measured
        for width, got in result.items():
            assert _disagreements(got["cards"]) == [], (label, width)


def test_the_disagreement_check_sees_two_spellings():
    cards = [{"title": "Path is 78.35 s", "pairs": ["78.3 s"]}]
    assert _disagreements(cards) == [("Path is 78.35 s", "78.35 s", "78.3 s")]
    assert _disagreements([{"title": "78.3 s long", "pairs": ["78.3 s"]}]) == []
    fraction = [{"title": "Confidence: 1.00 (high)", "pairs": ["100.0%"]}]
    assert _disagreements(fraction) == [("Confidence: 1.00 (high)", "1.00", "100.0%")]
