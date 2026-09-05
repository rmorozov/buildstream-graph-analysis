"""UX-396: sixteen of forty-four sections drew something.

The user asked whether every piece of data that could carry a visual
has one. The filing counted the round-63 export and named ten sections
that "hold quantities and draw nothing".

**"Carries numbers" is not the same as "has a shape", and the
difference is what this file measures.** A section is *shapeable* when
it publishes a population of numbers that are **all one declared
quantity** - a total split into parts, or one measure over many keys.
A section holding eleven numbers in six different units has nothing to
rank; drawing one anyway is the fiction `UX-407` removed from
`projection` two items earlier in this round, where a strip read
`19050000 -> 43200000 across 3 rows` over three numbers that are not a
distribution.

Measured on `tests/fixtures/macro_micro/run`, against the schema
rather than against the DOM - the declaration is where the unit lives:

```text
attribution                  8 values, all duration_us
blast_radius_distribution    5 values, all count
by_binary                   11 values, all count
wall_clock_share_us         11 values, all duration_us
```

Four, not ten. Two of them draw. `attribution` is the one this item
gives a shape - it is the section that *asks* where the wall clock
went, its eight buckets are published parts of a published total, and
they sum to it exactly - and the other two are recorded below with
what they would need.

**`findings` cannot take the shape the filing names, and that is
measured too.** The Required Fix says "a finding carries a magnitude
and a share; the density strip already draws exactly that". On this
run one finding of eleven carries `share`, and each finding's evidence
is in its own units:

```text
wait-category            share=0.0589   keys=category, category_us, hint, share
time-concentration       share=None     keys=chain_bound, path_us, rows, share_of_path
joint-saving             share=None     keys=joint_saving_us, savings_add, ...
memory-envelope          share=None     keys=builders, envelope_bytes, fits, ...
```

There is no per-finding magnitude to rank, and inventing one would be
the page doing analysis (`UX-193`'s rule that the page chooses
nothing).
"""
import json
import os
import pathlib
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga import schemas
from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

RUN = REPO / "tests/fixtures/macro_micro/run"

#: A population smaller than this is a handful of numbers a reader
#: reads; `UX-303`'s `SERIES_MIN_POINTS` makes the same call for a
#: series, and `columnStrip` states rather than draws below it.
POPULATION_FLOOR = 5

#: The two-state answer the Required Fix asks for: every shapeable
#: section either names the instrument it draws, or says why it has
#: none. Silence is not a state - that is what left ten sections
#: unanswered until somebody counted them.
SHAPES = {
    "attribution": (
        "decomposition",
        "`UX-361`'s instrument: eight published buckets of a published "
        "total, summing to it exactly (43,200,000 + 2,717,000 + 216,000 "
        "= 46,133,000 = `total_duration_us`), so the page lays out "
        "numbers it was handed."),
    "blast_radius_distribution": (
        "density strip",
        "`UX-303`'s instrument, declared by `bga:distribution` since "
        "`UX-260` published the percentiles."),
    "by_binary": (
        None,
        "A ranked map - one call count per binary name. `UX-411` "
        "decided it gets no fifth instrument: the four each answer a "
        "question no other one does (how did it change, how is it "
        "spread, what is it made of, where does it sit), and *which "
        "is biggest* is already answered by a mechanism the page has "
        "everywhere - a sortable table with a Top-N preset, a filter "
        "and `columnStrip` as its annotation-grade shape. A second "
        "answer to an answered question is what `UX-305`'s emphasis "
        "budget forbids. See RANKED_MAP below."),
    "wall_clock_share_us": (
        None,
        "The same shape as `by_binary` - one duration per task uid, "
        "ranked - and the same decision, for the same reasons: "
        "`UX-411` closed as a decision, not as a fifth shape. The "
        "population grows with the payload rather than with the run, "
        "so a drawn bar per key is unbounded by construction, which "
        "is the volume `UX-360`'s budget exists to prevent."),
}


#: `UX-411`'s decision, written where the census can read it.
#:
#: A **ranked map** is one measure over many data keys with no order
#: the schema declares. It is a real shape and it is not one of the
#: four - and the answer is that it wants no drawing of its own:
#:
#: 1. Each of the four instruments answers a question none of the
#:    others does. *Which is biggest* is already answered, and by a
#:    general mechanism rather than a drawing: sort, `Top N by
#:    <column>`, the filter box, and `columnStrip` beside the column.
#:    `UX-305` spends emphasis once per block; a fifth instrument
#:    would be a second answer to an answered question.
#: 2. A ranked map grows with the **payload**, not with the run - one
#:    key per binary, per task uid - so a bar per key is unbounded by
#:    construction, which is what `UX-360`'s volume budget exists to
#:    stop.
#: 3. `UX-193`: the page chooses nothing. Drawing a ranking asserts an
#:    order the schema does not declare, which is the decision
#:    `UX-413`'s Out of Scope deliberately left with the emitter.
#:
#: What this does *not* say is that the two sections below are finished
#: - measured at 120 keys, both draw every pair and no table, which is
#: `UX-413`'s defect in the shape its sweep cannot see. Filed as
#: `UX-419`; it is a bound, not a drawing, which is why it is not this
#: row.
RANKED_MAP = "no instrument, by decision (UX-411)"


def _quantities(value, node):
    """The declared quantity of every number one level inside `value`.

    Read off the *schema*, not the rendered cells: a unit a page
    guessed is exactly what `UX-201` removed, and two numbers that
    happen to print the same way are not one population.
    """
    quantity = schemas.QUANTITY
    found = []
    if isinstance(value, dict):
        extra = (node or {}).get("additionalProperties")
        for name, member in value.items():
            if not isinstance(member, (int, float)) or isinstance(member, bool):
                continue
            child = ((node or {}).get("properties") or {}).get(name) or extra
            found.append((child or {}).get(quantity))
    elif isinstance(value, list):
        item = (node or {}).get("items") or {}
        for member in value:
            if isinstance(member, (int, float)) and not isinstance(member, bool):
                found.append(item.get(quantity))
    return found


@pytest.fixture(scope="module")
def shapeable():
    """`{section: (count, quantity)}` for the fixture's own payload."""
    done = subprocess.run(
        [sys.executable, "-m", "bga.cli", "analyze", str(RUN),
         "--format", "json"],
        capture_output=True, text=True, cwd=REPO, timeout=180,
        env=dict(os.environ, PYTHONPATH=str(REPO)))
    assert done.returncode == 0, done.stderr[-3000:]
    payload = json.loads(done.stdout)
    properties = schemas.schema(schemas.ANALYZE)["properties"]
    found = {}
    for key, value in payload.items():
        units = _quantities(value, properties.get(key))
        if len(units) >= POPULATION_FLOOR and len(set(units)) == 1 and units[0]:
            found[key] = (len(units), units[0])
    return found


class TestTheCensusIsTheAnswer:
    def test_every_shapeable_section_is_answered(self, shapeable):
        """Read off the payload, not off the list.

        A census that only sees what it was told about cannot catch the
        next section that arrives with a population and no shape -
        which is how ten of them accumulated.
        """
        unanswered = sorted(set(shapeable) - set(SHAPES))
        assert unanswered == [], (
            f"{len(unanswered)} section(s) publish one quantity over "
            f"{POPULATION_FLOOR}+ values and neither draw nor say why: "
            f"{[(k, shapeable[k]) for k in unanswered]}")

    def test_the_census_names_nothing_that_is_not_shapeable(self, shapeable):
        stale = sorted(set(SHAPES) - set(shapeable))
        assert stale == [], (
            f"the census answers for sections that no longer publish a "
            f"single-quantity population: {stale}")

    def test_a_section_with_no_shape_says_why(self):
        for key, (instrument, why) in SHAPES.items():
            if instrument is not None:
                continue
            assert len(why.split()) >= 15, (
                f"`{key}` is recorded as having no shape in {len(why.split())} "
                f"words: {why!r}. The two-state answer is only worth having "
                f"if the second state is a reason")

    def test_the_four_instruments_are_the_four_that_exist(self):
        """No fifth shape landed here, which is the Out of Scope.

        `UX-411` asked whether a ranked map should make it five and
        answered no - see `RANKED_MAP` above for why. So this clause is
        the decision's guard as well as the item's: a fifth name
        appearing here without that reasoning being revisited fails.
        """
        drawn = {instrument for instrument, _why in SHAPES.values()
                 if instrument}
        assert drawn <= {"sparkline", "density strip", "decomposition",
                         "interval"}, drawn

    def test_the_ranked_maps_are_decided_rather_than_pending(self):
        """`UX-411` closes as a decision, and a decision that is not
        written down where the next round reads it is not one.

        Both reasons named an open filing before; a reason that says
        "somebody will decide this" is the shape of the silence this
        census replaced.
        """
        for key in ("by_binary", "wall_clock_share_us"):
            instrument, why = SHAPES[key]
            assert instrument is None, (key, instrument)
            assert "UX-411" in why, why
            assert "needs a fifth shape" not in why, (
                f"`{key}`'s reason still defers the decision UX-411 made: "
                f"{why!r}")


class TestFindingsCannotTakeTheShapeTheFilingNames:
    """The premise, re-measured. Sixth false one of the round."""

    def test_a_finding_has_no_magnitude_to_rank(self, shapeable):
        done = subprocess.run(
            [sys.executable, "-m", "bga.cli", "analyze", str(RUN),
             "--format", "json"],
            capture_output=True, text=True, cwd=REPO, timeout=180,
            env=dict(os.environ, PYTHONPATH=str(REPO)))
        findings = json.loads(done.stdout)["findings"]
        assert len(findings) > 5, len(findings)
        with_share = [f["id"] for f in findings
                      if (f.get("evidence") or {}).get("share") is not None]
        assert len(with_share) < len(findings) / 2, (
            f"most findings now carry a share ({with_share}), so the "
            f"filing's density-strip proposal may be buildable after all "
            f"- re-open UX-396 rather than leaving this clause green")
        assert "findings" not in shapeable, (
            "`findings` now publishes one quantity over its whole "
            "population, which is the premise this clause records as false")


@pytest.fixture(scope="module")
def drawn(tmp_path_factory):
    if find_chrome() is None:
        pytest.skip(NO_BROWSER)
    look = """(() => {
      const out = {};
      for (const s of document.querySelectorAll("section[data-section]")) {
        out[s.getAttribute("data-section")] = Boolean(
          s.querySelector("figure, svg, .density, .decomposition"));
      }
      return out;
    })()"""
    into = tmp_path_factory.mktemp("shapes")
    uri = pages.export_uri(pages.FIXTURES["macro_micro"], into)
    with Browser(find_chrome()) as browser:
        return browser.measure(uri, look, 1440, 900)


@pytest.mark.skipif(find_chrome() is None, reason=NO_BROWSER)
class TestThePageDrawsWhatTheCensusSays:
    """A census nothing checks against the page is a comment."""

    def test_every_declared_instrument_is_on_the_page(self, drawn):
        missing = [key for key, (instrument, _why) in SHAPES.items()
                   if instrument and not drawn.get(key)]
        assert missing == [], (
            f"the census says these draw and the page does not: {missing}")

    def test_the_wall_clock_question_draws_its_answer(self, drawn):
        """`attribution` is the one this item gave a shape.

        It is the section that asks where the wall clock went, and it
        was eight numbers in a list.
        """
        assert drawn.get("attribution"), (
            "the section named `Where did the wall-clock go?` draws "
            "nothing again")

    def test_a_section_recorded_as_shapeless_stays_undrawn(self, drawn):
        """The other direction: the census is not a wish list.

        A drawing that appeared without the census being updated would
        mean the two disagree, and the census is what a later round
        reads.
        """
        wrong = [key for key, (instrument, _why) in SHAPES.items()
                 if instrument is None and drawn.get(key)]
        assert wrong == [], (
            f"{wrong} draw something the census says they cannot - "
            f"update the census, or the reason is now wrong")
