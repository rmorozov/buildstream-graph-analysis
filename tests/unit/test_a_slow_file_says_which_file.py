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
import pathlib
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

    def test_the_scale_moves_the_floors_and_not_the_measurement(self):
        """A step that reported a time nobody could reproduce would be
        worse than none, so the scale moves the line."""
        scale = 2.0
        just_under = tiers.LARGE_FLOOR_S * scale - 0.001
        assert drift.tier_for(just_under) == "large"
        assert drift.tier_for(just_under, scale) == "medium"
        assert drift.tier_for(tiers.LARGE_FLOOR_S * scale, scale) == "large"


class TestItCalibratesBeforeItCompares:
    """`UX-418`'s own first CI run is why this class exists.

    The step called three medium files large at 20.4-21.5s. Nothing had
    drifted: CI's runner is slower than the machine `tests/tiers.py`'s
    numbers were taken on, and single-process here those files are
    11.3-13.5s. The version that shipped carried a fixed
    `PARALLEL_REPORT_SLACK = 1.35`, sized on this container - **wrong by
    a factor on the first foreign clock it met**, which is what a
    constant standing in for a measurement does.

    So the ratio is derived from the report, and these clauses are
    about that derivation rather than about any particular machine.
    """

    def test_every_listed_file_carries_the_measurement_that_placed_it(self):
        """What the calibration reads. A tier entry without its seconds
        is a file the scale cannot be read against - and, before this,
        a file whose placement had no stated evidence at all."""
        reference = tiers.recorded()
        missing = [name for name in (*tiers.LARGE, *tiers.MEDIUM)
                   if name not in reference]
        assert missing == [], (
            f"{missing} are listed with no measured seconds beside them")
        assert len(reference) >= len(tiers.LARGE) + len(tiers.MEDIUM)

    def test_a_report_on_the_tiers_own_clock_reads_as_one(self, tmp_path):
        """The identity case: a report that reproduces the recorded
        numbers exactly must calibrate to 1.0, or the scale is measuring
        something other than the clock."""
        report = _report(tmp_path, tiers.recorded())
        assert drift.clock(drift.measured(report)) == pytest.approx(1.0)

    def test_a_slower_runner_reads_as_slower(self, tmp_path):
        report = _report(tmp_path, {name: seconds * 1.6 for name, seconds
                                    in tiers.recorded().items()})
        assert drift.clock(drift.measured(report)) == pytest.approx(1.6)

    def test_one_file_cannot_move_the_scale(self, tmp_path):
        """A median, not a mean. A scale any single file can move is a
        scale a slow test can talk its way out of."""
        times = dict(tiers.recorded())
        first = sorted(times)[0]
        times[first] = times[first] * 50
        report = _report(tmp_path, times)
        assert drift.clock(drift.measured(report)) == pytest.approx(1.0)

    def test_a_slower_runner_does_not_make_a_listed_file_drift(self,
                                                               tmp_path):
        """The failure this class was written for, as a clause."""
        report = _report(tmp_path, {name: seconds * 1.6 for name, seconds
                                    in tiers.recorded().items()})
        times = drift.measured(report)
        scale = drift.clock(times) * tiers.TIER_DRIFT_MARGIN
        assert drift.drift(times, scale) == []

    def test_a_real_drift_still_shows_through_a_slow_runner(self, tmp_path):
        """And the other half: calibration must not become an excuse."""
        times = {name: seconds * 1.6 for name, seconds
                 in tiers.recorded().items()}
        victim = tiers.MEDIUM[0]
        times[victim] = tiers.LARGE_FLOOR_S * 1.6 * 3
        report = _report(tmp_path, times)
        read = drift.measured(report)
        scale = drift.clock(read) * tiers.TIER_DRIFT_MARGIN
        assert [row[0] for row in drift.drift(read, scale)] == [victim]

    def test_it_refuses_to_compare_two_clocks_it_cannot_relate(self,
                                                              tmp_path):
        """A report measuring none of the listed files gives no reading,
        and the step says so rather than comparing seconds from one
        machine against floors from another - which is the whole
        defect."""
        report = _report(tmp_path, {SMALL_FILE: 99.0})
        assert drift.clock(drift.measured(report)) is None
        assert drift.main([str(report)]) == 2

    def test_the_margin_is_stated_and_above_one(self):
        assert tiers.TIER_DRIFT_MARGIN > 1.0, tiers.TIER_DRIFT_MARGIN

    def test_a_listed_file_is_read_from_the_list_it_is_in(self):
        assert drift.listed_tier(tiers.LARGE[0]) == "large"
        assert drift.listed_tier(tiers.MEDIUM[0]) == "medium"
        assert drift.listed_tier(SMALL_FILE) == "small"


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
        report = _report(tmp_path, {**tiers.recorded(), SMALL_FILE: 51.0})
        assert drift.main([str(report)]) == 1
        said = capsys.readouterr().err
        assert SMALL_FILE in said, said
        assert "51.0s" in said, said
        assert "listed small, measured large" in said, said

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


class TestItRunsWhereAFullRunAlreadyHappens:
    """`UX-418`: *it runs where a full run already happens, so it costs
    a parse rather than a second suite.* Both halves of that are facts
    about the workflow, and nothing else reads them."""

    WORKFLOW = REPO / ".github/workflows/ci.yml"

    def test_the_suite_writes_the_report_the_step_reads(self):
        text = self.WORKFLOW.read_text(encoding="utf-8")
        assert "--junitxml=" in text, (
            "no CI step writes a junit report, so the drift step has "
            "nothing to read")
        assert "tools/dev_tier_drift.py" in text, (
            "the tool is not run in CI, which is the only place a full "
            "run happens")

    def test_it_does_not_run_a_second_suite(self):
        text = self.WORKFLOW.read_text(encoding="utf-8")
        step = text.split("tools/dev_tier_drift.py", 1)[1].splitlines()[0]
        assert "pytest" not in step and "make test" not in step, step


class TestTheToolIsRunnable:
    def test_it_runs_as_a_module_and_says_what_it_checked(self, tmp_path):
        report = _report(tmp_path, {**tiers.recorded(), SMALL_FILE: 0.2})
        done = subprocess.run(
            [sys.executable, "tools/dev_tier_drift.py", str(report)],
            capture_output=True, text=True, cwd=REPO, timeout=60)
        assert done.returncode == 0, done.stderr
        assert "tiers ok" in done.stdout, done.stdout
        # The derived scale, printed whether or not anything drifted:
        # it is the number that decides, and the run that reddens is not
        # the first place it should be visible.
        assert "against the tiers' own clock" in done.stdout, done.stdout
        assert str(tiers.TIER_DRIFT_MARGIN) in done.stdout, done.stdout


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
