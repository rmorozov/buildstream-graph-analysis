"""UX-999: `dev_retro.py` groups a window's bookkeeping by the command
that shows it.

Every source is read with `git log -p --since`, so the guard is a
scratch repository with commits both sides of the window rather than a
fixture file - the property under test is what git includes, not what
a parser accepts.
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
    return subprocess.run(["git", *argv], cwd=repo, check=check, env=env,
                          capture_output=True, text=True)


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


def _bk_line(path, what, command, status="open", filed=1, cls="misc"):
    return f"- r{filed} · {status} · {cls} · `{path}` · {what} · `{command}`\n"


def _commit_bookkeeping(repo, lines, date, mode="w"):
    path = repo / "docs/backlog/bookkeeping.md"
    header = "# Bookkeeping\n\n" if mode == "w" and not path.exists() else ""
    existing = path.read_text(encoding="utf-8") if path.exists() else "# Bookkeeping\n\n"
    path.write_text(existing + "".join(lines) if mode == "a" else header + "".join(lines),
                    encoding="utf-8")
    _git(repo, "add", "docs/backlog/bookkeeping.md")
    _git(repo, "commit", "-qm", "bookkeeping", date=date)


class TestPreWindowLinesAreUncounted:

    def test_only_the_in_window_line_is_counted(self, tmp_path):
        repo = _repo(tmp_path)
        before = (TODAY - datetime.timedelta(days=20)).isoformat()
        since = (TODAY - datetime.timedelta(days=10)).isoformat()
        after = (TODAY - datetime.timedelta(days=5)).isoformat()
        _commit_bookkeeping(
            repo, [_bk_line("tools/dev_before.py", "a stale figure",
                            "tools/dev_before.py --check")], before)
        _commit_bookkeeping(
            repo, [_bk_line("tools/dev_after.py", "another stale figure",
                            "tools/dev_after.py --check")], after, mode="a")
        out = retro.report(repo, since)
        assert "tools/dev_before.py" not in out, out
        assert "tools/dev_after.py" in out, out


class TestOneClassAcrossTwoSources:

    def test_a_list_item_and_a_table_row_are_one_class(self, tmp_path):
        repo = _repo(tmp_path)
        since = (TODAY - datetime.timedelta(days=10)).isoformat()
        in_window = (TODAY - datetime.timedelta(days=3)).isoformat()
        _commit_bookkeeping(
            repo, [_bk_line("bga/report.py", "a shared drift",
                            "tools/dev_probe.py --check")], in_window)
        ledger = repo / "docs/audits/agent-runs.md"
        ledger.write_text(
            "| round | agent | model | task | tokens | tool calls | wall "
            "| outcome | friction |\n|---|---|---|---|---|---|---|---|---|\n",
            encoding="utf-8")
        _git(repo, "add", "docs/audits/agent-runs.md")
        _git(repo, "commit", "-qm", "ledger header", date=in_window)
        with ledger.open("a", encoding="utf-8") as fh:
            fh.write("| 1 | implementer | sonnet | UX-1 | 10k | 5 | 1 m | "
                     "merged | tools/dev_probe.py drifted again |\n")
        _git(repo, "add", "docs/audits/agent-runs.md")
        _git(repo, "commit", "-qm", "ledger row", date=in_window)

        out = retro.report(repo, since)
        assert out.count("tools/dev_probe.py") == 1, out
        line = [l for l in out.splitlines() if "tools/dev_probe.py" in l][0]
        assert line.strip().endswith("2"), out


class TestNoTokenIsUnclassed:

    def test_a_line_with_no_token_is_unclassed(self, tmp_path):
        repo = _repo(tmp_path)
        since = (TODAY - datetime.timedelta(days=10)).isoformat()
        in_window = (TODAY - datetime.timedelta(days=3)).isoformat()
        _commit_bookkeeping(
            repo, [_bk_line("docs/x.md", "a stale number", "eyeball the diff")],
            in_window)
        out = retro.report(repo, since)
        assert "unclassed: 1 of 1" in out, out


class TestALineMovedIsNotFiledTwice:

    def test_a_status_change_is_one_finding_and_an_unrelated_removal_is_none(
            self, tmp_path):
        repo = _repo(tmp_path)
        before = (TODAY - datetime.timedelta(days=20)).isoformat()
        since = (TODAY - datetime.timedelta(days=10)).isoformat()
        first = (TODAY - datetime.timedelta(days=6)).isoformat()
        second = (TODAY - datetime.timedelta(days=3)).isoformat()

        # A line unrelated to the window's findings, filed before the
        # window and dropped inside it - its removal must not be a filing.
        _commit_bookkeeping(
            repo, [_bk_line("tools/dev_stale.py", "a retired flag",
                            "tools/dev_stale.py --check")], before)
        # In-window: the moved line, filed open ...
        _commit_bookkeeping(
            repo, [_bk_line("bga/report.py", "a moved finding",
                            "tools/dev_moved.py --check", status="open")],
            first, mode="a")
        # ... and, in the same window, its status changes (same path/what)
        # while the pre-window line above is dropped with no replacement.
        text = (repo / "docs/backlog/bookkeeping.md").read_text(encoding="utf-8")
        text = text.replace(
            _bk_line("bga/report.py", "a moved finding",
                    "tools/dev_moved.py --check", status="open"),
            _bk_line("bga/report.py", "a moved finding",
                    "tools/dev_moved.py --check", status="swept r2 UX-1"))
        text = text.replace(
            _bk_line("tools/dev_stale.py", "a retired flag",
                    "tools/dev_stale.py --check"), "")
        (repo / "docs/backlog/bookkeeping.md").write_text(text, encoding="utf-8")
        _git(repo, "add", "docs/backlog/bookkeeping.md")
        _git(repo, "commit", "-qm", "sweep", date=second)

        out = retro.report(repo, since)
        assert "tools/dev_stale.py" not in out, out
        line = [l for l in out.splitlines() if "tools/dev_moved.py" in l][0]
        assert line.strip().endswith("1"), out


class TestSinceDefaultsToTheNewestRetroDocument:

    def test_default_since_reads_the_retro_document_not_seven_days(self, tmp_path):
        repo = _repo(tmp_path)
        retro_date = (TODAY - datetime.timedelta(days=10)).isoformat()
        (repo / "docs/audits" / f"retro-{retro_date}.md").write_text(
            "x\n", encoding="utf-8")
        _git(repo, "add", "docs/audits")
        _git(repo, "commit", "-qm", "retro doc", date=retro_date)

        # 9 days back: outside a naive 7-day default, inside the
        # retro document's 10-day window.
        in_window = (TODAY - datetime.timedelta(days=9)).isoformat()
        _commit_bookkeeping(
            repo, [_bk_line("tools/dev_late.py", "a late drift",
                            "tools/dev_late.py --check")], in_window)

        since = retro.default_since(repo, today=TODAY)
        assert since == retro_date, since
        out = retro.report(repo, since)
        assert "tools/dev_late.py" in out, out


if __name__ == "__main__":  # pragma: no cover
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
