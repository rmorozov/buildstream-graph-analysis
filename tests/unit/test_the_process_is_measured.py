"""`tools/dev_process_bands.py`, held to the record it reads.

The playbook's Maintenance stage says detection "stays entirely
deterministic, with no model involved" and that the script "is version
controlled and unit tested". This is that half.

Every clause here works on a synthetic Outcome rather than on the real
backlog, because a guard that asserts today's rate is a guard that
reddens on the next honest round - the numbers are supposed to move.
What must not move is what each phrase counts.
"""
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools import dev_process_bands as bands                    # noqa: E402


def task(outcome=None, motivation=""):
    """A task file's text, with the Outcome only where one is given."""
    text = f"# UX-9999: a thing\n\n## Motivation\n\n{motivation}\n"
    if outcome is not None:
        text += f"\n## Outcome (round 1, 2026-01-01)\n\n{outcome}\n"
    return text


def written(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


class TestItReadsTheOutcomeAndOnlyTheOutcome:
    def test_an_item_with_no_outcome_is_not_counted(self, tmp_path):
        assert bands.read(written(tmp_path, "UX-0001-x.md", task())) is None

    def test_a_phrase_in_the_motivation_is_not_this_item_s(self, tmp_path):
        """The Motivation quotes other items constantly - that is what
        the backlog is for. Counting those would make every item that
        cites `UX-420` look like it found a guard of its own."""
        text = task(outcome="Nothing notable.",
                    motivation="UX-412's C3 did not discriminate.")
        found = bands.read(written(tmp_path, "UX-0001-x.md", text))
        assert found["non_discriminating"] is False, found


class TestEachSignalCountsWhatItSays:
    @pytest.mark.parametrize("key,outcome", (
        ("falsified", "### Mutations verified red and reverted (3)"),
        ("falsified", "One mutation verified red and reverted."),
        ("non_discriminating", "B2 did not discriminate until D3 said so."),
        ("non_discriminating", "a non-discriminating guard of its own"),
        ("premise_false", "The whole Motivation rested on a false premise."),
        ("premise_false", "its premise was false, and that is recorded"),
    ))
    def test_a_phrase_the_repository_writes_is_caught(self, tmp_path, key,
                                                      outcome):
        found = bands.read(written(tmp_path, "UX-0001-x.md", task(outcome)))
        assert found[key] is True, (key, outcome, found)

    @pytest.mark.parametrize("key", ("falsified", "non_discriminating",
                                     "premise_false"))
    def test_an_ordinary_outcome_trips_nothing(self, tmp_path, key):
        found = bands.read(written(tmp_path, "UX-0001-x.md", task(
            "The gap is closed and the suite is green.")))
        assert found[key] is False, (key, found)


class TestTheDeviationSignalIsInverted:
    """It is the one row whose pattern matches the *absence* of the
    thing counted, because the section is mandatory and says "None."
    when there was nothing to report. Getting the polarity backwards
    would report a disciplined round as a sloppy one."""

    def test_none_is_not_a_deviation(self, tmp_path):
        found = bands.read(written(tmp_path, "UX-0001-x.md", task(
            "### Deviation from the Required Fix\n\n- **None.** It holds.")))
        assert found["deviation_stated"] is True
        assert found["deviated"] is False, found

    def test_anything_else_is(self, tmp_path):
        found = bands.read(written(tmp_path, "UX-0001-x.md", task(
            "### Deviation from the Required Fix\n\n- The acceptance test's "
            "first clause cannot be met by the design it mandates.")))
        assert found["deviated"] is True, found

    def test_an_item_with_no_such_section_is_counted_neither_way(self,
                                                                 tmp_path):
        """Outcomes predating the heading exist. Counting them as
        deviations would put a step in the series that is a change of
        convention rather than a change of behaviour."""
        found = bands.read(written(tmp_path, "UX-0001-x.md",
                                   task("Closed, and nothing to add.")))
        assert found["deviation_stated"] is False
        assert found["deviated"] is False, found


class TestTheCensusAndTheReport:
    def test_the_window_is_the_most_recent_ids(self, tmp_path):
        """Sorted by filename, which is why `UX-0001` is zero-padded -
        a window over lexical order is a window over time only while
        that holds, and `test_docs_links_and_commands.py` enforces it."""
        for index in range(1, 6):
            written(tmp_path, f"UX-000{index}-x.md",
                    task("Mutations verified red." if index >= 4 else "ok"))
        rows, totals = bands.census(tmp_path.glob("UX-*.md"))
        assert [name for name, _f in rows] == [
            f"UX-000{i}-x.md" for i in range(1, 6)]
        assert totals["falsified"] == 2
        assert sum(1 for _n, f in rows[-2:] if f["falsified"]) == 2

    def test_it_says_no_band_is_drawn_and_why(self, tmp_path):
        written(tmp_path, "UX-0001-x.md", task("ok"))
        rows, _totals = bands.census(tmp_path.glob("UX-*.md"))
        text = "\n".join(bands.report(rows, 40))
        assert "No band is drawn" in text
        assert "ambiguous by direction" in text, (
            "the report must say why a band would fire at improvement, or "
            "the next round draws one on the wrong row")

    def test_it_names_the_row_a_band_should_start_on(self, tmp_path):
        written(tmp_path, "UX-0001-x.md", task("ok"))
        rows, _totals = bands.census(tmp_path.glob("UX-*.md"))
        assert "falsify rate" in "\n".join(bands.report(rows, 40))

    def test_an_empty_backlog_is_an_error_not_a_clean_bill(self, tmp_path,
                                                           monkeypatch):
        """`UX-109`'s shape: a report over nothing that prints 0.0%
        everywhere reads as a healthy process."""
        monkeypatch.setattr(bands, "SCENARIOS", tmp_path)
        assert bands.main([]) == 2


class TestItRunsAgainstTheRealRecord:
    def test_it_reports_without_crashing(self):
        assert bands.main([]) == 0

    def test_the_record_has_enough_outcomes_to_be_worth_reading(self):
        rows, totals = bands.census(bands.SCENARIOS.glob("UX-*.md"))
        assert totals["outcomes"] > 50, (
            f"only {totals['outcomes']} Outcome(s) parsed - the signals "
            f"read phrases this repository writes by convention, and if "
            f"that convention moved they stop matching silently")
        assert len(rows) == totals["outcomes"]
