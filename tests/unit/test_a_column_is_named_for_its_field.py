"""UX-1184 (styleguide §6e.2): a column named for a quantity is that quantity.

No two table columns drawn from different source fields share a title,
and the task table's share of the window reads "Wall-clock share" with a
lead linking the element table. A column's field is its `data-column`
(`element_uid` is `element`), a map's value column is the map itself;
a map's key column names its population, not a field, and is skipped.
Chromium on the 1,202-element two-plane page and `macro_micro`, at 1440.
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
  const heads = [];
  for (const table of document.querySelectorAll("table[data-table]")) {
    for (const th of table.querySelectorAll(":scope > thead th[data-column]")) {
      const column = th.getAttribute("data-column");
      if (column === "key") continue;
      const field = column === "value" ? table.getAttribute("data-table").split(".").pop()
        : column.replace(/_uid$/, "");
      const title = th.textContent.replace(/[▲▼↑↓▾▸]/g, "").trim();
      if (title) heads.push([title, field]);
    }
  }
  const share = document.querySelector('#wall_clock_share_us table[data-table="wall_clock_share_us"]');
  const lead = document.querySelector('#wall_clock_share_us p.section-lead');
  return {
    heads,
    shareHead: share?.querySelector('thead th[data-column="value"]')?.textContent.trim() ?? null,
    lead: lead?.textContent ?? null,
    leadLink: lead?.querySelector("a")?.getAttribute("href") ?? null,
  };
})()
"""


@pytest.fixture(scope="module")
def looked(tmp_path_factory):
    uris = pages.pages(tmp_path_factory, prefix="ux1184", labels=["macro_micro"])
    run = pages.two_plane_run(tmp_path_factory.mktemp("ux1184-big"), ("--layers", "20", "--width", "60"))
    page = tmp_path_factory.mktemp("ux1184-big-page") / "report.html"
    import tools.bga_view as view

    view.export(str(run), str(page))
    uris["big"] = page.as_uri()
    with Browser(find_chrome()) as browser:
        return {label: browser.measure(uri, _LOOK, 1440, 900) for label, uri in uris.items()}


@needs_browser
class TestAColumnIsNamedForItsField:
    def test_no_two_fields_share_a_title(self, looked):
        for label, out in looked.items():
            fields = {}
            for title, field in out["heads"]:
                fields.setdefault(title, set()).add(field)
            assert len(out["heads"]) > 40, (label, len(out["heads"]))
            shared = {title: sorted(f) for title, f in fields.items() if len(f) > 1}
            assert not shared, f"{label}: one title, several fields: {shared}"

    def test_the_share_says_it_is_a_share(self, looked):
        for label, out in looked.items():
            assert out["shareHead"] == "Wall-clock share", (label, out["shareHead"])
            assert "not a duration" in (out["lead"] or ""), (label, out["lead"])
            assert out["leadLink"] == "#elements", (label, out["leadLink"])
