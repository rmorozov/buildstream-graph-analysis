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
    """The floors stay the authority for *placing* a file, and
    `--exact` is where they are read directly."""

    def test_the_boundaries_are_the_declared_floors(self):
        assert drift.tier_for(tiers.MEDIUM_FLOOR_S - 0.001) == "small"
        assert drift.tier_for(tiers.MEDIUM_FLOOR_S) == "medium"
        assert drift.tier_for(tiers.LARGE_FLOOR_S - 0.001) == "medium"
        assert drift.tier_for(tiers.LARGE_FLOOR_S) == "large"


class TestItComparesRankAndNotSeconds:
    """`UX-418`'s two CI runs are why this class exists.

    The step first called three medium files large at 20.4-21.5s; on the
    machine `tests/tiers.py`'s numbers were taken on they are 11.3-13.5s
    single-process. A fixed slack was the first answer and was wrong by
    a factor on the first foreign clock it met. A scale derived from the
    report was the second, and was wrong too: on CI the **median**
    listed file ran at 1.05x its recorded number while those two ran at
    1.61x and 1.73x, neither having grown. The difference is per file.

    So the comparison is the order, which travels. These clauses are
    about that and about the one thing it costs.
    """

    def test_every_listed_file_carries_the_measurement_that_placed_it(self):
        """A tier entry without its seconds is a file whose placement
        has no stated evidence - and `recorded()` is what reads them."""
        reference = tiers.recorded()
        missing = [name for name in (*tiers.LARGE, *tiers.MEDIUM)
                   if name not in reference]
        assert missing == [], (
            f"{missing} are listed with no measured seconds beside them")

    def test_the_boundary_is_the_middle_of_the_tier_above(self, tmp_path):
        report = _report(tmp_path, tiers.recorded())
        limits = drift.boundaries(drift.measured(report))
        assert set(limits) == {"small", "medium"}, limits
        large = sorted(tiers.recorded()[n] for n in tiers.LARGE)
        assert limits["medium"] == pytest.approx(
            large[len(large) // 2] if len(large) % 2
            else (large[len(large) // 2 - 1] + large[len(large) // 2]) / 2)
        assert limits["small"] < limits["medium"], limits

    @pytest.mark.parametrize("factor", [0.5, 1.0, 2.0, 5.0])
    def test_a_uniformly_different_clock_changes_nothing(self, tmp_path,
                                                         factor):
        """The property the whole redesign is for: multiply every
        measurement and the verdict is identical, because both sides of
        every comparison move together."""
        report = _report(tmp_path, {name: seconds * factor for name, seconds
                                    in tiers.recorded().items()})
        times = drift.measured(report)
        assert drift.drift(times, drift.boundaries(times)) == []

    def test_a_real_drift_shows_through_any_clock(self, tmp_path):
        """And calibration must not become an excuse."""
        times = {name: seconds * 5 for name, seconds
                 in tiers.recorded().items()}
        victim = tiers.MEDIUM[0]
        times[victim] = max(times[n] for n in tiers.LARGE) * 2
        report = _report(tmp_path, times)
        read = drift.measured(report)
        found = drift.drift(read, drift.boundaries(read))
        assert [row[0] for row in found] == [victim], found

    def test_what_the_rank_rule_costs_is_a_file_just_over_its_floor(
            self, tmp_path):
        """Stated as a clause rather than left to be discovered: a
        medium file a second over the large floor is *not* reported,
        because it has not outrun its neighbours. `--exact` is the more
        sensitive rule, and only means anything on the machine the
        floors were measured on."""
        times = dict(tiers.recorded())
        victim = tiers.MEDIUM[0]
        times[victim] = tiers.LARGE_FLOOR_S + 1
        report = _report(tmp_path, times)
        read = drift.measured(report)
        assert drift.drift(read, drift.boundaries(read)) == []
        assert [row[0] for row in drift.by_floors(read)] == [victim]

    def test_it_refuses_a_report_it_cannot_place_a_boundary_from(
            self, tmp_path):
        """A median drawn from almost nothing is not a boundary, and
        comparing against one is the shape of guard `UX-403`'s census
        exists to find."""
        report = _report(tmp_path, {SMALL_FILE: 99.0})
        assert drift.boundaries(drift.measured(report)) == {}
        assert drift.main([str(report)]) == 2


class TestItFailsNamingTheFile:
    """`UX-418`'s whole complaint about the status quo: the small-tier
    timeout does catch this, and it fails saying *the small tier took
    longer than the budget* - a number, not a file."""

    def test_an_unlisted_file_over_the_medium_floor_is_named(self, tmp_path):
        report = _report(tmp_path, {SMALL_FILE: tiers.MEDIUM_FLOOR_S + 0.5})
        found = drift.by_floors(drift.measured(report))
        assert [row[0] for row in found] == [SMALL_FILE], found
        assert found[0][2:] == ("small", "medium"), found

    def test_the_message_carries_the_name_and_the_seconds(self, tmp_path,
                                                          capsys):
        report = _report(tmp_path, {**tiers.recorded(), SMALL_FILE: 51.0})
        assert drift.main([str(report), "--exact"]) == 1
        said = capsys.readouterr().err
        assert SMALL_FILE in said, said
        assert "51.0s" in said, said
        assert "listed small, measured large" in said, said

    def test_a_file_inside_its_tier_is_not_named(self, tmp_path):
        report = _report(tmp_path, {SMALL_FILE: tiers.MEDIUM_FLOOR_S - 0.1})
        assert drift.by_floors(drift.measured(report)) == []

    def test_a_listed_file_at_its_own_size_is_not_named(self, tmp_path):
        report = _report(tmp_path, {tiers.LARGE[0]: tiers.LARGE_FLOOR_S + 30})
        assert drift.by_floors(drift.measured(report)) == []

    def test_a_file_that_got_faster_is_not_a_failure(self, tmp_path):
        """The other direction wastes nothing, and reporting it would
        red the build on an ordinary fast run."""
        report = _report(tmp_path, {tiers.LARGE[0]: 0.1})
        assert drift.by_floors(drift.measured(report)) == []


class TestItCannotPassOverNothing:
    """The mistake `UX-403`'s census exists to find, in the instrument
    written to fix it: a report whose classnames resolve to no file
    would make every clause above vacuous."""

    def test_an_empty_report_is_an_error_not_a_pass(self, tmp_path):
        path = tmp_path / "junit.xml"
        path.write_text("<testsuites><testsuite /></testsuites>",
                        encoding="utf-8")
        assert drift.main([str(path)]) == 2
        assert drift.main([str(path), "--exact"]) == 2

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
        # The boundaries, printed whether or not anything drifted: they
        # are what decides, and the run that reddens is not the first
        # place they should be visible.
        assert "the median of the tier above" in done.stdout, done.stdout


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
