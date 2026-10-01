"""UX-1032: the §3k census presses every step control at the largest size class.

Measured on the 4,002-element run (`bga gen-synthetic --seed 1 --layers
20 --width 200 --store --runs 30`), exported, 1440x900, every chapter
open, every `<details>` open, then every step control pressed:

```text
largest table at rest     40 rows (TABLE_OPENS_BOUNDED_ABOVE)
after "All rows"          4,002 rows (elements)
largest reveal at rest    6 + 3 names
after "+N more"           3,625 names, one 72,703-character run
largest JSON door         3,592,666 characters (elements)
```

At rest all three §3k violations pass - a table opens on its bound, a
reveal shows its head and tail, a JSON door is closed. Only pressing
the steps finds them, which is why this census presses every one of
them **ten times**: a step that replaces its mounted window passes at
one press and fails at the tenth if it silently starts appending.

The ceilings below are this file's own literals, not imports from the
constants they audit (`ALL_ROWS_CEILING`, `REVEAL_STEP`,
`JSON_DOOR_CHAR_CAP`) - a guard that read the production bound would
pass whatever that bound happened to be.

`UX-1037`: the growing paths §3k's own table names are filled to
`GROWN` names on a second page and held to the control that table says
draws them - read from the styleguide, not restated here.
"""

import copy
import json
import pathlib
import re
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

import pages
from browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

#: styleguide §3k's three ceilings, at the largest size class.
MOUNTED_ROWS_MAX = 200
NAMES_MAX = 60
TEXT_CHARS_MAX = 20_000

#: Every step control this census knows how to press, generically -
#: by the class each fix names its control, not by re-implementing what
#: any of them does.
_CENSUS = r"""
(() => {
  for (const box of document.querySelectorAll("section.chapter")) {
    box.setAttribute("data-open", "true");
  }
  for (const fold of document.querySelectorAll("details")) fold.open = true;

  // A table's own mounted rows: direct `<tr>` children of its own
  // `<tbody>` that are not `hidden` - `UX-532`'s own-row rule, read
  // without importing `tables.js`.
  const mountedRows = (table) => {
    const tbody = [...table.children].find((c) => c.tagName === "TBODY");
    if (!tbody) return 0;
    return [...tbody.children].filter(
      (tr) => tr.tagName === "TR" && !tr.hidden).length;
  };

  const tables = [];
  for (const table of document.querySelectorAll("table[data-table]")) {
    const tools = table.previousElementSibling;
    const select = tools?.querySelector?.(".top-n");
    const pager = tools?.querySelector?.(".table-pager");
    const next = pager?.querySelector(".page-next");
    const allOption = select?.querySelector('option[value=""]');
    const readings = [mountedRows(table)];
    // Every step this table offers: "All rows" where it is offered at
    // all, then the paging step ten times over.
    if (allOption) {
      select.value = "";
      select.dispatchEvent(new Event("change"));
      readings.push(mountedRows(table));
    }
    if (next) {
      for (let i = 0; i < 10; i += 1) {
        next.click();
        readings.push(mountedRows(table));
      }
    }
    tables.push({ key: table.getAttribute("data-table"),
                 offersAllRows: Boolean(allOption), readings,
                 max: Math.max(...readings) });
  }

  // Read structurally, not by the fix's own class name: `list-head`
  // and `list-tail` are read at rest, once, and how many *more* names
  // either now holds - plus whatever a `list-middle` (if there is one)
  // holds - is "how many of the folded middle are mounted now". A
  // reveal that dumps the whole middle into `list-head` (the shape
  // this census exists to catch) reads as a middle count too, through
  // the growth of `list-head` past its rest reading.
  const tokens = (text) => {
    const t = (text || "").replace(/^,\s*/, "").trim();
    return t ? t.split(",").map((s) => s.trim()).filter(Boolean).length : 0;
  };
  const reveals = [];
  for (const list of document.querySelectorAll(".bounded-list")) {
    const headEl = list.querySelector(".list-head");
    const middleEl = list.querySelector(".list-middle");
    const tailEl = list.querySelector(".list-tail");
    const restHead = tokens(headEl?.textContent);
    const restTail = tokens(tailEl?.textContent);
    const more = list.querySelector("button.fold-more");
    const prev = list.querySelector("button.list-prev");
    const position = list.querySelector(".list-position");
    const mountedMiddle = () => Math.max(0,
      (tokens(headEl?.textContent) - restHead) + tokens(middleEl?.textContent)
      + Math.max(0, restTail - tokens(tailEl?.textContent)));
    // The *names*, not only their count - a mutation that never moves
    // (`prev` a no-op) would otherwise still read the same count on
    // every uniform `REVEAL_STEP`-sized chunk and pass regardless.
    const middleText = () => middleEl?.textContent ?? "";
    const readings = [mountedMiddle()];
    let firstChunkText = null;
    for (let i = 0; i < 10 && more && !more.hidden; i += 1) {
      more.click();
      readings.push(mountedMiddle());
      if (i === 0) firstChunkText = middleText();
    }
    // `UX-1029` review: a reader who pressed "+N more" twice had no way
    // back. `prev` must return to the same first chunk's own names,
    // without ever mounting past the bound on the way - so it is
    // pressed the same ten times, back toward the head.
    const firstChunkReading = readings[1] ?? readings[0];
    const positionsBack = [];
    const backReadings = [];
    const backTexts = [];
    for (let i = 0; i < 10 && prev && !prev.hidden; i += 1) {
      prev.click();
      readings.push(mountedMiddle());
      backReadings.push(mountedMiddle());
      backTexts.push(middleText());
      positionsBack.push(position ? position.textContent : null);
    }
    reveals.push({ items: Number(list.getAttribute("data-items")),
                  readings, max: Math.max(...readings),
                  firstChunkReading, firstChunkText,
                  backReadings, backTexts, positionsBack });
  }

  const doors = [];
  for (const button of document.querySelectorAll("button.json-toggle")) {
    const key = button.getAttribute("data-json-toggle");
    const section = button.closest("section[data-section]");
    const readings = [];
    for (let i = 0; i < 10; i += 1) {
      button.click();
      const pre = section.querySelector("[data-raw-json] pre");
      readings.push(pre ? pre.textContent.length : 0);
      button.click();
    }
    doors.push({ key, readings, max: Math.max(...readings, 0) });
  }

  return { tables, reveals, doors };
})()
"""


@pytest.fixture(scope="module")
def browser():
    with Browser(chrome) as opened:
        yield opened


@pytest.fixture(scope="module")
def census(browser, tmp_path_factory):
    """The 4,002-element run, every chapter and fold open, every step
    control pressed ten times."""
    into = tmp_path_factory.mktemp("u1032")
    uri = pages.export_uri(pages.xl_run(into), into, name="xl.html")
    return browser.measure(uri, _CENSUS, 1440, 900)


@needs_browser
@pytest.mark.large
class TestTheCensusReadsSomething:
    """Non-vacuity: a census over nothing passes every clause below."""

    def test_it_found_tables(self, census):
        assert census["tables"], "no table on the page - reading nothing"

    def test_it_found_reveals(self, census):
        assert census["reveals"], "no bounded-list reveal on the page"

    def test_it_found_json_doors(self, census):
        assert census["doors"], "no 'view as JSON' toggle on the page"

    def test_at_least_one_table_is_pressed_past_one_reading(self, census):
        assert any(len(t["readings"]) > 1 for t in census["tables"]), (
            "no table offered a step to press - the census pressed nothing"
        )

    def test_at_least_one_reveal_is_pressed_past_one_reading(self, census):
        assert any(len(r["readings"]) > 1 for r in census["reveals"]), (
            "no reveal offered a step to press - the census pressed nothing"
        )

    def test_at_least_one_door_reaches_the_cap(self, census):
        """The door that broke this: `elements`, 3,592,666 characters.
        A door that never reaches the cap does not prove the cap holds
        at the size that matters."""
        assert any(d["max"] == TEXT_CHARS_MAX for d in census["doors"]), [d["max"] for d in census["doors"]]


@needs_browser
@pytest.mark.large
class TestEveryTableStaysBounded:
    def test_no_table_ever_mounts_past_the_bound(self, census):
        over = [(t["key"], t["readings"]) for t in census["tables"] if t["max"] > MOUNTED_ROWS_MAX]
        assert not over, f"table(s) mounted more than {MOUNTED_ROWS_MAX} rows at some step: {over}"

    def test_all_rows_is_not_offered_past_the_ceiling(self, census):
        """The other half of the same rule: a table large enough to
        need ten presses to page through must not also offer the whole
        population in one step."""
        wrong = [t["key"] for t in census["tables"] if t["offersAllRows"] and t["max"] > MOUNTED_ROWS_MAX]
        assert not wrong, f"table(s) offer 'All rows' and mount past the bound: {wrong}"


@needs_browser
@pytest.mark.large
class TestEveryRevealStaysBounded:
    def test_no_reveal_ever_mounts_past_the_bound(self, census):
        over = [(r["items"], r["readings"]) for r in census["reveals"] if r["max"] > NAMES_MAX]
        assert not over, f"reveal(s) mounted more than {NAMES_MAX} names between the head and tail at some step: {over}"


@needs_browser
@pytest.mark.large
class TestARevealCanBePagedBackward:
    """Review (#295): a reveal used to have no way back.

    Pressed forward, then `prev` pressed back the same number of times
    must reach the first chunk again - proving the "no reload" claim -
    and not mount past the bound on the way there either.
    """

    def test_prev_is_offered_on_a_reveal_that_pages_forward(self, census):
        offered = [r for r in census["reveals"] if len(r["readings"]) > 1]
        assert offered, "no reveal pressed 'more' at all - nothing to page back"
        assert any(r["positionsBack"] for r in offered), "no reveal offered 'prev' after being paged forward"

    def test_prev_returns_to_the_first_chunk(self, census):
        """Reachable, not necessarily the last backward reading: pressed
        the same ten times as forward, `prev` may walk one chunk further
        back, past the first, into the at-rest state - the claim is only
        that the first chunk's own names were mounted again on the way.

        By text, not only by count: a mutation that never moves `prev`
        at all still reads the same count on every uniform
        `REVEAL_STEP`-sized chunk, so a count-only check passes it.
        """
        for r in census["reveals"]:
            if not r["backReadings"]:
                continue
            assert r["firstChunkText"] in r["backTexts"], (
                f"{r['items']}-item reveal never showed the first chunk's "
                f"own names again while paging back: {r['backTexts']}"
            )
            assert r["firstChunkReading"] in r["backReadings"], (
                f"{r['items']}-item reveal never showed the first chunk's "
                f"{r['firstChunkReading']} names again while paging back: "
                f"{r['backReadings']}"
            )

    def test_prev_never_mounts_past_the_bound_either(self, census):
        over = [(r["items"], r["readings"]) for r in census["reveals"] if r["max"] > NAMES_MAX]
        assert not over, f"reveal(s) mounted more than {NAMES_MAX} names while paging backward: {over}"


@needs_browser
@pytest.mark.large
class TestEveryJsonDoorStaysBounded:
    def test_no_door_ever_draws_past_the_cap(self, census):
        over = [(d["key"], d["max"]) for d in census["doors"] if d["max"] > TEXT_CHARS_MAX]
        assert not over, f"door(s) drew more than {TEXT_CHARS_MAX} characters: {over}"


#: `UX-1188`: the compare chapter's count sentence, and its table filtered to one uid.
_COMPARE = r"""
(() => {
  const section = document.querySelector('[data-section="culprits"]');
  const table = section?.querySelector("table[data-table=element_deltas]");
  const mounted = () => [...table.tBodies[0].rows].filter((tr) => !tr.hidden)
    .map((tr) => tr.getAttribute("data-element"));
  const rest = table ? mounted() : [];
  const box = section?.querySelector("input.table-filter");
  if (box) {
    box.value = window.__uid;
    box.dispatchEvent(new Event("input"));
  }
  return { counts: section?.querySelector('[data-role="delta-counts"]')?.textContent ?? null,
           rows: table ? Number(table.getAttribute("data-rows")) : null,
           rest, filtered: table && box ? mounted() : null };
})()
"""


@pytest.fixture(scope="module")
def compare_page(browser, tmp_path_factory):
    """The 1,202-element two-plane store page, whose second run compares against its first."""
    from tools.bga_view import export, payloads

    into = tmp_path_factory.mktemp("u1188")
    page = into / "compare.html"
    run = str(pages.two_plane_run(into, ("--layers", "20", "--width", "60")))
    export(run, str(page))
    deltas = payloads(run)["compare.json"]["element_deltas"]
    last = deltas["rows"][-1]["element_uid"]
    got = browser.measure(page.as_uri(), f"window.__uid = {json.dumps(last)};" + _COMPARE, 1440, 900)
    return deltas, last, got, browser.measure(page.as_uri(), _CENSUS, 1440, 900)


@needs_browser
@pytest.mark.large
class TestTheCompareChapterCountsWhatMoved:
    """`UX-1188`: `element_deltas.counts` stated, and every row reachable through the table."""

    def test_the_sentence_states_the_payloads_counts(self, compare_page):
        deltas, _, got, _ = compare_page
        counts = deltas["counts"]
        assert counts["grew"] and counts["shrank"], counts
        for key in ("grew", "shrank"):
            assert f"{counts[key]:,} {key}" in (got["counts"] or ""), (key, got["counts"])
        assert f"of {len(deltas['rows']):,} elements" in got["counts"], got["counts"]

    def test_the_table_holds_every_row_and_opens_bounded(self, compare_page):
        deltas, _, got, census = compare_page
        assert got["rows"] == len(deltas["rows"]), got["rows"]
        table = next(t for t in census["tables"] if t["key"] == "element_deltas")
        assert len(got["rest"]) > 0 and table["max"] <= MOUNTED_ROWS_MAX, (len(got["rest"]), table)

    def test_the_filter_reaches_one_element_past_the_bound(self, compare_page):
        _, last, got, _ = compare_page
        assert last not in got["rest"], "the last-ranked row is mounted at rest - the filter proves nothing"
        assert got["filtered"] == [last], got["filtered"]


#: Past `NAMES_MAX`, `REVEAL_STEP` and `TABLE_OPENS_BOUNDED_ABOVE` at
#: once, so a fill reaches every step; a reveal keeps a head and tail
#: of at most ten names besides its window.
GROWN = 300
NAMES_PER_LIST_MAX = NAMES_MAX + 10
STYLEGUIDE = REPO / "docs/design/styleguide.md"
_ROW = re.compile(r"^\| `([^`]+)` \| (reveal|table|JSON door|not drawn) \|", re.M)
#: Plane 2 containers the synthetic store has no data for.
_GRAFTED = (
    "element_join",
    "element_join_coverage",
    "plane2_coverage",
    "cache",
    "capacity_recommendation",
    "restructuring",
    "timestamp_agreement",
    "serialization_point_risks",
)


def _named_paths() -> dict:
    """§3k's `UX-1037` table: `{path: drawn as}`."""
    text = STYLEGUIDE.read_text(encoding="utf-8")
    section = text[text.index("## 3k.") :]
    section = section[: section.index("\n## ", 1)]
    return dict(_ROW.findall(section))


def _holders(value, segments):
    """`(container, key)` for every instance of a dotted `[]` path."""
    key = segments[0].removesuffix("[]")
    if not isinstance(value, dict) or key not in value:
        return
    if len(segments) == 1:
        yield value, key
        return
    below = value[key]
    for item in below if segments[0].endswith("[]") else [below]:
        yield from _holders(item, segments[1:])


def _analyze(run) -> dict:
    done = subprocess.run(
        [sys.executable, "-m", "bga.cli", "analyze", str(run), "--format", "json"],
        capture_output=True,
        text=True,
        cwd=REPO,
        timeout=600,
    )
    assert done.returncode == 0, done.stderr[-2000:]
    return json.loads(done.stdout)


def _fill(payload, paths) -> dict:
    """Each path, every instance, `GROWN` marker names: `{marker: path}`."""
    markers = {}
    for idx, path in enumerate(sorted(paths)):
        tag = f"g{idx:02d}x"
        markers[tag] = path
        holders = list(_holders(payload, path.split(".")))
        items = [i for h, k in holders for i in (h[k] or [])]
        template = items[0] if items else "x.bst"
        for inst, (holder, key) in enumerate(holders):
            names = [f"{tag}{inst}x{j:04d}.bst" for j in range(GROWN)]
            if isinstance(template, dict):
                holder[key] = [{f: (n if isinstance(v, str) else v) for f, v in template.items()} for n in names]
            else:
                tail = "|" + template.partition("|")[2] if "|" in template else ""
                holder[key] = [n + tail for n in names]
    return markers


#: Every fold open; then every reveal and pager pressed, ten times. Per
#: marker instance, the most names mounted at any step and where.
_GROWN_CENSUS = r"""
(() => {
  for (const box of document.querySelectorAll("section.chapter")) box.setAttribute("data-open", "true");
  for (const fold of document.querySelectorAll("details")) fold.open = true;
  const re = /(g\d\dx)(\d+)x(\d{4})/g;
  const seen = {};
  const read = () => {
    const now = {};
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    for (let t = walker.nextNode(); t; t = walker.nextNode()) {
      const at = t.parentElement;
      const where = at.closest("[data-raw-json]") ? "door"
        : at.closest(".bounded-list") ? "reveal"
        : at.closest("table[data-table]") ? "table" : "bare";
      for (const m of t.nodeValue.matchAll(re)) {
        const tag = m[1];
        seen[tag] ??= { where: {}, max: 0 };
        seen[tag].where[where] = (seen[tag].where[where] ?? 0) + 1;
        (now[tag + m[2]] ??= new Set()).add(m[3]);
      }
    }
    for (const [key, names] of Object.entries(now)) {
      const tag = key.slice(0, 4);
      seen[tag].max = Math.max(seen[tag].max, names.size);
    }
  };
  read();
  for (let i = 0; i < 10; i += 1) {
    for (const more of document.querySelectorAll(".bounded-list button.fold-more")) {
      if (!more.hidden) more.click();
    }
    for (const next of document.querySelectorAll(".table-pager .page-next")) next.click();
    read();
  }
  const doors = [...document.querySelectorAll("button.json-toggle")].map(
    (b) => b.getAttribute("data-json-toggle"));
  return { seen, doors };
})()
"""


@pytest.fixture(scope="module")
def grown(browser, tmp_path_factory):
    """The 4,002-element store snapshot, Plane 2 grafted from
    `macro_micro`, every §3k-named path filled to `GROWN` names."""
    from tools.bga_view import export

    into = tmp_path_factory.mktemp("u1037")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "bga.cli",
            "gen-synthetic",
            str(into / "s"),
            "--seed",
            "1",
            "--layers",
            "20",
            "--width",
            "200",
            "--store",
            "--runs",
            "2",
        ],
        check=True,
        capture_output=True,
        cwd=REPO,
    )
    snapshot = sorted((into / "s/.bga/runs").iterdir())[-1]
    payload = _analyze(snapshot / "run")
    two_plane = _analyze(pages.FIXTURES["macro_micro"])
    for key in _GRAFTED:
        if not payload.get(key):
            payload[key] = copy.deepcopy(two_plane[key])
    payload["findings"].append(
        copy.deepcopy(next(f for f in two_plane["findings"] if f.get("evidence", {}).get("steps")))
    )
    named = _named_paths()
    markers = _fill(payload, named)
    (snapshot / "analyze.json").write_text(json.dumps(payload))
    page = into / "grown.html"
    export(str(snapshot / "run"), str(page))
    got = browser.measure(page.as_uri(), _GROWN_CENSUS, 1440, 900)
    return named, markers, got


@needs_browser
@pytest.mark.large
class TestEveryNamedGrowerIsDrawnByItsBound:
    """`UX-1037`: §3k's table of growing paths, held to the page."""

    def test_the_table_names_paths_and_the_page_draws_them(self, grown):
        named, markers, got = grown
        drawn = {p for p, how in named.items() if how in ("reveal", "table")}
        missing = sorted(p for tag, p in markers.items() if p in drawn and tag not in got["seen"])
        assert drawn and not missing, ("filled but never drawn", missing)

    def test_no_instance_mounts_past_the_bound(self, grown):
        _, markers, got = grown
        over = sorted((markers[tag], s["max"]) for tag, s in got["seen"].items() if s["max"] > NAMES_PER_LIST_MAX)
        assert not over, f"path(s) mounted more than {NAMES_PER_LIST_MAX} names of one instance at some step: {over}"

    def test_each_path_lands_only_in_its_named_control(self, grown):
        named, markers, got = grown
        wrong = []
        for tag, path in markers.items():
            where = set(got["seen"].get(tag, {}).get("where", {}))
            want = {"reveal": {"reveal"}, "table": {"table"}}.get(named[path], set())
            if where - want - {"door"}:
                wrong.append((path, named[path], sorted(where)))
            door = path.split("[")[0].split(".")[0] in got["doors"]
            if named[path] in ("JSON door", "not drawn") and (door != (named[path] == "JSON door")):
                wrong.append((path, named[path], "door" if door else "no door"))
        assert not wrong, wrong

    def test_a_named_path_has_left_the_unbounded_list(self):
        sys.path.insert(0, str(REPO / "tests/unit"))
        from test_every_payload_sequence_is_declared import KNOWN_UNBOUNDED_GROWERS

        stale = sorted(set(_named_paths()) & KNOWN_UNBOUNDED_GROWERS)
        assert not stale, f"bounded in §3k and still listed unbounded (UX-1037): {stale}"


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
