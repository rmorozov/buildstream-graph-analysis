"""UX-418: the half of the tier partition that needs a measurement.

`UX-403`'s guard census mutated one guard per family and watched it go
red. Ten of eleven did; the one that did not was
`test_the_tiers_are_a_partition.py`, under *a large file demoted to no
tier*:

```text
tier partition               GREEN    14 passed in 0.58s
```

Deleting a **fifty-second** entry from `LARGE` changed nothing, because
`small` is the default: a file that belongs in a tier and is absent
from both lists reads as "small on purpose".

`tools/dev_tier_drift.py` closes it by reading the timings the CI suite
already writes. This file guards the tool, and it guards it the way the
tool has to be guarded: **against synthetic reports**, so a clause can
assert the failing case without a fifty-second file existing to produce
it. The real run is in CI; what is checked here is that the rule reads
the floors, names the file, and can fail.
"""
import json
import pathlib
import re
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tests import tiers                                        # noqa: E402
from tools import dev_tier_drift as drift                      # noqa: E402

def _a_small_file():
    """A real file in neither tier list, chosen rather than written in.

    `file_of` resolves a classname against the filesystem, so an
    invented name is dropped and every clause below would pass over an
    empty set. Hard-coding a real one is worse: the first candidate
    tried here was already in `MEDIUM`, which turned three clauses into
    assertions about the wrong transition.
    """
    listed = set(tiers.LARGE) | set(tiers.MEDIUM)
    for path in sorted((REPO / "tests/unit").glob("test_*.py")):
        name = str(path.relative_to(REPO))
        if name not in listed:
            return name
    raise AssertionError("every unit file is in a tier list")


#: A file in no tier list, so `listed_tier` says `small`.
SMALL_FILE = _a_small_file()


def _report(tmp_path, rows):
    """A junit report with `{file: seconds}`, in pytest's own shape."""
    cases = []
    for name, seconds in rows.items():
        dotted = name[:-len(".py")].replace("/", ".")
        cases.append(f'<testcase classname="{dotted}.TestThing" '
                     f'name="test_one" time="{seconds}" />')
    path = tmp_path / "junit.xml"
    path.write_text(
        '<?xml version="1.0" encoding="utf-8"?><testsuites>'
        f'<testsuite name="pytest">{"".join(cases)}</testsuite>'
        "</testsuites>", encoding="utf-8")
    return path


class TestTheReportIsReadTheWayPytestWritesIt:
    def test_the_chosen_file_is_really_unlisted(self):
        """What every clause below stands on."""
        assert drift.listed_tier(SMALL_FILE) == "small", SMALL_FILE

    def test_a_classname_resolves_to_its_file(self):
        dotted = SMALL_FILE[:-3].replace("/", ".")
        assert drift.file_of(f"{dotted}.TestSomething") == SMALL_FILE

    def test_a_module_level_classname_resolves_too(self):
        """pytest writes no class component for a bare function, and a
        rule that only handled the class form would silently drop every
        such file."""
        assert drift.file_of(SMALL_FILE[:-3].replace("/", ".")) == SMALL_FILE

    def test_a_classname_that_names_no_file_is_dropped(self):
        assert drift.file_of("not.a.module.TestThing") is None

    def test_every_case_of_a_file_is_summed(self, tmp_path):
        path = tmp_path / "junit.xml"
        dotted = SMALL_FILE[:-3].replace("/", ".")
        path.write_text(
            "<testsuites><testsuite>"
            + "".join(f'<testcase classname="{dotted}.T" name="t{i}" '
                      f'time="0.5" />' for i in range(4))
            + "</testsuite></testsuites>", encoding="utf-8")
        assert drift.measured(path) == pytest.approx({SMALL_FILE: 2.0})


class TestTheRuleReadsTheFloors:
    """The floors stay the authority; this only reads them."""

    def test_the_boundaries_are_the_declared_floors(self):
        assert drift.tier_for(tiers.MEDIUM_FLOOR_S - 0.001) == "small"
        assert drift.tier_for(tiers.MEDIUM_FLOOR_S) == "medium"
        assert drift.tier_for(tiers.LARGE_FLOOR_S - 0.001) == "medium"
        assert drift.tier_for(tiers.LARGE_FLOOR_S) == "large"


class TestTheReferenceIsReadableAndComplete:
    """Every tier entry states the measurement that placed it.

    `recorded()` is what makes the lists a record and not only a
    selector, and `UX-418` needed it: a step that reports a file has
    outgrown its tier is answering a question about a number, and the
    number should be findable.
    """

    def test_every_listed_file_carries_the_measurement_that_placed_it(self):
        reference = tiers.recorded()
        missing = [name for name in (*tiers.LARGE, *tiers.MEDIUM)
                   if name not in reference]
        assert missing == [], (
            f"{missing} are listed with no measured seconds beside them")

    def test_the_record_agrees_with_the_tier_it_is_in(self):
        """The lists and their own numbers, checked against each other -
        which nothing did before. A `LARGE` entry recorded at 3s is
        either a stale number or a wrong list, and both want looking at.
        """
        reference = tiers.recorded()
        wrong = {name: reference[name] for name in tiers.LARGE
                 if drift.tier_for(reference[name]) != "large"}
        wrong.update({name: reference[name] for name in tiers.MEDIUM
                      if drift.tier_for(reference[name]) != "medium"})
        assert wrong == {}, (
            f"listed in one tier and recorded in another: {wrong}")


class TestItFailsNamingTheFile:
    """`UX-418`'s whole complaint about the status quo: the small-tier
    timeout does catch this, and it fails saying *the small tier took
    longer than the budget* - a number, not a file."""

    def test_an_unlisted_file_over_the_medium_floor_is_named(self, tmp_path):
        report = _report(tmp_path, {SMALL_FILE: tiers.MEDIUM_FLOOR_S + 0.5})
        found = drift.drift(drift.measured(report))
        assert [row[0] for row in found] == [SMALL_FILE], found
        assert found[0][2:] == ("small", "medium"), found

    def test_the_message_carries_the_name_and_the_seconds(self, tmp_path,
                                                          capsys):
        """`--no-confirm`, because the seconds here are fabricated.

        `UX-455` made the floors branch re-run each accused file by
        itself before reporting it - the report it parses is `-n auto`
        and the floors are single-process. This clause is about the
        *message*, and its 51.0s is a number written into a synthetic
        junit document for a file that really costs hundredths. The
        confirmation correctly clears it, which is the flag's whole
        reason for existing: read what the parallel report alone said.
        The clause below it, and
        `tests/unit/test_a_candidate_is_confirmed_alone.py`, are where
        the confirmation itself is exercised.
        """
        report = _report(tmp_path, {**tiers.recorded(), SMALL_FILE: 51.0})
        assert drift.main([str(report), "--no-confirm"]) == 1
        said = capsys.readouterr().err
        assert SMALL_FILE in said, said
        assert "51.0s" in said, said
        assert "listed small, measured large" in said, said

    def test_the_same_report_confirmed_clears_it(self, tmp_path, capsys):
        """And the other half, so `--no-confirm` is not a way past the
        gate that nothing notices. The same fabricated 51.0s, run
        through the shipped path, comes back cleared and *said so* -
        exit 0, with the file named on stderr as over a floor in the
        parallel report and under it alone."""
        report = _report(tmp_path, {**tiers.recorded(), SMALL_FILE: 51.0})
        assert drift.main([str(report)]) == 0
        said = capsys.readouterr().err
        assert SMALL_FILE in said, said
        assert "51.0s under -n auto" in said, said
        assert "alone" in said, said

    def test_a_file_inside_its_tier_is_not_named(self, tmp_path):
        report = _report(tmp_path, {SMALL_FILE: tiers.MEDIUM_FLOOR_S - 0.1})
        assert drift.drift(drift.measured(report)) == []

    def test_a_listed_file_at_its_own_size_is_not_named(self, tmp_path):
        report = _report(tmp_path, {tiers.LARGE[0]: tiers.LARGE_FLOOR_S + 30})
        assert drift.drift(drift.measured(report)) == []

    def test_a_file_that_got_faster_is_not_a_failure(self, tmp_path):
        """The other direction wastes nothing, and reporting it would
        red the build on an ordinary fast run."""
        report = _report(tmp_path, {tiers.LARGE[0]: 0.1})
        assert drift.drift(drift.measured(report)) == []


class TestItCannotPassOverNothing:
    """The mistake `UX-403`'s census exists to find, in the instrument
    written to fix it: a report whose classnames resolve to no file
    would make every clause above vacuous."""

    def test_an_empty_report_is_an_error_not_a_pass(self, tmp_path):
        path = tmp_path / "junit.xml"
        path.write_text("<testsuites><testsuite /></testsuites>",
                        encoding="utf-8")
        assert drift.main([str(path)]) == 2

    def test_a_report_of_unresolvable_names_is_an_error(self, tmp_path):
        path = tmp_path / "junit.xml"
        path.write_text('<testsuites><testsuite><testcase '
                        'classname="nope.Test" name="t" time="99" />'
                        "</testsuite></testsuites>", encoding="utf-8")
        assert drift.main([str(path)]) == 2


class TestCiIsReadAgainstItsOwnRecord:
    """`UX-420`: the comparison the three failures leave standing.

    `UX-418` established that CI's seconds cannot be compared to the
    floors in `tests/tiers.py` in any form. What is left is CI against
    **CI** - one machine against itself over time - and the whole
    difficulty is the reference, which is what the filing says to design
    first. These clauses are the four ways it rots.
    """

    def _ref(self, times, source="a runner"):
        return drift.record(times, source)

    def test_a_run_read_against_itself_is_quiet(self):
        times = dict(tiers.recorded())
        verdict, shift, rows = drift.against(times, self._ref(times))
        assert (verdict, rows) == ("ok", []), (verdict, rows)
        assert shift == pytest.approx(1.0)

    @pytest.mark.parametrize("factor", [0.7, 1.0, 1.3, 1.6])
    def test_the_whole_runner_moving_is_not_drift(self, factor):
        """Rot 2. A new image shifts every file together, and per file
        that reads as drift everywhere. The median goes out first."""
        reference = self._ref(dict(tiers.recorded()))
        moved = {name: seconds * factor
                 for name, seconds in tiers.recorded().items()}
        verdict, shift, rows = drift.against(moved, reference)
        assert verdict == "ok", (verdict, rows[:3])
        assert shift == pytest.approx(factor)

    def test_a_runner_that_moved_too_far_says_the_reference_is_stale(self):
        """And past the band it stops naming files, because naming them
        would name the wrong thing."""
        reference = self._ref(dict(tiers.recorded()))
        moved = {name: seconds * 3
                 for name, seconds in tiers.recorded().items()}
        verdict, _shift, rows = drift.against(moved, reference)
        assert verdict == "stale", verdict
        assert rows == [], rows

    def test_one_file_slower_is_drift_on_any_image(self):
        """Rot 2's other end: dividing the median out must not become an
        excuse. The same file, on an unchanged and a 1.3x image.

        The victim is a `LARGE` file rather than the first `MEDIUM` one,
        because a file has to add `CI_DRIFT_SECONDS` as well as clear
        the ratio - and doubling a one-second file adds one second. That
        is the rule working, not an obstacle to testing it: see
        `TestTheFirstArmedRunIsTheRegressionSuite` for the run that put
        the seconds gate there.
        """
        reference = self._ref(dict(tiers.recorded()))
        victim = tiers.LARGE[0]
        for image in (1.0, 1.3):
            times = {name: seconds * image
                     for name, seconds in tiers.recorded().items()}
            times[victim] *= drift.CI_DRIFT_FACTOR + 0.5
            verdict, _shift, rows = drift.against(times, reference)
            assert verdict == "drift", (image, verdict)
            assert [row[0] for row in rows] == [victim], (image, rows)

    def test_a_new_slow_file_with_no_entry_is_reported(self):
        """Rot 1. An unreferenced file is checked by nothing, which is
        the silence this whole item is about one level along."""
        reference = self._ref(dict(tiers.recorded()))
        times = dict(tiers.recorded())
        times["tests/unit/test_a_slow_file_says_which_file.py"] = 30.0
        verdict, _shift, rows = drift.against(times, reference)
        assert verdict == "drift", verdict
        assert [(row[0], row[2]) for row in rows] == [
            ("tests/unit/test_a_slow_file_says_which_file.py", None)], rows

    def test_a_new_fast_file_needs_no_entry(self):
        """The proportionate half of rot 1: every PR adding a test would
        fail otherwise, and nothing about a fast file is at risk."""
        reference = self._ref(dict(tiers.recorded()))
        times = dict(tiers.recorded())
        times["tests/unit/test_a_slow_file_says_which_file.py"] = 0.2
        verdict, _shift, rows = drift.against(times, reference)
        assert (verdict, rows) == ("ok", []), rows

    def test_a_reference_of_other_files_is_refused_not_believed(self):
        """A reference naming nothing this run measured is not a
        reference for it, and comparing against it would be the
        pass-over-nothing this file exists to prevent."""
        verdict, _shift, rows = drift.against(
            dict(tiers.recorded()), self._ref({"tests/unit/nope.py": 1.0}))
        assert (verdict, rows) == ("empty", []), (verdict, rows)

    def test_recording_round_trips_and_says_where_it_came_from(self,
                                                               tmp_path):
        times = dict(tiers.recorded())
        report = _report(tmp_path, times)
        out = tmp_path / "ref.json"
        assert drift.main([str(report), "--record", str(out),
                           "--source", "a named runner"]) == 0
        written = json.loads(out.read_text(encoding="utf-8"))
        assert written["measured_on"] == "a named runner"
        assert set(written["files"]) == set(times)
        assert drift.main([str(report), "--against", str(out)]) == 0

    @pytest.mark.parametrize("shape", ["absent", "unrecorded"])
    def test_the_step_says_so_rather_than_passing_over_no_reference(
            self, tmp_path, capsys, shape):
        """Rot 4, and the one that would make this a guard that cannot
        fail. With nothing to compare against, the step prints the
        document to commit and says nothing is being checked - it does
        not quietly pass. Both shapes of nothing: no file at all, and
        the committed file before its first CI run."""
        report = _report(tmp_path, dict(tiers.recorded()))
        path = tmp_path / "ref.json"
        if shape == "unrecorded":
            path.write_text(json.dumps({"files": {}}), encoding="utf-8")
        assert drift.main([str(report), "--against", str(path)]) == 0
        said = capsys.readouterr()
        assert "nothing is being checked" in said.err, said.err
        assert json.loads(said.out)["files"], said.out

    def test_the_committed_reference_is_in_one_of_those_two_states(self):
        """It is either waiting for its first CI run or it has real
        numbers - and if it has them, they came from a runner rather
        than from somebody's laptop, which is the whole point."""
        held = json.loads(
            drift.CI_REFERENCE.read_text(encoding="utf-8"))
        assert "files" in held, held.keys()
        if held["files"]:
            assert "github" in held.get("measured_on", "").lower(), (
                f"the reference was recorded on {held.get('measured_on')!r}, "
                f"which is not the runner - see UX-418's outcome for the "
                f"three ways a developer machine's seconds fail here")
        else:
            assert held.get("bootstrap"), (
                "an empty reference with no note reads as a bug rather "
                "than as a state")

    def test_a_refreshed_reference_carries_the_spread_it_saw(self):
        """Rot 3's other half, and `CI_DRIFT_FACTOR`'s only route to
        being a measurement. The factor is admittedly a guess; the
        quantity it should be sized against is how far one file departs
        from its peers between two CI runs, and only a refresh can see
        it. So the refresh writes it down."""
        first = self._ref(dict(tiers.recorded()))
        times = {name: seconds * 1.2
                 for name, seconds in tiers.recorded().items()}
        victim = tiers.MEDIUM[0]
        times[victim] *= 2.0
        second = drift.record(times, "a runner, later", first)
        assert second["spread"]["shift"] == pytest.approx(1.2, abs=0.05)
        assert second["spread"]["max"] == pytest.approx(2.0, abs=0.05)
        assert second["spread"]["files"] == len(first["files"])

    def test_the_first_record_states_no_spread_rather_than_a_made_up_one(
            self):
        """With nothing to compare against there is no spread, and a
        1.0 written in its place would read as a measurement."""
        assert "spread" not in drift.record(dict(tiers.recorded()), "a runner")

    def test_the_factor_and_the_band_are_stated(self):
        assert drift.CI_DRIFT_FACTOR > 1.0, drift.CI_DRIFT_FACTOR
        low, high = drift.IMAGE_BAND
        assert low < 1.0 < high, drift.IMAGE_BAND


class TestTheShiftIsEstimatedWhereARatioMeansSomething:
    """`UX-423`. The shift stands for "how much slower this runner is",
    and it was a median over every referenced file - 42% of which run
    under a tenth of a second, where a ratio is noise.

    Two runs of the whole suite on one machine at one commit measured
    the noise directly: a file under 0.1s ran x4.21 its own time with
    nothing changed, against x1.17 worst for files over five seconds.

    A median is robust, so this is a **precision** fix and not an
    accuracy one - the point estimate moved 0.983 to 0.980 - and these
    clauses hold the property that survives that: what the estimate is
    computed *from*.
    """

    def _pair(self, small_ratio, big_ratio=1.0, smalls=200, bigs=40):
        """A reference and a run where the two size classes disagree."""
        reference = {f"tests/unit/test_tiny_{i}.py": 0.05
                     for i in range(smalls)}
        reference.update({f"tests/unit/test_big_{i}.py": 8.0
                          for i in range(bigs)})
        times = {name: seconds * (small_ratio if "tiny" in name else
                                  big_ratio)
                 for name, seconds in reference.items()}
        return times, {"files": reference}

    def test_a_crowd_of_tiny_files_does_not_set_the_shift(self):
        """The failure this item is about. Two hundred sub-second files
        all reading x1.6 must not persuade the rule that the runner got
        60% slower, because at 0.05s that ratio is a measurement of the
        timer."""
        times, reference = self._pair(small_ratio=1.6, big_ratio=1.0)
        _verdict, shift, _rows = drift.against(times, reference)
        assert shift == pytest.approx(1.0), (
            f"shift {shift:.3f} - the tiny files outvoted the ones that "
            f"carry the runner's speed")

    def test_the_files_that_carry_the_runner_do_set_it(self):
        """The other direction, so the fix is a distinction and not a
        rule that ignores small files' existence."""
        times, reference = self._pair(small_ratio=1.0, big_ratio=1.4)
        _verdict, shift, _rows = drift.against(times, reference)
        assert shift == pytest.approx(1.4), shift

    def test_the_floor_is_read_on_the_reference_not_the_run(self):
        """A file that got slower must not buy its way into the
        population by getting slower - that would let a regression drag
        the baseline toward itself."""
        reference = {f"tests/unit/test_big_{i}.py": 8.0 for i in range(40)}
        reference["tests/unit/test_was_tiny.py"] = 0.05
        times = dict.fromkeys(reference, 8.0)
        times["tests/unit/test_was_tiny.py"] = 30.0     # x600, and small
        assert "tests/unit/test_was_tiny.py" not in drift.shift_population(
            {n: times[n] / reference[n] for n in reference}, reference)

    def test_a_suite_with_too_few_big_files_keeps_its_estimator(self):
        """A median of four ratios is worse than a median of four
        hundred noisy ones. Below `SHIFT_MIN_FILES` the floor is
        abandoned rather than the estimate being made from nearly
        nothing."""
        reference = {f"tests/unit/test_tiny_{i}.py": 0.05 for i in range(200)}
        reference["tests/unit/test_big.py"] = 8.0
        ratios = dict.fromkeys(reference, 1.2)
        assert len(drift.shift_population(ratios, reference)) == len(reference)

    def test_the_run_reports_the_precision_of_its_own_shift(self, tmp_path,
                                                            capsys):
        """`UX-420` sized a threshold on one sample and its first armed
        run named thirty-one files on an unchanged suite. A later round
        can only do better with a series, so every run prints the
        population and spread behind its shift."""
        times = dict(tiers.recorded())
        reference = tmp_path / "ref.json"
        reference.write_text(json.dumps(drift.record(times, "a runner")),
                             encoding="utf-8")
        report = _report(tmp_path, times)
        assert drift.main([str(report), "--against", str(reference)]) == 0
        said = capsys.readouterr()
        assert "IQR" in said.out, said.out
        assert f"over {drift.SHIFT_FLOOR_S:g}s" in said.out, said.out

    def test_the_floor_is_the_repositorys_own_and_is_stated(self):
        """Not a new number. `MEDIUM_FLOOR_S` is already the line for
        "this file is not trivial", and a second one would need a
        sample nobody has."""
        assert drift.SHIFT_FLOOR_S == tiers.MEDIUM_FLOOR_S
        source = pathlib.Path(drift.__file__).read_text(encoding="utf-8")
        assert "UX-423" in source
        assert "4.208" in source, (
            "the noise measurement that sized this is not in the file, so "
            "the next round cannot re-check the choice")


class TestTheFirstArmedRunIsTheRegressionSuite:
    """`UX-420`'s reference, armed, immediately reported 31 files on a
    suite nobody had touched. That run is this class.

    The reference was recorded on run 33304444986; run 33306283177 was
    the next one, carrying the same suite plus a JSON file and a
    document. Everything it named was noise, and the shape of the noise
    is the finding: **a ratio is meaningless at small magnitudes**. The
    worst offender by ratio (x18.27) added three tenths of a second; the
    file that led the list by seconds added 2.4 and read x1.66.
    """

    #: `(measured, recorded)` as the step printed them, worst first.
    #: **Twelve of the thirty-one**, and only twelve on purpose: the
    #: step prints seconds to one decimal, so a row reading "against
    #: 0.0s recorded" is anywhere in 0.005-0.049 and its ratio cannot be
    #: reconstructed. Reconstructing it would be inventing precision the
    #: log does not have. These twelve are every row whose *recorded*
    #: figure is 0.2s or more, which is where one decimal still says
    #: something - and they carry the whole claim anyway, because the
    #: largest addition in the entire report is the first row's 2.4s.
    REPORTED = (
        (5.9, 4.3), (4.4, 3.1), (3.8, 2.7), (1.9, 1.2), (1.3, 0.5),
        (1.1, 0.7), (1.0, 0.7), (0.7, 0.4), (0.6, 0.4), (0.5, 0.3),
        (0.4, 0.2), (0.3, 0.2))

    #: The run's own median shift, as the step reported it.
    SHIFT = 0.82

    def _that_run(self):
        """The reported files, plus enough unchanged ones to hold the
        median at the shift the run actually had."""
        reference, times = {}, {}
        for index, (measured, recorded) in enumerate(self.REPORTED):
            name = f"tests/unit/test_reported_{index}.py"
            reference[name], times[name] = recorded, measured
        for index in range(200):
            name = f"tests/unit/test_steady_{index}.py"
            reference[name] = 1.0 + index * 0.05
            times[name] = reference[name] * self.SHIFT
        return times, drift.record(reference and
                                   {k: v for k, v in reference.items()})

    def test_the_replay_really_is_that_run(self):
        """The premise. If the synthetic run's median is not the shift
        the step reported, this class is replaying something else."""
        times, held = self._that_run()
        _verdict, shift, _rows = drift.against(times, held)
        assert shift == pytest.approx(self.SHIFT, abs=0.02), shift

    def test_a_ratio_alone_reports_all_of_them(self):
        """What the shipped rule did, so the clause below is a
        difference and not a tautology."""
        times, held = self._that_run()
        known = held["files"]
        loud = [name for name in known
                if times[name] / known[name] / self.SHIFT
                > drift.CI_DRIFT_FACTOR]
        assert len(loud) == len(self.REPORTED), len(loud)

    def test_the_rule_that_also_counts_seconds_reports_none(self):
        """And the fix: nothing here added five seconds, so nothing here
        is drift. The largest addition on that run was 2.4s."""
        times, held = self._that_run()
        verdict, _shift, rows = drift.against(times, held)
        assert (verdict, rows) == ("ok", []), (verdict, rows[:3])

    def test_a_file_that_added_real_seconds_is_still_reported(self):
        """The half that must not be lost. Both gates, one file: a
        thirty-second file that went to sixty on the same run."""
        times, held = self._that_run()
        victim = "tests/unit/test_steady_0.py"
        held["files"][victim] = 30.0
        times[victim] = 60.0
        verdict, _shift, rows = drift.against(times, held)
        assert verdict == "drift", verdict
        assert [row[0] for row in rows] == [victim], rows

    def test_seconds_alone_is_not_enough_either(self):
        """A big file drifts by five seconds without drifting by much:
        88s against 82s expected is six seconds and only x1.07, which is
        this run's noise on a file that size rather than a regression.
        The ratio gate is what says so.

        The first draft of this clause added *four* seconds and proved
        nothing - the seconds gate alone already excluded it, so
        deleting the ratio gate left the file green. Found by mutating
        (`D2`), which is the only way that kind of clause is found.
        """
        times, held = self._that_run()
        victim = "tests/unit/test_steady_0.py"
        held["files"][victim] = 100.0
        times[victim] = 100.0 * self.SHIFT + 6.0
        added = times[victim] - held["files"][victim] * self.SHIFT
        assert added >= drift.CI_DRIFT_SECONDS, added
        verdict, _shift, rows = drift.against(times, held)
        assert (verdict, rows) == ("ok", []), rows

    def test_the_seconds_are_counted_on_this_run_s_clock(self):
        """`expected` is the record *times the shift*, not the record.
        On a runner 18% faster than the one that recorded, a file at
        13.7s against 8.2s expected has added 5.5 seconds; measured
        against the raw 10.0s record it has added 3.7 and disappears.

        The whole rule is one machine against itself over time, so the
        seconds have to be counted on the clock the run actually had.
        Also found by mutating (`D3`) rather than by reading.
        """
        times, held = self._that_run()
        victim = "tests/unit/test_steady_0.py"
        held["files"][victim] = 10.0
        times[victim] = 10.0 * self.SHIFT + 5.5
        raw = times[victim] - held["files"][victim]
        assert raw < drift.CI_DRIFT_SECONDS, raw
        verdict, _shift, rows = drift.against(times, held)
        assert verdict == "drift", verdict
        assert [row[0] for row in rows] == [victim], rows

    def test_both_thresholds_are_stated(self):
        assert drift.CI_DRIFT_SECONDS > 0, drift.CI_DRIFT_SECONDS


class TestTheThreeFailuresAreTheRegressionSuite:
    """`UX-420`'s acceptance test, second clause: *the three failures
    above, replayed against the new rule, report nothing.*

    Each replays the **shape** `UX-418` measured, not a re-run of the
    numbers: CI is 1.05x the developer machine on the median listed file
    and 1.61-1.73x on two particular ones, neither having grown. Against
    the floors that shape is drift; against CI's own record of the same
    files it is a run that has not changed since the last one.
    """

    #: `tests/tiers.py`'s comment block, as ratios. The distortion is
    #: per file, which is the whole finding - so it is applied per file.
    OUTLIERS = {"tests/unit/test_output_schemas.py": 1.61,
                "tests/unit/test_marginal_efficiency_gate.py": 1.73}
    MEDIAN_SHIFT = 1.05

    def _a_ci_run(self):
        """The developer machine's record, distorted the way CI was."""
        return {name: seconds * self.OUTLIERS.get(name, self.MEDIAN_SHIFT)
                for name, seconds in tiers.recorded().items()}

    def test_the_two_outliers_are_still_files_in_the_lists(self):
        """If either is renamed this class silently stops replaying
        anything, which is how a regression suite becomes decoration."""
        listed = set(tiers.LARGE) | set(tiers.MEDIUM)
        assert set(self.OUTLIERS) <= listed, set(self.OUTLIERS) - listed

    def test_against_the_floors_that_run_is_exactly_the_three_failures(self):
        """The premise. Read against `tests/tiers.py` this synthetic run
        does report files - it has to, or the clauses below would be
        asserting that nothing happens to nothing."""
        found = drift.drift(self._a_ci_run())
        assert found, "the replayed distortion moves no file's tier"

    def test_read_against_cis_own_record_it_reports_nothing(self):
        """Failures 1 and 2 together: neither a fixed slack nor a single
        derived scale can absorb a per-file distortion, and neither has
        to, because the reference carries each file's own number."""
        on_ci = self._a_ci_run()
        verdict, _shift, rows = drift.against(on_ci, drift.record(on_ci))
        assert (verdict, rows) == ("ok", []), (verdict, rows[:3])

    def test_the_order_it_could_not_preserve_is_never_consulted(self):
        """Failure 3. Rank was the third answer and it does not survive
        a per-file distortion: on this run the two outliers pass files
        they are recorded below. The rule reports nothing anyway,
        because it compares each file to itself and not to its
        neighbours."""
        on_ci = self._a_ci_run()
        by_seconds = sorted(on_ci, key=on_ci.get, reverse=True)
        recorded_order = sorted(tiers.recorded(),
                                key=tiers.recorded().get, reverse=True)
        assert by_seconds != recorded_order, (
            "the replayed distortion did not reorder anything, so this "
            "clause is not replaying failure 3")
        verdict, _shift, rows = drift.against(on_ci, drift.record(on_ci))
        assert (verdict, rows) == ("ok", []), (verdict, rows[:3])


class TestEachComparisonRunsWhereItMeansSomething:
    """Two checks, two machines, and neither reads the other's numbers.

    `UX-418` established that the **floors** in `tests/tiers.py` describe
    a developer machine and cannot be compared to a report from CI's
    runner - a fixed slack, a derived scale and a rank comparison each
    reported files that had not drifted. `UX-420` added the comparison
    that does travel: CI against its own recorded numbers.

    So `make test-tiers` reads the floors here, CI reads the reference
    there, and a later round that crosses them will find these clauses.
    """

    MAKEFILE = REPO / "Makefile"
    WORKFLOW = REPO / ".github/workflows/ci.yml"

    def test_one_command_runs_the_suite_and_reads_its_report(self):
        text = self.MAKEFILE.read_text(encoding="utf-8")
        assert "test-tiers:" in text, (
            "no target runs the drift check, so nothing does")
        target = text.split("test-tiers:", 1)[1].split("\n\n", 1)[0]
        assert "--junitxml=" in target, target
        assert "tools/dev_tier_drift.py" in target, target
        assert ".PHONY:" in text and "test-tiers" in text.split(
            ".PHONY:", 1)[1].splitlines()[0], "test-tiers is not phony"

    def test_it_costs_a_parse_and_not_a_second_suite(self):
        for text, where in ((self.MAKEFILE.read_text(encoding="utf-8"),
                             "test-tiers:"),
                            (self.WORKFLOW.read_text(encoding="utf-8"),
                             "--against")):
            step = text.split(where, 1)[1].split("\n\n", 1)[0]
            assert "pytest" not in step, (where, step)

    def test_ci_reads_the_reference_and_not_the_floors(self):
        """The distinction the three failures bought. A CI step reading
        the floors is the defect; a CI step reading the reference is the
        fix, and they are one flag apart."""
        text = self.WORKFLOW.read_text(encoding="utf-8")
        runs = [line for line in text.splitlines()
                if "dev_tier_drift.py" in line and not
                line.strip().startswith("#")]
        assert runs, "CI runs no drift check at all"
        for line in runs:
            assert "--against" in line or "--against" in text.split(
                line, 1)[1].split("\n\n", 1)[0], (
                f"a CI step reads the developer floors: {line.strip()!r} - "
                f"see UX-418's outcome for the three ways that fails")

    def test_ci_writes_the_report_the_step_reads(self):
        text = self.WORKFLOW.read_text(encoding="utf-8")
        assert "--junitxml=" in text, (
            "no CI step writes a junit report, so the check reads nothing")

    def test_one_interpreter_records_so_there_is_one_reference(self):
        """Four jobs would be four references to keep true, which is the
        rot this item is mostly about."""
        text = self.WORKFLOW.read_text(encoding="utf-8")
        assert text.count("--junitxml=") == 1, (
            "more than one CI job writes a timing report; the reference "
            "is per runner-and-interpreter, so this needs a decision")
        assert "matrix.python-version == '3.11'" in text, text[:0]


class TestAnExcursionMustRepeat:
    """`UX-442`: a series, not a run.

    `test (3.11)` went red on `279900f`, a commit whose diff is one
    backlog file and one index row. The suite passed; the drift step
    reported `test_the_page_has_a_reader.py` at 13.9s against 7.1s
    recorded. The same file over four runs of that branch read
    `7.13, 7.13, 7.53, 13.85`, and the run that excursed had a *lower*
    shift and a *lower* spread than the run before it, which passed. One
    file swung; the machine did not.

    `UX-418` set two gates so a small file could not trip on a ratio and
    a big one could not trip on seconds. `UX-423` measured the shift's
    own dispersion so a slow runner is not read as drift. Neither
    measures **one file's** dispersion, and neither can - from a single
    run there is nothing to disperse.

    So the rule is agreement between runs, and the fixture has to be a
    series. Every clause below runs `main` several times over one carry
    file, which is what CI does with its cache.
    """

    #: Two files big enough that doubling them clears both gates -
    #: `CI_DRIFT_FACTOR` needs x1.5 and `CI_DRIFT_SECONDS` needs five
    #: seconds, and a file that only clears one is the case UX-418
    #: already covers.
    FLAKY = "tests/unit/test_the_page_has_geometry.py"
    STEADY = "tests/unit/test_the_journey_has_an_answer_key.py"

    def _run(self, tmp_path, capsys, over, carry=True):
        """One CI run: `over` are the files at twice their recorded time."""
        times = dict(tiers.recorded())
        for name in over:
            times[name] = times[name] * 2
        reference = tmp_path / "ref.json"
        reference.write_text(json.dumps(drift.record(dict(tiers.recorded()))),
                             encoding="utf-8")
        argv = [str(_report(tmp_path, times)), "--against", str(reference)]
        if carry:
            argv += ["--carry", str(tmp_path / "carry.json")]
        code = drift.main(argv)
        said = capsys.readouterr()
        return code, said.out + said.err

    def test_only_the_file_two_runs_agree_on_is_reported(self, tmp_path,
                                                         capsys):
        """The acceptance test. `FLAKY` is over the gates on runs 1 and
        3 with a clean run between; `STEADY` is over on 2 and 3. Only
        `STEADY` has drifted, and only `STEADY` is reported."""
        first, _said = self._run(tmp_path, capsys, [self.FLAKY])
        second, _said = self._run(tmp_path, capsys, [self.STEADY])
        third, said = self._run(tmp_path, capsys,
                                [self.STEADY, self.FLAKY])
        assert (first, second) == (0, 0), (
            f"a single run over the gates failed the build ({first}, "
            f"{second}); that is the red UX-442 was filed for")
        assert third == 1, (
            f"{self.STEADY} was over the gates on two consecutive runs "
            f"and nothing reported it - the rule now hides real drift")
        reported = said.split("slower than CI's own record", 1)[1]
        assert self.STEADY in reported, reported
        assert self.FLAKY not in reported, (
            f"{self.FLAKY} recovered on run 2 and excursed again on run "
            f"3. Two excursions are not two *consecutive* excursions, "
            f"and the run between is what says so")

    def test_a_clean_run_between_them_breaks_the_chain(self, tmp_path,
                                                       capsys):
        """The half that needs the carry written on runs that find
        nothing. An excursion, a run with nothing over the gates, then
        the same excursion again is two excursions and not two
        consecutive ones - and only an empty carry says so."""
        self._run(tmp_path, capsys, [self.STEADY])
        clean, _said = self._run(tmp_path, capsys, [])
        third, said = self._run(tmp_path, capsys, [self.STEADY])
        assert clean == 0, said
        assert third == 0, (
            "a run that found nothing left the previous run's finding in "
            "the carry, so an excursion either side of it confirmed")

    def test_the_run_that_only_saw_it_once_still_says_so(self, tmp_path,
                                                        capsys):
        """Not a failure and not silence. A gate that swallows the first
        sample entirely would leave the second red with no history a
        reader could see."""
        _code, said = self._run(tmp_path, capsys, [self.FLAKY])
        assert self.FLAKY in said and "UX-442" in said, said
        assert f"{drift.CI_DRIFT_RUNS} consecutive runs" in said, said

    def test_a_branch_with_no_history_reports_nothing(self, tmp_path,
                                                      capsys):
        """The cost, asserted rather than described: the first run of a
        branch has nothing to agree with, so it cannot report. A cache
        that failed to restore lands in the same state, which is why an
        unreadable carry is an empty history and not an error."""
        (tmp_path / "carry.json").write_text("not json", encoding="utf-8")
        code, _said = self._run(tmp_path, capsys, [self.STEADY])
        assert code == 0, (
            "an unreadable carry failed the build over its own absence")
        assert drift.carried(tmp_path / "carry.json") == [
            {self.STEADY}], (
            "the unreadable carry was not replaced by this run's finding, "
            "so the next run has nothing to agree with either")

    def test_without_a_carry_one_sample_still_decides(self, tmp_path,
                                                     capsys):
        """The rule needs memory, and a run given none has to say which
        rule it applied. Silently passing would turn a forgotten flag
        into a gate that cannot fail."""
        code, said = self._run(tmp_path, capsys, [self.STEADY], carry=False)
        assert code == 1, said
        assert "no --carry" in said, said

    def test_every_run_behind_this_one_must_agree(self):
        """`repeated` called directly, with a two-run history, because
        `CI_DRIFT_RUNS` is 2 today and no series the tool writes is long
        enough to tell `all` from `any`. The contract is *consecutive*,
        so a file missing from one of the runs behind this one has not
        drifted through all of them - and if the constant is ever raised,
        this is the clause that already says what raising it means."""
        row = (self.STEADY, 20.0, 10.0, 2.0)
        both = [{self.STEADY}, {self.STEADY}]
        gap = [{self.STEADY}, {self.FLAKY}]
        assert drift.repeated([row], both) == ([row], []), (
            "a file every run behind this one found was not confirmed")
        assert drift.repeated([row], gap) == ([], [row]), (
            "one run in the history was enough to confirm, so the rule "
            "is 'ever' rather than 'consecutively'")

    def test_the_history_is_bounded_by_the_constant(self, tmp_path,
                                                    capsys):
        """`CI_DRIFT_RUNS` is the whole rule, so the file it writes must
        not quietly accumulate a longer one - a carry holding every run
        a branch ever had would confirm on agreement with a fortnight
        ago."""
        for _ in range(4):
            self._run(tmp_path, capsys, [self.STEADY])
        held = json.loads((tmp_path / "carry.json").read_text(
            encoding="utf-8"))
        assert len(held["runs"]) == drift.CI_DRIFT_RUNS - 1, held["runs"]


class TestCiSuppliesTheMemoryTheRuleNeeds:
    """The rule above is only in force where CI hands it a series. The
    clauses that decide are in `TestAnExcursionMustRepeat`; these tie
    the workflow to them, and they are text about YAML - which is why
    they are not the ones the item rests on.
    """

    WORKFLOW = REPO / ".github/workflows/ci.yml"

    def _text(self):
        return self.WORKFLOW.read_text(encoding="utf-8")

    def test_the_drift_step_is_given_a_carry(self):
        text = self._text()
        step = text.split("--against", 1)[1].split("\n\n", 1)[0]
        assert "--carry" in step, (
            f"CI's drift step has no run-to-run memory, so one sample "
            f"decides it again - which is UX-442 undone: {step!r}")

    def test_the_carry_is_restored_and_saved_around_it(self):
        text = self._text()
        path = re.search(r'--carry "([^"]+)"', text).group(1)
        for action, why in (("cache/restore",
                             "nothing restores it, so every run is a first "
                             "run and the gate never reports"),
                            ("cache/save",
                             "nothing saves it, so this run's finding is "
                             "thrown away with the runner")):
            steps = [block for block in text.split("      - ")
                     if action in block and path in block]
            assert steps, f"{action}: {why}"

    def test_the_save_runs_when_the_step_reported(self):
        """The run worth remembering is the one that just failed, and
        a save gated on success would forget exactly it."""
        text = self._text()
        save = [block for block in text.split("      - ")
                if "cache/save" in block][0]
        # The step's own `if:`, not the block - the comment introducing
        # the next step says "always()" too, and reading the block let
        # this clause pass a mutation that removed the gate (R9).
        gate = [line for line in save.splitlines()
                if line.startswith("        if:")]
        assert gate and "always()" in gate[0], (
            "the carry is saved only on a green run, so a reported file "
            "cannot be confirmed by the run after it")

    def test_a_branch_reads_its_own_series(self):
        """Two branches sharing a carry would confirm one branch's
        excursion with another's, which is not agreement about anything."""
        text = self._text()
        # `\S+` would stop inside `${{ github.ref }}`, which is the
        # half that matters - take the rest of the line.
        keys = re.findall(r"key: (tier-carry-.*)", text)
        assert keys, "the carry cache has no key at all"
        for key in keys:
            assert "github.ref" in key, (
                f"the carry cache key {key!r} does not name the branch")

class TestTheRecordStepDoesNotBuryTheFailure:
    """`UX-441`. `UX-427`'s step prints this run's timings so the
    reference can be refreshed from a real runner, and `if: always()` is
    right: a red run's timings are still timings, and the reds are the
    runs a refresh most wants. But the document is one line per test
    file, it ran *after* the suite, and printed to stdout it was the
    last thing in the job's log. Twice in round 69 a red arrived that
    way; on `9675209` the failing assertion was never reached, because
    the dump is longer than any tail worth fetching.

    So the property is not "the step is gated" - it must not be - it is
    **the step prints a handful of lines**, and the document stays
    reachable somewhere that is not the log. The clause that decides is
    `test_a_recorded_run_prints_a_line_and_not_the_document`, which runs
    the tool both ways and counts; the workflow clauses only tie CI to
    the mode that measurement covers.
    """

    WORKFLOW = REPO / ".github/workflows/ci.yml"

    @classmethod
    def _steps(cls):
        """`{name: body}` for the job's steps, comments dropped."""
        text = cls.WORKFLOW.read_text(encoding="utf-8")
        steps, name = {}, None
        for line in text.splitlines():
            if line.strip().startswith("#"):
                continue
            started = re.match(r"      - name: (.+)", line)
            if started:
                name = started.group(1).strip()
                steps[name] = []
            elif name is not None and line.startswith("      - "):
                name = None
            elif name is not None and (line.startswith("        ")
                                       or not line.strip()):
                steps[name].append(line)
            elif name is not None:
                name = None
        return {key: "\n".join(body) for key, body in steps.items()}

    @classmethod
    def _recording(cls):
        """The step that runs `--record`, and the path it records to."""
        found = [(name, body) for name, body in cls._steps().items()
                 if "--record" in body]
        assert len(found) == 1, (
            f"{len(found)} CI steps record the timings, so which one this "
            f"item is about is a guess: {[name for name, _ in found]}")
        name, body = found[0]
        # Quoted, because the path CI records to contains a space
        # inside `${{ runner.temp }}` and `\S+` stops at it.
        argument = re.search(r'--record\s+("[^"]*"|\S+)',
                             body).group(1).strip('"')
        return name, body, argument

    def test_a_recorded_run_prints_a_line_and_not_the_document(self,
                                                               tmp_path,
                                                               capsys):
        """The measurement the rest of this class rests on. Both modes,
        same report, counted - because "writes a file" is only worth
        asserting in CI if it is what shortens the log."""
        report = _report(tmp_path, dict(tiers.recorded()))
        assert drift.main([str(report), "--record",
                           str(tmp_path / "ref.json")]) == 0
        to_a_file = capsys.readouterr().out.splitlines()
        assert drift.main([str(report), "--record", "-"]) == 0
        to_the_log = capsys.readouterr().out.splitlines()
        assert len(to_a_file) <= 2, (
            f"recording to a file printed {len(to_a_file)} lines; the "
            f"whole point is that the failure above it stays readable")
        assert len(to_the_log) > 50, (
            f"recording to stdout printed {len(to_the_log)} lines, so the "
            f"two modes no longer differ and this guard decides nothing")

    def test_ci_records_to_a_file(self):
        name, _body, argument = self._recording()
        assert argument != "-", (
            f"the {name!r} step dumps the whole reference to stdout again. "
            f"It runs after the suite, so on a red the document is the "
            f"tail of the log and the failing assertion is not - which is "
            f"the two reds UX-441 was filed for")
        assert "${{ runner.temp }}" in argument, (
            f"the {name!r} step records to {argument!r}, which is inside "
            f"the checkout - a workspace the next step and check-clean "
            f"both read")

    def test_it_still_runs_when_the_suite_fails(self):
        """The half `UX-427` chose and this item must not undo: gating
        the record on success loses exactly the runs worth recording."""
        name, body, _argument = self._recording()
        assert "always()" in body, (
            f"the {name!r} step no longer runs on a red, so the runs a "
            f"refresh most wants are the ones that record nothing")

    def test_the_document_is_still_a_click_away(self):
        """Writing it to a file and stopping there would not shorten the
        log, it would delete the record - which is `UX-427` undone."""
        _name, _body, argument = self._recording()
        uploads = [body for body in self._steps().values()
                   if "upload-artifact" in body and argument in body]
        assert uploads, (
            f"nothing uploads {argument!r}, so the timings are written "
            f"into a runner that is thrown away and UX-427's step now "
            f"records for nobody")

    def test_the_log_says_where_the_document_went(self):
        """The cost of taking it out of the log. The tool's own advice
        is *re-record with --record and commit*, and before this item
        the document that advice needs was the next thing on screen.
        Now it is an artifact, so the step has to name it - otherwise
        the reader is left with advice and no numbers."""
        _name, body, _argument = self._recording()
        uploaded = [re.search(r"\n          name: (\S+)", other).group(1)
                    for other in self._steps().values()
                    if "upload-artifact" in other]
        assert uploaded, "no artifact is uploaded at all"
        assert any(name in body for name in uploaded), (
            f"the recording step's own output never names any of "
            f"{uploaded}, so a reader following 're-record with --record' "
            f"has nowhere to get this run's numbers from")

class TestTheToolIsRunnable:
    def test_it_runs_as_a_module_and_says_what_it_checked(self, tmp_path):
        report = _report(tmp_path, {**tiers.recorded(), SMALL_FILE: 0.2})
        done = subprocess.run(
            [sys.executable, "tools/dev_tier_drift.py", str(report)],
            capture_output=True, text=True, cwd=REPO, timeout=60)
        assert done.returncode == 0, done.stderr
        assert "tiers ok" in done.stdout, done.stdout
        # The boundaries, printed whether or not anything drifted: they
        # are what decides, and the run that reddens is not the first
        # place they should be visible.
        assert "against the declared floors" in done.stdout, done.stdout
        assert str(tiers.LARGE_FLOOR_S) in done.stdout, done.stdout


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
