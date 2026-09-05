"""UX-405: a relative `--project` forfeited Plane 2, in silence.

The documented shape, run from the repository root against a cold
`lib-c.bst`:

```text
bga snapshot --project examples/06-macro-micro-optimization \\
    --trace-opens --trace-spine=on -- bst build lib-c.bst

before   Processes traced: 0 (0 matched, 0 no observed exit)     exit 0
after    Processes traced: 87 (87 matched, 0 no observed exit)   exit 0
         By element:  lib-c.bst  87
```

Empty `plane2.log.gz`, green snapshot, and the whole second plane gone.
The mechanism: everything the capture hands to another process is
derived from `project_dir` - the scratch root, the shim directory that
goes on `PATH`, and `BST_TRACE_BIND_SRC`. **A relative `PATH` entry
resolves against each process's own working directory**, and
`buildbox-casd` chdirs away, so nothing found the shim and the real
`bwrap` ran untraced.

That is `UX-155`'s lesson one variable over: the same module's docstring
already records a user who was told to set a relative `TMPDIR` and got
`mkdtemp` errors out of C++ that Python had silently tolerated.

**Two clauses, because the bug had two halves.** The paths are absolute
now - held here without a build, which is what makes it a guard rather
than an anecdote. And a capture that saw nothing while sandboxes ran
says so: the old run printed "ELEMENT ATTRIBUTION UNRELIABLE" and
completed green, which is `UX-107`'s rule ("nobody could look" must not
read as "looked and found nothing") broken at the loudest possible
place.
"""
import os
import pathlib
import shutil
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.bst_native_build_tracer import (
    capture_scratch,
    format_untraced_build_warning,
    run_traced_build,
)

#: One string each, so `UX-213`'s skip census counts them once.
NO_CC = "no C compiler on PATH"
#: `install_bwrap_shim` writes a shim that *falls back* to the real
#: `bwrap`, and refuses when there is none to fall back to. This clause
#: reaches that call before it reaches anything it is about, so on a
#: machine without bwrap it fails rather than skipping - which is
#: `UX-213`'s class, and is how it passed here and failed on every CI
#: runner: the `test` job installs a C compiler and no sandbox.
NO_BWRAP = "no bwrap for the capture's shim to fall back to"


class TestThePathsTheBuildInherits:
    """What leaves this process has to survive another one's chdir."""

    def test_the_scratch_of_a_relative_project_is_absolute(self, tmp_path):
        project = tmp_path / "proj"
        project.mkdir()
        here = os.getcwd()
        os.chdir(tmp_path)
        try:
            with capture_scratch("proj", "trace-") as scratch:
                assert os.path.isabs(scratch), (
                    f"the capture's scratch is {scratch!r}; every path "
                    "derived from it - the shim directory on PATH, the bind "
                    "source - is then relative to whichever process reads it")
        finally:
            os.chdir(here)

    @pytest.mark.skipif(shutil.which("cc") is None
                        and shutil.which("gcc") is None, reason=NO_CC)
    @pytest.mark.skipif(shutil.which("bwrap") is None, reason=NO_BWRAP)
    def test_every_path_the_build_inherits_is_absolute(self, tmp_path,
                                                       monkeypatch):
        """The real environment, from a real relative invocation.

        No `bst` and no sandbox: the wrapped command is `true`, and the
        `Popen` that would run it is intercepted so the guard can read
        the environment the build would have inherited. Everything
        before that point - the scratch, the compiled hook, the shim -
        is the shipping path, unchanged.
        """
        project = tmp_path / "proj"
        project.mkdir()
        seen = {}

        class _Finished:
            def wait(self):
                return 0

        real_popen = subprocess.Popen

        def spy(cmd, cwd=None, env=None, **kwargs):
            # The build's own spawn is the one that asks for its own
            # session (`UX-157`, so an interrupt cannot orphan it).
            # Everything else here - the hook compile, the shim probe -
            # is real work this guard wants to actually happen.
            if kwargs.get("start_new_session"):
                seen["cwd"] = cwd
                seen["env"] = dict(env or {})
                # Read at spawn time: the scratch is a context manager
                # and is gone by the time this function returns, so a
                # check afterwards would be checking a deleted path.
                first = (env or {}).get("PATH", "").split(os.pathsep)[0]
                seen["shim_exists"] = os.path.isfile(
                    os.path.join(first, "bwrap"))
                seen["hook_exists"] = os.path.isfile(os.path.join(
                    (env or {}).get("BST_TRACE_BIND_SRC", ""), "hook.so"))
                return _Finished()
            return real_popen(cmd, cwd=cwd, env=env, **kwargs)

        monkeypatch.setattr(
            "tools.bst_native_build_tracer.subprocess.Popen", spy)

        here = os.getcwd()
        os.chdir(tmp_path)
        try:
            code = run_traced_build(
                "proj", ["true"], str(tmp_path / "raw.log"))
        finally:
            os.chdir(here)
        assert code == 0
        assert seen, "the build was never spawned, so nothing was measured"

        assert os.path.isabs(seen["cwd"]), (
            f"the build runs with cwd={seen['cwd']!r}; a relative cwd is the "
            "same class of defect one argument over")

        # The shim goes on the *front* of PATH, so the entry under test
        # is the one this capture added rather than the host's.
        prepended = seen["env"]["PATH"].split(os.pathsep)[0]
        assert os.path.isabs(prepended), (
            f"PATH begins with {prepended!r}. A relative PATH entry "
            "resolves against each process's own working directory, and "
            "buildbox-casd chdirs away - which is how a capture traces 0 "
            "of 87 processes and exits 0")
        assert seen["shim_exists"], (
            f"{prepended} is absolute but held no bwrap shim when the build "
            "was spawned, so the PATH entry points somewhere that cannot "
            "intercept the sandbox")

        bind = seen["env"]["BST_TRACE_BIND_SRC"]
        assert os.path.isabs(bind), (
            f"BST_TRACE_BIND_SRC is {bind!r}; the shim reads it after bst "
            "has moved, so a relative value binds nothing")
        assert seen["hook_exists"], (
            f"{bind} is absolute but held no hook.so when the build was "
            "spawned")


class TestACaptureThatSawNothingSaysSo:
    """`UX-107`'s three states, at the loudest place in the tool."""

    def test_sandboxes_ran_and_nothing_was_traced_is_loud(self):
        said = format_untraced_build_warning(0, 9)
        assert said, (
            "a build that ran 9 sandbox tasks and traced 0 processes has "
            "no second plane, and used to print a confident report anyway")
        assert "9 sandbox" in said, (
            "the warning states what it counted; a warning with no number "
            "cannot be checked by the person reading it")
        assert "--diagnose" in said, (
            "and what to run next - `UX-147`'s rule that the failing user "
            "is told what would answer the question")

    def test_nothing_launched_a_sandbox_is_a_result_not_a_failure(self):
        assert format_untraced_build_warning(0, 0) is None, (
            "a fully cached build legitimately traces nothing; warning "
            "there would train the reader to ignore this")

    def test_no_plane_one_log_is_cannot_say(self):
        assert format_untraced_build_warning(0, None) is None, (
            "without a Plane 1 log there is no count to compare against, "
            "and `UX-308`'s rule is that absence is stated, not guessed")

    def test_a_capture_that_saw_processes_says_nothing(self):
        assert format_untraced_build_warning(87, 9) is None
