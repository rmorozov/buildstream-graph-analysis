"""UX-696: the register's commit-body row, and the tool CI runs for it.

The body counter is unit-tested against synthetic bodies rather than
against this repository's history, which changes under it. What the
history *is* used for is the one thing a synthetic body cannot show:
that the rule was measured on a real population before it shipped.
"""
import pathlib
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
import dev_commit_bodies as tool

WORKFLOW = REPO / ".github/workflows/ci.yml"


class TestTheCounter:
    def test_a_short_body_is_under(self):
        assert len(tool.body_lines("one\ntwo\nthree")) == 3

    def test_blank_lines_are_free(self):
        assert len(tool.body_lines("one\n\n\ntwo\n\n")) == 2

    @pytest.mark.parametrize("footer", (
        "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>",
        "Claude-Session: https://claude.ai/code/session_x",
        "Signed-off-by: Someone <a@b.c>",
    ))
    def test_the_pinned_footer_does_not_count(self, footer):
        """`UX-696`'s acceptance clause names this: the harness appends
        the footer, so counting it would spend two of the eight lines on
        something the author did not write."""
        assert len(tool.body_lines(f"one\ntwo\n\n{footer}")) == 2

    def test_a_body_that_is_only_footer_is_zero(self):
        assert tool.body_lines("Co-Authored-By: X <y@z>") == []

    def test_the_cap_is_the_number_claude_md_states(self):
        register = (REPO / "CLAUDE.md").read_text(encoding="utf-8")
        assert f"≤ {tool.CAP} lines" in register, (
            f"CLAUDE.md does not state a {tool.CAP}-line commit body, so "
            f"the tool and the register are two numbers")


class TestCIRunsIt:
    def test_the_workflow_calls_the_tool(self):
        assert "tools/dev_commit_bodies.py" in WORKFLOW.read_text(
            encoding="utf-8"), (
            "nothing in CI runs the commit-body check, so the register's "
            "row is stated and unread again")

    def test_the_tool_exits_nonzero_when_it_finds_one(self, tmp_path):
        """The half that makes the step a gate. A tool that reports and
        exits 0 is a `UX-491` log line, not a check."""
        repo = tmp_path / "r"
        repo.mkdir()
        env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
               "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
               "PATH": "/usr/bin:/bin", "HOME": str(tmp_path)}
        run = lambda *a: subprocess.run(a, cwd=repo, env=env, check=True,
                                        capture_output=True)
        run("git", "init", "-q", "-b", "main")
        (repo / "a").write_text("1")
        run("git", "add", "a")
        run("git", "commit", "-qm", "base")
        run("git", "branch", "-f", "base-ref")
        (repo / "a").write_text("2")
        run("git", "add", "a")
        body = "\n".join(f"line {i}" for i in range(tool.CAP + 1))
        run("git", "commit", "-qm", f"subject\n\n{body}")
        out = subprocess.run(
            [sys.executable, str(REPO / "tools/dev_commit_bodies.py"),
             "base-ref"], cwd=repo, env=env, capture_output=True, text=True)
        assert out.returncode == 1, out.stdout
        assert "over the" in out.stdout

    def test_a_body_within_the_cap_exits_zero(self, tmp_path):
        """The other direction, so the clause above is not passing on a
        tool that fails whatever it reads."""
        repo = tmp_path / "r"
        repo.mkdir()
        env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
               "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
               "PATH": "/usr/bin:/bin", "HOME": str(tmp_path)}
        run = lambda *a: subprocess.run(a, cwd=repo, env=env, check=True,
                                        capture_output=True)
        run("git", "init", "-q", "-b", "main")
        (repo / "a").write_text("1")
        run("git", "add", "a")
        run("git", "commit", "-qm", "base")
        run("git", "branch", "-f", "base-ref")
        (repo / "a").write_text("2")
        run("git", "add", "a")
        run("git", "commit", "-qm", "subject\n\nline one\nline two")
        out = subprocess.run(
            [sys.executable, str(REPO / "tools/dev_commit_bodies.py"),
             "base-ref"], cwd=repo, env=env, capture_output=True, text=True)
        assert out.returncode == 0, out.stdout


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
