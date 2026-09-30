"""UX-1177: Jump and the rail agree on folds and presets.

Chromium on the 114-element two-plane run at 1440: every rail sub-entry
(a fold or a preset) is a Jump hit under its own text, a rail press on a
level fold leaves it open, the level folds' summaries read apart, the
Top-N select's name is a phrase, and a partial uid several elements
share says how many.
"""

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

needs_browser = pytest.mark.skipif(find_chrome() is None, reason=NO_BROWSER)

_WALK = r"""
(async () => {
  const turn = (ms = 50) => new Promise((done) => setTimeout(done, ms));
  const text = (node) => (node?.textContent ?? "").replace(/\s+/g, " ").trim();
  const jump = document.getElementById("jump");
  const hits = (typed) => {
    jump.value = typed;
    jump.dispatchEvent(new Event("input", { bubbles: true }));
    return [...document.querySelectorAll(".jump-hits button[data-jump]")].map(text);
  };
  const rail = [...document.querySelectorAll("nav.toc a[data-toc-sub], nav.toc a[data-toc-view]")].map(text);
  const missed = rail.filter((entry) => !hits(entry).includes(entry));
  const typed = Object.fromEntries(["level 3", "critical", "leaves"].map((q) => [q, hits(q)]));
  hits("");
  const levels = [...document.querySelectorAll('#parallelism details.map[data-fold-path$=".elements"] > summary')]
    .map(text);
  const select = document.querySelector('select.top-n[aria-label^="Rows shown: Level 1"]')
    ?? document.querySelector('table[data-table="levels.1.elements"]')?.closest(".map-table")
      ?.querySelector("select.top-n");
  const link = [...document.querySelectorAll("nav.toc a[data-toc-sub]")].find((a) => text(a) === "Elements · Level 3");
  link?.click();
  await turn(300);
  const fold = link ? document.getElementById(decodeURIComponent(link.getAttribute("href").slice(1))) : null;
  const ask = document.querySelector("[data-role=query-element]");
  const note = document.getElementById(ask?.getAttribute("aria-describedby") ?? "");
  let partial = null;
  if (ask) {
    const population = Number(ask.getAttribute("data-population"));
    const uids = [...document.querySelectorAll(`#${ask.getAttribute("list")} option`)].map((o) => o.value);
    const needle = "mod00";
    ask.value = needle;
    ask.dispatchEvent(new Event("input", { bubbles: true }));
    await turn();
    partial = { needle, population, says: text(note), sample: uids.slice(0, 3) };
  }
  return { rail, missed, typed, levels, selectName: select?.getAttribute("aria-label") ?? null,
           linked: Boolean(link), open: fold?.open ?? null, hash: location.hash, partial };
})()
"""


@pytest.fixture(scope="module")
def walked(tmp_path_factory):
    both = pages.two_plane_run(tmp_path_factory.mktemp("ux1177-both"), pages.REVIEW_SHAPE)
    page = tmp_path_factory.mktemp("ux1177-page") / "report.html"
    import tools.bga_view as view

    view.export(str(both), str(page))
    with Browser(find_chrome()) as browser:
        return browser.measure(page.as_uri(), _WALK, 1440, 900)


@needs_browser
class TestJumpFindsWhatTheRailLists:
    def test_every_rail_entry_is_a_jump_hit(self, walked):
        assert len(walked["rail"]) >= 10, walked["rail"]
        assert walked["missed"] == [], walked["missed"]

    def test_the_words_a_reader_types_find_the_rail_entries(self, walked):
        typed = walked["typed"]
        assert "Elements · Level 3" in typed["level 3"], typed
        assert any(hit.startswith("Critical path") for hit in typed["critical"]), typed
        assert any(hit.startswith("Leaves") for hit in typed["leaves"]), typed

    def test_a_rail_press_on_a_fold_opens_it(self, walked):
        assert walked["linked"], walked["rail"]
        assert walked["open"] is True, walked

    def test_each_level_fold_names_its_level(self, walked):
        levels = walked["levels"]
        assert len(levels) == 8, levels
        assert len(set(levels)) == 8, levels
        assert "Elements · Level 3 · 1 level, 14 rows" in levels, levels

    def test_the_rows_shown_select_reads_as_a_phrase(self, walked):
        assert walked["selectName"] == "Rows shown: Level 1 elements", walked["selectName"]

    def test_a_partial_uid_says_how_many_it_matched(self, walked):
        partial = walked["partial"]
        assert partial is not None, walked
        count = int(partial["says"].split(" ")[0].replace(",", ""))
        assert 1 < count < partial["population"], partial
        assert partial["says"].startswith(f"{count} elements match \"{partial['needle']}\""), partial
