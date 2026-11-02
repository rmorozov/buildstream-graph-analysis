"""`UX-1371`: a session started above the checkout still gets its agents, skills and hooks."""

import json
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
SETUP = REPO / "tools/dev_cloud_setup.sh"
DISPATCH = REPO / ".claude/hooks/dispatch_by_repo.py"


def _setup(home, repo=str(REPO), cwd=None):
    env = {"HOME": str(home), "PATH": "/usr/bin:/bin"}
    subprocess.run(["bash", str(SETUP), "--links-only", repo], env=env, cwd=cwd, check=True)
    return json.loads((home / ".claude/settings.json").read_text())


def _dispatch(event, payload, allowed=(str(REPO),)):
    return subprocess.run(
        [sys.executable, str(DISPATCH), event, *allowed],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
    )


def test_the_agents_and_skills_are_linked_and_a_rerun_adds_no_second_hook(tmp_path):
    _setup(tmp_path)
    settings = _setup(tmp_path)
    for linked in ("agents/verifier.md", "agents/implementer.md", "skills/verify", "skills/falsify"):
        assert (tmp_path / ".claude" / linked).resolve() == REPO / ".claude" / linked
    for event in ("PreToolUse", "PostToolUse", "SessionStart"):
        assert len(settings["hooks"][event]) == 1, settings["hooks"][event]
        assert str(DISPATCH) in settings["hooks"][event][0]["hooks"][0]["command"]


def test_a_bulk_add_inside_the_checkout_is_refused():
    done = _dispatch("PreToolUse", {"tool_name": "Bash", "cwd": str(REPO), "tool_input": {"command": "git add -A"}})
    assert done.returncode == 2, done


def test_outside_any_checkout_or_for_another_tool_nothing_runs(tmp_path):
    bulk = {"command": "git add -A"}
    assert _dispatch("PreToolUse", {"tool_name": "Bash", "cwd": str(tmp_path), "tool_input": bulk}).returncode == 0
    assert _dispatch("PreToolUse", {"tool_name": "Read", "cwd": str(REPO), "tool_input": bulk}).returncode == 0


def test_a_checkout_outside_the_allowlist_runs_no_hook(tmp_path):
    clone = tmp_path / "capture-src"
    (clone / ".claude").mkdir(parents=True)
    hook = {"matcher": "Bash", "hooks": [{"type": "command", "command": "exit 7"}]}
    (clone / ".claude/settings.json").write_text(json.dumps({"hooks": {"PreToolUse": [hook]}}))
    subprocess.run(["git", "init", "-q", str(clone)], check=True)
    call = {"tool_name": "Bash", "cwd": str(clone), "tool_input": {"command": "ls"}}
    assert _dispatch("PreToolUse", call).returncode == 0
    assert _dispatch("PreToolUse", call, allowed=(str(clone),)).returncode == 7


def test_a_command_from_the_parent_that_enters_the_checkout_is_still_refused():
    parent = str(REPO.parent)
    name = REPO.name
    for command in (
        f"cd {name} && git add -A",
        f"cd {REPO} && git status && git add -A",
        f"cd {name}; git add -A",
        f"cd {name}&& git add -A",
    ):
        call = {"tool_name": "Bash", "cwd": parent, "tool_input": {"command": command}}
        assert _dispatch("PreToolUse", call).returncode == 2, command


def test_a_relative_repo_argument_links_and_allowlists_the_absolute_checkout(tmp_path):
    settings = _setup(tmp_path, repo=REPO.name, cwd=REPO.parent)
    assert (tmp_path / ".claude/agents/verifier.md").resolve() == REPO / ".claude/agents/verifier.md"
    assert f" {REPO}" in settings["hooks"]["PreToolUse"][0]["hooks"][0]["command"]


def test_an_edit_made_from_outside_runs_the_edited_files_checkout_hooks(tmp_path):
    clone = tmp_path / "repo"
    (clone / ".claude").mkdir(parents=True)
    hook = {"matcher": "Edit|Write", "hooks": [{"type": "command", "command": "exit 7"}]}
    (clone / ".claude/settings.json").write_text(json.dumps({"hooks": {"PreToolUse": [hook]}}))
    subprocess.run(["git", "init", "-q", str(clone)], check=True)
    for path in (str(clone / ".claude/settings.json"), "repo/tests/x.py"):
        call = {"tool_name": "Edit", "cwd": str(tmp_path), "tool_input": {"file_path": path}}
        assert _dispatch("PreToolUse", call, allowed=(str(clone),)).returncode == 7, path


def test_a_relative_edit_path_still_names_the_file_when_the_hook_runs_in_the_checkout(tmp_path):
    clone = tmp_path / "repo"
    (clone / ".claude").mkdir(parents=True)
    exists = "python3 -c 'import json,os,sys; sys.exit(0 if os.path.isfile(json.load(sys.stdin)[\"tool_input\"][\"file_path\"]) else 7)'"
    hook = {"matcher": "Edit", "hooks": [{"type": "command", "command": exists}]}
    (clone / ".claude/settings.json").write_text(json.dumps({"hooks": {"PostToolUse": [hook]}}))
    subprocess.run(["git", "init", "-q", str(clone)], check=True)
    (clone / "sub").mkdir()
    (clone / "sub/x.py").write_text("x = 1\n")
    for cwd, path in ((tmp_path, "repo/sub/x.py"), (clone / "sub", "x.py")):
        call = {"tool_name": "Edit", "cwd": str(cwd), "tool_input": {"file_path": path}}
        assert _dispatch("PostToolUse", call, allowed=(str(clone),)).returncode == 0, path


def test_a_git_file_redirecting_into_the_checkout_does_not_borrow_its_allowlist(tmp_path):
    source = tmp_path / "capture-src"
    (source / ".claude").mkdir(parents=True)
    hook = {"matcher": "Bash", "hooks": [{"type": "command", "command": "exit 7"}]}
    (source / ".claude/settings.json").write_text(json.dumps({"hooks": {"PreToolUse": [hook]}}))
    (source / ".git").write_text(f"gitdir: {REPO / '.git'}\n")
    call = {"tool_name": "Bash", "cwd": str(source), "tool_input": {"command": "ls"}}
    assert _dispatch("PreToolUse", call).returncode == 0


def test_a_command_that_leaves_one_allowed_checkout_for_another_runs_both_hooks(tmp_path):
    for name, code in (("a", "0"), ("b", "7")):
        repo = tmp_path / name
        (repo / ".claude").mkdir(parents=True)
        hook = {"matcher": "Bash", "hooks": [{"type": "command", "command": f"exit {code}"}]}
        (repo / ".claude/settings.json").write_text(json.dumps({"hooks": {"PreToolUse": [hook]}}))
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
    call = {
        "tool_name": "Bash",
        "cwd": str(tmp_path / "a"),
        "tool_input": {"command": f"cd {tmp_path / 'b'} && git push"},
    }
    assert _dispatch("PreToolUse", call, allowed=(str(tmp_path / "a"), str(tmp_path / "b"))).returncode == 7


def _repo_with_hook(path, command):
    (path / ".claude").mkdir(parents=True)
    hook = {"matcher": "Bash", "hooks": [{"type": "command", "command": command}]}
    (path / ".claude/settings.json").write_text(json.dumps({"hooks": {"PreToolUse": [hook]}}))
    subprocess.run(["git", "init", "-q", str(path)], check=True)


def test_a_chained_cd_resolves_from_the_directory_the_last_one_entered(tmp_path):
    _repo_with_hook(tmp_path / "outer/repo", "exit 7")
    call = {"tool_name": "Bash", "cwd": str(tmp_path), "tool_input": {"command": "cd outer && cd repo && git push"}}
    assert _dispatch("PreToolUse", call, allowed=(str(tmp_path / "outer/repo"),)).returncode == 7


def test_a_prefix_sharing_sibling_is_not_inside_the_checkout(tmp_path):
    # The hook refuses unless its payload's cwd is its own checkout.
    _repo_with_hook(
        tmp_path / "repo",
        'python3 -c "import json,os,sys; sys.exit(0 if json.load(sys.stdin)[\'cwd\'] == os.getcwd() else 7)"',
    )
    _repo_with_hook(tmp_path / "repo-other", "exit 0")
    call = {
        "tool_name": "Bash",
        "cwd": str(tmp_path / "repo-other"),
        "tool_input": {"command": "cd ../repo && git push"},
    }
    assert _dispatch("PreToolUse", call, allowed=(str(tmp_path / "repo"), str(tmp_path / "repo-other"))).returncode == 0
