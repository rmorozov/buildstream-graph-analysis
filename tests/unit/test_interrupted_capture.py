"""UX-157: Ctrl-C on an hours-long capture must keep the trace it has.

Round 16 interrupted a live capture and got a raw `KeyboardInterrupt`
traceback and a snapshot holding only `build.log`. The mechanism was
structural: every Plane 2 artifact lives in the scratch *during* the
build and is copied out only after `run_wrapped` returns, so an
exception skipped the copies and `capture_scratch`'s `finally:
shutil.rmtree` then deleted hours of trace that were already on disk.
"""
import os
import signal
import subprocess
import sys

import pytest

from tools import bst_native_build_tracer as tracer
from tools.bst_run_wrapped import shutdown_build_group, signal_build_group


class _FakeProc:
    """Records what it was sent instead of dying, so the escalation
    ladder can be walked without real processes."""

    def __init__(self, dies_after=0):
        self.pid = os.getpid()
        self.signals = []
        self.dies_after = dies_after
        self.waits = 0

    def wait(self, timeout=None):
        self.waits += 1
        if self.waits > self.dies_after:
            return 0
        raise subprocess.TimeoutExpired("bst", timeout)


class TestTheBuildIsStoppedNotOrphaned:
    def test_sigint_first_because_bst_handles_it(self, monkeypatch):
        """`bst` shuts down gracefully on SIGINT - it stops scheduling and
        writes its summary, which is what makes the partial Plane 1 log
        worth salvaging. Anything harsher first would throw that away."""
        sent = []
        monkeypatch.setattr(os, "killpg", lambda pgid, sig: sent.append(sig))
        monkeypatch.setattr(os, "getpgid", lambda pid: 4242)

        shutdown_build_group(_FakeProc(dies_after=0))

        assert sent == [signal.SIGINT]

    def test_it_escalates_when_the_build_ignores_sigint(self, monkeypatch):
        sent = []
        monkeypatch.setattr(os, "killpg", lambda pgid, sig: sent.append(sig))
        monkeypatch.setattr(os, "getpgid", lambda pid: 4242)

        # Survives the SIGINT wait, goes on the SIGTERM one.
        shutdown_build_group(_FakeProc(dies_after=1), grace=0.01)

        assert sent == [signal.SIGINT, signal.SIGTERM]

    def test_it_reaches_sigkill_for_a_build_that_will_not_go(self, monkeypatch):
        sent = []
        monkeypatch.setattr(os, "killpg", lambda pgid, sig: sent.append(sig))
        monkeypatch.setattr(os, "getpgid", lambda pid: 4242)

        shutdown_build_group(_FakeProc(dies_after=99), grace=0.01)

        assert sent == [signal.SIGINT, signal.SIGTERM, signal.SIGKILL]

    def test_it_signals_the_group_not_the_child(self, monkeypatch):
        """Round 16 watched a `bst` build on for hours after the `bga`
        that started it was gone, because nothing addressed anything but
        the direct child. `killpg`, not `kill`."""
        called = {}
        monkeypatch.setattr(os, "killpg",
                            lambda pgid, sig: called.update(pgid=pgid, sig=sig))
        monkeypatch.setattr(os, "getpgid", lambda pid: 4242)

        signal_build_group(_FakeProc(), signal.SIGINT)

        assert called == {"pgid": 4242, "sig": signal.SIGINT}

    def test_a_group_that_is_already_gone_is_not_an_error(self, monkeypatch):
        """Racing the build's own exit is the normal case here."""
        def boom(pgid, sig):
            raise ProcessLookupError()
        monkeypatch.setattr(os, "killpg", boom)
        monkeypatch.setattr(os, "getpgid", lambda pid: 4242)

        signal_build_group(_FakeProc(), signal.SIGINT)  # must not raise

    def test_run_wrapped_spawns_the_build_in_its_own_group(self, tmp_path):
        """The property all the forwarding above depends on, measured on
        the build `run_wrapped` actually starts.

        Deleting `start_new_session=True` used to redden nothing: the
        first version of this test spawned its own `Popen` and checked
        that, which proves only that Python's kwarg works.
        """
        fake_bst = tmp_path / "bst"
        fake_bst.write_text(
            f"#!{sys.executable}\nimport os\nprint('PGID', os.getpgid(0))\n")
        fake_bst.chmod(0o755)
        log = tmp_path / "wrapped.log"

        from tools.bst_run_wrapped import run_wrapped
        with open(log, "w", encoding="utf-8") as handle:
            run_wrapped(str(tmp_path), [str(fake_bst)], handle)

        reported = int([line for line in log.read_text().splitlines()
                        if "PGID" in line][0].split("PGID")[1])
        assert reported != os.getpgid(0), (
            "the build shares this process's group, so a signal aimed at it "
            "would hit bga too - and nothing could be forwarded selectively")


class TestRunWrappedActuallyCallsTheShutdown:
    """Deleting the `shutdown_build_group` call reddened nothing at first:
    every test above calls it directly, so none of them checked that
    anything invokes it. Testing a function is not testing its caller.
    """

    class _Proc:
        pid = 1234
        returncode = None

        class _Stdout:
            def __iter__(self):
                raise KeyboardInterrupt()

        stdout = _Stdout()

        def wait(self, timeout=None):
            return 0

    def _run(self, tmp_path, monkeypatch, exc_type):
        import tools.bst_run_wrapped as rw
        called = []
        monkeypatch.setattr(rw.subprocess, "Popen", lambda *a, **k: self._Proc())
        monkeypatch.setattr(rw, "shutdown_build_group",
                            lambda proc, emit=None, **kw: called.append(proc))
        with open(tmp_path / "log", "w", encoding="utf-8") as handle:
            with pytest.raises(exc_type):
                rw.run_wrapped(str(tmp_path), ["bst", "build", "x.bst"], handle)
        return called

    def test_an_interrupt_stops_the_build_before_propagating(self, tmp_path, monkeypatch):
        assert len(self._run(tmp_path, monkeypatch, KeyboardInterrupt)) == 1

    def test_it_stops_the_build_on_any_exception_not_just_interrupts(
            self, tmp_path, monkeypatch):
        """Whatever gets us out of the read loop leaves a build running
        that nobody is reading from any more."""
        import tools.bst_run_wrapped as rw

        class _Boom(self._Proc):
            class _Stdout:
                def __iter__(self):
                    raise RuntimeError("pipe died")
            stdout = _Stdout()

        called = []
        monkeypatch.setattr(rw.subprocess, "Popen", lambda *a, **k: _Boom())
        monkeypatch.setattr(rw, "shutdown_build_group",
                            lambda proc, emit=None, **kw: called.append(proc))
        with open(tmp_path / "log", "w", encoding="utf-8") as handle:
            with pytest.raises(RuntimeError):
                rw.run_wrapped(str(tmp_path), ["bst", "build", "x.bst"], handle)
        assert len(called) == 1


class TestTheTraceSurvivesTheInterrupt:
    """The heart of it: the copy-out is in a `finally`."""

    def _capture(self, tmp_path, monkeypatch, raiser):
        project = tmp_path / "proj"
        project.mkdir()
        raw_log = tmp_path / "trace.log"
        monkeypatch.setattr(tracer, "compile_hook", lambda d: None)
        monkeypatch.setattr(tracer, "install_bwrap_shim", lambda d: "/usr/bin/bwrap")
        monkeypatch.setattr(tracer, "write_bwrap_shim", lambda d: os.path.join(d, "bwrap"))
        monkeypatch.setattr(tracer, "probe_bwrap_shim", lambda p: None)

        def fake_run(cmd, cwd=None, env=None, **kwargs):
            # The hook has already written its trace by the time an
            # interrupt lands - that is the whole point of the item.
            with open(os.path.join(env["BST_TRACE_BIND_SRC"], "trace.log"),
                      "w", encoding="utf-8") as handle:
                handle.write("START pid=1 element=core.bst\n")
            raiser()

        monkeypatch.setattr(tracer.subprocess, "Popen", fake_run)
        return project, raw_log

    def test_an_interrupt_keeps_the_trace_already_on_disk(self, tmp_path, monkeypatch):
        def interrupt():
            raise KeyboardInterrupt()
        project, raw_log = self._capture(tmp_path, monkeypatch, interrupt)

        with pytest.raises(tracer.CaptureInterrupted):
            tracer.run_traced_build(str(project), ["bst", "build", "x.bst"],
                                    str(raw_log))

        assert raw_log.read_text() == "START pid=1 element=core.bst\n"

    def test_the_scratch_is_still_cleaned_up(self, tmp_path, monkeypatch):
        def interrupt():
            raise KeyboardInterrupt()
        project, raw_log = self._capture(tmp_path, monkeypatch, interrupt)

        with pytest.raises(tracer.CaptureInterrupted):
            tracer.run_traced_build(str(project), ["bst", "build", "x.bst"],
                                    str(raw_log))

        scratch = project / ".bga" / "tmp"
        assert not any(scratch.iterdir()), "the scratch must not leak on this path"

    def test_any_other_exception_also_keeps_the_trace(self, tmp_path, monkeypatch):
        """`finally`, not `except KeyboardInterrupt` - a crash mid-build
        loses the trace just as thoroughly as an interrupt does."""
        def blow_up():
            raise RuntimeError("something else entirely")
        project, raw_log = self._capture(tmp_path, monkeypatch, blow_up)

        with pytest.raises(RuntimeError):
            tracer.run_traced_build(str(project), ["bst", "build", "x.bst"],
                                    str(raw_log))

        assert raw_log.read_text() == "START pid=1 element=core.bst\n"

    def test_an_interrupt_is_reported_as_its_own_kind_of_failure(
            self, tmp_path, monkeypatch):
        """Not a bare 130 exit status: that is how an interrupt got
        mistaken for a build failure in the first place."""
        def interrupt():
            raise KeyboardInterrupt()
        project, raw_log = self._capture(tmp_path, monkeypatch, interrupt)

        with pytest.raises(tracer.CaptureInterrupted) as caught:
            tracer.run_traced_build(str(project), ["bst", "build", "x.bst"],
                                    str(raw_log))

        assert "interrupted" in str(caught.value)
        assert isinstance(caught.value, tracer.TraceError)


class TestAnInterruptIsNotAFailedBuild:
    def test_the_run_context_records_it(self):
        from bga.ingest.models import RunContext
        interrupted = RunContext(build_outcome={"failed_elements": [],
                                                "failed_count": 0,
                                                "interrupted": True})
        assert interrupted.interrupted
        assert interrupted.incomplete_reason == "interrupted"

    def test_a_finished_build_is_neither(self):
        from bga.ingest.models import RunContext
        clean = RunContext(build_outcome={"failed_elements": [], "failed_count": 0,
                                          "interrupted": False})
        assert not clean.interrupted
        assert clean.incomplete_reason is None

    def test_a_failed_build_still_reports_as_failed(self):
        from bga.ingest.models import RunContext
        failed = RunContext(build_outcome={"failed_elements": ["lib-d.bst"],
                                           "failed_count": 1})
        assert failed.incomplete_reason == "failed"

    def test_the_verdict_says_interrupted_not_failed(self):
        """"The build failed" would send a user looking for a compile
        error that does not exist."""
        from bga.compare import _describe_build_failures
        text = _describe_build_failures([{
            'run': 'candidate', 'failed_elements': [], 'built': 3,
            'scheduled': 11, 'interrupted': True}])
        assert "was interrupted" in text
        assert "failed" not in text.replace("unfinished", "")

    def test_an_interrupted_snapshot_is_skipped_as_a_baseline(self, tmp_path):
        """UX-156 skips wreckage; an interrupted run is wreckage too."""
        import json
        from tools.bga_snapshot import _snapshot_failed
        run = tmp_path / "snap" / "run"
        run.mkdir(parents=True)
        (run / "run-context.json").write_text(json.dumps(
            {"build_outcome": {"failed_elements": [], "failed_count": 0,
                               "interrupted": True}}))
        assert _snapshot_failed(str(tmp_path / "snap"))
