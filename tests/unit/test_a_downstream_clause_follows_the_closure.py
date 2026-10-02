"""UX-1228: `downstream:<uid>` filters the Elements table to everything <uid> blocks, through every level.

`depends_on:<uid>` reaches the direct dependents only. Read on the two-plane page
(`gen-synthetic --seed 1 --store --layers 20 --width 60`, 1,202 elements), where
toolchain.bst's Downstream count is 1,201 and its direct dependents 1,200.
"""

import json
import os
import pathlib
import shutil
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

_TYPED = r"""
(() => {
  const t = document.querySelector('table[data-table="elements"]');
  const tools = t.parentNode.querySelector(".table-tools");
  const box = tools.querySelector("input.table-filter");
  const read = (clause) => {
    box.value = clause;
    box.dispatchEvent(new Event("input", { bubbles: true }));
    const copy = tools.querySelector(".copy-rows")?.textContent ?? "";
    return { matched: Number((/([\d,]+) matched row/.exec(copy) ?? [0, "-1"])[1].replace(/,/g, "")),
             badge: tools.querySelector(".badge").textContent };
  };
  read("element:toolchain.bst");
  const count = t.querySelector('tbody tr[data-element="toolchain.bst"] td[data-column="downstream_count"]');
  return { count: Number(count?.getAttribute("data-raw")), downstream: read("downstream:toolchain.bst"),
           direct: read("depends_on:toolchain.bst"), help: box.title,
           bare: read("downstream > 1000"), named: read("downstream_count > 1000"),
           element: read("element > 1"), none: read("blocks > 1") };
})()
"""


@pytest.fixture(scope="module")
def uri(tmp_path_factory):
    import tools.bga_view as view

    into = tmp_path_factory.mktemp("ux1228")
    page = into / "report.html"
    view.export(str(pages.two_plane_run(into, ("--layers", "20", "--width", "60"))), str(page))
    return page.as_uri()


@needs_browser
def test_downstream_matches_the_downstream_count_and_depends_on_the_direct_ones(uri):
    with Browser(chrome) as browser:
        seen = browser.measure(uri, _TYPED)
    assert seen["count"] == 1201, seen
    assert seen["downstream"]["matched"] == seen["count"], seen
    assert "1,201" in seen["downstream"]["badge"], seen
    assert seen["direct"]["matched"] == 1200, seen
    assert "downstream:X" in seen["help"], seen


@needs_browser
def test_a_downstream_comparison_reads_the_count_column_bare_or_named(uri):
    with Browser(chrome) as browser:
        seen = browser.measure(uri, _TYPED)
    for form in ("bare", "named"):
        assert seen[form]["matched"] == 1, (form, seen)
        assert seen[form]["badge"] == "1 matched", (form, seen)


_CARRIERS = (
    '{ key: "downstream", drawn: false }, { key: "downstream_count", title: "Downstream count", quantity: "count" }'
)


def _parse(clause, specs):
    script = (
        'const t = await import(process.env.BGA_REPO + "/bga/viewer/tables.js");'
        f"console.log(JSON.stringify(t.parseQuery({json.dumps(clause)}, [{specs}])));"
    )
    out = subprocess.run(
        [shutil.which("node"), "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "BGA_REPO": str(REPO)},
    )
    return json.loads(out.stdout)


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_a_bare_word_two_columns_carry_is_said_back_unread():
    """UX-1260: UX-1236's several-candidates branch - two quantity columns carry `downstream`, so neither is read."""
    two = _parse(
        "downstream > 1000",
        _CARRIERS + ', { key: "downstream_wall_us", title: "Downstream wall", quantity: "duration_us" }',
    )
    assert two["thresholds"] == {} and two["unread"] == [{"clause": "downstream > 1000", "column": "downstream"}], two
    one = _parse("downstream > 1000", _CARRIERS)
    assert list(one["thresholds"]) == ["downstream_count"] and one["unread"] == [], one


@needs_browser
def test_a_drawn_name_or_one_no_column_carries_is_not_re_pointed(uri):
    with Browser(chrome) as browser:
        seen = browser.measure(uri, _TYPED)
    for form in ("element", "none"):
        assert seen[form]["badge"].startswith("25 of 1,202") and "matched" not in seen[form]["badge"], (form, seen)
