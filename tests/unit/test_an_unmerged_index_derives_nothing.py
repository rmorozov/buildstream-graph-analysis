"""UX-935: `--check` reads nothing from an index that is mid-merge.

`git ls-files` lists an unmerged path once per stage, so a count taken
mid-merge is the file count plus two per conflict. The quiet case is
`git checkout --ours`: the text is resolved, the index is not, and
`--check` (`UX-996`: read-only throughout) must refuse rather than
print "0 problem(s)" over a git index it cannot answer for.
"""
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))

import dev_close_task as close_task

TASK = ("# UX-1: a row\n\n"
        "**Priority:** Medium | **Status:** 🔴 Not Started | "
        "**Topic:** guards | **Area:** tools | **Shape:** judgement\n\n"
        "## Motivation\n\n{line}\n")
README = ("# Index\n\n"
          "7 scenarios: **7 open**, 0 closed.\n\n"
          "| Topic | Open | Total |\n|---|---|---|\n| guards | 7 | 7 |\n\n"
          "| UX-1 | a row | guards | Medium | x | 🔴 Not Started |\n")
ARCHITECTURE = ("It counts 3 `docs/backlog/scenarios/` files and "
                "0 `docs/backlog/tasks/` files.\n\n## Chapter\n")


def _git(repo, *argv, check=True):
    return subprocess.run(["git", *argv], cwd=repo, check=check,
                          capture_output=True, text=True)


def _mid_merge(tmp_path):
    """One task file changed on both sides, then `checkout --ours`: the
    text is resolved and the index still holds three stages of it."""
    repo = tmp_path / "repo"
    scenarios = repo / "docs/backlog/scenarios"
    scenarios.mkdir(parents=True)
    (repo / "docs/backlog/tasks").mkdir(parents=True)
    (repo / "docs/backlog/areas").mkdir(parents=True)
    (repo / "docs/design").mkdir(parents=True)
    task = scenarios / "UX-0001-a-row.md"
    task.write_text(TASK.format(line="base"), encoding="utf-8")
    (scenarios / "README.md").write_text(README, encoding="utf-8")
    (scenarios / "closed.md").write_text("# Closed\n", encoding="utf-8")
    (repo / "docs/backlog/areas/tools.md").write_text("stale\n",
                                                      encoding="utf-8")
    (repo / "docs/design/architecture.md").write_text(ARCHITECTURE,
                                                      encoding="utf-8")
    for argv in (["init", "-q", "-b", "main"],
                 ["config", "user.email", "a@b"], ["config", "user.name", "a"],
                 ["add", "-f", "docs"], ["commit", "-qm", "base"],
                 ["checkout", "-qb", "other"]):
        _git(repo, *argv)
    task.write_text(TASK.format(line="theirs"), encoding="utf-8")
    _git(repo, "commit", "-qam", "theirs")
    _git(repo, "checkout", "-q", "main")
    task.write_text(TASK.format(line="ours"), encoding="utf-8")
    _git(repo, "commit", "-qam", "ours")
    assert _git(repo, "merge", "-q", "other", check=False).returncode != 0
    _git(repo, "checkout", "--ours", "--", str(task))
    return repo


def _pointed_at(repo, monkeypatch):
    scenarios = repo / "docs/backlog/scenarios"
    monkeypatch.setattr(close_task, "REPO", repo)
    monkeypatch.setattr(close_task, "SCENARIOS", scenarios)
    monkeypatch.setattr(close_task, "INDEX", scenarios / "README.md")
    monkeypatch.setattr(close_task, "CLOSED", scenarios / "closed.md")


def _snapshot(repo):
    """`{path: bytes}` for every tracked-directory file - `UX-996`:
    nothing `--check` reads is ever written, so nothing here should
    move either way."""
    return {p.relative_to(repo).as_posix(): p.read_bytes()
            for p in sorted((repo / "docs").rglob("*")) if p.is_file()}


class TestAnUnmergedIndexIsRefused:

    def test_the_fixture_is_the_inflated_count(self, tmp_path):
        """Three files, one of them at three stages: git lists five."""
        repo = _mid_merge(tmp_path)
        listed = _git(repo, "ls-files", "docs/backlog/scenarios").stdout
        assert len(listed.splitlines()) == 5, listed

    def test_check_refuses_mid_merge(
            self, tmp_path, monkeypatch, capsys):
        repo = _mid_merge(tmp_path)
        _pointed_at(repo, monkeypatch)
        before = _snapshot(repo)
        try:
            code = close_task.main(["--check"])
        except SystemExit as exited:
            code = exited.code
        err = capsys.readouterr().err
        assert code not in (0, None), "`--check` read from a mid-merge index"
        assert "unmerged" in err and "UX-0001-a-row.md" in err, err
        assert len(err.strip().splitlines()) == 1, err
        assert _snapshot(repo) == before, (
            "`--check` changed a file while the index was unmerged")

    def test_a_staged_resolution_checks_as_before(
            self, tmp_path, monkeypatch, capsys):
        repo = _mid_merge(tmp_path)
        _git(repo, "add", "docs/backlog/scenarios/UX-0001-a-row.md")
        _pointed_at(repo, monkeypatch)
        before = _snapshot(repo)
        code = close_task.main(["--check"])
        captured = capsys.readouterr()
        assert "unmerged" not in captured.err, captured.err
        assert code == 0, captured.out + captured.err
        assert _snapshot(repo) == before, (
            "`--check` wrote a file once the index was staged")
