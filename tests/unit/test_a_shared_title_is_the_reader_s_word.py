"""UX-1234: the critical-path probability column and its card field read "On the path"; Element durations reads "Element duration" (one title per field: `duration_us` holds "Duration").

Read on the 1,202-element two-plane page (`gen-synthetic --seed 1 --store
--layers 20 --width 60`), Critical path view: column head and card label of
each; the old words (`probability`, `durations`) still parse as that column.
"""

import json
import os
import shutil
import subprocess

import pytest

from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

_READ = r"""
(async () => {
  for (const b of document.querySelectorAll("section.chapter")) b.setAttribute("data-open", "true");
  const select = document.querySelector('select.preset-view[data-table="elements"]');
  select.value = "Critical path";
  select.dispatchEvent(new Event("change", { bubbles: true }));
  const table = document.querySelector('table[data-table="elements"]');
  const heads = {};
  for (const th of table.querySelectorAll("thead th")) heads[th.getAttribute("data-column")] = th.textContent.trim();
  const card = {};
  for (const tr of [...table.querySelectorAll("tbody tr")].slice(0, 25)) {
    const id = "element-" + tr.getAttribute("data-element").replace(/[^\w-]+/g, "-");
    location.hash = "#" + id;
    await new Promise((done) => setTimeout(done, 100));
    for (const dd of document.getElementById(id)?.querySelectorAll("dl.pairs > dd[data-field]") ?? [])
      card[dd.getAttribute("data-field")] = dd.previousElementSibling?.textContent.trim();
  }
  return { heads, card };
})()
"""

_QUERIES = ["probability > 0%", "on the path > 0%", "durations > 1s", "duration > 1s"]

_PARSE = """
const t = await import(process.env.BGA_REPO + "/bga/viewer/tables.js");
const f = await import(process.env.BGA_REPO + "/bga/viewer/format.js");
const specs = [{ key: "element", title: "Element" },
  { key: "probability", title: f.title("probability", "share"), quantity: "share" },
  { key: "element_durations", title: f.title("element_durations", "duration_us"), quantity: "duration_us" }];
const out = {};
for (const q of JSON.parse(process.env.BGA_QUERIES)) {
  const r = t.parseQuery(q, specs);
  out[q] = [Object.keys(r.thresholds), r.unread.length];
}
console.log(JSON.stringify(out));
"""


@needs_browser
def test_the_column_and_the_card_read_on_the_path_and_duration(tmp_path):
    import tools.bga_view as view

    page = tmp_path / "big.html"
    view.export(str(pages.two_plane_run(tmp_path, ("--layers", "20", "--width", "60"), name="big")), str(page))
    with Browser(chrome) as browser:
        got = browser.measure(page.as_uri(), _READ, 1440, 900)
    assert got["heads"]["probability"] == got["card"]["probability"] == "On the path", got
    assert (got["heads"]["element_durations"], got["card"]["duration_us"]) == ("Element duration", "Duration"), got


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_the_old_words_still_filter():
    run = subprocess.run(
        [shutil.which("node"), "--input-type=module", "-e", _PARSE],
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "BGA_REPO": str(pages.REPO), "BGA_QUERIES": json.dumps(_QUERIES)},
    )
    got = json.loads(run.stdout)
    assert got["probability > 0%"] == got["on the path > 0%"] == [["probability"], 0], got
    assert got["durations > 1s"] == got["duration > 1s"] == [["element_durations"], 0], got
