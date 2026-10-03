"""UX-1157, UX-1164, UX-1171: at 390 and 1440 nothing overlaps, overflows or breaks a word.

No axis's tick labels overlap, cover the caption after it, leave the
viewport or say a mark twice; nothing outside a scroll box passes the
document; a stacked table of tables labels every cell; a
`dl` holds only `dt`/`dd`, with its door just before it; no table's box
passes the viewport; the constraints table and a table of tables fit
their box with no word split; a query scrolls in its own box; a chapter's
question has its head's row; the rail's steps show their whole labels; a
16-character run name stays whole on the wordmark's row.

Styleguide §6e rule 10.
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
  const sec = (n) => n.closest("[data-section]")?.dataset.section;
  const hit = (r, s) => r.left < s.right - 0.5 && s.left < r.right - 0.5
    && r.top < s.bottom - 0.5 && s.top < r.bottom - 0.5;
  const overlaps = [], offScreen = [], doubled = [];
  for (const axis of document.querySelectorAll("main .draw-axis")) {
    const ticks = [...axis.querySelectorAll(".draw-tick")].filter(shown);
    const boxes = ticks.map((t) => [t.textContent.trim(), t.getBoundingClientRect()]);
    boxes.forEach(([a, r], i) => boxes.slice(i + 1).forEach(([b, s]) => {
      if (hit(r, s)) overlaps.push(`${sec(axis)}: ${a} / ${b}`);
    }));
    for (const t of ticks) {
      const r = t.getBoundingClientRect();
      if (r.left < -0.5 || r.right > vw + 0.5) offScreen.push(`${sec(t)}: ${t.textContent} ${Math.round(r.left)}-${Math.round(r.right)}`);
      const after = getComputedStyle(t, "::after").content;
      const said = t.textContent + (after === "none" ? "" : after);
      if ((t.dataset.mark || "").split(" ").some((m) => said.split(m).length > 2)) doubled.push(`${sec(t)}: ${said}`);
    }
  }
  const overCaption = [];
  for (const axis of document.querySelectorAll("main .draw-axis")) {
    const next = axis.nextElementSibling;
    if (!next || !shown(next)) continue;
    for (const t of [...axis.querySelectorAll(".draw-tick")].filter(shown)) {
      if (hit(t.getBoundingClientRect(), next.getBoundingClientRect())) overCaption.push(`${sec(axis)}: ${t.textContent}`);
    }
  }
  const pastDocument = [...new Set([...document.querySelectorAll("main *")].filter(shown)
    .filter((n) => !n.closest("pre, table") && n.getBoundingClientRect().right > vw + 0.5)
    .map((n) => `${sec(n)} ${n.tagName}.${n.className}`))];
  const ofTables = [...document.querySelectorAll("main table")].filter((t) => shown(t) && t.querySelector("td table"));
  const stacked = ofTables.filter((t) => getComputedStyle(t.querySelector("td")).display === "block").length;
  const unlabelled = ofTables.flatMap((t) => [...t.querySelectorAll(":scope > tbody > tr > td:not([colspan])")]
    .filter((c) => getComputedStyle(c).display === "block" && !/^"[^"\s]/.test(getComputedStyle(c, "::before").content))
    .map((c) => `${t.dataset.table}: ${c.dataset.column}`));
  const unclipped =[...document.querySelectorAll("main pre")].filter(shown)
    .filter((p) => p.scrollWidth > p.clientWidth + 0.5 && getComputedStyle(p).overflowX === "visible")
    .map((p) => `${sec(p)} ${p.scrollWidth}/${p.clientWidth}`);
  const narrowed = [...document.querySelectorAll(".chapter-head > h2")].filter(shown).filter((h) => {
    const range = document.createRange();
    range.selectNodeContents(h);
    const lines = new Set([...range.getClientRects()].map((r) => Math.round(r.top))).size;
    const head = getComputedStyle(h.parentElement);
    const room = h.parentElement.clientWidth - parseFloat(head.paddingLeft) - parseFloat(head.paddingRight);
    return lines > 1 && h.getBoundingClientRect().width < room - 0.5;
  }).map((h) => `${h.textContent} ${Math.round(h.getBoundingClientRect().width)}`);
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
                                || t.querySelector("td table"));
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
  // The rail's Top shows once the page is scrolled past its first screen.
  scrollTo(0, 3 * innerHeight);
  dispatchEvent(new Event("scroll"));
  const steps = [...document.querySelectorAll(".toc-steps button")].filter(shown);
  const keys = document.querySelector(".toc-keys");
  const clipped = steps.filter((b) => b.scrollWidth > b.clientWidth + 0.5
      || (keys && shown(keys) && hit(b.getBoundingClientRect(), keys.getBoundingClientRect())))
    .map((b) => `${b.textContent} ${b.scrollWidth}/${b.clientWidth}`);
  return { overCaption, pastDocument, unlabelled, stacked, overlaps, offScreen, doubled, unclipped, narrowed, steps: steps.length, clipped, strayChildren, doorless, described: described.length,
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
        assert found[1440]["steps"] == 3, (label, found[1440]["steps"])
        if label != "golden":
            assert "constraints" in found[390]["mustFit"], (label, found[390]["mustFit"])

    def test_no_tick_label_overlaps_another(self, measured):
        label, found = measured
        assert {w: g["overlaps"] for w, g in found.items() if g["overlaps"]} == {}, label

    def test_no_tick_label_covers_its_caption(self, measured):
        label, found = measured
        assert {w: g["overCaption"] for w, g in found.items() if g["overCaption"]} == {}, label

    def test_nothing_outside_a_scroll_box_passes_the_document(self, measured):
        label, found = measured
        assert {w: g["pastDocument"][:5] for w, g in found.items() if g["pastDocument"]} == {}, label

    def test_a_stacked_table_labels_every_cell(self, measured):
        label, found = measured
        if label != "golden":
            assert found[390]["stacked"] > 0 and found[1440]["stacked"] == 0, (label, found)
        assert {w: g["unlabelled"][:5] for w, g in found.items() if g["unlabelled"]} == {}, label

    def test_no_tick_label_leaves_the_viewport(self, measured):
        label, found = measured
        assert {w: g["offScreen"] for w, g in found.items() if g["offScreen"]} == {}, label

    def test_a_merged_tick_says_its_marks_once(self, measured):
        label, found = measured
        assert {w: g["doubled"] for w, g in found.items() if g["doubled"]} == {}, label

    def test_a_query_scrolls_in_its_own_box(self, measured):
        label, found = measured
        assert {w: g["unclipped"][:3] for w, g in found.items() if g["unclipped"]} == {}, label

    def test_a_chapter_question_has_its_heads_row(self, measured):
        label, found = measured
        assert {w: g["narrowed"] for w, g in found.items() if g["narrowed"]} == {}, label

    def test_the_rail_steps_show_their_whole_labels(self, measured):
        label, found = measured
        assert {w: g["clipped"] for w, g in found.items() if g["clipped"]} == {}, label

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
