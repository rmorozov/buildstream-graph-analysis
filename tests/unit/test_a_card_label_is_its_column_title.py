"""UX-1226: a card's label for a field is the Elements column's title for it.

Before, one field carried two names: Rebuilds / Downstream count, Depth /
Unweighted depth, Duration / Element durations, Kind / Element kind.
Read on the two-plane page (`gen-synthetic --seed 1 --store --layers 20
--width 60`, 1,202 elements), its `--workload binaries` variant and
`macro_micro`: the first element of every Elements view, its card opened.
"""

import json
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

BIG = ("--layers", "20", "--width", "60")

_READ = r"""
(async () => {
  for (const b of document.querySelectorAll("section.chapter")) b.setAttribute("data-open", "true");
  const select = document.querySelector('select.preset-view[data-table="elements"]');
  const columns = {}, firsts = new Set();
  for (const option of select ? [...select.options] : [null]) {
    if (option) { select.value = option.value; select.dispatchEvent(new Event("change", { bubbles: true })); }
    const table = document.querySelector('table[data-table="elements"]');
    for (const th of table.querySelectorAll("thead th")) columns[th.getAttribute("data-column")] = th.textContent.trim();
    const uid = table.querySelector("tbody tr")?.getAttribute("data-element");
    if (uid) firsts.add(uid);
  }
  const cards = {};
  for (const uid of firsts) {
    const id = "element-" + uid.replace(/[^\w-]+/g, "-");
    location.hash = "#" + id;
    await new Promise((done) => setTimeout(done, 150));
    const card = document.getElementById(id);
    cards[uid] = [...(card?.querySelectorAll("dl.pairs > dd[data-field]") ?? [])]
      .map((dd) => [dd.getAttribute("data-field"), dd.previousElementSibling?.textContent.trim()]);
  }
  return { columns, cards };
})()
"""


@pytest.fixture(scope="module")
def uris(tmp_path_factory):
    import tools.bga_view as view

    made = {}
    into = tmp_path_factory.mktemp("ux1226")
    for name, shape in (("big", BIG), ("bin", ("--workload", "binaries", *BIG))):
        page = into / f"{name}.html"
        view.export(str(pages.two_plane_run(into, shape, name=name)), str(page))
        made[name] = page.as_uri()
    made["macro_micro"] = pages.export_uri(pages.FIXTURES["macro_micro"], into / "mm")
    return made


@needs_browser
@pytest.mark.parametrize("name", ["big", "bin", "macro_micro"])
def test_every_card_label_with_a_column_is_that_columns_title(uris, name):
    with Browser(chrome) as browser:
        seen = browser.measure(uris[name], _READ)
    columns, cards = seen["columns"], seen["cards"]
    checked = [
        (uid, field, label, columns[field]) for uid, rows in cards.items() for field, label in rows if field in columns
    ]
    assert len(cards) >= 3 and len(checked) >= 6, json.dumps(seen)[:2000]
    assert [c for c in checked if c[2] != c[3]] == [], checked
