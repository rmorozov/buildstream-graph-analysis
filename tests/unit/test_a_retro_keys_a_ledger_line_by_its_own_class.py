"""UX-1090: a bookkeeping line keys by its own `class` field, and a
ledger friction cell keys by agent + token, or is no finding at all.

Same scratch-repo approach as UX-999's test - the property is what
`git log -p --since` includes, not what a parser accepts.
"""

import datetime
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))

import dev_retro as retro

TODAY = datetime.date.today()


def _git(repo, *argv, date=None, check=True):
    env = None
    if date is not None:
        import os

        stamp = f"{date}T12:00:00"
        env = {**os.environ, "GIT_AUTHOR_DATE": stamp, "GIT_COMMITTER_DATE": stamp}
    return subprocess.run(["git", *argv], cwd=repo, check=check, env=env, capture_output=True, text=True)


def _repo(tmp_path):
    repo = tmp_path / "repo"
    (repo / "docs/backlog/scenarios").mkdir(parents=True)
    (repo / "docs/audits").mkdir(parents=True)
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "a@b")
    _git(repo, "config", "user.name", "a")
    (repo / "README.md").write_text("x\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-qm", "base", date=(TODAY - datetime.timedelta(days=30)).isoformat())
    return repo


def _bk_line(path, what, command, status="open", filed=1, cls="coverage"):
    return f"- r{filed} · {status} · {cls} · `{path}` · {what} · `{command}`\n"


def _commit_bookkeeping(repo, lines, date):
    path = repo / "docs/backlog/bookkeeping.md"
    existing = path.read_text(encoding="utf-8") if path.exists() else "# Bookkeeping\n\n"
    path.write_text(existing + "".join(lines), encoding="utf-8")
    _git(repo, "add", "docs/backlog/bookkeeping.md")
    _git(repo, "commit", "-qm", "bookkeeping", date=date)


def _commit_ledger_row(repo, row, date, header=False):
    path = repo / "docs/audits/agent-runs.md"
    if header or not path.exists():
        path.write_text(
            "| round | agent | model | task | tokens | tool calls | wall "
            "| outcome | friction |\n|---|---|---|---|---|---|---|---|---|\n",
            encoding="utf-8",
        )
        _git(repo, "add", "docs/audits/agent-runs.md")
        _git(repo, "commit", "-qm", "ledger header", date=date)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(row)
    _git(repo, "add", "docs/audits/agent-runs.md")
    _git(repo, "commit", "-qm", "ledger row", date=date)


class TestABookkeepingLineWithNoTokenKeysByItsClass:
    def test_a_coverage_line_with_no_token_is_classed(self, tmp_path):
        repo = _repo(tmp_path)
        since = (TODAY - datetime.timedelta(days=10)).isoformat()
        in_window = (TODAY - datetime.timedelta(days=3)).isoformat()
        _commit_bookkeeping(
            repo, [_bk_line("docs/x.md", "a stale number", "eyeball the diff", cls="coverage")], in_window
        )
        out = retro.report(repo, since)
        line = [l for l in out.splitlines() if l.strip().startswith("coverage")][0]
        assert line.strip().endswith("1"), out
        assert "unclassed: 0 of 1" in out, out


class TestNoFindingFrictionCellsAddNothing:
    def test_none_reported_and_em_dash_rows_add_zero_findings(self, tmp_path):
        repo = _repo(tmp_path)
        since = (TODAY - datetime.timedelta(days=10)).isoformat()
        in_window = (TODAY - datetime.timedelta(days=3)).isoformat()
        _commit_ledger_row(
            repo,
            "| 1 | implementer | sonnet | UX-1 | 10k | 5 | 1 m | merged | none reported |\n",
            in_window,
            header=True,
        )
        _commit_ledger_row(repo, "| 1 | implementer | sonnet | UX-2 | 10k | 5 | 1 m | merged | — |\n", in_window)
        out = retro.report(repo, since)
        assert "since " + since + ": 0 finding(s)" in out, out
        assert "friction without a command" not in out, out


class TestATokenedFrictionCellKeysByAgentAndToken:
    def test_the_key_is_agent_then_token(self, tmp_path):
        repo = _repo(tmp_path)
        since = (TODAY - datetime.timedelta(days=10)).isoformat()
        in_window = (TODAY - datetime.timedelta(days=3)).isoformat()
        _commit_ledger_row(
            repo,
            "| 1 | implementer | sonnet | UX-1 | 10k | 5 | 1 m | merged | tools/dev_probe.py drifted |\n",
            in_window,
            header=True,
        )
        out = retro.report(repo, since)
        line = [l for l in out.splitlines() if "implementer · tools/dev_probe.py" in l][0]
        assert line.strip().endswith("1"), out


class TestAFrictionCellWithNoCommandIsOutsideTheCount:
    def test_no_command_is_reported_separately_not_unclassed(self, tmp_path):
        repo = _repo(tmp_path)
        since = (TODAY - datetime.timedelta(days=10)).isoformat()
        in_window = (TODAY - datetime.timedelta(days=3)).isoformat()
        _commit_ledger_row(
            repo,
            "| 1 | researcher | sonnet | UX-1 | 10k | 5 | 1 m | merged | escape language is unstandardised |\n",
            in_window,
            header=True,
        )
        out = retro.report(repo, since)
        assert "since " + since + ": 0 finding(s)" in out, out
        assert "friction without a command: 1" in out, out


if __name__ == "__main__":  # pragma: no cover
    import pytest

    raise SystemExit(pytest.main([__file__, "-v"]))
