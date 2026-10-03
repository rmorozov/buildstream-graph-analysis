"""UX-1152: four shapes that drew on screen what was already there.

An open long-text fold shows its text once and is not labelled by a
character count; every Why fold opens below its row; a table of two rows
or fewer carries no badge and no strip, and a one-row array is pairs;
an element card's "Also in:" link reads its section's own title.

Styleguide §5a.
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
  const frames = () => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
  for (const box of document.querySelectorAll("section.chapter")) box.setAttribute("data-open", "true");
  await frames();
  const shown = (n) => { const r = n.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const flat = (t) => t.replace(/\s+/g, " ").trim();
  const folds = [...document.querySelectorAll("details.long-text")];
  const repeated = [], counted = [];
  for (const fold of folds) {
    const summary = fold.querySelector(":scope > summary");
    if (/\d[\d,]*\s*chars/.test(summary.textContent)) counted.push(flat(summary.textContent).slice(0, 40));
    fold.open = true;
    await frames();
    const full = flat(fold.querySelector(".full-text")?.textContent ?? "");
    const preview = summary.querySelector(":scope > span");
    const head = flat((preview?.textContent ?? "").replace(/….*$/s, ""));
    const drawn = preview && getComputedStyle(preview).display !== "none";
    if (drawn && head.length > 20 && full.startsWith(head)) repeated.push(head.slice(0, 40));
  }
  const beside = [];
  const whys = [...document.querySelectorAll("details.why-ranked")].filter(shown);
  for (const why of whys) {
    why.open = true;
    await frames();
    const first = why.parentNode.firstElementChild.getBoundingClientRect();
    if (why.getBoundingClientRect().top < first.bottom - 1) beside.push(flat(why.querySelector("summary").textContent));
    why.open = false;
  }
  await frames();
  const counts = [];
  let small = 0;
  for (const table of document.querySelectorAll("table[data-rows]")) {
    const n = Number(table.getAttribute("data-rows"));
    const tools = table.parentNode.querySelector(":scope > .table-tools");
    if (n > 2 || !tools) continue;
    small += 1;
    // The count is `Copy N rows` alone; a strip under the floor states it (`UX-226`), unlabelled.
    const said = (flat(tools.textContent).match(/\d+ rows?\b/g) ?? []).length;
    if (said > 1 || tools.querySelector(".badge, .density-label, [data-column][data-drawn='true']")) {
      counts.push([table.getAttribute("data-table"), n]);
    }
  }
  // A row holding a nested table stays a table: the nested one keeps its fold and rail entry.
  const flatRow = "table[data-rows='1']:not([data-element-column]):not(:has(td table))";
  const oneRow = [...document.querySelectorAll(
    `section[data-section] > ${flatRow}, dl.pairs > dd > .map-table > ${flatRow}`)]
    .map((t) => t.getAttribute("data-table"));
  const idLinks = [];
  let links = 0;
  for (const a of document.querySelectorAll("[data-where]")) {
    links += 1;
    const key = a.getAttribute("data-where");
    const head = document.getElementById(key)?.querySelector(":scope > h2, :scope > h3");
    const own = head ? flat([...head.childNodes].filter((n) => n.nodeType === 3).map((n) => n.textContent).join("")) : "";
    if (own && flat(a.textContent) !== own) idLinks.push([key, flat(a.textContent), own]);
  }
  return { folds: folds.length, counted, repeated, whys: whys.length, beside, small, counts, oneRow, links, idLinks };
})()
"""


def _two_plane(into):
    import tools.bga_view as view

    run = pages.two_plane_run(into, shape=("--layers", "8", "--width", "14"), name="both")
    page = pathlib.Path(into) / "both.html"
    view.export(str(run), str(page))
    return page.as_uri()


@pytest.fixture(scope="module", params=["golden", "macro_micro", "two_plane"])
def measured(request, tmp_path_factory):
    into = tmp_path_factory.mktemp(f"u1152-{request.param}")
    two = request.param == "two_plane"
    uri = _two_plane(into) if two else pages.export_uri(pages.FIXTURES[request.param], into)
    with Browser(chrome) as opened:
        result = opened.measure(uri, _MEASURE)
    result["label"] = request.param
    return result


@needs_browser
class TestRepeatsAreNotDrawnTwice:
    def test_the_two_plane_page_holds_every_shape(self, measured):
        if measured["label"] == "two_plane":
            held = (measured["folds"], measured["whys"], measured["small"], measured["links"])
            assert all(held), measured

    def test_an_open_fold_shows_its_text_once(self, measured):
        assert not measured["repeated"], measured

    def test_a_fold_is_not_labelled_by_its_length(self, measured):
        assert not measured["counted"], measured

    def test_every_why_opens_below_its_row(self, measured):
        assert not measured["beside"], measured

    def test_two_rows_carry_no_count_and_no_strip(self, measured):
        assert not measured["counts"], measured

    def test_one_row_is_pairs_not_a_table(self, measured):
        assert not measured["oneRow"], measured

    def test_a_card_link_reads_its_sections_title(self, measured):
        assert not measured["idLinks"], measured
