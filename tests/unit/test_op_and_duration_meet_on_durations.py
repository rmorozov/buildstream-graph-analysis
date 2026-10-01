"""UX-1194: `op:BUILD > 60s` reads each task's own duration, never its share.

The task table carries `task_durations_us` as its Duration column, ahead of
the share, so a bare threshold reads the duration and the share's head is
marked. Held on the 1,202-element two-plane page, `golden` and `macro_micro`.
"""

import base64
import gzip
import json
import pathlib
import re

import pytest

from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

_LOOK = r"""
(() => {
  const t = document.querySelector('table[data-table="wall_clock_share_us"]');
  const heads = [...t.querySelectorAll(":scope > thead th")].map(
    (th) => [th.getAttribute("data-column"), th.hasAttribute("data-share")]);
  const cells = (tr) => Object.fromEntries([...tr.children].map(
    (td) => [td.getAttribute("data-column"), td.getAttribute("data-raw")]));
  const rows = () => [...t.querySelector(":scope > tbody").children].map(cells);
  const lead = t.closest("section").querySelector("p.section-lead")?.textContent ?? null;
  const out = { heads, lead, opening: rows(), q: {} };
  const box = t.parentNode.querySelector(".table-tools input.table-filter");
  for (const text of box ? ["op:BUILD > 60s", "op:BUILD > 5s"] : []) {
    box.value = text;
    box.dispatchEvent(new Event("input", { bubbles: true }));
    const copy = t.parentNode.querySelector(".table-tools .copy-rows").textContent;
    out.q[text] = { matched: Number(/([\d,]+) matched row/.exec(copy)[1].replace(/,/g, "")), rows: rows() };
  }
  return out;
})()
"""


def _report_in(page):
    text = pathlib.Path(page).read_text(encoding="utf-8")
    packed = re.search(r'id="bga-report-gz">([^<]*)</script>', text)
    if packed:
        return json.loads(gzip.decompress(base64.b64decode(packed.group(1))))
    return json.loads(re.search(r'id="bga-report"[^>]*>(.*?)</script>', text, re.S).group(1))


@pytest.fixture(scope="module")
def seen(tmp_path_factory):
    into = tmp_path_factory.mktemp("op-duration")
    walk = pages.two_plane_run(into, ("--layers", "20", "--width", "60"), name="walk")
    built = {"walk": pages.export_page(walk, into / "walk", "walk.html")}
    built.update(
        {label: pages.export_page(fixture, into / label, f"{label}.html") for label, fixture in pages.FIXTURES.items()}
    )
    # An analysis from before the key: the share table as it was, lead and all.
    text = built["walk"].read_text(encoding="utf-8")
    packed = re.search(r'id="bga-report-gz">([^<]*)</script>', text)
    report = json.loads(gzip.decompress(base64.b64decode(packed.group(1))))
    del report["task_durations_us"]
    repacked = base64.b64encode(gzip.compress(json.dumps(report).encode())).decode()
    built["older"] = into / "older.html"
    built["older"].write_text(text[: packed.start(1)] + repacked + text[packed.end(1) :], encoding="utf-8")
    with Browser(chrome) as browser:
        return {
            label: {"report": _report_in(page), "page": browser.measure(page.as_uri(), _LOOK, 1440, 900)}
            for label, page in built.items()
        }


def _build_over(report, seconds):
    return {k for k, v in report["task_durations_us"].items() if k.split("|")[1] == "BUILD" and v > seconds * 1e6}


@needs_browser
def test_op_build_over_60s_is_the_build_tasks_over_60s(seen):
    report, got = seen["walk"]["report"], seen["walk"]["page"]["q"]
    assert got["op:BUILD > 60s"]["matched"] == len(_build_over(report, 60)) == 0, got["op:BUILD > 60s"]
    assert "toolchain.bst|BUILD|BUILD|0" not in {row["key"] for row in got["op:BUILD > 60s"]["rows"]}


@needs_browser
def test_a_threshold_that_matches_reads_the_duration(seen):
    report, got = seen["walk"]["report"], seen["walk"]["page"]["q"]["op:BUILD > 5s"]
    # Not vacuous: read off the share, the same query keeps a different count.
    assert sum(v > 5e6 for k, v in report["wall_clock_share_us"].items() if "|BUILD|" in k) != len(
        _build_over(report, 5)
    )
    assert got["matched"] == len(_build_over(report, 5)) > 0, got["matched"]
    assert {row["key"] for row in got["rows"]} <= _build_over(report, 5)


@needs_browser
def test_a_task_duration_is_its_element_s_on_a_one_task_run(seen):
    report = seen["walk"]["report"]
    durations, elements = report["task_durations_us"], report["elements"]["element_durations"]
    assert len({k.split("|")[0] for k in durations}) == len(durations) == len(elements)
    assert durations == {k: elements[k.split("|")[0]] for k in durations}


@needs_browser
@pytest.mark.parametrize("label", ["walk", "golden", "macro_micro"])
def test_the_duration_column_stands_before_the_marked_share(seen, label):
    report, got = seen[label]["report"], seen[label]["page"]
    assert got["heads"] == [["key", False], ["duration_us", False], ["value", True]], got["heads"]
    assert got["opening"] and all(
        float(row["duration_us"]) == report["task_durations_us"][row["key"]] for row in got["opening"]
    ), got["opening"][:3]


@needs_browser
def test_without_the_key_the_share_table_is_as_it_was(seen):
    got = seen["older"]["page"]
    assert got["heads"] == [["key", False], ["value", False]], got["heads"]
    assert "not a duration" in (got["lead"] or ""), got["lead"]


@needs_browser
@pytest.mark.parametrize("label", ["walk", "golden", "macro_micro"])
def test_no_task_holds_more_of_the_window_than_it_ran(seen, label):
    # `UX-1194` follow-up: a zero-length task's end sorted before its own start, so it held the window to the end.
    report = seen[label]["report"]
    over = {
        k: (report["task_durations_us"][k], v)
        for k, v in report["wall_clock_share_us"].items()
        if v > report["task_durations_us"][k]
    }
    assert not over, over
    if label == "walk":
        assert report["task_durations_us"]["toolchain.bst|BUILD|BUILD|0"] == 0
