"""UX-387: the fast check is blind to the mismatch it exists for.

`tools/dev_close_task.py --check` is the command the fixing guide's own
loop puts before a closure commit, and it exists because `UX-131` found
the backlog index and its task files drifting apart.
`test_docs_links_and_commands.py` holds the same property in the suite.

They did not agree, and the reason is one line of scope:

```text
rows in docs/backlog/scenarios/README.md      7    read by --check
rows in docs/backlog/scenarios/closed.md    379    read by the suite only
```

`UX-232` split the backlog by liveness and the tool kept reading the
open half, so `--check` answered for 1.8% of the backlog and printed
"0 problem(s)" for the rest. Round 61 hit it live: `UX-382`'s row moved
to `closed.md`, its file's marker stayed 🔴, `--check` passed, and a
full `make test-fast` two items later was what noticed.

**A fast check that returns a clean bill of health on a tree the suite
rejects makes the loop slower, not faster** - it teaches a contributor
that the fast check means nothing, which is `UX-336`'s finding one
level up.

So this file holds the two halves the repair rests on: that the tool
and the suite are one implementation rather than two agreeing readings,
and that `--check` says what it looked at.
"""
import pathlib
import shutil
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools import dev_close_task as close  # noqa: E402

SCENARIOS = REPO / "docs/backlog/scenarios"
TOOL = REPO / "tools/dev_close_task.py"


def _run(scenarios):
    return subprocess.run(
        [sys.executable, str(TOOL), "--check", "--scenarios", str(scenarios)],
        capture_output=True, text=True)


@pytest.fixture
def backlog(tmp_path):
    """A copy of the real backlog, so a mutation can be applied to it.

    The tool takes `--scenarios` for exactly this. Copying rather than
    editing in place is what lets the mutations below run against a
    committed tree without a `git checkout --` that could revert an
    unrelated edit - which this repository has done to itself before.
    """
    into = tmp_path / "scenarios"
    into.mkdir()
    for path in SCENARIOS.glob("*.md"):
        shutil.copy(path, into / path.name)
    return into


def _flip(path, frm="🟢 Done", to="🔴 Not Started"):
    text = path.read_text(encoding="utf-8")
    assert f"**Status:** {frm}" in text, (path.name, frm)
    path.write_text(
        text.replace(f"**Status:** {frm}", f"**Status:** {to}", 1),
        encoding="utf-8")


class TestItReadsTheWholeBacklog:
    def test_a_closed_row_whose_file_disagrees_is_reported(self, backlog):
        """The defect, reproduced. `UX-382` is the item round 61 hit,
        and its row lives in `closed.md` - the half `--check` could not
        see."""
        _flip(backlog / "UX-0382-the-element-entity-has-two-shapes-"
                        "sharing-one-attribute.md")
        result = _run(backlog)
        assert result.returncode == 1, (
            "--check passed a tree whose closed row and task file "
            f"disagree:\n{result.stdout}")
        assert "UX-382" in result.stdout

    def test_it_is_symmetric(self, backlog):
        """Flipping the *row* rather than the file is the same defect
        from the other side, and a check that only looked one way would
        pass half of them."""
        closed = backlog / "closed.md"
        text = closed.read_text(encoding="utf-8")
        row = next(line for line in text.splitlines()
                   if line.startswith("| UX-382 |"))
        closed.write_text(text.replace(row, row.replace("🟢", "🔴"), 1),
                          encoding="utf-8")
        result = _run(backlog)
        assert result.returncode == 1, result.stdout
        assert "UX-382" in result.stdout

    def test_an_agreeing_tree_still_reports_zero(self, backlog):
        """The other direction, so the repair is not "complain about
        everything"."""
        result = _run(backlog)
        assert result.returncode == 0, result.stdout
        assert "0 problem(s)" in result.stdout

    def test_it_reads_both_halves_of_the_backlog(self):
        """The scope that was wrong, asserted directly: `closed.md`
        carries the overwhelming majority of the rows, so a reader that
        skipped it would be checking a rounding error."""
        names = [path.name for path in close.backlog_files()]
        assert names == ["README.md", "closed.md"]
        rows = close.table_statuses()
        assert len(rows) > 100, (
            f"only {len(rows)} row(s) read - the closed half is missing")


class TestOneImplementationNotTwo:
    """The Required Fix's first half. The tool and the guard asserting
    one property by two readings is how they came to disagree."""

    def test_the_suite_imports_the_tools_readers(self):
        source = (REPO / "tests/unit/test_docs_links_and_commands.py"
                  ).read_text(encoding="utf-8")
        assert "from tools.dev_close_task import" in source, (
            "the guard has its own reader again, which is the "
            "arrangement `UX-387` was filed about")

    def test_both_answer_the_same_on_the_real_tree(self):
        from tests.unit import test_docs_links_and_commands as guard
        assert guard._table_statuses is close.table_statuses
        assert guard._file_statuses is close.file_statuses
        assert close.status_disagreements() == []


class TestItSaysWhatItChecked:
    """The Required Fix's second half. "0 problem(s)" reads the same for
    "four properties passed" and "three passed and the fourth is not
    implemented", and a contributor cannot tell those apart - which is
    the whole reason this went unnoticed."""

    def test_every_property_is_named_in_the_output(self, backlog):
        result = _run(backlog)
        for what, _run_it in close.CHECKS:
            assert what in result.stdout, (
                f"`--check` holds {what!r} and does not say so:\n"
                f"{result.stdout}")

    def test_the_count_of_properties_is_reported(self, backlog):
        result = _run(backlog)
        assert f"{len(close.CHECKS)} propert" in result.stdout, result.stdout

    def test_a_failure_names_the_property_it_broke(self, backlog):
        _flip(backlog / "UX-0382-the-element-entity-has-two-shapes-"
                        "sharing-one-attribute.md")
        result = _run(backlog)
        line = next((line for line in result.stdout.splitlines()
                     if "FAIL" in line), None)
        assert line is not None, (
            f"a failing property is not marked as such:\n{result.stdout}")
        assert close.CHECKS[0][0] in line, line


class TestTheScopeFlagIsHonoured:
    """`--scenarios` rebinds the module's paths at runtime, so a reader
    that captured them at import would silently answer about the real
    backlog while the caller believed it was pointed at a fixture. Every
    clause above rests on this working."""

    def test_the_readers_follow_the_flag(self, backlog, monkeypatch):
        (backlog / "README.md").write_text("| UX-9001 | x | 🔴 |\n",
                                           encoding="utf-8")
        (backlog / "closed.md").write_text("", encoding="utf-8")
        monkeypatch.setattr(close, "SCENARIOS", backlog)
        monkeypatch.setattr(close, "INDEX", backlog / "README.md")
        monkeypatch.setattr(close, "CLOSED", backlog / "closed.md")
        assert close.table_statuses() == {9001: "🔴"}


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
