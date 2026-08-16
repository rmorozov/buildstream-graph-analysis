#!/usr/bin/env python3
"""UX-11: real per-process visibility *inside* a single BuildStream
element's "Running commands" span - `bga`'s own element-level log never
records more than one START/SUCCESS pair per element, so a `make -j8`'s
own internal parallelism (or lack of it) is otherwise invisible from
outside the sandbox. See docs/scenarios/UX-11-native-build-system-
profiler-tool.md for the full design history: five brainstormed
options, an external contribution's `LD_PRELOAD` + `bwrap` PATH-shadow
proxy design, a risk-reduction spike that resolved the cache-key risk
favorably and confirmed the static-binary coverage gap as real, and a
Deep Experiment that proved the interception mechanism end-to-end
against a real `cmake`+`make`+`gcc` build (119 real per-process traces,
including real evidence of `-j4` concurrency) - refuting a second
external review's unnecessary "nested proxy" elaboration in the
process (no `buildbox-run-bubblewrap` binary exists to shadow in real
BuildStream 2.7.0; the naive single-layer shadow already works).

This is deliberately a **separate, standalone tool** from `bga`'s own
`analyze` pipeline (same rationale as tools/bst_checkout_cost.py's own
Background: this data has no shared horizon with a BuildStream element
trace - it's a different timeline, one level down inside a single
element's sandbox).

Mechanism (validated for real, not theoretical - see UX-11's Deep
Experiment Findings):
- A `bwrap` shim (tools/native_trace/bwrap_shim.py) placed ahead of the
  real `/usr/bin/bwrap` in `$PATH` re-parses BuildStream's own generated
  bwrap argv and injects one `--bind` (a host-writable trace directory)
  plus `--setenv LD_PRELOAD <hook.so>`, positioned *after* BuildStream's
  own root-filesystem bind so it survives being overlaid.
- The injected shared library (compiled from the checked-in
  tools/native_trace/hook.c) records a real wall-clock START line at
  process load and an END line at process exit, for every dynamically-
  linked process the sandbox execs - including compiler-driver internals
  like `cc1plus`/`as`/`ld`/`collect2`, not just the outer `cmake`/`make`
  wrappers.
- Every timestamp is `CLOCK_MONOTONIC` - the same shared kernel clock
  for every process on the system, `bwrap --unshare-pid` sandbox or not
  (bwrap does not unshare `CLONE_NEWTIME` by default) - so no extra
  cross-process time correlation is needed.

Known, deliberately un-papered-over limitation (UX-11's Risk 2, real and
confirmed, not hypothetical): `LD_PRELOAD` only affects dynamically-
linked executables. A statically-linked toolchain component (musl-based
builds, some Rust/Go tooling, `busybox`) produces no trace entry and no
error - there is no reliable way for this tool to detect its own
absence from outside, so `run`'s report always carries a fixed
disclaimer rather than a false claim of complete coverage - see
`STATIC_BINARY_DISCLAIMER` below.

Usage:
    python3 -m tools.bst_native_build_tracer run PROJECT_DIR trace.json -- bst build core.bst
    python3 -m tools.bst_native_build_tracer report trace.json --raw-log trace.log
"""
import argparse
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from tools.bst_run_wrapped import run_wrapped
from tools.native_trace.bwrap_shim import __file__ as _bwrap_shim_source

STATIC_BINARY_DISCLAIMER = (
    "LD_PRELOAD only affects dynamically-linked executables. Any "
    "statically-linked process invoked inside the sandbox (e.g. a "
    "musl-based toolchain, busybox, some Rust/Go tooling) ran but "
    "produced no trace entry, silently - this tool cannot detect its "
    "own absence. Treat the process list below as a lower bound, not an "
    "exhaustive trace, unless the toolchain being profiled is known to "
    "be entirely dynamically-linked (the common case for a real C/C++ "
    "gcc/clang toolchain - see docs/scenarios/UX-11-native-build-system-"
    "profiler-tool.md's Deep Experiment Findings)."
)

_HOOK_C = os.path.join(os.path.dirname(__file__), "native_trace", "hook.c")


class TraceError(RuntimeError):
    pass


def compile_hook(build_dir: str) -> str:
    """Compile the checked-in LD_PRELOAD hook fresh into build_dir - not
    cached, to avoid the exact stale-compiled-artifact bug this design
    already hit once for real during its own prototype (a hook.so whose
    trace-log path went stale after a mid-experiment path change; see
    UX-11's Deep Experiment Findings)."""
    hook_so = os.path.join(build_dir, "hook.so")
    cc = shutil.which("cc") or shutil.which("gcc")
    if cc is None:
        raise TraceError("no C compiler (cc/gcc) found on PATH - required to build the LD_PRELOAD hook")
    result = subprocess.run(
        [cc, "-shared", "-fPIC", "-O2", "-o", hook_so, _HOOK_C],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise TraceError(f"failed to compile {_HOOK_C}:\n{result.stderr}")
    return hook_so


def install_bwrap_shim(shim_dir: str) -> str:
    """Copy the checked-in shim script into shim_dir as a file literally
    named `bwrap`, executable - PATH lookup only cares about the
    filename, not where it lives."""
    real_bwrap = shutil.which("bwrap")
    if real_bwrap is None:
        raise TraceError("no real bwrap found on PATH - required for the shim to fall back to")
    shim_path = os.path.join(shim_dir, "bwrap")
    shutil.copyfile(_bwrap_shim_source, shim_path)
    st = os.stat(shim_path)
    os.chmod(shim_path, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return real_bwrap


def run_traced_build(project_dir: str, cmd: List[str], raw_log_path: str, wrapped_log_path: Optional[str] = None) -> int:
    """Run cmd (a real `bst` invocation) with the bwrap shim + LD_PRELOAD
    hook active, writing raw START/END lines to raw_log_path. Returns
    cmd's own real exit code - a trace is captured best-effort and must
    never change whether the wrapped build itself succeeds or fails.

    `wrapped_log_path` (UX-24): when given, also captures a real
    Plane-1-compatible wrapped-format log of this *same* `bst`
    invocation (`tools/bst_run_wrapped.run_wrapped`, reused directly -
    it gained an `env` param specifically for this), so one single real
    build produces both a Plane 1 log (`tools/bst_log_to_chrome_trace.py`-
    ready) and a Plane 2 native trace, correlatable via
    `tools/native_trace_to_chrome_trace.py`'s combined mode. `None` (the
    default) reproduces this function's own prior plain-`subprocess.run`
    behavior exactly, unchanged.
    """
    open(raw_log_path, "w").close()  # truncate/create up front - the hook only ever appends

    with tempfile.TemporaryDirectory(prefix="bst-native-trace-") as tmp:
        shim_dir = os.path.join(tmp, "shim")
        bind_dir = os.path.join(tmp, "bind")
        os.makedirs(shim_dir)
        os.makedirs(bind_dir)

        compile_hook(bind_dir)  # writes bind_dir/hook.so directly - no extra copy step
        real_bwrap = install_bwrap_shim(shim_dir)

        env = dict(os.environ)
        env["PATH"] = shim_dir + os.pathsep + env.get("PATH", "")
        env["BST_TRACE_REAL_BWRAP"] = real_bwrap
        env["BST_TRACE_BIND_SRC"] = bind_dir
        env["BST_TRACE_BIND_DST"] = "/tmp/.bst-native-trace"
        env["BST_TRACE_PRELOAD_SO"] = "/tmp/.bst-native-trace/hook.so"
        env["BST_TRACE_LOG_DST"] = "/tmp/.bst-native-trace/trace.log"

        if wrapped_log_path is not None:
            with open(wrapped_log_path, "w", encoding="utf-8") as out_f:
                returncode = run_wrapped(project_dir, cmd, out_f, env=env)
        else:
            returncode = subprocess.run(cmd, cwd=project_dir, env=env).returncode

        captured_log = os.path.join(bind_dir, "trace.log")
        if os.path.exists(captured_log):
            shutil.copyfile(captured_log, raw_log_path)
        return returncode


def parse_trace_log(text: str) -> List[dict]:
    """Parse raw `START pid=.. ppid=.. ts=.. element=.. cmd=..` / `END
    ...` lines from hook.c into structured events. `element=` (UX-23) is
    optional for backward compatibility with a raw log captured before
    element-tagging existed, or one hook.c was preloaded into without
    `BST_TRACE_ELEMENT` set (UX-11's own original single-element mode) -
    missing/absent defaults to `"unknown"`, never a hard parse failure.
    Malformed lines (truncated by a killed process mid-write, or
    unrelated stderr noise that ended up in the same file) are skipped,
    not fatal - a partial trace is still useful and this tool must never
    crash on a real, imperfect log."""
    events = []
    for line in text.splitlines():
        line = line.rstrip("\n")
        if not line or not (line.startswith("START ") or line.startswith("END ")):
            continue
        event, rest = line.split(" ", 1)
        fields: Dict[str, str] = {}
        remaining = rest
        for key in ("pid", "ppid", "ts"):
            marker = f"{key}="
            idx = remaining.find(marker)
            if idx != 0:
                fields = {}
                break
            remaining = remaining[len(marker):]
            next_space = remaining.find(" ")
            if next_space == -1:
                fields = {}
                break
            fields[key] = remaining[:next_space]
            remaining = remaining[next_space + 1:]
        if not fields:
            continue
        element = "unknown"
        if remaining.startswith("element="):
            remaining = remaining[len("element="):]
            next_space = remaining.find(" ")
            if next_space == -1:
                continue  # element= present but no cmd= after it - malformed, skip
            element = remaining[:next_space]
            remaining = remaining[next_space + 1:]
        cmd = remaining[4:] if remaining.startswith("cmd=") else ""
        try:
            events.append({
                "event": event,
                "pid": int(fields["pid"]),
                "ppid": int(fields["ppid"]),
                "ts": float(fields["ts"]),
                "element": element,
                "cmd": cmd,
            })
        except (KeyError, ValueError):
            continue
    return events


def pair_events(events: List[dict]) -> List[dict]:
    """Pair each START with its own process's END, FIFO per `(element,
    pid)` - correct as long as one pid's own lifetime doesn't overlap a
    later reused instance of the same pid *within the same element's own
    sandbox* (true for bwrap's own `--unshare-pid` namespace: a pid is
    only reused after its holder has actually exited).

    Keying on pid alone (UX-11's original single-element design) is
    unsound once a trace spans multiple elements (UX-23): each element
    gets its own independent `--unshare-pid` namespace, so the *same*
    small pid number (e.g. 2, 24, 27 - the low numbers a fresh PID
    namespace always starts from) recurs across every element's own
    sandbox and refers to a *different* real process each time. Pairing
    by pid alone would silently cross-pair a START in one element with
    an END from a different one whenever their real lifetimes overlap -
    a real correctness bug that stayed latent in UX-11's own
    single-element-focused testing and only became visible once
    multi-element traces needed to be trusted per-element (this task).

    A START with no matching END (killed by a signal, or still running
    when the trace was captured) is reported "open" with
    duration_us=None rather than a fabricated duration."""
    open_by_key: Dict[Tuple[str, int], List[dict]] = {}
    records: List[dict] = []
    for ev in sorted(events, key=lambda e: e["ts"]):
        key = (ev["element"], ev["pid"])
        if ev["event"] == "START":
            open_by_key.setdefault(key, []).append(ev)
        elif ev["event"] == "END":
            pending = open_by_key.get(key)
            if not pending:
                continue
            start_ev = pending.pop(0)
            records.append({
                "pid": ev["pid"],
                "ppid": start_ev["ppid"],
                "element": start_ev["element"],
                "cmd": start_ev["cmd"],
                "start_ts": start_ev["ts"],
                "end_ts": ev["ts"],
                "duration_s": ev["ts"] - start_ev["ts"],
                "open": False,
            })
    for pending in open_by_key.values():
        for start_ev in pending:
            records.append({
                "pid": start_ev["pid"],
                "ppid": start_ev["ppid"],
                "element": start_ev["element"],
                "cmd": start_ev["cmd"],
                "start_ts": start_ev["ts"],
                "end_ts": None,
                "duration_s": None,
                "open": True,
            })
    return sorted(records, key=lambda r: r["start_ts"])


def _binary_name(cmd: str) -> str:
    first = cmd.split(" ", 1)[0] if cmd else ""
    return os.path.basename(first) if first else "(unknown)"


# UX-23: real, confirmed sources of spurious per-element/per-invocation
# uniqueness in an otherwise-identical logical operation - each pattern
# below was found by directly inspecting a real trace, not guessed.
_NORMALIZE_PATTERNS = [
    # A per-element absolute build path - element-specific by
    # construction (every element gets its own sandbox/builddir), and
    # the single largest source of spurious "uniqueness" for what is
    # otherwise the exact same real operation.
    (re.compile(r"/buildstream/[^/\s]+/[^/\s]+\.bst/"), "<element-root>/"),
    # gcc/binutils own temp files (assembly/object intermediates) - a
    # fresh random name every single invocation, even for the exact
    # same logical compile.
    (re.compile(r"/tmp/cc[A-Za-z0-9]+\.\w+"), "/tmp/<tmp>"),
    # CMake's own randomly-suffixed try-compile scratch directory
    # (CMakeFiles/cmTC_xxxxx.dir/...) - a fresh random suffix every
    # single try-compile probe, even for the exact same logical check.
    (re.compile(r"cmTC_[0-9a-fA-F]+"), "cmTC_<id>"),
    # CMake's own scratch try-compile top-level directory name
    # (TryCompile-XXXXXX) - same rationale.
    (re.compile(r"TryCompile-[A-Za-z0-9]+"), "TryCompile-<id>"),
]


def normalize_cmd_signature(cmd: str) -> str:
    """UX-23: a best-effort, heuristic normalization of a real traced
    command line into a stable "logical operation" signature, so the
    *same* real operation run independently inside different elements'
    own sandboxes is recognized as the same signature rather than
    treated as unrelated because of incidental path/tmpfile differences.

    Deliberately not a general/robust solution (UX-23's own doc names
    this explicit Out-of-Scope boundary: real flag-order-insensitivity
    and fully general path/tmpfile stripping "needs its own design
    pass") - covers only the specific, real patterns this design has
    directly confirmed cause spurious mismatches (see docs/scenarios/
    UX-23's own real `CMakeCXXCompilerABI.cpp` evidence: 6 independent
    per-element runs of the exact same compiler-capability probe). A
    command line with some other, unhandled source of incidental
    uniqueness simply won't be recognized as redundant - a false
    negative, not a false positive; this detector is intentionally
    conservative rather than over-eager.
    """
    normalized = cmd
    for pattern, replacement in _NORMALIZE_PATTERNS:
        normalized = pattern.sub(replacement, normalized)
    return normalized


def detect_redundant_operations(records: List[dict]) -> List[dict]:
    """UX-23: group matched (start+end known), element-attributed traced
    processes by their normalized command signature - any signature
    occurring under 2+ *distinct* real elements is a real, concrete
    redundant-operation candidate. Processes tagged `element="unknown"`
    (a raw log captured without element-tagging, or hook.c loaded
    without `BST_TRACE_ELEMENT` set) are excluded entirely - never claim
    cross-element redundancy for a process this tool couldn't actually
    attribute to a real element. Sorted by real total duration spent on
    each redundant signature, most costly first, so a user can
    immediately see which finding is actually worth investigating (a
    100ms probe repeated 6 times is very different from a 30s codegen
    step repeated 6 times - same principle as this tool's own
    static-binary disclaimer: report real numbers, let the user judge).
    """
    by_signature: Dict[str, List[dict]] = defaultdict(list)
    for r in records:
        if r["open"] or r["element"] == "unknown":
            continue
        by_signature[normalize_cmd_signature(r["cmd"])].append(r)

    findings = []
    for signature, occurrences in by_signature.items():
        elements = sorted({r["element"] for r in occurrences})
        if len(elements) < 2:
            continue
        findings.append({
            "signature": signature,
            "elements": elements,
            "occurrence_count": len(occurrences),
            "total_duration_s": sum(r["duration_s"] for r in occurrences),
            "example_cmd": occurrences[0]["cmd"],
        })
    return sorted(findings, key=lambda f: -f["total_duration_s"])


def compute_max_concurrency(records: List[dict]) -> int:
    """A real sweep over process intervals - matched (start+end known)
    records only. Open (unmatched) records are deliberately excluded,
    not extended to the trace's last timestamp: a real run against
    examples/05-cmake-cpp-toolchain showed every open record is a `sh -c
    '<single command>'` wrapper whose *own* process exits via `_exit()`
    once its forked child (the real command) completes - `_exit()`
    bypasses libc's normal exit path, so `__attribute__((destructor))`
    never fires for it (see hook.c's own header for the confirmed
    mechanism). Such a wrapper is typically done in milliseconds, not
    "still running" - extending it to the trace's last timestamp (an
    earlier version of this function did exactly that) produced a
    max_concurrency of 24 for a real `-j4` build, an obviously inflated,
    physically implausible number. Excluding them instead makes this
    figure a real, honest lower bound rather than a false one."""
    matched = [r for r in records if not r["open"]]
    if not matched:
        return 0
    points = []
    for r in matched:
        points.append((r["start_ts"], 1))
        points.append((r["end_ts"], -1))
    points.sort(key=lambda p: (p[0], p[1]))  # ends (-1) before starts (+1) at equal ts
    current = 0
    peak = 0
    for _ts, delta in points:
        current += delta
        peak = max(peak, current)
    return peak


def summarize(records: List[dict]) -> dict:
    matched = [r for r in records if not r["open"]]
    open_records = [r for r in records if r["open"]]
    by_binary: Dict[str, int] = {}
    for r in records:
        name = _binary_name(r["cmd"])
        by_binary[name] = by_binary.get(name, 0) + 1
    by_element: Dict[str, int] = {}
    for r in records:
        by_element[r["element"]] = by_element.get(r["element"], 0) + 1
    wall_start = min((r["start_ts"] for r in records), default=None)
    wall_end = max((r["end_ts"] if r["end_ts"] is not None else r["start_ts"] for r in records), default=None)
    return {
        "process_count": len(records),
        "matched_count": len(matched),
        "open_count": len(open_records),
        "open_records_note": (
            "Processes with no observed exit are excluded from max_concurrency, not "
            "assumed to run indefinitely. Real cause, confirmed against this tool's own "
            "prototype run: a `sh -c '<command>'` wrapper that forks a child for the "
            "real command and then exits via `_exit()` once it completes - `_exit()` "
            "bypasses the normal exit path, so this hook's destructor never fires for "
            "the wrapper itself, even though it exited quickly and normally."
        ) if open_records else None,
        "by_binary": dict(sorted(by_binary.items(), key=lambda kv: -kv[1])),
        "by_element": dict(sorted(by_element.items(), key=lambda kv: -kv[1])),
        "max_concurrency": compute_max_concurrency(records),
        "wall_span_s": (wall_end - wall_start) if wall_start is not None and wall_end is not None else None,
        "redundant_operations": detect_redundant_operations(records),
        "processes": records,
        "static_binary_disclaimer": STATIC_BINARY_DISCLAIMER,
    }


def load_and_summarize(raw_log_path: str) -> dict:
    with open(raw_log_path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()
    events = parse_trace_log(text)
    records = pair_events(events)
    return summarize(records)


def _format_text(report: dict) -> str:
    lines = [
        f"Processes traced: {report['process_count']} "
        f"({report['matched_count']} matched, {report['open_count']} no observed exit)",
        f"Max observed concurrency: {report['max_concurrency']} (matched processes only - see open_records_note)",
    ]
    if report.get("open_records_note"):
        lines.append(f"  ({report['open_records_note']})")
    if report["wall_span_s"] is not None:
        lines.append(f"Wall span: {report['wall_span_s']:.3f}s")
    lines.append("By binary:")
    for name, count in report["by_binary"].items():
        lines.append(f"  {name:20s} {count}")
    by_element = report.get("by_element", {})
    if len(by_element) > 1 or (len(by_element) == 1 and "unknown" not in by_element):
        lines.append("By element:")
        for name, count in by_element.items():
            lines.append(f"  {name:30s} {count}")
    redundant = report.get("redundant_operations") or []
    if redundant:
        lines.append("")
        lines.append(f"Redundant cross-element operations ({len(redundant)} found):")
        for finding in redundant:
            lines.append(
                f"  {finding['occurrence_count']}x across {len(finding['elements'])} elements "
                f"({finding['elements']}), {finding['total_duration_s']:.3f}s total:"
            )
            lines.append(f"    {finding['example_cmd'][:100]}")
    lines.append("")
    lines.append(f"NOTE: {report['static_binary_disclaimer']}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run a real bst command under the tracer and report on it")
    run_parser.add_argument("project_dir", help="cwd for the wrapped command (the BuildStream project directory)")
    run_parser.add_argument("output", help="Path to write the JSON report to")
    run_parser.add_argument("--raw-log", help="Also keep the raw trace log at this path (default: discarded after parsing)")
    run_parser.add_argument(
        "--wrapped-log",
        help="UX-24: also capture a real Plane-1-compatible wrapped-format log of this same bst "
             "invocation (tools/bst_log_to_chrome_trace.py-ready) - lets one real build feed both "
             "planes for tools/native_trace_to_chrome_trace.py's combined mode.",
    )
    run_parser.add_argument("--json", action="store_true", help="Print the report as JSON to stdout too")
    run_parser.add_argument("cmd", nargs=argparse.REMAINDER, help="The bst command to run, e.g. -- bst build core.bst")

    report_parser = subparsers.add_parser("report", help="Summarize a previously captured raw trace log")
    report_parser.add_argument("raw_log", help="Path to a raw trace log (as written by `run --raw-log`)")
    report_parser.add_argument("--json", action="store_true", help="Emit JSON instead of a human-readable summary")

    args = parser.parse_args()

    if args.command == "run":
        cmd = args.cmd
        if cmd and cmd[0] == "--":
            cmd = cmd[1:]
        if not cmd:
            parser.error("no command given (pass it after --, e.g. -- bst build core.bst)")

        raw_log_path = args.raw_log or os.path.join(tempfile.mkdtemp(prefix="bst-native-trace-log-"), "trace.log")
        try:
            returncode = run_traced_build(args.project_dir, cmd, raw_log_path, wrapped_log_path=args.wrapped_log)
        except TraceError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

        report = load_and_summarize(raw_log_path)
        report["wrapped_command_exit_code"] = returncode
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print(_format_text(report))
            print(f"\nWrapped command exit code: {returncode}")
        return returncode

    # report
    try:
        report = load_and_summarize(args.raw_log)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2) if args.json else _format_text(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
