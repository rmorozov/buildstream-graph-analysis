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
import subprocess
import sys
from datetime import datetime, timezone


def _now_str():
    # Matches tests/fixtures/synthetic_multi_subproject/wrapper_log.txt's
    # reference format exactly: "%Y-%m-%d %H:%M:%S,%f" truncated to
    # milliseconds, which is what WrapperTraceConverter.parse_timestamp
    # (strptime "%Y-%m-%d %H:%M:%S,%f") expects.
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]


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
        text=True,
        bufsize=1,
        env=env,
    )
    for line in proc.stdout:
        emit(line.rstrip("\n"))
    proc.wait()

    emit(f"Return code: {proc.returncode}")
    return proc.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("project_dir", help="Path to the BuildStream project directory (cwd for the command)")
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
