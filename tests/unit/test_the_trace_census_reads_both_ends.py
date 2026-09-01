"""UX-466 stages 1-2: the field census, checked against itself.

`tools/dev_trace_coverage.py` answers "which captured field reaches the
emitted trace". It is an instrument, so what it needs is the thing
`UX-411` and `UX-449` needed: clauses that fail when it stops
discriminating, rather than clauses that agree with whatever it says.

The three ways it could go quiet, and the clause for each:

- the vocabulary comes back empty, so every field reads as dropped;
- the map/record split collapses, so every element uid becomes its own
  field path and the census counts elements instead of fields;
- the assessability rule stops excluding what it cannot judge, so a
  boolean field is reported as reached or dropped on a coincidence.
"""
import pathlib

import pytest

from tools import dev_trace_coverage as census

REPO = pathlib.Path(__file__).resolve().parents[2]
WITH_TIMELINE = REPO / "tests/fixtures/with_timeline"


@pytest.fixture(scope="module")
def emitted(tmp_path_factory):
    """The vocabulary and carriers of a real emitted trace."""
    trace, complaint = census.emit_trace(
        WITH_TIMELINE, tmp_path_factory.mktemp("trace"))
    assert trace is not None, complaint
    return census.decode(trace)


class TestTheTraceSideIsReallyRead:
    def test_the_vocabulary_is_not_empty(self, emitted):
        """An empty vocabulary reports every field dropped and looks
        like a finding. It is the failure mode this census has."""
        vocabulary, _used = emitted
        assert len(vocabulary) > 10, sorted(vocabulary)

    def test_the_vocabulary_holds_names_from_more_than_one_carrier(self, emitted):
        """Slice names alone would miss every field that arrives as an
        annotation or a category, and report it dropped.

        The first version of this clause asserted a *shape* -
        lowercase, an underscore, no spaces - and did not
        discriminate: dropping the whole annotation table left it
        green, because slice names satisfy that shape too. So it names
        strings that exist in exactly one carrier and nowhere else, and
        checks one per carrier.
        """
        vocabulary, _used = emitted

        # A slice name: the element and the log it wrote.
        assert any(v.startswith("app.bst [") for v in vocabulary)
        # A category: only the interned category table has these.
        assert "bst-builder" in vocabulary, sorted(vocabulary)[:8]
        # A debug-annotation key: not an element, not a category.
        assert {"on_critical_path", "downstream_count"} <= vocabulary

    def test_the_carriers_it_reports_are_the_ones_in_the_bytes(self, emitted):
        """`bga timeline` draws Plane 1 slices on named tracks with
        dependency arrows, so those four must come back used - and this
        capture has no Plane 2, so counters must not."""
        _vocabulary, used = emitted
        assert {"slice", "track", "flow", "debug-annotation"} <= used
        assert "counter" not in used, (
            "this fixture carries no Plane 2, so a counter here means the "
            "carrier detection is reporting something it did not read")


class TestTheCaptureSideSplitsFieldsFromData:
    def test_a_map_collapses_and_a_record_does_not(self):
        """`binary_cost` is keyed by element uid - data. `wall_clock`'s
        keys are the schema. Collapsing both would count elements as
        fields; collapsing neither would report one field per element."""
        document = {"binary_cost": {"a.bst": 1, "b.bst": 2},
                    "wall_clock": {"start_us": 0, "end_us": 9}}
        paths = set(census.fields(document))

        assert "binary_cost.{}" in paths
        assert "binary_cost.{}#key" in paths
        assert "wall_clock.start_us" in paths
        assert "wall_clock.end_us" in paths
        assert "binary_cost.a.bst" not in paths

    def test_homogeneous_types_alone_do_not_make_a_map(self):
        """The condition this clause was written for, and it was right:
        `{"start_us": 0, "end_us": 9}` has two same-typed values and is
        a record. Collapsing it turned a schema into data, which is
        what the first version of `_is_map` did."""
        assert not census._is_map({"start_us": 0, "end_us": 9})
        assert not census._is_map({"name": "x", "count": 2})
        assert census._is_map({"a.bst": 1, "b.bst": 2})
        assert not census._is_map({"only": 1}), "one key cannot be a map"

    def test_the_declared_failure_mode_is_the_one_it_has(self):
        """`_is_map`'s docstring says a map whose keys are all plain
        identifiers reads as a record. Pinned, so the claim in the
        docstring is a measurement rather than a guess."""
        assert not census._is_map({"fetch": {"n": 1}, "build": {"n": 2}})

    def test_list_indices_do_not_become_field_paths(self):
        paths = set(census.fields({"spans": [{"uid": "a"}, {"uid": "b"}]}))
        assert paths == {"spans[].uid"}


class TestItDeclaresWhatItCannotAssess:
    def test_a_boolean_field_is_never_reached_or_dropped(self):
        """`UX-376`: a census names what it could not judge. `true`
        matches any trace with the word in it, so it must be excluded
        rather than counted either way."""
        verdict, reason = census.assess({True, False})
        assert verdict == "unassessable", reason

    def test_a_single_valued_field_is_unassessable(self):
        verdict, _reason = census.assess({"BUILD"})
        assert verdict == "unassessable"

    def test_a_numeric_field_is_unassessable(self):
        """The trace rebases every timestamp, so a duration may or may
        not appear as itself and a match would mean nothing."""
        verdict, _reason = census.assess({1000, 2000, 3000})
        assert verdict == "unassessable"

    def test_two_real_strings_are_assessable(self):
        verdict, values = census.assess({"app.bst", "core.bst"})
        assert verdict == "assessable"
        assert values == {"app.bst", "core.bst"}


class TestADeclinedFieldIsDeclaredAndNotJustAbsent:
    """`UX-469`: "nothing carries this" and "nothing carries this on
    purpose" are different answers, and a census that cannot tell them
    apart makes every decision look like an oversight.

    `DECLINED` is the declaration. The clauses below hold it to the
    same standard `dev_finding_coverage.UNREACHABLE` is held to: every
    entry names a real field, carries a real reason, and is reported
    under its own verdict rather than quietly dropped from the count.
    """

    def test_a_declined_field_is_never_reached_or_dropped(self,
                                                          tmp_path_factory):
        trace, complaint = census.emit_trace(
            WITH_TIMELINE, tmp_path_factory.mktemp("declined"))
        assert trace is not None, complaint
        vocabulary, _used = census.decode(trace)
        report = census.coverage(WITH_TIMELINE, vocabulary)

        seen = set()
        for buckets in report.values():
            for verdict in ("reached", "dropped", "unassessable"):
                for field, _detail in buckets.get(verdict, []):
                    assert field not in census.DECLINED, (
                        f"{field} is declared declined and is reported "
                        f"{verdict}")
            seen |= {f for f, _why in buckets.get("declined", [])}

        assert seen, "no declined field was reported at all"

    def test_every_reason_says_who_decided_it(self):
        for field, why in census.DECLINED.items():
            assert len(why) > 40, (field, why)
            assert "UX-" in why, (
                f"{field}'s reason names no item that decided it: {why}")

    def test_the_declared_paths_are_paths_a_capture_really_holds(self):
        """A declaration keyed on a path nothing writes is a
        declaration about nothing, and it goes quiet the day a field is
        renamed - which is exactly when it should speak.

        Only the two a clone can see: the static-census lists come from
        a Plane 2 report no committed capture carries beside a log
        (`UX-466` stage 3), so this asserts what it can and names what
        it cannot rather than asserting nothing.
        """
        held = set()
        for capture in (WITH_TIMELINE, REPO / "tests/fixtures/macro_micro"):
            for _plane, fields in census.capture_fields(capture).items():
                held |= set(fields)

        assert "trace.spans[].resources[]" in held
        assert "graph.elements[].cache_key" in held
        unseen = {f for f in census.DECLINED if f not in held}
        assert unseen == {f for f in census.DECLINED
                          if f.startswith("plane2.static_census.")}, unseen


class TestTheCensusOverTheCommittedCaptures:
    def test_it_names_the_captures_it_could_not_draw(self):
        """The population it can speak about is smaller than the
        population of captures, and the difference is the finding: a
        run directory imported or generated on its own has no
        `build.log`, so no timeline can be drawn from it."""
        _blocks, cannot, _planes, _carriers = census.survey()
        names = {name for name, _why in cannot}

        assert "tests/fixtures/macro_micro" in names
        assert all("build.log" in why for _n, why in cannot), cannot

    def test_plane_2_reaches_no_committed_capture_that_can_draw_one(self):
        """`UX-466`'s headline, and the reason stage 3 needs `UX-465`:
        `macro_micro` has the Plane 2 report and no log to draw from;
        `with_timeline` has the log and no Plane 2 report. So on a clone
        nothing measures what Plane 2 maps to.

        This is a **negative** clause about the fixture population, so
        it must fail the day that stops being true - which is the day
        someone commits a snapshot with both, and the day this item's
        stage 3 becomes runnable from a clone.
        """
        blocks, _cannot, planes, _carriers = census.survey()

        assert blocks, "no committed capture can draw a timeline at all"
        assert "1" in planes
        assert "2" not in planes, (
            "a committed capture now carries Plane 2 records *and* a log - "
            "UX-466 stage 3 is reachable from a clone, so re-point this")

    def test_two_carriers_are_exercised_by_nothing_a_clone_has(self):
        """Counters are Plane 2's, and no committed capture that can
        draw a timeline has Plane 2 - so the counter path ships
        unexercised by anything in the repository."""
        _blocks, _cannot, _planes, carriers = census.survey()

        assert "counter" not in carriers
        assert "counter-unit" not in carriers
        assert {"slice", "track", "flow"} <= carriers
