"""UX-773: `atexit` (`browser._close_shared`) never runs for a worker
`SIGKILL`ed mid-test, so the Chrome it started - reparented to pid 1 -
and its profile survive it. Round 107 read the margin that ate into
disk headroom as `UX-760`'s reserve arithmetic; it was this leak.

A subprocess launches a `Browser` and kills itself with `SIGKILL` from
inside the `with` - exactly the exit `atexit` cannot reach. The guard's
own claim is what a **second** `Browser` entry, in this process, does
about it: `browser._sweep_stale()` runs on every entry, before making
its own root, so the process that starts cleans up the one the signal
cut off.

Both `tempfile.tempdir` here and `TMPDIR` for the subprocess point at
this test's own directory, so the count is this guard's and not
whatever else this machine is running under `-n auto`.

That directory is **not** `tmp_path`: Chrome keeps a `SingletonSocket`
inside its profile, a `PF_UNIX` path capped at ~104 bytes, and
`tmp_path`'s own name embeds this test's - a launch that opens its
port in every other guard failed every time here once nested under
it. A short root of our own making stays under that ceiling.
"""
import glob
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tests"))

from browser import NO_BROWSER, Browser, find_chrome

CHROME = find_chrome()
needs_browser = pytest.mark.skipif(CHROME is None, reason=NO_BROWSER)

#: Prints its profile, then kills itself before its own `__exit__` (or
#: `atexit`) ever runs - the case this guard is about.
_LAUNCH_AND_SIGKILL = """
import os, signal, sys
sys.path.insert(0, {tests_dir!r})
import browser as b
with b.Browser({binary!r}) as br:
    print(br.profile, flush=True)
    os.kill(os.getpid(), signal.SIGKILL)
"""


def _profiles(where):
    return glob.glob(os.path.join(str(where), "bga-geometry-*"))


def _pids_using(profile):
    """Every pid whose command line names `profile` - the leaked
    Chrome, if it is still there."""
    needle = profile.encode()
    found = []
    for entry in glob.glob("/proc/[0-9]*"):
        try:
            cmdline = pathlib.Path(entry, "cmdline").read_bytes()
        except OSError:
            continue
        if needle in cmdline:
            found.append(os.path.basename(entry))
    return found


@pytest.fixture
def isolated_tmp(monkeypatch):
    """`mkdtemp` with no `dir=` lands here, in this process and in the
    launcher subprocess (`TMPDIR`), so the count is this guard's alone -
    a root of our own rather than `tmp_path` (see the module docstring)."""
    scratch = tempfile.mkdtemp(prefix="ux773-")
    monkeypatch.setattr(tempfile, "tempdir", scratch)
    monkeypatch.setenv("TMPDIR", scratch)
    yield scratch
    shutil.rmtree(scratch, ignore_errors=True)


def _launch_and_kill(where):
    script = _LAUNCH_AND_SIGKILL.format(
        tests_dir=str(REPO / "tests"), binary=CHROME)
    done = subprocess.run(
        [sys.executable, "-c", script], env=dict(os.environ, TMPDIR=str(where)),
        capture_output=True, text=True, timeout=60)
    lines = done.stdout.strip().splitlines()
    profile = lines[-1] if lines else ""
    assert profile, (
        f"launcher printed no profile (code {done.returncode}): "
        f"{done.stderr[-500:]}")
    assert done.returncode < 0, (
        f"launcher exited {done.returncode}, not by signal - the case "
        f"this guard is about")
    return profile


@needs_browser
class TestAKilledBrowserDoesNotOutliveTheWorker:

    #: `UX-783`: whether this worker already holds `UX-523`'s shared
    #: browser. It decides whether the second entry makes a root of its
    #: own or returns early reusing one - and the sweep must happen
    #: either way, which is the claim. The clause ran only the `False`
    #: case until a verifier composed this file with a sibling geometry
    #: guard and got the reuse path, where the old bookkeeping
    #: (`after == before + 1`) is false by construction.
    @pytest.mark.parametrize("reusing", [False, True])
    def test_a_second_entry_sweeps_the_first(self, isolated_tmp, reusing):
        import browser as module
        module._close_shared()
        try:
            if reusing:
                with Browser(CHROME):
                    pass
                assert module._SHARED, (
                    "the reuse case needs a live shared browser and has "
                    "none - this parameter would repeat the other")

            before = len(_profiles(isolated_tmp))
            profile = _launch_and_kill(isolated_tmp)

            # The positive control: without it, "gone afterwards" would
            # be satisfied by a launcher that never leaked anything.
            assert os.path.isdir(profile), (
                "the killed launcher's own profile is gone already - "
                "nothing here for a sweep to prove itself against")
            left = _pids_using(profile)
            assert left, (
                "no process names the leaked profile - reparenting did "
                "not happen the way this guard assumes, so it would "
                "prove nothing")
            during = len(_profiles(isolated_tmp))
            assert during == before + 1, f"before={before} during={during}"

            with Browser(CHROME) as second:
                assert not os.path.isdir(profile), (
                    f"a second Browser entry left {profile} behind")
                assert not _pids_using(profile), (
                    f"a second Browser entry left {_pids_using(profile)} "
                    f"still using {profile}")
                # A reused entry makes no root; a fresh one makes
                # exactly its own. Counting a fixed +1 is what tied
                # this clause to the order the worker happened to run.
                own = 0 if second._reused else 1
                after = len(_profiles(isolated_tmp))
                assert after == before + own, (
                    f"reusing={reusing} second._reused={second._reused}: "
                    f"expected before={before}+{own}, got {after}")
        finally:
            # An entry becomes `_SHARED` and would otherwise outlive the
            # `with`, still running when `isolated_tmp` removes its root
            # at teardown - closed here rather than left for this
            # process's own `atexit`.
            module._close_shared()
