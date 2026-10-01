"""UX-1190 (styleguide §6e.8, §6d): a sortable header is a button.

On the 1,202-element two-plane page, `golden` and `macro_micro`: every
sortable header of a table over `SORTABLE_ABOVE` (10) rows holds a
`button.th-sort` that takes focus; a table that opens ranked shows that
ranking at rest (`aria-sort` and its glyph); and one press on a quantity
puts the population's maximum in row 1 - over all 1,202 rows where a
bound shows 25, read back by walking the pager. The heavy-binary page
(`UX-1182`) is left to the next wave.
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

_READ = r"""
(() => {
  for (const box of document.querySelectorAll("section.chapter")) {
    box.setAttribute("data-open", "true");
    for (const s of box.querySelectorAll(":scope > section[data-section]")) s.removeAttribute("hidden");
  }
  for (const fold of document.querySelectorAll("details")) fold.open = true;
  const own = (t) => [...(t.querySelector(":scope > thead > tr")?.children ?? [])];
  const rows = (t) => [...t.querySelector(":scope > tbody").children].filter((tr) => !tr.hidden);
  const raw = (tr, column) => [...tr.children].find((td) => td.getAttribute("data-column") === column)
    ?.getAttribute("data-raw") ?? "";
  const out = { heads: [], openings: [], presses: [] };
  for (const table of document.querySelectorAll("table[data-table]")) {
    if (Number(table.getAttribute("data-rows")) <= 10) continue;
    const key = table.getAttribute("data-table");
    for (const th of own(table)) {
      if (th.getAttribute("data-sortable") === "false") continue;
      const button = th.querySelector(":scope > button.th-sort");
      if (button) button.focus();
      out.heads.push({ key, column: th.getAttribute("data-column"),
                       focused: Boolean(button) && document.activeElement === button });
    }
    const tools = table.parentNode.querySelector(".table-tools");
    const opening = tools?.querySelector(".top-n")?.opening;
    const column = opening ? opening.split(":")[1] : "";
    if (column) {
      const th = own(table).find((h) => h.getAttribute("data-column") === column);
      out.openings.push({ key, column, sort: th?.getAttribute("aria-sort"),
                          glyph: th ? getComputedStyle(th.querySelector("button.th-sort"), "::after").content : null });
    }
    // One press on a quantity the table is not already ranked by.
    const th = own(table).find((h) => h.getAttribute("data-quantity") && !h.getAttribute("aria-sort")
      && h.querySelector("button.th-sort"));
    if (!th) continue;
    const pressed = th.getAttribute("data-column");
    th.querySelector("button.th-sort").click();
    const values = rows(table).map((tr) => raw(tr, pressed));
    const next = tools?.querySelector(".page-next");
    for (let guard = 0; next && !next.disabled && guard < 400; guard += 1) {
      next.click();
      values.push(...rows(table).map((tr) => raw(tr, pressed)));
    }
    out.presses.push({ key, column: pressed, sort: th.getAttribute("aria-sort"),
                       total: Number(table.getAttribute("data-rows")), values });
  }
  return out;
})()
"""


@pytest.fixture(scope="module")
def read(tmp_path_factory):
    import tools.bga_view as view

    into = tmp_path_factory.mktemp("sort-big")
    run = pages.two_plane_run(into, ("--layers", "20", "--width", "60"))
    page = into / "page.html"
    view.export(str(run), str(page))
    uris = {"big": page.as_uri(), **pages.pages(tmp_path_factory, "sort", ("golden", "macro_micro"))}
    with Browser(chrome) as browser:
        return {label: browser.measure(uri, _READ, 1440, 900) for label, uri in uris.items()}


@needs_browser
def test_every_sortable_header_of_a_long_table_takes_focus(read):
    for label, got in read.items():
        # golden has one table over ten rows (`provenance`, two columns).
        assert len(got["heads"]) >= 2, (label, got["heads"])
        missed = [h for h in got["heads"] if not h["focused"]]
        assert missed == [], (label, missed)


@needs_browser
def test_the_opening_ranking_shows_at_rest(read):
    keys = sorted(o["key"] for o in read["big"]["openings"])
    assert keys == ["binary_cost", "element_deltas", "elements", "wall_clock_share_us"], keys
    for label, got in read.items():
        for opening in got["openings"]:
            assert opening["sort"] == "descending" and "▼" in opening["glyph"], (label, opening)


@needs_browser
def test_one_press_on_a_quantity_puts_the_population_maximum_first(read):
    assert any(p["key"] == "elements" for p in read["big"]["presses"]), read["big"]["presses"]
    # golden's one long table has no quantity to press.
    assert read["macro_micro"]["presses"] and not read["golden"]["presses"], read["golden"]["presses"]
    for label, got in read.items():
        for press in got["presses"]:
            numbers = [float(v) for v in press["values"] if v != ""]
            assert press["sort"] == "descending", (label, press["key"], press["sort"])
            assert len(press["values"]) == press["total"], (label, press["key"], len(press["values"]))
            assert numbers and numbers[0] == max(numbers), (label, press["key"], press["column"], numbers[:5])
            assert numbers == sorted(numbers, reverse=True), (label, press["key"], press["column"])
