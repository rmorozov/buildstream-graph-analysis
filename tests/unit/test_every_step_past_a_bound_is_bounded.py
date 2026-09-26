"""UX-1032: the §3k census presses every step control at the largest size class.

Measured on the 4,002-element run (`bga gen-synthetic --seed 1 --layers
20 --width 200 --store --runs 30`), exported, 1440x900, every chapter
open, every `<details>` open, then every step control pressed:

```text
largest table at rest     40 rows (TABLE_OPENS_BOUNDED_ABOVE)
after "All rows"          4,002 rows (elements)
largest reveal at rest    6 + 3 names
after "+N more"           3,625 names, one 72,703-character run
largest JSON door         3,592,666 characters (elements)
```

At rest all three §3k violations pass - a table opens on its bound, a
reveal shows its head and tail, a JSON door is closed. Only pressing
the steps finds them, which is why this census presses every one of
them **ten times**: a step that replaces its mounted window passes at
one press and fails at the tenth if it silently starts appending.

The ceilings below are this file's own literals, not imports from the
constants they audit (`ALL_ROWS_CEILING`, `REVEAL_STEP`,
`JSON_DOOR_CHAR_CAP`) - a guard that read the production bound would
pass whatever that bound happened to be.
"""
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

import pages
from browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

#: styleguide §3k's three ceilings, at the largest size class.
MOUNTED_ROWS_MAX = 200
NAMES_MAX = 60
TEXT_CHARS_MAX = 20_000

#: Every step control this census knows how to press, generically -
#: by the class each fix names its control, not by re-implementing what
#: any of them does.
_CENSUS = r"""
(() => {
  for (const box of document.querySelectorAll("section.chapter")) {
    box.setAttribute("data-open", "true");
  }
  for (const fold of document.querySelectorAll("details")) fold.open = true;

  // A table's own mounted rows: direct `<tr>` children of its own
  // `<tbody>` that are not `hidden` - `UX-532`'s own-row rule, read
  // without importing `tables.js`.
  const mountedRows = (table) => {
    const tbody = [...table.children].find((c) => c.tagName === "TBODY");
    if (!tbody) return 0;
    return [...tbody.children].filter(
      (tr) => tr.tagName === "TR" && !tr.hidden).length;
  };

  const tables = [];
  for (const table of document.querySelectorAll("table[data-table]")) {
    const tools = table.previousElementSibling;
    const select = tools?.querySelector?.(".top-n");
    const pager = tools?.querySelector?.(".table-pager");
    const next = pager?.querySelector(".page-next");
    const allOption = select?.querySelector('option[value=""]');
    const readings = [mountedRows(table)];
    // Every step this table offers: "All rows" where it is offered at
    // all, then the paging step ten times over.
    if (allOption) {
      select.value = "";
      select.dispatchEvent(new Event("change"));
      readings.push(mountedRows(table));
    }
    if (next) {
      for (let i = 0; i < 10; i += 1) {
        next.click();
        readings.push(mountedRows(table));
      }
    }
    tables.push({ key: table.getAttribute("data-table"),
                 offersAllRows: Boolean(allOption), readings,
                 max: Math.max(...readings) });
  }

  // Read structurally, not by the fix's own class name: `list-head`
  // and `list-tail` are read at rest, once, and how many *more* names
  // either now holds - plus whatever a `list-middle` (if there is one)
  // holds - is "how many of the folded middle are mounted now". A
  // reveal that dumps the whole middle into `list-head` (the shape
  // this census exists to catch) reads as a middle count too, through
  // the growth of `list-head` past its rest reading.
  const tokens = (text) => {
    const t = (text || "").replace(/^,\s*/, "").trim();
    return t ? t.split(",").map((s) => s.trim()).filter(Boolean).length : 0;
  };
  const reveals = [];
  for (const list of document.querySelectorAll(".bounded-list")) {
    const headEl = list.querySelector(".list-head");
    const middleEl = list.querySelector(".list-middle");
    const tailEl = list.querySelector(".list-tail");
    const restHead = tokens(headEl?.textContent);
    const restTail = tokens(tailEl?.textContent);
    const more = list.querySelector("button.fold-more");
    const mountedMiddle = () => Math.max(0,
      (tokens(headEl?.textContent) - restHead) + tokens(middleEl?.textContent)
      + Math.max(0, restTail - tokens(tailEl?.textContent)));
    const readings = [mountedMiddle()];
    for (let i = 0; i < 10 && more && !more.hidden; i += 1) {
      more.click();
      readings.push(mountedMiddle());
    }
    reveals.push({ items: Number(list.getAttribute("data-items")),
                  readings, max: Math.max(...readings) });
  }

  const doors = [];
  for (const button of document.querySelectorAll("button.json-toggle")) {
    const key = button.getAttribute("data-json-toggle");
    const section = button.closest("section[data-section]");
    const readings = [];
    for (let i = 0; i < 10; i += 1) {
      button.click();
      const pre = section.querySelector("[data-raw-json] pre");
      readings.push(pre ? pre.textContent.length : 0);
      button.click();
    }
    doors.push({ key, readings, max: Math.max(...readings, 0) });
  }

  return { tables, reveals, doors };
})()
"""


@pytest.fixture(scope="module")
def browser():
    with Browser(chrome) as opened:
        yield opened


@pytest.fixture(scope="module")
def census(browser, tmp_path_factory):
    """The 4,002-element run, every chapter and fold open, every step
    control pressed ten times."""
    into = tmp_path_factory.mktemp("u1032")
    uri = pages.export_uri(pages.xl_run(into), into, name="xl.html")
    return browser.measure(uri, _CENSUS, 1440, 900)


@needs_browser
@pytest.mark.large
class TestTheCensusReadsSomething:
    """Non-vacuity: a census over nothing passes every clause below."""

    def test_it_found_tables(self, census):
        assert census["tables"], "no table on the page - reading nothing"

    def test_it_found_reveals(self, census):
        assert census["reveals"], "no bounded-list reveal on the page"

    def test_it_found_json_doors(self, census):
        assert census["doors"], "no 'view as JSON' toggle on the page"

    def test_at_least_one_table_is_pressed_past_one_reading(self, census):
        assert any(len(t["readings"]) > 1 for t in census["tables"]), (
            "no table offered a step to press - the census pressed nothing")

    def test_at_least_one_reveal_is_pressed_past_one_reading(self, census):
        assert any(len(r["readings"]) > 1 for r in census["reveals"]), (
            "no reveal offered a step to press - the census pressed nothing")

    def test_at_least_one_door_reaches_the_cap(self, census):
        """The door that broke this: `elements`, 3,592,666 characters.
        A door that never reaches the cap does not prove the cap holds
        at the size that matters."""
        assert any(d["max"] == TEXT_CHARS_MAX for d in census["doors"]), (
            [d["max"] for d in census["doors"]])


@needs_browser
@pytest.mark.large
class TestEveryTableStaysBounded:
    def test_no_table_ever_mounts_past_the_bound(self, census):
        over = [(t["key"], t["readings"]) for t in census["tables"]
                if t["max"] > MOUNTED_ROWS_MAX]
        assert not over, (
            f"table(s) mounted more than {MOUNTED_ROWS_MAX} rows at some "
            f"step: {over}")

    def test_all_rows_is_not_offered_past_the_ceiling(self, census):
        """The other half of the same rule: a table large enough to
        need ten presses to page through must not also offer the whole
        population in one step."""
        wrong = [t["key"] for t in census["tables"]
                 if t["offersAllRows"] and t["max"] > MOUNTED_ROWS_MAX]
        assert not wrong, (
            f"table(s) offer 'All rows' and mount past the bound: {wrong}")


@needs_browser
@pytest.mark.large
class TestEveryRevealStaysBounded:
    def test_no_reveal_ever_mounts_past_the_bound(self, census):
        over = [(r["items"], r["readings"]) for r in census["reveals"]
                if r["max"] > NAMES_MAX]
        assert not over, (
            f"reveal(s) mounted more than {NAMES_MAX} names between the "
            f"head and tail at some step: {over}")


@needs_browser
@pytest.mark.large
class TestEveryJsonDoorStaysBounded:
    def test_no_door_ever_draws_past_the_cap(self, census):
        over = [(d["key"], d["max"]) for d in census["doors"]
                if d["max"] > TEXT_CHARS_MAX]
        assert not over, (
            f"door(s) drew more than {TEXT_CHARS_MAX} characters: {over}")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
