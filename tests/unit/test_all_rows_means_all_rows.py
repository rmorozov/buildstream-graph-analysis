"""UX-366: the control that says "All" shows all of it.

Measured on the seeded 1,202-element run, exported and booted at
1440x900, driving the element table's two controls:

```text
control                            rows visible
baseline                                     25
population = Choke points (1)                 1
population = Critical path (14)              14
population = All elements (1202)             25
row limit  = All rows                        25
```

**1,177 of 1,202 elements could not be reached from this table by any
control.** The population select named the whole run, the limit select
said "All rows", and both drew 25.

The cause was one bound applied twice. `bga/schemas.py` carried
`{"name": "All elements", …, "bound": 25}` and `applyPreset` sliced to
it *before* `buildTable` ever saw the rows — so the reader's own limit
control, which had always had an "All rows" option, was overriding a
population that had already been cut. `buildTable` has bounded tables
of more than `TABLE_OPENS_BOUNDED_ABOVE` rows since `UX-262`, with the
badge saying `25 of 1,202` and "All rows" to lift it. The preset's copy
was a second mechanism for the same thing, one layer too high to be
reachable.

So the preset's `bound` goes and the table's own limit does the work.

**The caption had to move too, and its first two rewrites were wrong.**
With the preset's bound gone `view.shown` is the whole view, so the old
`${view.shown.length} of ${rows.length}` said "1202 of 1202" over 25
visible rows — one disagreement traded for another. Counting the
*visible* rows instead was the second wrong answer: the limit control
changes that number and the caption is drawn once, so pressing "All
rows" left it claiming 25 over 1,202. The caption says how big the view
is; the badge says how much of it is shown. One fact each, and neither
can go stale.

`test_the_page_has_a_volume_budget.py` gained a fifth measure over
this: the change put 1,177 rows in the DOM and height, words and
controls were all nearly blind to it.
"""
import collections
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

import pages    # noqa: E402
from browser import NO_BROWSER, Browser, find_chrome    # noqa: E402

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

#: The whole point: a control naming the whole population delivers it.
#: **Re-query the table between changes** - the handler replaces the
#: node, and the round-58 measurement that cached it read 25 rows for
#: every selection including `Choke points (1)` and nearly reported
#: "no control on this page works".
_DRIVE = r"""
(() => {
  for (const b of document.querySelectorAll("section.chapter")) {
    b.setAttribute("data-open", "true");
  }
  const body = () => document.querySelector("[data-preset]").closest(".preset-body");
  const visible = () => [...body().querySelectorAll("tbody tr")]
    .filter((row) => !row.hidden).length;
  const caption = () => body().querySelector("p.muted").textContent;
  const badge = () => (body().querySelector(".badge") || {}).textContent || "";
  const population = document.querySelector("[data-table=elements]");
  const views = {};
  for (const option of [...population.options]) {
    population.value = option.value;
    population.dispatchEvent(new Event("change"));
    const limit = body().querySelector(".top-n");
    const chose = limit.options[limit.selectedIndex].textContent;
    const atRest = { label: option.textContent, visible: visible(),
                     caption: caption(), badge: badge(), limit: chose };
    limit.value = "";                       // "All rows"
    limit.dispatchEvent(new Event("change"));
    views[option.value] = { ...atRest, allRows: visible(),
                            captionAfter: caption() };
  }
  return { views, population: [...population.options].map((o) => o.textContent) };
})()
"""


@pytest.fixture(scope="module")
def browser():
    with Browser(chrome) as opened:
        yield opened


@pytest.fixture(scope="module")
def driven(browser, tmp_path_factory):
    """The scale page, every population driven, at rest and at "All
    rows". Eleven elements cannot show this defect - the cap was 25 and
    both fixtures are smaller - so the population is the seeded run."""
    into = tmp_path_factory.mktemp("u366")
    uri = pages.export_uri(pages.scale_run(into), into, name="scale.html")
    return browser.measure(uri, _DRIVE, 1440, 900)


@pytest.fixture(scope="module")
def total(tmp_path_factory):
    from tools.bga_view import payloads

    run = pages.scale_run(tmp_path_factory.mktemp("u366-count"))
    return len(payloads(str(run))["report.json"]["elements"]
               ["element_durations"])


class TestThePresetDoesNotCapWhatTheReaderCanLift:
    def test_no_element_preset_carries_its_own_bound(self):
        """At the source. A bound here is applied above `buildTable`,
        where the limit control cannot reach it - which is the defect,
        not an implementation detail of it."""
        from bga.schemas import _ELEMENT_PRESETS

        bounded = [p["name"] for p in _ELEMENT_PRESETS if p.get("bound")]
        assert bounded == [], (
            f"preset(s) still cap their own rows: {bounded}. The table's "
            f"own limit is where a cap belongs, because that is the one a "
            f"reader can lift")


@needs_browser
@pytest.mark.medium
class TestAllRowsMeansAllRows:
    def test_the_population_that_names_the_run_can_be_seen_whole(
            self, driven, total):
        """The defect, as a clause: choose the population that names
        every element, then the limit that says all rows."""
        view = driven["views"]["All elements"]
        assert view["allRows"] == total, (
            f"'All elements' with the limit on 'All rows' shows "
            f"{view['allRows']} of {total}")

    def test_every_population_can_be_seen_whole(self, driven):
        """Not only the one this was filed about. A cap that is right
        for `All elements` is right for `Leaves`, and the reverse."""
        for name, view in driven["views"].items():
            assert view["allRows"] >= view["visible"], (name, view)
        leaves = driven["views"].get("Leaves")
        if leaves:
            assert leaves["allRows"] > leaves["visible"], (
                f"Leaves shows {leaves['visible']} at rest and "
                f"{leaves['allRows']} on 'All rows' - the limit did "
                f"nothing")

    def test_a_long_table_still_opens_bounded(self, driven):
        """The other direction, so the fix is not "render everything".
        `UX-262`'s rule survives: a table of more than 40 rows opens on
        its top 25, and the reader lifts it."""
        view = driven["views"]["All elements"]
        assert view["visible"] == 25, (
            f"the element table opens on {view['visible']} rows; a "
            f"1,202-row table that opens whole is the page `UX-262` "
            f"bounded")
        assert "Top 25" in view["limit"], view["limit"]

    def test_a_short_population_is_not_bounded_at_all(self, driven):
        """And a table under the threshold is left alone rather than
        given a limit it does not need."""
        for name in ("Critical path", "Choke points"):
            view = driven["views"].get(name)
            if not view:
                continue
            assert view["visible"] == view["allRows"], (name, view)
            assert view["limit"] == "All rows", (name, view["limit"])

    def test_the_caption_and_the_badge_say_different_true_things(
            self, driven, total):
        """The half the first two rewrites got wrong. The caption names
        the view's size and never moves; the badge names what is shown
        and moves with the limit."""
        view = driven["views"]["All elements"]
        assert f"all {total} elements" in view["caption"], view["caption"]
        assert view["caption"] == view["captionAfter"], (
            "the caption changed when the limit did - it is now claiming "
            "a shown-count it does not own")
        assert view["badge"].startswith("25 of "), view["badge"]

        narrow = driven["views"].get("Leaves")
        if narrow:
            assert f"of {total} elements" in narrow["caption"], (
                narrow["caption"])
            assert f"all {total}" not in narrow["caption"], (
                f"a view narrower than the run says it holds all of it: "
                f"{narrow['caption']}")

    def test_the_three_statements_agree(self, driven):
        """`UX-366`'s acceptance, stated as one clause: the population
        label, the limit label and the badge cannot contradict each
        other. Two of the three were wrong when this was filed."""
        for name, view in driven["views"].items():
            stated = name.split("(")[-1].rstrip(")") if "(" in name else None
            if not (stated or "").isdigit():
                continue
            assert view["allRows"] == int(stated), (
                f"the population is labelled {name!r} and 'All rows' "
                f"shows {view['allRows']}")
            if view["limit"] == "All rows":
                assert view["visible"] == view["allRows"], (
                    f"{name}: the limit reads 'All rows' and shows "
                    f"{view['visible']} of {view['allRows']}")


#: `UX-532`: the same three statements, over a table whose cells fold.
#:
#: The outer table's own rows are the direct `<tr>` children of its own
#: `<tbody>`; the nested tables' rows are their own. Read as children
#: rather than by selector, so a guard cannot inherit the descent it is
#: about.
#:
#: `UX-526` then took the rows past the bound *out of the document*, so
#: the attached own rows are the shown ones and the nested tables that
#: travel with a held row are unreachable too. Both counts are read at
#: rest and again with the bound lifted, and the claim is stated over
#: the pair: the migration this file is about would put 660 rows in the
#: outer tbody at either reading.
_NESTED = r"""
(() => {
  for (const b of document.querySelectorAll("section.chapter")) {
    b.setAttribute("data-open", "true");
  }
  const table = document.querySelector(
    "[data-section=resource_blast] table");
  const tools = table.closest(".preset-body") || table.parentElement;
  const own = () => [...table.querySelector("tbody").children]
    .filter((n) => n.tagName === "TR");
  const read = () => ({
    ownRows: own().length,
    visible: own().filter((tr) => !tr.hidden).length,
    badge: (tools.querySelector(".badge") || {}).textContent || "",
    copy: (tools.querySelector(".copy-rows") || {}).textContent || "",
    nested: [...table.querySelectorAll("tbody table")].map(
      (t) => [...t.querySelector("tbody").children]
        .filter((n) => n.tagName === "TR").length),
  });
  const atRest = read();
  const limit = tools.querySelector(".top-n");
  limit.value = "";                       // "All rows"
  limit.dispatchEvent(new Event("change", { bubbles: true }));
  const allRows = read();
  // Sorting re-appends rows too, and it is a separate site.
  table.querySelector("thead th").click();
  return { atRest, allRows, sorted: read() };
})()
"""


#: How many shared resources the fixture publishes, and so how many
#: rows the outer table owns.
RESOURCES = 60

#: `openingBound`'s head. What `UX-526` leaves attached at rest.
OPENING = 25


@pytest.fixture(scope="module")
def folded(browser, tmp_path_factory):
    into = tmp_path_factory.mktemp("u532")
    uri = pages.shared_resource_uri(into, RESOURCES)
    return browser.measure(uri, _NESTED, 1440, 900)


@needs_browser
@pytest.mark.medium
class TestATableDoesNotOwnTheNestedTablesRows:
    """`UX-532`. Measured before the fix on this fixture: 660 own `<tr>`
    in the outer tbody, 60 nested tables holding 0 rows each, and "All
    rows" reading `660 of 60` over `Copy 660 rows`."""

    def test_the_outer_table_owns_only_its_published_rows(self, folded):
        """The defect itself: every nested row was migrated up.

        At rest the bound holds all but `OPENING` of them out of the
        document (`UX-526`), so the number to assert is the head; the
        migration put 660 here, which is neither.
        """
        assert folded["atRest"]["ownRows"] == OPENING, (
            f"the outer tbody holds {folded['atRest']['ownRows']} direct "
            f"<tr> where the bound shows {OPENING} of {RESOURCES}")

    def test_the_nested_folds_keep_their_own_rows(self, folded):
        """The other end of the same migration - the folds opened empty
        because their rows had been appended to the outer tbody."""
        nested = folded["atRest"]["nested"]
        assert nested and all(n > 0 for n in nested), (
            f"{sum(1 for n in nested if not n)} of {len(nested)} nested "
            f"tables hold no rows")

    def test_the_badge_and_the_copy_count_say_the_published_number(
            self, folded):
        """`UX-366`'s three statements, on this shape."""
        assert folded["atRest"]["badge"] == f"25 of {RESOURCES}", (
            folded["atRest"]["badge"])
        assert folded["allRows"]["visible"] == RESOURCES, (
            folded["allRows"])
        assert folded["allRows"]["copy"] == f"Copy {RESOURCES} rows", (
            folded["allRows"]["copy"])

    def test_all_rows_moves_no_row_between_tables(self, folded):
        """And lifting the bound is not what tears them out.

        It re-attaches the held rows, so the population grows from
        `OPENING` to `RESOURCES` and every nested table that arrives
        with one still holds its own rows. What the migration did -
        empty folds, `660 of 60` - reddens on both halves.
        """
        assert folded["allRows"]["ownRows"] == RESOURCES, (
            folded["allRows"]["ownRows"])
        nested = folded["allRows"]["nested"]
        assert len(nested) == RESOURCES and all(n > 0 for n in nested), (
            f"{sum(1 for n in nested if not n)} of {len(nested)} nested "
            f"tables hold no rows once the bound is lifted")
        # A sub-multiset, not a prefix of the sorted list: the bound
        # keeps the top rows by its own column, which is not the 25
        # smallest folds.
        rest = collections.Counter(folded["atRest"]["nested"])
        assert not (rest - collections.Counter(nested)), (
            "pressing 'All rows' changed what the nested tables hold: "
            f"{rest - collections.Counter(nested)}")

    def test_sorting_moves_no_row_between_tables(self, folded):
        """`sortable` re-appends every row it ranked, which is the same
        migration by another control."""
        assert folded["sorted"]["ownRows"] == RESOURCES, (
            folded["sorted"]["ownRows"])
        # Against `allRows`, not `atRest`: the sort happens with the
        # bound already lifted, so those two hold the same population
        # and only the order between them differs.
        assert (sorted(folded["sorted"]["nested"])
                == sorted(folded["allRows"]["nested"])), (
            "sorting the outer table changed what the nested tables hold")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
