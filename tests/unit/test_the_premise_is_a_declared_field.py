"""UX-586: the premise a closed item records is a field, not a phrase.

`dev_process_bands.py` read the premise row with a regex over the
Outcome's prose and reported 0.0 % of a round whose own summary line
says seven. The phrase form cannot be lengthened into a reader - "the
premise is falsified", "premise was wrong" and "premise is half wrong"
are three sentences, and the next round writes a fourth.

So `--outcome` writes `Premise: held | falsified - <one line>` and the
tool reads that field. What these clauses hold is the pair: the
skeleton keeps printing the field, and the reader keeps preferring it
to the prose around it.
"""
import pathlib
import re
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
SCENARIOS = REPO / "docs/backlog/scenarios"
sys.path.insert(0, str(REPO))

from tools import dev_process_bands as bands                    # noqa: E402

#: The items annotated when the field was introduced - round 81's rows
#: and the two round 80 closed beside them. A later round's Outcomes
#: carry the field because the skeleton prints it, which is the clause
#: above; this range is the one that was annotated by hand.
ANNOTATED = range(538, 563)


def written(tmp_path, outcome, name="UX-0001-x.md"):
    """One task file carrying an Outcome, and the tool's reading of it."""
    path = tmp_path / name
    path.write_text(f"# UX-9999: a thing\n\n## Motivation\n\nx\n\n"
                    f"## Outcome (round 1, 2026-01-01)\n\n{outcome}\n",
                    encoding="utf-8")
    return bands.read(path)


class TestTheSkeletonWritesTheField:
    """The field is only collected if the skeleton asks for it: a
    metric needing a ritual nobody is prompted for stops being
    collected in three rounds, which is why the phrase form was chosen
    in the first place."""

    def _printed(self):
        done = subprocess.run(
            [sys.executable, str(REPO / "tools/dev_close_task.py"),
             "UX-586", "--outcome", "--round", "83"],
            capture_output=True, text=True, cwd=str(REPO), timeout=120)
        assert done.returncode == 0, done.stderr
        return done.stdout

    def test_the_printed_skeleton_declares_a_premise(self):
        printed = self._printed()
        assert bands.PREMISE_DECLARED.search(printed), (
            "`--outcome` no longer prints the `Premise:` field; "
            "dev_process_bands.py would read every new Outcome as "
            "declaring nothing and count it in neither direction")

    def test_the_skeleton_pre_fills_no_verdict(self):
        """`UX-506`'s rule for every other measurement in the skeleton:
        a pre-filled answer is an invitation to the unmeasured claim."""
        pattern = dict((k, p) for k, _h, p in bands.SIGNALS)["premise_false"]
        assert not pattern.search(self._printed()), (
            "the skeleton pre-fills `falsified`, so an unedited Outcome "
            "would be counted as one")


class TestTheFieldIsReadAndNotThePhrase:
    def test_a_declared_falsified_is_counted(self, tmp_path):
        found = written(tmp_path, "**Premise:** falsified - it did not hold.")
        assert found["premise_false"] is True, found
        assert found["premise_stated"] is True, found

    def test_a_declared_held_is_not(self, tmp_path):
        found = written(tmp_path, "**Premise:** held - it reproduced.")
        assert found["premise_false"] is False, found
        assert found["premise_stated"] is True, found

    def test_the_field_beats_the_prose_around_it(self, tmp_path):
        """The old reader's own phrase, in an item that declares its
        premise held. Counting the sentence here is the defect this
        item was filed for, one direction over."""
        found = written(tmp_path,
                        "**Premise:** held - the census was dead as filed.\n\n"
                        "The whole Motivation rested on a false premise, "
                        "said `UX-412`, and its premise was false too.")
        assert found["premise_false"] is False, found

    @pytest.mark.parametrize("prose", (
        "The premise is falsified: the 200 is a spec default.",
        "The premise was wrong, and that is what closed the row.",
        "the premise is half wrong",
        "The filing's own mechanism was wrong.",
    ))
    def test_a_phrase_alone_is_not_a_declaration(self, tmp_path, prose):
        """Four sentences four items actually wrote. Each is a premise
        falsified and none is the same regex, which is the measurement
        `UX-586` was filed on."""
        found = written(tmp_path, prose)
        assert found["premise_stated"] is False, (prose, found)
        assert found["premise_false"] is False, (prose, found)

    def test_an_outcome_with_no_field_is_counted_neither_way(self, tmp_path):
        """Every Outcome before `UX-586` is this case. Reading them as
        `held` would put a change of convention into the series and
        report it as a change in the process."""
        found = written(tmp_path, "The gap is closed and the suite is green.")
        assert found["premise_stated"] is False, found
        assert found["premise_false"] is False, found

    @pytest.mark.parametrize("line", (
        "**Premise:** falsified - x",
        "Premise: falsified - x",
        "**Premise**: falsified - x",
        "**Premise:** **falsified** - x",
    ))
    def test_the_forms_a_writer_actually_types(self, tmp_path, line):
        assert written(tmp_path, line)["premise_false"] is True, line


class TestTheRateIsOverTheItemsThatDeclare:
    def test_the_denominator_is_the_declared_rows(self, tmp_path):
        """A rate over rows that cannot answer is the wrong population
        (fixing guide §5). Two of these four declare; one of the two is
        falsified, so the row reads 50 % and not 25 %."""
        for index, outcome in enumerate((
                "**Premise:** falsified - it did not hold.",
                "**Premise:** held - it reproduced.",
                "nothing declared here",
                "nothing declared here either")):
            (tmp_path / f"UX-000{index + 1}-x.md").write_text(
                f"# t\n\n## Outcome (r)\n\n{outcome}\n", encoding="utf-8")
        rows, totals = bands.census(tmp_path.glob("UX-*.md"))
        assert (totals["premise_false"], totals["premise_stated"]) == (1, 2)
        text = "\n".join(bands.report(rows, 4))
        premise = next(line for line in text.splitlines()
                       if line.startswith("found the premise"))
        assert "50.0%" in premise, premise
        assert "declares a Premise field at all" in text, (
            "the report states the rate but not its denominator")


class TestTheRecordItWasAnnotatedFrom:
    @pytest.mark.parametrize("path", sorted(
        p for p in SCENARIOS.glob("UX-*.md")
        if int(re.match(r"UX-(\d+)", p.name).group(1)) in ANNOTATED),
        ids=lambda p: p.name[:7])
    def test_every_annotated_outcome_declares_its_premise(self, path):
        outcome = bands.outcome_of(path.read_text(encoding="utf-8"))
        assert outcome is not None, f"{path.name} lost its Outcome"
        assert bands.PREMISE_DECLARED.search(outcome), (
            f"{path.name}: no `Premise: held | falsified` line. The "
            f"bands tool counts this item in neither direction, which "
            f"is the 0 % `UX-586` was filed for")

    def test_the_reading_is_not_vacuous(self):
        """Both verdicts appear in the annotated range. All-held would
        pass every clause above and still report the 0 % this item is
        about."""
        rows, _totals = bands.census(SCENARIOS.glob("UX-*.md"))
        declared = [(n, f) for n, f in rows if f["premise_stated"]]
        falsified = sum(1 for _n, f in declared if f["premise_false"])
        assert 0 < falsified < len(declared), (falsified, len(declared))
