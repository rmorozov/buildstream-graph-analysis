"""UX-1157: at 390 and 1440 nothing overlaps, overflows or breaks a word.

The floors ticks stay apart; a `dl` holds only `dt`/`dd`, with its door
just before it; no table's box passes the viewport; the constraints table
and a table of tables fit their box with no word split; a 16-character
run name stays whole on the wordmark's row.
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

WIDTHS = (390, 1440)

_MEASURE = (
    "(() => {"
    + pages.OPEN_EVERY_DOOR_JS
    + r"""
  const vw = document.documentElement.clientWidth;
  const shown = (n) => n.getClientRects().length > 0;
  const overlaps = [];
  for (const axis of document.querySelectorAll("[data-section=floors] .draw-axis")) {
    const boxes = [...axis.querySelectorAll(".draw-tick")].filter(shown)
      .map((t) => [t.textContent.trim(), t.getBoundingClientRect()]);
    boxes.forEach(([a, r], i) => boxes.slice(i + 1).forEach(([b, s]) => {
      if (r.left < s.right - 0.5 && s.left < r.right - 0.5
          && r.top < s.bottom - 0.5 && s.top < r.bottom - 0.5) overlaps.push(`${a} / ${b}`);
    }));
  }
  const described = [...document.querySelectorAll("dl")].filter((dl) =>
    dl.querySelector(".description:not([data-inline])"));
  const doorless = described.filter((dl) => !dl.previousElementSibling?.matches("button.describe"))
    .map((dl) => dl.closest("[data-section]")?.dataset.section);
  const strayChildren = [...document.querySelectorAll("dl")].flatMap((dl) =>
    [...dl.children].filter((c) => !["DT", "DD", "DIV", "SCRIPT", "TEMPLATE"].includes(c.tagName))
      .map((c) => `${dl.closest("[data-section]")?.dataset.section}: ${c.tagName}.${c.className}`));
  const tables = [...document.querySelectorAll("main table")].filter(shown);
  const name = (t) => t.dataset.table || t.closest("[data-section]")?.dataset.section;
  const pastViewport = tables.filter((t) => t.getBoundingClientRect().right > vw + 0.5).map(name);
  const mustFit = tables.filter((t) => t.dataset.table === "constraints"
                                || (vw < 960 && t.querySelector("td table")));
  const scrolling = mustFit.filter((t) => t.scrollWidth > t.clientWidth + 0.5)
    .map((t) => `${name(t)} ${t.scrollWidth}/${t.clientWidth}`);
  const splitWords = [];
  for (const t of mustFit) {
    const walker = document.createTreeWalker(t, NodeFilter.SHOW_TEXT);
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      if (!shown(node.parentElement)) continue;
      for (const m of node.data.matchAll(/\S+/g)) {
        const range = document.createRange();
        range.setStart(node, m.index);
        range.setEnd(node, m.index + m[0].length);
        const tops = new Set([...range.getClientRects()].map((r) => Math.round(r.top)));
        if (tops.size > 1) splitWords.push(`${name(t)}: ${m[0]}`);
      }
    }
  }
  // The review page's own run id; a fixture's "run" is too short to be cut.
  const h1 = document.querySelector("h1#run-name");
  if (h1) h1.textContent = "20260303T091500Z";
  const mark = document.querySelector("#wordmark");
  const sameRow = h1 && mark && Math.abs(h1.getBoundingClientRect().top - mark.getBoundingClientRect().top) < 16;
  return { overlaps, strayChildren, doorless, described: described.length,
           evidence: document.querySelectorAll("article.finding dl.evidence").length, pastViewport, scrolling, splitWords,
           axes: document.querySelectorAll("[data-section=floors] .draw-axis").length,
           dls: document.querySelectorAll("dl").length, mustFit: mustFit.map(name),
           h1: h1 ? [h1.scrollWidth, h1.clientWidth, sameRow] : null };
})()
"""
)


def _uri(label, into):
    if label == "two_plane":
        return pages.export_uri(pages.two_plane_run(into, shape=pages.REVIEW_SHAPE), into / "page")
    return pages.export_uri(pages.FIXTURES[label], into)


@pytest.fixture(scope="module", params=["golden", "macro_micro", "two_plane"])
def measured(request, tmp_path_factory):
    uri = _uri(request.param, tmp_path_factory.mktemp(f"u1157-{request.param}"))
    with Browser(chrome) as opened:
        found = {
            width: opened.measure(uri, _MEASURE, width=width, height=844 if width == 390 else 900) for width in WIDTHS
        }
    return request.param, found


@needs_browser
class TestTheCompactPageFitsItsWidth:
    def test_the_page_has_what_is_measured(self, measured):
        label, found = measured
        for width, got in found.items():
            assert got["axes"] > 0 and got["dls"] > 0 and got["h1"], (label, width, got)
        if label != "golden":
            assert "constraints" in found[390]["mustFit"], (label, found[390]["mustFit"])

    def test_no_floors_label_overlaps_another(self, measured):
        label, found = measured
        assert {w: g["overlaps"] for w, g in found.items() if g["overlaps"]} == {}, label

    def test_a_dl_holds_only_its_pairs(self, measured):
        label, found = measured
        assert {w: g["strayChildren"][:5] for w, g in found.items() if g["strayChildren"]} == {}, label

    def test_its_door_stands_just_before_it(self, measured):
        label, found = measured
        for width, got in found.items():
            assert got["described"] > 0 and got["evidence"] > 0, (label, width, got)
        assert {w: g["doorless"][:5] for w, g in found.items() if g["doorless"]} == {}, label

    def test_no_table_passes_the_viewport(self, measured):
        label, found = measured
        assert {w: g["pastViewport"] for w, g in found.items() if g["pastViewport"]} == {}, label

    def test_a_prose_table_fits_without_scrolling(self, measured):
        label, found = measured
        assert {w: g["scrolling"] for w, g in found.items() if g["scrolling"]} == {}, label

    def test_no_word_in_it_breaks_across_lines(self, measured):
        label, found = measured
        assert {w: g["splitWords"][:5] for w, g in found.items() if g["splitWords"]} == {}, label

    def test_the_run_name_is_whole(self, measured):
        label, found = measured
        cut = {w: g["h1"] for w, g in found.items() if g["h1"][0] > g["h1"][1] or not g["h1"][2]}
        assert cut == {}, label
