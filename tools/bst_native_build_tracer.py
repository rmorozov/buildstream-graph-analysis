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

HELP = """Trace what runs *inside* each element's sandbox (Plane 2).

A BuildStream log records one START/SUCCESS pair per element, so a
`make -j8`'s own parallelism is invisible from outside. This runs a real
`bst` command with an LD_PRELOAD hook and a PATH-shadowed `bwrap` shim and
reports the per-process picture: who ran, for how long, at what concurrency.

Full background: docs/backlog/scenarios/UX-0011-native-build-system-profiler-tool.md
"""
import argparse
import array
import atexit
import contextlib
import errno
import gzip
import itertools
import json
import os
import re
import platform
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
import threading
import time
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple


from bga import progress
# `UX-297`: the report's contract, owned by the module that describes the
# shape rather than by the writer - which is how `bga.contracts` finds it.
from bga.plane2 import SCHEMA as PLANE2_SCHEMA
from .bst_run_wrapped import run_wrapped, shutdown_build_group
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
    filename, not where it lives.

    UX-147: the shebang is rewritten to this interpreter's absolute path.
    It shipped as `#!/usr/bin/env python3`, which makes the exec depend
    on the PATH of whatever process `buildbox-run` hands the sandbox -
    and if that PATH has no `python3`, the exec fails inside a layer that
    reports only `returncode 1`. `sys.executable` is the interpreter
    already running this capture, so there is no lookup left to fail.
    """
    real_bwrap = shutil.which("bwrap")
    if real_bwrap is None:
        raise TraceError("no real bwrap found on PATH - required for the shim to fall back to")
    write_bwrap_shim(shim_dir)
    return real_bwrap


def write_bwrap_shim(shim_dir: str) -> str:
    """Materialize the shim as `<shim_dir>/bwrap`, executable.

    Split out of `install_bwrap_shim` (`UX-147` follow-up): resolving the
    *real* bwrap and writing the shim are two different things, and only
    the first needs bubblewrap installed. The tests for what this file
    contains - an absolute shebang, an exec that answers its own probe, a
    fall-through when the environment is missing - are about this half,
    and requiring a bwrap binary made all four fail in the one CI matrix
    that has none, which is exactly where they most needed to run.
    """
    shim_path = os.path.join(shim_dir, "bwrap")
    with open(_bwrap_shim_source, "r", encoding="utf-8") as handle:
        source = handle.read()
    if source.startswith("#!"):
        source = f"#!{sys.executable}\n" + source.split("\n", 1)[1]
    with open(shim_path, "w", encoding="utf-8") as handle:
        handle.write(source)
    st = os.stat(shim_path)
    os.chmod(shim_path, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return shim_path


class CaptureInterrupted(TraceError):
    """The user stopped the capture; whatever was traced was kept.

    `UX-157`. A distinct class rather than a return code because the
    caller has a different job in this case - salvage and say so - and
    because `130` arriving as an ordinary exit status is exactly how
    an interrupt got mistaken for a build failure before.
    """


class ScratchError(TraceError):
    """`.bga/tmp` could not be created, and no fallback was usable."""


@contextlib.contextmanager
def capture_scratch(project_dir: str, prefix: str):
    """A temporary directory under the project's `.bga/tmp`, removed after.

    UX-155, filed from a real report: this used to be
    `tempfile.TemporaryDirectory()`, so the shim, `hook.so` and the
    spine landed wherever `TMPDIR` pointed - and the shim has to be
    *executed* from there. On a machine whose temp mount is `noexec`
    that fails inside `buildbox-run`, where the error is swallowed.

    `TMPDIR` is the wrong knob to reach for, in both directions. It is
    inherited by every service `bst` starts, so changing it to suit one
    directory bga owns also reconfigures `buildbox-casd` and the
    sandbox. The user who reported this was told by our own error text
    to set it, set it to a *relative* path, and got

        error in mkdtemp, errno: no such file or directory

    out of `buildbox-casd` - because Python's `tempfile` treats an
    unusable `TMPDIR` as a candidate and silently falls back, while the
    C++ `mkdtemp` underneath takes it literally after the daemon has
    `chdir`'d away.

    So: bga's scratch goes where bga's other state already goes. The
    fallback to `TMPDIR` remains for a project directory that cannot be
    written to, but it is now the exception and it announces itself,
    rather than being the default nobody could see.
    """
    from bga.run_store import ensure_store_ignored, scratch_dir

    root = scratch_dir(project_dir)
    try:
        os.makedirs(root, exist_ok=True)
        ensure_store_ignored(project_dir)
        tmp = tempfile.mkdtemp(prefix=prefix, dir=root)
    except OSError as error:
        try:
            tmp = tempfile.mkdtemp(prefix=prefix)
        except OSError as fallback_error:
            raise ScratchError(
                f"could not create a scratch directory in {root} "
                f"({error.strerror}) and the fallback to the system temp "
                f"directory failed too ({fallback_error.strerror})."
            ) from fallback_error
        print(
            f"Note: {root} is not writable ({error.strerror}); using {tmp} "
            f"instead. bga executes a shim from this directory, so a noexec "
            f"mount here will fail the capture inside the sandbox layer.",
            file=sys.stderr,
        )
    try:
        yield tmp
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def scratch_mkdtemp(project_dir: str, prefix: str) -> str:
    """A scratch directory that has to outlive its `with` block.

    UX-155's other half. `run`'s unnamed intermediates - the raw trace
    log, the Plane 1 log written only to be parsed, the invocation
    record - are read at several points across `main` and so cannot sit
    in a context manager without wrapping the whole command in one.
    They went to `tempfile.mkdtemp()` and were never removed at all,
    which put them in `TMPDIR` *and* left them there.

    Same directory as everything else bga owns, removed at exit. The
    `atexit` hook is what buys the second half without re-shaping
    `main` around a stack of context managers whose only job is
    deletion.
    """
    root = scratch_dir_or_fallback(project_dir) if project_dir else None
    tmp = tempfile.mkdtemp(prefix=prefix, dir=root)
    atexit.register(shutil.rmtree, tmp, ignore_errors=True)
    return tmp


def scratch_dir_or_fallback(project_dir: str) -> Optional[str]:
    """`<project>/.bga/tmp`, or `None` meaning "let tempfile decide".

    `None` rather than a raise: a scratch directory bga cannot create is
    a reason to fall back, not a reason to refuse to capture. The one
    place that genuinely needs the directory to be executable
    (`capture_scratch`) says so when it falls back; these callers write
    data files and do not care.
    """
    from bga.run_store import ensure_store_ignored, scratch_dir

    root = scratch_dir(project_dir)
    try:
        os.makedirs(root, exist_ok=True)
        ensure_store_ignored(project_dir)
    except OSError:
        return None
    return root


def absolute_tmpdir_env(env: Dict[str, str]) -> Dict[str, str]:
    """Make an inherited relative `TMPDIR` absolute before `bst` sees it.

    UX-155. Python tolerates a relative `TMPDIR` - `tempfile` treats it
    as one candidate among several and falls back when it is not usable
    from the current directory. `buildbox-casd` does not: it is C++, it
    `chdir`s, and its `mkdtemp` fails with `ENOENT` on a path that was
    only ever meaningful relative to the directory the user typed it in.

    That asymmetry is invisible from the outside - bga appears to accept
    the setting, and the build dies several layers down with an error
    that names neither `TMPDIR` nor bga. Resolving it here costs nothing
    and means the value every process in the build sees is the one the
    user meant.
    """
    value = env.get("TMPDIR")
    if not value or os.path.isabs(value):
        return env
    resolved = os.path.abspath(value)
    env["TMPDIR"] = resolved
    print(
        f"Note: TMPDIR was set to the relative path {value!r}; using {resolved} "
        f"instead. BuildStream's helper daemons resolve it after changing "
        f"directory - `buildbox-casd` runs from the cache directory - where a "
        f"relative value fails as `mkdtemp, errno: no such file or directory`.",
        file=sys.stderr,
    )
    return env


def normalize_tmpdir() -> None:
    """Fix a relative `TMPDIR` in this process, so every child inherits it.

    UX-155. Doing this to the child `env` dict alone was not enough, and
    the measurement that showed it is worth keeping: a wrapper on
    `buildbox-casd` recording its own environment logged **two** casd
    starts per capture,

        casd TMPDIR=/tmp/ux155/p6/.bga_tmp cwd=/tmp/ux155/p6
        casd TMPDIR=/tmp/ux155/p6/.bga_tmp cwd=/root/.cache/buildstream
        casd TMPDIR=.bga_tmp              cwd=/tmp/ux155/p6
        casd TMPDIR=.bga_tmp              cwd=/root/.cache/buildstream

    - the traced build with the corrected value, and a second `bst` with
    the raw one, because it spawns from `os.environ` and never saw the
    fixed dict. Measured, that second one is `bst show`, run by
    `extract_run` to build the run directory after the build; the census
    and the `--diagnose` fingerprint probe shell out the same way. The
    `cwd` column is the mechanism: casd really does run from the cache
    directory, so a path that was only ever meaningful in the project
    directory is gone by the time it resolves.

    With the call removed, the capture still traced all nine sandboxes
    and then failed at extraction with
    `bst show failed (exit 255) ... buildbox-casd process died` - which
    is why fixing only the build's environment looked like it worked.

    Assigning through `os.environ` calls `putenv`, so this reaches every
    subsequent child however it is spawned - which is the property the
    per-call dict could not have.
    """
    absolute_tmpdir_env(os.environ)


def probe_bwrap_shim(shim_path: str) -> None:
    """Exec the installed shim once, here, before the build starts.

    UX-147 item 1: three different environment faults - a `noexec`
    temp mount, an AppArmor denial on executing from `/tmp`, an
    interpreter the sandbox layer cannot find - all fail this exec
    *inside* `buildbox-run`, which reports `returncode 1` with the
    stderr swallowed. The capture then finishes with an empty
    diagnostics record and a summary calling the build unmodified.

    Ten milliseconds here turns all three into one sentence with the
    real errno, before an hour of build.
    """
    from .native_trace.bwrap_shim import SELF_TEST_ARGV

    try:
        result = subprocess.run([shim_path, SELF_TEST_ARGV],
                                capture_output=True, text=True, timeout=120)
    except OSError as error:
        if error.errno == errno.ENOENT:
            # Either the shim or the interpreter its shebang names. Both
            # are bga's own doing, and neither is the user's TMPDIR.
            raise TraceError(
                f"the bwrap shim at {shim_path} could not be run: {error.strerror}. "
                f"Either it was not installed or the interpreter its first line "
                f"names is gone - both are bga bugs; please report this."
            ) from error
        raise TraceError(
            f"the bwrap shim at {shim_path} cannot be executed "
            f"({error.strerror}). That is the filesystem it sits on, not bga: a "
            f"noexec mount or an AppArmor rule on executing from it will fail "
            f"the same way inside the sandbox layer, where the error is "
            f"swallowed. bga writes this shim under the project's `.bga/tmp` "
            f"(UX-155), so mounting the project - or wherever `--run-dir` "
            f"points - with exec permitted is what fixes it. Do not reach for "
            f"TMPDIR: `bst` starts helper daemons that inherit it, and this "
            f"error text used to say otherwise."
        ) from error
    if result.returncode != 0 or "bga-shim-ok" not in result.stdout:
        raise TraceError(
            f"the bwrap shim at {shim_path} ran but did not answer its own probe "
            f"(exit {result.returncode}). stderr: {result.stderr.strip()[:400]}"
        )


def read_scalar_key(path: str, key: str) -> Optional[str]:
    """One top-level scalar out of a YAML-ish config, tolerantly.

    `UX-162` item 4 wrote this for `element-path:` and `UX-166` found the
    same naive `startswith` had been copied for `cachedir:` - the same
    lesson, the next key. One implementation, so the third key does not
    repeat it: indentation, quoting and trailing comments are all
    tolerated, because a config that BuildStream reads and bga does not
    is a silent wrong answer.

    Read textually rather than with a YAML parser, for the reason the
    rest of this file does: it has to work against a project whose
    plugins are not installed and without importing BuildStream.
    """
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped.startswith(key + ":"):
                    continue
                value = stripped.split(":", 1)[1].strip()
                value = value.split("#", 1)[0].strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                    value = value[1:-1]
                return value or None
    except OSError:
        pass
    return None


def element_path(project_dir: str) -> str:
    """The project's declared `element-path`, or BuildStream's default.

    UX-142 taught doctor's load probe to read this; UX-153 found the same
    assumption surviving in seven places here, where it costs something:
    `bga snapshot` defaults to `--trace-spine=auto`, and a census that
    finds no elements reports every element as unassessed - so the
    fail-safe traces *everything*, silently at full spine price, on
    exactly the nonstandard-layout projects UX-142 was filed for.

    Read straight out of `project.conf` rather than through BuildStream,
    for the same reason `read_declared_build_deps` is: this has to work
    on a project whose plugins are not installed.
    """
    return read_scalar_key(os.path.join(project_dir, "project.conf"),
                           "element-path") or "elements"


CASD_NAME = "buildbox-casd"


def buildstream_cache_dir() -> str:
    """The cache directory `bst` will use, resolved the way `bst` does.

    `UX-161`. `XDG_CACHE_HOME` if set, else `~/.cache`, plus
    `buildstream` - and a `cachedir` in the user configuration wins over
    both, which is how anyone with a large project moves the cache off
    the root filesystem. Read textually for the same reason
    `element_path` is: this has to work without importing BuildStream.
    """
    config_home = (os.environ.get("XDG_CONFIG_HOME")
                   or os.path.expanduser("~/.config"))
    # UX-166: bst 2.x tries `buildstream2.conf` *first* and falls back to
    # `buildstream.conf` (`buildstream/_context.py`, confirmed in the
    # installed source). Reading only the second pointed this check at
    # the wrong directory for anyone following bst's own docs - a silent
    # false negative on the real daemon, or a false positive against one
    # sitting on the XDG default.
    # UX-177 item 2: the *file* is selected by existence, and the search
    # stops there - which is what bst does. Falling through on a missing
    # *key* instead would read `cachedir` out of `buildstream.conf` when
    # bst is using a `buildstream2.conf` that simply does not set one,
    # and answer a directory bst is not using.
    for name in ("buildstream2.conf", "buildstream.conf"):
        path = os.path.join(config_home, name)
        if not os.path.exists(path):
            continue
        value = read_scalar_key(path, "cachedir")
        if value:
            return os.path.abspath(os.path.expanduser(value))
        break
    base = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    return os.path.join(os.path.abspath(base), "buildstream")


def _process_start_age(pid: str, proc_root: str = "/proc") -> Optional[float]:
    """How many seconds ago this process started, or `None`.

    From `/proc/<pid>/stat` field 22 against `/proc/uptime`, which is
    the canonical answer. The `)` split is because a process name can
    itself contain spaces and parentheses.
    """
    try:
        with open(f"{proc_root}/{pid}/stat", "r", encoding="utf-8") as handle:
            fields = handle.read().rsplit(")", 1)[1].split()
        started_ticks = int(fields[19])
        uptime = float(
            open(f"{proc_root}/uptime", encoding="utf-8").read().split()[0])
        return uptime - started_ticks / os.sysconf("SC_CLK_TCK")
    except (OSError, ValueError, IndexError):
        return None


def detect_stale_casd(cache_dir: Optional[str] = None,
                      proc_root: str = "/proc") -> List[dict]:
    """Running `buildbox-casd` processes already serving this cache.

    `UX-161`, completing `UX-147`'s deferred item 2. A `casd` started
    before the capture was started by a `bst` that never saw the
    capture's `PATH`, so a build that reuses it can miss the shim
    entirely - and that produces a zero-invocation capture whose summary
    could previously only list it as one of three guesses, after the
    build.

    Detection is evidence-shaped and deliberately not clever: `casd`
    takes the cache directory as its last argument (measured -
    `... --jobs=16 /tmp/x/cache/buildstream`), so a process named
    `buildbox-casd` carrying this build's cache directory is one that
    would be reused. What it does *not* claim is that reuse definitely
    bypasses the shim on every `bst` version; `UX-147`'s caution stands
    and the wording stays "this is running", not "this is your bug".

    `proc_root` is a test seam. Nothing in production passes it, and a
    process's `comm` cannot be faked any other way - the alternative
    was to leave these matching rules unguarded.
    """
    cache_dir = os.path.normpath(os.path.abspath(
        cache_dir or buildstream_cache_dir()))
    found = []
    try:
        pids = [name for name in os.listdir(proc_root) if name.isdigit()]
    except OSError:
        return []
    for pid in pids:
        try:
            with open(f"{proc_root}/{pid}/comm", "r", encoding="utf-8") as handle:
                if handle.read().strip() != CASD_NAME:
                    continue
            with open(f"{proc_root}/{pid}/cmdline", "rb") as handle:
                argv = [part.decode("utf-8", "replace")
                        for part in handle.read().split(b"\0") if part]
        except OSError:
            continue  # it exited while we looked; that is not staleness
        # UX-166: `abspath` on the daemon's argv resolved relative paths
        # against *bga's* cwd, not the daemon's - a different directory,
        # and a match derived from it would be a coincidence. A daemon
        # started with a relative cache path is unmatchable evidence, so
        # it is skipped rather than guessed at.
        # `normpath`, not `abspath`: normalising an *absolute* path is
        # unambiguous, while resolving a relative one uses bga's cwd
        # rather than the daemon's - a different directory, so a match
        # derived from it would be a coincidence.
        if not any(os.path.normpath(arg) == cache_dir for arg in argv
                   if arg.startswith("/")):
            continue
        found.append({"pid": int(pid),
                      "age_s": _process_start_age(pid, proc_root),
                      "cache_dir": cache_dir})
    return sorted(found, key=lambda entry: entry["pid"])


def format_stale_casd_warning(found: List[dict]) -> Optional[str]:
    """The up-front warning, or `None` when there is nothing to say.

    Silent on a quiet machine is a requirement, not an oversight: a
    warning that fires on every capture is one nobody reads by the
    third.
    """
    if not found:
        return None
    lines = []
    for entry in found:
        age = entry["age_s"]
        when = f", started {age / 60:.0f}m ago" if age and age >= 60 else (
            f", started {age:.0f}s ago" if age else "")
        lines.append(
            f"Warning: a {CASD_NAME} serving {entry['cache_dir']} was already "
            f"running when this capture started (pid {entry['pid']}{when}). It "
            f"was started by a `bst` that never saw this capture's PATH, so a "
            f"build that reuses it can miss the shim entirely and capture "
            f"nothing. Stop it first - `bst shutdown`, or `kill "
            f"{entry['pid']}` - and `bst` will start a fresh one."
        )
    return "\n".join(lines)


def discover_element_names(project_dir: str) -> List[str]:
    """Every element in the project, by the name BuildStream calls it.

    `UX-160`. Discovery was `os.listdir(...).endswith(".bst")` in four
    places here and one in doctor - non-recursive, every one of them.
    Every example in this repository keeps its elements at the top of
    the element directory, so every test passed; essentially every real
    project nests them (`elements/components/foo.bst` is
    freedesktop-sdk's whole layout), and there the census assessed
    nothing below the top level.

    The bill lands through `UX-113`'s fail-safe: an unassessed element
    is traced. With most elements unassessed, `--trace-spine=auto` -
    snapshot's default - quietly becomes `--trace-spine=on` for the
    whole build, at a per-process ptrace cost `UX-108` has still never
    measured on a real workload.

    Names are project-relative with `/` separators, which is what
    BuildStream calls them, what Plane 1 records, and - since `UX-160`
    also fixed the shim's recovery - what the shim reports per sandbox.
    That agreement is the point: a census keyed differently from the
    lookups is a census nobody reads.

    This is `UX-142`'s lesson one directory deeper, and `UX-153`'s left
    half: that item routed *which* directory through `element_path()`
    and left *how it is walked* alone.
    """
    root = elements_dir_for(project_dir)
    if not os.path.isdir(root):
        return []
    names = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for filename in filenames:
            if filename.endswith(".bst"):
                names.append(os.path.relpath(os.path.join(dirpath, filename), root))
    return sorted(names)


def elements_dir_for(project_dir: str) -> str:
    return os.path.join(project_dir, element_path(project_dir))


#: How often the host is sampled while the build runs. One sample costs
#: 37 microseconds (measured: 1,000 reads of both files in 0.037 s), so
#: the interval is set by how fast the thing being watched moves rather
#: than by cost - memory pressure builds over seconds, and a 2-second
#: series over a four-hour build is 7,200 lines.
HOST_SAMPLE_INTERVAL_S = 2.0

HOST_SAMPLES_SCHEMA = "host-samples/v1"

#: `/proc/meminfo` keys kept, and the name each takes. Everything here
#: is in kB as that file reports it; the reader converts.
_MEMINFO_KEYS = {
    "MemTotal": "mem_total_kb",
    "MemFree": "mem_free_kb",
    "MemAvailable": "mem_available_kb",
    "Cached": "cached_kb",
    "SwapTotal": "swap_total_kb",
    "SwapFree": "swap_free_kb",
}

#: `/proc/vmstat` counters kept. All three are monotonic totals since
#: boot, so a reader takes differences; publishing the raw value keeps
#: that decision with the reader rather than baking a window in here.
_VMSTAT_KEYS = ("pgmajfault", "pswpin", "pswpout")


def read_host_sample() -> dict:
    """One reading of what the host's memory is doing.

    `UX-378`. Everything bga said about swapping - and it says it in
    four separate places - was a model over `host_memory_mb` and a sum
    of per-process peaks. This is the measurement.
    """
    sample = {}
    try:
        with open("/proc/meminfo", "r") as handle:
            for line in handle:
                key, _, rest = line.partition(":")
                name = _MEMINFO_KEYS.get(key)
                if name:
                    sample[name] = int(rest.split()[0])
    except (OSError, ValueError, IndexError):
        return {}
    try:
        with open("/proc/vmstat", "r") as handle:
            for line in handle:
                key, _, value = line.partition(" ")
                if key in _VMSTAT_KEYS:
                    sample[key] = int(value)
    except (OSError, ValueError):
        pass
    return sample


class HostSampler:
    """A background thread writing one JSON object per sample.

    **The clock is the trace's own.** `hook.c` stamps every record with
    `clock_gettime(CLOCK_MONOTONIC)` and `time.monotonic()` is the same
    clock on Linux, so a sample and a process record can be put on one
    timeline without an offset - which is the whole point, because the
    question is *how many processes were alive when the memory ran out*.

    **JSON Lines, flushed per sample**, for `UX-157`'s reason: a capture
    killed partway keeps every sample it had taken, and the file a
    reader gets is the file that was being written.

    Best-effort throughout. A host with no `/proc/meminfo` writes a
    header saying so and no samples; nothing here may change whether the
    build itself succeeds.
    """

    def __init__(self, path: str, interval_s: float = HOST_SAMPLE_INTERVAL_S):
        self.path = path
        self.interval_s = interval_s
        self._stop = threading.Event()
        self._thread = None
        self._handle = None
        self.samples = 0

    def __enter__(self):
        try:
            self._handle = open(self.path, "w", encoding="utf-8")
        except OSError:
            return self
        first = read_host_sample()
        header = {
            "schema": HOST_SAMPLES_SCHEMA,
            "interval_s": self.interval_s,
            "clock": "CLOCK_MONOTONIC",
            # The pair that puts this series on a wall clock, the same
            # way `UX-185`'s `bga-clocks` line does for the build.
            "wall_at_start": time.time(),
            "monotonic_at_start": time.monotonic(),
            "mem_total_kb": first.get("mem_total_kb"),
            "swap_total_kb": first.get("swap_total_kb"),
            # Named rather than inferred from an empty file: "this host
            # exposes no /proc/meminfo" and "the build was too short to
            # sample" are different facts.
            "available": bool(first),
        }
        self._write(header)
        if first:
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
        return self

    def __exit__(self, *exc):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=self.interval_s + 1.0)
        if self._handle is not None:
            try:
                self._handle.close()
            except OSError:
                pass
        return False

    def _write(self, row: dict) -> None:
        if self._handle is None:
            return
        try:
            self._handle.write(json.dumps(row, separators=(",", ":")) + "\n")
            self._handle.flush()
        except (OSError, ValueError):
            pass

    def _run(self) -> None:
        while not self._stop.is_set():
            sample = read_host_sample()
            if sample:
                sample["t"] = round(time.monotonic(), 3)
                # `mem_total_kb` is in the header and does not move.
                sample.pop("mem_total_kb", None)
                sample.pop("swap_total_kb", None)
                self._write(sample)
                self.samples += 1
            self._stop.wait(self.interval_s)


def read_host_samples(path: str) -> dict:
    """A written series back, as `{header, samples}`.

    Tolerates a truncated last line, which is what an interrupted
    capture leaves.
    """
    header, samples = {}, []
    try:
        with open(path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if row.get("schema") == HOST_SAMPLES_SCHEMA:
                    header = row
                else:
                    samples.append(row)
    except OSError:
        return {"header": {}, "samples": []}
    return {"header": header, "samples": samples}


def run_traced_build(project_dir: str, cmd: List[str], raw_log_path: str, wrapped_log_path: Optional[str] = None, trace_opens: bool = False, argv_log_path: Optional[str] = None, invocation_log_path: Optional[str] = None,
                     trace_spine=False, diagnostics_path: Optional[str] = None,
                     no_inject: bool = False, inhibit: bool = False,
                     host_samples_path: Optional[str] = None) -> int:
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
    # UX-161: before the build, because after it the same fact is only
    # one of three guesses about a zero-invocation capture.
    stale_casd = detect_stale_casd()
    warning = format_stale_casd_warning(stale_casd)
    if warning:
        print(warning, file=sys.stderr)

    # UX-155: before anything here spawns a process. Correcting only the
    # build's own `env` left every other `bst` bga shells out to - the
    # census, the fingerprint probe, and `extract_run`'s `bst show` - on
    # the broken value.
    normalize_tmpdir()

    open(raw_log_path, "w").close()  # truncate/create up front - the hook only ever appends

    with capture_scratch(project_dir, "trace-") as tmp:
        shim_dir = os.path.join(tmp, "shim")
        bind_dir = os.path.join(tmp, "bind")
        os.makedirs(shim_dir)
        os.makedirs(bind_dir)

        print("Compiling the trace hook...", file=sys.stderr)
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
        # UX-147: after the shim exists, before `bst` runs. (Placed before
        # `install_bwrap_shim` on the first attempt, which probed a file
        # that was not there yet and reported ENOENT as a noexec mount -
        # the error text now tells the two apart rather than assuming.)
        probe_bwrap_shim(os.path.join(shim_dir, "bwrap"))

        env = absolute_tmpdir_env(dict(os.environ))
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
                # UX-159: on a big project this walk plus the declared-deps
                # resolution takes real time, and it used to be silent -
                # so the user could not tell "working" from "hung"
                # between `Capturing into ...` and BuildStream's first
                # line. The rule this follows: any bga-owned step that
                # can plausibly take >5s announces itself.
                print(f"Assessing {len(discover_element_names(project_dir))} "
                      f"element(s) for static binaries...", file=sys.stderr)
                verdicts = census_spine_verdicts(project_dir)
                census_path = os.path.join(shim_dir, "spine-census.json")
                with open(census_path, "w", encoding="utf-8") as handle:
                    json.dump(verdicts, handle, sort_keys=True)
                env["BST_TRACE_SPINE_POLICY"] = "auto"
                env["BST_TRACE_SPINE_CENSUS"] = census_path
                # UX-160 item 3: `auto` silently becoming `on` is the
                # expensive outcome, and it used to produce no output at
                # all. One line, before the build, so the price is at
                # least visible when it is being paid.
                print(format_census_coverage(
                          project_dir, verdicts,
                          getattr(census_spine_verdicts,
                                  "last_unassessable", None)),
                      file=sys.stderr)
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

        # UX-146: what the shim received and what it exec'd, per
        # invocation. Written on the host side into the same temporary
        # directory the shim already owns, and copied out afterwards, so
        # a build that dies mid-way still leaves the record.
        captured_diagnostics = os.path.join(bind_dir, "capture-diagnostics.jsonl")
        if diagnostics_path is not None:
            env["BST_TRACE_DIAGNOSTICS"] = captured_diagnostics
            # UX-151: once per capture, as the record's first line - what
            # the argvs below should be parsed *against*.
            with open(captured_diagnostics, "w", encoding="utf-8") as handle:
                fingerprint = capture_fingerprint()
                # UX-161: pid and age, so "was a daemon already running?"
                # is answerable from the record the user sends on rather
                # than from memory of what they typed that afternoon.
                fingerprint["stale_casd"] = stale_casd
                handle.write(json.dumps(fingerprint, sort_keys=True) + "\n")
        else:
            env.pop("BST_TRACE_DIAGNOSTICS", None)
        if no_inject:
            env["BST_TRACE_NO_INJECT"] = "1"
        else:
            env.pop("BST_TRACE_NO_INJECT", None)

        def copy_out():
            """Move everything the shim wrote out of the scratch.

            UX-157: this is in a `finally` because the scratch is deleted
            on the way out of `capture_scratch`, and until UX-157 an
            interrupt skipped straight past these copies to that
            deletion. On a three-hour build that threw away three hours
            of trace that were already on disk - and interruption is the
            *common* way a long build ends, far more so than the
            mid-build failure the original comment had in mind.
            """
            captured_log = os.path.join(bind_dir, "trace.log")
            if os.path.exists(captured_log):
                shutil.copyfile(captured_log, raw_log_path)
            if argv_log_path is not None and os.path.exists(captured_argv):
                shutil.copyfile(captured_argv, argv_log_path)
            if diagnostics_path is not None:
                # Created empty when the shim never ran, deliberately:
                # zero invocations is this file's most important reading,
                # and an absent file reads as "the flag did not work".
                if os.path.exists(captured_diagnostics):
                    shutil.copyfile(captured_diagnostics, diagnostics_path)
                else:
                    open(diagnostics_path, "w").close()
                # UX-148: the per-invocation stderr the shim tee'd. It is
                # written beside the record *inside the scratch*, which
                # `capture_scratch` deletes - so without this the files
                # exist for the length of the build and are gone by the
                # time anyone reads the summary that points at them.
                captured_stderr = captured_diagnostics + ".stderr"
                if os.path.isdir(captured_stderr):
                    shutil.copytree(captured_stderr,
                                    diagnostics_path + ".stderr",
                                    dirs_exist_ok=True)
            if invocation_log_path is not None and os.path.exists(captured_invocations):
                shutil.copyfile(captured_invocations, invocation_log_path)

        # `UX-378`: the host's own memory, sampled while the build runs.
        # Around the build and nothing else - the census and the shim
        # probe before it are bga's own work, and a series that included
        # them would describe this tool rather than the build.
        sampler = (HostSampler(host_samples_path) if host_samples_path
                   else contextlib.nullcontext())
        try:
            with sampler:
                if wrapped_log_path is not None:
                    with open(wrapped_log_path, "w", encoding="utf-8") as out_f:
                        returncode = run_wrapped(project_dir, cmd, out_f,
                                                 env=env, inhibit=inhibit)
                else:
                    # UX-157: same own-group treatment as the wrapped
                    # path, so an interrupt here cannot orphan the build.
                    proc = subprocess.Popen(cmd, cwd=project_dir, env=env,
                                            start_new_session=True)
                    try:
                        returncode = proc.wait()
                    except BaseException:
                        shutdown_build_group(proc)
                        raise
        except KeyboardInterrupt:
            # The trace is already on disk; `copy_out` in the `finally`
            # below is what saves it. Re-raised as `CaptureInterrupted`
            # so callers can tell "the user stopped this" from "bga
            # crashed" without matching on a signal number.
            raise CaptureInterrupted(
                "the capture was interrupted; the trace captured so far was kept"
            ) from None
        finally:
            copy_out()
        return returncode


_RUSAGE_KEYS = frozenset({"utime", "stime", "cutime", "cstime"})
# UX-63: peak RSS from the same struct rusage. Integers in KiB (Linux),
# not the float seconds the keys above carry, hence a separate set.
# `UX-379`: six more counters out of the same struct. Integers like the
# two above, so they join that set rather than getting a third.
# `inblock`/`oublock` are the kernel's 512-byte block-layer units;
# `_IO_BLOCK_BYTES` is where that is converted, once.
_RUSAGE_INT_KEYS = frozenset({"maxrss_kb", "cmaxrss_kb",
                              "inblock", "oublock", "majflt", "minflt",
                              "nvcsw", "nivcsw"})

#: `ru_inblock`/`ru_oublock` count 512-byte blocks (the kernel divides
#: its byte counters by 512 on the way in), so this recovers bytes.
#: Verified against a 64 MiB file read with a cold page cache: 135,264
#: blocks x 512 = 69,255,168 B, against 67,108,864 B of file plus the
#: reader's own binary and libraries.
_IO_BLOCK_BYTES = 512

#: `UX-379`'s six, in the record's own vocabulary. Named here because
#: three places read the same list - the pairing pass carries them
#: through, `_ResourcePressure` folds them, and `bga timeline` annotates
#: with four of them - and a list written out three times is how a
#: seventh field would reach two of them.
_PRESSURE_FIELDS = ("read_bytes", "written_bytes", "major_faults",
                    "minor_faults", "voluntary_switches",
                    "involuntary_switches")

# UX-57: `part=` is appended by hooks that flush more than one window
# per process, and absent in logs written before that existed - optional
# so one parser reads both.
_OPENS_HEADER_RE = re.compile(
    r"^OPENS pid=(\d+) element=(\S+)(?: inv=(\S+))? unique=(\d+) dropped=(\d+)"
    r"(?: part=(\d+))?$"
)


def parse_open_records(text: str, open_element_overrides: Optional[Dict[str, str]] = None) -> Dict[str, dict]:
    """`parse_open_lines`, over one string instead of an iterable.

    Kept because callers outside the analysis path have a string in hand
    already; the analysis path itself hands over the file (`UX-169`).
    """
    return parse_open_lines(text.splitlines(), open_element_overrides)


def parse_open_lines(lines, open_element_overrides: Optional[Dict[str, str]] = None) -> Dict[str, dict]:
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
    # UX-169: one pass over an iterable, with the block's own `unique`
    # count as the only state - the index-with-lookahead version needed
    # the whole trace as a list of lines, which is the copy the analysis
    # path was trying not to make.
    entry: Optional[dict] = None
    remaining = 0
    for raw in lines:
        # UX-177 item 5: the `\r` too. `splitlines()`, which the
        # string-taking wrappers use, drops it; iterating a handle
        # does not, and a CRLF trace would leave one on every line.
        line = raw.rstrip("\r\n")
        match = _OPENS_HEADER_RE.match(line)
        if match is None:
            if remaining <= 0:
                continue
            if line.startswith(("START ", "END ")):
                # The block was short - the process was killed mid-write.
                # Keep what it managed to say and stop counting.
                remaining = 0
                continue
            remaining -= 1
            if line.startswith("/"):
                entry["paths"].add(line)
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
        # A header arriving mid-block ends the previous one, which the
        # loop above gets for free by testing the header first.
        remaining = int(unique)
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
    return parse_trace_lines(text.splitlines())


def parse_trace_lines(lines, total_lines: Optional[int] = None) -> List[dict]:
    """`parse_trace_log`, over an iterable of lines instead of one string.

    `UX-168`. The caller used to read the whole trace into memory and
    then build the event list beside it - two copies of a file that on a
    multi-hour build is hundreds of MB. Measured on a 62 MB / 800k-event
    trace: 596 MB peak, a ~10x amplification, on the machine that just
    finished the build and in the phase right after it.

    The format is line-oriented, so a file handle is a perfectly good
    argument and the string copy simply need not exist.

    **The list, for the callers that want one.** `UX-297` needed the
    events never to exist all at once, and the parse was always a
    stream - `stream_trace_events` below is that stream, and this is it
    poured into a list. One parser, two shapes: a second copy of this
    loop is exactly the drift `UX-214` and `UX-273` are about.
    """
    return list(stream_trace_events(lines, total_lines))


def stream_trace_events(lines, total_lines: Optional[int] = None):
    """Each trace event as it is parsed, holding none of them.

    `UX-297`'s open half. The measured floor of an extraction was the
    event list itself, not the fold beside it - on a 200,000-process
    trace, 400,000 event dicts are **212.6 MB** of a 340.8 MB peak, and
    pairing them added 1.2 MB net because the records replaced the
    events as they drained. Nothing needed the list; `pair_events`
    needed *order*, which is the next function's problem and not this
    one's.
    """
    # UX-183: a 200k-process trace holds `Analyzing the captured trace...`
    # for minutes. The line count is not known in advance without a
    # second pass over the file, so this counts up rather than toward a
    # total - which is what the user needs anyway: evidence of motion.
    tick = progress.ticker("parsing trace", total=total_lines)
    for index, line in enumerate(lines):
        if not index % 5000:
            tick.step(index)
        line = line.rstrip("\r\n")
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
        # `UX-379`: the three axes the same struct was already carrying.
        # Attached field by field rather than as a set, because a hook
        # built before this wrote none of them and one built after
        # writes all six - and a record with some is a record from a
        # capture that ran out of line buffer, which is a fact to keep
        # rather than a set to discard.
        if "inblock" in rusage:
            record["read_bytes"] = rusage["inblock"] * _IO_BLOCK_BYTES
        if "oublock" in rusage:
            record["written_bytes"] = rusage["oublock"] * _IO_BLOCK_BYTES
        for key, field in (("majflt", "major_faults"),
                           ("minflt", "minor_faults"),
                           ("nvcsw", "voluntary_switches"),
                           ("nivcsw", "involuntary_switches")):
            if key in rusage:
                record[field] = rusage[key]
        yield record
    tick.done()


def _pair_key(ev: dict) -> Tuple[str, int, str]:
    """What makes two records the same process's, for pairing.

    The sandbox (UX-56/UX-61) rather than the element, because pids are
    namespaced per sandbox and a build-root override collapses every
    element to one name; and the mechanism (UX-107), because with the
    spine running each process writes a START and an END from *each*
    stream and a shared key pops one stream's START for the other's END.
    """
    return (ev.get("invocation") or ev["element"], ev["pid"], ev.get("src", "hook"))


def count_unmatched_ends(events: List[dict]) -> Dict[str, int]:
    """ENDs with no START to pair with, split by what they can support.

    `UX-123` counted these as one number and called all of them
    "fork-without-exec children". `UX-133` found that wrong twice over:

    - **Under-counted.** `seen_start` was never cleared, so a pid that
      exec'd, exited, and was then reused by a fork-only child had its
      END matched against the *first* process's START and went
      uncounted. The set now tracks whether a START is currently open,
      exactly as `pair_events` does, so a reused pid is a fresh question.
    - **Mislabelled.** Only the **spine** can produce a fork-only exit:
      `PTRACE_EVENT_EXIT` fires for every tracee whether or not it
      exec'd. The hook is loaded *by* the dynamic linker at exec, so a
      hook END with no START is not a fork-only child at all - it is a
      truncated log, or a START lost to a full buffer. Rendering it as
      "fork-without-exec children, wearing their parent's command line"
      states something that record cannot support.

    Returns `{"fork_only": N, "unmatched": M}` - the first countable, the
    second an honest "we have an exit and no beginning for it".
    """
    open_now = set()
    counts = {"fork_only": 0, "unmatched": 0}
    for ev in sorted(events, key=lambda e: e["ts"]):
        key = _pair_key(ev)
        if ev["event"] == "START":
            open_now.add(key)
        elif ev["event"] == "END":
            if key in open_now:
                open_now.discard(key)
            elif ev.get("src") == "spine":
                counts["fork_only"] += 1
            else:
                counts["unmatched"] += 1
    return counts


def count_fork_only_exits(events: List[dict]) -> int:
    """`UX-123`'s name, kept for its callers; the spine half of the pair
    above. See `count_unmatched_ends` for why the two are not one number.
    """
    return count_unmatched_ends(events)["fork_only"]


def _drain(events: List[dict]):
    """Yield each event and drop the list's own reference to it.

    `UX-169`. Iterating a list and clearing it afterwards keeps every
    event alive until the last record is built; releasing each slot as
    it is read means the two lists never both hold 400,000 dicts.
    """
    for index, event in enumerate(events):
        events[index] = None
        yield event
    del events[:]


def pair_events(events: List[dict], consume: bool = False) -> List[dict]:
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
    duration_us=None rather than a fabricated duration.

    `consume=True` (`UX-169`) sorts `events` in place and empties it as
    it goes, so an event is freed as soon as its record exists instead
    of the whole event list living alongside the whole record list. It
    is destructive, which is why it is opt-in: only the analysis path,
    which drops its reference immediately afterwards, asks for it.
    Measured on a 400k-process trace: 479 MB peak against 545 MB before,
    and the record list is unchanged either way.

    `UX-297`: the algorithm is `stream_records` now, and this is it
    sorted - both the events going in (which is what makes this
    function's answer byte-identical to what it always was) and the
    records coming out. The streaming callers skip the first sort; see
    that function for the ordering property they rely on and the
    measurement behind it."""
    if consume:
        events.sort(key=lambda e: e["ts"])
        ordered = _drain(events)
    else:
        ordered = sorted(events, key=lambda e: e["ts"])
    return sorted(stream_records(ordered), key=lambda r: r["start_ts"])


def stream_records(events, counts: Optional[Dict[str, int]] = None):
    """`pair_events`, as the single pass it can be.

    Yields each record when its END arrives, then the open ones - so a
    caller that folds as it reads never holds the record list either.
    Holds only the processes currently open, which is a build's
    concurrency rather than its size.

    **Why no sort.** Pairing needs one property: that a key's own events
    arrive in order. A global sort is far stronger, and it is what
    forced the event list to exist. A *key* is one process seen through
    one mechanism (`_pair_key`), and one process's own START and END are
    written by one writer in that order - the hook writes both from the
    traced process itself, the spine writes both from the single
    supervisor. Concurrent writers interleave *across* keys, which is
    what breaks the global order and not this one.

    Measured on the two real captures in this repository:

    ```text
                          events   keys   global inv.   per-key inv.
    examples/01 raw           64     40             0              0
    examples/06 plane2.gz   1485    813             2              0
    ```

    `examples/06` is the case: the file is **not** globally ordered and
    **is** per-key ordered, so the weaker property is the one that
    actually holds. `test_the_pairing_pass_streams.py` asserts the two
    entry points agree record-for-record on both, and on a generated
    trace whose global order is deliberately shuffled.

    `counts` is filled as the stream runs with the same keys
    `count_unmatched_ends` returns. It is an argument rather than a
    second walk because after this pass the events are gone - and
    because the open-set it needs is the one this loop already keeps.
    """
    open_by_key: Dict[Tuple[str, int, str], List[dict]] = {}
    if counts is not None:
        counts.setdefault("fork_only", 0)
        counts.setdefault("unmatched", 0)
    # UX-183: the second half of the same wait. A 200k-process trace pairs
    # for as long as it parses, and both sit behind one phase line.
    # The stream yields lazily on purpose, so there is no length to count
    # toward - the ticker then counts up, which is the same signal.
    pair_tick = progress.ticker("pairing processes", total=None)
    for index, ev in enumerate(events, 1):
        if not index % 5000:
            pair_tick.step(index)
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
        key = _pair_key(ev)
        if ev["event"] == "START":
            pending = open_by_key.setdefault(key, [])
            # UX-133: an exec chain and a reused pid look identical in the
            # record stream - both are "another START for a pid that
            # already has one open". `pending.clear()` on the eventual END
            # collapsed *whatever was queued*, so a lost END plus a reused
            # pid fabricated one record spanning two distinct processes,
            # wearing `exec_chain=2` as if it were an ordinary chain.
            #
            # `execve` cannot change a process's parent. So a START whose
            # ppid differs from the open chain's is **proof** of a
            # different process, not a heuristic - and the chain is closed
            # as END-lost rather than merged into.
            #
            # Reuse under the *same* parent stays undecidable from the
            # record stream alone, and is left that way rather than
            # guessed at with a timing threshold: measured on the retained
            # freedesktop-sdk capture, 1859 real exec-chain gaps run from
            # 0.4 ms (median) to 13.9 ms (max), and a `sh -c 'sleep 5;
            # exec …'` is a legitimate chain five seconds wide. Any cut
            # that separates those two populations would be picked to fit
            # this corpus, which is the kind of threshold this codebase
            # does not add.
            if pending and pending[-1].get("ppid") != ev.get("ppid"):
                yield _open_record(pending[0], pending[-1], len(pending),
                                   reason="end-lost-pid-reused")
                pending.clear()
            pending.append(ev)
        elif ev["event"] == "END":
            pending = open_by_key.get(key)
            if not pending:
                # UX-123: an exit for a pid that never exec'd - a
                # fork-without-exec child, whose recorded cmdline is its
                # parent's. Dropped here and counted as it passes, so the
                # report can say how many rather than leaving a whole
                # record class neither shown nor mentioned.
                #
                # UX-297: counted *here* rather than by
                # `count_unmatched_ends` walking a second sorted copy of
                # the events. The split is UX-133's and unchanged: only
                # the spine can see a fork-only exit, so a hook END with
                # no START is a truncated log and says so.
                if counts is not None:
                    if ev.get("src") == "spine":
                        counts["fork_only"] += 1
                    else:
                        counts["unmatched"] += 1
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
            # `UX-379`: the rest of the same struct, carried through
            # pairing on the same rule - omitted rather than zeroed when
            # the hook predates them, because a build that touched no
            # disk and a capture that could not look are different
            # claims.
            for _field in _PRESSURE_FIELDS:
                if _field in ev:
                    record[_field] = ev[_field]
            # UX-106: only the spine has this - the hook's destructor
            # runs before the process has a status, and not at all when
            # it is killed.
            if "exit_status" in ev:
                record["exit_status"] = ev["exit_status"]
            yield record
    for pending in open_by_key.values():
        for start_ev in pending:
            yield _open_record(start_ev, start_ev, 1)
    pair_tick.done()


def _open_record(start_ev: dict, final_ev: dict, exec_chain: int,
                 reason: str = "no-observed-exit") -> dict:
    """A process whose exit was never seen.

    `reason` distinguishes the two ways that happens, because they are
    different facts about the capture: `no-observed-exit` is the ordinary
    one (killed by a signal, or still running when the trace ended), and
    `end-lost-pid-reused` means the pid was handed to a new process
    before this one's END arrived - so the record is deliberately left
    incomplete rather than merged with its successor's (`UX-133`).
    """
    return {
        "pid": start_ev["pid"],
        "ppid": final_ev.get("ppid", start_ev.get("ppid")),
        "element": start_ev["element"],
        "invocation": start_ev.get("invocation"),
        "cmd": final_ev["cmd"],
        "start_ts": start_ev["ts"],
        "end_ts": None,
        "duration_s": None,
        "open": True,
        "open_reason": reason,
        "src": start_ev.get("src", "hook"),
        "exec_chain": exec_chain,
    }


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

#: `UX-375`: how many findings the report carries. Every other
#: population in `plane2/v2` is bounded - `binary_cost` takes a `top_n`
#: of 5, the rest are `O(elements)` or `O(distinct binaries)` - and this
#: one was not, so it was 77-92% of the report on every capture with
#: repeated work in it. Measured at 40 elements: 278,510 B of a 363 kB
#: report, cut to 31,888 B by this cap.
#:
#: 40 rather than a round 10, and the same number as the viewer's
#: `TABLE_OPENS_BOUNDED_ABOVE`: it is what this repository already uses
#: for "more rows than a reader will act on", and the findings are
#: ranked by the figure a reader acts on.
REDUNDANCY_FINDINGS_MAX = 40

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
    state = _RedundantOperations()
    for record in records:
        state.add(record)
    return state.finish()


class _RedundantOperations:
    """`detect_redundant_operations`, one record at a time.

    `UX-297`: a signature's finding needs its element set, its
    occurrence count, the per-element duration sums and the first
    command line seen under it - all of which fold. The occurrences
    themselves were only ever read for those four things, and a real
    build has orders of magnitude fewer distinct signatures than
    processes.
    """

    def __init__(self):
        self.by_signature: Dict[str, dict] = {}
        # Signatures seen under a non-element bucket, so a finding that
        # disappears for lack of a *second* resolved element can be
        # counted rather than silently dropped.
        self.unresolved_signatures: Dict[str, set] = defaultdict(set)
        self.excluded_command_blocks = 0

    def add(self, r):
        if r["open"] or r["element"] == "unknown":
            return
        if _is_element_command_block(r):
            self.excluded_command_blocks += 1
            return
        if not _is_element_name(r["element"]):
            self.unresolved_signatures[
                normalize_cmd_signature(r["cmd"])].add(r["element"])
            return
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
            return
        signature = normalize_cmd_signature(r["cmd"])
        entry = self.by_signature.get(signature)
        if entry is None:
            # A four-slot list, not a dict of four keys. Most signatures
            # on a real capture occur once - a compile of one file -
            # and a per-signature dict costs several times what the
            # record it replaced did, which turns a memory fix into a
            # memory regression at the scale this item is about.
            entry = self.by_signature[signature] = [0, 0.0, r["cmd"], {}]
        entry[0] += 1
        entry[1] += r["duration_s"]
        per_element = entry[3]
        per_element[r["element"]] = per_element.get(
            r["element"], 0.0) + r["duration_s"]

    def finish(self):
        by_signature = self.by_signature
        unresolved_signatures = self.unresolved_signatures
        excluded_command_blocks = self.excluded_command_blocks
        findings = []
        excluded_unresolved_only = 0
        for signature, occurrence in by_signature.items():
            count, total_duration_s, example_cmd, per_element_duration = occurrence
            elements = sorted(per_element_duration)
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
            worst_element = max(per_element_duration,
                                key=lambda e: per_element_duration[e])
            findings.append({
                "signature": signature,
                "elements": elements,
                # `UX-375`: the count beside the list. `correlate` reads
                # `worst_element` and the durations and never the list,
                # so this is what a consumer actually wants - and it is
                # the number that stays true when the list is one day
                # bounded (which needs a contract bump; see the item).
                "element_count": len(elements),
                "occurrence_count": count,
                "total_duration_s": total_duration_s,
                # UX-37: an upper bound on recoverable wall-clock, not a
                # promise - sharing this work would still cost whatever the
                # shared version costs, and these elements overlapped.
                "max_element_duration_s": per_element_duration[worst_element],
                "worst_element": worst_element,
                "example_cmd": example_cmd,
            })
        # A signature seen *only* under unresolved buckets never reached the
        # loop above, so it is counted here.
        excluded_unresolved_only += sum(
            1 for signature, buckets in unresolved_signatures.items()
            if signature not in by_signature and len(buckets) >= 2
        )
        # Ranked by the wall-clock-relevant figure, not by the sum: a
        # 6x-repeated 50ms probe across six concurrent elements is not a
        # bigger finding than a 2x-repeated 5s codegen step. The rank is
        # what makes the cap below safe: what it drops is the cheapest.
        findings.sort(key=lambda f: -f["max_element_duration_s"])
        total = len(findings)
        omitted = max(0, total - REDUNDANCY_FINDINGS_MAX)
        # `UX-375` took the second of its filing's two endings. The
        # first - move `_REDUNDANCY_MIN_SECONDS` here, so the contract
        # and the terminal agree about what a finding is - looked
        # obviously right and is not: **14 of the 20 findings in
        # `tests/fixtures/macro_micro` fall below that floor**, and
        # `correlate.py` iterates every finding to build each element's
        # `redundancy_count` and `worst_redundancy`. Moving the floor
        # would therefore have changed a published per-element number
        # for a reason no reader could see, which is a bigger defect
        # than the one being fixed. So the floor stays a *display*
        # threshold and the contract says so, which is the ending the
        # filing offered beside it.
        coverage = {
            "excluded_unresolved_only": excluded_unresolved_only,
            "excluded_element_command_blocks": excluded_command_blocks,
            # `UX-375`: what this list is not. A shorter list reads as a
            # cleaner build unless the reason it is short is named.
            "findings_cap": REDUNDANCY_FINDINGS_MAX,
            "omitted_beyond_cap": omitted,
            "total_findings": total,
            "display_floor_seconds": _REDUNDANCY_MIN_SECONDS,
            "note": (
                "Each finding's `max_element_duration_s` is an upper bound on what "
                "sharing that one operation could recover, for the single "
                "worst-affected element. They are per-signature maxima over "
                "elements that ran concurrently: they must not be summed, and on a "
                "real capture their sum exceeds the build's own duration. A "
                "signature is a finding only when it ran under 2+ *resolved* "
                "elements (UX-73); processes in the unresolved attribution bucket "
                "and each element's own top-level command block are excluded, and "
                "counted above. The list holds at most `findings_cap` findings, "
                "the most costly first, out of `total_findings`; "
                "`omitted_beyond_cap` is how many were cut. It deliberately "
                "*includes* findings below `display_floor_seconds`, which the "
                "terminal does not show - they are still real repeats, and "
                "each element's `redundancy_count` in `correlate` counts them."
            ),
        }
        return findings[:REDUNDANCY_FINDINGS_MAX], coverage


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
    state = _PerElementParallelism()
    for record in records:
        state.add(record)
    return state.finish()


class _PerElementParallelism:
    """`compute_per_element_parallelism`, one record at a time.

    `UX-297`: what a profile needs from a work process is its two
    timestamps, so those go into per-element `array('d')`s as the
    stream passes; the binary name and the `-jN` are reduced on arrival
    and the command line is not kept. Same arithmetic, same order - the
    elements are profiled in the order the trace first named them,
    which is what the list-based version did with its `defaultdict`.
    """

    def __init__(self):
        self.starts: Dict[str, array.array] = {}
        self.ends: Dict[str, array.array] = {}
        self.unclassified: Dict[str, Dict[str, int]] = {}
        self.requested: Dict[str, Optional[int]] = {}

    def add(self, r):
        if r["open"] or r["end_ts"] is None:
            return
        element = r["element"]
        if element not in self.starts:
            self.starts[element] = array.array("d")
            self.ends[element] = array.array("d")
            self.unclassified[element] = {}
            self.requested[element] = None
        name = _binary_name(r["cmd"])
        kind = classify_binary(name)
        if kind == "work":
            self.starts[element].append(r["start_ts"])
            self.ends[element].append(r["end_ts"])
        elif kind == "unclassified":
            counts = self.unclassified[element]
            counts[name] = counts.get(name, 0) + 1
        if name in ("make", "gmake", "ninja"):
            match = _REQUESTED_JOBS_RE.search(r["cmd"])
            if match:
                # Highest wins: an element can run several `make`
                # invocations (configure probes, install), and the
                # real build one is the one that asked for the most.
                value = int(match.group(1))
                current = self.requested[element]
                self.requested[element] = (
                    value if current is None else max(current, value))

    def finish(self):
        profiles = []
        for element in self.starts:
            work_intervals = list(zip(self.starts[element], self.ends[element]))
            unclassified = self.unclassified[element]
            requested_jobs = self.requested[element]
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
    state = _MaxConcurrency()
    for record in records:
        state.add(record)
    return state.finish()


class _MaxConcurrency:
    """`compute_max_concurrency`, one record at a time.

    `UX-297`: the sweep needs two timestamps per matched process and
    nothing else, so it keeps two `array('d')` - 16 bytes a process
    against the ~1.2 kB the record itself costs - and never holds the
    records.
    """

    def __init__(self):
        self.starts = array.array("d")
        self.ends = array.array("d")

    def add(self, record):
        if record["open"]:
            return
        self.starts.append(record["start_ts"])
        self.ends.append(record["end_ts"])

    def finish(self):
        """The same sweep, walked over two sorted arrays.

        The list-of-points version built one tuple per endpoint - two
        per process, ~29 MB on a 200,000-process trace, allocated at
        the exact moment the aggregates are all live. Two sorted arrays
        and two cursors give the identical answer with no allocation
        past the sort: an end at the same timestamp as a start is taken
        first, which is what `sort(key=(ts, delta))` did with `-1`
        ordering before `+1`.
        """
        if not self.starts:
            return 0
        starts = sorted(self.starts)
        ends = sorted(self.ends)
        current = peak = 0
        opened = closed = 0
        total_starts, total_ends = len(starts), len(ends)
        while opened < total_starts:
            if closed < total_ends and ends[closed] <= starts[opened]:
                current -= 1
                closed += 1
            else:
                current += 1
                opened += 1
                if current > peak:
                    peak = current
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


_ELEMENT_YAML_CACHE: Dict[tuple, Optional[dict]] = {}


def read_element_yaml(path: str) -> Optional[dict]:
    """One parse of one `.bst` file, shared by every reader that wants one.

    `None` means "could not be read", which is not the same answer as an
    element that declares nothing - both callers here already
    distinguished the two and keep doing so.

    UX-168: the census parsed each element file twice, once for its
    declared build dependencies and once for its local sources, and YAML
    parsing was where its time went: 5.0s of 5.9s under cProfile on a
    synthetic 1,000-element project. The cache is keyed on the file's
    mtime and size as well as its path, so a project edited between two
    calls inside one process is re-read rather than remembered wrong.

    UX-77: `yaml` stays imported inside the function. A module-scope
    import made `bga capture --help` fail outright on an install without
    PyYAML, and that is still true here.
    """
    import yaml

    try:
        stat = os.stat(path)
    except OSError:
        return None
    key = (path, stat.st_mtime_ns, stat.st_size)
    if key in _ELEMENT_YAML_CACHE:
        return _ELEMENT_YAML_CACHE[key]
    try:
        with open(path, "r", encoding="utf-8") as handle:
            # libyaml's loader wherever the binding was built with it;
            # the pure-Python scanner is several times slower and this
            # is the census's dominant cost.
            loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
            data = yaml.load(handle, Loader=loader) or {}
    except (OSError, yaml.YAMLError):
        data = None
    else:
        data = data if isinstance(data, dict) else {}
    _ELEMENT_YAML_CACHE[key] = data
    return data


def _local_source_paths(project_dir: str, element: str) -> List[str]:
    """The directories an element stages from its own `local` sources.

    Read from the `.bst` file for the same reason
    `read_declared_build_deps` reads its own: this must work against a
    project directory without invoking BuildStream. Only `local`
    sources - a `git` or `tar` source is not on disk before a fetch, and
    a census that silently skipped one would be worse than one that says
    it only sees local sources.
    """
    path = os.path.join(elements_dir_for(project_dir), element)
    data = read_element_yaml(path)
    if data is None:
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
        elements = discover_element_names(project_dir)
        if not elements:
            return {}
        census = census_project(project_dir, elements)
    except (OSError, ValueError):
        return {}
    # `UX-376`: recorded on the function so the caller can say *why* an
    # element is traced without running the census a second time - it is
    # the expensive step (`UX-183` measured minutes on freedesktop-sdk).
    census_spine_verdicts.last_unassessable = set(
        census.get("elements_unassessable") or ())
    # `UX-376`: an unassessable element gets the spine. The docstring
    # above always said "not assessed" and "assessed and clean" are
    # different claims and only one is safe to skip - and until this
    # item every element was reported as assessed, because the census
    # answered from local sources for elements whose sandboxes are
    # mostly built. Measured on a fixture where one element produces a
    # `-static` tool and a later one runs it 200 times: `auto` traced 21
    # processes of 221 and printed "the spine is not needed".
    return {
        element: bool(entry.get("static_count"))
        or not entry.get("assessable", True)
        for element, entry in (census.get("per_element") or {}).items()
    }


def format_census_coverage(project_dir: str, verdicts: Dict[str, bool],
                           unassessable: Optional[Set[str]] = None) -> str:
    """One line naming what `--trace-spine=auto` decided, and on what.

    `UX-160` item 3. The unassessed count is the number that matters:
    those elements are traced by the fail-safe, so a large one means
    `auto` is really `on` and the build is paying full spine price.
    Until `UX-108` measures that price, this line is the user's only
    hint that it is being charged.
    """
    declared = discover_element_names(project_dir)
    unassessable = set(unassessable or ())
    assessed = len(verdicts) - len(unassessable & set(verdicts))
    # `UX-376`: the two reasons an element gets the spine, counted
    # apart. They are different facts and a reader should do different
    # things about them: "something static is staged here" is a
    # property of the project, and "part of what will be staged here
    # does not exist yet" is a limit of the instrument.
    static = sum(1 for element, needs in verdicts.items()
                 if needs and element not in unassessable)
    produced = len(unassessable & set(verdicts))
    unassessed = max(0, len(declared) - len(verdicts))
    # UX-168 item 5: "0 with static binaries (spine traced)" made the
    # parenthetical describe the zero elements, which is a riddle.
    # `UX-376`: and the sentence must not claim more than the census
    # can support. "None with static binaries (the spine is not needed)"
    # was printed for a build in which the spine was the difference
    # between 21 processes and 221, because the tool the build produced
    # was outside what a census of `local` sources can see.
    if static:
        line = (f"Census: {assessed} of {len(declared)} element(s) assessed, "
                f"{static} with static binaries (those get the spine)")
    elif assessed:
        line = (f"Census: {assessed} of {len(declared)} element(s) assessed, "
                f"none of those staged a static binary")
    else:
        line = f"Census: 0 of {len(declared)} element(s) could be assessed"
    if produced:
        line += (f"; {produced} stage what this build produces and cannot be "
                 f"assessed before it runs - those get the spine")
    if unassessed:
        line += (f"; {unassessed} unassessed and therefore traced by default "
                 f"- `auto` is behaving as `on` for those")
    return line


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
    # UX-183: on freedesktop-sdk this walks every `local` source of every
    # element before the build starts - minutes, behind one phase line.
    census_tick = progress.ticker("census", total=len(elements))
    for index, element in enumerate(elements, 1):
        census_tick.step(index)
        merged = {"static": [], "dynamic": 0, "libraries": 0,
                  "unclassified": 0, "scripts": 0}
        for root in _local_source_paths(project_dir, element):
            counted = census_static_executables(root)
            merged["static"].extend(counted["static"])
            for key in ("dynamic", "libraries", "unclassified", "scripts"):
                merged[key] += counted[key]
        merged["static"] = sorted(set(merged["static"]))
        own[element] = merged
    census_tick.done()

    # UX-168: the closure was recomputed from scratch for every element,
    # and recursively, so a project whose graph is a chain cost O(V*E)
    # and needed one Python frame per link. Measured on a synthetic
    # 1,000-element project (each element depending on the previous
    # five): 2.04s before this memo.
    closures: Dict[str, Set[str]] = {}

    def _closure(element: str) -> Set[str]:
        """Everything reachable from `element` over declared build deps.

        Plain iterative reachability, short-circuited by `closures`
        wherever a dependency's own answer is already complete. Written
        so a dependency cycle cannot mislead it: every entry it stores
        is a *finished* reachable set, so consuming one is always safe -
        which a post-order memo would not be.
        """
        cached = closures.get(element)
        if cached is not None:
            return cached
        seen: Set[str] = set()
        stack = list(declared.get(element) or [])
        while stack:
            dependency = stack.pop()
            if dependency in seen:
                continue
            seen.add(dependency)
            memo = closures.get(dependency)
            if memo is not None:
                seen.update(memo)
            else:
                stack.extend(declared.get(dependency) or [])
        closures[element] = seen
        return seen

    def _prime_closures() -> None:
        """Resolve dependencies before dependents, so each `_closure`
        walk stops at the first memo instead of re-walking the tree.

        Without this the saving depends on the order `elements` happens
        to arrive in; a list in reverse dependency order would memoize
        every answer and still walk the whole graph for each one.
        """
        visited: Set[str] = set()
        for root in list(declared):
            if root in visited:
                continue
            stack = [(root, iter(declared.get(root) or []))]
            visited.add(root)
            while stack:
                name, pending = stack[-1]
                for dependency in pending:
                    if dependency in visited:
                        continue
                    visited.add(dependency)
                    stack.append((dependency, iter(declared.get(dependency) or [])))
                    break
                else:
                    stack.pop()
                    _closure(name)

    _prime_closures()

    # `UX-376`: which dependencies this build produces rather than
    # stages. Read once for the whole census.
    kinds = read_element_kinds(project_dir)

    per_element = {}
    for element in elements:
        static = set(own[element]["static"])
        staged_by = {name: sorted(own.get(name, {}).get("static") or [])
                     for name in _closure(element)}
        for names in staged_by.values():
            static.update(names)
        # `UX-376`: what this element's sandbox will hold that the
        # census never saw. It reads `local` sources - files on disk
        # before anything runs - so a dependency whose artifact this
        # build *produces* stages contents that do not exist yet. An
        # `import` element stages its sources verbatim and is therefore
        # assessable; every other kind runs commands and produces
        # something new.
        produced = sorted(name for name in _closure(element)
                          if kinds.get(name, "unknown") != "import")
        per_element[element] = {
            "static_executables": sorted(static),
            "static_count": len(static),
            "own_static": own[element]["static"],
            "staged_by_dependencies": {
                name: names for name, names in sorted(staged_by.items()) if names
            },
            "dynamic_executables": own[element]["dynamic"],
            # "assessed and clean" and "not assessed" are different
            # claims and only one of them is safe to act on, which is
            # the rule `census_spine_verdicts` was already written to -
            # it just had no unassessable elements to apply it to.
            "assessable": not produced,
            "unassessable_because": produced,
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
        # `UX-376`: the elements this census could not answer for. Named
        # rather than folded into `elements_at_risk`, because the reason
        # is different and so is what a reader should do about it: a
        # risk is "something static is staged here", and this is "part
        # of what will be staged here does not exist yet".
        "elements_unassessable": sorted(
            element for element, entry in per_element.items()
            if not entry["assessable"]
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
    elements_dir = elements_dir_for(project_dir)
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
    elements_dir = elements_dir_for(project_dir)
    declared: Dict[str, List[str]] = {}
    for element in elements:
        path = os.path.join(elements_dir, element)
        # UX-168: one shared, memoised parse - the census used to read
        # every element file here and again in `_local_source_paths`.
        data = read_element_yaml(path)
        if data is None:
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
    state = _ElementOpensCoverage()
    for record in records:
        state.add(record)
    return state.finish()


class _ElementOpensCoverage:
    """`compute_element_opens_coverage`, one record at a time. `UX-297`."""

    def __init__(self):
        self.coverage: Dict[str, dict] = {}
        self.saw_spine = False

    def add(self, record):
        if record.get("coverage") in (COVERAGE_BOTH, COVERAGE_SPINE_ONLY):
            self.saw_spine = True
        entry = self.coverage.setdefault(
            record.get("element") or "unknown",
            {"processes": 0, "opens_covered": 0, "spine_only": 0},
        )
        entry["processes"] += 1
        if record.get("coverage") == COVERAGE_SPINE_ONLY:
            entry["spine_only"] += 1
        else:
            entry["opens_covered"] += 1

    def finish(self):
        if not self.saw_spine:
            return {}
        for entry in self.coverage.values():
            entry["opens_coverage"] = entry["opens_covered"] / entry["processes"]
        return self.coverage


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
    state = _SandboxDurations()
    for record in records:
        state.add(record)
    return state.finish()


class _SandboxDurations:
    """`sandbox_durations`, one record at a time. `UX-297`."""

    def __init__(self):
        self.first: Dict[str, float] = {}
        self.last: Dict[str, float] = {}

    def add(self, record):
        key = record.get("invocation")
        if key is None:
            return
        key = str(key)
        start_ts = record.get("start_ts")
        if start_ts is not None:
            self.first[key] = min(self.first.get(key, start_ts), start_ts)
        end_ts = record.get("end_ts")
        if end_ts is not None:
            self.last[key] = max(self.last.get(key, end_ts), end_ts)

    def finish(self):
        first, last = self.first, self.last
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
    state = _BinaryCost()
    for record in records:
        state.add(record)
    return state.finish(top_n=top_n)


class _BinaryCost:
    """`compute_binary_cost`, one record at a time. `UX-297`."""

    def __init__(self):
        self.per_element: Dict[str, dict] = {}

    def add(self, record):
        element = record.get("element")
        if not element:
            return
        binary = os.path.basename((record.get("cmd") or "").split(" ")[0]) or "unknown"
        entry = self.per_element.setdefault(element, {})
        stat = entry.setdefault(
            binary, {"count": 0, "cpu_us": 0, "wall_s": 0.0, "measured": 0}
        )
        stat["count"] += 1
        if record.get("cpu_us") is not None:
            stat["cpu_us"] += record["cpu_us"]
            stat["measured"] += 1
        if record.get("duration_s") is not None:
            stat["wall_s"] += record["duration_s"]

    def finish(self, top_n: int = 5):
        result: Dict[str, dict] = {}
        for element, binaries in self.per_element.items():
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
    state = _PeakMemory()
    for record in records:
        state.add(record)
    return state.finish()


class _PeakMemory:
    """`compute_peak_memory`, one record at a time. `UX-297`."""

    def __init__(self):
        self.per_element: Dict[str, dict] = {}

    def add(self, record):
        entry = self.per_element.setdefault(
            record["element"],
            {"peak_rss_kb": None, "measured": 0, "unmeasured": 0},
        )
        if "max_rss_kb" in record:
            entry["measured"] += 1
            current = entry["peak_rss_kb"]
            entry["peak_rss_kb"] = max(current or 0, record["max_rss_kb"])
        else:
            entry["unmeasured"] += 1

    def finish(self):
        per_element = self.per_element
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


def compute_process_outcomes(records: List[dict]) -> dict:
    """How each element's processes ended (`UX-378`).

    The spine reads the wait status from the kernel's own exit-stop
    message, so a process the kernel killed is distinguishable from one
    that returned that number - and that distinction reached `bga
    timeline` and stopped there. `plane2/v2` had no key for it, so
    neither the terminal report nor `bga view` could say a process had
    been killed, which is the signature an OOM leaves.

    **Unavailable is not zero, and here the difference is the whole
    point.** Only the spine writes `exit_status`; under the default
    policy there are usually no spine records at all, and a hook record
    carries no status because its destructor runs before the process has
    one. So a capture with no spine reports `available: false` rather
    than "nothing was killed" - the second is a claim this capture
    cannot make, and it is exactly the claim a reader whose build was
    OOM-killed would be misled by.

    Killed processes are counted **by signal**, because 9 and 15 mean
    different things: `SIGKILL` with no `bst` cancellation around it is
    the shape an OOM kill has, and `SIGTERM` is usually the build being
    stopped on purpose.
    """
    state = _ProcessOutcomes()
    for record in records:
        state.add(record)
    return state.finish()


class _ProcessOutcomes:
    """`compute_process_outcomes`, one record at a time."""

    def __init__(self):
        self.exited_zero = 0
        self.exited_nonzero = 0
        self.by_signal: Dict[str, int] = {}
        self.unknown = 0
        #: Only the elements with something to say appear, so this stays
        #: `O(elements that had a failure)` rather than `O(elements)`.
        self.per_element: Dict[str, dict] = {}

    def add(self, record):
        status = record.get("exit_status")
        if status is None:
            self.unknown += 1
            return
        if str(status).startswith("signal:"):
            signal = str(status).split(":", 1)[1]
            self.by_signal[signal] = self.by_signal.get(signal, 0) + 1
            self._note(record["element"], "killed", signal)
        elif str(status) == "0":
            self.exited_zero += 1
        else:
            self.exited_nonzero += 1
            self._note(record["element"], "exited_nonzero", str(status))

    def _note(self, element, kind, detail):
        entry = self.per_element.setdefault(
            element, {"killed": 0, "exited_nonzero": 0, "statuses": {}})
        entry[kind] += 1
        entry["statuses"][detail] = entry["statuses"].get(detail, 0) + 1

    def finish(self):
        measured = self.exited_zero + self.exited_nonzero + sum(
            self.by_signal.values())
        if measured == 0:
            return {
                "available": False,
                "unknown": self.unknown,
                "note": "no process reported how it ended. Only the ptrace "
                        "spine can - the hook's destructor runs before the "
                        "process has a status, and not at all when one is "
                        "killed - so this is a capture taken without it "
                        "(`--trace-spine=on`). Reported as unavailable rather "
                        "than as zero kills, which is a claim this capture "
                        "cannot make.",
            }
        return {
            "available": True,
            "exited_zero": self.exited_zero,
            "exited_nonzero": self.exited_nonzero,
            "killed_by_signal": dict(sorted(self.by_signal.items())),
            "killed": sum(self.by_signal.values()),
            "unknown": self.unknown,
            "per_element": {k: self.per_element[k]
                            for k in sorted(self.per_element)},
            "note": "How each traced process ended, from the spine's read of "
                    "the kernel exit-stop. `unknown` is the processes no "
                    "spine record covered - hook-only records carry no "
                    "status, and one still running when the trace ended has "
                    "none to carry. A `signal:9` with no cancellation around "
                    "it is the shape an OOM kill leaves; `signal:15` is "
                    "usually a build stopped on purpose.",
        }


def compute_resource_pressure(records: List[dict]) -> dict:
    """What each element's processes did to the disk, to memory and to
    the run queue (`UX-379`).

    The three axes bga otherwise only models. `cpu_time` says how long a
    process ran and `peak_memory` how large it got; neither can tell an
    element that was slow because it read a gigabyte from one that was
    slow because fifteen siblings preempted it, and both present as low
    CPU concurrency. These counters separate them, and they cost nothing
    - `hook.c` already reads the struct they live in.

    **Summed, unlike `peak_memory`.** A block read and a fault are
    events, not levels: two processes that each read 100 MB did read 200
    MB between them, whichever order they ran in. That is the opposite
    of `ru_maxrss`, and the reason the two aggregates look different.

    **Self only.** Every child is traced and reports its own counts, so
    folding a parent's `RUSAGE_CHILDREN` copy in would count each block
    twice - which is why `hook.c` does not write one.

    **Zero is a measurement here.** A read served from the page cache
    never reaches the block layer, so `read_bytes` of 0 means "nothing
    went to the device", not "unmeasured" - the unmeasured case is a
    process that ran no destructor, counted separately as it is
    everywhere else.
    """
    state = _ResourcePressure()
    for record in records:
        state.add(record)
    return state.finish()


class _ResourcePressure:
    """`compute_resource_pressure`, one record at a time."""

    #: The record fields this folds. All six are additive, which is what
    #: lets one loop do them; the list is `_PRESSURE_FIELDS` rather than
    #: a copy, so a seventh reaches the fold and the pairing pass at once.
    FIELDS = _PRESSURE_FIELDS

    def __init__(self):
        self.per_element: Dict[str, dict] = {}

    def add(self, record):
        entry = self.per_element.get(record["element"])
        if entry is None:
            entry = {name: 0 for name in self.FIELDS}
            entry["measured"] = 0
            entry["unmeasured"] = 0
            self.per_element[record["element"]] = entry
        # One field decides, rather than all six: a hook that wrote the
        # line writes every field, and a record carrying some but not
        # all came from a truncated line - which `hook.c`'s buffer is
        # sized against and which would otherwise read as a low count.
        if "read_bytes" in record:
            entry["measured"] += 1
            for name in self.FIELDS:
                entry[name] += record.get(name, 0)
        else:
            entry["unmeasured"] += 1

    def finish(self):
        per_element = self.per_element
        measured_total = sum(e["measured"] for e in per_element.values())
        if measured_total == 0:
            return {
                "available": False,
                "note": "no process reported these counters - either the hook "
                        "predates UX-379 or every traced process was killed "
                        "before its destructor ran. Reported as unavailable "
                        "rather than as zero, which here would read as a build "
                        "that touched no disk.",
            }
        for entry in per_element.values():
            total = entry["measured"] + entry["unmeasured"]
            entry["coverage"] = entry["measured"] / total if total else 0.0
        return {
            "available": True,
            "per_element": {k: per_element[k] for k in sorted(per_element)},
            "measured": measured_total,
            "unmeasured": sum(e["unmeasured"] for e in per_element.values()),
            "note": "Summed per element over the processes whose destructor "
                    "ran (getrusage at exit). `read_bytes`/`written_bytes` are "
                    "block-layer I/O - what reached the device - so a read "
                    "served from the page cache is genuinely zero and a large "
                    "figure is genuinely disk. `involuntary_switches` is the "
                    "run queue preempting a process that still had work, which "
                    "rises with oversubscription; `voluntary_switches` is a "
                    "process choosing to wait. `major_faults` is the page "
                    "pressure a memory-starved host produces.",
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
    state = _CpuTime()
    for record in records:
        state.add(record)
    return state.finish()


class _CpuTime:
    """`compute_cpu_time`, one record at a time.

    `UX-297`: the per-element wall span used to be a second pass that
    re-scanned **every** record once per element - O(elements x
    processes), and 2.0 s of the 9.4 s an extraction spent on a
    200,000-process trace. The same span is a running min and max over
    the records that have an end, which is what it always meant.
    """

    def __init__(self):
        self.per_element: Dict[str, dict] = {}
        self.spans: Dict[str, list] = {}
        self.spine_sourced = 0

    def add(self, record):
        element = record["element"]
        entry = self.per_element.setdefault(
            element,
            {"cpu_us": 0, "children_cpu_us": 0, "measured": 0, "unmeasured": 0,
             "wall_span_s": None},
        )
        if "cpu_us" in record:
            entry["cpu_us"] += record["cpu_us"]
            entry["children_cpu_us"] += record.get("children_cpu_us", 0)
            entry["measured"] += 1
        else:
            entry["unmeasured"] += 1
        if record.get("cpu_source") == "spine":
            self.spine_sourced += 1
        if record["end_ts"] is not None:
            span = self.spans.get(element)
            if span is None:
                self.spans[element] = [record["start_ts"], record["end_ts"]]
            else:
                span[0] = min(span[0], record["start_ts"])
                span[1] = max(span[1], record["end_ts"])

    def finish(self):
        per_element = self.per_element
        for element, entry in per_element.items():
            span = self.spans.get(element)
            if span is not None:
                entry["wall_span_s"] = span[1] - span[0]
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
        spine_sourced = self.spine_sourced
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
    state = _ConfigurePhase()
    for record in records:
        state.add(record)
    return state.finish()


class _ConfigurePhase:
    """`classify_configure_phase`, one record at a time.

    `UX-297`, and the only aggregate here that cannot be a per-element
    fold: a process is configure work because of *what started it*, so
    the classification needs the whole sandbox's parentage before any
    record can be classified. Two passes, then - but over the four
    things the walk reads rather than over the records.

    What is kept per process: its sandbox and pid (as one integer key),
    its parent's pid, whether its own command line is a configure root,
    which element it billed to, and its CPU time. The command line
    itself - the bulk of a record - is reduced to a boolean on arrival
    and dropped. The ancestor walk is unchanged, so the classification
    is the one this function has always made.
    """

    _NO_CPU = -1

    def __init__(self):
        # `(sandbox, pid) -> ppid`, keyed by one integer rather than by
        # a tuple: a tuple key costs its own object per process, which
        # on the traces this item is about is tens of megabytes of
        # nothing. Sandboxes are numbered as they are met and the pid
        # occupies the low bits. Last writer wins, exactly as the record
        # map this replaces did - a sandbox that recycles a pid leaves
        # the later process as that key's occupant, and changing that
        # here would change the classification.
        self.parent: Dict[int, int] = {}
        # The subset of those keys whose own command line is a
        # configure entry point. A set, because on most builds it is
        # nearly empty.
        self.roots = set()
        self.sandbox_ids: Dict[str, int] = {}
        # Both of the above are built in `finish`, from the rows, not as
        # the stream arrives. Measured: the parent map is ~100 bytes a
        # process, and building it during the fold puts it beside the
        # records that have not been released yet. The rows cost a
        # quarter of that, and by the time they are turned into a map
        # the records are gone.
        # One compact row per record, in arrival order.
        self.rows_sandbox = array.array("i")
        self.rows_pid = array.array("q")
        self.rows_ppid = array.array("q")
        self.rows_root = bytearray()
        self.elements: List[str] = []
        self.cpu = array.array("q")

    _NO_PARENT = -1
    _PID_BITS = 32

    def _key(self, sandbox_id: int, pid: int) -> int:
        return (sandbox_id << self._PID_BITS) | (pid & 0xFFFFFFFF)

    def add(self, record):
        sandbox = record.get("invocation") or record.get("element")
        sandbox_id = self.sandbox_ids.get(sandbox)
        if sandbox_id is None:
            sandbox_id = self.sandbox_ids[sandbox] = len(self.sandbox_ids)
        pid = record["pid"]
        ppid = record.get("ppid")
        root = is_configure_root(record["cmd"])
        self.rows_sandbox.append(sandbox_id)
        self.rows_pid.append(pid)
        self.rows_ppid.append(self._NO_PARENT if ppid is None else ppid)
        self.rows_root.append(1 if root else 0)
        self.elements.append(record["element"])
        self.cpu.append(record["cpu_us"] if "cpu_us" in record else self._NO_CPU)

    def _is_configure(self, sandbox_id, pid, ppid, own_root) -> bool:
        """The walk `classify_configure_phase` has always made, over the
        parent map rather than over the records."""
        if own_root:
            return True
        seen = {self._key(sandbox_id, pid)}
        current = None if ppid == self._NO_PARENT else ppid
        while current is not None:
            key = self._key(sandbox_id, current)
            if key in seen:  # defensive: a pid cycle is not possible,
                return False  # but cheap to refuse
            seen.add(key)
            if key not in self.parent:
                return False
            if key in self.roots:
                return True
            parent_pid = self.parent[key]
            current = None if parent_pid == self._NO_PARENT else parent_pid
        return False

    def finish(self):
        # The parent map, last-writer-wins in arrival order - the same
        # rule the record map this replaces followed, and the reason a
        # sandbox that recycles a pid classifies the way it always did.
        for index in range(len(self.rows_pid)):
            key = self._key(self.rows_sandbox[index], self.rows_pid[index])
            self.parent[key] = self.rows_ppid[index]
            if self.rows_root[index]:
                self.roots.add(key)
            else:
                self.roots.discard(key)

        per_element: Dict[str, dict] = {}
        for index, element in enumerate(self.elements):
            entry = per_element.setdefault(element, {
                "configure_cpu_us": 0, "build_cpu_us": 0,
                "configure_processes": 0, "build_processes": 0,
                "measured": 0, "unmeasured": 0,
            })
            configure = self._is_configure(
                self.rows_sandbox[index], self.rows_pid[index],
                self.rows_ppid[index], self.rows_root[index])
            entry["configure_processes" if configure else "build_processes"] += 1
            cpu = self.cpu[index]
            if cpu != self._NO_CPU:
                entry["measured"] += 1
                entry["configure_cpu_us" if configure else "build_cpu_us"] += cpu
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
                            fork_only_exits: int = 0,
                            unmatched_ends: int = 0) -> dict:
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
    state = _StreamCoverage()
    for record in records:
        state.add(record)
    return state.finish(fork_only_exits=fork_only_exits,
                        unmatched_ends=unmatched_ends)


class _StreamCoverage:
    """`compute_stream_coverage`, one record at a time.

    `UX-297`: every figure here is a counter except the CPU
    disagreements, and those are the records where the two mechanisms
    differ by more than a few clock ticks - a handful on a real capture,
    and the only place a command line is kept.
    """

    def __init__(self):
        self.records = 0
        self.counts: Dict[str, int] = {}
        self.disagreements: List[dict] = []
        self.reconciled = 0
        self.spine_total = 0
        self.hook_total = 0
        self.cpu_from_spine_only = 0
        self.exec_chains_collapsed = 0

    def add(self, record):
        self.records += 1
        coverage = record.get("coverage", COVERAGE_HOOK_ONLY)
        self.counts[coverage] = self.counts.get(coverage, 0) + 1
        if record.get("cpu_source") == "spine":
            self.cpu_from_spine_only += 1
        if record.get("exec_chain", 1) > 1:
            self.exec_chains_collapsed += 1
        if "hook_cpu_us" not in record or "spine_cpu_us" not in record:
            return
        self.reconciled += 1
        self.spine_total += record["spine_cpu_us"]
        self.hook_total += record["hook_cpu_us"]
        delta = abs(record["hook_cpu_us"] - record["spine_cpu_us"])
        if delta > CPU_RECONCILIATION_TOLERANCE_US:
            self.disagreements.append({
                "pid": record["pid"], "element": record["element"],
                "spine_cpu_us": record["spine_cpu_us"],
                "hook_cpu_us": record["hook_cpu_us"],
                "delta_us": delta, "cmd": record["cmd"][:120],
            })

    def finish(self, fork_only_exits: int = 0, unmatched_ends: int = 0):
        if not self.records:
            return {}
        counts = self.counts
        opens_covered = counts.get(COVERAGE_BOTH, 0) + counts.get(
            COVERAGE_HOOK_ONLY, 0)
        disagreements = self.disagreements
        disagreements.sort(key=lambda entry: -entry["delta_us"])
    # The per-process check above cannot see a *systematic* difference:
    # 663 pairs each within one clock tick still summed to 58.47s against
    # 54.14s on a real examples/06 capture - a 7.4% aggregate gap, and
    # every pair individually "agreeing". Measured on the same
    # population the per-process check ran on, because a total over one
    # set compared with a total over another measures the sets.
        aggregate = None
        if self.reconciled:
            spine_total = self.spine_total
            hook_total = self.hook_total
            aggregate = {
                "processes": self.reconciled,
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
            "processes": self.records,
            "by_coverage": dict(sorted(counts.items())),
            # Opened paths need the hook. This is the share of processes any
            # opens-based finding (`UX-46`'s declared-vs-used) can speak
            # about at all - published because the alternative is a finding
            # that reads as "no unused dependencies" when it means "nobody
            # could look".
            "opens_covered_processes": opens_covered,
            "opens_coverage": opens_covered / self.records,
            "cpu_reconciled_processes": self.reconciled,
            # UX-107: how many processes' CPU time is a tick-truncated
            # figure because no finer one exists for them. Published because
            # a static-heavy build's CPU total is materially low and the
            # report must say so rather than let the number pass as exact.
            "cpu_from_spine_only": self.cpu_from_spine_only,
            # UX-123: pids that ran more than one image. Collapsed into one
            # record each, because the kernel's CPU and RSS figures are
            # per-pid and cumulative across execs - published so a reader can
            # see the collapse rather than wonder where the records went.
            "exec_chains_collapsed": self.exec_chains_collapsed,
            # UX-123: exits recorded for pids that never exec'd - a
            # fork-without-exec child is the same program as its parent and
            # wears its cmdline, so it is not a process to list. Dropped, and
            # said so.
            "fork_only_exits": fork_only_exits,
            # UX-133: an END with no START that the *hook* produced. Only the
            # spine can see a fork-without-exec exit, so a hook orphan is a
            # truncated log or a lost START - a different fact, and one the
            # old single count asserted was something it is not.
            "unmatched_ends": unmatched_ends,
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


class Plane2Fold:
    """Every Plane 2 aggregate, folded from a record stream.

    `UX-297`, Direction 15's rules 2 and 5. `summarize` used to take the
    whole record list and hand it to ten functions that each walked it
    again; the list itself was then embedded in the report. Measured on
    a 200,000-process trace, holding it cost 204 MB of a 267 MB
    extraction, and at the field's 2.7 M processes the same list is
    ~2.9 GB - allocated on the machine that has just finished the build.

    Each aggregate is the same computation, split into `add` and
    `finish`. `summarize(records)` folds a list and is byte-identical by
    construction, so every existing caller and every existing guard is
    the migration's equality check; `load_and_summarize` folds the
    stream and never builds the list at all.

    What is still O(processes) is named rather than hidden: the
    concurrency sweeps keep two `array('d')` of timestamps (16 bytes a
    process against ~1.2 kB for the record), and the configure
    classifier keeps a parent map, because a process is configure work
    because of what started it and that cannot be known until the
    sandbox is complete.
    """

    def __init__(self, resolved: Optional[Dict[str, str]] = None):
        # `UX-56`'s correction, applied as each record arrives rather
        # than by a second pass that rewrites the list in place - there
        # is no list to rewrite. Every aggregate is keyed on the element
        # name, so the correction has to happen before the fold, not
        # after it.
        self.resolved = resolved or {}
        self.relabelled = 0
        self.count = 0
        self.matched = 0
        self.open_records = 0
        self.by_binary: Dict[str, int] = {}
        self.by_element: Dict[str, int] = {}
        self.wall_start = None
        self.wall_end = None
        self.concurrency = _MaxConcurrency()
        self.cpu_time = _CpuTime()
        self.configure = _ConfigurePhase()
        self.peak_memory = _PeakMemory()
        self.pressure = _ResourcePressure()
        self.outcomes = _ProcessOutcomes()
        self.binary_cost = _BinaryCost()
        self.parallelism = _PerElementParallelism()
        self.redundancy = _RedundantOperations()
        self.coverage = _StreamCoverage()
        self.opens_coverage = _ElementOpensCoverage()
        self.sandboxes = _SandboxDurations()

    def add(self, record: dict) -> None:
        element = self.resolved.get(str(record.get("invocation")))
        if element and record.get("element") != element:
            record["element"] = element
            self.relabelled += 1
        self.count += 1
        if record["open"]:
            self.open_records += 1
        else:
            self.matched += 1
        name = _binary_name(record["cmd"])
        self.by_binary[name] = self.by_binary.get(name, 0) + 1
        self.by_element[record["element"]] = self.by_element.get(
            record["element"], 0) + 1
        start = record["start_ts"]
        end = record["end_ts"] if record["end_ts"] is not None else start
        self.wall_start = start if self.wall_start is None else min(
            self.wall_start, start)
        self.wall_end = end if self.wall_end is None else max(self.wall_end, end)
        self.concurrency.add(record)
        self.cpu_time.add(record)
        self.configure.add(record)
        self.peak_memory.add(record)
        self.pressure.add(record)
        self.outcomes.add(record)
        self.binary_cost.add(record)
        self.parallelism.add(record)
        self.redundancy.add(record)
        self.coverage.add(record)
        self.opens_coverage.add(record)
        self.sandboxes.add(record)

    def report(self, correlation: Optional[dict] = None,
               fork_only_exits: int = 0, unmatched_ends: int = 0) -> dict:
        return _summarize_folded(self, correlation=correlation,
                                 fork_only_exits=fork_only_exits,
                                 unmatched_ends=unmatched_ends)


def summarize(records: List[dict], correlation: Optional[dict] = None,
              fork_only_exits: int = 0, unmatched_ends: int = 0) -> dict:
    """The report over a record list. `UX-297`: a fold with the list
    poured into it, so the list-based and streaming paths cannot
    disagree - they are one code path with two callers."""
    fold = Plane2Fold()
    for record in records:
        fold.add(record)
    return fold.report(correlation=correlation,
                       fork_only_exits=fork_only_exits,
                       unmatched_ends=unmatched_ends)


def _summarize_folded(fold: "Plane2Fold", correlation: Optional[dict] = None,
                      fork_only_exits: int = 0, unmatched_ends: int = 0) -> dict:
    by_binary = fold.by_binary
    by_element = fold.by_element
    wall_start, wall_end = fold.wall_start, fold.wall_end
    open_records = fold.open_records
    redundant_operations, redundant_coverage = fold.redundancy.finish()
    return {
        # `UX-297`: the shape this document is. Every report written
        # before this item carried the whole per-process record list
        # under `"processes"` and no stamp; every report written after
        # carries the aggregates alone and this one. A reader that has
        # to tell them apart has a field to read rather than a key to
        # guess from.
        "schema": PLANE2_SCHEMA,
        "process_count": fold.count,
        "matched_count": fold.matched,
        "open_count": open_records,
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
        "max_concurrency": fold.concurrency.finish(),
        # UX-45: real, kernel-measured CPU time per element.
        "cpu_time": fold.cpu_time.finish(),
        # UX-102: of that CPU, how much was the build system working out
        # how to build rather than building.
        "configure_phase": fold.configure.finish(),
        "peak_memory": fold.peak_memory.finish(),
        # `UX-379`: disk, page pressure and preemption, from the struct
        # `peak_memory` above already reads one field of.
        "resource_pressure": fold.pressure.finish(),
        # `UX-378`: the evidence an OOM leaves, which the spine already
        # wrote and no report had a key for.
        "process_outcomes": fold.outcomes.finish(),
        # UX-69: where the time went inside each element, not how many
        # times something ran.
        "binary_cost": fold.binary_cost.finish(),
        # UX-32: per-element achieved parallelism - the question this
        # plane exists to answer. See compute_per_element_parallelism.
        "per_element_parallelism": fold.parallelism.finish(),
        "wall_span_s": (wall_end - wall_start) if wall_start is not None and wall_end is not None else None,
        "redundant_operations": redundant_operations,
        # UX-73: additive sibling key - what the list above excluded and
        # why, and the note that its figures do not add. Kept beside the
        # findings rather than folded into them, the same shape UX-04's
        # `attribution_hints` uses, so an existing consumer of
        # `redundant_operations` sees no change.
        "redundant_operations_coverage": redundant_coverage,
        "static_binary_disclaimer": STATIC_BINARY_DISCLAIMER,
        # UX-107: which mechanism saw each process, as counts rather
        # than as a footnote.
        "stream_coverage": fold.coverage.finish(
            fork_only_exits=fork_only_exits, unmatched_ends=unmatched_ends),
    }


# UX-38: the keys `summarize` always emits. Used to recognize a
# previously-saved JSON *report* being handed to `report`, which
# otherwise parses as zero trace lines and prints a confident, wrong
# "Processes traced: 0" with exit 0.
#
# `UX-297` took `processes` out of that set along with the list itself.
# The remaining four are still emitted by every report this tool has
# ever written, so a legacy monolith is recognized by exactly the same
# rule as a new aggregates-only report - which is what keeps an old
# store readable.
_REPORT_MARKER_KEYS = frozenset({"process_count", "matched_count", "by_binary",
                                 "by_element"})


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


def load_records(raw_log_path: str, merge: bool = True) -> List[dict]:
    """Every process record a raw trace log holds.

    `UX-297` took the record list out of the report, so the log it came
    from is where it lives - which is what a snapshot keeps anyway
    (`plane2.log.gz`) and what the timeline is already rendered from.
    This is the one call that rebuilds it, for the consumers that
    genuinely need per-process rows: the trace converter, and a
    ground-truth test checking records against arithmetic.

    Deliberately **not** on any `bga view` or `bga analyze` path. Every
    published number is a per-element reduction, and reading the rows
    to reach one is the defect this item is about.

    `merge=False` returns the paired rows without `UX-107`'s two-stream
    join, which is what the trace converter has always drawn: one bar
    per *record*, so a dynamically-linked process seen by both the hook
    and the spine gets two. Whether the timeline should draw the merged
    process instead is a real question and `UX-298`'s, not this item's -
    changing it here would have been a silent edit to what the timeline
    shows, under a change about memory.

    `UX-297`: streamed, so the events never exist as a list beside the
    records they became. The rows come back sorted by start, which is
    what `pair_events` always returned and what every caller reads.
    """
    with open(raw_log_path, "r", encoding="utf-8", errors="ignore") as handle:
        records = sorted(stream_records(stream_trace_events(handle)),
                         key=lambda record: record["start_ts"])
    return merge_record_streams(records) if merge else records


def _open_maybe_gzipped(path: str):
    """The raw log, compressed or not (`UX-330`).

    Every snapshot stores its Plane 2 log as `plane2.log.gz` - the
    capture writes it compressed and `bga timeline` and `bga correlate`
    both read it that way. `bga capture report` opened it as plain text,
    found no parseable event in the deflate stream, and said *"this
    error means the file is neither"* a raw trace nor a JSON report.
    It is a raw trace; it is gzipped. The refusal named the one thing
    that was not wrong with the file.

    Detected by magic number rather than by extension: a log named
    `.log` that happens to be compressed is the same file, and a
    reader who renamed it should not get a different answer.
    """
    with open(path, "rb") as probe:
        gzipped = probe.read(2) == b"\x1f\x8b"
    if gzipped:
        return gzip.open(path, "rt", encoding="utf-8", errors="ignore")
    return open(path, "r", encoding="utf-8", errors="ignore")


def load_and_summarize(raw_log_path: str, project_dir: Optional[str] = None,
                       invocation_log_path: Optional[str] = None,
                       plane1_log_path: Optional[str] = None) -> dict:
    """Parse a raw trace log into a report.

    `project_dir` (UX-46) enables the declared-vs-used dependency
    analysis, which needs to ask BuildStream what each element's artifact
    staged. Omitted - the default, and what `report` does without a
    project - the rest of the report is exactly as before.
    """
    # UX-168: stream it. `stream_trace_events` takes the handle directly,
    # so the file is never held as one string beside the events it
    # produced.
    # UX-297: and the events are never held either. This used to build
    # the whole event list, count over it, and pair it - 212.6 MB of a
    # 340.8 MB peak on a 200,000-process trace, for a list nothing kept.
    # Parsing and pairing are now one pass, and the counts the report
    # needs are filled by the pass that already visits every event.
    unmatched = {"fork_only": 0, "unmatched": 0}
    with _open_maybe_gzipped(raw_log_path) as f:
        events = stream_trace_events(f)
        first = next(events, None)
        if first is None and os.path.getsize(raw_log_path) > 0:
            # UX-38: non-empty file, nothing parseable in it. Almost
            # always the wrong file (this tool's own JSON report is the
            # usual culprit); never something to report as "0 processes
            # traced". Asked of the first event rather than of a list,
            # because there is no list any more - and one event is the
            # whole question.
            raise EmptyTraceError(
                f"{raw_log_path}: no trace events could be parsed from this file. "
                "`report` expects a raw trace log (as written by `run --raw-log`). "
                "If this is a JSON report written by `run`, it is now rendered "
                "directly - this error means the file is neither."
            )
        if first is not None:
            events = itertools.chain((first,), events)
        # UX-107: one process, one entry. With the spine running every
        # dynamically-linked process appears in both streams, and
        # summing them would double-count exactly the CPU and
        # concurrency this plane exists to measure. A capture with no
        # spine records passes through unchanged, which is what keeps
        # every pre-spine capture parsing byte-identically.
        # UX-123: counted from the events, since pairing drops them.
        # UX-169: counted *before* pairing, so the event list could be
        # dropped the moment the records existed - a quarter of a
        # gigabyte on a 400k-process trace, alive for no reason at the
        # exact moment the report's own aggregates were being built.
        # UX-297: there is no second walk now, and no list to drop. The
        # pairing pass fills `unmatched` as it runs, because after it
        # the events are gone - and the open-set that count needs is the
        # one that loop already keeps. The records are still sorted by
        # start, which is the order every downstream reader has always
        # seen; that list is the remaining floor, and it is O(processes)
        # rather than O(events).
        records = merge_record_streams(sorted(
            stream_records(events, unmatched),
            key=lambda record: record["start_ts"]))
    fork_only_exits = unmatched["fork_only"]
    unmatched_ends = unmatched["unmatched"]

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
    # `os.path.exists` and not just a truthy path: a build in which no
    # sandbox ran at all - every element a cache hit, which is the
    # *ordinary* second run of UX-126's loop - never creates the file,
    # and this used to raise FileNotFoundError from inside the capture,
    # after the build, discarding a report that was otherwise complete.
    if invocation_log_path and os.path.exists(invocation_log_path) and plane1_log_path:
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
        correlation["elements_in_plane1"] = len(spans)

    # UX-297: fold the records into the aggregates and drop each one as
    # it is folded, rather than holding the whole list through ten
    # functions that each walked it again - and through the `by_key`
    # and `by_signature` maps those functions built beside it.
    # `UX-56`'s relabelling happens on the way in for the same reason:
    # there is no list left to rewrite afterwards.
    fold = Plane2Fold(resolved=(correlation or {}).get("resolved"))
    for index in range(len(records)):
        fold.add(records[index])
        records[index] = None
    del records
    if correlation is not None:
        correlation["relabelled_processes"] = fold.relabelled
    report = fold.report(correlation=correlation,
                         fork_only_exits=fork_only_exits,
                         unmatched_ends=unmatched_ends)
    if spine_policy:
        report["spine_policy"] = spine_policy

    # UX-46: only attempted when a project directory is available, since
    # it needs `bst artifact list-contents` and the project's own
    # declared dependency edges.
    # UX-168: a second streaming pass rather than keeping the whole trace
    # in memory for this one. `OPENS` blocks are a small fraction of a
    # trace, so re-reading costs IO and saves the copy.
    # UX-169: and the handle goes in, not `handle.read()`. The comment
    # above said "streaming" while the call built exactly the whole-file
    # string it was written to avoid.
    with open(raw_log_path, "r", encoding="utf-8", errors="ignore") as handle:
        opens_by_element = parse_open_lines(
            handle,
            open_element_overrides=(correlation or {}).get('resolved'))
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
    element_coverage = fold.opens_coverage.finish()
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
        elements = discover_element_names(project_dir)
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


def _format_resource_pressure(pressure: dict) -> List[str]:
    """`UX-379`'s per-element block, beside `peak_memory` because it is
    the rest of the same `getrusage` call.

    Sums, and says so: unlike the peak above these are events, and a
    reader who has just been told not to sum one column must be told
    that this one may be."""
    if not pressure:
        return []
    if not pressure.get("available"):
        return ["I/O and contention: unavailable - " + pressure.get("note", ""), ""]
    lines = ["I/O, Faults and Contention (summed per element):",
             f"  {'element':40s} {'read':>10s} {'written':>10s} "
             f"{'majflt':>8s} {'preempted':>10s}"]
    for element, entry in pressure["per_element"].items():
        coverage = ""
        if entry["unmeasured"]:
            coverage = (f"  ({entry['measured']} of "
                        f"{entry['measured'] + entry['unmeasured']} measured)")
        lines.append(
            f"  {element:40s} {_human_bytes(entry['read_bytes']):>10s} "
            f"{_human_bytes(entry['written_bytes']):>10s} "
            f"{entry['major_faults']:>8d} "
            f"{entry['involuntary_switches']:>10d}{coverage}")
    lines.append("  NOTE: read/written are block-layer I/O - what reached the "
                 "device - so a cache-served read is genuinely 0. `preempted` "
                 "is involuntary context switches, which rise with "
                 "oversubscription rather than with work.")
    lines.append("")
    return lines


def _human_bytes(value: int) -> str:
    """Bytes at the width this block's column has. Local to the text
    renderer: `bga.units` is the payload's boundary and this is not the
    payload."""
    size = float(value)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def _format_process_outcomes(outcomes: dict) -> List[str]:
    """`UX-378`'s block. Silent on a clean, fully-covered capture and
    loud on a killed one - a heading that always fires teaches a reader
    to skip it, and this is the line they must not skip."""
    if not outcomes:
        return []
    if not outcomes.get("available"):
        return ["How processes ended: unavailable - "
                + outcomes.get("note", ""), ""]
    killed = outcomes.get("killed", 0)
    nonzero = outcomes.get("exited_nonzero", 0)
    if not killed and not nonzero:
        return [f"How processes ended: {outcomes['exited_zero']} exited 0, "
                f"none killed, {outcomes['unknown']} not covered by a spine "
                f"record.", ""]
    lines = ["How Processes Ended:"]
    lines.append(f"  exited 0        {outcomes['exited_zero']:>6d}")
    if nonzero:
        lines.append(f"  exited non-zero {nonzero:>6d}")
    for signal, count in (outcomes.get("killed_by_signal") or {}).items():
        lines.append(f"  killed signal:{signal:<3s} {count:>5d}")
    lines.append(f"  not covered     {outcomes['unknown']:>6d}")
    for element, entry in (outcomes.get("per_element") or {}).items():
        detail = ", ".join(f"{k} x{v}" for k, v in entry["statuses"].items())
        lines.append(f"    {element:38s} {detail}")
    if killed:
        lines.append("  NOTE: a process the kernel killed with signal:9, with "
                     "no cancellation around it, is the shape an OOM kill "
                     "leaves. The host memory series beside this run "
                     "(host-samples.jsonl) says whether memory was the "
                     "reason.")
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
    unmatched = coverage.get("unmatched_ends") or 0
    if collapsed or fork_only or unmatched:
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
                f"{fork_only} exit(s) the spine recorded for pids that never exec'd "
                f"(fork-without-exec children, wearing their parent's command line) "
                f"and are not listed as processes"
            )
        if unmatched:
            # UX-133: said separately, because only the spine can see a
            # fork-only exit. A hook END with no START is a truncated log
            # or a lost START, and calling it a fork-only child asserts
            # something the record cannot support.
            parts.append(
                f"{unmatched} exit(s) have no matching start in the same stream - "
                f"a truncated log or a start lost to a full buffer, not a "
                f"fork-without-exec child"
            )
        lines.append("  " + "; ".join(parts) + " (UX-123, UX-133).")
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
    lines.extend(_format_resource_pressure(report.get("resource_pressure") or {}))
    lines.extend(_format_process_outcomes(report.get("process_outcomes") or {}))
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
    _coverage = report.get("redundant_operations_coverage") or {}
    if redundant:
        lines.append("")
        # UX-37: rank and filter on the wall-clock-relevant figure. A
        # finding worth a millisecond is noise however it is measured,
        # and the previous unfiltered list ran 37 entries deep down to
        # `uname -r` at 0.001s.
        # `UX-375`: both of those now happen where the list is *built*,
        # so the terminal and the contract agree about what a finding
        # is. This reads the counts rather than re-deriving them - the
        # filter lived here alone, and the stored list carried every
        # finding while the terminal showed a shorter one.
        shown = [
            f for f in redundant
            if f.get("max_element_duration_s", f["total_duration_s"])
            >= _REDUNDANCY_MIN_SECONDS
        ]
        below_floor = len(redundant) - len(shown)
        beyond_cap = _coverage.get("omitted_beyond_cap", 0)
        total = _coverage.get("total_findings", len(redundant))
        lines.append(
            f"Redundant cross-element operations ({total} found, "
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
        # No silent truncation (UX-26's own pattern), and `UX-375` gave
        # it a second reason: a finding can be missing from this list
        # for being below the display floor - in which case it *is* in
        # the JSON - or for falling outside the cap, in which case it is
        # not. Two different facts, so two different sentences.
        if below_floor:
            lines.append(
                f"  ({below_floor} further finding(s) below "
                f"{_REDUNDANCY_MIN_SECONDS:.2f}s recoverable wall-clock, "
                f"omitted here - see --json for all of them)"
            )
        if beyond_cap:
            lines.append(
                f"  ({beyond_cap} further finding(s) fall outside the "
                f"{_coverage.get('findings_cap')}-finding cap and are in no "
                f"output; the list is the most costly first, so these are the "
                f"cheapest of what was found)"
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
    coverage = _coverage
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
    # `getattr`: this is reached from callers that build an args object by
    # hand, and a missing project directory is a reason to fall back to
    # the system temp directory, not to fail resolving a log path.
    return os.path.join(
        scratch_mkdtemp(getattr(args, "project_dir", None), "invocations-"),
        "invocations.jsonl",
    )



def _spine_policy(flag: str):
    """`--trace-spine`'s three values, as `run_traced_build` wants them.

    `False`/`True` rather than `"off"`/`"on"` so every existing caller
    and test that passes a bool keeps working unchanged - the flag grew a
    third value, which is not a reason to churn the two already there.
    """
    return {"off": False, "on": True, "auto": "auto"}[flag]


def read_capture_fingerprint(path: str) -> Optional[dict]:
    """The `UX-151` header line, if the record has one."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if entry.get("record") == "fingerprint":
                    return entry
    except OSError:
        pass
    return None


def read_capture_diagnostics(path: str) -> List[dict]:
    """The shim's own records, or an empty list.

    The fingerprint line (`UX-151`) is not one of them: it describes the
    capture, not a sandbox, and counting it as an invocation would make
    "the shim ran 0 times" impossible to say.
    """
    records = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if line.strip():
                    try:
                        entry = json.loads(line)
                    except ValueError:
                        continue
                    if entry.get("record") == "fingerprint":
                        continue
                    records.append(entry)
    except OSError:
        pass
    return records


def _looks_mis_split(record: dict) -> bool:
    """Whether this invocation's parsed command looks like a command.

    Three shapes say it does not, and only the first was checked before
    `UX-151`: a leading flag, a leading bare number (a file descriptor, a
    size or an octal mode - the operand of a newer bwrap option the arity
    table does not know), and a `--` surviving inside the command, which
    means the split fell on the wrong side of bwrap's own separator.
    """
    command = record.get("command") or []
    if not command:
        return False
    first = command[0]
    if first.startswith("-"):
        return True
    if first.isdigit():
        return True
    return "--" in command[1:]


def count_build_tasks(plane1_log_path: Optional[str]) -> Optional[int]:
    """How many element build tasks this run started, or `None`.

    `None` and `0` are different answers and the summary treats them as
    such: no log means "cannot say", and zero means "nothing was ever
    going to launch a sandbox" (`UX-147`).
    """
    if not plane1_log_path or not os.path.exists(plane1_log_path):
        return None
    # `Running commands` is the phase that launches a sandbox, and it is
    # the one whose count matches the shim's: measured on `examples/06`,
    # 9 phases against 9 shim invocations. Staging and caching phases run
    # inside BuildStream and launch nothing.
    started = 0
    try:
        with open(plane1_log_path, "r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if "START" in line and "Running commands" in line:
                    started += 1
    except OSError:
        return None
    return started


def resolve_buildbox_run() -> Optional[str]:
    """Where `buildbox-run` actually is.

    `UX-162` item 1. This field was `shutil.which("buildbox-run")`, which
    is null on every standard install: bst 2.x vendors the binary at
    `site-packages/buildstream/subprojects/buildbox/buildbox-run` and
    never puts it on `PATH`. Verified null live on this container while
    the binary was sitting there - and `UX-151`'s motivation had named
    this exact field as the one a maintainer needs.

    Asking BuildStream where its own subprojects live is the reliable
    answer; `PATH` stays as the fallback for a distro that does install
    it normally.
    """
    try:
        from buildstream import _site
        candidate = os.path.join(_site.subprojects, "buildbox", "buildbox-run")
        if os.access(candidate, os.X_OK):
            return candidate
    except (ImportError, AttributeError, OSError):
        pass
    return shutil.which("buildbox-run")


def _record_line(path: str) -> str:
    """`Record: <path>`, saying "empty" only when the file is.

    `UX-162` item 2. This printed `(empty)` on every zero-invocation
    capture, including one whose record holds `UX-151`'s fingerprint
    line - so a maintainer told to look at an "empty" file found the
    version data they needed sitting in it. "Empty" is a claim about
    the file.
    """
    try:
        empty = os.path.getsize(path) == 0
    except OSError:
        empty = True
    return f"  Record: {path}" + (" (empty)" if empty else "")


def capture_fingerprint() -> dict:
    """What the argv above should be *parsed against* (`UX-151`).

    `UX-146`'s record blames an arity table validated on one bubblewrap
    version and then recorded no version of anything, so a maintainer
    reading a user's JSONL could not tell which table applied. Collected
    once per capture rather than per sandbox.
    """
    def _version(argv):
        try:
            result = subprocess.run(argv, capture_output=True, text=True, timeout=60)
        except (OSError, subprocess.SubprocessError):
            return None
        return (result.stdout or result.stderr or "").strip().splitlines()[:1] or None

    bwrap = shutil.which("bwrap")
    return {
        "record": "fingerprint",
        "bwrap_path": bwrap,
        "bwrap_version": _version([bwrap, "--version"]) if bwrap else None,
        "bst_version": _version(["bst", "--version"]) if shutil.which("bst") else None,
        "buildbox_run_path": resolve_buildbox_run(),
        "arity_table_validated_against": "bubblewrap 0.9.0",
        "platform": platform.platform(),
    }


def read_invocations(path: str) -> List[dict]:
    """Every invocation record in a diagnostics file, fingerprint aside."""
    rows = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if isinstance(row, dict) and "pid" in row:
                    rows.append(row)
    except OSError:
        pass
    return rows


def sandbox_stderr_path(diagnostics: str, row: dict) -> Optional[str]:
    """This invocation's stderr file, as it exists *now*.

    `UX-148`. The path recorded in the row is where the shim wrote it -
    inside the capture's scratch, which no longer exists by the time
    anyone reads the summary. The file is copied out beside the
    diagnostics record under the same name, so the live location is
    derivable; the recorded path stays in the row as provenance and is
    the fallback for a record moved by hand.
    """
    beside = os.path.join(diagnostics + ".stderr", f"{row.get('pid')}.stderr")
    if os.path.exists(beside):
        return beside
    recorded = row.get("stderr_path")
    return recorded if recorded and os.path.exists(recorded) else None


def format_sandbox_stderr(path: str, tail_lines: int = 12) -> Optional[str]:
    """What the failing sandbox said, if `--diagnose` kept it.

    `UX-148` item 2. `buildbox-run` reports only a return code on at
    least one real stack, so `buildbox-run failed with returncode 1` was
    the whole of what a user could see - the record proved the rewrite
    happened and could not say what `bwrap` objected to.

    The *last* invocation with non-empty stderr is the one quoted: the
    build stops at its first failing element, so the sandbox that spoke
    last is the sandbox that died.
    """
    rows = read_invocations(path)
    speaking = [(position, row) for position, row in enumerate(rows, 1)
                if _stderr_size(sandbox_stderr_path(path, row) or "")]
    if not speaking:
        return None
    position, row = speaking[-1]
    live = sandbox_stderr_path(path, row)
    try:
        with open(live, "r", encoding="utf-8", errors="replace") as handle:
            lines = handle.read().splitlines()
    except OSError:
        return None
    if not lines:
        return None
    shown = lines[-tail_lines:]
    elided = len(lines) - len(shown)
    out = [
        "",
        f"  The sandbox for {row.get('element') or 'an unnamed element'} "
        f"(pid {row.get('pid')}) wrote this before it ended:",
        "",
    ]
    if elided:
        # UX-168 item 2: `.get`, not `[...]`. A record written before
        # UX-148 has no `stderr_path`, and this branch would have raised
        # while rendering a *failure* report - the worst place to.
        out.append(f"    ... {elided} earlier line(s) in "
                   f"{row.get('stderr_path') or live}")
    out.extend(f"    {line}" for line in shown)
    out += [
        "",
        f"  Full output: {live}",
        "  Re-run that sandbox directly, without buildbox-run in the way:",
        f"    bga capture replay-sandbox {path} -n {position}",
    ]
    return "\n".join(out)


def _stderr_size(path: str) -> int:
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def replay_sandbox(diagnostics: str, index: Optional[int] = None,
                   listing: bool = False, dry_run: bool = False) -> int:
    """Re-exec one recorded rewritten argv, with nothing in the way.

    `UX-148` item 3. Some sandboxes fail only under BuildStream's exact
    argv, and `bga doctor`'s probe structurally cannot see that class: it
    builds a sandbox out of bga's *own* arguments. This runs the argv
    that actually ran.

    Refuses politely when the recorded binds are gone rather than
    letting `bwrap` fail obscurely: sandbox roots are ephemeral, so a
    partially-expired recording is the common case, and a confusing
    error here would recreate the problem this exists to fix.
    """
    rows = read_invocations(diagnostics)
    if not rows:
        print(f"No invocations recorded in {diagnostics}. A capture with zero "
              f"shim invocations records none - see the capture's own summary "
              f"for why.", file=sys.stderr)
        return 2

    if listing:
        for position, row in enumerate(rows, 1):
            spoke = _stderr_size(sandbox_stderr_path(diagnostics, row) or "")
            print(f"{position:>3}  {row.get('element') or '(unnamed)':<28} "
                  f"pid {row.get('pid')}"
                  + (f"  [{spoke} bytes of stderr]" if spoke else ""))
        return 0

    if index is None:
        speaking = [r for r in rows
                    if _stderr_size(sandbox_stderr_path(diagnostics, r) or "")]
        row = speaking[-1] if speaking else rows[-1]
    elif 1 <= index <= len(rows):
        row = rows[index - 1]
    else:
        print(f"There are {len(rows)} recorded invocation(s); -n must be "
              f"between 1 and {len(rows)}. `--list` shows them.", file=sys.stderr)
        return 2

    argv = row.get("exec_argv") or []
    if not argv:
        print("That record has no exec argv - it predates UX-146.", file=sys.stderr)
        return 2

    missing = missing_bind_paths(argv)
    if missing:
        print(f"Cannot replay: {len(missing)} path(s) this sandbox bound no "
              f"longer exist. Sandbox roots are ephemeral, so a recording "
              f"outlives them:", file=sys.stderr)
        for path in missing[:5]:
            print(f"  {path}", file=sys.stderr)
        if len(missing) > 5:
            print(f"  ... and {len(missing) - 5} more", file=sys.stderr)
        print("Re-run the capture with --diagnose to record a fresh one.",
              file=sys.stderr)
        return 2

    print(f"Replaying {row.get('element') or '(unnamed element)'} "
          f"(pid {row.get('pid')} at capture time)", file=sys.stderr)
    if dry_run:
        print(" ".join(argv))
        return 0
    try:
        return subprocess.run(argv).returncode
    except OSError as error:
        print(f"Could not run {argv[0]}: {error}", file=sys.stderr)
        return 2


# bwrap's own bind options, whose *source* argument is a host path that a
# recording can outlive.
_BIND_FLAGS = frozenset({
    "--bind", "--bind-try", "--ro-bind", "--ro-bind-try",
    "--dev-bind", "--dev-bind-try",
})


def missing_bind_paths(argv: List[str]) -> List[str]:
    """Host paths this argv binds that are no longer there (`UX-148`)."""
    missing = []
    for i, token in enumerate(argv):
        if token in _BIND_FLAGS and i + 1 < len(argv):
            source = argv[i + 1]
            if source.startswith("/") and not os.path.exists(source):
                missing.append(source)
    return missing


def format_post_build_interrupt(report_path: Optional[str],
                                wrapped_log_path: Optional[str],
                                run_dir: Optional[str],
                                project_dir: Optional[str],
                                build_interrupted: bool = False) -> str:
    """What is on disk after an interrupt *between* phases, and how to finish.

    `UX-163` item 2. The build is over by this point: `build.log` is
    complete and `plane2.json` may be too, so nothing needs re-building -
    only the extraction, which is a pure function of the log. Round 17
    got a traceback and a snapshot with no `run/` here, and no
    indication that one command would finish the job.

    `build_interrupted` (`UX-175`) distinguishes the two ways of arriving
    here. A second Ctrl-C during the salvage of a *mid-build* interrupt
    reached the same text, which told the user "the build itself
    completed" about a build that had not - and printed a recovery
    command that would produce a run directory claiming the same thing.
    """
    if build_interrupted:
        lines = ["", "Interrupted again, during the salvage of an interrupted "
                     "build. The build did not finish either; what was "
                     "interrupted this time is bga's own post-processing."]
    else:
        lines = ["", "Interrupted after the build. The build itself completed; "
                     "what was interrupted is bga's own post-processing."]
    kept = [(name, path) for name, path in (
        ("Plane 1 log", wrapped_log_path),
        ("Plane 2 report", report_path),
    ) if path and os.path.exists(path)]
    if kept:
        lines.append("")
        lines.append("  Already on disk:")
        lines.extend(f"    {name}: {path}" for name, path in kept)
    if run_dir and not os.path.isdir(run_dir) and wrapped_log_path \
            and os.path.exists(wrapped_log_path) and project_dir:
        lines += [
            "",
            "  The run directory was not extracted. Nothing needs rebuilding -",
            "  extraction reads the log above, so this finishes the job:",
            "",
            f"    bga extract --format wrapped{' --interrupted' if build_interrupted else ''} "
            f"{project_dir} {wrapped_log_path} {run_dir}",
        ]
        if build_interrupted:
            lines += [
                "",
                "  `--interrupted` is not optional here: without it the "
                "recovered run",
                "  reads as a complete build, and every figure in it would be "
                "presented",
                "  as a measurement of one.",
            ]
    elif run_dir and os.path.isdir(run_dir):
        lines += ["", f"  The run directory is complete: {run_dir}"]
    return "\n".join(lines)


def format_capture_diagnostics(path: str, no_inject: bool = False,
                               sandbox_tasks: Optional[int] = None) -> str:
    """UX-146: the count first, because zero is the answer that matters.

    `sandbox_tasks` is how many element tasks the build actually ran, from
    Plane 1. It is what separates UX-147's three causes of a zero: no
    tasks means nothing was ever going to call the shim, and tasks with no
    shim lines means it was never resolved.

    A capture that produced nothing has two completely different causes -
    the `$PATH` shadow never reaching `buildbox-run`, so the build ran
    entirely unmodified, or the shadow working and the rewrite breaking
    the sandbox - and from outside they are the same silence. The
    invocation count tells them apart in one line, so it leads.
    """
    records = read_capture_diagnostics(path)
    lines = ["", "=" * 60, "Capture diagnostics (UX-146)", "=" * 60]
    if not records:
        # UX-147: zero has three causes and this asserted the benign one.
        # The probe at capture start (`probe_bwrap_shim`) has already
        # excluded the third - the capture would have failed outright -
        # so what is left is told apart by whether any sandbox was
        # supposed to run at all.
        lines += ["  The bwrap shim ran 0 times.", ""]
        if sandbox_tasks is None:
            lines += [
                "  Three things produce that, and this record cannot tell them",
                "  apart on its own:",
            ]
        elif sandbox_tasks == 0:
            lines += [
                "  This build launched no sandbox at all - every element was a",
                "  cache hit - so there was nothing for the shim to be called by.",
                "  That is the benign reading, and here it is the confirmed one.",
            ]
            lines.append(_record_line(path))
            return "\n".join(lines)
        else:
            lines += [
                f"  This build ran {sandbox_tasks} element task(s), so sandboxes were",
                "  launched and the shim was not called by any of them. The shim",
                "  itself is executable - the capture probes that before starting -",
                "  so it was never *resolved*:",
            ]
        # UX-161: when the pre-build check fired, the middle possibility
        # below stops being a guess. The record carries the pid, so this
        # is a reading of evidence rather than a hunch about it.
        stale = (read_capture_fingerprint(path) or {}).get("stale_casd") or []
        if stale:
            pids = ", ".join(str(entry.get("pid")) for entry in stale)
            lines += [
                "",
                f"    A `buildbox-casd` (pid {pids}) was ALREADY RUNNING when this",
                "    capture started - it was warned about then, and it is by far the",
                "    likeliest explanation for this zero. Its environment predates the",
                "    shim directory, so a build that reused it never had the shim on",
                "    $PATH. Stop it (`bst shutdown`, or kill it), re-run, and this",
                "    count should be non-zero.",
                "",
                "  Less likely, if that is not it:",
                "",
                "    - `buildbox-run` found `bwrap` by an absolute path rather than",
                "      through $PATH;",
                "    - or something in the chain sanitises $PATH.",
                "",
            ]
        else:
            lines += [
                "",
                "    - `buildbox-run` found `bwrap` by an absolute path rather than",
                "      through $PATH;",
                "    - or `bst` reused a `buildbox-casd` that was already running",
                "      before this capture, whose environment predates the shim",
                "      directory. No such daemon was running when this capture",
                "      started (UX-161 checks), so this one is unlikely here;",
                "    - or something in the chain sanitises $PATH.",
                "",
            ]
        lines += [
            "  A fully cached build also launches no sandbox, which is benign -",
            "  but this build did run tasks, so that is not what happened here."
            if sandbox_tasks else
            "  A fully cached build launches no sandbox, which is benign.",
            _record_line(path),
        ]
        return "\n".join(lines)

    injected = sum(1 for r in records if r.get("injected"))
    elements = sorted({r.get("element") for r in records if r.get("element")})
    unexecutable = [r for r in records if not r.get("real_bwrap_executable")]
    # UX-151: what a mis-split actually looks like. This checked only
    # `command[0].startswith("-")` - and the mis-splits a post-0.9.0
    # bwrap produces put the flag's *operand* first: a file descriptor, a
    # size, an octal mode. All of those start with a digit, so the one
    # automated detector for the rewrite breaking missed the shapes most
    # likely to occur.
    suspicious = [r for r in records if _looks_mis_split(r)]
    unknown = {}
    for record in records:
        for flag in record.get("unknown_flags") or []:
            unknown[flag] = unknown.get(flag, 0) + 1

    fingerprint = read_capture_fingerprint(path) or {}
    lines += [
        f"  The bwrap shim ran {len(records)} time(s); "
        f"{injected} rewritten, {len(records) - injected} passed through.",
        f"  Real bwrap: {records[-1].get('real_bwrap')}"
        + (f" ({' '.join(fingerprint['bwrap_version'])})"
           if fingerprint.get("bwrap_version") else ""),
    ]
    if fingerprint.get("bst_version"):
        lines.append(f"  {' '.join(fingerprint['bst_version'])}"
                     f"; arity table validated against "
                     f"{fingerprint.get('arity_table_validated_against')}")
    if elements:
        shown = ", ".join(elements[:6])
        more = f" (+{len(elements) - 6} more)" if len(elements) > 6 else ""
        lines.append(f"  Elements seen: {shown}{more}")
    else:
        lines.append("  Elements seen: none recoverable from the argv (UX-56)")
    if unexecutable:
        lines.append(f"  {len(unexecutable)} invocation(s) found no executable "
                     f"bwrap at that path - that alone fails the build.")
    if unknown:
        named = ", ".join(f"{flag} (x{count})" for flag, count in
                          sorted(unknown.items(), key=lambda kv: -kv[1])[:6])
        lines += [
            f"  {len(unknown)} bwrap option(s) this build used are not in the",
            "  shim's arity table, so how many arguments each takes was guessed:",
            f"    {named}",
            "  That guess is zero, and if any of them actually takes an operand the",
            "  rewritten argv is malformed - which bwrap reports as a non-zero exit",
            "  and BuildStream as `buildbox-run failed with returncode 1`.",
        ]
    if suspicious:
        first = suspicious[0]
        lines += [
            f"  {len(suspicious)} invocation(s) parsed a sandboxed command that "
            f"does not look like one:",
            f"    {' '.join((first.get('command') or [])[:4])}",
            "  That is what a mis-split looks like - the first token should be a",
            "  program, not a flag, a number or a separator. Send this file.",
        ]
    if no_inject:
        lines += [
            "",
            "  --no-inject was set, so nothing was captured and no process record",
            "  exists. If this build SUCCEEDED and the same build fails without",
            "  the flag, the argv rewrite is at fault. If it failed here too, the",
            "  shim's presence is - the PATH shadow or the exec, not the rewrite.",
        ]
    lines.append(f"  Record: {path}")
    return "\n".join(lines)


def _CompactRawHelp(prog):
    """UX-158: one shared compact help layout, imported lazily so
    this module stays runnable on its own."""
    from bga.help_format import CompactRawHelp
    return CompactRawHelp(prog)

def main(argv: Optional[List[str]] = None) -> int:
    """`argv` defaults to `sys.argv[1:]`, as argparse does.

    Named so this is callable in-process (`UX-126`'s `bga snapshot`
    composes `capture run` rather than reimplementing it); every existing
    caller passes nothing and is unaffected.
    """
    parser = argparse.ArgumentParser(description=HELP, formatter_class=_CompactRawHelp)
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run a real bst command under the tracer and report on it")
    run_parser.add_argument("project_dir", help="cwd for the wrapped command (the BuildStream project directory)")
    run_parser.add_argument("output", help="Path to write the JSON report to")
    run_parser.add_argument("--raw-log", help="Keep the raw trace log at PATH.")
    run_parser.add_argument(
        "--host-samples", metavar="PATH",
        help="UX-378: where to write the host's memory series while the "
             "build runs (JSON Lines, one sample every "
             f"{HOST_SAMPLE_INTERVAL_S:g}s). Costs 37 microseconds a sample; "
             "without it an OOM leaves no trace but a process with no "
             "observed exit, which is also what a normal wrapper leaves."
    )
    run_parser.add_argument(
        "--invocation-log", metavar="PATH",
        help='Where to write the per-sandbox invocation record.'
    )
    run_parser.add_argument(
        "--no-invocation-log", action="store_true",
        help='UX-80: opt out of the automatic invocation record.'
    )
    run_parser.add_argument(
        "--argv-log", metavar="PATH",
        help='Record the bwrap argv BuildStream generated, as JSON lines.'
    )
    run_parser.add_argument(
        "--trace-opens", action="store_true",
        help='Also record opened files, and unread declared dependencies.'
    )
    run_parser.add_argument(
        "--trace-spine", nargs="?", const="on", default="off",
        choices=("off", "on", "auto"),
        help='UX-106: also run a ptrace process-event spine inside the sandbox, which sees statically-linked processes the LD_PRELOAD hook structurally cannot.'
    )
    run_parser.add_argument(
        "--wrapped-log",
        help='UX-24: also capture a real Plane-1-compatible wrapped-format log of this same bst invocation (tools/bst_log_to_chrome_trace.py-ready) - lets one real build feed both planes for tools/native_trace_to_chrome_trace.py\'s combined mode.'
    )
    run_parser.add_argument(
        "--run-dir", metavar="PATH",
        help='UX-126: also extract a bga run directory (`bga analyze`\'s input) into PATH, from the Plane 1 log this same invocation captures.'
    )
    run_parser.add_argument(
        "--diagnose", action="store_true",
        help='UX-146: record what the bwrap shim received and what it exec\'d, one JSON line per sandbox, and print a summary of it.'
    )
    run_parser.add_argument(
        "--no-inject", action="store_true",
        help='UX-146: install the shim but pass BuildStream\'s bwrap argv through untouched.'
    )
    run_parser.add_argument(
        "--inhibit", action="store_true",
        help="UX-185: stop the machine sleeping while the build runs, via "
             "systemd-inhibit (and gnome-session-inhibit when present)."
    )
    run_parser.add_argument("--json", action="store_true", help="Print the report as JSON to stdout too")
    run_parser.add_argument("cmd", nargs=argparse.REMAINDER, help="The bst command to run, e.g. -- bst build core.bst")

    report_parser = subparsers.add_parser(
        "report",
        help="Summarize a previously captured raw trace log, or re-render a JSON report written by `run`",
    )
    report_parser.add_argument(
        "path",
        help='A raw trace log (as written by `run --raw-log`) or a JSON report (as written by `run`) - the kind is detected, not declared (UX-38)'
    )
    report_parser.add_argument("--json", action="store_true", help="Emit JSON instead of a human-readable summary")
    report_parser.add_argument(
        "--project-dir",
        help='UX-46: the BuildStream project this trace came from.'
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
        help='A BuildStream project directory.'
    )
    census_parser.add_argument(
        "--json", action="store_true", help="Emit JSON instead of a summary",
    )

    # UX-148 item 3: the ten-second local reproduction for the class of
    # failure where the sandbox only breaks under BuildStream's exact
    # argv - which doctor's own-args probe can never see, because it
    # builds a sandbox with bga's arguments rather than BuildStream's.
    replay_parser = subparsers.add_parser(
        "replay-sandbox",
        help="Re-run a recorded sandbox argv directly, without buildbox-run",
    )
    replay_parser.add_argument(
        "diagnostics", help="A capture's .diagnostics.jsonl file.")
    replay_parser.add_argument(
        "-n", type=int, default=None, metavar="N",
        help="Which recorded invocation to replay (1-based). Default: the last "
             "one that wrote to stderr, or the last recorded.")
    replay_parser.add_argument(
        "--list", action="store_true",
        help="List the recorded invocations and exit.")
    replay_parser.add_argument(
        "--dry-run", action="store_true",
        help="Print the argv that would run, and exit.")

    args = parser.parse_args(argv)

    if args.command == "replay-sandbox":
        return replay_sandbox(args.diagnostics, index=args.n,
                              listing=args.list, dry_run=args.dry_run)

    if args.command == "census":
        elements_dir = elements_dir_for(args.project_dir)
        if not os.path.isdir(elements_dir):
            print(f"Error: no {element_path(args.project_dir)}/ directory "
                  f"under {args.project_dir} (the project's declared "
                  f"element-path)", file=sys.stderr)
            return 1
        elements = discover_element_names(args.project_dir)
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

        raw_log_path = args.raw_log or os.path.join(
            scratch_mkdtemp(args.project_dir, "trace-log-"), "trace.log")
        # UX-146: `--no-inject` without the record would answer "did it
        # work?" and nothing else, and the record is the artifact the
        # user sends on.
        diagnostics_path = (f"{args.output}.diagnostics.jsonl"
                            if (args.diagnose or args.no_inject) else None)
        # UX-126: a run directory is extracted *from* the Plane 1 log, so
        # asking for one asks for the log. Same shape as UX-80's implied
        # invocation record: named, it is kept; unnamed, it goes to a
        # temporary path, because what was asked for is the artifact it
        # feeds and not the file itself.
        wrapped_log_path = args.wrapped_log
        if args.run_dir and not wrapped_log_path:
            wrapped_log_path = os.path.join(
                scratch_mkdtemp(args.project_dir, "plane1-"), "build.log")
        args.wrapped_log = wrapped_log_path
        invocation_log_path = resolve_invocation_log_path(args)
        interrupted = False
        try:
            returncode = run_traced_build(args.project_dir, cmd, raw_log_path,
                                          wrapped_log_path=wrapped_log_path,
                                          trace_opens=args.trace_opens,
                                          argv_log_path=args.argv_log,
                                          invocation_log_path=invocation_log_path,
                                          trace_spine=_spine_policy(args.trace_spine),
                                          diagnostics_path=diagnostics_path,
                                          no_inject=args.no_inject,
                                          inhibit=args.inhibit,
                                          host_samples_path=getattr(
                                              args, "host_samples", None))
        except CaptureInterrupted:
            # UX-157: everything below this point is salvage, and it is
            # the same salvage a failed build already got. The trace was
            # copied out of the scratch before the exception reached
            # here; what is left is to analyze what there is and say so.
            interrupted = True
            returncode = 130
            # UX-168 item 4: this used to say "analyzed above" while half
            # the report was still below it. It prints before any of the
            # analysis, so "below" is the whole of it.
            print("\nInterrupted. Analyzing what was captured before the "
                  "interrupt - this is a partial build, and every figure "
                  "that follows describes only the elements that finished.",
                  file=sys.stderr)
        except KeyboardInterrupt:
            # UX-163: the *pre*-build window - compiling the hook, and the
            # census walk, which on a big project is minutes of silence
            # with only UX-159's one line to show for it. Nothing was
            # built, so there is nothing to salvage and nothing to resume.
            print("\nInterrupted before the build started. Nothing was "
                  "captured and nothing was left behind.", file=sys.stderr)
            return 130
        except TraceError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

        if diagnostics_path:
            # UX-147: how many element tasks actually ran, so a zero can
            # be told apart from a cache-hit build. Read from the Plane 1
            # log this same capture wrote.
            print(format_capture_diagnostics(
                diagnostics_path, no_inject=args.no_inject,
                sandbox_tasks=count_build_tasks(wrapped_log_path)),
                file=sys.stderr)
            # UX-148 item 2: on a failed build, the generic return code
            # becomes "and here is what bwrap said".
            if returncode != 0:
                spoke = format_sandbox_stderr(diagnostics_path)
                if spoke:
                    print(spoke, file=sys.stderr)

        # UX-163: everything after the build is unprotected without this.
        # Round 17 SIGINTed a capture during `Extracting run data...` and
        # got a raw traceback and a snapshot with no `run/` - even though
        # `build.log` was complete on disk and extraction is re-runnable
        # from it, which nothing said. On a big project these are the
        # long phases: they are the ones UX-159 gave announcement lines
        # *because* they take minutes, so they are exactly where a user
        # who has already waited three hours presses Ctrl-C.
        try:
            print("Analyzing the captured trace...", file=sys.stderr)
            report = load_and_summarize(raw_log_path, project_dir=args.project_dir,
                                        invocation_log_path=invocation_log_path,
                                        plane1_log_path=wrapped_log_path)
            report["wrapped_command_exit_code"] = returncode
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)
            # UX-296: and the two capacity scalars the store's aggregate
            # needs, beside it. Written here because here is the one
            # moment the report is already in memory - every reader that
            # wanted them used to parse the whole document again, once
            # per snapshot, on every page load.
            from bga.run_store import RESOURCE_NAME, write_resource_profile
            write_resource_profile(
                os.path.join(os.path.dirname(os.path.abspath(args.output)),
                             RESOURCE_NAME),
                report)
            if args.run_dir:
                # Best-effort, and after the report is on disk: a build that
                # failed early produces a log with no `Targets:` line, and
                # losing the Plane 2 capture over that would throw away the
                # expensive half of what just ran.
                from .bst_extract_run import extract_run
                print("Extracting run data (bst show)...", file=sys.stderr)
                try:
                    extract_run(args.project_dir, wrapped_log_path, args.run_dir,
                                log_format="wrapped", interrupted=interrupted)
                except Exception as exc:  # noqa: BLE001 - reported, not swallowed
                    print(f"Warning: could not extract a run directory into "
                          f"{args.run_dir}: {exc}", file=sys.stderr)
                else:
                    print(f"Run directory: {args.run_dir}", file=sys.stderr)
            if args.json:
                print(json.dumps(report, indent=2))
            else:
                print(_format_text(report))
                print(f"\nWrapped command exit code: {returncode}")
            # UX-147 item 5: the failing user is told what would answer the
            # question. Only when it was not already asked for, and only on a
            # failure - a working capture does not need advice.
            if returncode != 0 and not diagnostics_path and not interrupted:
                print(
                    "\nThe wrapped build failed. If it succeeds under plain `bst` and "
                    "only fails here, re-run with --diagnose: it records what the "
                    "bwrap shim received and exec'd, and the invocation count alone "
                    "separates the three things that produce this.",
                    file=sys.stderr)
            return returncode
        except KeyboardInterrupt:
            print(format_post_build_interrupt(
                args.output, wrapped_log_path, args.run_dir,
                args.project_dir, build_interrupted=interrupted),
                file=sys.stderr)
            return 130

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
            elements = discover_element_names(args.project_dir)
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
