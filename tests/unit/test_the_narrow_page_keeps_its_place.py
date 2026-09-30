"""UX-1178: the compact page keeps its layout, and Expand all and the rail keep the reader's place.

At 390 a stacked table (rows that print their own `::before` labels)
drew its `thead` as well - 87 px on `restructuring`, 204 px on
`serialization_point_risks` (macro_micro) - and a code name broke at its
hyphen. After Expand all the current chapter sat 456-686 px under the
top, and a rail press on the chapter you were on pushed an entry.
`binary_cost` quantity cells ("695 ms") break across lines at 320.
"""

import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

import pages

from tests.browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

#: One line at the compact type size.
LINE_PX = 24

_OPEN = r"""
const open = async () => {
  for (const box of document.querySelectorAll("section.chapter")) {
    box.setAttribute("data-open", "true");
    for (const s of box.querySelectorAll(":scope > section[data-section]")) s.removeAttribute("hidden");
  }
  document.querySelectorAll("details").forEach((d) => { d.open = true; });
  await new Promise((done) => setTimeout(done, 500));
};
"""

_LAYOUT = (
    _OPEN
    + r"""
(async () => {
  await open();
  const lines = (node) => {
    const range = document.createRange();
    range.selectNodeContents(node);
    return new Set([...range.getClientRects()].map((r) => Math.round(r.top))).size;
  };
  const stacked = [...document.querySelectorAll("table")].filter((t) => t.matches(":has(td table)"))
    .map((t) => ({
      id: t.closest("[data-section]")?.getAttribute("data-section"),
      head: t.querySelector(":scope > thead")?.getBoundingClientRect().height ?? 0,
      width: Math.round(t.getBoundingClientRect().width),
      box: Math.round(t.parentElement.getBoundingClientRect().width),
    }));
  const code = [...document.querySelectorAll("main code")]
    .filter((c) => !/\s/.test(c.textContent.trim()) && lines(c) > 1)
    .map((c) => c.textContent.slice(0, 40));
  const cells = [...document.querySelectorAll('[data-section="binary_cost"] td.num')];
  return { stacked, code, cells: cells.length,
           wrapped: cells.filter((c) => lines(c) > 1).map((c) => c.textContent) };
})()
"""
)

_TOP = (
    _OPEN
    + r"""
(async () => {
  const wait = (ms) => new Promise((done) => setTimeout(done, ms));
  const rows = [...document.querySelectorAll(".toc li[data-chapter]")];
  const id = rows[Math.min(2, rows.length - 1)].getAttribute("data-chapter");
  const press = () => document.querySelector(`[data-toc-chapter="${id}"]`).click();
  const before = history.length;
  press();
  await wait(300);
  const pushed = history.length - before;
  press();
  await wait(300);
  const again = history.length - before;
  const all = [...document.querySelectorAll("button")].find((b) => b.textContent.trim() === "Expand all");
  all.click();
  await wait(1500);
  const box = document.querySelector(`section.chapter[data-chapter="${id}"]`);
  const margin = parseFloat(getComputedStyle(box).scrollMarginTop) || 0;
  return { id, pushed, again, off: box.getBoundingClientRect().top - margin };
})()
"""
)


@pytest.fixture(scope="module")
def uris(tmp_path_factory):
    return pages.pages(tmp_path_factory, "narrow")


@pytest.fixture(scope="module")
def browser():
    if chrome is None:
        pytest.skip(NO_BROWSER)
    with Browser(chrome) as opened:
        yield opened


@needs_browser
@pytest.mark.parametrize("label", sorted(pages.FIXTURES))
def test_a_stacked_table_shows_no_header_and_fills_its_box(browser, uris, label):
    got = browser.measure(uris[label], _LAYOUT, width=390, height=844)
    if label == "macro_micro":
        assert got["stacked"], "macro_micro has stacked tables"
    for table in got["stacked"]:
        assert table["head"] == 0, table
        assert table["width"] == table["box"], table


@needs_browser
@pytest.mark.parametrize("label", sorted(pages.FIXTURES))
def test_no_code_name_breaks_inside_a_token(browser, uris, label):
    got = browser.measure(uris[label], _LAYOUT, width=390, height=844)
    assert got["code"] == []


@needs_browser
@pytest.mark.parametrize("width", [390, 320])
def test_no_binary_cost_quantity_wraps(browser, uris, width):
    got = browser.measure(uris["macro_micro"], _LAYOUT, width=width, height=844)
    assert got["cells"] > 0
    assert got["wrapped"] == []


@needs_browser
@pytest.mark.parametrize("width", [390, 1440])
@pytest.mark.parametrize("label", sorted(pages.FIXTURES))
def test_expand_all_keeps_the_current_chapter_at_the_top(browser, uris, label, width):
    got = browser.measure(uris[label], _TOP, width=width, height=844)
    assert abs(got["off"]) <= LINE_PX, got


@needs_browser
@pytest.mark.parametrize("label", sorted(pages.FIXTURES))
def test_a_press_on_the_current_chapter_adds_no_entry(browser, uris, label):
    got = browser.measure(uris[label], _TOP, width=1440, height=844)
    assert got["pushed"] <= 1, got
    assert got["again"] == got["pushed"], got
