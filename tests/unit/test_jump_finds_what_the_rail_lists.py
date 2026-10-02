"""UX-1177: Jump and the rail agree on folds and presets.

Chromium on the 114-element two-plane run at 1440: every rail sub-entry
(a fold or a preset) is a Jump hit under its own text, a rail press on a
level fold leaves it open, the level folds' summaries read apart, the
Top-N select's name is a phrase, and a partial uid several elements
share says how many. On the heavy-binary page a Jump press lands an
element's card, a mounted binary row and a row past the bound at the
target's scroll margin, below its table's stuck tools for a row.
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

# A press from rest, then the target's top against its section's scroll margin (where a rail press
# lands): an element's card, a mounted binary row, and a binary the bound left unmounted.
_LAND = r"""
(async () => {
  const turn = (ms = 50) => new Promise((done) => setTimeout(done, ms));
  const jump = document.getElementById("jump");
  const press = (key) => {
    jump.value = key;
    jump.dispatchEvent(new Event("input", { bubbles: true }));
    [...document.querySelectorAll(".jump-hits button[data-jump]")].find((b) => b.getAttribute("data-jump") === key)
      ?.click();
  };
  const rows = [...document.querySelectorAll('table[data-table="binary_cost"] > tbody > tr[data-binary]')];
  const names = [];
  for (let i = 0; !names.length && i < 1000; i += 1) {
    jump.value = `lognormal-${String(i).padStart(3, "0")}`;
    jump.dispatchEvent(new Event("input", { bubbles: true }));
    names.push(...[...document.querySelectorAll(".jump-hits button[data-jump^='lognormal-']")]
      .map((b) => b.getAttribute("data-jump")).filter((name) => !document.querySelector(`[data-binary="${name}"]`)));
  }
  const key = { element: rows[rows.length - 1]?.getAttribute("data-element"),
                binary: rows[rows.length - 1]?.getAttribute("data-binary"), unmounted: names[0] }[KIND];
  // `UX-1260`: a rail-open drive opens the rail by its own toggle first and reads it open.
  const toc = document.querySelector(".toc");
  if (RAIL === "open" && toc?.getAttribute("data-folded") === "true") toc.querySelector(".toc-title")?.click();
  const rail = toc?.getAttribute("data-folded") ?? null;
  press(key);
  await turn(1200);
  const at = KIND === "element"
    ? document.getElementById(`element-${key.replace(/[^\w-]+/g, "-")}`)
    : document.querySelector(`${location.hash.split("~")[0]} [data-binary="${key}"]`);
  const section = parseFloat(getComputedStyle(at?.closest("section[data-section]") ?? document.body).scrollMarginTop);
  const tools = at?.tagName === "TR" ? at.closest("table")?.parentNode?.querySelector(":scope > .table-tools") : null;
  const stuck = tools && getComputedStyle(tools).position === "sticky" ? tools.getBoundingClientRect().bottom : 0;
  const table = at?.tagName === "TR" ? at.closest("table") : null;
  const shown = table ? [...table.querySelectorAll(":scope > tbody > tr")].filter((r) => r.offsetParent).length : null;
  return { kind: KIND, rail, key, stuck: Math.round(stuck), shown, top: Math.round(at?.getBoundingClientRect().top ?? -1),
           margin: Math.round(Math.max(section, stuck)), section: Math.round(section),
           tag: at?.tagName ?? null, hash: location.hash.split("~")[0] };
})()
"""


@pytest.fixture(scope="module")
def landed(tmp_path_factory):
    into = tmp_path_factory.mktemp("ux1177-heavy")
    uri = pages.export_uri(pages.heavy_binary_run(into), into / "page")
    drives = [(kind, "as-found") for kind in ("element", "binary", "unmounted")]
    drives += [("binary", "open"), ("unmounted", "open")]
    with Browser(find_chrome()) as browser:
        return [
            browser.measure(uri, f"const KIND = {kind!r}; const RAIL = {rail!r};" + _LAND, 1440, 900) | {"drive": rail}
            for kind, rail in drives
        ]


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

    def test_a_jump_lands_on_its_target(self, landed):
        for target in landed:
            assert target["key"] and target["tag"], landed
            assert abs(target["top"] - target["margin"]) <= 8, str(target)
        # `UX-1225`: a binary lands on its own table filtered to it, so its tools sit above the row, not over it.
        assert all(t["hash"] == "#by_binary" for t in landed if t["tag"] == "TR"), landed
        rows = [t for t in landed if t["tag"] == "TR"]
        assert rows, landed
        # `UX-1235`: the stuck tools are measured, not the hash: their bottom clears the row, one row is shown.
        assert all(0 < t["stuck"] <= t["top"] + 1 and t["shown"] == 1 for t in rows), rows

    def test_a_binary_lands_below_the_tools_with_the_rail_open_at_1440(self, landed):
        """`UX-1260`: the rail read open before the press, the row under the stuck tools, one row shown."""
        opened = [t for t in landed if t["drive"] == "open"]
        assert len(opened) == 2 and all(t["rail"] == "false" for t in opened), opened
        for t in opened:
            assert t["tag"] == "TR" and t["hash"] == "#by_binary" and t["shown"] == 1, t
            assert abs(t["top"] - max(t["section"], t["stuck"])) <= 8 and 0 < t["stuck"] <= t["top"] + 1, t
