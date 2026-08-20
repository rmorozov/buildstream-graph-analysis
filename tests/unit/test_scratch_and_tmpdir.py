"""UX-155: bga's scratch is project-local, and TMPDIR is left alone.

Filed from a field report that took two steps, the second of which bga
supplied: a capture failed on temp-directory permissions, and
`probe_bwrap_shim`'s advice was "set TMPDIR". The user set it to a
relative path and `buildbox-casd` died with
`error in mkdtemp, errno: no such file or directory`.
"""
import os
import subprocess
import sys

import pytest

from bga import run_store
from tools import bst_native_build_tracer as tracer


class TestScratchIsProjectLocal:
    def test_scratch_dir_is_under_the_projects_bga(self, tmp_path):
        project = str(tmp_path)
        assert run_store.scratch_dir(project) == os.path.join(project, ".bga", "tmp")

    def test_scratch_dir_creates_nothing(self, tmp_path):
        """Resolution stays safe to call anywhere, as the rest of the store is."""
        run_store.scratch_dir(str(tmp_path))
        assert not (tmp_path / ".bga").exists()

    def test_capture_scratch_lands_in_the_project_not_tmpdir(self, tmp_path, monkeypatch):
        """The whole point: TMPDIR is where this used to go, and must not now."""
        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        monkeypatch.setenv("TMPDIR", str(elsewhere))
        project = tmp_path / "proj"
        project.mkdir()
        with tracer.capture_scratch(str(project), "trace-") as scratch:
            assert scratch.startswith(str(project / ".bga" / "tmp"))
            assert not os.listdir(elsewhere)

    def test_capture_scratch_removes_what_it_made(self, tmp_path):
        project = tmp_path / "proj"
        project.mkdir()
        with tracer.capture_scratch(str(project), "trace-") as scratch:
            open(os.path.join(scratch, "f"), "w").close()
        assert not os.path.exists(scratch)

    def test_a_file_written_there_can_be_executed(self, tmp_path):
        """`install_bwrap_shim` puts a `bwrap` on $PATH from this directory.

        A scratch bga cannot execute from is the original failure, so the
        directory choice is only worth anything if this holds.
        """
        project = tmp_path / "proj"
        project.mkdir()
        with tracer.capture_scratch(str(project), "trace-") as scratch:
            script = os.path.join(scratch, "probe")
            with open(script, "w", encoding="utf-8") as handle:
                handle.write("#!/bin/sh\nexit 0\n")
            os.chmod(script, 0o755)
            assert subprocess.run([script]).returncode == 0

    def test_a_project_it_cannot_write_to_falls_back_rather_than_refusing(
            self, tmp_path, capsys):
        """A scratch directory bga cannot make is a reason to fall back, not to
        refuse to capture - but it says so, because the fallback lands
        back in `TMPDIR`, which is the `noexec` case this item is about.

        The obstruction is a regular file where `.bga` should be, not a
        mode bit: this suite runs as root often enough (in this
        container, and in CI) that `chmod 0o500` proves nothing there -
        the first version of this test passed for the wrong reason.
        """
        project = tmp_path / "obstructed"
        project.mkdir()
        (project / ".bga").write_text("not a directory")
        with tracer.capture_scratch(str(project), "trace-") as scratch:
            assert os.path.isdir(scratch)
            assert not scratch.startswith(str(project))
        assert "not writable" in capsys.readouterr().err

    def test_a_bga_created_only_for_scratch_still_ignores_itself(self, tmp_path):
        """Otherwise a capture that never snapshots leaves the first untracked
        `.bga/` in the user's project with no `.gitignore` beside it."""
        project = tmp_path / "proj"
        project.mkdir()
        with tracer.capture_scratch(str(project), "trace-"):
            pass
        assert (project / ".bga" / ".gitignore").is_file()

    def test_scratch_mkdtemp_also_lands_in_the_project(self, tmp_path, monkeypatch):
        """`run`'s unnamed intermediates, which outlive any `with` block."""
        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        monkeypatch.setenv("TMPDIR", str(elsewhere))
        project = tmp_path / "proj"
        project.mkdir()
        made = tracer.scratch_mkdtemp(str(project), "trace-log-")
        assert made.startswith(str(project / ".bga" / "tmp"))
        assert not os.listdir(elsewhere)


class TestRelativeTmpdirIsMadeAbsolute:
    """The half bga cannot fix by moving its own files.

    Python's `tempfile` treats a relative `TMPDIR` as one candidate and
    falls back when it is unusable, so bga appears to accept it.
    `buildbox-casd` is C++, `chdir`s to the cache directory, and its
    `mkdtemp` takes the value literally.
    """

    def test_a_relative_tmpdir_is_resolved(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        env = tracer.absolute_tmpdir_env({"TMPDIR": "rel_tmp"})
        assert env["TMPDIR"] == os.path.join(str(tmp_path), "rel_tmp")
        assert os.path.isabs(env["TMPDIR"])

    def test_an_absolute_tmpdir_is_left_exactly_as_it_was(self):
        env = tracer.absolute_tmpdir_env({"TMPDIR": "/var/tmp/mine"})
        assert env["TMPDIR"] == "/var/tmp/mine"

    def test_an_unset_tmpdir_is_not_invented(self):
        assert "TMPDIR" not in tracer.absolute_tmpdir_env({})

    def test_it_says_so_rather_than_changing_the_environment_silently(
            self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        tracer.absolute_tmpdir_env({"TMPDIR": "rel_tmp"})
        err = capsys.readouterr().err
        assert "TMPDIR" in err and "rel_tmp" in err
        assert "mkdtemp" in err, "the message should name the error the user will have seen"

    def test_normalize_tmpdir_fixes_os_environ_so_children_inherit_it(
            self, tmp_path, monkeypatch):
        """The child `env` dict alone was not enough.

        Measured against a wrapper on `buildbox-casd`: the traced build
        got the corrected value and `extract_run`'s `bst show` did not,
        because it spawns from `os.environ`. Assigning through
        `os.environ` calls `putenv`, so a real child sees it - which is
        what this asserts, rather than just re-reading `os.environ`.
        """
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("TMPDIR", "rel_tmp")
        tracer.normalize_tmpdir()
        seen = subprocess.run(
            [sys.executable, "-c", "import os; print(os.environ['TMPDIR'])"],
            capture_output=True, text=True, check=True).stdout.strip()
        assert seen == os.path.join(str(tmp_path), "rel_tmp")
        assert os.path.isabs(seen)

    def test_normalize_tmpdir_is_a_no_op_when_there_is_nothing_to_fix(
            self, monkeypatch):
        monkeypatch.setenv("TMPDIR", "/var/tmp/mine")
        tracer.normalize_tmpdir()
        assert os.environ["TMPDIR"] == "/var/tmp/mine"


class TestTheAdviceThatCausedTheReport:
    def test_the_probe_no_longer_tells_anyone_to_set_tmpdir(self, tmp_path):
        """The exact sentence the user followed into the second failure."""
        shim = tmp_path / "bwrap"
        shim.write_text("#!/bin/sh\nexit 0\n")
        os.chmod(shim, 0o644)  # present, not executable
        with pytest.raises(tracer.TraceError) as caught:
            tracer.probe_bwrap_shim(str(shim))
        message = str(caught.value)
        assert "Set TMPDIR" not in message
        assert ".bga/tmp" in message, "it should name where the shim actually lives"
