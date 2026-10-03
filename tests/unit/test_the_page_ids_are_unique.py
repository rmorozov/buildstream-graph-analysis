"""UX-1173: every id is unique, and nothing a reader reads says itself twice.

On the page: no id twice, no two rail entries alike, the parallelism
drawing numbering levels as the table does (roots are level 0), a
list's column holding items rather than indexes, a preset sentence not
repeating its heading, and a rail entry the ellipsis cuts carrying its
label as a title. Chromium
on `golden`, `macro_micro` and the 114-element two-plane run, at 1440.

Styleguide §5a.
"""

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

import pages
from browser import NO_BROWSER, Browser, find_chrome

needs_browser = pytest.mark.skipif(find_chrome() is None, reason=NO_BROWSER)

_LOOK = r"""
(() => {
  const text = (node) => (node?.textContent ?? "").trim();
  const ids = {};
  for (const node of document.querySelectorAll("[id]")) ids[node.id] = (ids[node.id] ?? 0) + 1;
  const rail = [...document.querySelectorAll("nav.toc a")];
  const said = {};
  for (const a of rail) said[text(a)] = (said[text(a)] ?? 0) + 1;
  const levels = document.querySelector('#parallelism table[data-table="levels"]');
  const rows = [...(levels?.querySelectorAll("tbody tr") ?? [])].map((tr) => ({
    level: text(tr.querySelector('[data-column="level"]')),
    width: Number(tr.querySelector('[data-column="width"]')?.getAttribute("data-raw")),
  }));
  const widest = rows.reduce((best, row) => (row.width > (best?.width ?? -1) ? row : best), null);
  const series = document.querySelector("#parallelism .series");
  const indexed = [...document.querySelectorAll("table")].filter((table) => {
    const keys = [...table.querySelectorAll('tbody td[data-column="key"]')].map(text);
    return keys.length > 1 && keys.every((k, i) => k === String(i));
  }).map((table) => table.getAttribute("data-table"));
  const presetSays = text(document.querySelector("#elements .preset-body > p"));
  const presetAsks = text(document.querySelector("#elements h2, #elements h3")).replace(/[▾▸]/g, "").trim();
  return {
    twice: Object.entries(ids).filter(([, n]) => n > 1),
    alike: Object.entries(said).filter(([, n]) => n > 1),
    railLinks: rail.length,
    firstLevel: rows[0]?.level ?? null,
    widestLevel: widest?.level ?? null,
    firstTick: text(series?.querySelector('.draw-tick[data-mark~="first"]')),
    sentence: text(series?.querySelector(".series-sentence")),
    indexed,
    presetSays,
    presetAsks,
    cut: rail.filter((a) => a.scrollWidth > a.clientWidth)
      .map((a) => ({ text: text(a), title: a.getAttribute("title") })),
  };
})()
"""


@pytest.fixture(scope="module")
def looked(tmp_path_factory):
    uris = pages.pages(tmp_path_factory, prefix="ux1173", labels=["golden", "macro_micro"])
    both = pages.two_plane_run(tmp_path_factory.mktemp("ux1173-both"), ("--layers", "8", "--width", "14"))
    page = tmp_path_factory.mktemp("ux1173-both-page") / "report.html"
    import tools.bga_view as view

    view.export(str(both), str(page))
    uris["two_plane"] = page.as_uri()
    with Browser(find_chrome()) as browser:
        return {label: browser.measure(uri, _LOOK, 1440, 900) for label, uri in uris.items()}


@needs_browser
class TestThePageSaysEachThingOnce:
    def test_no_id_is_on_the_page_twice(self, looked):
        for label, out in looked.items():
            assert out["twice"] == [], (label, out["twice"])

    def test_no_two_rail_entries_read_alike(self, looked):
        for label, out in looked.items():
            assert out["railLinks"] > 20, (label, out["railLinks"])
            assert out["alike"] == [], (label, out["alike"])

    def test_the_drawing_counts_levels_as_the_table_does(self, looked):
        for label, out in looked.items():
            assert out["firstLevel"] == "0", (label, out["firstLevel"])
            # A merged tick reads "level 0 (peak 2)": the leading label is the level.
            assert out["firstTick"].split(" (")[0] == f"level {out['firstLevel']}", (label, out["firstTick"])
            assert out["sentence"].endswith(f"at level {out['widestLevel']}."), (label, out)

    def test_a_list_column_holds_items_not_indexes(self, looked):
        for label, out in looked.items():
            assert out["indexed"] == [], (label, out["indexed"])

    def test_the_preset_sentence_does_not_repeat_its_heading(self, looked):
        for label, out in looked.items():
            assert out["presetAsks"] and out["presetSays"], (label, out)
            assert out["presetAsks"] not in out["presetSays"], (label, out["presetSays"])

    def test_a_cut_rail_entry_carries_its_label(self, looked):
        for label, out in looked.items():
            assert out["cut"], f"{label}: no rail entry is cut at 1440 - the clause below reads nothing"
            for entry in out["cut"]:
                assert entry["title"] == entry["text"], (label, entry)
