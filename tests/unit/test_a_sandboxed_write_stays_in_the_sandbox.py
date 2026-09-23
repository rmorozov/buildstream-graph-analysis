"""UX-932/UX-996: `--check` writes no file, anywhere.

`UX-932` filed the defect: `--check --write --scenarios <tmp>` wrote the
area pages under the real `docs/backlog/areas/`, `AREA_PAGES` being
`REPO`-based while `--scenarios` moved only what the tool reads.
`UX-996` removed `--check`'s write path entirely - it no longer takes
`--write` at all - so there is nowhere left for that defect to recur.
This holds the read-only property directly, sandboxed or not.
"""
import hashlib
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import dev_close_task as close_task
from test_an_unmerged_index_derives_nothing import README, TASK


def _listing(directory):
    return {str(p.relative_to(directory)): hashlib.sha256(
                p.read_bytes()).hexdigest()
            for p in sorted(directory.rglob("*")) if p.is_file()}


def _narrow_sandbox(tmp_path):
    """One task file under area `tools`: narrower than any real tree."""
    scenarios = tmp_path / "sandbox/scenarios"
    scenarios.mkdir(parents=True)
    (scenarios / "UX-0001-a-row.md").write_text(TASK.format(line="x"),
                                                encoding="utf-8")
    (scenarios / "README.md").write_text(README, encoding="utf-8")
    (scenarios / "closed.md").write_text("# Closed\n", encoding="utf-8")
    return scenarios


class TestCheckWritesNoFile:

    def test_check_has_no_write_flag(self):
        """`--write` is now `--shape`'s alone (`UX-996`)."""
        with pytest.raises(SystemExit):
            close_task.main(["--check", "--write"])

    def test_a_sandboxed_check_adds_removes_or_rewrites_nothing(
            self, tmp_path, monkeypatch, capsys):
        scenarios = _narrow_sandbox(tmp_path)
        for name in ("SCENARIOS", "INDEX", "CLOSED"):
            monkeypatch.setattr(close_task, name, getattr(close_task, name))
        before = _listing(tmp_path)

        close_task.main(["--check", "--scenarios", str(scenarios)])
        capsys.readouterr()

        assert _listing(tmp_path) == before, (
            "`--check` added, removed or rewrote a file under the sandbox")

    def test_areas_prints_and_writes_nothing(
            self, tmp_path, monkeypatch, capsys):
        scenarios = _narrow_sandbox(tmp_path)
        for name in ("SCENARIOS", "INDEX", "CLOSED"):
            monkeypatch.setattr(close_task, name, getattr(close_task, name))
        before = _listing(tmp_path)

        close_task.main(["--areas", "--scenarios", str(scenarios)])
        printed = capsys.readouterr().out

        assert _listing(tmp_path) == before, (
            "`--areas` added, removed or rewrote a file under the sandbox")
        assert "UX-1" in printed, printed
