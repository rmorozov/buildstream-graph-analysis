"""UX-1183: a traced element's binaries reach the page whole or counted.

Measured before, on `pages.heavy_binary_run` (112 elements, 8 of them
exec'ing 214-499 distinct binaries): `binary_cost` kept the top 5 by CPU
and the top 5 by count, at most 10 rows per element, so `layer02/mod006`
showed 5 of its 499 binaries. The card's "+N more" lands on
`binary_cost` filtered to the element, pressed and opened fresh.
"""

import base64
import collections
import gzip
import json
import pathlib
import re

import pytest

from bga import schemas
from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome


def _report_in(page):
    text = pathlib.Path(page).read_text(encoding="utf-8")
    packed = re.search(r'id="bga-report-gz">([^<]*)</script>', text)
    return json.loads(gzip.decompress(base64.b64decode(packed.group(1))))


@pytest.fixture(scope="module")
def heavy(tmp_path_factory):
    into = tmp_path_factory.mktemp("binaries")
    run = pages.heavy_binary_run(into)
    seen = collections.defaultdict(set)
    for line in (into / "heavy-plane2.log").read_text(encoding="utf-8").splitlines():
        if line.startswith("START") and " element=" in line:
            element = line.split(" element=", 1)[1].split(" ", 1)[0]
            seen[element].add(line.split("cmd=", 1)[1].split(" ", 1)[0].rsplit("/", 1)[-1])
    page = pages.export_page(run, into / "page")
    return {"log": seen, "report": _report_in(page), "uri": page.as_uri(), "plane2": run.parent / "plane2.json"}


def _rows(report):
    by = collections.defaultdict(set)
    for row in report["binary_cost"]:
        by[row["element"]].add(row["binary"])
    return by


def test_the_widest_element_shows_every_binary_it_ran(heavy):
    widest = max(heavy["log"], key=lambda uid: len(heavy["log"][uid]))
    assert len(heavy["log"][widest]) >= 200, len(heavy["log"][widest])
    assert _rows(heavy["report"])[widest] == heavy["log"][widest]


def test_every_pair_the_log_holds_is_a_row(heavy):
    rows = _rows(heavy["report"])
    missing = {uid: len(names - rows[uid]) for uid, names in heavy["log"].items() if names - rows[uid]}
    assert missing == {}, f"(element: binaries the log holds and no row does) {missing}"


def test_a_binary_three_elements_ran_names_three(heavy):
    ran = collections.defaultdict(set)
    for uid, names in heavy["log"].items():
        for name in names:
            ran[name].add(uid)
    three = sorted(name for name, uids in ran.items() if len(uids) == 3)
    assert three, "the heavy page has no binary three elements ran"
    rows = collections.defaultdict(set)
    for row in heavy["report"]["binary_cost"]:
        rows[row["binary"]].add(row["element"])
    assert {name: len(rows[name]) for name in three} == dict.fromkeys(three, 3)


def test_every_row_carries_its_wall_time_and_the_table_draws_it(heavy):
    assert all(isinstance(row.get("wall_us"), int) for row in heavy["report"]["binary_cost"])
    columns = schemas.schema(schemas.ANALYZE)["properties"]["binary_cost"][schemas.COLUMNS]
    assert "wall_us" in [column if isinstance(column, str) else column["key"] for column in columns]


_PAGE = """(() => {
  const answer = document.querySelector('#binary_cost .section-answer')?.textContent ?? '';
  const fold = document.querySelector('section[data-element="%s"] details[data-fold="binaries"]');
  const names = [...(fold?.querySelectorAll(':scope > table td[data-column="binary"]') ?? [])]
    .map((n) => n.getAttribute('data-raw'));
  return { answer, shown: names.length, more: fold?.querySelector(':scope > p[data-more]')?.dataset.more ?? null,
           first: names[0] ?? null };
})()"""


@pytest.mark.skipif(find_chrome() is None, reason=NO_BROWSER)
def test_the_page_counts_the_capture_and_the_card_the_element(heavy):
    widest = max(heavy["log"], key=lambda uid: len(heavy["log"][uid]))
    whole = len(heavy["log"][widest])
    anchor = "element-" + re.sub(r"[^\w-]+", "-", widest)
    with Browser(find_chrome()) as browser:
        seen = browser.measure(f"{heavy['uri']}#{anchor}", _PAGE % widest, 1440, 900)
    by_binary = json.loads(heavy["plane2"].read_text(encoding="utf-8"))["by_binary"]
    assert seen["answer"].startswith(f"{len(by_binary)} binaries ran"), (seen["answer"], len(by_binary))
    costliest = max(
        (row for row in heavy["report"]["binary_cost"] if row["element"] == widest), key=lambda r: r["cpu_us"]
    )
    assert (seen["shown"], seen["more"], seen["first"]) == (5, str(whole - 5), costliest["binary"]), seen


#: The card's "+N more" pressed: what `binary_cost` then holds, and where it sits.
_FOLLOW = """(async () => {
  const fold = document.querySelector('section[data-element="%s"] details[data-fold="binaries"]');
  fold.open = true;
  const link = fold.querySelector(':scope > p[data-more] a');
  link.click();
  await new Promise((done) => setTimeout(done, 1200));
  return { href: link.getAttribute('href'), ...%s };
})()"""

_TABLE = """(() => {
  const section = document.getElementById('binary_cost');
  const rows = [...section.querySelectorAll('table[data-table="binary_cost"] > tbody > tr')].filter((tr) => !tr.hidden);
  return { filter: section.querySelector('input.table-filter')?.value ?? null,
           badge: section.querySelector('.badge')?.textContent ?? '',
           elements: [...new Set(rows.map((tr) => tr.getAttribute('data-element')))], rows: rows.length,
           top: Math.round(section.getBoundingClientRect().top), hash: location.hash };
})()"""


@pytest.mark.skipif(find_chrome() is None, reason=NO_BROWSER)
def test_the_more_link_lands_on_binary_cost_filtered_to_the_element(heavy):
    widest = max(heavy["log"], key=lambda uid: len(heavy["log"][uid]))
    held = sum(row["element"] == widest for row in heavy["report"]["binary_cost"])
    anchor = "element-" + re.sub(r"[^\w-]+", "-", widest)
    with Browser(find_chrome()) as browser:
        pressed = browser.measure(f"{heavy['uri']}#{anchor}", _FOLLOW % (widest, _TABLE), 1440, 900)
        # The link itself, opened fresh: a query string makes it a new document.
        fresh = browser.measure(f"{heavy['uri']}?fresh{pressed['href']}", _TABLE, 1440, 900)
    for seen in (pressed, fresh):
        assert seen["filter"] == f"element:{widest}" and seen["elements"] == [widest], seen
        assert seen["badge"].startswith(f"25 of {held:,} matched"), (seen["badge"], held)
    assert pressed["hash"].startswith("#binary_cost") and abs(pressed["top"] - 60) <= 8, pressed


@pytest.mark.skipif(find_chrome() is None, reason=NO_BROWSER)
def test_the_sentence_counts_the_capture_where_the_rows_are_ranked(tmp_path):
    """`macro_micro`'s committed Plane 2 report carries the two rankings only: 9 binaries in rows, 11 run."""
    fixture = pages.FIXTURES["macro_micro"]
    by_binary = json.loads((fixture.parent / "plane2.json").read_text(encoding="utf-8"))["by_binary"]
    with Browser(find_chrome()) as browser:
        seen = browser.measure(pages.export_uri(fixture, tmp_path), _PAGE % "", 1440, 900)
    assert seen["answer"].startswith(f"{len(by_binary)} binaries ran"), (seen["answer"], len(by_binary))
