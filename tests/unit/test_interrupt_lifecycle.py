"""UX-163: the interrupt contract has to cover the minutes around the build.

UX-157's salvage works mid-build, but the conversion happens inside
`run_traced_build`, so it protected only interrupts landing while `bst`
runs. Round 17 hit the other window live: a SIGINT during
`Extracting run data (bst show)...` produced a raw traceback and a
snapshot with no `run/` - even though `build.log` was complete on disk
and extraction is re-runnable from it, which nothing said.

On a big project the unprotected windows are the *long* ones: the census
before, extraction after. They are the phases UX-159 gave announcement
lines precisely because they take minutes, which makes them exactly where
someone who has waited three hours presses Ctrl-C.
"""
import os

from tools.bst_native_build_tracer import format_post_build_interrupt
from tools.bst_run_wrapped import (
    DEFAULT_SIGINT_GRACE, SIGINT_GRACE_ENV, sigint_grace_seconds,
)


class TestThePostBuildNotice:
    def test_it_names_the_artifacts_already_on_disk(self, tmp_path):
        log = tmp_path / "build.log"
        log.write_text("x")
        report = tmp_path / "plane2.json"
        report.write_text("{}")
        text = format_post_build_interrupt(str(report), str(log),
                                           str(tmp_path / "run"), str(tmp_path))
        assert "Already on disk" in text
        assert str(log) in text and str(report) in text

    def test_it_names_the_command_that_finishes_the_job(self, tmp_path):
        """Nothing needs rebuilding - extraction is a pure function of the
        log, and round 17's user was told none of that."""
        log = tmp_path / "build.log"
        log.write_text("x")
        text = format_post_build_interrupt(None, str(log),
                                           str(tmp_path / "run"), str(tmp_path))
        assert "bga extract --format wrapped" in text
        assert str(log) in text
        assert str(tmp_path / "run") in text

    def test_a_completed_run_directory_is_not_offered_for_extraction(self, tmp_path):
        log = tmp_path / "build.log"
        log.write_text("x")
        run = tmp_path / "run"
        run.mkdir()
        text = format_post_build_interrupt(None, str(log), str(run), str(tmp_path))
        assert "bga extract" not in text
        assert "complete" in text

    def test_it_says_the_build_itself_finished(self, tmp_path):
        """The distinction that matters to someone deciding whether to
        re-run: this interrupt cost post-processing, not the build."""
        text = format_post_build_interrupt(None, None, None, None)
        assert "build itself completed" in text

    def test_a_missing_log_offers_no_command_it_cannot_honour(self, tmp_path):
        text = format_post_build_interrupt(None, str(tmp_path / "gone.log"),
                                           str(tmp_path / "run"), str(tmp_path))
        assert "bga extract" not in text


class TestTheGraceWindow:
    def test_the_default_is_longer_than_the_original_guess(self):
        """120s was a guess, and round 17 found the cost of getting it
        wrong: SIGTERM kills bst before its closing Pipeline Summary, the
        run loses `queue_summary`, and the "N of M scheduled" clause -
        the most useful number - disappears from the biggest builds."""
        assert DEFAULT_SIGINT_GRACE > 120.0

    def test_it_is_overridable(self, monkeypatch):
        monkeypatch.setenv(SIGINT_GRACE_ENV, "900")
        assert sigint_grace_seconds() == 900.0

    def test_a_nonsense_value_falls_back_rather_than_crashing(self, monkeypatch):
        monkeypatch.setenv(SIGINT_GRACE_ENV, "not-a-number")
        assert sigint_grace_seconds() == DEFAULT_SIGINT_GRACE
        monkeypatch.setenv(SIGINT_GRACE_ENV, "-5")
        assert sigint_grace_seconds() == DEFAULT_SIGINT_GRACE

    def test_shutdown_reports_whether_bst_stopped_on_its_own(self, monkeypatch):
        """The caller needs to know: a killed bst never printed its summary,
        so a missing queue_summary is an escalation artifact rather than
        absent-by-nature."""
        import subprocess as sp
        from tools.bst_run_wrapped import shutdown_build_group

        class _Proc:
            pid = os.getpid()
            def __init__(self, dies): self.dies, self.waits = dies, 0
            def wait(self, timeout=None):
                self.waits += 1
                if self.waits > self.dies:
                    return 0
                raise sp.TimeoutExpired("bst", timeout)

        monkeypatch.setattr(os, "killpg", lambda *a: None)
        monkeypatch.setattr(os, "getpgid", lambda pid: 1)
        assert shutdown_build_group(_Proc(0), grace=0.01) is True
        assert shutdown_build_group(_Proc(1), grace=0.01) is False

    def test_the_escalation_message_names_the_knob(self, monkeypatch):
        import subprocess as sp
        from tools.bst_run_wrapped import shutdown_build_group

        class _Proc:
            pid = os.getpid()
            waits = 0
            def wait(self, timeout=None):
                self.waits += 1
                if self.waits > 1:
                    return 0
                raise sp.TimeoutExpired("bst", timeout)

        said = []
        monkeypatch.setattr(os, "killpg", lambda *a: None)
        monkeypatch.setattr(os, "getpgid", lambda pid: 1)
        shutdown_build_group(_Proc(), emit=said.append, grace=0.01)
        assert any(SIGINT_GRACE_ENV in message for message in said)


class TestEveryPhaseConverts:
    def test_main_catches_interrupts_from_the_pre_build_phases(self):
        """Compiling the hook and the census run before the build's own
        try/except, so they reached main as a bare KeyboardInterrupt."""
        import inspect
        from tools import bst_native_build_tracer as tracer
        source = inspect.getsource(tracer.main)
        assert source.count("except KeyboardInterrupt:") >= 2, (
            "both the pre-build and post-build windows need one")
        assert "Interrupted before the build started" in source

    def test_the_post_build_region_is_inside_a_handler(self):
        import inspect
        from tools import bst_native_build_tracer as tracer
        source = inspect.getsource(tracer.main)
        analysing = source.index("Analyzing the captured trace")
        handler = source.index("format_post_build_interrupt")
        assert analysing < handler, "the handler must follow the region it guards"
