"""UX-611: `bga whatif` prices its projection through the same converter.

Measured on the base commit, on `tests/fixtures/macro_micro/run`, with
`BGA_RATE=90 USD/machine-hour` set - the output was byte-identical to
the run with no rate at all:

    Makespan 43.200s -> 23.150s (saves 20.050s)

`UX-596` converted the headline and the plan; `bga whatif` was outside
its declared surface and kept printing the one unit the tool measures.

The property is **one rule, not two**. So the clause that carries this
file replaces `report.rate.phrase` with a sentinel and requires the
sentinel in `whatif`'s own output: a renderer that had grown its own
multiplication would go on printing a correct-looking figure, and only
reaching through the converter can be seen from outside.
"""
import json
import pathlib

import pytest

from bga import whatif
from bga.analyzer import BuildEfficiencyAnalyzer
from bga.report import rate

REPO = pathlib.Path(__file__).resolve().parents[2]
FIXTURE = REPO / "tests/fixtures/macro_micro/run"

RATE = "90 USD/machine-hour"
HOURS = "1.5 engineer-hours/build-hour"
CHOSEN = ["core.bst", "lib-b.bst", "lib-d.bst"]


@pytest.fixture(scope="module")
def analyzed():
    analyzer = BuildEfficiencyAnalyzer()
    analyzer.load(FIXTURE)
    return analyzer.analyze(FIXTURE), analyzer.graph


@pytest.fixture(scope="module")
def document(analyzed):
    result, graph = analyzed
    return whatif.project(result, graph, CHOSEN)


def _render(document, value, monkeypatch):
    if value is None:
        monkeypatch.delenv(rate.ENV_VAR, raising=False)
    else:
        monkeypatch.setenv(rate.ENV_VAR, value)
    return whatif.render(document)


class TestWithNoRateTheProjectionIsUnchanged:

    def test_nothing_is_added_and_nothing_is_invented(
            self, document, monkeypatch):
        lines = _render(document, None, monkeypatch)

        assert not [line for line in lines if "In your units" in line]
        assert not [line for line in lines if "USD" in line]

    def test_the_saving_is_still_published_in_seconds(
            self, document, monkeypatch):
        """The measurement is the seconds. The conversion is arithmetic
        on top of it, so it may not replace it."""
        lines = _render(document, RATE, monkeypatch)

        assert "(saves 20.050s)" in lines[1]


class TestTheProjectedSavingIsConverted:

    def test_the_saving_reaches_the_reader_s_unit(
            self, document, monkeypatch):
        converted = [line for line in _render(document, RATE, monkeypatch)
                     if "In your units" in line]

        assert converted, "the projected saving was not converted at all"
        assert "0.50 USD" in converted[0], converted[0]

    def test_no_converted_figure_travels_without_its_rate(
            self, document, monkeypatch):
        """`UX-596`'s rule, applied here: a row pasted into an issue
        alone must still say what converted it."""
        lines = _render(document, RATE, monkeypatch)
        preamble = rate.preamble(rate.parse(RATE))
        carrying = [line for line in lines
                    if " USD" in line and line.strip() != preamble]

        assert carrying, "no figure was converted at all"
        for line in carrying:
            assert f"at {RATE}" in line, line

    def test_the_seconds_stay_beside_the_conversion(
            self, document, monkeypatch):
        lines = _render(document, RATE, monkeypatch)

        assert "saves 20.050s = 0.50 USD at 90 USD/machine-hour" in lines[2]

    def test_the_rate_is_named_as_the_reader_s_input(
            self, document, monkeypatch):
        lines = _render(document, RATE, monkeypatch)

        assert lines[3].strip().startswith(f"rate: {RATE}")
        assert "an input you supplied" in lines[3]
        assert "not anything this run measured" in lines[3]

    def test_the_other_denominator_converts_too(self, document, monkeypatch):
        converted = [line for line in _render(document, HOURS, monkeypatch)
                     if "In your units" in line]

        assert converted
        assert f"engineer-hours at {HOURS}" in converted[0], converted[0]


class TestOneConverterAndNotTwo:

    def test_the_figure_comes_from_report_rate_and_not_a_copy(
            self, document, monkeypatch):
        """The Acceptance Test's mutation as an assertion. Replacing
        `report.rate.phrase` must change what `whatif` prints; a
        renderer carrying its own multiplication would be untouched by
        this and still look right."""
        monkeypatch.setenv(rate.ENV_VAR, RATE)
        monkeypatch.setattr(rate, "phrase",
                            lambda us, supplied: "THROUGH-THE-CONVERTER")

        lines = whatif.render(document)

        assert [line for line in lines if "THROUGH-THE-CONVERTER" in line], (
            "whatif did not reach report.rate.phrase for its figure")

    def test_the_rounding_and_vocabulary_are_the_converter_s(
            self, document, monkeypatch):
        """Not a restatement of `rate.py`'s formatting: the expected
        string is asked of `rate.phrase` itself, so the two surfaces
        cannot round or name the unit differently."""
        lines = _render(document, RATE, monkeypatch)
        saving_us = document["projected"]["joint_saving_us"]
        expected = rate.phrase(saving_us, rate.parse(RATE))

        assert expected in lines[2], (expected, lines[2])

    def test_whatif_carries_no_second_conversion_of_its_own(self):
        """`rate.convert` is the one place build seconds meet a rate."""
        source = (REPO / "bga/whatif.py").read_text()

        assert "3_600_000_000" not in source
        assert "3600" not in source


class TestARateThatCannotBeUsedIsNamed:

    def test_it_says_why_instead_of_falling_silent(
            self, document, monkeypatch):
        lines = _render(document, "cheap", monkeypatch)

        assert [line for line in lines if "not applied" in line], lines
        assert [line for line in lines if rate.ENV_VAR in line]
        assert not [line for line in lines if " USD " in line]

    def test_a_refused_selection_prices_nothing(self, analyzed, monkeypatch):
        """A refusal has no projected saving, so there is no figure to
        convert - and a rate beside a refusal would read as one."""
        result, graph = analyzed
        monkeypatch.setenv(rate.ENV_VAR, RATE)

        lines = whatif.render(whatif.project(result, graph, ["nope.bst"]))

        assert not [line for line in lines if "In your units" in line]
        assert not [line for line in lines if "USD" in line]


class TestTheRateIsNotAMeasurement:

    def test_it_never_reaches_the_whatif_document(
            self, analyzed, monkeypatch):
        """`whatif/v1` is a schema-described record of what this run
        measured; the rate is the reader's input and the multiplication
        is a rendering."""
        result, graph = analyzed
        monkeypatch.setenv(rate.ENV_VAR, RATE)

        payload = json.dumps(whatif.project(result, graph, CHOSEN),
                             default=str)

        assert "USD" not in payload
        assert rate.ENV_VAR not in payload


class TestTheCommandItself:

    def test_bga_whatif_under_a_set_rate(self, monkeypatch, capsys):
        """The Acceptance Test, through the command a reader types."""
        from bga.cli import main

        monkeypatch.setenv(rate.ENV_VAR, RATE)
        code = main(["whatif", str(FIXTURE)]
                    + [arg for uid in CHOSEN for arg in ("--element", uid)])
        out = capsys.readouterr().out

        assert code == 0
        assert "In your units: saves 20.050s = 0.50 USD at 90 USD/machine-hour" in out
