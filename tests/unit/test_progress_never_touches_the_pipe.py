"""UX-183: a moving number on a terminal, and nothing anywhere else.

The field request had two halves and the second one is the constraint:
*"progress bar and progression status messages would be great — but it
definitely can break some scenarios with passing tool output into
something through unix pipe."*

So the interesting tests here are the negative ones. Progress that
draws correctly on a TTY is worth a few assertions; progress that
cannot reach a pipe, a log file, or stdout is worth the rest of them.
"""
import io
import json
import os
import subprocess
import sys

import pytest

from bga import progress

GOLDEN = "tests/fixtures/golden/mixed_task_kinds"


class _FakeTTY(io.StringIO):
    """A stream that claims to be a terminal.

    A pty would test one more layer and cost a fixture that only runs on
    Linux; what is under test is the branch, and the branch reads
    `isatty()`.
    """

    def isatty(self):
        return True


class TestTheGate:
    def test_a_pipe_is_not_a_terminal(self):
        assert not progress.enabled(io.StringIO())

    def test_a_terminal_is(self, monkeypatch):
        monkeypatch.delenv("BGA_NO_PROGRESS", raising=False)
        assert progress.enabled(_FakeTTY())

    def test_the_environment_variable_wins_over_the_terminal(self, monkeypatch):
        monkeypatch.setenv("BGA_NO_PROGRESS", "1")
        assert not progress.enabled(_FakeTTY())

    def test_a_stream_that_cannot_answer_is_not_a_terminal(self):
        class Mute:
            pass

        assert not progress.enabled(Mute())

    def test_a_closed_stream_is_not_a_terminal(self, tmp_path):
        handle = open(tmp_path / "x", "w")
        handle.close()
        assert not progress.enabled(handle)


class TestWhatReachesANonTerminal:
    def test_nothing_at_all(self):
        """The whole pipe requirement, as one assertion: a ticker on a
        non-TTY writes zero bytes."""
        stream = io.StringIO()
        tick = progress.ticker("parsing trace", total=1000, stream=stream)
        for i in range(1000):
            tick.step(i)
        tick.done()
        assert stream.getvalue() == ""

    def test_no_carriage_return_ever_reaches_a_log_file(self, tmp_path):
        log = tmp_path / "capture.log"
        with open(log, "w") as handle:
            tick = progress.ticker("census", total=10, stream=handle)
            for i in range(10):
                tick.step(i)
            tick.done()
            progress.phase("Analyzing the captured trace...", stream=handle)
        text = log.read_text()
        assert "\r" not in text
        assert text == "Analyzing the captured trace...\n", (
            "a redirected stderr must carry the phase lines and nothing else")

    def test_the_phase_lines_are_unconditional(self):
        """`UX-159`'s behaviour is what the piped case still gets - the
        progress line is additive, not a replacement."""
        stream = io.StringIO()
        progress.phase("Extracting run data (bst show)...", stream=stream)
        assert stream.getvalue() == "Extracting run data (bst show)...\n"


class TestWhatATerminalSees:
    def test_the_line_is_drawn_and_overwrites_itself(self, monkeypatch):
        monkeypatch.delenv("BGA_NO_PROGRESS", raising=False)
        stream = _FakeTTY()
        tick = progress.ticker("parsing trace", total=480000, stream=stream)
        tick.step(120000)
        drawn = stream.getvalue()
        assert drawn.startswith("\r"), "a progress line must return the cursor"
        assert "parsing trace: 120000/480000" in drawn
        assert "\n" not in drawn, "it must not scroll the terminal"

    def test_it_is_cleared_before_the_next_whole_line(self, monkeypatch):
        monkeypatch.delenv("BGA_NO_PROGRESS", raising=False)
        stream = _FakeTTY()
        tick = progress.ticker("census", total=90, stream=stream)
        tick.step(45)
        tick.done()
        assert stream.getvalue().endswith("\r"), (
            "the cursor is left at column 0 with the line blanked, so the "
            "phase's own summary starts on a clean row")
        assert stream.getvalue().rstrip("\r").endswith(" ")

    def test_redraws_are_throttled(self, monkeypatch):
        """A tight loop must not become a terminal write per iteration -
        that is a measurable cost on the phase it is narrating."""
        monkeypatch.delenv("BGA_NO_PROGRESS", raising=False)
        stream = _FakeTTY()
        tick = progress.ticker("pairing processes", stream=stream)
        for i in range(10000):
            tick.step(i)
        assert stream.getvalue().count("\r") < 20, (
            f"{stream.getvalue().count(chr(13))} redraws for 10,000 steps")

    def test_the_line_never_wraps(self, monkeypatch):
        monkeypatch.delenv("BGA_NO_PROGRESS", raising=False)
        stream = _FakeTTY()
        tick = progress.ticker("x" * 200, total=999999, stream=stream)
        tick.step(1)
        assert max(len(part) for part in stream.getvalue().split("\r")) <= 72

    def test_a_terminal_that_goes_away_does_not_take_the_run_with_it(
            self, monkeypatch, tmp_path):
        monkeypatch.delenv("BGA_NO_PROGRESS", raising=False)

        class Broken(_FakeTTY):
            def write(self, _text):
                raise OSError("terminal closed")

        tick = progress.ticker("census", stream=Broken())
        tick.step(1)   # must not raise
        tick.done()

    def test_the_context_manager_clears_on_an_exception(self, monkeypatch):
        monkeypatch.delenv("BGA_NO_PROGRESS", raising=False)
        stream = _FakeTTY()
        with pytest.raises(ValueError):
            with progress.ticker("census", stream=stream) as tick:
                tick.step(3)
                raise ValueError("boom")
        assert stream.getvalue().endswith("\r")


class TestStdoutIsUntouched:
    """The user's own scenario, made a test: `bga analyze --format json |
    jq .` has to work with progress forced on."""

    def _analyze(self, env_extra):
        env = dict(os.environ, **env_extra)
        return subprocess.run(
            [sys.executable, "-c",
             "from bga.cli import main; raise SystemExit(main("
             "['analyze', %r, '--format', 'json']))" % GOLDEN],
            capture_output=True, env=env, cwd=os.getcwd())

    def test_the_json_bytes_are_identical_with_progress_on_and_off(self):
        with_progress = self._analyze({})
        without = self._analyze({"BGA_NO_PROGRESS": "1"})
        assert with_progress.returncode == without.returncode == 0
        assert with_progress.stdout == without.stdout, (
            "stdout differs depending on whether progress was drawn")

    def test_stdout_is_valid_json_the_way_a_pipeline_reads_it(self):
        """`| jq .` in the form this suite can assert: stdout parses on
        its own, with nothing prepended and nothing interleaved."""
        result = self._analyze({})
        payload = json.loads(result.stdout.decode())
        assert payload, "the report is empty"
        assert not result.stdout.startswith(b"\r")
        assert b"\r" not in result.stdout


class TestTheProgressPointsAreWired:
    """Which phases carry a ticker is a decision, and a decision that
    silently regresses to none is the failure this catches."""

    @pytest.mark.parametrize("module,label", [
        ("tools/bst_native_build_tracer.py", "parsing trace"),
        ("tools/bst_native_build_tracer.py", "census"),
        ("tools/bst_native_build_tracer.py", "pairing processes"),
        ("tools/bst_show_to_graph.py", "bst show"),
        ("bga/run_store.py", "measuring the store"),
    ])
    def test_the_long_phase_has_a_ticker(self, module, label):
        # Whitespace-normalised: a ticker whose arguments wrap over two
        # lines is the same wiring, and a guard that cares about the
        # line break is a guard about formatting.
        source = " ".join(open(module, encoding="utf-8").read().split())
        assert f'progress.ticker( "{label}"' in source or \
               f'progress.ticker("{label}"' in source, (
            f"{module} no longer narrates `{label}`")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
