"""UX-1185 (styleguide §3k): a pager continues the view.

On the 1,202-element two-plane page, every paged table's pages walk its
opening ranking: page 2's first row is rank 26 of the opening sort, the
rows over all pages are the whole population in that order, the copy
label counts the mounted rows at every step, and a reload with the
fragment lands on the same page. On `golden` and `macro_micro` a table
of at most `UNROLL_AT` (80) rows opens whole - `macro_micro`'s 71-row
`binary_cost` among them. The heavy-binary page (`UX-1182`) is left to
the next wave.
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

_OPEN = 'for (const b of document.querySelectorAll("section.chapter")) b.setAttribute("data-open", "true");'

#: Every paged table walked to its end; the fragment read after two steps of the first.
_WALK = (
    r"""
(async () => {
  """
    + _OPEN
    + r"""
  const out = [];
  let hash = null;
  for (const table of document.querySelectorAll("table[data-table]")) {
    const tools = table.parentNode.querySelector(".table-tools");
    const pager = tools && tools.querySelector(".table-pager");
    if (!pager) continue;
    const preset = tools.querySelector(".top-n");
    const column = (preset.opening || "").split(":")[1];
    const mounted = () => [...table.querySelector("tbody").children].filter((tr) => tr.tagName === "TR" && !tr.hidden);
    const value = (tr) => Number([...tr.children].find((td) => td.getAttribute("data-column") === column)
      ?.getAttribute("data-raw"));
    const copy = () => tools.querySelector(".copy-rows").textContent;
    const pagesSeen = [mounted().map(value)];
    const labels = [[copy(), mounted().length]];
    const next = pager.querySelector(".page-next");
    for (let guard = 0; !next.disabled && guard < 400; guard += 1) {
      next.click();
      pagesSeen.push(mounted().map(value));
      labels.push([copy(), mounted().length]);
      if (hash === null && pagesSeen.length === 3) {
        await new Promise((done) => setTimeout(done, 50));
        hash = { key: table.getAttribute("data-table"), hash: location.hash,
                 position: tools.querySelector(".page-position").textContent, first: pagesSeen[2][0] };
      }
    }
    out.push({ key: table.getAttribute("data-table"), column, badge: tools.querySelector(".badge").textContent,
               pages: pagesSeen, labels });
  }
  return { tables: out, hash };
})()
"""
)

_RELOADED = (
    r"""
(() => {
  """
    + _OPEN
    + r"""
  const out = {};
  for (const table of document.querySelectorAll("table[data-table]")) {
    const tools = table.parentNode.querySelector(".table-tools");
    const position = tools && tools.querySelector(".page-position");
    if (position) out[table.getAttribute("data-table")] = position.textContent;
  }
  return out;
})()
"""
)

#: At rest: every table's own rows, mounted and in all.
_AT_REST = (
    r"""
(() => {
  """
    + _OPEN
    + r"""
  return [...document.querySelectorAll("table[data-table]")].map((table) => {
    const rows = [...table.querySelector("tbody").children].filter((tr) => tr.tagName === "TR");
    const tools = table.parentNode.querySelector(".table-tools");
    const badge = tools && tools.querySelector(".badge");
    const whole = badge ? /of ([\d,]+)/.exec(badge.textContent) : null;
    return { key: table.getAttribute("data-table"), mounted: rows.filter((tr) => !tr.hidden).length,
             total: whole ? Number(whole[1].replace(/,/g, "")) : rows.length };
  });
})()
"""
)


@pytest.fixture(scope="module")
def browser():
    with Browser(chrome) as opened:
        yield opened


@pytest.fixture(scope="module")
def big(tmp_path_factory):
    import tools.bga_view as view

    into = tmp_path_factory.mktemp("pager-big")
    run = pages.two_plane_run(into, ("--layers", "20", "--width", "60"))
    page = into / "page.html"
    view.export(str(run), str(page))
    return page.as_uri()


@pytest.fixture(scope="module")
def walked(browser, big):
    return browser.measure(big, _WALK, 1440, 900)


@needs_browser
def test_four_tables_page_the_population(walked):
    keys = sorted(t["key"] for t in walked["tables"])
    assert keys == ["binary_cost", "element_deltas", "elements", "wall_clock_share_us"], keys


@needs_browser
def test_page_two_is_rank_twenty_six_and_the_pages_walk_the_ranking(walked):
    for table in walked["tables"]:
        whole = [v for page in table["pages"] for v in page]
        total = int(table["badge"].split(" of ")[1].replace(",", ""))
        assert len(whole) == total == 1202, (table["key"], len(whole), total)
        ranked = sorted(whole, reverse=True)
        assert table["pages"][1][0] == ranked[len(table["pages"][0])], (table["key"], table["pages"][1][:3])
        assert whole == ranked, f"{table['key']}: the pages leave the {table['column']} ranking"
        assert len(table["pages"][0]) == len(table["pages"][1]) == 25, table["key"]


@needs_browser
def test_the_copy_label_counts_the_mounted_rows(walked):
    for table in walked["tables"]:
        for label, mounted in table["labels"]:
            assert label.startswith(f"Copy {mounted} row"), (table["key"], label, mounted)


@needs_browser
def test_a_reload_with_the_fragment_keeps_the_page(browser, big, walked):
    moved = walked["hash"]
    assert moved and moved["position"] == "rows 51-75 of 1,202", moved
    assert "p." in pages.view_query(moved["hash"]), moved["hash"]
    # A query string makes it a new document; a hash alone is a same-document navigation.
    reloaded = browser.measure(big + "?reload" + moved["hash"], _RELOADED, 1440, 900)
    assert reloaded[moved["key"]] == moved["position"], reloaded


@pytest.fixture(scope="module")
def at_rest(browser, tmp_path_factory):
    uris = pages.pages(tmp_path_factory, "pager", ("golden", "macro_micro"))
    return {label: browser.measure(uri, _AT_REST, 1440, 900) for label, uri in uris.items()}


@needs_browser
def test_eighty_rows_or_fewer_open_whole(at_rest):
    for label, tables in at_rest.items():
        cut = [t for t in tables if t["total"] <= 80 and t["mounted"] < t["total"]]
        assert cut == [], (label, cut)
    binary = [t for t in at_rest["macro_micro"] if t["key"] == "binary_cost"]
    assert binary and binary[0]["mounted"] == binary[0]["total"] == 71, binary
