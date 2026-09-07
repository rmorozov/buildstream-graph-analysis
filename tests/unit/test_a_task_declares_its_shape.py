"""UX-706: which model runs a task is read off its text, never typed.

Three yes/no signals - the Required Fix names a file, the Acceptance
Test names a guard and a mutation, either names a contract or process
surface - give one of three shapes, and the header carries the word
the tool derived. `--check` holds the two equal for every open row.
"""
import pathlib
import shutil
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools import dev_close_task as close

TOOL = REPO / "tools/dev_close_task.py"
HEADER = "**Priority:** Low | **Status:** \U0001f534 Not Started | **Topic:** guards"


def _task(fix, test):
    return (f"# UX-9999: a task\n\n{HEADER}\n\n## Motivation\n\nx\n\n"
            f"## Required Fix\n\n{fix}\n\n## Out of Scope\n\n- none\n\n"
            f"## Acceptance Test\n\n{test}\n")


class TestTheThreeSignalsGiveThreeShapes:
    def test_a_file_a_guard_and_a_mutation_is_mechanical(self):
        text = _task("Edit `bga/blast.py`.",
                     "`test_the_blast_is_ranked.py` red under the mutation.")
        assert close.derived_shape(text) == "mechanical"

    def test_a_file_and_no_named_guard_is_bounded(self):
        text = _task("Edit `bga/blast.py`.", "the rank moves; mutation: drop it.")
        assert close.derived_shape(text) == "bounded"

    def test_no_file_named_is_judgement(self):
        text = _task("Rank the blast better.", "the rank moves.")
        assert close.derived_shape(text) == "judgement"

    @pytest.mark.parametrize("surface", ("bga/schemas.py", "docs/spec/specification.md",
                                         ".claude/hooks/x.sh", "pyproject.toml"))
    def test_a_contract_or_process_surface_is_judgement(self, surface):
        text = _task(f"Edit `{surface}` and `bga/blast.py`.",
                     "`test_x.py` red under the mutation.")
        assert close.derived_shape(text) == "judgement"

    def test_a_mutation_without_a_named_guard_is_not_mechanical(self):
        text = _task("Edit `bga/blast.py`.", "mutation: drop the rank - red.")
        assert close.shape_signals(text)["names a guard and a mutation"] is False


class TestTheHeaderCarriesTheDerivedWord:
    def test_the_word_is_appended_after_the_topic(self):
        text = close.with_shape(_task("a", "b"), "bounded")
        assert text.splitlines()[2] == HEADER + " | **Shape:** bounded"
        assert close.declared_shape(text) == "bounded"

    def test_writing_twice_replaces_rather_than_appends(self):
        text = close.with_shape(close.with_shape(_task("a", "b"), "bounded"), "judgement")
        assert text.count("**Shape:**") == 1
        assert close.declared_shape(text) == "judgement"


class TestTheRealBacklogAgrees:
    def test_every_open_task_declares_what_its_text_derives(self):
        assert close.shape_disagreements() == []

    def test_the_check_reports_a_typed_shape(self, tmp_path):
        """The mutation the guard exists for: a hand-edited word.

        The subject is whichever task is open when this runs, and its
        replacement shape is derived rather than named. `UX-702` was
        hard-coded here until the round that closed it: `--check` reads
        open rows only, so a closed fixture makes the mutation silent
        and the clause passes on a tool that has stopped working.
        """
        sys.path.insert(0, str(REPO / "tools"))
        import dev_close_task as tool

        into = tmp_path / "scenarios"
        into.mkdir()
        for path in (REPO / "docs/backlog/scenarios").glob("*.md"):
            shutil.copy(path, into / path.name)
        uid = sorted(tool.open_uids())[0]
        target = next(into.glob(f"UX-{uid:04d}-*.md"))
        text = target.read_text(encoding="utf-8")
        derived = tool.derived_shape(text)
        wrong = next(s for s in tool.SHAPES if s != derived)
        target.write_text(tool.with_shape(text, wrong), encoding="utf-8")
        run = subprocess.run([sys.executable, str(TOOL), "--check", "--scenarios", str(into)],
                             capture_output=True, text=True)
        assert run.returncode == 1
        assert (f"UX-{uid}: declares {wrong}, its text derives {derived}"
                in run.stdout), run.stdout
