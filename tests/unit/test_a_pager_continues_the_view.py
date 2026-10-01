"""UX-1185 (styleguide §3k): a pager continues the view.

On the 1,202-element two-plane page, every paged table's pages walk its
opening ranking: page 2's first row is rank 26 of the opening sort, the
rows over all pages are the whole population in that order, the copy
label counts the mounted rows at every step, and a reload with the
fragment lands on the same page. Editing or clearing the filter after a
step returns to the first rows, with `p.` gone from the link. On `golden` and `macro_micro` a table
of at most `UNROLL_AT` (80) rows opens whole - `macro_micro`'s 71-row
`binary_cost` among them. The heavy-binary page (`UX-1182`) is left to
the next wave.
UX-1197: Top 10, a filter, Next and a sort keep 10-row pages with the
select reading Top 10, and so does the copied link reloaded; each step
changes the live text; no two pager or sort buttons share a name.
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
    const column = table.querySelector("thead th[aria-sort]")?.getAttribute("data-column");
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
                 position: tools.querySelector(".badge").textContent, first: pagesSeen[2][0] };
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
    const position = tools && tools.querySelector(".table-pager") && tools.querySelector(".badge");
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


#: A filter, Next, then the filter edited and cleared: the pager position, the badge and the link each time.
_EDITED = (
    r"""
(async () => {
  """
    + _OPEN
    + r"""
  const turn = () => new Promise((done) => setTimeout(done, 50));
  const tools = document.querySelector('table[data-table="elements"]').parentNode.querySelector(".table-tools");
  const box = tools.querySelector("input.table-filter");
  const read = async () => {
    await turn();
    return { badge: tools.querySelector(".badge").textContent, hash: location.hash };
  };
  const type = (text) => { box.value = text; box.dispatchEvent(new Event("input", { bubbles: true })); };
  type("layer1");
  tools.querySelector(".page-next").click();
  const stepped = await read();
  type("layer12/");
  const edited = await read();
  type("");
  return { stepped, edited, cleared: await read() };
})()
"""
)


@pytest.fixture(scope="module")
def edited(browser, big):
    return browser.measure(big, _EDITED, 1440, 900)


@needs_browser
def test_a_filter_edit_returns_the_pager_to_its_first_rows(edited):
    # `UX-1197`: the badge, the one live region, carries the window.
    assert edited["stepped"]["badge"].startswith("rows 26-50 of "), edited["stepped"]
    assert "p." in pages.view_query(edited["stepped"]["hash"]), edited["stepped"]
    for step, said in (("edited", "25 of 60 matched"), ("cleared", "25 of 1,202")):
        assert edited[step]["badge"] == said, (step, edited[step])
        assert "p." not in pages.view_query(edited[step]["hash"]), (step, edited[step])


#: `UX-1197`: Top 10, a filter, Next, a sort and Next again - the rows, the select and the live text at each step.
_CONTINUED = (
    r"""
(async () => {
  """
    + _OPEN
    + r"""
  const turn = () => new Promise((done) => setTimeout(done, 80));
  const table = document.querySelector('table[data-table="elements"]');
  const tools = table.parentNode.querySelector(".table-tools");
  const select = tools.querySelector("select.top-n");
  const read = () => ({ rows: [...table.querySelector("tbody").children].filter((tr) => !tr.hidden).length,
                        select: select.selectedIndex < 0 ? null : select.options[select.selectedIndex].textContent,
                        status: tools.querySelector("[role=status].badge").textContent, hash: location.hash });
  const out = { options: [...select.options].map((o) => o.textContent) };
  select.value = [...select.options].find((o) => o.textContent === "Top 10 rows").value;
  select.dispatchEvent(new Event("change", { bubbles: true }));
  const box = tools.querySelector("input.table-filter");
  box.value = "layer12/";
  box.dispatchEvent(new Event("input", { bubbles: true }));
  out.top = read();
  tools.querySelector(".page-next").click();
  out.next = read();
  table.querySelector('th[data-column="downstream_count"] button').click();
  out.sorted = read();
  tools.querySelector(".page-next").click();
  await turn();
  out.again = read();
  return out;
})()
"""
)

_RELOAD_READ = r"""
(() => {
  const table = document.querySelector('table[data-table="elements"]');
  const select = table.parentNode.querySelector(".table-tools select.top-n");
  return { rows: [...table.querySelector("tbody").children].filter((tr) => !tr.hidden).length,
           select: select.selectedIndex < 0 ? null : select.options[select.selectedIndex].textContent,
           sort: table.querySelector("thead th[aria-sort]")?.getAttribute("data-column") };
})()
"""

#: Every pager and sort button's accessible name, over every chapter opened.
_NAMES = (
    r"""
(() => {
  """
    + _OPEN
    + r"""
  const name = (b) => b.getAttribute("aria-label") || b.textContent.trim();
  return [...document.querySelectorAll(".table-pager button, button.th-sort")].map(name);
})()
"""
)


@pytest.fixture(scope="module")
def continued(browser, big):
    out = browser.measure(big, _CONTINUED, 1440, 900)
    out["reloaded"] = browser.measure(big + "?reload" + out["again"]["hash"], _RELOAD_READ, 1440, 900)
    out["names"] = browser.measure(big, _NAMES, 1440, 900)
    out["old"] = browser.measure(big + "?old#elements~n.elements=10:downstream_count", _RELOAD_READ, 1440, 900)
    return out


@needs_browser
def test_the_bound_is_every_page_s_size_and_the_select_keeps_it(continued):
    assert "Top 10 rows" in continued["options"] and not any(" by " in o for o in continued["options"]), continued
    for step in ("top", "next", "sorted", "again"):
        assert continued[step]["rows"] == 10 and continued[step]["select"] == "Top 10 rows", (step, continued[step])


@needs_browser
def test_the_link_carries_the_bound_the_filter_and_the_sort(continued):
    assert continued["reloaded"] == {"rows": 10, "select": "Top 10 rows", "sort": "downstream_count"}, continued
    # A link from before the bound-only select: `Top 10 by Downstream count` is Top 10 and that sort.
    assert continued["old"] == {"rows": 10, "select": "Top 10 rows", "sort": "downstream_count"}, continued["old"]


@needs_browser
def test_a_step_and_a_sort_change_the_live_text(continued):
    said = [continued[step]["status"] for step in ("top", "next", "sorted", "again")]
    assert len(set(said)) == 4, said
    assert said[1].startswith("rows 11-20 of 60") and "Downstream count" in said[2], said


@needs_browser
def test_no_two_pager_or_sort_buttons_share_a_name(continued):
    names = continued["names"]
    twice = {name for name in names if names.count(name) > 1}
    assert len(names) > 20 and not twice, sorted(twice)
    # `UX-1197` follow-up: the task table's tools are named for its tasks, never for its share column.
    assert "Duration, sort: Tasks" in names and not [n for n in names if n.endswith(": Wall-clock share")], names


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
