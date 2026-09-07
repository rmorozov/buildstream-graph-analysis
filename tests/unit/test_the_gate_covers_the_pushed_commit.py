"""UX-762: the gate covers the commit you push, not the branch you ran it on.

Round 104 ran `make test` at `67cc0d1` and then pushed `4879bcc`, a
commit the gate never saw. `gate-covers-push.sh` reads `.gate-covered`
(the sha `make test` last passed on) and refuses a `HEAD` it does not
name. These clauses hold the matching (including a compound command,
`no_bulk_add.is_bulk_add`'s own failure mode), the marker comparison
and the escape hatch - not `make test`'s own recipe, which
`test_the_loop_stays_fast.py` already reads for its other clauses.

`.claude/hooks/gate-covers-push.sh` carries the row's marker; this
holds the decision the marker names.
"""
import importlib.util
import json
import os
import pathlib
import subprocess

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
HOOK = REPO / ".claude/hooks/gate-covers-push.sh"
HOOK_MODULE = REPO / ".claude/hooks/gate_covers_push.py"


def _module():
    spec = importlib.util.spec_from_file_location("gate_covers_push", HOOK_MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fire(command, cwd, env_extra=None):
    """`(exit code, stderr)` for one payload against the real hook."""
    run_env = {k: v for k, v in os.environ.items() if k != "BGA_SKIP_PUSH_GATE"}
    run_env.update(env_extra or {})
    done = subprocess.run(
        [str(HOOK)], input=json.dumps({"tool_input": {"command": command}}),
        cwd=cwd, capture_output=True, text=True, timeout=30, env=run_env)
    return done.returncode, done.stderr


@pytest.fixture
def repo(tmp_path):
    """A real, isolated git repo with one commit."""
    def run(*a):
        subprocess.run(["git", "-C", str(tmp_path), *a], check=True,
                       capture_output=True)
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    run("config", "user.email", "t@example.com")
    run("config", "user.name", "t")
    (tmp_path / "a.txt").write_text("x")
    run("add", "a.txt")
    run("commit", "-q", "-m", "one")
    return tmp_path


def _head(repo_path):
    return subprocess.run(["git", "-C", str(repo_path), "rev-parse", "HEAD"],
                          capture_output=True, text=True).stdout.strip()


class TestItRecognisesARealPush:

    @pytest.mark.parametrize("command", (
        "git push",
        "git push origin main",
        "git push origin HEAD:main",
        "make test && git push",
        "git push --force-with-lease",
        # UX-762's own gap: a qualifying push after a non-qualifying
        # `git` invocation, or after an exempt one - both must still
        # be seen, the way `is_bulk_add` sees a second `git add -A`.
        "git status && git push origin master",
        "git push --dry-run origin master && git push origin master",
    ))
    def test_it_sees_a_real_push(self, command):
        assert _module().is_real_push(command), command

    @pytest.mark.parametrize("command", (
        "git push --dry-run",
        "git push -n origin main",
        "git push origin --delete stale",
        "git push origin -d stale",
        "git push origin :stale",
        "git push --tags",
        "git status",
        "echo 'git push origin main'",
        'git commit -m "run git push after this"',
    ))
    def test_it_leaves_everything_else_alone(self, command):
        assert not _module().is_real_push(command), command


class TestTheHeadIsCheckedAgainstTheMarker:

    def test_a_covered_head_is_allowed(self, repo):
        (repo / ".gate-covered").write_text(_head(repo))
        code, said = fire("git push", repo)
        assert code == 0, said

    def test_an_uncovered_head_is_refused_naming_both_shas(self, repo):
        old_head = _head(repo)
        (repo / ".gate-covered").write_text(old_head)
        (repo / "b.txt").write_text("y")
        subprocess.run(["git", "-C", str(repo), "add", "b.txt"], check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "two"],
                       check=True)
        new_head = _head(repo)
        code, said = fire("git push", repo)
        assert code == 2, said
        assert old_head in said, said
        assert new_head in said, said

    def test_no_marker_at_all_is_refused(self, repo):
        code, said = fire("git push", repo)
        assert code == 2, said

    def test_a_non_push_command_is_never_checked(self, repo):
        code, said = fire("git status", repo)
        assert code == 0, said

    def test_a_dry_run_is_never_checked(self, repo):
        code, said = fire("git push --dry-run", repo)
        assert code == 0, said

    def test_a_branch_delete_is_never_checked(self, repo):
        code, said = fire("git push origin --delete stale", repo)
        assert code == 0, said

    def test_a_tag_push_is_never_checked(self, repo):
        code, said = fire("git push --tags", repo)
        assert code == 0, said

    def test_a_compound_push_is_refused_without_the_escape(self, repo):
        """The exact shape the coordinator's review reproduced: an
        uncovered HEAD, no escape variable, a `git push` hidden behind
        a first, harmless command."""
        code, said = fire("git status && git push origin master", repo)
        assert code == 2, said

    def test_a_dry_run_then_a_real_push_is_refused(self, repo):
        code, said = fire(
            "git push --dry-run origin master && git push origin master",
            repo)
        assert code == 2, said


class TestTheEscapeHatch:

    def test_it_is_named_in_the_message(self):
        source = HOOK_MODULE.read_text(encoding="utf-8")
        assert "BGA_SKIP_PUSH_GATE" in source
        assert "{escape}" in source.split("MESSAGE = ")[1].split('"""')[1]

    def test_a_bare_flag_is_refused_naming_why(self, repo):
        for reason in ("1", "true", "yes"):
            code, said = fire("git push", repo,
                              {"BGA_SKIP_PUSH_GATE": reason})
            assert code == 2, (reason, said)
            assert "does not name a task" in said, said

    def test_a_valid_reason_bypasses_and_prints_loudly(self, repo):
        head = _head(repo)
        code, said = fire("git push", repo,
                          {"BGA_SKIP_PUSH_GATE": "UX-762"})
        assert code == 0, said
        assert "BYPASSED" in said, said
        assert "UX-762" in said, said
        assert head in said, said

    def test_the_bypass_message_warns_it_holds_for_the_shell(self):
        source = HOOK_MODULE.read_text(encoding="utf-8")
        assert "shell" in source.split("MESSAGE = ")[1].split('"""')[1]


class TestSettingsDeclaresIt:

    def test_settings_declares_it_on_bash(self):
        held = json.loads((REPO / ".claude/settings.json").read_text(
            encoding="utf-8"))
        bash = [m for m in held["hooks"]["PreToolUse"]
                if m.get("matcher") == "Bash"]
        commands = [h["command"] for m in bash for h in m["hooks"]]
        assert any("gate-covers-push.sh" in c for c in commands), commands


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
