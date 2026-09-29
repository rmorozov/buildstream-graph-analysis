"""UX-1114: the SessionStart hook unshallows and installs the lock, once,
never in a linked worktree, and never fails the session. The installer
is a stub for pip; `git fetch --unshallow` really runs on a scratch clone."""
import importlib.util
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
HOOKS = REPO / ".claude/hooks"
sys.path.insert(0, str(REPO / "tools"))


def _load():
    spec = importlib.util.spec_from_file_location(
        "session_start", HOOKS / "session_start.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git(cwd, *args):
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


class Stub:
    """Runs git for real, records anything else instead of running pip."""

    def __init__(self):
        self.pip = []

    def __call__(self, cmd, cwd):
        if cmd[0].endswith("git"):
            subprocess.run(cmd, cwd=cwd, check=True, capture_output=True)
        else:
            self.pip.append(cmd)
        return True


def _shallow_clone(tmp_path):
    origin = tmp_path / "origin"
    origin.mkdir()
    _git(origin, "init", "-q")
    for n in range(3):
        (origin / "f").write_text(str(n))
        _git(origin, "add", "f")
        _git(origin, "commit", "-q", "-m", str(n))
    (origin / "requirements.lock").write_text("nopackagehere==1.0\n")
    _git(origin, "add", "requirements.lock")
    _git(origin, "commit", "-q", "-m", "lock")
    clone = tmp_path / "clone"
    _git(tmp_path, "clone", "-q", "--depth", "1", f"file://{origin}", "clone")
    return clone


def _is_shallow(root):
    return _git(root, "rev-parse", "--is-shallow-repository") == "true"


def test_a_shallow_clone_is_unshallowed_and_a_second_run_does_nothing(tmp_path):
    clone = _shallow_clone(tmp_path)
    assert _is_shallow(clone)
    stub = Stub()
    first = _load().start(clone, installer=stub, installed=lambda n: "1",
                          bga_ok=True)
    assert not _is_shallow(clone)
    assert "unshallowed" in first
    second = _load().start(clone, installer=stub, installed=lambda n: "1",
                           bga_ok=True)
    assert second == "session start: nothing to do"
    assert stub.pip == []


def test_a_missing_locked_package_runs_the_lock_install(tmp_path):
    clone = _shallow_clone(tmp_path)
    stub = Stub()
    line = _load().start(clone, installer=stub, installed=lambda n: None,
                         bga_ok=True)
    assert "installed the lock" in line
    assert [c[-2:] for c in stub.pip] == [["-r", "requirements.lock"]]


def test_a_linked_worktree_does_nothing(tmp_path):
    clone = _shallow_clone(tmp_path)
    linked = tmp_path / "linked"
    _git(clone, "worktree", "add", "-q", str(linked))
    stub = Stub()
    line = _load().start(linked, installer=stub, installed=lambda n: None,
                         bga_ok=False)
    assert line == ""
    assert stub.pip == []
    assert _is_shallow(clone)


def test_a_raising_installer_still_returns_a_line(tmp_path):
    clone = _shallow_clone(tmp_path)

    def boom(cmd, cwd):
        raise OSError("no network")

    line = _load().start(clone, installer=boom, installed=lambda n: None,
                         bga_ok=False)
    assert line.startswith("session start: skipped")


def test_the_shell_entry_exits_zero_outside_a_repo(tmp_path):
    done = subprocess.run([str(HOOKS / "session-start.sh")], cwd=tmp_path,
                          env={"PATH": "/usr/bin:/bin", "PYTHONPATH": str(REPO), "CLAUDE_PROJECT_DIR":
                               str(tmp_path)},
                          capture_output=True, text=True, timeout=60)
    assert done.returncode == 0


def test_missing_locked_names_only_absent_pins():

    lock = "a==1\n    # via b\nb-c==2\n"
    assert _load().missing_locked(lock, lambda n: None if n == "b-c" else "1") == ["b-c"]
