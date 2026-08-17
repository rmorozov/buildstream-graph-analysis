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


_RUSAGE_KEYS = frozenset({"utime", "stime", "cutime", "cstime"})


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
        # UX-45: optional real CPU-time fields, emitted on END lines only
        # by a hook built after that task. Parsed as "zero or more known
        # key=value pairs before cmd=", so a trace captured with the
        # previous hook still parses and simply reports CPU time as
        # unavailable rather than as zero - an unmeasured CPU time and a
        # genuinely-zero one are different claims.
        rusage: Dict[str, float] = {}
        while not remaining.startswith("cmd="):
            next_space = remaining.find(" ")
            if next_space == -1:
                break
            token, candidate = remaining[:next_space], remaining[next_space + 1:]
            key, _, value = token.partition("=")
            if key not in _RUSAGE_KEYS:
                break
            try:
                rusage[key] = float(value)
            except ValueError:
                break
            remaining = candidate

        cmd = remaining[4:] if remaining.startswith("cmd=") else ""
        try:
            record = {
                "event": event,
                "pid": int(fields["pid"]),
                "ppid": int(fields["ppid"]),
                "ts": float(fields["ts"]),
                "element": element,
                "cmd": cmd,
            }
        except (KeyError, ValueError):
            continue
        # Only attach when every field of a pair is present: a partial
        # set would be reported as if complete.
        if {"utime", "stime"} <= rusage.keys():
            record["cpu_us"] = int(round((rusage["utime"] + rusage["stime"]) * 1e6))
        if {"cutime", "cstime"} <= rusage.keys():
            record["children_cpu_us"] = int(
                round((rusage["cutime"] + rusage["cstime"]) * 1e6)
            )
        events.append(record)
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
            record = {
                "pid": ev["pid"],
                "ppid": start_ev["ppid"],
                "element": start_ev["element"],
                "cmd": start_ev["cmd"],
                "start_ts": start_ev["ts"],
                "end_ts": ev["ts"],
                "duration_s": ev["ts"] - start_ev["ts"],
                "open": False,
            }
            # UX-45: real CPU time, from the END event's own getrusage.
            # Absent for a trace captured with a pre-UX-45 hook, and the
            # key is then omitted rather than set to 0.
            if "cpu_us" in ev:
                record["cpu_us"] = ev["cpu_us"]
            if "children_cpu_us" in ev:
                record["children_cpu_us"] = ev["children_cpu_us"]
            records.append(record)
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


# UX-37: findings below this much recoverable wall-clock are omitted
# from the text report (kept in the JSON). A real capture produced 37
# findings ranked down to `uname -r` at 0.001s - true, and noise.
_REDUNDANCY_MIN_SECONDS = 0.05

# UX-37: how much of a command line to show. Truncating at 100 characters
# cut every `cc1plus`/`ld` invocation off before anything distinguishing,
# so two structurally different findings rendered identically.
_CMD_HEAD_CHARS = 90
_CMD_TAIL_CHARS = 60


def _elide_cmd(cmd: str) -> str:
    """Keep the binary and the leading arguments, plus the tail (where
    the actual input file usually is), eliding the middle - rather than
    truncating at a fixed prefix, which for a real compiler invocation is
    all boilerplate."""
    if len(cmd) <= _CMD_HEAD_CHARS + _CMD_TAIL_CHARS + 5:
        return cmd
    return f"{cmd[:_CMD_HEAD_CHARS]} ... {cmd[-_CMD_TAIL_CHARS:]}"


# UX-37: an element's own native build-driver invocation. Identical
# across every element of a project by construction, and doing entirely
# different work in each.
_BUILD_DRIVER_BINARIES = frozenset({"make", "gmake", "ninja"})


def _is_element_build_driver(cmd: str) -> bool:
    """True if this command *is* an element's own build/install driver -
    including through the wrappers real cmake projects use
    (`cmake -E env VERBOSE=1 /usr/bin/make ...`,
    `env DESTDIR=... cmake --build ... --target install`), which is why
    this looks at every token rather than only the leading binary.

    `cmake -B... -H...` (configure) deliberately does *not* match: that
    genuinely repeats the same work in every element, and is exactly the
    class of finding UX-23 was built for.
    """
    if "--build" in cmd:
        return True
    for token in cmd.split():
        if os.path.basename(token) in _BUILD_DRIVER_BINARIES:
            return True
    return False


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
        if _is_element_build_driver(r["cmd"]):
            # UX-37: every element runs `make -f Makefile -jN` and
            # `cmake --build ...`, so those signatures are identical
            # across elements by construction while doing entirely
            # different work - each compiles that element's own sources.
            # They are not redundancy, and once findings are ranked by
            # recoverable wall-clock (below) they would otherwise take
            # every top slot, since their duration is the element's whole
            # compile phase. The element's *configure* step and the
            # compiler-probe invocations are deliberately kept: those
            # really do repeat the same work per element, and are what
            # UX-23 was built to find.
            continue
        by_signature[normalize_cmd_signature(r["cmd"])].append(r)

    findings = []
    for signature, occurrences in by_signature.items():
        elements = sorted({r["element"] for r in occurrences})
        if len(elements) < 2:
            continue
        # UX-37: `total_duration_s` sums process time across elements
        # BuildStream dispatched *concurrently*, so it is not time the
        # build would get back. Eliminating all but one occurrence still
        # leaves the one that has to run somewhere, and the elements ran
        # side by side - so the wall-clock-relevant figure is what the
        # single worst-affected element paid, not the sum. Both are
        # reported, each labelled for what it is; the sum stays because
        # it is the honest "total machine time spent on this" number.
        per_element_duration: Dict[str, float] = defaultdict(float)
        for r in occurrences:
            per_element_duration[r["element"]] += r["duration_s"]
        worst_element = max(per_element_duration, key=lambda e: per_element_duration[e])
        findings.append({
            "signature": signature,
            "elements": elements,
            "occurrence_count": len(occurrences),
            "total_duration_s": sum(r["duration_s"] for r in occurrences),
            # UX-37: an upper bound on recoverable wall-clock, not a
            # promise - sharing this work would still cost whatever the
            # shared version costs, and these elements overlapped.
            "max_element_duration_s": per_element_duration[worst_element],
            "worst_element": worst_element,
            "example_cmd": occurrences[0]["cmd"],
        })
    # Ranked by the wall-clock-relevant figure, not by the sum: a
    # 6x-repeated 50ms probe across six concurrent elements is not a
    # bigger finding than a 2x-repeated 5s codegen step.
    return sorted(findings, key=lambda f: -f["max_element_duration_s"])


# UX-32: which traced binaries are doing the real work, and which are
# orchestration that spends its life waiting on children. A concurrency
# number over *all* processes is not interpretable - `core.bst` in a real
# capture showed 99.65s of total process lifetime inside a 14.91s span
# (an apparent 6.68 average concurrency) while its actual compiler
# concurrency never exceeded 1, because `make`/`sh`/`cmake` wrappers were
# alive the whole time and doing nothing.
#
# Deliberately a small, explicit list of real compiler/assembler/linker/
# archiver binaries rather than a "not a wrapper" rule: an unrecognized
# binary is reported as unclassified (see `unclassified_binaries`), never
# silently bucketed either way.
# UX-32: below this fraction of the `-jN` an element actually asked for,
# the report calls it out. Set well below 1.0 deliberately - a build with
# genuinely too few translation units to fill its job slots is common and
# not a defect (UX-09 measured exactly that), so this flags the
# unambiguous case: an element that asked for real parallelism and got
# essentially none.
_UNDERPARALLEL_RATIO = 0.5

WORK_BINARIES = frozenset({
    "cc1", "cc1plus", "cc1obj", "cc1objplus",  # gcc's real compiler
    "clang", "clang++", "clang-cpp",
    "as", "ld", "ld.bfd", "ld.gold", "ld.lld", "collect2", "lto1",
    "ar", "ranlib", "strip", "objcopy",
    "rustc", "go", "javac",
})
ORCHESTRATION_BINARIES = frozenset({
    "sh", "bash", "dash", "env", "make", "gmake", "ninja", "cmake",
    "meson", "python", "python3", "uname", "sed", "grep", "cat", "sort",
    "gcc", "g++", "cc", "c++", "clang-wrapper",  # compiler *drivers* - they exec cc1/as/ld
})

# UX-32: the real `-jN` an element's own native build system was asked
# for. It is in the trace verbatim (`/usr/bin/make -f Makefile -j1`), so
# achieved-vs-requested needs no new capture.
_REQUESTED_JOBS_RE = re.compile(r"(?:^|\s)-j\s*(\d+)(?:\s|$)")


def classify_binary(name: str) -> str:
    """"work" | "orchestration" | "unclassified" - see WORK_BINARIES."""
    if name in WORK_BINARIES:
        return "work"
    if name in ORCHESTRATION_BINARIES:
        return "orchestration"
    return "unclassified"


def _concurrency_profile(intervals: List[Tuple[float, float]]) -> dict:
    """Peak and time-weighted mean concurrency over a set of
    [start, end] process intervals, plus their span and total lifetime."""
    if not intervals:
        return {"peak": 0, "mean": 0.0, "span_s": 0.0, "total_lifetime_s": 0.0}
    points = []
    for start, end in intervals:
        points.append((start, 1))
        points.append((end, -1))
    points.sort(key=lambda p: (p[0], p[1]))
    current = peak = 0
    area = 0.0
    last_ts = points[0][0]
    for ts, delta in points:
        area += current * (ts - last_ts)
        last_ts = ts
        current += delta
        peak = max(peak, current)
    span = max(e for _, e in intervals) - min(s for s, _ in intervals)
    return {
        "peak": peak,
        "mean": (area / span) if span > 0 else 0.0,
        "span_s": span,
        "total_lifetime_s": sum(e - s for s, e in intervals),
    }


def compute_per_element_parallelism(records: List[dict]) -> List[dict]:
    """UX-32: for each BuildStream element, how much parallelism its own
    native build system actually achieved - the question Plane 2 exists
    to answer, and the one its report did not have a number for.

    Every input is already captured (`UX-11`'s timestamps, `UX-23`'s
    element tags, and the element's own `-jN` sitting verbatim in a
    recorded `cmd`); this only computes over them.

    Only matched records (real start *and* end observed) participate, for
    the same reason `compute_max_concurrency` excludes open ones.
    """
    by_element: Dict[str, List[dict]] = defaultdict(list)
    for r in records:
        if r["open"] or r["end_ts"] is None:
            continue
        by_element[r["element"]].append(r)

    profiles = []
    for element, element_records in by_element.items():
        work_intervals = []
        unclassified: Dict[str, int] = {}
        requested_jobs = None
        for r in element_records:
            name = _binary_name(r["cmd"])
            kind = classify_binary(name)
            if kind == "work":
                work_intervals.append((r["start_ts"], r["end_ts"]))
            elif kind == "unclassified":
                unclassified[name] = unclassified.get(name, 0) + 1
            if name in ("make", "gmake", "ninja"):
                match = _REQUESTED_JOBS_RE.search(r["cmd"])
                if match:
                    # Highest wins: an element can run several `make`
                    # invocations (configure probes, install), and the
                    # real build one is the one that asked for the most.
                    value = int(match.group(1))
                    requested_jobs = value if requested_jobs is None else max(requested_jobs, value)
        profile = _concurrency_profile(work_intervals)
        profiles.append({
            "element": element,
            "work_process_count": len(work_intervals),
            "peak_work_concurrency": profile["peak"],
            "mean_work_concurrency": profile["mean"],
            "work_span_s": profile["span_s"],
            "work_process_lifetime_s": profile["total_lifetime_s"],
            "requested_jobs": requested_jobs,
            # Deliberately None rather than a guess when either half is
            # unknown. Note this is NOT on its own the finding: an
            # element pinned to `-j1` achieves 100% (or more, since a
            # gcc driver pipelines cc1plus into as) of what it asked for
            # while being exactly the problem. See `findings` below.
            "achieved_vs_requested": (
                profile["peak"] / requested_jobs
                if requested_jobs else None
            ),
            "unclassified_binaries": dict(sorted(unclassified.items(), key=lambda kv: -kv[1])),
        })
    # Two distinct real findings, decided across the whole trace rather
    # than per element in isolation:
    #
    #  - `pinned_to_one_job`: this element asked for `-j1` while other
    #    elements in the same build asked for more. That is the
    #    `notparallel: True` case (UX-31), and it is invisible to any
    #    achieved-vs-requested ratio, because an element pinned to one
    #    job gets exactly what it asked for.
    #  - `underachieved_requested_jobs`: this element asked for real
    #    parallelism and got essentially none - a serializing Makefile, a
    #    dependency chain inside the element, or contention.
    peak_requested = max(
        (p["requested_jobs"] for p in profiles if p["requested_jobs"] is not None),
        default=None,
    )
    for profile in profiles:
        requested = profile["requested_jobs"]
        findings = []
        if requested == 1 and peak_requested is not None and peak_requested > 1:
            findings.append("pinned_to_one_job")
        elif (
            requested is not None and requested > 1
            and profile["peak_work_concurrency"] < requested * _UNDERPARALLEL_RATIO
        ):
            findings.append("underachieved_requested_jobs")
        profile["findings"] = findings
    profiles.sort(key=lambda p: -p["work_span_s"])
    return profiles


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


def compute_cpu_time(records: List[dict]) -> dict:
    """Real CPU time per element, from each process's own `getrusage`
    at exit (UX-45).

    Before this, `bga` had no CPU-time measurement anywhere - which is
    why I9 reconciliation is disabled on every real run and why three
    separate report caveats have to say "this is occupancy, not CPU".
    This is the measurement; wiring it into Plane 1's utilisation
    buckets is deliberately *not* done here (Plane 2 traces one element
    under a wrapped build, Plane 1 covers the whole run, and I9 needs
    both for the same run).

    Coverage is reported, never assumed. A process killed by a signal,
    or one whose image was replaced by `exec`, runs no destructor and
    contributes no CPU time - so a per-element total is a sum over the
    processes we could see, and saying how many that was is the
    difference between a measurement and a guess.

    `children_cpu_us` is summed separately rather than added in: a
    parent's `RUSAGE_CHILDREN` already includes CPU that its reaped
    children also reported for themselves, so adding both would
    double-count. Self time is the additive quantity; children time is
    published for the wrappers (`make`, `sh`) whose own self time is
    near zero and whose subtree cost is the interesting figure.
    """
    per_element: Dict[str, dict] = {}
    for record in records:
        entry = per_element.setdefault(
            record["element"],
            {"cpu_us": 0, "children_cpu_us": 0, "measured": 0, "unmeasured": 0,
             "wall_span_s": None},
        )
        if "cpu_us" in record:
            entry["cpu_us"] += record["cpu_us"]
            entry["children_cpu_us"] += record.get("children_cpu_us", 0)
            entry["measured"] += 1
        else:
            entry["unmeasured"] += 1

    for element, entry in per_element.items():
        spans = [
            r for r in records
            if r["element"] == element and r["end_ts"] is not None
        ]
        if spans:
            entry["wall_span_s"] = max(r["end_ts"] for r in spans) - min(
                r["start_ts"] for r in spans
            )
        total = entry["measured"] + entry["unmeasured"]
        entry["coverage"] = entry["measured"] / total if total else 0.0
        # The question the micro-optimization half of the walkthrough
        # could not answer: was this element's build CPU-bound, or was
        # it waiting? Only meaningful where something was measured.
        if entry["wall_span_s"] and entry["measured"]:
            entry["cpu_per_wall_second"] = (entry["cpu_us"] / 1e6) / entry["wall_span_s"]
        else:
            entry["cpu_per_wall_second"] = None

    measured_total = sum(e["measured"] for e in per_element.values())
    unmeasured_total = sum(e["unmeasured"] for e in per_element.values())
    return {
        "available": measured_total > 0,
        "measured_processes": measured_total,
        "unmeasured_processes": unmeasured_total,
        "total_cpu_us": sum(e["cpu_us"] for e in per_element.values()),
        "per_element": dict(
            sorted(per_element.items(), key=lambda kv: -kv[1]["cpu_us"])
        ),
        "note": (
            "Real CPU time (getrusage utime+stime) for processes that exited "
            "normally. Processes killed by a signal or replaced by exec run no "
            "destructor and are counted as unmeasured, never as zero. This is "
            "Plane 2 only - it is not wired into Plane 1's utilisation buckets, "
            "which remain slot occupancy (UX-36)."
        ) if measured_total else (
            "No CPU time in this trace - captured with a hook built before UX-45, "
            "or every process exited abnormally. Reported as unavailable rather "
            "than as zero."
        ),
    }


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
        # UX-45: real, kernel-measured CPU time per element.
        "cpu_time": compute_cpu_time(records),
        # UX-32: per-element achieved parallelism - the question this
        # plane exists to answer. See compute_per_element_parallelism.
        "per_element_parallelism": compute_per_element_parallelism(records),
        "wall_span_s": (wall_end - wall_start) if wall_start is not None and wall_end is not None else None,
        "redundant_operations": detect_redundant_operations(records),
        "processes": records,
        "static_binary_disclaimer": STATIC_BINARY_DISCLAIMER,
    }


# UX-38: the keys `summarize` always emits. Used to recognize a
# previously-saved JSON *report* being handed to `report`, which
# otherwise parses as zero trace lines and prints a confident, wrong
# "Processes traced: 0" with exit 0.
_REPORT_MARKER_KEYS = frozenset({"process_count", "matched_count", "by_binary", "processes"})


class EmptyTraceError(TraceError):
    """A trace log that yielded no parseable events at all.

    Distinct from a genuinely empty trace: an empty *log* (nothing ran,
    or the hook never loaded) is a legitimate zero-process result, but a
    file whose every line failed to parse is a wrong-input error, and the
    two used to render identically.
    """


def load_saved_report(path: str) -> Optional[dict]:
    """UX-38: return a previously-saved JSON report if `path` is one,
    else None. `run` writes its report to a JSON file, so that file - not
    the raw log, which `run` discards unless --raw-log is passed - is the
    artifact most sessions actually keep, and re-rendering it was
    impossible.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return None
    if isinstance(data, dict) and _REPORT_MARKER_KEYS.issubset(data.keys()):
        return data
    return None


def load_and_summarize(raw_log_path: str) -> dict:
    with open(raw_log_path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()
    events = parse_trace_log(text)
    if not events and text.strip():
        # UX-38: non-empty file, nothing parseable in it. Almost always
        # the wrong file (this tool's own JSON report is the usual
        # culprit); never something to report as "0 processes traced".
        raise EmptyTraceError(
            f"{raw_log_path}: no trace events could be parsed from this file. "
            "`report` expects a raw trace log (as written by `run --raw-log`). "
            "If this is a JSON report written by `run`, it is now rendered "
            "directly - this error means the file is neither."
        )
    records = pair_events(events)
    return summarize(records)


def _format_cpu_time(cpu_time: dict) -> List[str]:
    """Render UX-45's per-element CPU block, or say plainly that no CPU
    time was captured. Never renders a zero as if it were a measurement."""
    if not cpu_time:
        return []
    if not cpu_time.get("available"):
        return [f"CPU time: unavailable - {cpu_time.get('note', '')}"]

    measured = cpu_time["measured_processes"]
    unmeasured = cpu_time["unmeasured_processes"]
    lines = [
        f"Real CPU time (getrusage): {cpu_time['total_cpu_us'] / 1e6:.2f}s across "
        f"{measured} of {measured + unmeasured} traced processes"
        + (f" ({unmeasured} exited abnormally and are unmeasured)" if unmeasured else ""),
    ]
    for element, entry in cpu_time["per_element"].items():
        if not entry["measured"]:
            lines.append(f"  {element:30s} unmeasured ({entry['unmeasured']} processes)")
            continue
        detail = f"  {element:30s} {entry['cpu_us'] / 1e6:7.2f}s CPU"
        if entry["wall_span_s"]:
            detail += f" over {entry['wall_span_s']:6.2f}s wall"
        if entry["cpu_per_wall_second"] is not None:
            # The micro-optimization question: is this element CPU-bound
            # or waiting? Above ~1.0 means it really used more than one
            # core; well below means it spent its time blocked.
            detail += f" = {entry['cpu_per_wall_second']:5.2f} cores busy"
        if entry["coverage"] < 1.0:
            detail += f"  [{entry['coverage'] * 100:.0f}% of processes measured]"
        lines.append(detail)
    lines.append(f"  ({cpu_time['note']})")
    return lines


def _format_text(report: dict) -> str:
    lines = [
        f"Processes traced: {report['process_count']} "
        f"({report['matched_count']} matched, {report['open_count']} no observed exit)",
        # UX-32: this counts every traced process, including `make`/`sh`
        # wrappers that spend their lives waiting on children, so it
        # routinely exceeds the host's real core count and must not be
        # read as host load. The per-element block below is the
        # interpretable number.
        f"Max observed concurrency (all traced processes, incl. idle wrappers): "
        f"{report['max_concurrency']} (matched processes only - see open_records_note)",
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
    lines.extend(_format_cpu_time(report.get("cpu_time") or {}))
    # UX-32: per-element achieved parallelism.
    per_element = report.get("per_element_parallelism") or []
    if per_element:
        lines.append("")
        lines.append(
            "Per-element native parallelism (real compiler/assembler/linker processes only):"
        )
        lines.append(
            f"  {'element':<24} {'peak':>4} {'req':>4} {'achieved':>9} "
            f"{'span':>8} {'work':>4}"
        )
        for profile in per_element:
            requested = profile["requested_jobs"]
            achieved = profile["achieved_vs_requested"]
            requested_text = str(requested) if requested is not None else "?"
            achieved_text = f"{achieved * 100:6.0f}%" if achieved is not None else "     ?"
            findings = profile.get("findings") or []
            if "pinned_to_one_job" in findings:
                flag = "  <- pinned to -j1 while the rest of this build ran higher"
            elif "underachieved_requested_jobs" in findings:
                flag = "  <- asked for real parallelism and did not get it"
            else:
                flag = ""
            lines.append(
                f"  {profile['element']:<24} {profile['peak_work_concurrency']:>4} "
                f"{requested_text:>4} {achieved_text:>9} "
                f"{profile['work_span_s']:>7.2f}s {profile['work_process_count']:>4}{flag}"
            )
        unclassified = {}
        for profile in per_element:
            for name, count in profile["unclassified_binaries"].items():
                unclassified[name] = unclassified.get(name, 0) + count
        if unclassified:
            # No silent bucketing: a binary this tool doesn't recognize is
            # neither counted as work nor quietly dropped.
            lines.append(
                "  (unclassified binaries, counted as neither work nor orchestration: "
                + ", ".join(f"{n} x{c}" for n, c in sorted(unclassified.items(), key=lambda kv: -kv[1])[:6])
                + ")"
            )
    redundant = report.get("redundant_operations") or []
    if redundant:
        lines.append("")
        # UX-37: rank and filter on the wall-clock-relevant figure. A
        # finding worth a millisecond is noise however it is measured,
        # and the previous unfiltered list ran 37 entries deep down to
        # `uname -r` at 0.001s.
        shown = [
            f for f in redundant
            if f.get("max_element_duration_s", f["total_duration_s"]) >= _REDUNDANCY_MIN_SECONDS
        ]
        omitted = len(redundant) - len(shown)
        lines.append(
            f"Redundant cross-element operations ({len(redundant)} found, "
            f"{len(shown)} above {_REDUNDANCY_MIN_SECONDS:.2f}s):"
        )
        for finding in shown:
            worst = finding.get("worst_element")
            worst_s = finding.get("max_element_duration_s")
            wall_text = (
                f"up to {worst_s:.3f}s recoverable wall-clock (worst element: {worst})"
                if worst_s is not None else "wall-clock impact unknown"
            )
            lines.append(
                f"  {finding['occurrence_count']}x across {len(finding['elements'])} elements "
                f"({', '.join(finding['elements'])}) - {wall_text}; "
                f"{finding['total_duration_s']:.3f}s total machine time"
            )
            lines.append(f"    {_elide_cmd(finding['example_cmd'])}")
        if omitted:
            # No silent truncation (UX-26's own pattern).
            lines.append(
                f"  ({omitted} further finding(s) below {_REDUNDANCY_MIN_SECONDS:.2f}s "
                f"recoverable wall-clock, omitted - see --json for all of them)"
            )
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

    report_parser = subparsers.add_parser(
        "report",
        help="Summarize a previously captured raw trace log, or re-render a JSON report written by `run`",
    )
    report_parser.add_argument(
        "path",
        help="A raw trace log (as written by `run --raw-log`) or a JSON report (as written by `run`) - "
             "the kind is detected, not declared (UX-38)",
    )
    report_parser.add_argument("--json", action="store_true", help="Emit JSON instead of a human-readable summary")

    args = parser.parse_args()

    if args.command == "run":
        cmd = args.cmd
        if cmd and cmd[0] == "--":
            cmd = cmd[1:]
        if not cmd:
            parser.error("no command given (pass it after --, e.g. -- bst build core.bst)")
        # UX-38: `cmd` is argparse.REMAINDER, so any option written after
        # the positionals is silently swallowed into the wrapped command
        # and surfaces as a bare FileNotFoundError from subprocess.run
        # ("No such file or directory: '--wrapped-log'"). Say what
        # actually happened.
        if cmd[0].startswith("-"):
            parser.error(
                f"'{cmd[0]}' was taken as the start of the wrapped command, not as an option - "
                "options must come before the positional arguments, e.g. "
                "`run --wrapped-log PATH PROJECT_DIR OUTPUT -- bst build target.bst`"
            )

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
    # UX-38: `run` writes a JSON report and discards the raw log unless
    # --raw-log is passed, so the report is the artifact most sessions
    # keep - and handing it to `report` used to print "Processes traced: 0"
    # with exit 0. Detect and re-render it instead.
    saved = load_saved_report(args.path)
    if saved is not None:
        print(json.dumps(saved, indent=2) if args.json else _format_text(saved))
        return 0
    try:
        report = load_and_summarize(args.path)
    except (FileNotFoundError, TraceError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2) if args.json else _format_text(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
