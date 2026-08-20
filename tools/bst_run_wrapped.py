#!/usr/bin/env python3
"""Run a real `bst` command and capture its output as a "wrapped"-format
log (`[wrapper][UTC timestamp] LEVEL: <line>` per line, timestamped live
as each line arrives) - the same shape tools/bst_log_to_chrome_trace.py's
wrapped-mode parser expects (see tests/fixtures/synthetic_multi_subproject/
wrapper_log.txt for the reference format).

Why this exists: BuildStream's own `[HH:MM:SS]` per-line elapsed prefix
(consumed by --format raw) is a PER-ACTIVITY duration measured from each
task's own start (confirmed against BuildStream 2.7.0's
_messenger.py:timed_activity - `elapsed = datetime.datetime.now() -
timedata.start_time`, scoped to that one `timed_activity` call), not a
session-wide wall clock. `--format raw`'s parser (bst_log_to_chrome_trace.py
_process_raw_line) treats it as a global offset (`raw_start_time_us +
elapsed_s`), which corrupts cross-task ordering for any real multi-task
build captured to a file and parsed afterward - see
docs/backlog/scenarios/UX-0006-raw-log-timestamp-corruption.md for the full
writeup. `--format wrapped` doesn't have this problem (it anchors on an
externally-supplied absolute timestamp, never on BuildStream's own
elapsed field) - this tool supplies that external timestamp live, one
per line, as the command actually runs, so its extraction is real wall
clock rather than a saved log file's mtime-derived guess.

Usage:
    python3 -m tools.bst_run_wrapped PROJECT_DIR OUTPUT_LOG -- bst --builders 2 build all.bst

The command must start with "bst " (matches bst_log_to_chrome_trace.py's
own is_bst detection) for the resulting log to parse as a real BuildStream
invocation under --format wrapped.
"""
import argparse
import os
import select
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Optional


def _now_str():
    # Matches tests/fixtures/synthetic_multi_subproject/wrapper_log.txt's
    # reference format exactly: "%Y-%m-%d %H:%M:%S,%f" truncated to
    # milliseconds, which is what WrapperTraceConverter.parse_timestamp
    # (strptime "%Y-%m-%d %H:%M:%S,%f") expects.
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]


def signal_build_group(proc, sig) -> None:
    """Send `sig` to the whole process group the build runs in.

    `UX-157`. The build is spawned with `start_new_session=True`, so it
    is not in this process's group and a terminal's Ctrl-C no longer
    reaches it. That is deliberate: `bga` decides when the build is
    interrupted, so it can salvage the trace afterwards rather than
    being torn down alongside it. The cost is that forwarding becomes
    our job, which is what this is.

    Silent on a group that is already gone - a race with the build's own
    exit is the normal case here, not an error.
    """
    try:
        os.killpg(os.getpgid(proc.pid), sig)
    except (ProcessLookupError, PermissionError, OSError):
        pass


# UX-163 item 3: how long to let `bst` stop by itself before escalating.
# 120s was a guess, and round 17 found the cost of getting it wrong: on a
# big element bst's graceful stop can exceed it, SIGTERM then kills it
# before it prints its closing Pipeline Summary, the run loses
# `queue_summary`, and the "N of M scheduled" clause - the most useful
# number - silently disappears from exactly the biggest builds.
SIGINT_GRACE_ENV = "BGA_INTERRUPT_GRACE_SECONDS"
DEFAULT_SIGINT_GRACE = 300.0


def sigint_grace_seconds() -> float:
    """The SIGINT grace window, overridable for a project that needs more."""
    try:
        value = float(os.environ.get(SIGINT_GRACE_ENV, DEFAULT_SIGINT_GRACE))
    except (TypeError, ValueError):
        return DEFAULT_SIGINT_GRACE
    return value if value > 0 else DEFAULT_SIGINT_GRACE


def drain_until_exit(proc, deadline: float, say) -> bool:
    """Read everything the stopping build still writes, until it exits.

    `UX-175`, and the whole reason the grace window is worth anything.
    `UX-163` raised the SIGINT grace to 300s so `bst`'s closing Pipeline
    Summary - the source of every `queue_summary` count - could survive
    an interrupt. It could not: the read loop had already exited, so
    nothing read the child's stdout again and the summary `bst` wrote
    *during* its graceful stop went nowhere. Worse, once the pipe's
    ~64KB buffer filled, the stopping `bst` blocked in `write()` and
    burned the entire grace before the escalation killed it - the grace
    causing the slow path it existed to prevent.

    Raw reads on a non-blocking fd rather than `readline()`: a child
    that writes half a line and then hangs must not be able to hold this
    past the deadline, which is the one thing the escalation is for.
    Whatever Python had already buffered ahead of the interrupt is
    picked up first, so no line the build produced before it is lost.

    Returns True when the process exited before the deadline.
    """
    # `getattr`: a process spawned without `stdout=PIPE` has nothing to
    # drain, and neither does a stand-in for one.
    stream = getattr(proc, "stdout", None)
    if stream is None:
        return _wait_until(proc, deadline)
    fd = stream.fileno()
    try:
        os.set_blocking(fd, False)
        # What the buffered reader read ahead of the last line the loop
        # emitted. `read1` on a non-blocking fd returns it without a
        # syscall when it is there, and `None` rather than blocking when
        # it is not. An unbuffered stream has no `read1` and nothing to
        # hand over.
        read1 = getattr(stream, "read1", None)
        pending = (read1(1 << 20) or b"") if read1 is not None else b""
    except (OSError, ValueError):
        return _wait_until(proc, deadline)

    def flush_lines():
        nonlocal pending
        while b"\n" in pending:
            line, _, pending = pending.partition(b"\n")
            say(line.decode("utf-8", "replace").rstrip("\r"))

    flush_lines()
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        try:
            ready, _, _ = select.select([fd], [], [], min(remaining, 0.5))
        except (OSError, ValueError):
            break
        if ready:
            try:
                chunk = os.read(fd, 65536)
            except (BlockingIOError, InterruptedError):
                continue
            except OSError:
                break
            if not chunk:
                break  # EOF: the build closed its output and is on its way out
            pending += chunk
            flush_lines()
            continue
        if proc.poll() is not None:
            break
    if pending:
        say(pending.decode("utf-8", "replace"))
    return _wait_until(proc, deadline)


def _wait_until(proc, deadline: float) -> bool:
    remaining = max(0.0, deadline - time.monotonic())
    try:
        proc.wait(timeout=remaining)
    except subprocess.TimeoutExpired:
        return False
    return True


def shutdown_build_group(proc, emit=None, grace: Optional[float] = None) -> bool:
    """Stop an interrupted build the way a user pressing Ctrl-C expects.

    `UX-157`. SIGINT first, because `bst` handles it properly - it stops
    scheduling, lets running jobs finish or abort, and writes its
    summary, which is what makes the partial Plane 1 log worth having.
    Escalates only if it does not go, and the escalation is to the whole
    group: round 16 observed a `bst` that kept building for hours after
    `bga` died, because nothing had ever addressed anything but the
    direct child.

    Returns True when `bst` stopped on its own, False when it was
    killed. The distinction matters downstream: a killed `bst` never
    printed its closing summary, so the run's `queue_summary` is missing
    rather than absent-by-nature, and a caller that says "N of M
    scheduled" should say why it cannot instead (`UX-163` item 3).
    """
    def say(message):
        if emit is not None:
            emit(message)

    if grace is None:
        grace = sigint_grace_seconds()
    signal_build_group(proc, signal.SIGINT)
    # UX-175: draining *is* the wait. `proc.wait(timeout=grace)` left the
    # pipe unread for the whole window.
    if drain_until_exit(proc, time.monotonic() + grace, say):
        return True
    say(f"the build did not stop within {grace:g}s of SIGINT - sending "
        f"SIGTERM. bst's closing summary may be lost; set "
        f"{SIGINT_GRACE_ENV} higher if this project needs longer.")
    signal_build_group(proc, signal.SIGTERM)
    try:
        proc.wait(timeout=30)
        return False
    except subprocess.TimeoutExpired:
        say("the build did not stop after SIGTERM - sending SIGKILL")
    signal_build_group(proc, signal.SIGKILL)
    try:
        proc.wait(timeout=30)
    except subprocess.TimeoutExpired:
        say("the build's process group survived SIGKILL; giving up on it")
    return False


def run_wrapped(project_dir: str, cmd: list, out_f, env=None) -> int:
    """`env`: UX-24 - when given, replaces the subprocess's own
    environment entirely (matching `subprocess.Popen`'s own semantics),
    instead of always inheriting this process's environment unmodified.
    Needed so `tools/bst_native_build_tracer.py` can capture a real
    wrapped-format Plane 1 log *and* a real Plane 2 native trace from one
    single real `bst build` invocation, at once - the tracer's own PATH-
    shadowing/LD_PRELOAD env vars have to reach the same subprocess this
    function spawns, not a second, separate one. `None` (the default)
    reproduces this function's own prior behavior exactly, unchanged."""
    if not cmd or not (cmd[0] == "bst" or cmd[0].endswith("/bst")):
        raise ValueError(f"command must start with 'bst', got: {cmd!r}")

    def emit(line: str):
        out_f.write(f"[wrapper][{_now_str()}] INFO: {line}\n")
        out_f.flush()
        # Also echo live to this process's own stderr - without this, a
        # real build failure is completely silent to whatever's watching
        # this process (e.g. a CI job log), since every line otherwise
        # only ever reaches the log *file* - confirmed via a real CI
        # failure that showed nothing but a bare "exit code 255", making
        # the actual underlying bst error impossible to diagnose from the
        # CI log alone.
        print(line, file=sys.stderr, flush=True)

    emit(f"Executing command: {' '.join(cmd)}")

    proc = subprocess.Popen(
        cmd,
        cwd=project_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        # UX-175: bytes, not text. The shutdown path has to keep reading
        # this pipe after the read loop has gone, with a deadline it can
        # actually hold, and that means raw reads on the fd - which
        # cannot be mixed with a text wrapper's own decoding buffer.
        # Decoding moves to the one place that emits. Buffering stays
        # default: `readline` still returns as soon as a newline is in
        # the buffer, and unbuffered would read the whole build a byte
        # at a time.
        env=env,
        # UX-157: its own session, hence its own process group. Without
        # it there is nothing to address but the direct child, and round
        # 16 watched a `bst` build on for hours after the `bga` that
        # started it was gone.
        start_new_session=True,
    )
    try:
        for line in proc.stdout:
            emit(line.decode("utf-8", "replace").rstrip("\n").rstrip("\r"))
        proc.wait()
    except BaseException as error:
        # `BaseException`, not `Exception`: `KeyboardInterrupt` is the
        # case this exists for, and it is not an `Exception`. Anything
        # that gets us out of the read loop leaves a build running that
        # nobody is reading from any more, so it is stopped either way.
        emit(f"Stopping the build after {type(error).__name__}")
        # UX-175: the answer is used, not discarded. "Say why the summary
        # is missing instead of just missing it" was UX-163's own wording
        # for this, and it reached the tests and nothing else.
        if not shutdown_build_group(proc, emit=emit):
            emit("bst was escalated before it could print its closing "
                 "summary - this run has no queue_summary, so the "
                 "built/cached counts are unavailable rather than zero.")
        raise

    emit(f"Return code: {proc.returncode}")
    return proc.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("project_dir", help="Path to the BuildStream project directory (cwd for the command).")
    parser.add_argument("output_log", help="Path to write the wrapped-format log to")
    parser.add_argument("cmd", nargs=argparse.REMAINDER, help="The bst command to run, e.g. -- bst --builders 2 build all.bst")
    args = parser.parse_args()

    cmd = args.cmd
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    if not cmd:
        parser.error("no command given (pass it after --, e.g. -- bst build all.bst)")

    with open(args.output_log, "w", encoding="utf-8") as out_f:
        returncode = run_wrapped(args.project_dir, cmd, out_f)

    return returncode


if __name__ == "__main__":
    sys.exit(main())
