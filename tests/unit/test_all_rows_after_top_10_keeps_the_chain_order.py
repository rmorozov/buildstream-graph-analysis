"""UX-1223: All rows after Top 10 puts the critical path back in its chain order; a sort the reader presses is said.

Measured before, on the 1,202 two-plane page: Top 10 then All rows left the 22 rows ranked by duration
(`aria-sort` descending, layer16/mod006.bst first) with an empty badge - the chain order lost.
"""

import pytest

from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

# At rest, Top 10, All rows, then the Duration header pressed: row uids, badge, aria-sort each time.
_PATH = """(() => {
  const t = document.querySelector('table[data-table="critical_path_detail"]');
  const tools = t.parentNode.querySelector(".table-tools");
  const preset = tools.querySelector("select.top-n");
  const read = () => ({ uids: [...t.tBodies[0].rows].filter((tr) => tr.className !== "fold-row")
                          .map((tr) => tr.querySelector("td").getAttribute("data-raw")),
                        badge: tools.querySelector(".badge").textContent,
                        sorted: [...t.querySelectorAll("th[aria-sort]")].map((th) => th.dataset.column) });
  const choose = (text) => {
    preset.value = [...preset.options].find((o) => o.text === text).value;
    preset.dispatchEvent(new Event("change"));
    return read();
  };
  const rest = read();
  const top = choose("Top 10 rows");
  const all = choose("All rows");
  t.querySelector('th[data-column="duration_us"] button').click();
  return { rest, top, all, pressed: read() };
})()"""


@pytest.fixture(scope="module")
def page(tmp_path_factory):
    into = tmp_path_factory.mktemp("ux1223")
    run = pages.two_plane_run(into, ("--layers", "20", "--width", "60"))
    return run, pages.export_uri(run, into / "page")


@pytest.mark.skipif(find_chrome() is None, reason=NO_BROWSER)
def test_all_rows_after_top_10_keeps_the_chain_order(page):
    """Top 10 then All rows: uids in `critical_path_detail`'s order, no aria-sort; Duration pressed: "sorted by"."""
    from tools.bga_view import payloads

    run, uri = page
    chain = [row["element_uid"] for row in payloads(str(run))["report.json"]["critical_path_detail"]]
    with Browser(find_chrome()) as browser:
        got = {width: browser.measure(uri, _PATH, width, 900) for width in (1440, 390)}
    for width, read in got.items():
        assert len(chain) == 22 and read["rest"]["uids"] == chain, (width, read["rest"])
        assert len(read["top"]["uids"]) == 10 and read["top"]["sorted"] == ["duration_us"], (width, read["top"])
        assert read["all"]["uids"] == chain and read["all"]["sorted"] == [], (width, read["all"])
        assert read["all"]["badge"] == "", (width, read["all"])
        assert "sorted by Duration" in read["pressed"]["badge"], (width, read["pressed"])
