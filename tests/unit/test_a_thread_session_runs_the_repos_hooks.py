"""`UX-1371`: a session started above the checkout still gets its agents, skills and hooks."""

import json
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
SETUP = REPO / "tools/dev_cloud_setup.sh"
DISPATCH = REPO / ".claude/hooks/dispatch_by_repo.py"


def _setup(home):
    env = {"HOME": str(home), "PATH": "/usr/bin:/bin"}
    subprocess.run(["bash", str(SETUP), "--links-only", str(REPO)], env=env, check=True)
    return json.loads((home / ".claude/settings.json").read_text())


def _dispatch(event, payload):
    return subprocess.run(
        [sys.executable, str(DISPATCH), event], input=json.dumps(payload), capture_output=True, text=True, check=False
    )


def test_every_agent_and_skill_is_linked_and_a_rerun_adds_no_second_hook(tmp_path):
    _setup(tmp_path)
    settings = _setup(tmp_path)
    for kind in ("agents", "skills"):
        want = sorted(p.name for p in (REPO / ".claude" / kind).iterdir() if not p.name.startswith("__"))
        assert sorted(p.name for p in (tmp_path / ".claude" / kind).iterdir()) == want
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
