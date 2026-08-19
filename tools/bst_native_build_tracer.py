#!/usr/bin/env python3
"""UX-11: real per-process visibility *inside* a single BuildStream
element's "Running commands" span - `bga`'s own element-level log never
records more than one START/SUCCESS pair per element, so a `make -j8`'s
own internal parallelism (or lack of it) is otherwise invisible from
outside the sandbox. See docs/backlog/scenarios/UX-0011-native-build-system-
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
import struct
import subprocess
import sys
import tempfile
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple


from .bst_run_wrapped import run_wrapped
from .native_trace.bwrap_shim import __file__ as _bwrap_shim_source

STATIC_BINARY_DISCLAIMER = (
    "LD_PRELOAD only affects dynamically-linked executables. Any "
    "statically-linked process invoked inside the sandbox (e.g. a "
    "musl-based toolchain, busybox, some Rust/Go tooling) ran but "
    "produced no trace entry, silently - this tool cannot detect its "
    "own absence. Treat the process list below as a lower bound, not an "
    "exhaustive trace, unless the toolchain being profiled is known to "
    "be entirely dynamically-linked (the common case for a real C/C++ "
    "gcc/clang toolchain - see docs/backlog/scenarios/UX-0011-native-build-system-"
    "profiler-tool.md's Deep Experiment Findings)."
)

_HOOK_C = os.path.join(os.path.dirname(__file__), "native_trace", "hook.c")
_SPINE_C = os.path.join(os.path.dirname(__file__), "native_trace", "spine.c")


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
        # -ldl for UX-46's dlsym(RTLD_NEXT, ...) interposition. Harmless
        # on glibc >= 2.34 where libdl is folded into libc, and required
        # on older ones.
        [cc, "-shared", "-fPIC", "-O2", "-o", hook_so, _HOOK_C, "-ldl"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise TraceError(f"failed to compile {_HOOK_C}:\n{result.stderr}")
    return hook_so


def compile_spine(build_dir: str) -> str:
    """UX-106: compile the ptrace spine, statically, fresh into
    `build_dir`.

    Static for the same reason the spine exists: it runs *inside* the
    sandbox, and a sandbox assembled from a project's own elements may
    have no dynamic loader at all - `examples/01`'s is busybox and
    nothing else. A dynamically-linked tracer would fail to start
    exactly where the static blind spot is worst.

    Compiled fresh rather than cached, the same rule `compile_hook`
    follows and for the same reason it learned it.
    """
    spine_bin = os.path.join(build_dir, "spine")
    cc = shutil.which("cc") or shutil.which("gcc")
    if cc is None:
        raise TraceError(
            "no C compiler (cc/gcc) found on PATH - required to build the ptrace spine"
        )
    result = subprocess.run(
        [cc, "-static", "-O2", "-o", spine_bin, _SPINE_C],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise TraceError(f"failed to compile {_SPINE_C}:\n{result.stderr}")
    return spine_bin


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


def run_traced_build(project_dir: str, cmd: List[str], raw_log_path: str, wrapped_log_path: Optional[str] = None, trace_opens: bool = False, argv_log_path: Optional[str] = None, invocation_log_path: Optional[str] = None,
                     trace_spine=False) -> int:
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
        # UX-106: opt-in until `UX-108` measures the overhead. The hook
        # stays either way - it is the only source of opened paths and of
        # child-rusage enrichment, so the spine complements it rather
        # than replacing it.
        # UX-113: `False` / `True` / `"auto"`. Kept as the same parameter
        # rather than a second flag, because they are three values of one
        # question and a capture may only answer it once.
        spine_policy = "auto" if trace_spine == "auto" else bool(trace_spine)
        if spine_policy:
            compile_spine(bind_dir)
        real_bwrap = install_bwrap_shim(shim_dir)

        env = dict(os.environ)
        env["PATH"] = shim_dir + os.pathsep + env.get("PATH", "")
        env["BST_TRACE_REAL_BWRAP"] = real_bwrap
        env["BST_TRACE_BIND_SRC"] = bind_dir
        env["BST_TRACE_BIND_DST"] = "/tmp/.bst-native-trace"
        env["BST_TRACE_PRELOAD_SO"] = "/tmp/.bst-native-trace/hook.so"
        env["BST_TRACE_LOG_DST"] = "/tmp/.bst-native-trace/trace.log"
        if spine_policy:
            # The path *inside* the sandbox, where the bind lands - the
            # shim prepends this to the sandboxed command.
            env["BST_TRACE_SPINE"] = "/tmp/.bst-native-trace/spine"
            env.pop("BST_TRACE_SPINE_POLICY", None)
            env.pop("BST_TRACE_SPINE_CENSUS", None)
            if spine_policy == "auto":
                # UX-113: the census already knows, per element and
                # before the build starts, where the hook is blind.
                # Written on the host side, beside the shim's other
                # state, and read per sandbox by the shim.
                verdicts = census_spine_verdicts(project_dir)
                census_path = os.path.join(shim_dir, "spine-census.json")
                with open(census_path, "w", encoding="utf-8") as handle:
                    json.dump(verdicts, handle, sort_keys=True)
                env["BST_TRACE_SPINE_POLICY"] = "auto"
                env["BST_TRACE_SPINE_CENSUS"] = census_path
        else:
            env.pop("BST_TRACE_SPINE", None)
            env.pop("BST_TRACE_SPINE_POLICY", None)
            env.pop("BST_TRACE_SPINE_CENSUS", None)
        # UX-46: opt-in, and propagated into the sandbox by the shim.
        if trace_opens:
            env["BST_TRACE_OPENS"] = "1"
        else:
            env.pop("BST_TRACE_OPENS", None)
        # UX-58: the shim writes into the same temporary directory it
        # already owns, on the *host* side - it runs outside the sandbox,
        # so no bind path is involved.
        # UX-56: always on when tracing - one line per sandbox, so a
        # 126-element project writes 126 lines, and without it a capture
        # whose element names collapsed cannot be corrected at all.
        captured_invocations = os.path.join(bind_dir, "invocations.jsonl")
        env["BST_TRACE_INVOCATION_LOG"] = captured_invocations
        captured_argv = os.path.join(bind_dir, "bwrap-argv.jsonl")
        if argv_log_path is not None:
            env["BST_TRACE_ARGV_LOG"] = captured_argv
        else:
            env.pop("BST_TRACE_ARGV_LOG", None)

        if wrapped_log_path is not None:
            with open(wrapped_log_path, "w", encoding="utf-8") as out_f:
                returncode = run_wrapped(project_dir, cmd, out_f, env=env)
        else:
            returncode = subprocess.run(cmd, cwd=project_dir, env=env).returncode

        captured_log = os.path.join(bind_dir, "trace.log")
        if os.path.exists(captured_log):
            shutil.copyfile(captured_log, raw_log_path)
        if argv_log_path is not None and os.path.exists(captured_argv):
            shutil.copyfile(captured_argv, argv_log_path)
        if invocation_log_path is not None and os.path.exists(captured_invocations):
            shutil.copyfile(captured_invocations, invocation_log_path)
        return returncode


_RUSAGE_KEYS = frozenset({"utime", "stime", "cutime", "cstime"})
# UX-63: peak RSS from the same struct rusage. Integers in KiB (Linux),
# not the float seconds the keys above carry, hence a separate set.
_RUSAGE_INT_KEYS = frozenset({"maxrss_kb", "cmaxrss_kb"})

# UX-57: `part=` is appended by hooks that flush more than one window
# per process, and absent in logs written before that existed - optional
# so one parser reads both.
_OPENS_HEADER_RE = re.compile(
    r"^OPENS pid=(\d+) element=(\S+)(?: inv=(\S+))? unique=(\d+) dropped=(\d+)"
    r"(?: part=(\d+))?$"
)


def parse_open_records(text: str, open_element_overrides: Optional[Dict[str, str]] = None) -> Dict[str, dict]:
    """Parse UX-46's `OPENS` blocks into `{element: {...}}`.

    Each block is a header line followed by exactly `unique` absolute
    paths, one per line, written by one process at exit. Blocks from
    every process of an element are unioned: the question being answered
    is "did *this element's build* read anything this dependency staged",
    and which of its processes did the reading does not matter.

    `dropped` is carried through rather than discarded. A process that
    hit the hook's fixed path budget recorded a subset of what it read,
    and a subset is exactly the input that would turn a used dependency
    into a false "unused" - so any drop makes this element's verdict
    unsafe and is reported as such rather than quietly rounded away.
    """
    open_element_overrides = open_element_overrides or {}
    per_element: Dict[str, dict] = {}
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        match = _OPENS_HEADER_RE.match(lines[index])
        if match is None:
            index += 1
            continue
        pid, element, invocation, unique, dropped, _part = match.groups()
        # UX-56: when the element name collapsed, the sandbox id is
        # what lets the correlation relabel this block too - without
        # it declared-vs-used stays keyed on a name that is not an
        # element, which is exactly how it came back empty on the
        # real freedesktop-sdk capture.
        if invocation and invocation != 'none':
            element = open_element_overrides.get(invocation, element)
        entry = per_element.setdefault(
            element,
            {"paths": set(), "dropped": 0, "processes": 0, "dropped_by_pid": {}, "windows": 0},
        )
        # UX-57: one process may now write several windows, so counting
        # blocks would overstate the process count. `dropped` is a
        # running total the process re-reports each time, so the last
        # window's value is the total rather than their sum.
        entry["windows"] += 1
        # `dropped` is a running per-process total that the process
        # re-reports in every window it writes, so the largest value seen
        # for a pid is that pid's total; the element's total is their sum
        # across pids. Summing every block instead would multiply one
        # process's drops by how many windows it happened to flush.
        by_pid = entry["dropped_by_pid"]
        by_pid[pid] = max(by_pid.get(pid, 0), int(dropped))
        entry["processes"] = len(by_pid)
        entry["dropped"] = sum(by_pid.values())
        index += 1
        for _ in range(int(unique)):
            if index >= len(lines):
                break  # truncated block (killed mid-write) - keep what we have
            path = lines[index]
            index += 1
            # A following header means the block was short; don't consume it.
            if _OPENS_HEADER_RE.match(path) or path.startswith(("START ", "END ")):
                index -= 1
                break
            if path.startswith("/"):
                entry["paths"].add(path)
    return per_element


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
        # UX-56: optional sandbox id, emitted by a hook built after that
        # task. Absent in every earlier capture, so it is parsed only if
        # present and never fabricated - a trace without it simply cannot
        # be corrected when its element names collapsed.
        invocation = None
        if remaining.startswith("inv="):
            next_space = remaining.find(" ")
            if next_space != -1:
                raw = remaining[len("inv="):next_space]
                invocation = None if raw == "none" else raw
                remaining = remaining[next_space + 1:]
        # UX-45: optional real CPU-time fields, emitted on END lines only
        # by a hook built after that task. Parsed as "zero or more known
        # key=value pairs before cmd=", so a trace captured with the
        # previous hook still parses and simply reports CPU time as
        # unavailable rather than as zero - an unmeasured CPU time and a
        # genuinely-zero one are different claims.
        rusage: Dict[str, float] = {}
        # UX-106: `src=` and `exit=` are written by the ptrace spine and
        # absent from every hook-written record. Parsed here rather than
        # tolerated as unknown, because this loop *stops* at the first
        # key it does not know - so an unhandled field would not be
        # ignored, it would swallow `cmd=` and leave every spine record
        # with an empty command line.
        source = "hook"
        exit_status = None
        while not remaining.startswith("cmd="):
            next_space = remaining.find(" ")
            if next_space == -1:
                break
            token, candidate = remaining[:next_space], remaining[next_space + 1:]
            key, _, value = token.partition("=")
            if key == "src":
                source = value
                remaining = candidate
                continue
            if key == "exit":
                exit_status = value
                remaining = candidate
                continue
            if key not in _RUSAGE_KEYS and key not in _RUSAGE_INT_KEYS:
                break
            try:
                rusage[key] = int(value) if key in _RUSAGE_INT_KEYS else float(value)
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
                "invocation": invocation,
                "cmd": cmd,
                # UX-106: which mechanism saw this process. Defaults to
                # `hook` so every capture taken before the spine existed
                # keeps one honest answer rather than None.
                "src": source,
            }
        except (KeyError, ValueError):
            continue
        # Only attach when every field of a pair is present: a partial
        # set would be reported as if complete.
        if {"utime", "stime"} <= rusage.keys():
            record["cpu_us"] = int(round((rusage["utime"] + rusage["stime"]) * 1e6))
        # UX-63: a *peak*, carried through unchanged. Deliberately not
        # summed anywhere: two processes each peaking at 500 MB at
        # different moments never used 1 GB together, and adding them
        # would manufacture a concurrent total nothing measured.
        if "maxrss_kb" in rusage:
            record["max_rss_kb"] = rusage["maxrss_kb"]
        if "cmaxrss_kb" in rusage:
            record["children_max_rss_kb"] = rusage["cmaxrss_kb"]
        # UX-106: the spine reads this from the kernel's own exit-stop
        # message, so a process killed by a signal is distinguishable
        # from one that returned that number. The hook has no equivalent
        # - its destructor runs before the process has a status, and not
        # at all when one is killed.
        if exit_status is not None:
            record["exit_status"] = exit_status
        if {"cutime", "cstime"} <= rusage.keys():
            record["children_cpu_us"] = int(
                round((rusage["cutime"] + rusage["cstime"]) * 1e6)
            )
        events.append(record)
    return events


def count_fork_only_exits(events: List[dict]) -> int:
    """UX-123: exits recorded for pids that never exec'd.

    `PTRACE_EVENT_EXIT` fires for every tracee, including a
    fork-without-exec child - which is the same program as its parent and
    wears the parent's cmdline, so it is not a process a profiler should
    list. `pair_events` drops those ENDs; this counts them, because a
    record class that is neither reported nor summarised is
    indistinguishable from one that never occurred.
    """
    seen_start = set()
    fork_only = 0
    for ev in sorted(events, key=lambda e: e["ts"]):
        key = (ev.get("invocation") or ev["element"], ev["pid"], ev.get("src", "hook"))
        if ev["event"] == "START":
            seen_start.add(key)
        elif ev["event"] == "END" and key not in seen_start:
            fork_only += 1
    return fork_only


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
    open_by_key: Dict[Tuple[str, int, str], List[dict]] = {}
    records: List[dict] = []
    for ev in sorted(events, key=lambda e: e["ts"]):
        # UX-61: the sandbox id, when the capture has one, is the correct
        # disambiguator - not the element name. Pids are namespaced *per
        # sandbox*, so they collide freely across sandboxes, and keying on
        # the element only separates them while the element name is
        # per-element. Under a build-root override every process shares
        # one name (UX-56), so a START in one sandbox pairs with an END in
        # another: on a real collapsed capture, 822 records over 113
        # distinct pids, "durations" of 23s inside a 30s build, and a
        # max_concurrency of 34 on a 4-core `--builders 4` run. The real
        # freedesktop-sdk capture reported 5,268.
        # UX-107: and the *mechanism*, because with the spine running each
        # process writes a START and an END from each stream. Without
        # `src` in the key the FIFO pops the spine's START for the hook's
        # END and vice versa: on a real dual-stream capture of
        # `examples/07` every "spine" record carried the hook's
        # microsecond rusage and every "hook" record carried the spine's
        # tick-quantized one - pid 9's cc1plus reported utime 0.013204
        # under `src=spine`, a resolution /proc cannot produce. The
        # process count and the coverage classes both survive that
        # crossing intact, which is why it has to be keyed out rather
        # than checked for.
        key = (ev.get("invocation") or ev["element"], ev["pid"], ev.get("src", "hook"))
        if ev["event"] == "START":
            open_by_key.setdefault(key, []).append(ev)
        elif ev["event"] == "END":
            pending = open_by_key.get(key)
            if not pending:
                # UX-123: an exit for a pid that never exec'd - a
                # fork-without-exec child, whose recorded cmdline is its
                # parent's. Dropped here and counted by
                # `count_fork_only_exits` over the same events, so the
                # report can say how many rather than leaving a whole
                # record class neither shown nor mentioned.
                continue
            # UX-123: one pid, one record, even when it exec'd several
            # times.
            #
            # `sh -c "gcc …"` execs in place: N STARTs, one END. Pairing
            # the END with the *first* START billed the pid's whole CPU,
            # peak RSS and exit status to the pre-exec image and left the
            # rest as "no observed exit". Measured on freedesktop-sdk:
            # **7,384 records** misfiled that way, including
            # `sh -c -e python -P -mbuild …` carrying 195,219us that
            # `python` spent.
            #
            # The chain is collapsed instead. `/proc/<pid>/stat` and
            # `getrusage` are both per-*pid* and cumulative across execs,
            # so the figures describe the whole lifetime and belong to
            # the process, not to one of its images; the span runs from
            # the first exec to the exit, and the name is the last image,
            # which is what a profiler means by "the process".
            start_ev = pending[0]
            final_ev = pending[-1]
            exec_chain = len(pending)
            pending.clear()
            record = {
                "pid": ev["pid"],
                "ppid": final_ev["ppid"],
                "element": start_ev["element"],
                # UX-56: the sandbox this process ran in, so a correlation
                # can relabel a whole sandbox at once.
                "invocation": start_ev.get("invocation"),
                "cmd": final_ev["cmd"],
                "start_ts": start_ev["ts"],
                "end_ts": ev["ts"],
                "duration_s": ev["ts"] - start_ev["ts"],
                "open": False,
                # How many images this pid ran. 1 for the ordinary case;
                # published so a reader can see that a collapsed chain is
                # a collapse rather than a lost record.
                "exec_chain": exec_chain,
                # UX-106/UX-107: which mechanism produced this record.
                # Carried through pairing because the merge below joins
                # on it, and every consumer that reports coverage needs
                # to know which stream a process came from.
                "src": start_ev.get("src", "hook"),
            }
            # UX-45: real CPU time, from the END event's own getrusage.
            # Absent for a trace captured with a pre-UX-45 hook, and the
            # key is then omitted rather than set to 0.
            if "cpu_us" in ev:
                record["cpu_us"] = ev["cpu_us"]
            if "children_cpu_us" in ev:
                record["children_cpu_us"] = ev["children_cpu_us"]
            # UX-63: peak RSS, from the same END event's getrusage. Same
            # rule - omitted rather than zeroed when the hook predates it.
            if "max_rss_kb" in ev:
                record["max_rss_kb"] = ev["max_rss_kb"]
            if "children_max_rss_kb" in ev:
                record["children_max_rss_kb"] = ev["children_max_rss_kb"]
            # UX-106: only the spine has this - the hook's destructor
            # runs before the process has a status, and not at all when
            # it is killed.
            if "exit_status" in ev:
                record["exit_status"] = ev["exit_status"]
            records.append(record)
    for pending in open_by_key.values():
        for start_ev in pending:
            records.append({
                "pid": start_ev["pid"],
                "ppid": start_ev["ppid"],
                "element": start_ev["element"],
                "invocation": start_ev.get("invocation"),
                "cmd": start_ev["cmd"],
                "start_ts": start_ev["ts"],
                "end_ts": None,
                "duration_s": None,
                "open": True,
                "src": start_ev.get("src", "hook"),
                "exec_chain": 1,
            })
    return sorted(records, key=lambda r: r["start_ts"])


# UX-107: how far apart the two streams' START stamps may be and still
# describe the same process image.
#
# They cannot be identical by construction: the spine writes at the
# kernel's exec-stop, the hook writes from a constructor that runs after
# the image is loaded, so the hook's stamp is always the later of the
# two by however long the dynamic linker took. Measured on a real
# examples/06 capture, that gap is sub-millisecond; a full second of
# tolerance is three orders of magnitude of slack and still far below
# the interval at which one sandbox reuses a pid.
MERGE_START_TOLERANCE_S = 1.0

COVERAGE_BOTH = "spine+hook"
COVERAGE_SPINE_ONLY = "spine-only"
COVERAGE_HOOK_ONLY = "hook-only"


def merge_record_streams(records: List[dict]) -> List[dict]:
    """UX-107: two record streams, one process list.

    With `UX-106`'s spine running, a *dynamically*-linked process is
    recorded twice - once by the spine (argv, lifecycle, exit status,
    per-process CPU, peak RSS) and once by the hook (the same lifecycle
    plus opened paths and reaped-children rusage) - while a static
    process has only the spine's. Consumed naively that double-counts
    every dynamic process's CPU and its concurrency, which would corrupt
    every Plane 2 analysis in the name of fixing coverage. Measured on
    `examples/06` before this existed: 1635 spine records beside 1485
    hook records, and a report claiming 1644 processes.

    Joined on `(invocation, pid)` and a START within
    `MERGE_START_TOLERANCE_S`. That is exact in practice rather than
    heuristic: both streams read the same `CLOCK_MONOTONIC`, and pids
    are namespaced per sandbox, so the invocation id makes the pair
    unique inside the only scope where a pid means anything.

    **The spine is the base and the hook is enrichment**, not the other
    way round: the spine's record exists for every process, so building
    on it keeps one shape for both coverage classes. Only the fields the
    hook alone has - reaped-children rusage, and the opens attached
    later by path - are taken from it.

    Every entry carries `coverage`. A capture with no spine records at
    all comes back untouched with `hook-only` on every entry, which is
    what makes every pre-spine capture parse exactly as before.
    """
    spine_records = [r for r in records if r.get("src") == "spine"]
    if not spine_records:
        for record in records:
            record.setdefault("coverage", COVERAGE_HOOK_ONLY)
        return records

    hook_by_key: Dict[Tuple[Optional[str], int], List[dict]] = {}
    for record in records:
        if record.get("src") == "spine":
            continue
        hook_by_key.setdefault((record.get("invocation"), record["pid"]), []).append(record)
    for pending in hook_by_key.values():
        pending.sort(key=lambda r: r["start_ts"])

    merged: List[dict] = []
    matched_hooks = set()
    for record in sorted(spine_records, key=lambda r: r["start_ts"]):
        key = (record.get("invocation"), record["pid"])
        # UX-123: the *nearest* candidate within tolerance, not the
        # first. A `--unshare-pid` sandbox recycles small pids quickly -
        # this repository's own tests assert that it does - so a stale
        # unmatched hook record from an earlier holder of the pid could
        # capture a later spine record simply by being first in the list.
        partner = None
        best = None
        for candidate in hook_by_key.get(key) or []:
            if id(candidate) in matched_hooks:
                continue
            distance = abs(candidate["start_ts"] - record["start_ts"])
            if distance <= MERGE_START_TOLERANCE_S and (best is None or distance < best):
                partner, best = candidate, distance
        entry = dict(record)
        if partner is None:
            entry["coverage"] = COVERAGE_SPINE_ONLY
            if "cpu_us" in entry:
                entry["cpu_source"] = "spine"
        else:
            matched_hooks.add(id(partner))
            entry["coverage"] = COVERAGE_BOTH
            # What the hook alone can measure. Never its lifecycle and
            # never a second copy of a quantity the spine already
            # carries, which is the whole defect this function exists to
            # prevent.
            for field in ("children_cpu_us", "children_max_rss_kb"):
                if field in partner:
                    entry[field] = partner[field]
            if "max_rss_kb" in partner:
                entry["hook_max_rss_kb"] = partner["max_rss_kb"]
            # UX-53's free test: the same CPU time measured by two
            # mechanisms - `getrusage` at exit against `/proc/<pid>/stat`
            # read at the exit-stop. Kept as evidence rather than
            # averaged; a disagreement is a fact about the capture.
            #
            # And the *resolution* differs, which decides which of the
            # two is used. `/proc/<pid>/stat` reports whole `USER_HZ`
            # ticks - 10ms - and truncates, so every process shorter than
            # a tick reads as zero: on a real `examples/06` capture the
            # 531 processes under 20ms totalled 0.83s by the spine
            # against 3.82s by the hook, while the 34 over 200ms agreed
            # to 0.7%. The hook's microsecond figure is therefore the one
            # used wherever it exists; the spine's stands alone only for
            # a static process, where it is the only measurement there
            # is and its truncation is stated rather than hidden.
            if "cpu_us" in partner:
                if "cpu_us" in entry:
                    entry["spine_cpu_us"] = entry["cpu_us"]
                entry["hook_cpu_us"] = partner["cpu_us"]
                entry["cpu_us"] = partner["cpu_us"]
                entry["cpu_source"] = "hook"
            elif "cpu_us" in entry:
                entry["cpu_source"] = "spine"
        merged.append(entry)

    for record in records:
        if record.get("src") == "spine" or id(record) in matched_hooks:
            continue
        entry = dict(record)
        entry["coverage"] = COVERAGE_HOOK_ONLY
        merged.append(entry)
    return sorted(merged, key=lambda r: r["start_ts"])


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

# UX-73: the shells BuildStream's own command block runs in. Used only to
# recognize the inner shell of `sh -c -e (set -ex; sh -c -e '<script>')`
# as part of that block - never to classify work.
_SHELL_BINARIES = frozenset({"sh", "bash", "dash", "ash"})


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
    directly confirmed cause spurious mismatches (see docs/backlog/scenarios/
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


def _is_element_command_block(record: dict) -> bool:
    """True if this process is the sandbox's own top-level command -
    the element's `configure-commands`/`build-commands` block (`UX-73`).

    BuildStream runs an element's commands as a single `sh -c -e` inside
    the sandbox, and bwrap gives each sandbox its own PID namespace, so
    that shell is pid 2 with pid 1 (bwrap's init) as its parent. Measured
    on a real 127,627-process `freedesktop-sdk` capture: **exactly 25
    records have `ppid == 1`, exactly one per each of the 25 sandboxes**,
    all of them pid 2. It is a structural identification, not a string
    heuristic.

    They must not be counted as redundancy for the same reason `UX-37`
    excluded `make -jN`: two elements using the same BuildStream plugin
    run a byte-identical command block by construction while compiling
    entirely different sources. On the real capture this was 21
    occurrences of `sh -c -e if [ -n "bst_build_dir" ]; then` claiming
    664.6s, and a two-element `cmake -B_builddir` configure claiming
    512.6s.

    Both `pid == 2` and `ppid == 1` are required for the root. Either
    alone is a weaker claim than the measurement supports, and the
    failure mode of requiring both is to *under*-fire - leaving a false
    positive in the list, which is visible - rather than to silently drop
    a real finding. A capture taken without a PID namespace matches
    neither, so this simply never fires; it cannot exclude anything it
    was not meant to.

    **The block is two processes, not one.** BuildStream's command is
    `sh -c -e (set -ex; sh -c -e '<script>')`, so the script runs in an
    inner shell that is a direct child of the root. Measured: all 21
    occurrences of the `sh -c -e if [ -n "bst_build_dir" ]; then`
    signature - the largest remaining false positive after the root-only
    rule, claiming 664.6s across 5 elements - carry `ppid == 2`, and the
    root of each of their invocations is the same script one nesting
    level out. So a direct child of the root that is *itself a shell* is
    part of the command block; a direct child that is a compiler or a
    build driver is the element's real work and stays.
    """
    if record.get("ppid") == 1 and record.get("pid") == 2:
        return True
    return (
        record.get("ppid") == 2
        and _binary_name(record.get("cmd") or "") in _SHELL_BINARIES
    )


def _is_element_name(name: Optional[str]) -> bool:
    """The same narrow, syntactic test `assess_element_attribution` uses:
    a BuildStream element name ends in `.bst`.

    Shared rather than re-derived because `UX-64`/`UX-66` introduced a
    second non-element bucket name beside `unknown` - the *unresolved*
    bucket, holding processes whose sandbox could not be matched to
    exactly one element. Anything that tests only against `unknown` now
    treats that bucket as an element, which is exactly what `UX-73`
    found `detect_redundant_operations` doing.
    """
    return bool(name) and name.endswith(".bst")


def detect_redundant_operations(records: List[dict]) -> Tuple[List[dict], dict]:
    """UX-23: group matched (start+end known), element-attributed traced
    processes by their normalized command signature - any signature
    occurring under 2+ *distinct* real elements is a real, concrete
    redundant-operation candidate. Sorted by real total duration spent on
    each redundant signature, most costly first, so a user can
    immediately see which finding is actually worth investigating (a
    100ms probe repeated 6 times is very different from a 30s codegen
    step repeated 6 times - same principle as this tool's own
    static-binary disclaimer: report real numbers, let the user judge).

    `UX-73`: "element-attributed" means *resolved to a real element*, not
    merely "not `unknown`". The original guard excluded only `unknown`,
    which was complete until `UX-64`/`UX-66` added an explicitly
    unresolved bucket - and then a signature seen under one real element
    plus that bucket satisfied "2+ distinct elements". Measured on the
    real capture: **79 of 93 findings above the reporting floor involved
    the unresolved bucket, carrying 87% of the claimed recoverable
    wall-clock (3588s of 4129s)**, and the single largest finding in the
    report was `lto-wrapper` claiming "up to 1932.9s recoverable" against
    a bucket of 17,754 unattributed processes.

    Returns `(findings, coverage)`. The coverage half reports what was
    excluded and why, because "how many findings were dropped for being
    unresolved-only" is itself a signal - it rises when attribution gets
    worse, and a silently shorter list reads as a cleaner build.
    """
    by_signature: Dict[str, List[dict]] = defaultdict(list)
    # Signatures seen under a non-element bucket, so a finding that
    # disappears for lack of a *second* resolved element can be counted
    # rather than silently dropped.
    unresolved_signatures: Dict[str, set] = defaultdict(set)
    excluded_command_blocks = 0
    for r in records:
        if r["open"] or r["element"] == "unknown":
            continue
        if _is_element_command_block(r):
            excluded_command_blocks += 1
            continue
        if not _is_element_name(r["element"]):
            unresolved_signatures[normalize_cmd_signature(r["cmd"])].add(r["element"])
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
    excluded_unresolved_only = 0
    for signature, occurrences in by_signature.items():
        elements = sorted({r["element"] for r in occurrences})
        if len(elements) < 2:
            # UX-73: it would have been a finding only by counting an
            # unresolved bucket as a second element. Counted, because a
            # list that simply got shorter reads as a cleaner build.
            if len(elements) + len(unresolved_signatures.get(signature, ())) >= 2:
                excluded_unresolved_only += 1
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
    # A signature seen *only* under unresolved buckets never reached the
    # loop above, so it is counted here.
    excluded_unresolved_only += sum(
        1 for signature, buckets in unresolved_signatures.items()
        if signature not in by_signature and len(buckets) >= 2
    )
    coverage = {
        "excluded_unresolved_only": excluded_unresolved_only,
        "excluded_element_command_blocks": excluded_command_blocks,
        "note": (
            "Each finding's `max_element_duration_s` is an upper bound on what "
            "sharing that one operation could recover, for the single "
            "worst-affected element. They are per-signature maxima over "
            "elements that ran concurrently: they must not be summed, and on a "
            "real capture their sum exceeds the build's own duration. A "
            "signature is a finding only when it ran under 2+ *resolved* "
            "elements (UX-73); processes in the unresolved attribution bucket "
            "and each element's own top-level command block are excluded, and "
            "counted above."
        ),
    }
    # Ranked by the wall-clock-relevant figure, not by the sum: a
    # 6x-repeated 50ms probe across six concurrent elements is not a
    # bigger finding than a 2x-repeated 5s codegen step.
    return (
        sorted(findings, key=lambda f: -f["max_element_duration_s"]),
        coverage,
    )


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


def assess_element_attribution(by_element: Dict[str, int]) -> dict:
    """UX-56: is the per-element split real, or did every process land in
    one bucket that is not an element?

    Plane 2 tags each traced process with an element name taken from
    bwrap's `--dir` option, whose last path segment is the element in
    BuildStream's *default* build-root layout - which is what every
    project in `examples/` uses. A real project may set its own
    `build-root`, and `freedesktop-sdk` does: `/buildstream-build`. On a
    real 127,630-process capture of it, **126,871 processes (99.4%) were
    tagged `buildstream-build`**, one bucket that is not an element, and
    every per-element number in this report was therefore a whole-build
    number wearing an element's name - `peak_work_concurrency` 1019
    against 4 requested jobs, `achieved_vs_requested` 254.75, and 44,145
    seconds of "recoverable" time inside a 2,796-second build.

    The test is deliberately narrow and syntactic: a BuildStream element
    name ends in `.bst`. Nothing else in this report can tell a real
    element name from a directory that happens to be named after one, and
    a heuristic that tried would fail in the direction that matters -
    publishing per-element figures nobody can act on.

    Returns a dict; `reliable` false means every consumer should refuse
    the per-element view rather than render it (this repository's
    established posture since `UX-46`: refuse rather than guess).
    """
    total = sum(by_element.values())
    recognized = {k: v for k, v in by_element.items() if k.endswith(".bst")}
    recognized_processes = sum(recognized.values())
    largest = max(by_element.items(), key=lambda kv: kv[1], default=(None, 0))
    unrecognized = {k: v for k, v in by_element.items() if not k.endswith(".bst")}
    largest_unrecognized = max(
        unrecognized.items(), key=lambda kv: kv[1], default=(None, 0)
    )

    # UX-66: validity and coverage are different properties, and the
    # original rule (`recognized_processes == total`) conflated them.
    #
    # That was right when the measured answer was 0.6% and every
    # per-element figure was fiction. After `UX-64` it is wrong: round 8
    # measured 86.1% of processes correctly named, every resolved name
    # valid against the declared graph, and the residue sitting in an
    # explicitly *unresolved* bucket - and the report still refused,
    # citing `components/bison.bst`, which is an element, as evidence
    # that attribution had failed.
    #
    # So the question a consumer needs answered is "are the names I have
    # real?", not "do I have all of them". Coverage is reported
    # separately, the way `UX-45` reports measured CPU time and `UX-63`
    # measured memory: a partial measurement is published with its
    # coverage, not withheld.
    usable = bool(recognized) and recognized_processes > 0
    share = recognized_processes / total if total else 0.0
    note = None
    if not by_element:
        note = "no process carried an element tag at all"
    elif not usable:
        note = (
            f"none of {total} traced processes carry a name that looks like a "
            f"BuildStream element (ending in '.bst'); the largest bucket is "
            f"{largest[0]!r} with {largest[1]} processes. The element tag "
            "comes from bwrap's --dir, which is the element only under "
            "BuildStream's default build-root layout - a project that "
            "sets its own build-root collapses every element into one "
            "bucket. Per-element figures in this report are not per-"
            "element and must not be read as such (UX-56)."
        )
    elif recognized_processes < total:
        note = (
            f"{recognized_processes} of {total} traced processes ({share:.1%}) "
            f"are attributed to a named element; the remaining "
            f"{total - recognized_processes} are in the unresolved bucket "
            f"{largest_unrecognized[0]!r}, whose sandbox could not be matched "
            "to exactly one element (UX-56/UX-64). Per-element figures below "
            "cover the attributed share only - they are correct for the "
            "elements named, and silent about the rest."
        )
    return {
        # Whether the names present are real element names. False means
        # refuse the per-element view entirely.
        "reliable": usable,
        "tagged_processes": total,
        "recognized_processes": recognized_processes,
        # UX-66: coverage, published rather than folded into `reliable`.
        "attributed_share": share,
        "unattributed_processes": total - recognized_processes,
        "unresolved_bucket": largest_unrecognized[0],
        "recognized_elements": sorted(recognized),
        "largest_bucket": largest[0],
        "largest_bucket_processes": largest[1],
        "note": note,
    }


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


# UX-105: the four bytes that start every ELF file, and the program
# header type that means "this binary asks the dynamic linker to run
# it". A binary with no `PT_INTERP` never invokes `ld.so`, so
# `LD_PRELOAD` never reaches it and the hook cannot record it - which is
# the whole of Plane 2's blind spot, and it is knowable from the file
# before anything runs.
_ELF_MAGIC = b"\x7fELF"
_PT_INTERP = 3
_ET_EXEC = 2


def classify_elf(path: str) -> Optional[str]:
    """`"static"` | `"dynamic"` | `"library"` | None for a non-ELF file.

    Pure stdlib: a 64-byte header, then the program header table, read
    with `struct`. No new dependency for what is a fixed, documented
    layout - and one this repository can afford to get exactly right
    rather than approximately. 32- and 64-bit, either endianness,
    because a cross-built sysroot is exactly the case where this
    question matters.

    **`e_type` decides as much as `PT_INTERP` does**, and finding that
    out was the first thing running it taught: `examples/06`'s staged
    glibc toolchain reported five "static executables" that are
    `ld-linux-x86-64.so.2` and three copies of `liblto_plugin.so`.
    Shared objects have no `PT_INTERP` either - they are loaded, not
    exec'd - so `PT_INTERP` alone calls every library on the system a
    static binary.

    So:

    - `ET_EXEC` without `PT_INTERP` -> **static**: a classic static
      executable, the thing `LD_PRELOAD` cannot reach.
    - anything with `PT_INTERP` -> **dynamic**, `ET_EXEC` or PIE alike.
    - `ET_DYN` without `PT_INTERP` -> **library**, reported separately.

    The last bucket carries the one real ambiguity, stated rather than
    resolved: a *static-PIE* executable is `ET_DYN` with no `PT_INTERP`
    and is indistinguishable from a shared object without parsing the
    dynamic section for `DT_SONAME`/`DT_NEEDED`. Static-PIE is rare and a
    library is not; counting the bucket as libraries under-reports the
    blind spot rather than over-reporting it, which is the safe
    direction for a number whose whole job is to say "the trace may be
    missing something".

    A file that cannot be read, or is truncated mid-header, returns
    None: "not classifiable" and "not static" are different answers and
    only one of them is safe to act on.
    """
    try:
        with open(path, "rb") as handle:
            header = handle.read(64)
            if len(header) < 20 or header[:4] != _ELF_MAGIC:
                return None
            is_64 = header[4] == 2
            endian = "<" if header[5] == 1 else ">"
            e_type = struct.unpack_from(endian + "H", header, 16)[0]
            if is_64:
                phoff, phentsize, phnum = struct.unpack_from(
                    endian + "Q", header, 32)[0], *struct.unpack_from(
                    endian + "HH", header, 54)
            else:
                phoff, phentsize, phnum = struct.unpack_from(
                    endian + "I", header, 28)[0], *struct.unpack_from(
                    endian + "HH", header, 42)
            if not phnum:
                # No program headers at all: a relocatable object or a
                # static library, not an executable this can speak about.
                return None
            handle.seek(phoff)
            table = handle.read(phentsize * phnum)
            for index in range(phnum):
                entry = table[index * phentsize:(index + 1) * phentsize]
                if len(entry) < 4:
                    break
                if struct.unpack_from(endian + "I", entry, 0)[0] == _PT_INTERP:
                    return "dynamic"
            return "static" if e_type == _ET_EXEC else "library"
    except (OSError, struct.error):
        return None


def _shebang_interpreter(path: str) -> Optional[str]:
    """The interpreter a `#!` script names, or None.

    One level only, deliberately (`UX-105` scopes deeper chains out): a
    script is classified as whatever its interpreter is, because that is
    the process that actually execs and therefore the process the hook
    either sees or does not.
    """
    try:
        with open(path, "rb") as handle:
            first = handle.readline(256)
    except OSError:
        return None
    if not first.startswith(b"#!"):
        return None
    parts = first[2:].decode("utf-8", "replace").split()
    if not parts:
        return None
    # `#!/usr/bin/env python3` names the interpreter in the second word.
    if os.path.basename(parts[0]) == "env" and len(parts) > 1:
        return parts[1]
    return parts[0]


def census_static_executables(root: str) -> dict:
    """Every executable under `root`, classified.

    Returns `{"static": [paths], "dynamic": int, "libraries": int,
    "unclassified": int, "scripts": int}` with paths relative to `root`,
    sorted - two scans of one tree must produce identical output, and a
    set would not.

    Symlinks are followed to classify but reported at the name that was
    walked, since that is the name a build command would exec. A symlink
    loop or a dangling link is unclassified rather than an error: a
    census that dies on a broken link in a staged sysroot is a census
    nobody runs.
    """
    static: List[str] = []
    dynamic = libraries = unclassified = scripts = 0
    if not os.path.isdir(root):
        return {"static": [], "dynamic": 0, "libraries": 0,
                "unclassified": 0, "scripts": 0}
    for current, _dirs, files in os.walk(root):
        for name in sorted(files):
            path = os.path.join(current, name)
            try:
                if not os.access(path, os.X_OK) or not os.path.isfile(path):
                    continue
            except OSError:
                continue
            verdict = classify_elf(path)
            if verdict is None:
                interpreter = _shebang_interpreter(path)
                if interpreter is None:
                    unclassified += 1
                    continue
                # A script is whatever its interpreter is - that is the
                # process that execs, and so the one the hook sees or
                # does not. The interpreter is resolved inside this same
                # root when it is there, since that is what the sandbox
                # would run.
                scripts += 1
                staged = os.path.join(root, interpreter.lstrip("/"))
                verdict = classify_elf(staged)
                if verdict is None:
                    unclassified += 1
                    continue
            if verdict == "static":
                static.append(os.path.relpath(path, root))
            elif verdict == "library":
                libraries += 1
            else:
                dynamic += 1
    return {
        "static": sorted(static),
        "dynamic": dynamic,
        # Shared objects with the executable bit, which every sysroot
        # has. Counted, not listed: they are not programs a build execs.
        "libraries": libraries,
        "unclassified": unclassified,
        "scripts": scripts,
    }


def _local_source_paths(project_dir: str, element: str) -> List[str]:
    """The directories an element stages from its own `local` sources.

    Read from the `.bst` file for the same reason
    `read_declared_build_deps` reads its own: this must work against a
    project directory without invoking BuildStream. Only `local`
    sources - a `git` or `tar` source is not on disk before a fetch, and
    a census that silently skipped one would be worse than one that says
    it only sees local sources.
    """
    path = os.path.join(project_dir, "elements", element)
    if not os.path.exists(path):
        return []
    import yaml

    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
    except (OSError, yaml.YAMLError):
        return []
    paths = []
    for source in data.get("sources") or []:
        if isinstance(source, dict) and source.get("kind") == "local":
            local = source.get("path")
            if local:
                paths.append(os.path.join(project_dir, local))
    return paths


def census_spine_verdicts(project_dir: str) -> Dict[str, bool]:
    """UX-113: `{element: does the hook need help here}`, from the census.

    True where the element's sandbox stages at least one static
    executable - the case the `LD_PRELOAD` hook structurally cannot see.
    An element the census cannot assess is simply absent, and the shim
    traces what it has no verdict for: "not assessed" and "assessed and
    clean" are different claims, and only one of them is safe to skip.

    Returns `{}` on any failure, which the shim reads as "no census" and
    therefore traces everything - the safe direction for a policy whose
    whole purpose is to not lose coverage.
    """
    try:
        elements_dir = os.path.join(project_dir, "elements")
        elements = sorted(
            name for name in os.listdir(elements_dir) if name.endswith(".bst")
        )
        if not elements:
            return {}
        census = census_project(project_dir, elements)
    except (OSError, ValueError):
        return {}
    return {
        element: bool(entry.get("static_count"))
        for element, entry in (census.get("per_element") or {}).items()
    }


def census_project(project_dir: str, elements: List[str]) -> dict:
    """UX-105: which elements have a static executable in their sandbox,
    and which are therefore invisible to Plane 2 in part or in whole.

    Every Plane 2 report carries the same footnote - statically-linked
    processes ran but produced no trace entry, and the hook "cannot
    detect its own absence". It is honest and useless in equal measure:
    it fires identically on a capture that missed nothing and one that
    missed everything. `examples/01`'s manual elements run static
    busybox and their Plane 2 capture is empty; only a reader who knows
    the staging script would guess why.

    An element's sandbox holds what its own sources stage *and* what its
    build dependencies stage, so the census propagates over the declared
    build closure. Reported per element, so the disclaimer can name the
    element rather than the toolchain.

    **What this bounds, and what it does not.** It reads the project's
    own `local` sources - the files on disk before anything runs. A
    binary arriving from a remote artifact cache is not visible to it,
    and neither is one produced by the build. So a zero here is "nothing
    this project stages is static", not "nothing static will run"; the
    honest limit `UX-105` names, and the one `UX-106`'s spine is for.

    A staged-but-never-exec'd static binary inflates the *risk* count,
    not the *missed process* count - this bounds what the hook can miss,
    and only a spine measures what it did.
    """
    declared = read_declared_build_deps(project_dir, elements)
    own: Dict[str, dict] = {}
    for element in elements:
        merged = {"static": [], "dynamic": 0, "libraries": 0,
                  "unclassified": 0, "scripts": 0}
        for root in _local_source_paths(project_dir, element):
            counted = census_static_executables(root)
            merged["static"].extend(counted["static"])
            for key in ("dynamic", "libraries", "unclassified", "scripts"):
                merged[key] += counted[key]
        merged["static"] = sorted(set(merged["static"]))
        own[element] = merged

    def _closure(element: str, seen: Optional[Set[str]] = None) -> Set[str]:
        seen = seen if seen is not None else set()
        for dependency in declared.get(element) or []:
            if dependency in seen:
                continue
            seen.add(dependency)
            _closure(dependency, seen)
        return seen

    per_element = {}
    for element in elements:
        static = set(own[element]["static"])
        staged_by = {name: sorted(own.get(name, {}).get("static") or [])
                     for name in _closure(element)}
        for names in staged_by.values():
            static.update(names)
        per_element[element] = {
            "static_executables": sorted(static),
            "static_count": len(static),
            "own_static": own[element]["static"],
            "staged_by_dependencies": {
                name: names for name, names in sorted(staged_by.items()) if names
            },
            "dynamic_executables": own[element]["dynamic"],
        }
    total_static = sorted({
        name for entry in per_element.values()
        for name in entry["static_executables"]
    })
    return {
        "per_element": per_element,
        "static_executables": total_static,
        "elements_at_risk": sorted(
            element for element, entry in per_element.items() if entry["static_count"]
        ),
        "note": (
            "Read from the project's own `local` sources before anything runs: an "
            "ELF executable with no PT_INTERP never invokes the dynamic linker, so "
            "LD_PRELOAD never reaches it. A binary arriving from a remote artifact "
            "cache or produced by the build is not visible here, and a "
            "staged-but-never-exec'd static binary inflates the risk count rather "
            "than the missed-process count - this bounds what Plane 2 can miss, not "
            "what it did miss."
        ),
    }


def read_element_kinds(project_dir: str) -> Dict[str, str]:
    """`{element_uid: kind}` read from the element files themselves.

    UX-68 needs this to explain *why* a dependency staged nothing: a
    `stack` is pure aggregation with no artifact content of its own, so
    "nobody opened its files" is guaranteed rather than informative.

    Read from the `.bst` files rather than from `bst show`, for the same
    reason `read_declared_build_deps` does: this must work against a
    project directory without invoking BuildStream, and the kind is a
    plain top-level key. A file that cannot be read is simply absent from
    the mapping - the caller degrades to a reason without the kind, never
    to a wrong one.
    """
    kinds: Dict[str, str] = {}
    elements_dir = os.path.join(project_dir, "elements")
    if not os.path.isdir(elements_dir):
        return kinds
    for root, _dirs, files in os.walk(elements_dir):
        for name in files:
            if not name.endswith(".bst"):
                continue
            path = os.path.join(root, name)
            uid = os.path.relpath(path, elements_dir)
            try:
                with open(path, "r", errors="replace") as handle:
                    for line in handle:
                        if line.startswith("kind:"):
                            kinds[uid] = line.split(":", 1)[1].strip()
                            break
            except OSError:
                continue
    return kinds


def read_declared_build_deps(project_dir: str, elements: List[str]) -> Dict[str, List[str]]:
    """`{element: [directly declared build dependencies]}`, read from the
    element files themselves.

    "Declared" here has to mean *what the user wrote in the `.bst` file*,
    because that is what a removal recommendation would edit. An earlier
    version derived the direct set by subtracting transitive closures out
    of `bst show --deps build`, and it was wrong on real data: `lib-b.bst`
    declares `lib-a`, `core`, `codegen` and `toolchain` outright, but
    `codegen` and `core` are also inside `lib-a`'s own closure, so
    subtraction classified them as indirect and dropped three of the four
    declarations. The dependency being redundant is precisely the thing
    being detected - inferring directness from the closure hides it.

    Only `build`-type edges are returned. A `runtime` dependency is by
    definition not read during the build, so this analysis says nothing
    about one and must not propose removing it.
    """
    elements_dir = os.path.join(project_dir, "elements")
    declared: Dict[str, List[str]] = {}
    for element in elements:
        path = os.path.join(elements_dir, element)
        if not os.path.exists(path):
            continue
        # UX-77: imported here rather than at module scope. Only this
        # one function needs it, and a top-level import made `bga
        # capture --help` fail outright on an install without PyYAML -
        # the other three yaml call sites in `tools/` were already lazy
        # for the same reason.
        import yaml

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except (OSError, yaml.YAMLError):
            continue
        deps: List[str] = []
        for entry in data.get("depends") or []:
            if isinstance(entry, str):
                # Shorthand `- foo.bst` defaults to a build+runtime dep.
                deps.append(entry)
            elif isinstance(entry, dict):
                if entry.get("type") == "runtime":
                    continue
                name = entry.get("filename")
                if name:
                    deps.append(name)
        declared[element] = deps
    return declared


def read_artifact_contents(project_dir: str, elements: List[str]) -> Dict[str, Set[str]]:
    """`{element: {absolute staged paths}}` via `bst artifact list-contents`.

    This is the half UX-46 called "the half that does not exist yet".
    BuildStream stages every build dependency into one shared sandbox
    root, so by the time a compiler runs, a dependency's headers are
    indistinguishable from the base sysroot - a path carries no element
    identity. `bst artifact list-contents` supplies the inverse mapping
    directly, from BuildStream's own artifact metadata, with no
    re-staging and no per-element rebuild.

    Contents are reported relative to the artifact root (`usr/include/x.hpp`),
    and staged at the sandbox root, so each is prefixed with `/`.

    An element whose artifact cannot be read (never built, or pulled
    without contents) maps to an empty set, and the caller must treat
    that as "unknown", never as "staged nothing" - the latter would make
    every dependency look unused.
    """
    contents: Dict[str, Set[str]] = {}
    for element in elements:
        result = subprocess.run(
            ["bst", "artifact", "list-contents", element],
            cwd=project_dir, capture_output=True, text=True,
        )
        paths: Set[str] = set()
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                stripped = line.strip()
                # Skip the `<element>:` heading and blank lines.
                if not stripped or stripped.endswith(":"):
                    continue
                paths.add("/" + stripped.lstrip("/"))
        contents[element] = paths
    return contents


# UX-68: the number of staged files below which "none were opened" says
# nothing. A BuildStream `stack` has no artifact content of its own - it
# is pure aggregation - so it stages a single marker and every stack
# dependency scores 0-of-1 by construction. Measured on a real
# freedesktop-sdk capture: every one of the 9 stack candidates staged
# exactly 1 file, against 128 to 9,443 for the real elements.
_MIN_STAGED_FILES_FOR_EVIDENCE = 2


def compute_element_opens_coverage(records: List[dict]) -> Dict[str, dict]:
    """UX-107: per element, what share of its processes the *hook* could
    see - which is the share any opens-based finding speaks about.

    Empty by design on a capture with no spine records: without a second
    mechanism there is nothing to measure coverage against, and every
    pre-spine capture must go on producing exactly the analysis it always
    did. With the spine on, `spine-only` is a process the hook provably
    never entered, so the share stops being an assumption.
    """
    if not any(r.get("coverage") in (COVERAGE_BOTH, COVERAGE_SPINE_ONLY)
               for r in records):
        return {}
    coverage: Dict[str, dict] = {}
    for record in records:
        entry = coverage.setdefault(
            record.get("element") or "unknown",
            {"processes": 0, "opens_covered": 0, "spine_only": 0},
        )
        entry["processes"] += 1
        if record.get("coverage") == COVERAGE_SPINE_ONLY:
            entry["spine_only"] += 1
        else:
            entry["opens_covered"] += 1
    for entry in coverage.values():
        entry["opens_coverage"] = entry["opens_covered"] / entry["processes"]
    return coverage


def compute_declared_vs_used(
    opens_by_element: Dict[str, dict],
    declared_deps: Dict[str, List[str]],
    artifact_contents: Dict[str, Set[str]],
    element_kinds: Optional[Dict[str, str]] = None,
    opens_coverage: Optional[Dict[str, dict]] = None,
) -> dict:
    """Which declared build dependencies did each element never read?

    A dependency is a *candidate* for removal when the element's own
    sandbox opened none of the files that dependency staged. Deliberately
    not a verdict: a dependency can be needed at runtime, needed only by
    a configure-time probe whose result got cached, or needed for the
    mere existence of a directory. The output names the evidence and
    leaves the decision to the user, following the same posture UX-26 and
    UX-34 take toward omitted candidates.

    Safety rules, all of which make the analysis *refuse* rather than
    guess - the dangerous failure here is a confident false "unused" that
    gets a real dependency deleted:

    - an element with no observed opens at all is `uncovered`, not
      "used nothing". An element built entirely by statically-linked
      processes looks exactly like this (UX-11 Risk 2), and reporting
      every one of its dependencies as unused would be catastrophic.
    - an element whose hook dropped paths is `uncovered` too: a partial
      read set is precisely what turns a used dependency into a false
      unused.
    - UX-107: an element whose processes were not all reachable by the
      hook is `uncovered` by the *same* rule, now measured rather than
      assumed. `opens_coverage` (from `compute_element_opens_coverage`)
      names the share the spine proves the hook saw; anything below all
      of them leaves a process that could have opened the very file this
      analysis is about to call unread. Absent when the spine is off, and
      then nothing here changes.
    - a dependency whose artifact contents could not be read is skipped
      with a reason, never counted as unused.
    """
    unused: List[dict] = []
    used: List[dict] = []
    # UX-68: kept separate rather than dropped - the pattern is real
    # and worth reviewing, it is just not an 'unused dependency'.
    aggregating: List[dict] = []
    uncovered: List[dict] = []
    skipped: List[dict] = []

    for element, deps in sorted(declared_deps.items()):
        observed = opens_by_element.get(element)
        measured = (opens_coverage or {}).get(element)
        if not observed or not observed["paths"]:
            # UX-107: the same conclusion, but said as a measurement
            # wherever one exists. "It may be built entirely by static
            # processes" is a guess the spine can settle: it counted the
            # processes and knows how many the hook could not enter.
            if measured and not measured["opens_covered"]:
                reason = (
                    f"0 of {measured['processes']} process(es) run for this "
                    f"element were reachable by the LD_PRELOAD hook - every one "
                    f"was statically linked and seen only by the ptrace spine, "
                    f"so its read set is unmeasured rather than empty"
                )
            else:
                reason = ("no file opens observed for this element - it may be "
                          "built entirely by statically-linked processes, which "
                          "LD_PRELOAD cannot see")
            uncovered.append({"element": element, "reason": reason})
            continue
        if measured and measured["opens_covered"] < measured["processes"]:
            # Exactly the treatment a dropped-path element gets, and for
            # exactly the same reason: a partial read set is what turns a
            # used dependency into a false unused. The difference is that
            # this one is a counted share rather than a suspicion.
            uncovered.append({
                "element": element,
                "reason": f"only {measured['opens_covered']} of "
                          f"{measured['processes']} process(es) "
                          f"({measured['opens_coverage'] * 100:.0f}%) were "
                          f"reachable by the hook; the other "
                          f"{measured['spine_only']} ran statically and could "
                          f"have opened anything this analysis would call unread",
            })
            continue
        if observed["dropped"]:
            uncovered.append({
                "element": element,
                "reason": f"{observed['dropped']} path(s) exceeded the hook's "
                          f"per-process budget, so this element's read set is "
                          f"incomplete and a dependency could look unused when "
                          f"it is not",
            })
            continue

        opened = observed["paths"]
        for dep in sorted(deps):
            staged = artifact_contents.get(dep)
            if staged is None:
                skipped.append({
                    "element": element, "dependency": dep,
                    "reason": "artifact contents unavailable (not built, or "
                              "pulled without contents)",
                })
                continue
            if not staged:
                skipped.append({
                    "element": element, "dependency": dep,
                    "reason": "dependency staged no files - nothing to detect a "
                              "read of",
                })
                continue
            touched = opened & staged
            record = {
                "element": element,
                "dependency": dep,
                "staged_files": len(staged),
                "opened_files": len(touched),
            }
            if touched:
                used.append(record)
            elif len(staged) < _MIN_STAGED_FILES_FOR_EVIDENCE:
                # UX-68: a dependency that staged (almost) nothing cannot
                # be shown unused by nobody reading it. A `stack` is the
                # systematic case - pure aggregation, no artifact content
                # of its own - and it brings its *transitive* closure into
                # the sandbox, which this comparison never looked at. On a
                # real capture 9 of 10 "unused" candidates were stacks
                # staging exactly 1 file, including `runtime-minimal.bst`,
                # whose closure is glibc and gcc-libs: content no compile
                # can avoid touching.
                record["reason"] = (
                    f"{dep} staged only {len(staged)} file(s) of its own"
                    + (f" (kind: {element_kinds[dep]})"
                       if element_kinds and dep in element_kinds else "")
                    + " - it contributes content through its dependencies, "
                    "which this comparison does not attribute, so 'nobody "
                    "opened it' is not evidence of anything"
                )
                aggregating.append(record)
            else:
                record["evidence"] = (
                    f"0 of {len(staged)} files staged by {dep} were opened "
                    f"during {element}'s build"
                )
                unused.append(record)

    covered_elements = [
        element for element in declared_deps
        if not (opens_coverage or {}).get(element)
        or (opens_coverage or {})[element]["opens_covered"]
        == (opens_coverage or {})[element]["processes"]
    ]
    return {
        # UX-107: an element whose every process was static has no opens
        # and is still something this analysis has a measured statement
        # about ("0 of 24 processes were reachable"), so coverage data
        # alone makes the analysis available.
        "available": bool(opens_by_element) or bool(opens_coverage),
        # UX-107: the share this analysis speaks for. Published because a
        # candidate list computed over a fraction of the processes and one
        # computed over all of them render identically otherwise.
        "opens_coverage": ({
            "elements_considered": len(declared_deps),
            "elements_fully_covered": len(covered_elements),
            "processes": sum(e["processes"] for e in opens_coverage.values()),
            "hook_covered_processes": sum(
                e["opens_covered"] for e in opens_coverage.values()),
        } if opens_coverage else None),
        "unused_candidates": unused,
        # UX-68: dependencies that stage nothing of their own - stacks,
        # almost always. Reported separately because "nobody opened it"
        # is not evidence about them, and mixing them into the candidate
        # list made 9 of 10 real findings false positives.
        "aggregating_dependencies": aggregating,
        "used": used,
        "uncovered_elements": uncovered,
        "skipped": skipped,
        "note": (
            "A candidate is an element/dependency pair where none of the "
            "dependency's staged files were opened. This is evidence, not a "
            "verdict: runtime-only dependencies, cached configure probes, and "
            "dependencies needed only for a directory's existence all look the "
            "same from here. Elements with no observed opens, or with a "
            "truncated read set, are reported as uncovered rather than as "
            "having unused dependencies."
        ),
    }


def build_spans_from_wrapped_log(path: str) -> List[dict]:
    """UX-56: per-element BUILD spans in wall-clock seconds, from a
    wrapped BuildStream log.

    Wrapped specifically, and not raw: a raw log carries BuildStream's
    own *elapsed* prefix with no absolute anchor (`UX-06`), while the
    shim's invocation timestamps are real wall-clock. Correlating the two
    would need an anchor a raw log does not have, so this refuses rather
    than inventing one.

    Read straight from BuildStream's own `[hash][ build:element] START` /
    `SUCCESS` lines paired with the wrapper's UTC timestamp, rather than
    through the Chrome-trace event model - the question here is only
    "when was this element building", and going through the richer
    representation would couple this to its event shape for nothing.
    """
    try:
        from .bst_log_to_chrome_trace import BST_LOG_RE, PREFIX_RE, WrapperTraceConverter
    except ImportError:  # invoked as a script rather than as a package module
        from bst_log_to_chrome_trace import BST_LOG_RE, PREFIX_RE, WrapperTraceConverter

    converter = WrapperTraceConverter()
    open_starts: Dict[str, float] = {}
    spans: Dict[str, dict] = {}
    with open(path, "r", errors="replace") as handle:
        for line in handle:
            prefix = PREFIX_RE.match(line.strip())
            if not prefix:
                continue
            ts = converter.parse_timestamp(prefix.group(1))
            match = BST_LOG_RE.search(prefix.group(2))
            if ts is None or not match:
                continue
            _elapsed, _hash, action, element, status, _msg = match.groups()
            if action.strip() != "build":
                continue
            element = element.strip()
            seconds = ts / 1e6
            if status == "START":
                open_starts[element] = seconds
            elif element in open_starts:
                start = open_starts.pop(element)
                existing = spans.get(element)
                if existing is None:
                    spans[element] = {"element": element, "start": start, "end": seconds}
                else:
                    existing["start"] = min(existing["start"], start)
                    existing["end"] = max(existing["end"], seconds)
    return sorted(spans.values(), key=lambda s: s["start"])


def sandbox_durations(records: List[dict]) -> Dict[str, float]:
    """UX-64: how long each sandbox was alive, in seconds, from its own
    processes' `CLOCK_MONOTONIC` stamps.

    The shim `execv`s and so cannot record an end, but it does not have
    to: every traced process carries `inv=` (`UX-56`), so a sandbox's
    length is `max(end_ts) - min(start_ts)` over the processes that ran
    inside it. Combined with the shim's wall-clock start this yields a
    real interval without needing any clock anchor at all - the monotonic
    stamps supply only the *delta*, which is unit-comparable across
    clocks, and the wall-clock start supplies the origin.

    The interval is very slightly *shorter* than the sandbox's true one:
    bwrap starts before its first traced process and exits after its
    last. That is milliseconds against BUILD spans of seconds to minutes,
    but it errs toward accepting a containment, so it is stated rather
    than assumed away.
    """
    first: Dict[str, float] = {}
    last: Dict[str, float] = {}
    for record in records:
        key = record.get("invocation")
        if key is None:
            continue
        key = str(key)
        start_ts = record.get("start_ts")
        if start_ts is not None:
            first[key] = min(first.get(key, start_ts), start_ts)
        end_ts = record.get("end_ts")
        if end_ts is not None:
            last[key] = max(last.get(key, end_ts), end_ts)
    return {
        key: last[key] - first[key]
        for key in first.keys() & last.keys()
        if last[key] >= first[key]
    }


def correlate_invocations(
    invocations: List[dict], build_spans: List[dict],
    durations: Optional[Dict[str, float]] = None,
) -> dict:
    """UX-56/UX-64: recover each sandbox's real element by matching it
    against Plane 1's BUILD spans, when the name Plane 2 captured
    collapsed.

    Plane 2's element tag comes from bwrap's `--dir`, i.e. the build
    root. Under BuildStream's default per-element layout that *is* the
    element; under a project-wide override - `freedesktop-sdk` uses
    `build-root: /buildstream-build` - it is not. Round 7 measured what
    the tag actually contains across 25 real sandboxes: `buildstream-build`
    21 times, absent twice, and twice a *source subdirectory* name
    (`flit_core`, which is no element at all, and `expat`, which merely
    resembles one). A tag that is occasionally right by coincidence is
    worse than one uniformly wrong, because it survives a spot check.

    Matching is by **containment**: a sandbox whose whole interval lies
    inside exactly one element's BUILD span is that element's. With
    `durations` supplied the interval is real; without them only the
    start instant is known, which under `--builders 4` sits inside four
    overlapping spans and resolves almost nothing (round 7: 6 of 25).

    **No elimination.** An earlier version resolved further by assuming
    an element hosts at most one sandbox, so a resolved element could be
    struck from other candidate sets. Round 7 disproved the premise on
    real data: `components/bison.bst` hosted two sandboxes 4.1 seconds
    apart, and in the build's first 54 seconds 15 sandboxes ran against
    at most 10 concurrently-building elements. That assumption does not
    merely under-resolve, it can attribute a sandbox to the wrong
    element, so it is gone. What cannot be deduced is reported.

    Returns:
        `{"resolved": {invocation_id: element}, "ambiguous": [...],
          "unmatched": [...], "certain": int,
          "intervals_used": bool}`.
    """
    durations = durations or {}
    resolved: Dict[str, str] = {}
    ambiguous: List[str] = []
    unmatched: List[str] = []

    for invocation in invocations:
        key = str(invocation.get("invocation_id"))
        started = invocation.get("started_at")
        if started is None:
            unmatched.append(key)
            continue
        finished = started + durations.get(key, 0.0)
        # Matched on the sandbox's **end**, not its start or its whole
        # interval, and that is a measured choice rather than a tidy one.
        #
        # Plane 1 timestamps a line when the *wrapper reads* it, which
        # lags the event. Measured on a real traced build: every one of 9
        # sandboxes began BEFORE its element's logged BUILD START, by
        # 0.18s to 0.46s, so requiring the start inside the span rejects
        # nearly everything (7 of 9 came back unmatched). The same lag
        # makes the span systematically *shorter* than the sandbox, so
        # "sandbox no longer than its span" fails too - `app.bst`'s
        # sandbox ran 2.03s against a 1.62s span.
        #
        # The end is the reliable edge: BuildStream cannot log an
        # element's terminal status until its sandbox has finished, so a
        # sandbox's last process must exit before its span ends. Using it
        # alone resolved 8 of those 9 sandboxes, against 2 for whole-
        # interval containment.
        matching = [
            span["element"] for span in build_spans
            if span["start"] <= finished <= span["end"]
        ]
        if not matching:
            # No span contains the whole interval. Either the sandbox
            # belongs to no BUILD at all, or it outlived every candidate -
            # both are "cannot say", never a nearest-match.
            unmatched.append(key)
        elif len(matching) == 1:
            resolved[key] = matching[0]
        else:
            ambiguous.append(key)

    return {
        "resolved": resolved,
        "ambiguous": sorted(ambiguous),
        "unmatched": sorted(unmatched),
        "certain": len(resolved),
        # Whether the match used real intervals or only start instants -
        # the difference between a strong constraint and a weak one, and
        # a reader should not have to infer which they got.
        "intervals_used": bool(durations),
    }


def apply_correlation(records: List[dict], resolved: Dict[str, str]) -> int:
    """Relabel every traced process whose sandbox was resolved. Returns
    how many records were relabelled.

    Applied to the *whole* sandbox at once, which is the property that
    makes this worth doing: one correlated invocation fixes every process
    that ran inside it, however many thousands.
    """
    relabelled = 0
    for record in records:
        element = resolved.get(str(record.get("invocation")))
        if element and record.get("element") != element:
            record["element"] = element
            relabelled += 1
    return relabelled


def compute_binary_cost(records: List[dict], top_n: int = 5) -> dict:
    """UX-69: per element, which binaries actually burned the time.

    The report has always ranked binaries by **invocation count**, and on
    a real capture that hides the answer. For `cmake-stage1.bst` - the
    element Plane 1 correctly identifies as 43.5% of the critical path -
    the top five by count are `sh`, `as`, `ninja`, `gcc`, `cc1`, while
    the actual cost is:

        cc1plus    885 procs   4352.6 CPU s   <- absent from the count top 5
        as        1918 procs    397.5 CPU s
        cc1       1034 procs    252.9 CPU s
        dwz          1 proc     137.0 CPU s   <- one process, invisible by count

    `cc1plus` dominating by 10x is the heavy-C++-template signal; `dwz`
    holding 138 seconds of wall time in a *single* process is a
    serialization point. Counting can see neither.

    Everything here comes from records already captured (`UX-45`'s
    `cpu_us`, the paired `duration_s`), so this is a missing analysis
    rather than a missing measurement.

    CPU and wall are both reported because they answer different
    questions: CPU says what is expensive, wall says what is *blocking*.
    A single-process finding is called out separately, since one process
    holding N seconds cannot be parallelised away while N processes can.
    """
    per_element: Dict[str, dict] = {}
    for record in records:
        element = record.get("element")
        if not element:
            continue
        binary = os.path.basename((record.get("cmd") or "").split(" ")[0]) or "unknown"
        entry = per_element.setdefault(element, {})
        stat = entry.setdefault(
            binary, {"count": 0, "cpu_us": 0, "wall_s": 0.0, "measured": 0}
        )
        stat["count"] += 1
        if record.get("cpu_us") is not None:
            stat["cpu_us"] += record["cpu_us"]
            stat["measured"] += 1
        if record.get("duration_s") is not None:
            stat["wall_s"] += record["duration_s"]

    result: Dict[str, dict] = {}
    for element, binaries in per_element.items():
        by_cpu = sorted(binaries.items(), key=lambda kv: -kv[1]["cpu_us"])
        measured_cpu = sum(v["cpu_us"] for v in binaries.values())
        if not measured_cpu:
            # UX-45's rule: no CPU coverage means say so, never fall back
            # to ranking by count while looking like a cost ranking.
            result[element] = {
                "available": False,
                "note": "no CPU time was measured for this element's processes",
            }
            continue
        serial = [
            {"binary": b, "cpu_us": v["cpu_us"], "wall_s": v["wall_s"]}
            for b, v in by_cpu[:top_n]
            if v["count"] == 1 and v["wall_s"] > 0
        ]
        result[element] = {
            "available": True,
            "measured_cpu_us": measured_cpu,
            "by_cpu": [
                {"binary": b, "count": v["count"], "cpu_us": v["cpu_us"],
                 "wall_s": round(v["wall_s"], 1),
                 "cpu_share": v["cpu_us"] / measured_cpu}
                for b, v in by_cpu[:top_n]
            ],
            "by_count": [
                {"binary": b, "count": v["count"]}
                for b, v in sorted(binaries.items(), key=lambda kv: -kv[1]["count"])[:top_n]
            ],
            # UX-69: one process holding real wall time cannot be
            # parallelised away - a different fix from N processes.
            "single_process_costs": serial,
        }
    return result


def compute_peak_memory(records: List[dict]) -> dict:
    """UX-63: peak resident set size per element, from the same
    `getrusage` call `UX-45` already makes at exit.

    `UX-21` added a memory dimension to the oversubscription guard and
    had to run it entirely on two operator-*declared* numbers, because
    measurement "would need the same kind of intra-sandbox visibility"
    that was then hypothetical. It is not hypothetical now.

    Reported as a **maximum**, never a sum, and the distinction is the
    whole point. `ru_maxrss` is a per-process peak over that process's
    whole lifetime; two processes that each peaked at 500 MB at
    different moments never held 1 GB between them. Summing peaks would
    manufacture a concurrent total that nothing measured - the same
    class of error as reading occupancy as CPU (`UX-36`) or summing
    per-element redundancy savings (`UX-37`). What this *can* say is
    "no single process in this element exceeded X", which is exactly the
    input `UX-21`'s guard needs for its per-job estimate.

    Coverage is reported rather than assumed, matching `compute_cpu_time`:
    a process killed by a signal or replaced by `exec` runs no destructor
    and contributes nothing.
    """
    per_element: Dict[str, dict] = {}
    for record in records:
        entry = per_element.setdefault(
            record["element"],
            {"peak_rss_kb": None, "measured": 0, "unmeasured": 0},
        )
        if "max_rss_kb" in record:
            entry["measured"] += 1
            current = entry["peak_rss_kb"]
            entry["peak_rss_kb"] = max(current or 0, record["max_rss_kb"])
        else:
            entry["unmeasured"] += 1
    measured_total = sum(e["measured"] for e in per_element.values())
    if measured_total == 0:
        return {
            "available": False,
            "note": "no process reported a peak RSS - either the hook predates "
                    "UX-63 or every traced process was killed before its "
                    "destructor ran",
        }
    return {
        "available": True,
        "per_element": {k: per_element[k] for k in sorted(per_element)},
        "note": "Peak resident set size of the single largest process in each "
                "element (getrusage ru_maxrss at exit, KiB). A per-process "
                "peak, deliberately NOT summed across processes: two "
                "processes peaking at different moments never held the sum "
                "between them. Use it as 'no single process here exceeded "
                "this', which is what UX-21's per-job memory estimate wants.",
    }


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
    # UX-108: which mechanism actually produced the seconds above. With
    # the spine on, a process the hook never entered carries
    # `/proc/<pid>/stat`'s tick-truncated figure instead, and a note
    # naming only `getrusage` would describe a measurement this report
    # did not make. Zero on every capture taken without the spine, which
    # is what keeps their reports word-for-word what they were.
    spine_sourced = sum(
        1 for record in records if record.get("cpu_source") == "spine"
    )
    return {
        "available": measured_total > 0,
        "measured_processes": measured_total,
        "unmeasured_processes": unmeasured_total,
        "total_cpu_us": sum(e["cpu_us"] for e in per_element.values()),
        "per_element": dict(
            sorted(per_element.items(), key=lambda kv: -kv[1]["cpu_us"])
        ),
        # UX-108: which mechanism actually produced the seconds above.
        # With the spine on, a process the hook never entered carries
        # `/proc/<pid>/stat`'s tick-truncated figure instead, and a note
        # naming only `getrusage` would be describing a measurement this
        # report did not make.
        "spine_sourced_processes": spine_sourced,
        "note": (
            "Real CPU time (getrusage utime+stime) for processes that exited "
            "normally. "
            + ("Where only the ptrace spine reached a process, the figure is "
               "`/proc/<pid>/stat` read at its exit-stop instead, truncated to "
               "whole 10ms ticks - so a short static process reads as zero "
               "(UX-107). " if spine_sourced else "")
            + "Processes killed by a signal or replaced by exec run no "
            "destructor and are counted as unmeasured, never as zero. This is "
            "Plane 2 only - it is not wired into Plane 1's utilisation buckets, "
            "which remain slot occupancy (UX-36)."
        ) if measured_total else (
            "No CPU time in this trace - captured with a hook built before UX-45, "
            "or every process exited abnormally. Reported as unavailable rather "
            "than as zero."
        ),
    }


# UX-102: what a *configure* invocation looks like. Matched against the
# **executable**, never the whole command line - and that is a
# correction, not a precaution. Matching anywhere on the line classified
# `collect2 -plugin ... -L/buildstream-build/_build_dir/Bootstrap.cmk/cmake`
# and a `g++` compile as configure roots, because a *path argument*
# ended in `/cmake`. On the real freedesktop-sdk capture that inflated
# `cmake-stage1.bst` to 1329 CPU seconds of "configure", 34% of the
# element, by mis-filing whole subtrees under a linker.
_CONFIGURE_EXECUTABLES = (
    # autotools: `./configure`, `../configure`, `/src/foo/configure`,
    # and `config.status`, which re-runs it.
    'configure', 'config.status',
    # autotools' own generators - they exist only to produce the
    # configure machinery, so their cost is configure cost.
    'autoconf', 'autoreconf', 'automake', 'aclocal', 'autoheader', 'libtoolize',
    # meson's configure step.
    'meson',
)

# Wrappers whose *next* argument is the real program: `/bin/sh
# ./configure --prefix=/usr` is the ordinary autotools invocation, and
# `env FOO=1 cmake ...` is common in generated build systems.
_ARGV0_WRAPPERS = frozenset({'sh', 'bash', 'dash', 'env'})

# cmake is both phases in one binary, so it is decided by its arguments
# rather than by its name: `cmake -B... -H...` configures, `cmake
# --build` and `cmake --install` do not, and `cmake -E` is the utility
# mode the *build* uses for copies and directory creation.
_CMAKE_NON_CONFIGURE = re.compile(r'(?:^|\s)(?:--build|--install|-E)(?:\s|$)')


def _executable_candidates(cmd: str) -> List[str]:
    """The basenames that could name the program this command runs.

    Wrappers are walked through rather than stopped at:
    `/bin/sh ./configure --prefix=/usr` is the ordinary autotools
    invocation and its `argv[0]` says nothing, and `env CFLAGS=-O2
    /bin/sh ../configure` stacks two of them. Leading `VAR=value`
    assignments are skipped for the same reason, and a flag ends the
    walk - `sh -c '<script>'` runs a script, not a program named `-c`.
    """
    candidates = []
    for token in cmd.split():
        if '=' in token.split('/')[-1] and token[:1].isalpha():
            continue  # a leading `VAR=value` assignment, not the program
        if token.startswith('-'):
            # A flag: whatever the program was, it has already appeared.
            # `sh -c '<script>'` runs a script, not a program named `-c`.
            break
        base = os.path.basename(token)
        candidates.append(base)
        if base not in _ARGV0_WRAPPERS:
            break  # this is the program itself
    return candidates


def is_configure_root(cmd: str) -> bool:
    """Whether this command line is a build system configuring itself.

    A *root*, not a member: the classification takes the process tree
    below it, so what this has to recognise is the entry point, and
    conftest compilers, `sed`, `grep` and the hundreds of little probes
    autotools runs come along as descendants without needing a pattern
    each.
    """
    candidates = _executable_candidates(cmd)
    if 'cmake' in candidates:
        return not _CMAKE_NON_CONFIGURE.search(cmd)
    return any(name in _CONFIGURE_EXECUTABLES for name in candidates)


def classify_configure_phase(records: List[dict]) -> dict:
    """UX-102: split each element's traced CPU into configuring and
    building, by process parentage.

    Every element that runs `cmake` or `configure` re-answers questions
    its siblings already answered - compiler identity, ABI probes,
    header checks. `UX-23` already reports those as *repeated*; this
    reports what they *cost*, which is the number a build owner acts on.

    **By parentage, not by binary name.** An autotools configure run is
    hundreds of processes - `sed`, `grep`, `cc` compiling `conftest.c` -
    and not one of them is distinguishable from build work by its own
    command line. What is distinguishable is that they descend from
    `./configure`. So one pattern per build system's entry point, and
    the tree does the rest.

    Three limits, all of which make this an **under**-count rather than
    an over-count, and all published in the payload:

    - `LD_PRELOAD` does not see statically-linked executables. If a
      configure root itself is static, its whole subtree is misfiled as
      build work.
    - A process whose parent was not traced starts a tree of its own and
      is treated as build work. Defaulting the other way would attribute
      unknown work to configure, which is the number being argued for.
    - CPU time comes from `getrusage` at exit, so a process killed by a
      signal or replaced by `exec` contributes none. Coverage is
      reported per element.

    Parentage is resolved within a sandbox (`invocation`, falling back
    to the element name), because pids are namespaced per sandbox and
    collide freely across them - the same defect `pair_events` documents.
    """
    by_key: Dict[Tuple[str, int], dict] = {}
    for record in records:
        sandbox = record.get("invocation") or record.get("element")
        by_key[(sandbox, record["pid"])] = record

    def _is_configure(record: dict) -> bool:
        sandbox = record.get("invocation") or record.get("element")
        seen = set()
        current = record
        while current is not None:
            key = (sandbox, current["pid"])
            if key in seen:  # defensive: a pid cycle is not possible, but cheap to refuse
                return False
            seen.add(key)
            if is_configure_root(current["cmd"]):
                return True
            current = by_key.get((sandbox, current.get("ppid")))
        return False

    per_element: Dict[str, dict] = {}
    for record in records:
        entry = per_element.setdefault(record["element"], {
            "configure_cpu_us": 0, "build_cpu_us": 0,
            "configure_processes": 0, "build_processes": 0,
            "measured": 0, "unmeasured": 0,
        })
        configure = _is_configure(record)
        entry["configure_processes" if configure else "build_processes"] += 1
        if "cpu_us" in record:
            entry["measured"] += 1
            entry["configure_cpu_us" if configure else "build_cpu_us"] += record["cpu_us"]
        else:
            entry["unmeasured"] += 1

    for entry in per_element.values():
        total_cpu = entry["configure_cpu_us"] + entry["build_cpu_us"]
        entry["configure_share"] = (
            entry["configure_cpu_us"] / total_cpu if total_cpu else None
        )
        total_processes = entry["configure_processes"] + entry["build_processes"]
        entry["coverage"] = entry["measured"] / total_processes if total_processes else 0.0

    configure_total = sum(e["configure_cpu_us"] for e in per_element.values())
    cpu_total = configure_total + sum(e["build_cpu_us"] for e in per_element.values())
    return {
        "available": bool(per_element),
        "configure_cpu_us": configure_total,
        "total_cpu_us": cpu_total,
        "configure_share": configure_total / cpu_total if cpu_total else None,
        "per_element": dict(sorted(
            per_element.items(), key=lambda kv: -kv[1]["configure_cpu_us"],
        )),
        "note": (
            "Configure-phase CPU is every traced process descending from a build "
            "system's configure entry point (./configure, config.status, cmake "
            "without --build/--install/-E, meson setup, the autotools generators). "
            "Classified by parentage, so a process is configure work because of "
            "what started it, not what it is called. Statically-linked processes "
            "are invisible to LD_PRELOAD and a process with no traced parent is "
            "counted as build work - both make this a floor."
        ),
    }


# UX-107: how far the two mechanisms' CPU figures may differ before the
# disagreement is worth reporting.
#
# They measure the same quantity by different means - `getrusage` at
# exit against `/proc/<pid>/stat` read at the exit-stop - and are
# expected to agree to the clock tick. `/proc` reports in `USER_HZ`
# (10ms on every Linux this runs on), so a difference of one tick is
# quantization rather than disagreement; anything past a handful of them
# is a fact about the capture.
CPU_RECONCILIATION_TOLERANCE_US = 50_000


def compute_stream_coverage(records: List[dict],
                            fork_only_exits: int = 0) -> dict:
    """UX-107: coverage as a measured number rather than a footnote.

    Before the spine there was one sentence, printed identically whether
    the trace had missed nothing or everything. With two streams there
    are three real classes and the report can count them:

    - `spine+hook` - seen by both, and so complete: lifecycle, CPU,
      memory *and* opened paths.
    - `spine-only` - a statically-linked process. Fully measured except
      for opens, which need in-process interposition the spine
      deliberately does not do.
    - `hook-only` - either the spine was off (every capture before
      `UX-106`) or it missed something, which is itself worth knowing.

    Also reconciles the CPU figures the two mechanisms measured
    independently, in the `UX-53` spirit: a quantity computed twice is a
    free test. Disagreements are counted and the worst is named; nothing
    is averaged, because averaging two measurements hides the fact that
    they differed.
    """
    if not records:
        return {}
    counts: Dict[str, int] = {}
    for record in records:
        counts[record.get("coverage", COVERAGE_HOOK_ONLY)] = counts.get(
            record.get("coverage", COVERAGE_HOOK_ONLY), 0,
        ) + 1
    opens_covered = counts.get(COVERAGE_BOTH, 0) + counts.get(COVERAGE_HOOK_ONLY, 0)
    disagreements = []
    for record in records:
        if "hook_cpu_us" not in record or "spine_cpu_us" not in record:
            continue
        delta = abs(record["hook_cpu_us"] - record["spine_cpu_us"])
        if delta > CPU_RECONCILIATION_TOLERANCE_US:
            disagreements.append({
                "pid": record["pid"], "element": record["element"],
                "spine_cpu_us": record["spine_cpu_us"],
                "hook_cpu_us": record["hook_cpu_us"],
                "delta_us": delta, "cmd": record["cmd"][:120],
            })
    disagreements.sort(key=lambda entry: -entry["delta_us"])
    # The per-process check above cannot see a *systematic* difference:
    # 663 pairs each within one clock tick still summed to 58.47s against
    # 54.14s on a real examples/06 capture - a 7.4% aggregate gap, and
    # every pair individually "agreeing". Measured on the same
    # population the per-process check ran on, because a total over one
    # set compared with a total over another measures the sets.
    reconciled = [r for r in records if "hook_cpu_us" in r and "spine_cpu_us" in r]
    aggregate = None
    if reconciled:
        spine_total = sum(r["spine_cpu_us"] for r in reconciled)
        hook_total = sum(r["hook_cpu_us"] for r in reconciled)
        aggregate = {
            "processes": len(reconciled),
            "spine_cpu_us": spine_total,
            "hook_cpu_us": hook_total,
            "delta_us": spine_total - hook_total,
            # Against the hook's total, because that is the figure the
            # merged model uses - a percentage of the number nobody
            # consumes measures nothing a reader can act on.
            "delta_pct": (
                (spine_total - hook_total) / hook_total * 100 if hook_total else 0.0
            ),
        }
    return {
        "processes": len(records),
        "by_coverage": dict(sorted(counts.items())),
        # Opened paths need the hook. This is the share of processes any
        # opens-based finding (`UX-46`'s declared-vs-used) can speak
        # about at all - published because the alternative is a finding
        # that reads as "no unused dependencies" when it means "nobody
        # could look".
        "opens_covered_processes": opens_covered,
        "opens_coverage": opens_covered / len(records),
        "cpu_reconciled_processes": sum(
            1 for record in records if "hook_cpu_us" in record
        ),
        # UX-107: how many processes' CPU time is a tick-truncated
        # figure because no finer one exists for them. Published because
        # a static-heavy build's CPU total is materially low and the
        # report must say so rather than let the number pass as exact.
        "cpu_from_spine_only": sum(
            1 for record in records if record.get("cpu_source") == "spine"
        ),
        # UX-123: pids that ran more than one image. Collapsed into one
        # record each, because the kernel's CPU and RSS figures are
        # per-pid and cumulative across execs - published so a reader can
        # see the collapse rather than wonder where the records went.
        "exec_chains_collapsed": sum(
            1 for record in records if record.get("exec_chain", 1) > 1
        ),
        # UX-123: exits recorded for pids that never exec'd - a
        # fork-without-exec child is the same program as its parent and
        # wears its cmdline, so it is not a process to list. Dropped, and
        # said so.
        "fork_only_exits": fork_only_exits,
        "cpu_disagreements": disagreements[:8],
        "cpu_disagreement_count": len(disagreements),
        "cpu_aggregate": aggregate,
        "note": (
            "Process coverage is the union of both mechanisms; opens coverage is the "
            "hook's alone, since opened paths need in-process interposition. A "
            "`spine-only` process is fully measured except for its opens. CPU time "
            "reported for a process seen by both is the spine's per-process figure, "
            "never the sum of the two - and it is the later of the two "
            "measurements, since the hook's destructor runs before the process is "
            "finished while the spine reads /proc at the kernel's exit-stop."
        ),
    }


def summarize(records: List[dict], correlation: Optional[dict] = None,
              fork_only_exits: int = 0) -> dict:
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
    redundant_operations, redundant_coverage = detect_redundant_operations(records)
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
        # UX-56: whether those element names are element names at all.
        "element_attribution": assess_element_attribution(by_element),
        # UX-56: how the names above were arrived at, when a
        # correlation ran. Absent when it did not.
        "invocation_correlation": correlation,
        "max_concurrency": compute_max_concurrency(records),
        # UX-45: real, kernel-measured CPU time per element.
        "cpu_time": compute_cpu_time(records),
        # UX-102: of that CPU, how much was the build system working out
        # how to build rather than building.
        "configure_phase": classify_configure_phase(records),
        "peak_memory": compute_peak_memory(records),
        # UX-69: where the time went inside each element, not how many
        # times something ran.
        "binary_cost": compute_binary_cost(records),
        # UX-32: per-element achieved parallelism - the question this
        # plane exists to answer. See compute_per_element_parallelism.
        "per_element_parallelism": compute_per_element_parallelism(records),
        "wall_span_s": (wall_end - wall_start) if wall_start is not None and wall_end is not None else None,
        "redundant_operations": redundant_operations,
        # UX-73: additive sibling key - what the list above excluded and
        # why, and the note that its figures do not add. Kept beside the
        # findings rather than folded into them, the same shape UX-04's
        # `attribution_hints` uses, so an existing consumer of
        # `redundant_operations` sees no change.
        "redundant_operations_coverage": redundant_coverage,
        "processes": records,
        "static_binary_disclaimer": STATIC_BINARY_DISCLAIMER,
        # UX-107: which mechanism saw each process, as counts rather
        # than as a footnote.
        "stream_coverage": compute_stream_coverage(
            records, fork_only_exits=fork_only_exits),
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


def load_and_summarize(raw_log_path: str, project_dir: Optional[str] = None,
                       invocation_log_path: Optional[str] = None,
                       plane1_log_path: Optional[str] = None) -> dict:
    """Parse a raw trace log into a report.

    `project_dir` (UX-46) enables the declared-vs-used dependency
    analysis, which needs to ask BuildStream what each element's artifact
    staged. Omitted - the default, and what `report` does without a
    project - the rest of the report is exactly as before.
    """
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
    # UX-107: one process, one entry. With the spine running every
    # dynamically-linked process appears in both streams, and summing
    # them would double-count exactly the CPU and concurrency this plane
    # exists to measure. A capture with no spine records passes through
    # unchanged, which is what keeps every pre-spine capture parsing
    # byte-identically.
    records = merge_record_streams(pair_events(events))
    # UX-123: counted from the events, since pairing drops them.
    fork_only_exits = count_fork_only_exits(events)

    # UX-56: correct collapsed element names before anything is computed
    # from them - every downstream signal (declared-vs-used, per-element
    # parallelism, CPU time, peak memory) is keyed on this name, so a
    # correction applied later would leave them all disagreeing.
    correlation = None
    # UX-113: the spine policy's own decisions, which only the shim knows
    # and only the invocation log carries. Read whenever that log exists,
    # not only when a correlation is being computed: "the policy skipped
    # this element" and "this element ran no processes" are different
    # facts, and the trace alone cannot tell them apart.
    spine_policy = None
    if invocation_log_path and os.path.exists(invocation_log_path):
        sandboxes = [
            json.loads(line) for line in open(invocation_log_path, errors="replace")
            if line.strip()
        ]
        if sandboxes and any("spine_traced" in entry for entry in sandboxes):
            traced = sum(1 for entry in sandboxes if entry.get("spine_traced"))
            spine_policy = {
                "sandboxes": len(sandboxes),
                "spine_traced": traced,
                "policy": ("on" if traced == len(sandboxes)
                           else "off" if traced == 0 else "auto"),
            }
    if invocation_log_path and plane1_log_path:
        invocations = [
            json.loads(line) for line in open(invocation_log_path, errors="replace")
            if line.strip()
        ]
        spans = build_spans_from_wrapped_log(plane1_log_path)
        # UX-64: give the correlation real intervals rather than start
        # instants. Under `--builders 4` an instant sits inside four
        # overlapping spans and resolves almost nothing.
        correlation = correlate_invocations(
            invocations, spans, durations=sandbox_durations(records)
        )
        correlation["relabelled_processes"] = apply_correlation(
            records, correlation["resolved"]
        )
        correlation["elements_in_plane1"] = len(spans)
    report = summarize(records, correlation=correlation,
                       fork_only_exits=fork_only_exits)
    if spine_policy:
        report["spine_policy"] = spine_policy

    # UX-46: only attempted when a project directory is available, since
    # it needs `bst artifact list-contents` and the project's own
    # declared dependency edges.
    opens_by_element = parse_open_records(
        text, open_element_overrides=(correlation or {}).get('resolved'))
    # UX-107: the elements this analysis must speak about are not only the
    # ones with opens. An element built entirely by static processes has
    # none at all, and dropping it here is what made the analysis silent
    # in exactly the case it most needs to say "unmeasured" - the
    # difference between "no unused dependencies" and "nobody could look".
    #
    # Only elements the hook provably never entered are added, never
    # every element with coverage data: a capture taken without
    # open-tracking has no opens *and* full hook coverage, and pulling
    # those in would report nine fully-traced elements as "may be built
    # entirely by statically-linked processes" - a wrong reason where
    # there had been no claim at all. Measured on `examples/06`.
    element_coverage = compute_element_opens_coverage(records)
    unmeasured = {
        element for element, entry in element_coverage.items()
        if element != "unknown" and not entry["opens_covered"]
    }
    analysed = sorted(set(opens_by_element) | unmeasured)
    if project_dir and analysed and (opens_by_element or unmeasured):
        declared = read_declared_build_deps(project_dir, analysed)
        needed = {dep for deps in declared.values() for dep in deps}
        contents = read_artifact_contents(project_dir, sorted(needed))
        report["declared_vs_used"] = compute_declared_vs_used(
            opens_by_element, declared, contents,
            element_kinds=read_element_kinds(project_dir),
            # UX-107: computed over the hook-covered processes, and told
            # to say so - the alternative is a finding that reads "no
            # unused dependencies" when it means "nobody could look".
            opens_coverage=element_coverage,
        )

    # UX-105: what the hook *could not* have seen, measured from the
    # staged roots rather than left to a footnote that fires identically
    # whether it missed nothing or everything.
    if project_dir:
        elements = sorted(
            name for name in os.listdir(os.path.join(project_dir, "elements"))
            if name.endswith(".bst")
        ) if os.path.isdir(os.path.join(project_dir, "elements")) else []
        if elements:
            report["static_census"] = census_project(project_dir, elements)
    elif opens_by_element:
        report["declared_vs_used"] = {
            "available": False,
            "note": "opened-path data was captured, but the declared-vs-used "
                    "analysis needs the BuildStream project directory to read "
                    "each dependency's artifact contents - pass --project-dir.",
        }
    report["opens_captured"] = {
        element: {"paths": len(entry["paths"]), "dropped": entry["dropped"],
                  "processes": entry["processes"],
                  # UX-57: how many times a process filled its window and
                  # flushed rather than dropping. Zero on any build small
                  # enough never to fill one, which is most of them.
                  "windows": entry["windows"]}
        for element, entry in sorted(opens_by_element.items())
    }
    return report


def _format_cpu_time(cpu_time: dict) -> List[str]:
    """Render UX-45's per-element CPU block, or say plainly that no CPU
    time was captured. Never renders a zero as if it were a measurement."""
    if not cpu_time:
        return []
    if not cpu_time.get("available"):
        return [f"CPU time: unavailable - {cpu_time.get('note', '')}"]

    measured = cpu_time["measured_processes"]
    unmeasured = cpu_time["unmeasured_processes"]
    # UX-108: name the mechanism only when it is the one that measured.
    spine_sourced = cpu_time.get("spine_sourced_processes") or 0
    source = "getrusage" if not spine_sourced else (
        f"getrusage, {spine_sourced} from /proc at the ptrace exit-stop"
    )
    lines = [
        f"Real CPU time ({source}): {cpu_time['total_cpu_us'] / 1e6:.2f}s across "
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


def _format_configure_phase(configure: dict) -> List[str]:
    """UX-102: the configure tax, with the elements that pay it."""
    if not configure.get("available") or not configure.get("total_cpu_us"):
        return []
    share = configure["configure_share"] or 0.0
    lines = [
        "",
        f"Configure tax (Plane 2): {configure['configure_cpu_us'] / 1e6:.1f} of "
        f"{configure['total_cpu_us'] / 1e6:.1f} measured CPU seconds ({share * 100:.1f}%) "
        f"went to configuring rather than building",
    ]
    payers = [
        (element, entry) for element, entry in configure["per_element"].items()
        if entry["configure_cpu_us"]
    ][:_CONFIGURE_PAYERS_SHOWN]
    if not payers:
        lines.append("  No traced process descended from a configure entry point.")
    for element, entry in payers:
        lines.append(
            f"  {element:<32s} {entry['configure_cpu_us'] / 1e6:7.2f} CPU s "
            f"({(entry['configure_share'] or 0) * 100:3.0f}% of its measured CPU, "
            f"{entry['configure_processes']} process(es))"
        )
    remaining = sum(
        1 for entry in configure["per_element"].values() if entry["configure_cpu_us"]
    ) - len(payers)
    if remaining > 0:
        lines.append(f"  (+{remaining} more element(s), see --format json)")
    lines.append(f"  ({configure['note']})")
    return lines


_CONFIGURE_PAYERS_SHOWN = 8


def _format_binary_cost(binary_cost: dict, elements: List[str]) -> List[str]:
    """UX-69's per-element block, for the elements worth reading about.

    Ranked by CPU time with the count shown beside it, because the two
    answer different questions and the report used to publish only the
    one that hides the answer.
    """
    if not binary_cost:
        return []
    lines = ["Where the time went inside each element (by CPU time, not count):"]
    for element in elements:
        entry = binary_cost.get(element)
        if not entry:
            continue
        if not entry.get("available"):
            lines.append(f"  {element}: {entry.get('note', 'unavailable')}")
            continue
        lines.append(f"  {element}")
        for b in entry["by_cpu"]:
            lines.append(
                f"    {b['binary']:<14s} {b['cpu_us'] / 1e6:9.1f} CPU s "
                f"({b['cpu_share']:5.1%})  {b['count']:6d} process(es), "
                f"{b['wall_s']:.1f}s wall"
            )
        for serial in entry.get("single_process_costs") or []:
            lines.append(
                f"    NOTE: {serial['binary']} is a SINGLE process holding "
                f"{serial['wall_s']:.1f}s of wall time - a serialization point "
                f"that more parallelism cannot help"
            )
    lines.append("")
    return lines


def _format_peak_memory(peak_memory: dict) -> List[str]:
    """UX-63's per-element block. States that the figure is a per-process
    peak and not a total, because a bare "Peak memory" heading beside a
    per-element list reads as exactly the concurrent total it is not."""
    if not peak_memory:
        return []
    if not peak_memory.get("available"):
        return ["Peak memory: unavailable - " + peak_memory.get("note", ""), ""]
    lines = ["Peak Memory (largest single process per element):"]
    for element, entry in peak_memory["per_element"].items():
        peak_kb = entry["peak_rss_kb"]
        if peak_kb is None:
            lines.append(f"  {element:40s} not measured")
            continue
        coverage = ""
        if entry["unmeasured"]:
            coverage = (f"  ({entry['measured']} of "
                        f"{entry['measured'] + entry['unmeasured']} processes measured)")
        lines.append(f"  {element:40s} {peak_kb / 1024:8.1f} MB{coverage}")
    lines.append("  NOTE: a per-process peak, not a concurrent total - these are "
                 "maxima and must not be summed.")
    lines.append("")
    return lines


def _format_census_text(census: dict) -> str:
    """UX-105's standalone view: which elements have a static executable
    in their sandbox, and where it came from."""
    at_risk = census.get("elements_at_risk") or []
    names = census.get("static_executables") or []
    lines = [
        "=" * 60,
        "Static Executable Census (Plane 2 blind spot)",
        "=" * 60,
        f"{len(names)} static executable(s) staged, reaching {len(at_risk)} "
        f"element(s) of {len(census.get('per_element') or {})}",
    ]
    if not names:
        lines.append(
            "  Nothing this project stages is statically linked, so LD_PRELOAD has "
            "nothing to miss among them."
        )
    for name in names[:_CENSUS_BINARIES_SHOWN]:
        lines.append(f"    {name}")
    if len(names) > _CENSUS_BINARIES_SHOWN:
        lines.append(f"    (+{len(names) - _CENSUS_BINARIES_SHOWN} more)")
    for element in at_risk[:_CENSUS_ELEMENTS_SHOWN]:
        entry = census["per_element"][element]
        sources = entry.get("staged_by_dependencies") or {}
        origin = (
            f" via {', '.join(sorted(sources)[:2])}" if sources
            else " from its own sources"
        )
        lines.append(f"  {element}: {entry['static_count']} static{origin}")
    if len(at_risk) > _CENSUS_ELEMENTS_SHOWN:
        lines.append(f"  (+{len(at_risk) - _CENSUS_ELEMENTS_SHOWN} more element(s))")
    lines.append("")
    lines.append(f"({census['note']})")
    lines.append("=" * 60)
    return "\n".join(lines)


_CENSUS_BINARIES_SHOWN = 8
_CENSUS_ELEMENTS_SHOWN = 8


def _format_stream_coverage(report: dict) -> List[str]:
    """UX-107: coverage, counted. Silent on a capture with one stream and
    nothing to say about the other - which is every capture taken before
    the spine existed, and which must read exactly as it always did."""
    coverage = report.get("stream_coverage") or {}
    counts = coverage.get("by_coverage") or {}
    if not counts or set(counts) == {COVERAGE_HOOK_ONLY}:
        return []
    lines = [""]
    parts = ", ".join(f"{count} {name}" for name, count in counts.items())
    lines.append(f"Process coverage: {coverage['processes']} process(es) - {parts}")
    if counts.get(COVERAGE_SPINE_ONLY):
        lines.append(
            f"  {counts[COVERAGE_SPINE_ONLY]} were seen only by the ptrace spine - "
            f"statically-linked, so fully measured except for opened paths, which "
            f"need the in-process hook. Opens coverage: "
            f"{coverage['opens_coverage'] * 100:.0f}% of processes."
        )
    reconciled = coverage.get("cpu_reconciled_processes") or 0
    if reconciled:
        disagreements = coverage.get("cpu_disagreement_count") or 0
        if disagreements:
            worst = coverage["cpu_disagreements"][0]
            lines.append(
                f"  CPU measured twice for {reconciled} process(es), and "
                f"{disagreements} disagree by more than a clock tick - worst "
                f"{worst['delta_us'] / 1e6:.2f}s on {worst['element']} "
                f"(`{worst['cmd'][:60]}`). Reported, not averaged."
            )
        else:
            lines.append(
                f"  CPU measured twice for {reconciled} process(es) - `getrusage` at "
                f"exit against `/proc/<pid>/stat` at the exit-stop - and every pair "
                f"agrees to within a clock tick."
            )
        aggregate = coverage.get("cpu_aggregate")
        if aggregate and abs(aggregate["delta_pct"]) >= 1.0:
            lines.append(
                f"  Over those {aggregate['processes']} process(es) the two "
                f"mechanisms still total "
                f"{aggregate['spine_cpu_us'] / 1e6:.2f}s (spine) against "
                f"{aggregate['hook_cpu_us'] / 1e6:.2f}s (hook), "
                f"{aggregate['delta_pct']:+.1f}% - a systematic offset no "
                f"per-process tolerance can see, and a resolution difference "
                f"rather than a disagreement: /proc reports whole 10ms ticks and "
                f"truncates, so every process shorter than a tick reads as zero. "
                f"The hook's microsecond figure is the one used."
            )
    policy = report.get("spine_policy")
    if policy and policy["spine_traced"] < policy["sandboxes"]:
        lines.append(
            f"  The ptrace spine ran for {policy['spine_traced']} of "
            f"{policy['sandboxes']} sandbox(es) - the ones the pre-build census "
            f"says the LD_PRELOAD hook is blind for, plus any it could not assess. "
            f"The rest ran hook-only, at hook-only cost (UX-113)."
        )
    collapsed = coverage.get("exec_chains_collapsed") or 0
    fork_only = coverage.get("fork_only_exits") or 0
    if collapsed or fork_only:
        parts = []
        if collapsed:
            parts.append(
                f"{collapsed} pid(s) ran more than one image and are reported as one "
                f"process each, named for the last - CPU and peak RSS are per-pid and "
                f"cumulative across execs, so they describe the process rather than "
                f"any one of its images"
            )
        if fork_only:
            parts.append(
                f"{fork_only} exit(s) were recorded for pids that never exec'd "
                f"(fork-without-exec children, wearing their parent's command line) "
                f"and are not listed as processes"
            )
        lines.append("  " + "; ".join(parts) + " (UX-123).")
    spine_cpu = coverage.get("cpu_from_spine_only") or 0
    if spine_cpu:
        lines.append(
            f"  {spine_cpu} process(es) carry only the spine's tick-truncated "
            f"CPU time - statically linked, or gone before the hook's destructor "
            f"could run - so their share of the CPU total is a lower bound, and a "
            f"short-lived one among them reads as zero."
        )
    return lines


def _format_static_census(report: dict) -> List[str]:
    """UX-105: the blind spot, named where it is measured and silent
    where it is not there.

    The generic footnote fired on every report, which made it furniture:
    identical on a capture that missed nothing and one whose entire
    process list is empty because every command was static busybox. With
    a census in hand there are three different things to say, and only
    one of them is the old sentence.
    """
    census = report.get("static_census")
    coverage = report.get("stream_coverage") or {}
    counts = coverage.get("by_coverage") or {}
    # UX-107: whether a mechanism that sees a process regardless of its
    # linkage was running at all. The old footnote's central claim -
    # "this tool cannot detect its own absence" - stops being true the
    # moment it was.
    spine_ran = bool(
        counts.get(COVERAGE_BOTH, 0) or counts.get(COVERAGE_SPINE_ONLY, 0)
    )
    spine_seen = counts.get(COVERAGE_SPINE_ONLY, 0)
    if census is None:
        if not spine_ran:
            # No project directory and one mechanism, so nothing was
            # measured. The old footnote is exactly right here and stays
            # word for word.
            return ["", f"NOTE: {report['static_binary_disclaimer']}"]
        return [
            "",
            f"NOTE: the ptrace spine recorded every process regardless of its "
            f"linkage, so the LD_PRELOAD blind spot does not apply to this process "
            f"list: {spine_seen} of {coverage['processes']} process(es) were seen "
            f"by the spine alone. What remains partial is opened paths, which need "
            f"the in-process hook - "
            f"{coverage['opens_coverage'] * 100:.0f}% of processes (UX-107).",
        ]
    at_risk = census.get("elements_at_risk") or []
    if not at_risk:
        if spine_ran:
            # UX-108: the census's own stated blind spot - binaries it
            # cannot see because they arrive from a cache or are produced
            # by the build - is exactly what the spine *can* see. With
            # both, this stops being a caveat and becomes a result.
            # Measured on freedesktop-sdk: 0 of 127,632.
            return [
                "",
                f"NOTE: no statically-linked executable is staged by this project's "
                f"own sources, and the ptrace spine - which records a process "
                f"whatever its linkage - found none among the "
                f"{coverage['processes']} process(es) this build actually ran "
                f"either. The census's own blind spot (binaries from a remote "
                f"artifact cache, or produced by the build) is measured here "
                f"rather than left as a caveat (UX-105/UX-108).",
            ]
        return [
            "",
            "NOTE: no statically-linked executable is staged by this project's own "
            "sources, so LD_PRELOAD had nothing to miss among them. Binaries "
            "arriving from a remote artifact cache or produced by the build are "
            "outside what this census can see (UX-105).",
        ]
    names = census.get("static_executables") or []
    shown = ", ".join(os.path.basename(name) for name in names[:4])
    more = f" (+{len(names) - 4} more)" if len(names) > 4 else ""
    # UX-107: the census bounds what the hook can miss; the spine
    # measures what was actually seen. With both in hand the footnote
    # stops being a warning and becomes a statement about this capture.
    if spine_ran and not spine_seen:
        # The bound held and nothing hit it: the binaries are staged but
        # no process was exec'd from one. That is the census's own stated
        # limit - staged is not exec'd - closed by measurement rather
        # than left as a standing warning.
        return [
            "",
            f"NOTE: {len(names)} static executable(s) are staged ({shown}{more}), "
            f"and the ptrace spine - which sees a process whatever its linkage - "
            f"recorded none exec'd from them across "
            f"{coverage['processes']} process(es). The census bounds the risk; this "
            f"run did not hit it (UX-105/UX-107).",
        ]
    if spine_seen:
        return [
            "",
            f"NOTE: {len(names)} static executable(s) are staged ({shown}{more}) and "
            f"the ptrace spine recorded {spine_seen} process(es) the LD_PRELOAD hook "
            f"could not have seen. The blind spot the census bounds is measured here, "
            f"not merely disclaimed (UX-105/UX-106/UX-107).",
        ]
    return [
        "",
        f"NOTE: {len(names)} static executable(s) staged for {len(at_risk)} "
        f"element(s) - {shown}{more}. Processes exec'd from these produce no trace "
        f"record at all: LD_PRELOAD only reaches a binary that invokes the dynamic "
        f"linker. Affected: {', '.join(at_risk[:4])}"
        + (f" (+{len(at_risk) - 4} more)" if len(at_risk) > 4 else "")
        + ". This bounds what the trace can be missing; it does not measure what it "
          "did miss (UX-105). "
        # UX-108: the budget decided the default, and a default-off
        # mechanism that nothing points at is one nobody finds. Said
        # here, where the reader is already looking at the gap, and with
        # the price attached so it is a choice rather than an
        # advertisement.
          "Re-run with `bga capture run --trace-spine` to record them anyway: a "
          "ptrace process-event tracer sees a process whatever its linkage, at a "
          "measured +2.7% wall on a compile-bound build and +13.5% on a "
          "process-dense one, which is why it is not the default (UX-106/UX-108).",
    ]


def _format_declared_vs_used(analysis: dict) -> List[str]:
    """Render UX-46's declared-vs-used block as *candidates with
    evidence*, never as a verdict - a confident false "unused" is the
    dangerous failure here, since acting on it deletes a real edge."""
    if not analysis:
        return []
    if not analysis.get("available"):
        return [f"Declared-vs-used: not available - {analysis.get('note', '')}"]

    unused = analysis.get("unused_candidates") or []
    used = analysis.get("used") or []
    lines = [
        f"Declared build dependencies never read: {len(unused)} candidate(s) "
        f"across {len({u['element'] for u in unused})} element(s); "
        f"{len(used)} dependency edge(s) confirmed used"
    ]
    by_element: Dict[str, List[dict]] = {}
    for entry in unused:
        by_element.setdefault(entry["element"], []).append(entry)
    for element, entries in sorted(by_element.items()):
        names = ", ".join(e["dependency"] for e in entries)
        staged = sum(e["staged_files"] for e in entries)
        lines.append(f"  {element:26s} never read: {names}  ({staged} staged file(s))")
    for entry in analysis.get("uncovered_elements") or []:
        lines.append(f"  {entry['element']:26s} UNCOVERED - {entry['reason']}")
    for entry in analysis.get("skipped") or []:
        lines.append(
            f"  {entry['element']:26s} skipped {entry['dependency']} - {entry['reason']}"
        )
    # UX-75: `UX-68` filtered these out of the candidate list and gave
    # them their own key, and until now nothing rendered that key at all
    # - so the filtered population was visible only to someone reading
    # the raw JSON, which is indistinguishable from it not existing.
    aggregating = analysis.get("aggregating_dependencies") or []
    if aggregating:
        lines.append(
            f"  {len(aggregating)} further pair(s) set aside as aggregating - the "
            f"dependency stages almost nothing of its own (a `stack` stages one "
            f"marker file), so 'nobody opened it' is not evidence about it; see "
            f"`declared_vs_used.aggregating_dependencies` in the JSON report"
        )
    # UX-107: what share of the processes this verdict is computed over.
    # Silent when the spine was off, since then there is no measurement
    # to report and the report must read as it always did.
    share = analysis.get("opens_coverage")
    if share:
        lines.append(
            f"  Computed over the hook-covered processes: "
            f"{share['hook_covered_processes']} of {share['processes']} "
            f"({share['hook_covered_processes'] / share['processes'] * 100:.0f}%), "
            f"and {share['elements_fully_covered']} of "
            f"{share['elements_considered']} element(s) had every process covered. "
            f"The rest are listed UNCOVERED above rather than as having no unused "
            f"dependencies."
        )
    lines.append(f"  ({analysis['note']})")
    return lines


def _format_text(report: dict) -> str:
    # Every other report this tool prints opens with a banner naming
    # what it is; this one opened straight into a process count, so a
    # Plane 2 report pasted anywhere was unidentifiable as one. No run id
    # is claimed: that hash is Plane 1's, computed from the declared
    # graph, and a native report has no access to it - `bga correlate`
    # is where the two identities meet.
    lines = [
        "=" * 60,
        "Native Build Trace (Plane 2)",
        "=" * 60,
    ]
    lines += [
        f"Processes traced: {report['process_count']} "
        f"({report['matched_count']} matched, {report['open_count']} no observed exit)",
        # UX-32: this counts every traced process, including `make`/`sh`
        # wrappers that spend their lives waiting on children, so it
        # routinely exceeds the host's real core count and must not be
        # read as host load. The per-element block below is the
        # interpretable number.
        f"Max observed concurrency (all traced processes, incl. idle wrappers): "
        f"{report['max_concurrency']} live processes (matched only - see "
        # The task citation belongs at the end, where every other note
        # in this tool puts it - mid-sentence it interrupts the one line
        # a reader has to understand before any number below means
        # anything.
        f"open_records_note). A count of processes alive at once, NOT of "
        f"cores in use - most are blocked wrappers (sh, make, the gcc "
        f"driver), so a figure above the host's core count is expected and "
        f"is not oversubscription evidence on its own (UX-61).",
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
    # UX-56: said immediately after the split it invalidates, and before
    # every section derived from it.
    attribution = report.get("element_attribution") or {}
    if attribution.get("note"):
        lines.append("")
        lines.append(f"ELEMENT ATTRIBUTION UNRELIABLE: {attribution['note']}")
    lines.extend(_format_cpu_time(report.get("cpu_time") or {}))
    lines.extend(_format_configure_phase(report.get("configure_phase") or {}))
    # UX-69: shown for the elements that actually carry time - the
    # heaviest by measured CPU, which is where a reader is heading.
    _bc = report.get("binary_cost") or {}
    _heaviest = sorted(
        (e for e, v in _bc.items() if v.get("available")),
        key=lambda e: -_bc[e]["measured_cpu_us"],
    )[:3]
    lines.extend(_format_binary_cost(_bc, _heaviest))
    # UX-75: a text-side cap must say what it capped. The JSON carries
    # every element; a block that silently shows three reads as a build
    # with three elements worth measuring.
    _available = [e for e, v in _bc.items() if v.get("available")]
    if len(_available) > len(_heaviest):
        lines.append(
            f"  (+{len(_available) - len(_heaviest)} further element(s) measured, "
            f"shown in the JSON report under `binary_cost`)"
        )
    lines.extend(_format_peak_memory(report.get("peak_memory") or {}))
    lines.extend(_format_declared_vs_used(report.get("declared_vs_used") or {}))
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
        # UX-73: said under the list, because a reader scanning it
        # top-down will otherwise add the figures - and on the real
        # capture their sum (4129s) exceeds the build's own duration
        # (3614s), which is impossible.
        lines.append(
            "  (each figure is an upper bound for one signature on its own "
            "worst-affected element; they are maxima over concurrent elements "
            "and must not be summed)"
        )
    coverage = report.get("redundant_operations_coverage") or {}
    if coverage.get("excluded_unresolved_only") or coverage.get(
        "excluded_element_command_blocks"
    ):
        # UX-73: a shorter list reads as a cleaner build unless the
        # exclusions are stated. The unresolved-only count is also a
        # coverage signal in its own right: it rises when element
        # attribution gets worse.
        lines.append(
            f"  ({coverage.get('excluded_unresolved_only', 0)} candidate(s) excluded "
            f"as seen under the unresolved attribution bucket rather than 2+ real "
            f"elements, and {coverage.get('excluded_element_command_blocks', 0)} "
            f"process(es) excluded as each element's own top-level command block)"
        )
    lines.append("")
    lines.extend(_format_stream_coverage(report))
    lines.extend(_format_static_census(report))
    # Closed the way every other report in this tool closes, so a reader
    # can tell a truncated paste from a complete one.
    lines.append("=" * 60)
    return "\n".join(lines)


def resolve_invocation_log_path(args) -> Optional[str]:
    """Where the per-sandbox invocation record goes (`UX-80`).

    The correlation that recovers real element names (`UX-56`/`UX-64`)
    needs two artifacts: the invocation record, and the Plane 1 wrapped
    log whose wall-clock timestamps the invocations are matched against.
    It used to run only when *both* flags were passed explicitly — and
    `--invocation-log` appeared **zero times** in `README.md`,
    `docs/guides/cli.md` and `docs/guides/real-project.md`, while the CI workflow
    that produced every number those documents quote did pass it.

    So the documented capture command could not produce the documented
    join on any project that overrides `build-root` — which includes
    `freedesktop-sdk`, the project the guide is written from. It was
    invisible on every example in this repository because they all use
    the default layout, where the path-convention fallback happens to be
    right.

    There is no scenario in which a user asks for the Plane 1 log and
    does *not* want the join, so `--wrapped-log` now implies the record;
    it goes to a temporary path unless one is named, because its value is
    the correlation rather than the file. `--no-invocation-log` restores
    the old behaviour for anyone who needs to reproduce it.
    """
    if getattr(args, "invocation_log", None):
        return args.invocation_log
    if getattr(args, "no_invocation_log", False) or not getattr(args, "wrapped_log", None):
        return None
    return os.path.join(
        tempfile.mkdtemp(prefix="bst-native-invocations-"), "invocations.jsonl"
    )



def _spine_policy(flag: str):
    """`--trace-spine`'s three values, as `run_traced_build` wants them.

    `False`/`True` rather than `"off"`/`"on"` so every existing caller
    and test that passes a bool keeps working unchanged - the flag grew a
    third value, which is not a reason to churn the two already there.
    """
    return {"off": False, "on": True, "auto": "auto"}[flag]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run a real bst command under the tracer and report on it")
    run_parser.add_argument("project_dir", help="cwd for the wrapped command (the BuildStream project directory)")
    run_parser.add_argument("output", help="Path to write the JSON report to")
    run_parser.add_argument("--raw-log", help="Also keep the raw trace log at this path (default: discarded after parsing)")
    run_parser.add_argument(
        "--invocation-log", metavar="PATH",
        help="UX-56: where to write the per-sandbox invocation record used to "
             "recover element names when the project overrides build-root. "
             "Correlation also needs --wrapped-log, whose wall-clock timestamps "
             "are what the invocations are matched against. UX-80: recorded to a "
             "temporary path automatically whenever --wrapped-log is given, so "
             "the documented capture produces a joinable report; pass this only "
             "to keep the artifact.",
    )
    run_parser.add_argument(
        "--no-invocation-log", action="store_true",
        help="UX-80: opt out of the automatic invocation record. Only useful to "
             "reproduce the pre-UX-80 behaviour - without it, element attribution "
             "falls back to the sandbox path convention, which is the element "
             "only on a project that does not override build-root.",
    )
    run_parser.add_argument(
        "--argv-log", metavar="PATH",
        help="UX-58: record the first few bwrap command lines BuildStream "
             "generates, before this tool rewrites them, as JSON lines. The "
             "artifact UX-56 needs to identify an authoritative element name; "
             "bounded (BST_TRACE_ARGV_MAX, default 32) because a real build "
             "spawns thousands and a handful answers the question.",
    )
    run_parser.add_argument(
        "--trace-opens", action="store_true",
        help="UX-46: also record which files each element's sandbox opened, and "
             "report declared build dependencies it never read. Opt-in: unlike the "
             "lifecycle hooks this interposes open()/openat() on a hot path.",
    )
    run_parser.add_argument(
        "--trace-spine", nargs="?", const="on", default="off",
        choices=("off", "on", "auto"),
        help="UX-106: also run a ptrace process-event spine inside the sandbox, "
             "which sees statically-linked processes the LD_PRELOAD hook "
             "structurally cannot. The hook stays on either way, since it is the "
             "only source of opened paths. "
             "`auto` (UX-113) traces only the elements the pre-build census says "
             "the hook is blind for, plus any it could not assess - on an "
             "all-dynamic project that is no elements at all, and on a busybox "
             "one it is all of them. Bare `--trace-spine` means `on`.",
    )
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
    report_parser.add_argument(
        "--project-dir",
        help="UX-46: the BuildStream project this trace came from. Required for the "
             "declared-vs-used dependency analysis, which reads each dependency's "
             "artifact contents via `bst artifact list-contents`.",
    )

    # UX-105 item 3: the census, standalone. It reads files on disk and
    # runs nothing, so it answers "what can Plane 2 not see here?"
    # against an already-staged project without a build - which is when
    # a reader most wants to know.
    census_parser = subparsers.add_parser(
        "census",
        help="Classify a project's staged executables as static or dynamic (UX-105)",
    )
    census_parser.add_argument(
        "project_dir",
        help="A BuildStream project directory. Its elements' `local` sources are "
             "scanned; nothing is built and BuildStream is not invoked.",
    )
    census_parser.add_argument(
        "--json", action="store_true", help="Emit JSON instead of a summary",
    )

    args = parser.parse_args()

    if args.command == "census":
        elements_dir = os.path.join(args.project_dir, "elements")
        if not os.path.isdir(elements_dir):
            print(f"Error: no elements/ directory under {args.project_dir}",
                  file=sys.stderr)
            return 1
        elements = sorted(
            name for name in os.listdir(elements_dir) if name.endswith(".bst")
        )
        census = census_project(args.project_dir, elements)
        if args.json:
            print(json.dumps(census, indent=2))
            return 0
        print(_format_census_text(census))
        return 0

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
        invocation_log_path = resolve_invocation_log_path(args)
        try:
            returncode = run_traced_build(args.project_dir, cmd, raw_log_path,
                                          wrapped_log_path=args.wrapped_log,
                                          trace_opens=args.trace_opens,
                                          argv_log_path=args.argv_log,
                                          invocation_log_path=invocation_log_path,
                                          trace_spine=_spine_policy(args.trace_spine))
        except TraceError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

        report = load_and_summarize(raw_log_path, project_dir=args.project_dir,
                                    invocation_log_path=invocation_log_path,
                                    plane1_log_path=args.wrapped_log)
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
        # UX-105: a re-render with a project directory can still census
        # it - the census reads files on disk and runs nothing, so it is
        # available to a saved report exactly as it is to a fresh one.
        # Without this, re-rendering fell back to the generic footnote
        # on a project the census can answer for, which is the same
        # "fires identically whatever the truth is" problem one level up.
        if args.project_dir and "static_census" not in saved:
            elements_dir = os.path.join(args.project_dir, "elements")
            if os.path.isdir(elements_dir):
                elements = sorted(
                    name for name in os.listdir(elements_dir) if name.endswith(".bst")
                )
                if elements:
                    saved["static_census"] = census_project(args.project_dir, elements)
        print(json.dumps(saved, indent=2) if args.json else _format_text(saved))
        return 0
    try:
        report = load_and_summarize(args.path, project_dir=args.project_dir)
    except (FileNotFoundError, TraceError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2) if args.json else _format_text(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
