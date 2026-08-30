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


class TestItRunsWhereItsNumbersMeanSomething:
    """`UX-418` asks for a CI step and this is not one, which is a
    deviation with three CI runs behind it: the floors are seconds
    measured on a developer machine, and CI's runner differs from it
    *per file* rather than by a factor, so a fixed slack, a derived
    scale and a rank comparison each reported files that had not
    drifted. These clauses hold the decision in place - a later round
    that moves the step into CI without a CI-side reference will find
    them.
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
        target = self.MAKEFILE.read_text(encoding="utf-8").split(
            "test-tiers:", 1)[1].split("\n\n", 1)[0]
        assert target.count("pytest") == 0, target
        assert target.count("$(MAKE) test") == 1, target

    def test_ci_does_not_run_it_and_says_why(self):
        """An absence a later round could read as an oversight is one
        somebody restores. The workflow states the reason where the
        step would have gone."""
        text = self.WORKFLOW.read_text(encoding="utf-8")
        assert "tools/dev_tier_drift.py" not in text.replace(
            "`make test-tiers`", ""), (
            "the drift check is back in CI - see UX-418's outcome and "
            "UX-420 for what that needs first")
        assert "UX-420" in text, (
            "the workflow does not say why the check is absent, so the "
            "absence reads as an oversight")


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
