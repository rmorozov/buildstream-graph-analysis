"""UX-768: a closing note is one line, and never a shell argument.

Round 105's note backticked a command; the shell ran it before
`dev_close_task.py` ever saw the string. `--note-file` keeps the note
off the command line, and a note that arrives with a newline already
in it - the mark of a substitution, not typing - is refused before any
write, on both the single-id and the batch path (UX-709's population).
"""
import pathlib
import shutil
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
CLOSE_TASK = REPO / "tools/dev_close_task.py"


def _run(*argv, use_shell_backticks=None):
    """Plain argv, or - when `use_shell_backticks` is given - a real
    shell command line so a backtick in the note actually substitutes,
    the way round 105's did."""
    if use_shell_backticks is not None:
        return subprocess.run(
            ["bash", "-c", use_shell_backticks, "_", *argv],
            capture_output=True, text=True, cwd=str(REPO), timeout=120)
    return subprocess.run(
        [sys.executable, str(CLOSE_TASK), *argv],
        capture_output=True, text=True, cwd=str(REPO), timeout=120)


def _one_open_row(tmp_path, uid="UX-9911", slug="UX-9911-a-guard-row"):
    scenarios = tmp_path / "scenarios"
    shutil.copytree(REPO / "docs/backlog/scenarios", scenarios)
    (scenarios / f"{slug}.md").write_text(
        f"# {uid}: a row this guard wrote\n\n"
        f"**Priority:** Low | **Status:** \U0001f534 Not Started | "
        f"**Serves:** nobody | **Topic:** guards\n\n"
        f"## Outcome\n\nmeasured.\n", encoding="utf-8")
    readme = scenarios / "README.md"
    text = readme.read_text(encoding="utf-8")
    marker = "\n## UX-333"
    assert marker in text, "the open table's end moved"
    row = (f"| {uid} | [a guard row]({slug}.md) | guards | Low | — | "
           f"\U0001f534 |\n")
    readme.write_text(text.replace(marker, "\n" + row, 1), encoding="utf-8")
    return scenarios


def _two_open_rows(tmp_path):
    scenarios = tmp_path / "scenarios"
    shutil.copytree(REPO / "docs/backlog/scenarios", scenarios)
    ids = (("UX-9912", "UX-9912-a-guard-row-one"),
           ("UX-9913", "UX-9913-a-guard-row-two"))
    for uid, slug in ids:
        (scenarios / f"{slug}.md").write_text(
            f"# {uid}: a row this guard wrote\n\n"
            f"**Priority:** Low | **Status:** \U0001f534 Not Started | "
            f"**Serves:** nobody | **Topic:** guards\n\n"
            f"## Outcome\n\nmeasured.\n", encoding="utf-8")
    readme = scenarios / "README.md"
    text = readme.read_text(encoding="utf-8")
    marker = "\n## UX-333"
    assert marker in text, "the open table's end moved"
    rows = "".join(
        f"| {uid} | [a guard row]({slug}.md) | guards | Low | — | "
        f"\U0001f534 |\n" for uid, slug in ids)
    readme.write_text(text.replace(marker, "\n" + rows + marker, 1),
                      encoding="utf-8")
    return ids, scenarios


class TestNoteFileNeverTransitsAShellWord:

    def test_note_file_closes_the_row_backticks_and_all(self, tmp_path):
        scenarios = _one_open_row(tmp_path)
        note_path = tmp_path / "note.md"
        note_path.write_text(
            "a note with a `backtick span` that must not run\n",
            encoding="utf-8")
        done = _run("UX-9911", "--move", "--note-file", str(note_path),
                    "--scenarios", str(scenarios))
        assert done.returncode == 0, done.stdout + done.stderr
        closed = (scenarios / "closed.md").read_text(encoding="utf-8")
        assert "`backtick span`" in closed
        assert "| UX-9911 |" in closed


class TestASubstitutedNoteIsRefused:

    def test_a_real_backtick_substitution_is_refused_not_written(
            self, tmp_path):
        """The exact round-105 shape: a backtick in the note becomes
        command substitution before this tool ever sees the string,
        landing a real newline in argv - not a typed `\\n`."""
        scenarios = _one_open_row(tmp_path)
        before = (scenarios / "README.md").read_bytes()
        done = _run(
            "UX-9911", str(scenarios),
            use_shell_backticks=(
                'python3 tools/dev_close_task.py "$1" --move --note '
                '"`printf \'first line\\nsecond line\'`" --scenarios "$2"'))
        assert done.returncode != 0, done.stdout + done.stderr
        assert "UX-9911: --note is one line; a multi-line note is a " \
               "substituted note (UX-768)" in done.stderr
        assert (scenarios / "README.md").read_bytes() == before
        assert "| UX-9911 |" not in (
            scenarios / "closed.md").read_text(encoding="utf-8")

    def test_a_multiline_note_file_is_also_refused(self, tmp_path):
        scenarios = _one_open_row(tmp_path)
        note_path = tmp_path / "note.md"
        note_path.write_text("first line\nsecond line\n", encoding="utf-8")
        done = _run("UX-9911", "--move", "--note-file", str(note_path),
                    "--scenarios", str(scenarios))
        assert done.returncode != 0
        assert "UX-9911: --note is one line" in done.stderr
        assert "| UX-9911 |" not in (
            scenarios / "closed.md").read_text(encoding="utf-8")

    def test_a_trailing_newline_alone_does_not_trip_the_guard(
            self, tmp_path):
        """The common case a text file writes: one line, one trailing
        `\\n` - not a substitution, and not refused."""
        scenarios = _one_open_row(tmp_path)
        note_path = tmp_path / "note.md"
        note_path.write_text("one clean line\n", encoding="utf-8")
        done = _run("UX-9911", "--move", "--note-file", str(note_path),
                    "--scenarios", str(scenarios))
        assert done.returncode == 0, done.stdout + done.stderr

    def test_the_batch_path_refuses_a_substituted_note_too(self, tmp_path):
        """UX-709's population: a guard that only reads the single-id
        path is the narrow-population defect this repository has paid
        for seven times. The first id's good note must not write
        either - every id validates before any of them writes."""
        ids, scenarios = _two_open_rows(tmp_path)
        before_readme = (scenarios / "README.md").read_bytes()
        done = _run(
            ids[0][0], ids[1][0], str(scenarios),
            use_shell_backticks=(
                'python3 tools/dev_close_task.py --move "$1" --note '
                '"first found" "$2" --note '
                '"`printf \'two\\nlines\'`" --scenarios "$3"'))
        assert done.returncode != 0, done.stdout + done.stderr
        assert ids[1][0] in done.stderr
        assert (scenarios / "README.md").read_bytes() == before_readme
        closed = (scenarios / "closed.md").read_text(encoding="utf-8")
        assert f"| {ids[0][0]} |" not in closed, (
            "the first id closed before the batch's bad note was caught")
        assert f"| {ids[1][0]} |" not in closed
