"""UX-175: the grace window is only worth something if somebody reads.

UX-163 raised the SIGINT grace to 300s so a big build's graceful stop
could finish and its closing Pipeline Summary would survive. Round 18
showed the grace could not deliver that: the read loop had already
exited, so nothing read the child's stdout again and the summary went
nowhere - and a full pipe buffer blocked the stopping build into the
escalation the grace existed to avoid.

The fixtures here are the review's own reproduction: a child that traps
SIGINT and prints a marker, and a child that ignores it and floods.
"""
import os
import re
import subprocess
import sys
import textwrap
import time

import pytest

from tools import bst_run_wrapped
from tools.bst_native_build_tracer import format_post_build_interrupt


MARKER = "Pipeline Summary: 3 of 9 elements built"


def _fake_bst(tmp_path, body, name="bst"):
    """A stand-in for `bst`, named so `run_wrapped` accepts it."""
    path = tmp_path / name
    path.write_text("#!/usr/bin/env python3\n" + textwrap.dedent(body))
    path.chmod(0o755)
    return path


def _spawn(script, extra_args=()):
    return subprocess.Popen(
        [sys.executable, str(script), *extra_args],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        start_new_session=True,
    )


class TestTheStoppingBuildIsStillRead:
    def test_the_closing_summary_reaches_the_log(self, tmp_path):
        """The defect, as a guard.

        A child that traps SIGINT, prints its summary and exits well
        inside the grace. Before UX-175 the marker was never read: the
        log ended at the "Stopping the build" line no matter how quickly
        the child complied.
        """
        script = _fake_bst(tmp_path, f'''
            import signal, sys, time
            def stop(_signum, _frame):
                print({MARKER!r}, flush=True)
                sys.exit(0)
            signal.signal(signal.SIGINT, stop)
            print("Build started", flush=True)
            time.sleep(60)
        ''')
        proc = _spawn(script)
        # Let the child install its handler and say something first.
        assert proc.stdout.readline().strip() == b"Build started"

        said = []
        # Timed around the shutdown alone, the way the two clauses below
        # this one do it. It used to be an absolute deadline started
        # before the `readline()` above and set to the same 10s as the
        # grace, so the budget was `interpreter startup + shutdown <=
        # 10s` while the contract being tested is `shutdown <= 10s`.
        # Those cannot both hold, and on a loaded CI runner the pair
        # missed by 32 ms - a green shutdown reported as a red test.
        started = time.monotonic()
        stopped = bst_run_wrapped.shutdown_build_group(
            proc, emit=said.append, grace=10)
        elapsed = time.monotonic() - started

        # Well inside the grace, not merely within it: `stopped is True`
        # already means "before the deadline", so a bound *at* the grace
        # would assert nothing. The claim `UX-175` is about is that
        # draining **is** the wait, so a child that complies is noticed
        # when it complies - the old read loop burned the whole window.
        assert elapsed < 5, (
            f"the shutdown took {elapsed:.1f}s for a child that complied "
            f"at once; draining is supposed to be the wait")

        assert stopped is True, "the child complied; it must not read as killed"
        assert MARKER in "\n".join(said), (
            f"the closing summary never reached the log: {said!r}"
        )
        # And the escalation never fired.
        assert not any("SIGTERM" in line for line in said), said

    def test_a_flooding_child_is_escalated_and_its_output_kept(self, tmp_path):
        """The secondary effect: a full pipe must not become the grace.

        The child ignores SIGINT and writes far past the pipe's ~64KB
        buffer. Draining means it never blocks in `write()`, so the
        deadline is the deadline - and what it managed to say up to
        then is in the log rather than lost with it.
        """
        script = _fake_bst(tmp_path, '''
            import signal, sys, time
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            print("Build started", flush=True)
            for i in range(20000):
                print("flooding the pipe with line %06d of noise" % i, flush=True)
            time.sleep(60)
        ''')
        proc = _spawn(script)
        assert proc.stdout.readline().strip() == b"Build started"

        said = []
        started = time.monotonic()
        stopped = bst_run_wrapped.shutdown_build_group(
            proc, emit=said.append, grace=2)
        elapsed = time.monotonic() - started

        assert stopped is False, "a child that ignores SIGINT was not escalated"
        assert elapsed < 40, f"escalation took {elapsed:.1f}s past a 2s grace"
        assert any("SIGTERM" in line for line in said), said
        flooded = [line for line in said if "flooding the pipe" in line]
        assert len(flooded) > 500, (
            f"only {len(flooded)} of the child's lines were captured - the "
            f"drain is not keeping up, or is not running"
        )
        assert proc.poll() is not None, "the child outlived the escalation"

    def test_a_child_that_writes_half_a_line_cannot_hold_the_deadline(self, tmp_path):
        """Why this reads raw rather than calling `readline()`.

        A partial line with no newline behind it would block a
        line-oriented reader indefinitely, and the escalation exists
        precisely for a child that will not go.
        """
        script = _fake_bst(tmp_path, '''
            import signal, sys, time
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            print("Build started", flush=True)
            # After the shutdown has started, so the partial line arrives
            # through the drain's own reads rather than out of whatever
            # Python had buffered before it.
            time.sleep(0.4)
            sys.stdout.write("a line that never ends")
            sys.stdout.flush()
            time.sleep(60)
        ''')
        proc = _spawn(script)
        # Sync on the first complete line, so SIGINT cannot arrive before
        # the child has installed its handler.
        assert proc.stdout.readline().strip() == b"Build started"
        said = []
        started = time.monotonic()
        stopped = bst_run_wrapped.shutdown_build_group(
            proc, emit=said.append, grace=2)
        elapsed = time.monotonic() - started

        assert stopped is False
        assert elapsed < 40, f"the partial line held the shutdown for {elapsed:.1f}s"
        assert any("a line that never ends" in line for line in said), (
            f"the unterminated line was dropped instead of kept: {said!r}"
        )


class TestTheCallerSaysWhyTheSummaryIsMissing:
    def test_an_escalated_build_is_named_as_such_in_the_log(self, tmp_path):
        """UX-163's own wording for this reached the tests and nothing else."""
        script = _fake_bst(tmp_path, '''
            import signal, time
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            print("Build started", flush=True)
            time.sleep(120)
        ''', name="stubborn.py")
        log = tmp_path / "build.log"
        os.environ["BGA_INTERRUPT_GRACE_SECONDS"] = "1"
        try:
            with open(log, "w", encoding="utf-8") as handle:
                # `run_wrapped` insists on a bst-shaped command; the fake
                # is invoked through the interpreter under that name.
                bst = tmp_path / "bst"
                bst.write_text("#!/bin/sh\nexec %s %s\n" % (sys.executable, script))
                bst.chmod(0o755)
                with pytest.raises(KeyboardInterrupt):
                    _run_and_interrupt(str(tmp_path), [str(bst)], handle)
        finally:
            os.environ.pop("BGA_INTERRUPT_GRACE_SECONDS", None)
        text = log.read_text()
        assert "escalated before it could print its closing summary" in text, text
        assert "queue_summary" in text


def _run_and_interrupt(project_dir, cmd, handle):
    """Start the build, then raise KeyboardInterrupt out of the read loop."""
    real_emit_lines = []

    class _Interrupting:
        """Raises once the child has said something, from inside the loop."""
        # The wrapper's own preamble - what it writes before the child
        # has produced a line. Keyed on content rather than on a count:
        # counting broke the moment `UX-185` added a second preamble
        # line, and it broke *silently*, by interrupting before the read
        # loop instead of inside it.
        _PREAMBLE = ("Executing command:", "bga-clocks")

        def __init__(self, stream):
            self._stream = stream
            self._fired = False

        def write(self, text):
            real_emit_lines.append(text)
            handle.write(text)
            # Once, from inside the read loop - after that this is just a
            # file, because the shutdown path writes through it too.
            from_child = not any(marker in text for marker in self._PREAMBLE)
            if from_child and not self._fired:
                self._fired = True
                raise KeyboardInterrupt
            return len(text)

        def flush(self):
            handle.flush()

    return bst_run_wrapped.run_wrapped(project_dir, cmd, _Interrupting(handle))


class TestTheRecoveredRunRemembers:
    def test_extract_accepts_the_flag_the_hint_prints(self, tmp_path):
        """Not a `--help` grep: the flag is exercised.

        A rejected option exits 2 from argparse before anything runs; a
        recognised one gets as far as reading the log, which is where
        this fixture fails. The two are distinguishable, so this is a
        real check rather than a spelling check (`UX-176`'s complaint
        about guards weaker than their prose).
        """
        repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        completed = subprocess.run(
            [sys.executable, "-m", "tools.bst_extract_run", "--interrupted",
             "--format", "wrapped", str(tmp_path),
             str(tmp_path / "absent.log"), str(tmp_path / "run")],
            capture_output=True, text=True, cwd=repo,
        )
        assert "unrecognized arguments" not in completed.stderr, completed.stderr
        assert completed.returncode != 2, (
            f"`--interrupted` was rejected by the parser:\n{completed.stderr}"
        )
        assert re.search(r"--interrupted\b(?![-\w])", completed.stderr or "") is None

    def test_the_mid_build_hint_carries_it(self, tmp_path):
        log = tmp_path / "build.log"
        log.write_text("[wrapper] INFO: Executing command: bst build a.bst\n")
        text = format_post_build_interrupt(
            None, str(log), str(tmp_path / "run"), str(tmp_path),
            build_interrupted=True)
        assert "bga extract --format wrapped --interrupted" in text
        assert "The build did not finish either" in text
        assert "the build itself completed" not in text.lower()

    def test_the_post_build_hint_does_not(self, tmp_path):
        """An interrupt after a *complete* build recovers a complete run."""
        log = tmp_path / "build.log"
        log.write_text("[wrapper] INFO: Executing command: bst build a.bst\n")
        text = format_post_build_interrupt(
            None, str(log), str(tmp_path / "run"), str(tmp_path))
        assert "--interrupted" not in text
        assert "The build itself completed" in text


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
