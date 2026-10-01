"""UX-1191 (styleguide §3d): one filter box, one grammar, and a one-op task table says its op once.

`binary:ld` matches that column exactly (`ld*` its start), `cpu > 1s` is a
threshold (a bare `> 1s` reads the first quantity column), a word is a
substring; an unreadable threshold says so on the page. Held on the
heavy-binary page (`pages.heavy_binary_run`), `macro_micro` and `golden`.
UX-1195: on the 1,202-element page a clause reads a column stated once
above the table, the word a cell shows and a column's singular; a word
naming no column applies nothing and says so; the badge states one population.
"""

import base64
import collections
import gzip
import json
import os
import pathlib
import re
import shutil
import subprocess

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
  const ctx = new OffscreenCanvas(10, 10).getContext("2d");
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
        ["binary_cost", "binary: make"],
        ["binary_cost", "binary:constant-29"],
        ["binary_cost", "binary:constant-29*"],
        ["binary_cost", "cpu > 1s"],
        ["binary_cost", "cpu > 5q"],
        ["binary_cost", "cpu > 1 s"],
        ["wall_clock_share_us", "> 1s"],
    ]


#: `UX-1195`: each query the round-158 walk quoted, on the page it quoted them on.
_WALK_QUERIES = [
    ["binary_cost", "binary:cc"],
    ["binary_cost", "cc"],
    ["binary_cost", "calls = 1"],
    ["elements", "is_leaf:yes"],
    ["elements", "observed:yes"],
    ["elements", "duration > 5s"],
    ["elements", "durations > 5s"],
    ["elements", "share > 50%"],
    ["elements", "level = 12"],
    ["elements", "layer1"],
    # `UX-1206`: a column's whole displayed name, and the words before a name no column has.
    ["wall_clock_share_us", "wall-clock share > 2s"],
    ["wall_clock_share_us", "share > 2s"],
    ["elements", "element durations > 0.05min"],
    ["elements", "blast radius > 10min"],
    # `UX-1206` follow-up: words of a column's name before one word of it, and text before a key clause.
    ["elements", "is a leaf:yes"],
    ["elements", "is leaf:yes"],
    ["elements", "layer1 leaf:yes"],
    # `UX-1206`: a number, a space and its unit are one value.
    ["elements", "> 60s"],
    ["elements", "> 60 s"],
    ["elements", "> 5 ms"],
    ["elements", "> 5ms"],
    ["wall_clock_share_us", "> 2 s"],
    ["wall_clock_share_us", "> 2s"],
    ["wall_clock_share_us", "> 0.05 min"],
    ["wall_clock_share_us", "> 3s"],
    ["wall_clock_share_us", "share > 5 s extra"],
]

#: `UX-1206`: the Leaves view's column, by its whole name and by one word of it.
_LEAVES = """(() => { const view = document.querySelector('select.preset-view[data-table="elements"]');
  view.value = "Leaves"; view.dispatchEvent(new Event("change")); })();"""
_LEAF_QUERIES = [["elements", "is potentially deferrable:yes"], ["elements", "deferrable:yes"]]


@pytest.fixture(scope="module")
def seen(tmp_path_factory):
    import tools.bga_view as view

    into = tmp_path_factory.mktemp("key-exact")
    heavy = pages.export_page(pages.heavy_binary_run(into), into / "heavy.html")
    walk = into / "walk.html"
    view.export(str(pages.two_plane_run(into, ("--layers", "20", "--width", "60"), name="walk")), str(walk))
    # `UX-1206`: an analysis from before `task_durations_us` - the share is the task table's one quantity.
    text = walk.read_text(encoding="utf-8")
    packed = re.search(r'id="bga-report-gz">([^<]*)</script>', text)
    report = json.loads(gzip.decompress(base64.b64decode(packed.group(1))))
    del report["task_durations_us"]
    older = into / "older.html"
    older.write_text(
        text[: packed.start(1)]
        + base64.b64encode(gzip.compress(json.dumps(report).encode())).decode()
        + text[packed.end(1) :],
        encoding="utf-8",
    )
    uris = {"heavy": heavy.as_uri(), **pages.pages(tmp_path_factory, "key-exact", ("golden", "macro_micro"))}
    with Browser(chrome) as browser:
        return {
            "report": _report_in(heavy),
            "walk_report": _report_in(walk),
            "walk": browser.measure(walk.as_uri(), _QUERY.replace("QUERIES", json.dumps(_WALK_QUERIES)), 1440, 900),
            "leaves": browser.measure(
                walk.as_uri(), _LEAVES + _QUERY.replace("QUERIES", json.dumps(_LEAF_QUERIES)), 1440, 900
            ),
            "older": browser.measure(
                older.as_uri(),
                _QUERY.replace("QUERIES", '[["wall_clock_share_us", "> 2s"], ["wall_clock_share_us", "> 1 min"]]'),
                1440,
                900,
            ),
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
    assert got["binary_cost binary: make"]["matched"] == names["make"], got["binary_cost binary: make"]


@needs_browser
def test_binary_ld_is_the_ld_rows_only(seen):
    got = seen["macro"]["binary_cost binary:ld"]
    assert set(got["binaries"]) == {"ld"} and got["matched"] == len(got["binaries"]) > 0, got


@needs_browser
def test_a_threshold_is_the_box_s_own_grammar(seen):
    rows = seen["report"]["binary_cost"]
    # `UX-1194`: the task table's first quantity is each task's own duration.
    shares = seen["report"]["task_durations_us"]
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
def test_a_column_stated_once_still_answers_the_box(seen):
    rows = seen["walk_report"]["binary_cost"]
    assert {(row["binary"], row["calls"]) for row in rows} == {("cc", 1)} and len(rows) == 1202, len(rows)
    for query in ("binary:cc", "cc", "calls = 1"):
        assert seen["walk"][f"binary_cost {query}"]["matched"] == 1202, (query, seen["walk"][f"binary_cost {query}"])


@needs_browser
def test_a_key_clause_reads_the_word_the_cell_shows(seen):
    elements = seen["walk_report"]["elements"]
    leaves = sum(row["is_leaf"] for row in elements["blast_radius"].values())
    observed = sum(row["observed_critical"] for row in elements["criticality_probability"].values())
    got = seen["walk"]
    assert got["elements is_leaf:yes"]["matched"] == leaves > 0, got["elements is_leaf:yes"]
    assert got["elements observed:yes"]["matched"] == observed > 0, got["elements observed:yes"]


@needs_browser
def test_a_column_answers_to_its_singular(seen):
    over = sum(us > 5e6 for us in seen["walk_report"]["elements"]["element_durations"].values())
    got = seen["walk"]
    assert got["elements duration > 5s"]["matched"] == got["elements durations > 5s"]["matched"] == over > 0, over


@needs_browser
def test_a_word_naming_no_column_applies_nothing_and_says_so(seen):
    for query, word in (("share > 50%", "share"), ("level = 12", "level")):
        got = seen["walk"][f"elements {query}"]
        assert got["badge"] == "25 of 1,202" and len(got["binaries"]) == 25, (query, got)
        assert got["invalid"] == "true" and f"“{word}”" in (got["unread"] or ""), (query, got)


@needs_browser
def test_the_badge_states_one_population(seen):
    got = seen["walk"]["elements layer1"]
    assert 25 < got["matched"] < 1202 and got["badge"] == f"25 of {got['matched']:,} matched", got
    badges = [said["badge"] for page in ("walk", "heavy") for said in seen[page].values()]
    assert badges and all(badge.count(" of ") <= 1 for badge in badges), badges


@needs_browser
def test_the_placeholder_fits_its_box_at_390(seen):
    over = [(label, box) for label, got in seen["narrow"].items() for box in got["boxes"] if box[2] > box[3]]
    assert not over and any(got["boxes"] for got in seen["narrow"].values()), over


@needs_browser
def test_a_column_s_whole_displayed_name_reads_as_that_column(seen):
    report, got = seen["walk_report"], seen["walk"]
    shares = sum(us > 2e6 for us in report["wall_clock_share_us"].values())
    whole, word = got["wall_clock_share_us wall-clock share > 2s"], got["wall_clock_share_us share > 2s"]
    assert whole["matched"] == word["matched"] == shares > 0 and whole["unread"] is None, (whole, word)
    over = sum(us > 3e6 for us in report["elements"]["element_durations"].values())
    assert got["elements element durations > 0.05min"]["matched"] == over > 0, got[
        "elements element durations > 0.05min"
    ]
    leaves = report["leaf_analysis"]["leaves_detail"].values()
    deferrable = sum(row["is_potentially_deferrable"] for row in leaves)
    said = seen["leaves"]
    assert said["elements is potentially deferrable:yes"]["matched"] == deferrable > 0, said
    assert said["elements deferrable:yes"]["matched"] == deferrable and deferrable < len(leaves), said


@needs_browser
def test_a_clause_not_applied_filters_nothing(seen):
    got = seen["walk"]["elements blast radius > 10min"]
    assert got["badge"] == "25 of 1,202" and len(got["binaries"]) == 25, got
    assert "“blast radius”" in (got["unread"] or ""), got


@needs_browser
def test_a_clause_s_stray_name_words_are_said_back(seen):
    """`is a leaf:yes` matched nothing and said nothing: `is a` was read as row text."""
    got = seen["walk"]
    leaves = sum(bool(row.get("is_leaf")) for row in seen["walk_report"]["elements"]["blast_radius"].values())
    assert got["elements is leaf:yes"]["matched"] == leaves > 0 and got["elements is leaf:yes"]["unread"] is None, got
    stray = got["elements is a leaf:yes"]
    assert stray["badge"] == "25 of 1,202" and "\u201cis a leaf\u201d" in (stray["unread"] or ""), stray
    mixed = got["elements layer1 leaf:yes"]
    assert 0 < mixed["matched"] < leaves and mixed["unread"] is None, mixed


@needs_browser
def test_a_bare_threshold_on_a_share_says_it_is_a_share(seen):
    got = seen["older"]["wall_clock_share_us > 2s"]
    assert got["invalid"] == "true" and "is a share, not a duration" in (got["unread"] or ""), got
    assert "wall-clock share > 2s" in got["unread"] and "matched" not in got["badge"], got


@needs_browser
def test_a_spaced_unit_is_one_value(seen):
    walk, heavy = seen["walk"], seen["heavy"]
    for table, spaced, tight in [
        ("elements", "> 60 s", "> 60s"),
        ("elements", "> 5 ms", "> 5ms"),
        ("wall_clock_share_us", "> 2 s", "> 2s"),
    ]:
        a, b = walk[f"{table} {spaced}"], walk[f"{table} {tight}"]
        assert a["matched"] == b["matched"] and a["badge"] == b["badge"] and a["unread"] == b["unread"], (a, b)
    assert walk["wall_clock_share_us > 0.05 min"]["matched"] == walk["wall_clock_share_us > 3s"]["matched"] > 0
    assert walk["elements > 60 s"]["matched"] < 1200, walk["elements > 60 s"]
    assert walk["wall_clock_share_us share > 5 s extra"]["unread"] is None
    cpu = heavy["binary_cost cpu > 1 s"]
    assert cpu["matched"] == heavy["binary_cost cpu > 1s"]["matched"] and cpu["unread"] is None, cpu


@needs_browser
def test_a_spaced_unit_no_column_reads_is_quoted_whole(seen):
    got = seen["older"]["wall_clock_share_us > 1 min"]
    assert got["invalid"] == "true" and "\u201c> 1 min\u201d" in (got["unread"] or ""), got
    assert "matched" not in got["badge"], got


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_a_word_another_column_also_names_is_not_taken_as_the_column_s_own():
    script = (
        'const t = await import(process.env.BGA_REPO + "/bga/viewer/tables.js");'
        'const specs = [{ key: "element", title: "Element" }, { key: "element_kind", title: "Element kind" }];'
        'console.log(JSON.stringify(t.parseQuery("element foo kind:x", specs)));'
    )
    out = subprocess.run(
        [shutil.which("node"), "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "BGA_REPO": str(pages.REPO)},
    )
    got = json.loads(out.stdout)
    assert got["unread"] == [] and got["text"] == "element foo", got
    assert [(c["column"], c["value"]) for c in got["exact"]] == [("element_kind", "x")], got
