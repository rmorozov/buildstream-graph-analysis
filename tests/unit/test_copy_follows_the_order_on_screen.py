"""UX-1211: Copy writes a sorted table's rows in the order the table shows them.

Chromium at 1440 on golden, `macro_micro` and the 1,202-element two-plane
run: every table with a sortable head and a Copy control, bounded to its
first Rows-shown option where it has one, sorted by one head - the task
table by Duration ascending and the elements table by Unweighted depth on
the big page. Copy's JSON rows, read as published values, equal the shown
rows' in order; on the big page a filter as well.

Styleguide §4c.
"""

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

needs_browser = pytest.mark.skipif(find_chrome() is None, reason=NO_BROWSER)

_COPY = r"""
(async () => {
  let copied = null;
  Object.defineProperty(navigator, "clipboard", { value: { writeText: async (t) => { copied = t; } }, configurable: true });
  localStorage.removeItem("bga.copy-format");
  const turn = (ms = 50) => new Promise((done) => setTimeout(done, ms));
  document.querySelectorAll("section.chapter[data-open]").forEach((n) => n.setAttribute("data-open", "true"));
  await turn(100);
  // As `rowJson` reads a cell: a published value, a number as a number.
  const value = (td) => {
    if (!td) return null;
    const raw = td.getAttribute("data-raw");
    return raw === "true" || raw === "false" ? raw === "true" : raw !== "" && !Number.isNaN(Number(raw)) ? Number(raw) : raw;
  };
  const read = async (table) => {
    const copy = table.parentNode.querySelector(".table-tools .copy-rows");
    copy.click();
    await turn();
    const rows = JSON.parse(copied ?? "[]");
    const keys = Object.keys(rows[0] ?? {});
    // `UX-1207`: a map's `key`/`value` copy under the header's words; the copy's columns are the table's, in order.
    const columns = [...table.querySelectorAll(":scope > thead th")].map((th) => th.getAttribute("data-column"));
    const column = (name, at) => (keys.length === columns.length ? columns[at] : name);
    const print = (get) => JSON.stringify(keys.map((name, at) => get(name, column(name, at))));
    const shown = [...table.querySelector(":scope > tbody").children]
      .filter((tr) => !tr.hidden && tr.className !== "fold-row")
      .map((tr) => print((name, key) => value(tr.querySelector(`:scope > td[data-column="${key}"]`))));
    return { copied: rows.map((row) => print((name) => row[name] ?? null)), shown };
  };
  const out = [];
  for (const table of document.querySelectorAll("table[data-table]")) {
    const name = table.getAttribute("data-table");
    const heads = [...table.querySelectorAll(":scope > thead th")].filter((th) => th.querySelector("button.th-sort"));
    if (!heads.length || !table.parentNode.querySelector(".table-tools .copy-rows")) continue;
    const preset = table.parentNode.querySelector("select.top-n");
    const bound = preset && [...preset.options].find((option) => option.value);
    if (bound && preset.value !== bound.value) {
      preset.value = bound.value;
      preset.dispatchEvent(new Event("change", { bubbles: true }));
      await turn();
    }
    const before = (await read(table)).shown;
    const head = heads.find((th) => th.getAttribute("data-column") === PICK[name]?.[0]) ?? heads[heads.length - 1];
    const want = PICK[name]?.[1];
    for (let press = 0; press < 2 && (press === 0 || (want && head.getAttribute("aria-sort") !== want)); press += 1) {
      head.querySelector("button.th-sort").click();
      await turn();
    }
    const sorted = await read(table);
    const row = { name, bound: bound?.value ?? null, column: head.getAttribute("data-column"),
                  sort: head.getAttribute("aria-sort"), moved: JSON.stringify(before) !== JSON.stringify(sorted.shown),
                  ...sorted };
    const box = FILTER && table.parentNode.querySelector("input.table-filter");
    if (box) {
      box.value = FILTER;
      box.dispatchEvent(new Event("input", { bubbles: true }));
      await turn();
      row.filtered = await read(table);
    }
    out.push(row);
  }
  return out;
})()
"""

#: The Acceptance's two sorts on the big page: the task table by Duration ascending, the elements by depth.
_PICK = {"wall_clock_share_us": ["duration_us", "ascending"], "elements": ["unweighted_depth", None]}


def _probe(text_filter=""):
    return _COPY.replace("PICK", json.dumps(_PICK)).replace("FILTER", json.dumps(text_filter))


@pytest.fixture(scope="module")
def seen(tmp_path_factory):
    uris = pages.pages(tmp_path_factory, prefix="ux1211", labels=["golden", "macro_micro"])
    import tools.bga_view as view

    run = pages.two_plane_run(tmp_path_factory.mktemp("ux1211-big"), ("--layers", "20", "--width", "60"))
    page = tmp_path_factory.mktemp("ux1211-big-page") / "report.html"
    view.export(str(run), str(page))
    with Browser(find_chrome()) as browser:
        out = {label: browser.measure(uri, _probe(), 1440, 900) for label, uri in uris.items()}
        out["big"] = browser.measure(page.as_uri(), _probe("mod"), 1440, 900)
        return out


@needs_browser
class TestCopyFollowsTheOrderOnScreen:
    @pytest.mark.parametrize("label", ["golden", "macro_micro", "big"])
    def test_copy_writes_the_shown_rows_in_their_order(self, seen, label):
        assert seen[label], label
        for row in seen[label]:
            assert row["sort"] and row["shown"], row["name"]
            assert row["copied"] == row["shown"], (label, row["name"], row["column"], row["sort"])

    def test_a_filtered_copy_starts_with_the_shown_rows(self, seen):
        for row in seen["big"]:
            got = row.get("filtered")
            if got is None:
                continue
            assert got["shown"] and got["copied"][: len(got["shown"])] == got["shown"], row["name"]

    def test_the_acceptance_sorts_moved_a_bounded_table(self, seen):
        rows = {row["name"]: row for row in seen["big"]}
        task, elements = rows["wall_clock_share_us"], rows["elements"]
        assert task["column"] == "duration_us" and task["sort"] == "ascending" and task["moved"], task["name"]
        assert elements["column"] == "unweighted_depth" and elements["moved"], elements["name"]
        assert task["bound"] and elements["bound"], (task["bound"], elements["bound"])
