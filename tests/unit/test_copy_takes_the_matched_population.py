"""UX-1189 (styleguide §4c): copy states and copies the population it names.

On the 1,202-element two-plane page, after a filter the elements
table's copy takes every matched row up to `ALL_ROWS_CEILING` (200) and
its label says so - "Copy 60 matched rows" with 25 mounted, "Copy first
200 of 600 matched rows" past the ceiling - and a boolean column copies
as a JSON boolean. On that page, `golden` and `macro_micro` the copy
format is one page-wide box: no table carries its own, and ticking it
moves every table's copy to Markdown. The heavy-binary page (`UX-1182`)
is left to the next wave.
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

_CLIPBOARD = r"""
  let copied = null;
  Object.defineProperty(navigator, "clipboard", { value: { writeText: async (t) => { copied = t; } }, configurable: true });
  const settle = () => new Promise((done) => setTimeout(done, 20));
  for (const b of document.querySelectorAll("section.chapter")) b.setAttribute("data-open", "true");
"""

_FILTERED = (
    r"""
(async () => {
"""
    + _CLIPBOARD
    + r"""
  const table = document.querySelector("table[data-table=elements]");
  const tools = table.parentNode.querySelector(".table-tools");
  const box = tools.querySelector("input.table-filter");
  const button = tools.querySelector(".copy-rows");
  const out = {};
  for (const needle of ["layer19", "layer1", ""]) {
    box.value = needle;
    box.dispatchEvent(new Event("input", { bubbles: true }));
    const label = button.textContent;
    const mounted = [...table.querySelector("tbody").children].filter((tr) => !tr.hidden).length;
    button.click();
    await settle();
    out[needle || "cleared"] = { label, mounted, badge: tools.querySelector(".badge").textContent, copied };
  }
  return out;
})()
"""
)

_FORMAT = (
    r"""
(async () => {
"""
    + _CLIPBOARD
    + r"""
  const boxes = [...document.querySelectorAll("input.copy-markdown")];
  const copies = [...document.querySelectorAll("button.copy-rows")];
  const out = { boxes: boxes.length, inTools: document.querySelectorAll(".table-tools input.copy-markdown").length,
                copies: copies.length };
  if (boxes.length !== 1) return out;
  boxes[0].checked = false;
  boxes[0].dispatchEvent(new Event("change", { bubbles: true }));
  out.jsonTitles = copies.filter((b) => / as JSON,/.test(b.title)).length;
  boxes[0].checked = true;
  boxes[0].dispatchEvent(new Event("change", { bubbles: true }));
  out.markdownTitles = copies.filter((b) => / as Markdown,/.test(b.title)).length;
  copies[0].click();
  await settle();
  out.pasted = copied;
  boxes[0].checked = false;
  boxes[0].dispatchEvent(new Event("change", { bubbles: true }));
  return out;
})()
"""
)


@pytest.fixture(scope="module")
def uris(tmp_path_factory):
    import tools.bga_view as view

    into = tmp_path_factory.mktemp("copy-big")
    run = pages.two_plane_run(into, ("--layers", "20", "--width", "60"))
    page = into / "page.html"
    view.export(str(run), str(page))
    return {"big": page.as_uri(), **pages.pages(tmp_path_factory, "copy", ("golden", "macro_micro"))}


@pytest.fixture(scope="module")
def seen(uris):
    with Browser(chrome) as browser:
        return {
            "filtered": browser.measure(uris["big"], _FILTERED, 1440, 900),
            "format": {label: browser.measure(uri, _FORMAT, 1440, 900) for label, uri in uris.items()},
        }


@needs_browser
def test_a_filter_copies_what_it_matched_and_says_so(seen):
    got = seen["filtered"]["layer19"]
    rows = json.loads(got["copied"])
    assert got["badge"] == "25 of 60 matched" and got["mounted"] == 25, got
    assert got["label"] == "Copy 60 matched rows", got["label"]
    assert len(rows) == 60 and all("layer19" in row["element"] for row in rows), len(rows)


@needs_browser
def test_past_the_ceiling_the_label_states_it(seen):
    got = seen["filtered"]["layer1"]
    assert got["badge"] == "25 of 600 matched", got["badge"]
    assert got["label"] == "Copy first 200 of 600 matched rows", got["label"]
    assert len(json.loads(got["copied"])) == 200


@needs_browser
def test_a_cleared_filter_copies_the_page_again(seen):
    got = seen["filtered"]["cleared"]
    assert got["label"] == "Copy 25 rows" and len(json.loads(got["copied"])) == 25, got["label"]


@needs_browser
def test_a_boolean_copies_as_a_boolean(seen):
    rows = json.loads(seen["filtered"]["layer19"]["copied"])
    for column in ("is_leaf", "observed_critical"):
        assert {type(row[column]) for row in rows} == {bool}, (column, rows[0])


@needs_browser
def test_one_page_wide_box_sets_every_tables_format(seen):
    for label, got in seen["format"].items():
        assert got["boxes"] == 1 and got["inTools"] == 0, (label, got)
        assert got["copies"] > 5, (label, got)
        assert got["jsonTitles"] == got["markdownTitles"] == got["copies"], (label, got)
        assert got["pasted"].startswith("| "), (label, got["pasted"][:80])
