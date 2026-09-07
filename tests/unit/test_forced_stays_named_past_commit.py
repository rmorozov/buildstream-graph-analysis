"""UX-766: a committed forced entry stays named in `--check`, not silent.

Mirrors `test_the_baseline_only_shrinks.py`'s temporary-package harness.
"""
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
TOOL = REPO / "tools" / "dev_baseline.py"

VIOLATION = ("import subprocess\n\n\n"
             "def f():\n"
             "    subprocess.run(cmd, shell=True)\n")


def _run(root, baseline, *flags):
    cmd = [sys.executable, str(TOOL), "--root", str(root), "--paths", "pkg",
           "--baseline", str(baseline), *flags]
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args],
                          capture_output=True, text=True, check=True)


def _force_and_commit(tmp_path, baseline, reason, message):
    assert _run(tmp_path, baseline, "--write", "--force",
                "--reason", reason).returncode == 0
    _git(tmp_path, "-c", "user.email=t@example.com", "-c", "user.name=t",
         "commit", "-q", "-am", message)


class TestForcedStaysNamedPastCommit:
    def test_a_committed_forced_entry_is_named_not_silent(self, tmp_path):
        module = tmp_path / "pkg" / "m.py"
        baseline = tmp_path / "baseline.json"
        _write(module, "def f():\n    return 1\n")
        assert _run(tmp_path, baseline, "--write").returncode == 0
        _git(tmp_path, "init", "-q")
        _git(tmp_path, "-c", "user.email=t@example.com", "-c", "user.name=t",
             "add", "-A")
        _git(tmp_path, "-c", "user.email=t@example.com", "-c", "user.name=t",
             "commit", "-q", "-m", "baseline")
        _write(module, VIOLATION)
        _force_and_commit(tmp_path, baseline, "UX-1", "UX-1 forces a finding")
        # Before this row: `--check` here printed only
        # "clean: N finding(s) match ...", indistinguishable from a
        # baseline nothing ever forced.
        check = _run(tmp_path, baseline, "--check")
        assert check.returncode == 0, check.stdout
        assert "still forced by UX-1" in check.stdout
        assert "clean:" in check.stdout

    def test_a_line_never_forced_stays_silent(self, tmp_path):
        module = tmp_path / "pkg" / "m.py"
        baseline = tmp_path / "baseline.json"
        _write(module, "def f():\n    return 1\n")
        assert _run(tmp_path, baseline, "--write").returncode == 0
        check = _run(tmp_path, baseline, "--check")
        assert check.returncode == 0, check.stdout
        assert "still forced" not in check.stdout
        assert check.stdout.strip().startswith("clean:")

    def test_an_uncommitted_forced_entry_is_not_double_named(self, tmp_path):
        """Pre-commit it is already named `authorised ... red until
        committed`; it must not also print as `still forced`."""
        module = tmp_path / "pkg" / "m.py"
        baseline = tmp_path / "baseline.json"
        _write(module, "def f():\n    return 1\n")
        assert _run(tmp_path, baseline, "--write").returncode == 0
        _git(tmp_path, "init", "-q")
        _git(tmp_path, "-c", "user.email=t@example.com", "-c", "user.name=t",
             "add", "-A")
        _git(tmp_path, "-c", "user.email=t@example.com", "-c", "user.name=t",
             "commit", "-q", "-m", "baseline")
        _write(module, VIOLATION)
        assert _run(tmp_path, baseline, "--write", "--force",
                    "--reason", "UX-1").returncode == 0
        check = _run(tmp_path, baseline, "--check")
        assert check.returncode == 1, check.stdout
        assert "authorised by UX-1, red until committed" in check.stdout
        assert "still forced" not in check.stdout

    def test_a_second_unrelated_force_does_not_silence_the_first(self, tmp_path):
        """The verifier's constructed defect: `write_baseline` held one
        `forced_by`/`forced` slot that a later `--force` overwrote, so
        `UX-OLD`'s lines dropped out of `still forced` (not out of
        `findings`) the moment an unrelated `UX-NEW` batch landed."""
        old = tmp_path / "pkg" / "old.py"
        new = tmp_path / "pkg" / "new.py"
        baseline = tmp_path / "baseline.json"
        _write(old, "def f():\n    return 1\n")
        assert _run(tmp_path, baseline, "--write").returncode == 0
        _git(tmp_path, "init", "-q")
        _git(tmp_path, "-c", "user.email=t@example.com", "-c", "user.name=t",
             "add", "-A")
        _git(tmp_path, "-c", "user.email=t@example.com", "-c", "user.name=t",
             "commit", "-q", "-m", "baseline")
        _write(old, VIOLATION)
        _force_and_commit(tmp_path, baseline, "UX-OLD", "UX-OLD forces a finding")
        _write(new, VIOLATION)
        _force_and_commit(tmp_path, baseline, "UX-NEW", "UX-NEW forces an unrelated one")
        check = _run(tmp_path, baseline, "--check")
        assert check.returncode == 0, check.stdout
        assert "still forced by UX-OLD" in check.stdout
        assert "still forced by UX-NEW" in check.stdout
