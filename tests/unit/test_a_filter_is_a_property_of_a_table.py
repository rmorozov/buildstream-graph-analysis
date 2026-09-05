"""UX-392: thirty-one tables, one search box.

The user asked whether the search controls help, naming the main one
and "the blast radius search control". The filing counted the round-63
export:

```text
tables                        31
  with a filter box            1
```

**Two of that item's three premises are false, and this file is where
they are re-measured.** The filter is already a property of the table
renderer (`interrogable`), gated on row count by `UX-349`:

```text
const worthFiltering = total > TABLE_OPENS_BOUNDED_ABOVE;   // 40
```

So thirty tables of thirty-one carried no filter because thirty of
them had fewer than forty rows on an *eleven-element* example - which
is `UX-367`'s finding ("the volume budget is enforced at eleven
elements") arriving at a second guard. Measured here on the 1,202
element synthetic run, the rule holds exactly: two tables above the
gate, both filtered; twenty below it, none.

The palette premise is false too. `go()` resolves an element with
`root.querySelector('[data-element=...]')`, and the first such node in
the document *is* a table row - so typing an element name has landed
on a row, not on a section, since `UX-223`.

**What was real: the two controls did not compose.** The Top-N menu
ran a second pass over every row, so choosing one re-showed rows the
filter had hidden. Measured on the same run before the fix - filter to
12 rows, choose `Top 10`, and the table shows ten rows drawn from all
1,202 while the filter box still says `mod023`.
"""
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

#: `UX-349`'s gate, read off the source so the survey below asks the
#: page about the rule the page actually has.
GATE = int(
    (REPO / "bga/viewer/structured.js").read_text(encoding="utf-8")
    .split("TABLE_OPENS_BOUNDED_ABOVE = ", 1)[1].split(";", 1)[0].strip())

#: And the number `UX-349` measured, written down.
#:
#: Reading the gate off the source is right for the survey and useless
#: as a *bound*: the mutation that lowers the constant lowers this
#: file's own expectation with it, so both clauses stayed green while
#: every short table on the page grew five inputs. Found by running it.
#: The two together are the check - the page obeys whatever the source
#: says, and the source says what was measured.
GATE_AS_MEASURED = 40

_SURVEY = """(() => {
  const tables = [...document.querySelectorAll("table[data-table]")];
  // `UX-526`: the population the table has, not the rows it is
  // showing - a row past the bound is out of the document now.
  const rows = (t) => Number(t.getAttribute("data-rows"));
  const filtered = (t) => Boolean(
    t.closest("[data-bounded], section")?.querySelector("input.table-filter"));
  return {
    tables: tables.length,
    big: tables.filter((t) => rows(t) > GATE).map(
      (t) => [t.getAttribute("data-table"), rows(t), filtered(t)]),
    small: tables.filter((t) => rows(t) <= GATE).map(
      (t) => [t.getAttribute("data-table"), rows(t), filtered(t)]),
  };
})()"""

_COMPOSES = """(() => {
  const t = document.querySelector('table[data-table="elements"]');
  const box = t.closest("section").querySelector("input.table-filter");
  const preset = t.closest("section").querySelector("select.top-n");
  const badge = t.closest("section").querySelector("span.badge");
  const shown = () => [...t.querySelectorAll("tbody tr")].filter(
    (r) => !r.hidden);
  const out = { total: Number(t.getAttribute("data-rows")),
                opened: shown().length, badgeOpened: badge.textContent };
  box.value = "mod023";
  box.dispatchEvent(new Event("input", { bubbles: true }));
  out.filtered = shown().length;
  out.badgeFiltered = badge.textContent;
  preset.value = preset.options[1].value;
  preset.dispatchEvent(new Event("change", { bubbles: true }));
  out.afterPreset = shown().length;
  out.badgeAfterPreset = badge.textContent;
  out.everyShownStillMatches = shown().every(
    (r) => r.textContent.includes("mod023"));
  out.filterBoxStillSays = box.value;
  // And back: clearing the filter must restore the preset's own view
  // rather than leaving the table on whatever the filter left.
  box.value = "";
  box.dispatchEvent(new Event("input", { bubbles: true }));
  out.afterClearing = shown().length;
  return out;
})()"""


@pytest.fixture(scope="module")
def at_scale(tmp_path_factory):
    """The 1,202-element synthetic run, exported.

    Not a committed fixture: the whole point is a page whose tables
    cross the gate, and no committed fixture has one. `--seed 1` makes
    it the same 1,202 elements on every machine (`UX-213`).
    """
    if find_chrome() is None:
        pytest.skip(NO_BROWSER)
    import tools.bga_view as view

    into = tmp_path_factory.mktemp("filter-scale")
    run = pages.scale_run(into)
    page = into / "scale.html"
    view.export(str(run), str(page))
    return page.as_uri()


@pytest.fixture(scope="module")
def survey(at_scale):
    with Browser(find_chrome()) as browser:
        return browser.measure(
            at_scale, _SURVEY.replace("GATE", str(GATE)), 1440, 900)


@pytest.fixture(scope="module")
def composed(at_scale):
    with Browser(find_chrome()) as browser:
        return browser.measure(at_scale, _COMPOSES, 1440, 900)


@pytest.mark.skipif(find_chrome() is None, reason=NO_BROWSER)
class TestTheFilterIsAPropertyOfEveryTable:
    """The Falsification's first clause, at a scale where it bites."""

    def test_every_table_over_the_gate_carries_one(self, survey):
        without = [row for row in survey["big"] if not row[2]]
        assert without == [], (
            f"{len(without)} table(s) over {GATE} rows with no filter: "
            f"{without}. A filter belongs to the table renderer, so a "
            f"section cannot have one and its neighbour not")
        assert len(survey["big"]) >= 2, (
            f"the scale run stopped producing tables over {GATE} rows, so "
            f"this file is asserting nothing: {survey['big']}")

    def test_the_gate_is_where_it_was_measured(self):
        """`UX-349` set it by measuring, and it is a bound, not a knob.

        Below it a reader scans; at or above it the tools appear, and
        it is the same number that decides whether a table opens
        bounded because it is the same question - is this a table
        somebody reads to the end. Twelve of golden's thirteen tables
        carried a filter row before that gate, every one of them short
        enough to read at a glance.
        """
        assert GATE == GATE_AS_MEASURED, (
            f"the filter gate moved to {GATE}; say what was measured "
            f"before changing it, because every table on every page "
            f"gains or loses its tools with this number")

    def test_no_table_under_the_gate_carries_one(self, survey):
        """The other direction, and it is `UX-349`'s measurement.

        Five inputs above an eleven-row table is the defect that gate
        was set for. The filing counted those tables as *unable* to
        take a filter; they are below the line on purpose.
        """
        with_one = [row for row in survey["small"] if row[2]]
        assert with_one == [], with_one
        assert len(survey["small"]) >= 10, survey["small"]


@pytest.mark.skipif(find_chrome() is None, reason=NO_BROWSER)
class TestTheTwoControlsCompose:
    """What was actually broken, and the Falsification's second clause.

    "The filter filters - a fixture, a query, a row count that drops."
    """

    def test_the_filter_reaches_past_the_bound(self, composed):
        """Not only the twenty-five rows the table opened with.

        The bound is a display cap; the filter runs over the table.
        """
        assert composed["total"] == 1202, composed["total"]
        assert composed["opened"] == 25, composed["opened"]
        assert 0 < composed["filtered"] < composed["total"], composed
        assert composed["badgeFiltered"] == (
            f"{composed['filtered']} of 1,202"), composed

    def test_a_preset_narrows_what_the_filter_left(self, composed):
        """The defect: a second pass over every row.

        Choosing `Top 10` re-showed rows the filter had hidden, while
        the filter box still said `mod023` - a reader looking at ten
        rows that have nothing to do with what they typed.
        """
        assert composed["filterBoxStillSays"] == "mod023"
        assert composed["afterPreset"] <= composed["filtered"], composed
        assert composed["everyShownStillMatches"], (
            "the preset showed rows the filter had hidden - two controls "
            "and one hidden state, which is the pair `UX-392`'s Out of "
            "Scope insists on keeping *both* of")

    def test_the_badge_never_describes_a_state_the_table_is_not_in(
            self, composed):
        """One pass, so one place the shown-count comes from."""
        assert composed["badgeAfterPreset"] == (
            f"{composed['afterPreset']} of 1,202"), composed

    def test_clearing_the_filter_returns_to_the_preset(self, composed):
        """Composition both ways.

        A fix that made the preset respect the filter and then forgot
        the preset when the filter cleared would pass every clause
        above.
        """
        assert composed["afterClearing"] == 10, composed


@pytest.mark.skipif(find_chrome() is None, reason=NO_BROWSER)
class TestThePaletteReachesARow:
    """The third Required Fix bullet, re-measured rather than assumed.

    `go()` resolves an element by `[data-element=...]`, and the first
    such node in the document is a table row - so this has worked since
    `UX-223` and the filing's premise is false. Asserted here because a
    premise that was checked is worth more written down than a bullet
    quietly dropped.
    """

    def test_an_element_name_resolves_to_a_row_first(self, tmp_path_factory):
        look = """(() => {
          const nodes = [...document.querySelectorAll(
            '[data-element="lib-c.bst"]')];
          return { tags: nodes.map((n) => n.tagName),
                   firstIsRow: nodes[0]?.tagName === "TR",
                   inATable: Boolean(nodes[0]?.closest?.("table")) };
        })()"""
        into = tmp_path_factory.mktemp("palette-row")
        uri = pages.export_uri(pages.FIXTURES["macro_micro"], into)
        with Browser(find_chrome()) as browser:
            seen = browser.measure(uri, look, 1440, 900)
        assert seen["firstIsRow"], seen["tags"]
        assert seen["inATable"]
