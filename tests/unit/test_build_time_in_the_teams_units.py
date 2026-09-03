"""UX-596: the same saving, in the unit the lead argues in.

Measured on `main` before this item, on `tests/fixtures/macro_micro/run`:

    core.bst      19.1s (44.1% of path)  -> fixing it saves 12.1s (26.1%)
    Together, the top 3 are worth 23.1s (50% of the build)

Every price is in build seconds, for one project, and nothing converts
them to anything a budget speaks (`roles.md`'s R8 row, `UX-580`).

The trap this file guards is the item's own Out of Scope: **a made-up
default rate presented as a figure is the anecdote this replaces**. So
two properties, and the second is why the first is not enough - with no
rate the report is byte-identical to before, and with one, no converted
figure can be printed apart from the rate that converted it.
"""
import json
import os
import pathlib
import subprocess
import sys

import pytest

from bga.analyzer import BuildEfficiencyAnalyzer
from bga.findings import compute_findings
from bga.report import rate
from bga.report.text import _format_in_your_units, format_text

REPO = pathlib.Path(__file__).resolve().parents[2]
FIXTURE = REPO / "tests/fixtures/macro_micro/run"

RATE = "90 USD/machine-hour"
HOURS = "1.5 engineer-hours/build-hour"


@pytest.fixture(scope="module")
def analysis():
    analyzer = BuildEfficiencyAnalyzer()
    analyzer.load(FIXTURE)
    return analyzer.analyze()


def _block(analysis, value, monkeypatch):
    if value is None:
        monkeypatch.delenv(rate.ENV_VAR, raising=False)
    else:
        monkeypatch.setenv(rate.ENV_VAR, value)
    return _format_in_your_units(analysis, compute_findings(analysis))


class TestWithNoRateNothingIsInvented:

    def test_the_block_is_absent_rather_than_empty(self, analysis, monkeypatch):
        assert _block(analysis, None, monkeypatch) == []

    def test_and_the_report_says_nothing_about_units(
            self, analysis, monkeypatch):
        monkeypatch.delenv(rate.ENV_VAR, raising=False)
        text = format_text(analysis)

        assert "In Your Units" not in text
        assert "USD" not in text and "engineer-hour" not in text

    def test_no_rate_is_carried_anywhere_to_fall_back_on(self):
        """The item's Out of Scope, as a guard rather than a promise: a
        default would make every figure below a number `bga` appears to
        have measured."""
        assert rate.supplied({}) is None
        assert rate.supplied({"OTHER": RATE}) is None
        source = (REPO / "bga/report/rate.py").read_text()
        assert "DEFAULT" not in source


class TestEveryConvertedFigureNamesItsRate:

    def test_the_rate_is_stated_as_the_reader_s_input(
            self, analysis, monkeypatch):
        lines = _block(analysis, RATE, monkeypatch)

        assert lines[1].strip().startswith(f"rate: {RATE}")
        assert "an input you supplied" in lines[1]
        assert "not anything this run measured" in lines[1]

    def test_no_converted_figure_is_printed_apart_from_its_rate(
            self, analysis, monkeypatch):
        """The acceptance test's mutation, as the assertion: find every
        line carrying a figure in the supplied unit and require the rate
        on that same line - not merely somewhere in the block, which a
        heading would satisfy while every pasted row travelled alone."""
        lines = _block(analysis, RATE, monkeypatch)
        converted = [line for line in lines[2:] if " USD" in line]

        assert converted, "no figure was converted at all"
        for line in converted:
            assert f"at {RATE}" in line, line

    def test_the_same_holds_for_an_engineer_hours_rate(
            self, analysis, monkeypatch):
        lines = _block(analysis, HOURS, monkeypatch)
        converted = [line for line in lines[2:] if " engineer-hours" in line]

        assert converted
        for line in converted:
            assert f"at {HOURS}" in line, line

    def test_the_seconds_stay_beside_the_conversion(
            self, analysis, monkeypatch):
        """The measurement is the seconds; the conversion is the
        reader's arithmetic on top. A row that dropped the seconds would
        publish the derived number as the fact."""
        lines = _block(analysis, RATE, monkeypatch)

        assert "12.05s = 0.30 USD at 90 USD/machine-hour" in lines[2]


class TestTheArithmeticAndWhatItIsAppliedTo:

    def test_an_hour_of_build_costs_the_rate(self):
        supplied = rate.parse(RATE)

        assert rate.convert(3_600_000_000, supplied) == pytest.approx(90.0)
        assert rate.convert(1_800_000_000, supplied) == pytest.approx(45.0)

    def test_the_joint_figure_is_published_not_summed(
            self, analysis, monkeypatch):
        """`UX-230`'s rule: two fixes on one chain do not add. The
        together row is `joint-saving`'s own number, and on this fixture
        that number differs from the sum of the rows above it."""
        lines = _block(analysis, RATE, monkeypatch)
        findings = compute_findings(analysis)
        joint = next(f for f in findings if f["id"] == "joint-saving")
        published = joint["evidence"]["joint_saving_us"]
        rows = [action for action in lines[2:-1] if "together" not in action]

        assert f"{published / 1e6:.2f}s" in lines[-2]
        assert len(rows) == 3
        assert published != 12_050_000 + 4_000_000 + 4_000_000

    def test_a_run_that_prices_no_fix_says_so(self, analysis, monkeypatch):
        """Silence would read as "this build is worth nothing to fix",
        which is a claim, and not the one being made."""
        monkeypatch.setenv(rate.ENV_VAR, RATE)

        lines = _format_in_your_units(analysis, [])

        assert "nothing to convert" in " ".join(lines)
        assert not [line for line in lines if " USD " in line]


class TestARateThatCannotBeUsedIsNamed:

    @pytest.mark.parametrize("supplied", [
        "cheap", "90USD/machine-hour", "90 USD", "90 USD/fortnight",
        "-90 USD/machine-hour", "0 USD/machine-hour"])
    def test_it_refuses_rather_than_guessing(self, supplied):
        assert rate.parse(supplied).get("error"), supplied

    def test_and_the_report_says_why_instead_of_falling_silent(
            self, analysis, monkeypatch):
        """A reader who set a rate and got the unconverted report has no
        way to learn that the tool did not understand it."""
        lines = _block(analysis, "cheap", monkeypatch)

        assert "not applied" in lines[1]
        assert rate.ENV_VAR in lines[1]
        assert not [line for line in lines if " USD " in line]

    def test_both_denominators_are_accepted_and_kept_apart(self):
        """They are different arguments - what the runner cost, and what
        the wait cost - so the record keeps the one that was written."""
        assert rate.parse(RATE)["per"] == "machine-hour"
        assert rate.parse(HOURS)["per"] == "build-hour"


class TestTheRateIsNotAMeasurement:

    def test_it_never_reaches_the_published_document(self):
        """The seconds are what this run measured and the payload
        publishes them; the rate is the reader's input, and a
        schema-described record of a build is not where an input goes."""
        done = subprocess.run(
            [sys.executable, "-m", "bga.cli", "analyze", str(FIXTURE),
             "--format", "json"],
            capture_output=True, text=True, cwd=REPO, timeout=300,
            env={**os.environ, "PYTHONPATH": str(REPO),
                 rate.ENV_VAR: RATE})
        assert done.returncode == 0, done.stderr[-2000:]
        payload = json.loads(done.stdout)

        assert "USD" not in json.dumps(payload)
        assert rate.ENV_VAR not in json.dumps(payload)
