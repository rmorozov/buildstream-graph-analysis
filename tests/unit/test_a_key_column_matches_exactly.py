"""UX-1191 (styleguide §3d): one filter box, one grammar, and a one-op task table says its op once.

`binary:ld` matches that column exactly (`ld*` its start), `cpu > 1s` is a
threshold (a bare `> 1s` reads the first quantity column), a word is a
substring; an unreadable threshold says so on the page. Held on the
heavy-binary page (`pages.heavy_binary_run`), `macro_micro` and `golden`.
"""

import base64
import collections
import gzip
import json
import pathlib
import re

import pytest

from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

_QUERY = r"""
(() => {
  const out = {};
  for (const [table, text] of QUERIES) {
    const t = document.querySelector(`table[data-table="${table}"]`);
    const tools = t.parentNode.querySelector(".table-tools");
    const box = tools.querySelector("input.table-filter");
    box.value = text;
    box.dispatchEvent(new Event("input", { bubbles: true }));
    const unread = tools.querySelector(".filter-unread");
    out[`${table} ${text}`] = {
      matched: Number((/([\d,]+) matched row/.exec(tools.querySelector(".copy-rows").textContent) ?? [0, "-1"])[1]
        .replace(/,/g, "")),
      binaries: [...t.querySelector("tbody").children].map((tr) => tr.getAttribute("data-binary")),
      badge: tools.querySelector(".badge").textContent,
      invalid: box.getAttribute("aria-invalid"),
      unread: unread && !unread.hidden ? unread.textContent : null,
    };
    box.value = "";
    box.dispatchEvent(new Event("input", { bubbles: true }));
  }
  return out;
})()
"""

_STATIC = r"""
(() => {
  const ctx = document.createElement("canvas").getContext("2d");
  const task = document.querySelector('section[data-section="wall_clock_share_us"]');
  return {
    inHeads: document.querySelectorAll("th input, th select").length,
    qualifiers: task ? task.querySelectorAll(".task-qualifier").length : null,
    notes: task ? [...task.querySelectorAll(".uniform-columns")].map((n) => n.textContent) : [],
    boxes: [...document.querySelectorAll("input.table-filter[id^=bga-filter-]")].map((box) => {
      const cs = getComputedStyle(box);
      ctx.font = cs.font;
      return [box.id, box.placeholder, ctx.measureText(box.placeholder).width,
              box.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight)];
    }),
  };
})()
"""


def _report_in(page):
    text = pathlib.Path(page).read_text(encoding="utf-8")
    packed = re.search(r'id="bga-report-gz">([^<]*)</script>', text)
    return json.loads(gzip.decompress(base64.b64decode(packed.group(1))))


def _heavy_queries():
    return [
        ["binary_cost", "binary:make"],
        ["binary_cost", "binary:constant-29"],
        ["binary_cost", "binary:constant-29*"],
        ["binary_cost", "cpu > 1s"],
        ["binary_cost", "cpu > 5q"],
        ["wall_clock_share_us", "> 1s"],
    ]


@pytest.fixture(scope="module")
def seen(tmp_path_factory):
    into = tmp_path_factory.mktemp("key-exact")
    heavy = pages.export_page(pages.heavy_binary_run(into), into / "heavy.html")
    uris = {"heavy": heavy.as_uri(), **pages.pages(tmp_path_factory, "key-exact", ("golden", "macro_micro"))}
    with Browser(chrome) as browser:
        return {
            "report": _report_in(heavy),
            "heavy": browser.measure(uris["heavy"], _QUERY.replace("QUERIES", json.dumps(_heavy_queries())), 1440, 900),
            "macro": browser.measure(
                uris["macro_micro"], _QUERY.replace("QUERIES", '[["binary_cost", "binary:ld"]]'), 1440, 900
            ),
            "static": {label: browser.measure(uri, _STATIC, 1440, 900) for label, uri in uris.items()},
            "narrow": {label: browser.measure(uri, _STATIC, 390, 844) for label, uri in uris.items()},
        }


@needs_browser
def test_a_key_value_matches_that_column_exactly(seen):
    names = collections.Counter(row["binary"] for row in seen["report"]["binary_cost"])
    got = seen["heavy"]
    assert got["binary_cost binary:make"]["matched"] == names["make"] > 0, got["binary_cost binary:make"]
    assert set(got["binary_cost binary:make"]["binaries"]) == {"make"}
    longer = sum(n for name, n in names.items() if name.startswith("constant-29"))
    assert names["constant-29"] == 0 and longer > 0, longer
    assert got["binary_cost binary:constant-29"]["matched"] == 0, got["binary_cost binary:constant-29"]
    assert got["binary_cost binary:constant-29*"]["matched"] == longer, got["binary_cost binary:constant-29*"]


@needs_browser
def test_binary_ld_is_the_ld_rows_only(seen):
    got = seen["macro"]["binary_cost binary:ld"]
    assert set(got["binaries"]) == {"ld"} and got["matched"] == len(got["binaries"]) > 0, got


@needs_browser
def test_a_threshold_is_the_box_s_own_grammar(seen):
    rows = seen["report"]["binary_cost"]
    shares = seen["report"]["wall_clock_share_us"]
    got = seen["heavy"]
    assert got["binary_cost cpu > 1s"]["matched"] == sum(row["cpu_us"] > 1e6 for row in rows) > 0
    assert got["wall_clock_share_us > 1s"]["matched"] == sum(v > 1e6 for v in shares.values()) > 0


@needs_browser
def test_an_unreadable_threshold_says_so_and_filters_nothing(seen):
    got = seen["heavy"]["binary_cost cpu > 5q"]
    assert got["invalid"] == "true" and "5q" in (got["unread"] or ""), got
    total = f"{len(seen['report']['binary_cost']):,}"
    assert got["badge"].endswith(f"of {total}") and "matched" not in got["badge"], got["badge"]


@needs_browser
def test_no_head_carries_a_filter_of_its_own(seen):
    assert {label: got["inHeads"] for label, got in seen["static"].items()} == dict.fromkeys(seen["static"], 0)


@needs_browser
def test_a_one_op_task_table_says_its_op_once(seen):
    heavy = seen["static"]["heavy"]
    assert heavy["qualifiers"] == 0 and sum("op BUILD" in n for n in heavy["notes"]) == 1, heavy
    golden = seen["static"]["golden"]
    assert golden["qualifiers"] > 0 and not any("op " in n for n in golden["notes"]), golden


@needs_browser
def test_the_placeholder_fits_its_box_at_390(seen):
    over = [(label, box) for label, got in seen["narrow"].items() for box in got["boxes"] if box[2] > box[3]]
    assert not over and any(got["boxes"] for got in seen["narrow"].values()), over
