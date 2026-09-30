"""UX-1156: each sentence is drawn once, and no pair restates its section's lead.

Booted with every chapter and fold open on `golden`, `macro_micro` and the
two-plane page (8 layers x 14): no sentence of 8 or more words is drawn
twice, and under a section's lead no pair draws a member the lead says
(`data-said`) or a verdict the lead answers; no element card's evidence block
repeats an earlier one's pairs, and no strip label restates the row count.
A link's text names a place and a stock line an absence; neither is a sentence.
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

WORDS = 8

_MEASURE = (
    pages.FULL_LAYOUT_JS
    + r"""
(async () => {
  for (const box of document.querySelectorAll("section.chapter")) box.setAttribute("data-open", "true");
  for (const shut of document.querySelectorAll("section.chapter > [hidden='until-found']")) shut.removeAttribute("hidden");
  for (const fold of document.querySelectorAll("details")) fold.open = true;
  await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
  const flat = (t) => t.replace(/\s+/g, " ").trim();
  // A link or control names a place or an act, code is a command; the stock lines name an absence.
  const STOCK = "a, button, code, pre, script, style, svg, .empty-population, [data-drawn='false'] > .density-sentence";
  const BLOCK ="p, li, dd, dt, td, th, summary, h1, h2, h3, h4, h5, h6, figcaption, caption, pre, div, section, article";
  const blocks = new Map();
  const walker = document.createTreeWalker(document.querySelector("main") ?? document.body, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    const text = walker.currentNode, parent = text.parentElement;
    if (!parent || parent.closest(STOCK)) continue;
    if (!parent.checkVisibility({ visibilityProperty: true })) continue;
    const block = parent.closest(BLOCK);
    blocks.set(block, (blocks.get(block) ?? "") + text.textContent);
  }
  const drawn = new Map();
  for (const [block, text] of blocks) {
    for (const piece of flat(text).split(/(?<=[.!?])\s+|\s·\s/)) {
      const sentence = piece.replace(/[.:;,]+$/, "");
      if ((sentence.match(/[A-Za-z]{2,}/g) ?? []).length < __WORDS__) continue;
      const where = block.closest("[data-section], article[id]")?.id ?? "?";
      drawn.set(sentence, [...(drawn.get(sentence) ?? []), where]);
    }
  }
  const twice = [...drawn].filter(([, at]) => at.length > 1).map(([s, at]) => [s.slice(0, 90), at]);
  const restated = [];
  let leads = 0, keys = 0;
  for (const lead of document.querySelectorAll("p.section-answer, p.section-lead")) {
    leads += 1;
    // The members an answer says are on its `data-said`; a producer's lead answers
    // its booleans and its empty lists (a list draws "none" with no `data-raw`).
    const said = (lead.getAttribute("data-said") ?? "").split(" ").filter(Boolean);
    keys += said.length;
    const producer = lead.classList.contains("section-lead");
    const section = lead.closest("[data-section]");
    for (const dt of section.querySelectorAll(":scope > dl.pairs > dt")) {
      const dd = dt.nextElementSibling;
      const value = flat((dd?.querySelector(":scope > span") ?? dd)?.textContent ?? "");
      const empty = dd?.querySelector(":scope > span.muted:not([data-raw])")?.textContent === "none";
      if (said.includes(dt.getAttribute("data-key")) || (producer && (/^(yes|no)$/.test(value) || empty))) {
        restated.push([section.id, flat(dt.textContent), value]);
      }
    }
  }
  // An evidence block whose every pair an earlier block of the fold draws; a strip label counting rows.
  const pairsOf = (dl) => [...dl.querySelectorAll(":scope > dt")].map((dt) => flat(`${dt.textContent}=${dt.nextElementSibling?.textContent}`));
  const blocksTwice = [];
  let evidence = 0;
  for (const fold of document.querySelectorAll("details.join-evidence")) {
    const lists = [...fold.querySelectorAll(":scope > dl.pairs")].map(pairsOf);
    evidence += lists.length;
    lists.forEach((mine, at) => {
      if (lists.slice(0, at).some((had) => mine.every((pair) => had.includes(pair)))) blocksTwice.push([fold.closest("[data-section]").id, mine]);
    });
  }
  // A link is a name only while it reads as one: no clause break past a leading "from: ".
  const links = [...document.querySelectorAll("main a")].map((a) => flat(a.textContent).replace(/^\w+: /, ""))
    .filter((t) => /[.:;] \S/.test(t));
  const counted = [...document.querySelectorAll(".density-label")].map((n) => flat(n.textContent)).filter((t) => /\d+ rows?\b/.test(t));
  return { sentences: drawn.size, twice, leads, keys, restated, evidence, blocksTwice, counted, links };
})()
""".replace("__WORDS__", str(WORDS))
)


def _two_plane(into):
    import tools.bga_view as view

    run = pages.two_plane_run(into, shape=("--layers", "8", "--width", "14"), name="both")
    page = pathlib.Path(into) / "both.html"
    view.export(str(run), str(page))
    return page.as_uri()


@pytest.fixture(scope="module", params=["golden", "macro_micro", "two_plane"])
def measured(request, tmp_path_factory):
    into = tmp_path_factory.mktemp(f"u1156-{request.param}")
    two = request.param == "two_plane"
    uri = _two_plane(into) if two else pages.export_uri(pages.FIXTURES[request.param], into)
    with Browser(chrome) as opened:
        result = opened.measure(uri, _MEASURE)
    result["label"] = request.param
    return result


@needs_browser
class TestEachSentenceIsDrawnOnce:
    def test_the_census_reads_a_page(self, measured):
        assert measured["sentences"] > 40, measured
        if measured["label"] == "two_plane":
            assert measured["leads"] >= 5 and measured["keys"] >= 10, measured

    def test_no_sentence_is_drawn_twice(self, measured):
        assert not measured["twice"], measured["twice"]

    def test_a_link_reads_as_a_name(self, measured):
        """The census skips link text as a name; a link carrying a clause is a sentence it would miss."""
        assert not measured["links"], measured["links"][:5]

    def test_no_pair_restates_its_sections_lead(self, measured):
        assert not measured["restated"], measured["restated"]

    def test_no_evidence_block_repeats_an_earlier_one(self, measured):
        if measured["label"] == "two_plane":
            assert measured["evidence"] > 10, measured
        assert not measured["blocksTwice"], measured["blocksTwice"][:3]

    def test_a_strip_label_names_its_column_not_the_count(self, measured):
        assert not measured["counted"], measured["counted"]
