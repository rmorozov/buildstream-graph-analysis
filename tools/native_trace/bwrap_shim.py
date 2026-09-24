#!/usr/bin/env python3
"""A `bwrap` shim placed ahead of the real `/usr/bin/bwrap` in `$PATH` -
the mechanism validated for real in UX-11's Deep Experiment (see
docs/backlog/scenarios/UX-0011-native-build-system-profiler-tool.md): a naive
top-level `$PATH` shadow of `bwrap` really does reach BuildStream's real
sandbox creation (`buildbox-run`'s own subprocess spawn), contrary to an
external review's unverified claim that it "often fails to penetrate"
BuildStream's C++ daemon layer.

`split_bwrap_args` is the one piece of real logic this shim depends on,
and it is deliberately kept as a pure, standalone function (no bwrap/bst
needed to test it) - during the real prototype this exact split was
needed to fix two real, confirmed bugs:

1. Injecting extra `--bind`/`--setenv` args *before* BuildStream's own
   args caused BuildStream's own root-filesystem bind (`--bind
   <cas-tmpdir> /`) to silently wipe them out, since it rebinds "/"
   itself over anything mounted earlier - the injected bind must land
   *after* all of BuildStream's own mount-setup options, not before.
2. A first attempt mis-parsed `--dir`'s arity (assumed 2 trailing args
   like `--bind`; it only takes 1), corrupting the argv split and
   producing "bwrap: Can't chdir to --bind: No such file or directory".

Both bugs are exactly why this is a real, tested function instead of an
inline shell one-liner: the same class of arity mistake is trivial to
reintroduce by hand and easy to miss without a fixture-driven test
(tests/unit/test_bwrap_shim.py exercises real captured bwrap argv from
UX-11's own prototype run).
"""
import contextlib
import fnmatch
import json
import os
import re
import select
import signal
import subprocess
import sys
import time
from typing import Optional

# bwrap flags, keyed by how many trailing positional args each consumes.
#
# UX-151: this used to list only the flags BuildStream's own invocation
# was *confirmed* to emit, with everything else conservatively assumed to
# take none. That assumption is the likeliest field failure this tool
# has: a newer `buildbox-run` emitting, say, `--json-status-fd 12` makes
# the split stop at the flag's own operand -
# `opts=["--json-status-fd"]`, `command=["12", "--bind", ...]` - and the
# rewritten argv hands bwrap garbage. bwrap exits non-zero and the user
# sees `buildbox-run failed with returncode 1`, unchanged by turning
# either optional mechanism off, because the injection happens either
# way.
#
# So the table is now bubblewrap's *whole* option set, transcribed from
# `bwrap --help` at 0.9.0 (the version this was checked against, printed
# into every diagnostics record by UX-151 so a reader can tell), plus the
# post-0.9.0 overlay family. An unknown flag is still assumed to take no
# arguments - there is no safer guess - but it is now *recorded and
# reported* rather than silently believed.
_THREE_ARG_FLAGS = {"--overlay"}
_TWO_ARG_FLAGS = {
    "--bind", "--bind-try", "--dev-bind", "--dev-bind-try",
    "--ro-bind", "--ro-bind-try", "--bind-fd", "--ro-bind-fd",
    "--file", "--bind-data", "--ro-bind-data", "--symlink",
    "--setenv", "--chmod",
}
_ONE_ARG_FLAGS = {
    "--args", "--argv0", "--userns", "--userns2", "--pidns",
    "--uid", "--gid", "--hostname", "--chdir", "--unsetenv",
    "--lock-file", "--sync-fd", "--remount-ro", "--exec-label",
    "--file-label", "--proc", "--dev", "--tmpfs", "--mqueue", "--dir",
    "--seccomp", "--add-seccomp-fd", "--block-fd", "--userns-block-fd",
    "--info-fd", "--json-status-fd", "--cap-add", "--cap-drop",
    "--perms", "--size",
    # post-0.9.0
    "--overlay-src", "--tmp-overlay", "--ro-overlay",
}
_ZERO_ARG_FLAGS = {
    "--help", "--version", "--unshare-all", "--share-net",
    "--unshare-user", "--unshare-user-try", "--unshare-ipc",
    "--unshare-pid", "--unshare-net", "--unshare-uts",
    "--unshare-cgroup", "--unshare-cgroup-try",
    "--disable-userns", "--assert-userns-disabled",
    "--clearenv", "--new-session", "--die-with-parent", "--as-pid-1",
    # post-0.9.0
    "--level-prefix",
}

KNOWN_FLAGS = _THREE_ARG_FLAGS | _TWO_ARG_FLAGS | _ONE_ARG_FLAGS | _ZERO_ARG_FLAGS


def unknown_flags(args: list[str]) -> list[str]:
    """Option-looking tokens the table has no arity for, in order.

    Reported rather than reasoned about: an unknown flag means the split
    below is a guess, and a reader of the diagnostics record should be
    told which guess was made. `--args FD` deserves particular suspicion
    - it tells bwrap to read *more arguments from a file descriptor*, so
    an argv containing it is not fully visible here at all.
    """
    seen, i, n = [], 0, len(args)
    while i < n:
        arg = args[i]
        if arg in _THREE_ARG_FLAGS:
            i += 4
        elif arg in _TWO_ARG_FLAGS:
            i += 3
        elif arg in _ONE_ARG_FLAGS:
            i += 2
        elif arg in _ZERO_ARG_FLAGS:
            i += 1
        elif arg.startswith("--"):
            seen.append(arg)
            i += 1
        else:
            break
    return seen


def split_bwrap_args(args: list[str]) -> tuple[list[str], list[str]]:
    """Split a real bwrap argv (as BuildStream generates it) into
    (options, command): every leading `--flag [args...]` bwrap option,
    then the trailing positional command to exec inside the sandbox
    (e.g. `["sh", "-c", "-e", "..."]`). Stops at the first token that
    isn't a recognized `--`-prefixed option and isn't consumed as that
    option's own argument - matching bwrap's own "first non-option token
    starts the command" parsing.

    A flag not in any of the three known sets (forward-compatibility
    with a future bwrap version) is conservatively treated as taking 0
    args - the same posture bwrap itself would need it to have to be
    followed directly by another `--flag`, and safer than guessing an
    arity that could swallow real command tokens.
    """
    i = 0
    n = len(args)
    opts: list[str] = []
    while i < n:
        arg = args[i]
        if arg in _THREE_ARG_FLAGS:
            opts.extend(args[i:i + 4])
            i += 4
        elif arg in _TWO_ARG_FLAGS:
            opts.extend(args[i:i + 3])
            i += 3
        elif arg in _ONE_ARG_FLAGS:
            opts.extend(args[i:i + 2])
            i += 2
        elif arg in _ZERO_ARG_FLAGS or arg.startswith("--"):
            opts.append(arg)
            i += 1
        else:
            break
    return opts, list(args[i:])


def extract_element_name(opts: list[str]) -> Optional[str]:
    """UX-23: BuildStream's own generated bwrap argv always includes a
    real `--dir buildstream/<project-name>/<element>.bst` option (the
    sandbox's own working directory, confirmed present in every real
    captured invocation this whole `UX-11`/`UX-23` arc has examined) -
    the element name is its own path's last segment. Returns `None` if
    no `--dir` option is present (defensive - a future BuildStream
    version could drop or rename it; element tagging is additive, never
    load-bearing for the interception mechanism itself).
    """
    for i, opt in enumerate(opts):
        if opt == "--dir" and i + 1 < len(opts):
            return element_from_build_root(opts[i + 1])
    return None


# BuildStream's default build root is `buildstream/<project-name>/<element>`,
# where `<element>` is the element's *project-relative* name and so may
# itself contain directories.
_BUILD_ROOT = "buildstream"


def element_from_build_root(path: str) -> Optional[str]:
    """The element name BuildStream would call this build root's element.

    `UX-160`. This used to be "the last path segment", which is right
    only for a project whose elements all sit at the top of the element
    directory - the layout every example in this repository happens to
    use. Measured on a nested copy of `examples/06`:

        --dir buildstream/<project>/components/core.bst

    so the last segment is `core.bst` while BuildStream, Plane 1, and a
    recursive census all call that element `components/core.bst`. Making
    the census recursive *without* this would have left every nested
    element unassessed, with the census carrying entries nobody looks
    up - and `--trace-spine=auto` then traces them all at full price,
    which is the bill this item is about.

    Anything that is not a `buildstream/<project>/...` path keeps the
    old last-segment answer: under a `build-root` override (`UX-56`)
    every element collapses to the same directory, and inventing
    structure there would be worse than the flat name.
    """
    parts = [part for part in path.strip("/").split("/") if part]
    if len(parts) >= 3 and parts[0] == _BUILD_ROOT:
        return "/".join(parts[2:])
    return parts[-1] if parts else None


# make/autotools compose `MAKEFLAGS: -j%{max-jobs}`; cmake composes
# `JOBS: -j%{max-jobs}` too, but meson composes `JOBS` as a bare
# integer (verified: `bst show --format '%{env}'` on a `notparallel`
# meson element prints `JOBS: 1`, not `JOBS: -j1`) - so `JOBS` alone
# also accepts a bare int, `MAKEFLAGS` never does.
_JOB_SETENV_VARS = ("MAKEFLAGS", "JOBS")
_JOB_FLAG_RE = re.compile(r"-j\s*(\d+)|--jobs=(\d+)")
_BARE_INT_RE = re.compile(r"^(\d+)$")

JOBSERVER_PINNED = "pinned"
JOBSERVER_JOINED = "joined"
JOBSERVER_CAPPED_PENDING = "capped_pending"


def parse_element_max_jobs(opts: list[str]) -> Optional[int]:
    """UX-842/UX-843: the element's own `-jK`, read from BuildStream's
    own composed `--setenv MAKEFLAGS`/`--setenv JOBS` - the argv-level
    fact that a `notparallel` pin (`-j1`, or meson's bare `1`) really
    is. `None` when neither shape matches (no `-j` at all)."""
    for i, opt in enumerate(opts):
        if (opt == "--setenv" and i + 2 < len(opts)
                and opts[i + 1] in _JOB_SETENV_VARS):
            value = opts[i + 2]
            match = _JOB_FLAG_RE.search(value)
            if match:
                return int(match.group(1) or match.group(2))
            if opts[i + 1] == "JOBS":
                bare = _BARE_INT_RE.match(value.strip())
                if bare:
                    return int(bare.group(1))
    return None


def jobserver_decision(element_max_jobs: Optional[int],
                       project_max_jobs: Optional[int]) -> str:
    """UX-842: `pinned` (`-j1` - no injection at all), `joined` (`-jK`
    equal to the project's own `max-jobs`, no `-j` entry at all, or the
    project's `max-jobs` itself unknown - `project_max_jobs_unknown`),
    `capped_pending` (any other `K` - joins uncapped until `UX-849`'s
    proxy caps it)."""
    if element_max_jobs == 1:
        return JOBSERVER_PINNED
    if element_max_jobs is None or project_max_jobs is None:
        return JOBSERVER_JOINED
    if element_max_jobs == project_max_jobs:
        return JOBSERVER_JOINED
    return JOBSERVER_CAPPED_PENDING


JOBSERVER_UNKNOWN_KIND = "unknown_kind"

# UX-843: cmake and meson compose `JOBS: -j%{max-jobs}` as a literal
# flag on the generator's own command line - beside a jobserver auth
# that resets `make` (Motivation). make/autotools already join via
# MAKEFLAGS alone; cargo is a client and only needs its own env unset.
_MAKE_LIKE_KINDS = frozenset({"make", "autotools"})
_NINJA_CAPABLE_KINDS = frozenset({"cmake", "meson"})


def compiler_safe_auth(auth_value: str, sandbox_fifo_path: Optional[str],
                       make_below_44: bool) -> Optional[str]:
    """UX-878: the `MAKEFLAGS` auth an *unwrapped* native jobserver
    client (gcc's lto-wrapper, cargo) reads directly - unlike `ninja`/
    `ld.*`/`mold`, no shell wrapper stands between it and the string bga
    injected. A `fifo:` auth is already path-based and stands. A raw
    `fd` auth is only valid for a direct child - gcc's lto-wrapper is a
    deep grandchild, so the fd number is not open there (measured:
    GCC-13 ICE, `opts-common.cc:2123`) - rewritten to `fifo:
    <sandbox_fifo_path>` instead, which gcc-13 reopens by path. Unless a
    sub-4.4 make shares the recipe and would reject that `fifo:` outright
    (UX-874): then `None`, so the caller scrubs the auth for both rather
    than re-arm either defect."""
    if "fifo:" in auth_value:
        return auth_value
    if make_below_44:
        return None
    return f"--jobserver-auth=fifo:{sandbox_fifo_path}"


def _ninja_aware_env(ninja_probe, wrappers_dir, auth_value, base_policy):
    """UX-843/UX-859: `JOBS` emptied, `MAKEFLAGS` injected, gated on
    what the sandbox's own `ninja --version`/`--help` probe found -
    shared by the cmake/meson table row and a table-less kind that
    spends `JOBS` itself (`base_policy` names the no-ninja-info case)."""
    if ninja_probe and ninja_probe.get("available"):
        if ninja_probe.get("jobserver_client"):
            return [("JOBS", ""), ("MAKEFLAGS", auth_value)], [], "ninja_client"
        if wrappers_dir:
            # UX-846's ninja wrapper reads the auth from MAKEFLAGS.
            return [("JOBS", ""), ("MAKEFLAGS", auth_value)], [], "ninja_wrapper"
        return [], [], "ninja_static"
    return [("JOBS", ""), ("MAKEFLAGS", auth_value)], [], base_policy


def kind_job_env(kind, auth_value, ninja_probe=None, wrappers_dir=None,
                 jobs_present=None):
    """The `(setenv_pairs, unsetenv_vars, policy)` this element's kind
    gets, applied only for a `joined`/`capped_pending` decision.
    `ninja_probe` is `{"available", "jobserver_client"}` or `None` (not
    run, or no ninja in the sandbox - the make path, same injection as
    a plain make generator). `jobs_present` (UX-859, default `None` so
    every prior caller stands) is whether BuildStream's own composed
    argv set `JOBS` for this sandbox - a kind outside the table gets
    the cmake treatment under it (policy `jobs_env`) rather than
    `unknown_kind` when it carries one, since `JOBS` is the recipe's
    own promise to spend it, whatever its kind."""
    if kind in _MAKE_LIKE_KINDS:
        return [("MAKEFLAGS", auth_value)], [], "make"
    if kind == "cargo":
        return [("MAKEFLAGS", auth_value)], ["CARGO_BUILD_JOBS"], "cargo"
    if kind in _NINJA_CAPABLE_KINDS:
        return _ninja_aware_env(ninja_probe, wrappers_dir, auth_value, "cmake_meson")
    if jobs_present:
        return _ninja_aware_env(ninja_probe, wrappers_dir, auth_value, "jobs_env")
    return [], [], JOBSERVER_UNKNOWN_KIND


def parse_ninja_help(text: str) -> bool:
    """UX-843: does `ninja --help`'s text name a jobserver client? 1.11.1
    on this box does not (pasted in the task file's Outcome); a ninja
    that speaks the protocol names it in its own help text."""
    return "jobserver" in text.lower()


_NINJA_VERSION_RE = re.compile(r"^(\d+)\.(\d+)")
# UX-1001: 1.13's client never names itself in `--help` - read the version too.
_NINJA_CLIENT_MIN_VERSION = (1, 13)


def ninja_is_client(version: Optional[str], helptext: str) -> bool:
    """UX-843/UX-1001: a help text naming the jobserver, or a version at or
    past the first release that ships the client (1.13.0)."""
    match = _NINJA_VERSION_RE.match((version or "").strip())
    by_version = bool(match) and \
        (int(match.group(1)), int(match.group(2))) >= _NINJA_CLIENT_MIN_VERSION
    return by_version or parse_ninja_help(helptext)


def _probe_tool_version(real_bwrap: str, opts: list[str], tool: str,
                        timeout: float) -> subprocess.CompletedProcess:
    """The one `<tool> --version` subprocess call site `probe_ninja` and
    `probe_make` (UX-874) both use - a second sandbox-tool probe is a
    new caller of the same forced S603 (UX-843), not a new finding."""
    version = subprocess.run(
        [real_bwrap, *opts, tool, "--version"],
        capture_output=True, text=True, timeout=timeout, check=False)
    return version


def probe_ninja(real_bwrap: str, opts: list[str], cache_path: Optional[str],
                timeout: float = 5.0) -> dict:
    """UX-843: `ninja --version` then `--help`, run through this same
    sandbox argv with the trailing command replaced - once per capture,
    cached at `cache_path` beside the FIFO. Never raises: a probe that
    cannot run just means no ninja client, the safer of the two guesses.
    """
    if cache_path:
        with contextlib.suppress(OSError, ValueError), \
                open(cache_path, encoding="utf-8") as handle:
            return json.load(handle)
    result = {"available": False, "version": None, "jobserver_client": None}
    try:
        version = _probe_tool_version(real_bwrap, opts, "ninja", timeout)
        if version.returncode == 0 and version.stdout.strip():
            result["available"] = True
            result["version"] = version.stdout.strip()
            helptext = subprocess.run(
                [real_bwrap, *opts, "ninja", "--help"],
                capture_output=True, text=True, timeout=timeout, check=False)
            result["jobserver_client"] = ninja_is_client(
                result["version"], helptext.stdout + helptext.stderr)
    except (OSError, subprocess.TimeoutExpired):
        pass
    if cache_path:
        with contextlib.suppress(OSError), \
                open(cache_path, "w", encoding="utf-8") as handle:
            json.dump(result, handle)
    return result


_MAKE_VERSION_RE = re.compile(r"GNU Make (\d+)\.(\d+)")
_MAKE_JOBSERVER_AUTH_MIN_VERSION = (4, 4)


def style_for_make_version(make_version_output: Optional[str]) -> str:
    """UX-841's cutoff, shared: `"fifo"` for GNU Make >= 4.4, `"fd"`
    otherwise (absent/unparseable included). `jobserver_auth_style`'s
    host pick and UX-874's sandbox probe below both apply this one
    function rather than each carrying its own regex and tuple."""
    match = _MAKE_VERSION_RE.search(make_version_output or "")
    if not match:
        return "fd"
    version = (int(match.group(1)), int(match.group(2)))
    return "fifo" if version >= _MAKE_JOBSERVER_AUTH_MIN_VERSION else "fd"


def probe_make(real_bwrap: str, opts: list[str], cache_path: Optional[str],
               timeout: float = 5.0) -> dict:
    """UX-874: `make --version` run through this same sandbox argv -
    `probe_ninja`'s own shape, cached at `cache_path`
    (`_make_probe_cache_path`: per element, not per capture -
    `ninja_probe.json`'s own sharing is wrong for a make that can
    genuinely differ element to element). Never raises: a probe that
    cannot run just means an absent sandbox make, exactly
    `style_for_make_version`'s own "fd" case."""
    if cache_path:
        with contextlib.suppress(OSError, ValueError), \
                open(cache_path, encoding="utf-8") as handle:
            return json.load(handle)
    result = {"available": False, "version": None}
    try:
        version = _probe_tool_version(real_bwrap, opts, "make", timeout)
        if version.returncode == 0 and version.stdout.strip():
            result["available"] = True
            result["version"] = version.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    if cache_path:
        with contextlib.suppress(OSError), \
                open(cache_path, "w", encoding="utf-8") as handle:
            json.dump(result, handle)
    return result


def _make_probe_cache_path(jobserver_path: Optional[str],
                           element: Optional[str]) -> Optional[str]:
    """UX-874 (verifier): `ninja_probe.json`'s own cache is shared by
    the whole capture (one `dirname(BST_TRACE_JOBSERVER)`, set once in
    `run_traced_build`) - real for ninja (one generator per build) but
    wrong for make: two make-kind elements can genuinely tar-stage
    different makes (the junctioned/toolchain shape), and a shared key
    would hand the second element the first one's stale answer,
    reproducing the exact defect this item fixes. Keyed per element
    (`main`'s own `element`, already derived by `extract_element_name`)
    - `ninja_probe.json`'s per-capture cache is unchanged, a separate,
    pre-existing matter."""
    if not jobserver_path:
        return None
    tag = (element or "unknown").replace("/", "_")
    return os.path.join(os.path.dirname(jobserver_path), f"make_probe-{tag}.json")


# UX-877: `kind_job_env`'s own policy names whose MAKEFLAGS a *make*
# reads - ninja_client/ninja_wrapper/ninja_static hand MAKEFLAGS (or
# nothing) to ninja, not make, so fifo is never a problem for them.
_MAKE_CONSUMER_POLICIES = frozenset({"make", "cargo", "cmake_meson", "jobs_env"})

# UX-878: of those, the policies whose MAKEFLAGS an *unwrapped* native
# jobserver client (gcc-lto, cargo) reads directly - "make" excluded,
# since its MAKEFLAGS consumer is make itself, a direct child, for which
# a raw fd is valid. UX-1001: ninja_client too - ninja 1.13 reads only `fifo:`.
_COMPILER_SAFE_POLICIES = frozenset({"cmake_meson", "jobs_env", "cargo", "ninja_client"})

# UX-913: of those, the policies whose MAKEFLAGS consumer is `make`
# itself - a direct child, for which a raw fd is valid - so the scrub
# does not apply and the auth stands (it cost every make-4.3 cmake
# element its jobserver: `11-serial-giant` read `peak 2` against a
# ceiling of 4). The `flto/` shims are NOT mounted with it - they need
# `dirname`, which a staged-toolchain sandbox has not got; an element
# that also drives LTO takes the `flto` override.
_FD_DIRECT_POLICIES = frozenset({"cmake_meson"})

# UX-879: the styles a per-element override may force. UX-880: `flto`
# added - keeps the raw auth like `fd` (falls through `_forced_auth`
# the same way), and is the glob a wrapper-directory GCC-driver shim
# (tools/native_trace/wrappers/gcc et al.) reads `-flto` for.
_AUTH_OVERRIDE_STYLES = frozenset({"fd", "fifo", "off", "flto"})


def resolve_auth_override(auth_map_str: Optional[str],
                          element: Optional[str]) -> Optional[str]:
    """`BST_TRACE_JOBSERVER_AUTH_MAP`'s own serialization -
    `style:glob[,glob];style:glob...` (`bga capture run
    --jobserver-auth-override`, UX-879) - resolved against one element
    name. First matching style wins across the `;`-separated groups.
    `None` for an empty/absent map, no element name, or no glob match -
    the caller's own auto/compiler_safe path then stands unchanged.
    Pure (no I/O), so this is unit-testable without a sandbox.
    """
    if not auth_map_str or not element:
        return None
    for group in auth_map_str.split(";"):
        style, sep, globs = group.partition(":")
        style = style.strip()
        if not sep or style not in _AUTH_OVERRIDE_STYLES:
            continue
        for glob in globs.split(","):
            if glob.strip() and fnmatch.fnmatch(element, glob.strip()):
                return style
    return None


def _forced_auth(override: str, auth_value: str, ctx: dict) -> Optional[str]:
    """UX-879: `auth_value` narrowed by a matched per-element override
    instead of `_compiler_safe_makeflags` - `fd` keeps `auth_value` raw,
    exactly as `_jobserver_injection` computed it pre-UX-878 (no fifo
    rewrite, no scrub); `off` scrubs it (`None`), reusing the same
    downstream MAKEFLAGS/JOBS drop UX-878's own scrub already triggers;
    `fifo` rewrites to the `fifo:` path when one is derivable (the same
    lookup `_compiler_safe_makeflags` uses), else leaves `auth_value`
    unchanged rather than crash on an element with no FIFO to name.
    UX-880: `flto` falls through to the same raw-`auth_value` branch as
    `fd` - `make` keeps filling the pool, and it is the wrapper-mounted
    GCC-driver shim, not this function, that strips the fd auth before
    it ever reaches `lto-wrapper`. `ctx`: `{bind_src, bind_dst, pool,
    element}` - the same bundling `_compiler_safe_makeflags` uses for
    PLR0913's cap.
    """
    if override == "off":
        return None
    if override == "fifo" and "fifo:" not in auth_value:
        host_fifo = _compiler_safe_fifo_host(ctx["pool"], ctx.get("element"))
        if host_fifo is not None:
            sandbox_fifo_path = _sandbox_fifo_path(
                ctx["bind_src"], ctx["bind_dst"], host_fifo)
            return f"--jobserver-auth=fifo:{sandbox_fifo_path}"
    return auth_value


def sandbox_make_auth_style(element_kind: Optional[str], real_bwrap: str,
                            opts: list[str], cache_path: Optional[str],
                            kind_probe: Optional[dict] = None) -> str:
    """UX-874/UX-877: this element's own sandbox `make --version`,
    probed through the real bwrap - `"fd"` when the sandbox make can't
    parse `fifo:` (absent, unparseable, or below 4.4), `"fifo"`
    otherwise. Probed for every kind `kind_job_env` would actually hand
    a `MAKEFLAGS` a *make* reads - derived by calling it with a
    sentinel auth rather than hand-keeping a second kind list, so a
    kind added to the table there is covered here for free. `kind_probe`
    (`{ninja_probe, wrappers_dir, jobs_present}` or `None`, PLR0913's
    cap) is `kind_job_env`'s own remaining inputs. A kind whose own
    result carries no `MAKEFLAGS`, or hands it to ninja instead
    (`_MAKE_CONSUMER_POLICIES`), is reported unnarrowed - the style the
    host already resolved stands, never widened by this probe."""
    kind_probe = kind_probe or {}
    pairs, _unsets, policy = kind_job_env(
        element_kind, "fifo:sentinel", kind_probe.get("ninja_probe"),
        kind_probe.get("wrappers_dir"), kind_probe.get("jobs_present"))
    makeflags_injected = any(var == "MAKEFLAGS" for var, _ in pairs)
    if not makeflags_injected or policy not in _MAKE_CONSUMER_POLICIES:
        return "fifo"
    probe = probe_make(real_bwrap, opts, cache_path)
    return style_for_make_version(probe.get("version"))


# UX-846: where the wrapper directory lands inside the sandbox - under
# the trace bind rather than a new top-level path, since a real sandbox
# root is not writable for an unbound directory (`bwrap: Can't mkdir
# parents for /.bga/wrappers: Read-only file system`, measured live).
# Key-invisible like `bind_dst` itself, so no cache key ever names it.
WRAPPER_BIND_SUBDIR = "wrappers"


def _setenv_value(opts: list[str], name: str) -> Optional[str]:
    """The value of BuildStream's own `--setenv <name> <value>`, if any.

    UX-846: bwrap's last `--setenv` for a variable wins outright rather
    than merging (measured with a real `bwrap --setenv PATH a --setenv
    PATH b` - `$PATH` inside came out `b`, not `a:b`) - so a wrapper
    `PATH` splice has to read BuildStream's own value and prepend to it,
    not just append a second `--setenv`.
    """
    for i, opt in enumerate(opts):
        if opt == "--setenv" and i + 1 < len(opts) and opts[i + 1] == name and i + 2 < len(opts):
            return opts[i + 2]
    return None


def _wrapper_mount(opts: list[str], wrapper_dir: str, bind_dst: str,
                   caps: Optional[dict] = None) -> list[str]:
    """UX-846: the wrappers bound read-only ahead of BuildStream's own
    `PATH` (bwrap: the last `--setenv` wins outright, measured), with
    the ledger path and the cap the wrapper reads. `caps` (PLR0913's
    cap, UX-880 pushed a 4th env past the 5-arg baseline): `{wrapper_cap,
    lto_cap, flto_active, wrapper_dir_override, wrapper_mode}`. `lto_cap`
    (`BST_TRACE_LTO_CAP`) is the same shape as `wrapper_cap` - read by
    the GCC-driver shim in this same directory, not the held-tool
    wrappers `wrapper_cap` sizes. `flto_active`: the GCC-driver shims
    live in a `flto/` subdir put on `PATH` (ahead of the held-tool dir)
    ONLY for a flto-matched element, so a bystander sandbox this mounts
    for held-tool coverage never has `cc`/`gcc` shadowed by a shim it
    cannot source (a minimal make element has no `dirname`: bst-examples
    exit 255). Belt-and-suspenders, `BST_TRACE_FLTO_ACTIVE=1` is also
    set, and the shim gates on it too; both come from
    `_jobserver_injection`'s already-resolved `override`, never
    re-derived (re-matching the glob in the shell would drift).

    UX-881: `wrapper_dir_override` (an operator's own directory,
    matching bga's published wrapper contract) is prepended to `PATH`
    ahead of the shipped one when `wrapper_mode` is `augment` (default,
    or unset) - a second `--ro-bind`, so a replace loses nothing this
    element already had. `replace` binds ONLY the operator's directory
    at the shipped mount point - no shipped dir, no shipped `flto/`
    subdir, since the operator's directory is theirs to populate. No
    override: today's single-mount behaviour, byte for byte."""
    caps = caps or {}
    bst_path = _setenv_value(opts, "PATH") or "/usr/bin:/bin"
    dst = os.path.join(bind_dst, WRAPPER_BIND_SUBDIR)
    override_dir = caps.get("wrapper_dir_override")
    replace = bool(override_dir) and caps.get("wrapper_mode") == "replace"
    # The GCC-driver shims live in a `flto/` subdir put on PATH ONLY for a
    # flto-matched element - a bystander sandbox (a minimal make element
    # with no coreutils) that gets this mount for held-tool coverage must
    # not have `cc`/`gcc` shadowed by a shim it cannot even source
    # (bst-examples exit 255: `dirname: not found`). A `replace` drops
    # the shipped directory entirely, so its `flto/` subdir never applies.
    path_head = dst
    if caps.get("flto_active") and not replace:
        path_head = f"{os.path.join(dst, 'flto')}:{dst}"
    if replace:
        mount = ["--ro-bind", override_dir, dst]
    else:
        mount = ["--ro-bind", wrapper_dir, dst]
        if override_dir:
            operator_dst = f"{dst}-operator"
            mount += ["--ro-bind", override_dir, operator_dst]
            path_head = f"{operator_dst}:{path_head}"
    mount += [
        "--setenv", "PATH", f"{path_head}:{bst_path}",
        "--setenv", "BST_TRACE_JOBSERVER_LEDGER",
        os.path.join(bind_dst, "jobserver_ledger.jsonl"),
    ]
    if caps.get("wrapper_cap"):
        mount += ["--setenv", "BST_TRACE_WRAPPER_CAP", str(caps["wrapper_cap"])]
    if caps.get("lto_cap"):
        mount += ["--setenv", "BST_TRACE_LTO_CAP", str(caps["lto_cap"])]
    if caps.get("flto_active"):
        mount += ["--setenv", "BST_TRACE_FLTO_ACTIVE", "1"]
    return mount


def _active_jobserver_fifo(pool: dict) -> Optional[str]:
    """The host FIFO path fifo-style auth would bind, or `None` for fd
    style / nothing active - the proxy-over-global precedence
    `_jobserver_injection` applies, factored out for `main`'s own
    diagnostics record."""
    proxy_fd, proxy_fifo = pool.get("proxy_fd"), pool.get("proxy_fifo")
    if proxy_fd is not None or proxy_fifo is not None:
        return proxy_fifo
    if pool.get("fd") is not None:
        return None
    return pool.get("fifo")


def _sandbox_fifo_path(bind_src: str, bind_dst: str, host_path: Optional[str]) -> str:
    """UX-869: the jobserver/proxy FIFO already lives inside `bind_src`,
    which `build_shim_argv` binds whole at `bind_dst` - no `--bind` of
    its own is needed, just the path rewritten under that mount (a
    second, own-path bind failed on a read-only sandbox root whenever
    `bind_src` was not already under `/tmp`). `host_path` is `Optional`
    only because the caller's own dict is - both callers only reach here
    once fd style is already ruled out."""
    if host_path is None:
        raise ValueError("no FIFO host path to rewrite under bind_dst")
    return os.path.join(bind_dst, os.path.relpath(host_path, bind_src))


def _compiler_safe_fifo_host(pool: dict, element: Optional[str]) -> Optional[str]:
    """UX-878 (verifier fix): the host FIFO an unwrapped compiler's
    rewritten auth must name - a UX-849 per-element proxy's own FIFO,
    never the *global* jobserver a proxy exists specifically not to be,
    whichever style each happens to be in. Mirrors `_jobserver_injection`'s
    own "proxy wins outright" precedence (`:600`), which the original
    fix missed: `pool["proxy_fifo"]` is `None` under `fd` style
    (`_resolve_proxy_auth` opens the fd and discards the path), so a
    proxy active in the *default* `fd`/`auto` style is re-derived from
    `BST_TRACE_PROXY_DIR` + `element` - `_element_proxy_paths`'s own
    construction, at the point its own fd was opened from. `None` only
    when a proxy is active and neither is available (defensive; not
    reachable in practice, since a live `proxy_fd` was itself opened
    from that same path in this same process)."""
    proxy_active = pool.get("proxy_fd") is not None or pool.get("proxy_fifo") is not None
    if proxy_active:
        if pool.get("proxy_fifo") is not None:
            return pool["proxy_fifo"]
        proxy_dir = os.environ.get("BST_TRACE_PROXY_DIR")
        if proxy_dir and element is not None:
            return os.path.join(proxy_dir, f"{element}.fifo")
        return None
    return pool.get("fifo") or os.environ.get("BST_TRACE_JOBSERVER")


def _compiler_safe_makeflags(auth_value: str, policy: str, opts: list[str],
                             ctx: dict) -> Optional[str]:
    """UX-878: `auth_value` narrowed through `compiler_safe_auth` for the
    policies an unwrapped compiler/cargo actually reads
    (`_COMPILER_SAFE_POLICIES`); every other policy - `make` included -
    passes `auth_value` straight through, unchanged. Takes precedence
    over UX-874's downgrade above it: this reads the *resolved* pool
    (already fd if that downgrade fired) and re-derives `make_below_44`
    from the same cached probe, so a downgraded fd is scrubbed here
    rather than re-armed. `ctx` (`{bind_src, bind_dst, pool, real_bwrap,
    element}`, PLR0913's cap) bundles `_jobserver_injection`'s own
    `binds`/`pool` plus `kind_context`'s `real_bwrap`/`element`.
    `sandbox_fifo_path`'s own host FIFO is `_compiler_safe_fifo_host`'s
    (a proxy's own FIFO over the global one, `BST_TRACE_JOBSERVER` the
    last resort for an fd opened from it, `open_jobserver_fd`) - `None`
    when nothing names one (a bare fd with no FIFO behind it, e.g. a
    unit test's own pipe) or `real_bwrap` is unknown, in which case no
    `fifo:` rewrite is possible and `auth_value` stands, same as today.

    UX-913: a `_FD_DIRECT_POLICIES` policy keeps its auth where the
    scrub would have dropped it - `make` is a direct child and the raw
    fd is valid for it.
    """
    if policy not in _COMPILER_SAFE_POLICIES or "fifo:" in auth_value:
        return auth_value
    pool = ctx["pool"]
    real_bwrap = ctx.get("real_bwrap")
    host_fifo = _compiler_safe_fifo_host(pool, ctx.get("element"))
    if host_fifo is None or real_bwrap is None:
        return auth_value
    sandbox_fifo_path = _sandbox_fifo_path(ctx["bind_src"], ctx["bind_dst"], host_fifo)
    cache_path = _make_probe_cache_path(
        os.environ.get("BST_TRACE_JOBSERVER"), ctx.get("element"))
    probe = probe_make(real_bwrap, opts, cache_path)
    make_below_44 = bool(probe.get("available")) and \
        style_for_make_version(probe.get("version")) == "fd"
    safe = compiler_safe_auth(auth_value, sandbox_fifo_path, make_below_44)
    if safe is None and policy in _FD_DIRECT_POLICIES:
        return auth_value
    return safe


def _jobserver_injection(opts: list[str], binds: tuple, decision: str,
                         pool: dict, kind_context: dict) -> list[str]:
    """`build_shim_argv`'s own jobserver branch, split out to keep its
    complexity under the baseline's cap. `binds` is `(bind_src,
    bind_dst)`, kept as one param for PLR0913's cap. `pool` is `{fd,
    fifo, proxy_fd, proxy_fifo}` - UX-679/UX-841's global pair, UX-849's
    proxy pair, which wins outright over the global one when either is
    set. A proxy follows the *same* auth style the global FIFO resolved
    to (`BST_TRACE_JOBSERVER_AUTH` - UX-841 already reads it from `make
    --version`; a proxy has no version of its own to probe), the
    coordinator's fix for GNU Make 4.3 rejecting `fifo:` outright
    (measured live: `internal error: invalid --jobserver-auth string`).
    `kind_context` is `_resolve_kind_and_probe`'s own shape one module
    over, plus `wrapper_cap`. `[]` for a pinned decision or with
    nothing active - argv byte for byte."""
    bind_src, bind_dst = binds
    fd, fifo = pool.get("fd"), pool.get("fifo")
    proxy_fd, proxy_fifo = pool.get("proxy_fd"), pool.get("proxy_fifo")
    proxy_active = proxy_fd is not None or proxy_fifo is not None
    if decision == JOBSERVER_PINNED or (fd is None and fifo is None and not proxy_active):
        return []
    # UX-679 (spike) / UX-841: fd style passes an inherited fd straight
    # into the sandbox with no bind. Fifo style (GNU Make >= 4.4) names
    # the FIFO's in-sandbox path - already reachable under `bind_dst`
    # (UX-869: no bind of its own, which failed read-only outside
    # `/tmp`). UX-849: a proxy mirrors this exact pair, `main` having
    # already opened its own fd (fd style) or left only the path set
    # (fifo style).
    if proxy_active:
        auth_value = (f"--jobserver-auth={proxy_fd},{proxy_fd}"
                     if proxy_fd is not None
                     else f"--jobserver-auth=fifo:{_sandbox_fifo_path(bind_src, bind_dst, proxy_fifo)}")
    else:
        auth_value = (f"--jobserver-auth={fd},{fd}" if fd is not None
                     else f"--jobserver-auth=fifo:{_sandbox_fifo_path(bind_src, bind_dst, fifo)}")
    # UX-843/UX-859: the per-kind table - a kind not in it gets nothing
    # (`unknown_kind`) unless its own sandbox env carries `JOBS`
    # (`jobs_env`); cmake/meson and a `jobs_env` kind both consult the
    # ninja probe.
    pairs, unsets, policy = kind_job_env(
        kind_context.get("element_kind"), auth_value,
        kind_context.get("ninja_probe"), kind_context.get("wrappers_dir"),
        jobs_present=_setenv_value(opts, "JOBS") is not None)
    ctx = {"bind_src": bind_src, "bind_dst": bind_dst, "pool": pool,
          "real_bwrap": kind_context.get("real_bwrap"),
          "element": kind_context.get("element")}
    # UX-879: a per-element override takes precedence over the
    # auto/compiler_safe/downgrade path below - matched, it forces the
    # style outright and `_compiler_safe_makeflags` never runs. UX-882:
    # the command-line map wins outright; only when it does not match
    # does a committed `public: bga: jobserver-auth:` annotation apply.
    override = resolve_auth_override(
        os.environ.get("BST_TRACE_JOBSERVER_AUTH_MAP"), ctx["element"]
    ) or _annotation_style(ctx["element"])
    if override is not None:
        safe_auth = _forced_auth(override, auth_value, ctx)
    else:
        # UX-878: for the policies an unwrapped compiler/cargo reads
        # MAKEFLAGS directly (gcc-lto, cargo), narrow the auth to a form
        # that survives the sandbox boundary - `None` scrubs it outright
        # rather than hand a raw fd to a deep grandchild that cannot use
        # it.
        safe_auth = _compiler_safe_makeflags(
            auth_value, policy, opts, ctx=ctx)
    if safe_auth != auth_value:
        pairs = [pair for pair in pairs if pair[0] != "MAKEFLAGS"]
        if safe_auth is not None:
            pairs.append(("MAKEFLAGS", safe_auth))
        else:
            # UX-878: a scrub leaves no jobserver, so an emptied JOBS would serialize the build; drop it too and the recipe's own -jN stands (jobserver-off behaviour).
            pairs = [pair for pair in pairs if pair[0] != "JOBS"]
    auth_injected = any(var == "MAKEFLAGS" for var, _ in pairs)
    tokens = []
    for var, value in pairs:
        tokens += ["--setenv", var, value]
    for var in unsets:
        tokens += ["--unsetenv", var]
    # UX-846: a tool that will not read the pipe (lld below LLVM 22,
    # gold, mold, ninja) holds tokens instead - bind a read-only `PATH`
    # of wrappers ahead of BuildStream's own, only when an auth was
    # actually injected above (an empty MAKEFLAGS is nothing to hold
    # from). `bst_native_build_tracer.probe_jobserver_wrapper_policy`
    # decides which tools this directory covers before the build.
    wrapper_dir = kind_context.get("wrappers_dir")
    if wrapper_dir is not None and auth_injected:
        tokens += _wrapper_mount(opts, wrapper_dir, bind_dst, caps={
            "wrapper_cap": kind_context.get("wrapper_cap"),
            "lto_cap": kind_context.get("lto_cap"),
            "flto_active": override == "flto",
            # UX-881: an operator's own wrapper directory and its mode,
            # carried straight through from `main` (never re-derived here).
            "wrapper_dir_override": kind_context.get("wrapper_dir_override"),
            "wrapper_mode": kind_context.get("wrapper_mode"),
        })
    return tokens


def build_shim_argv(
    real_bwrap: str,
    bst_args: list[str],
    bind_src: str,
    bind_dst: str,
    preload_so: str,
    trace_log: str,
    invocation_id: Optional[int] = None,
    spine: Optional[str] = None,
    jobserver_fd: Optional[int] = None,
    jobserver_fifo: Optional[str] = None,
    project_max_jobs: Optional[int] = None,
    element_kind: Optional[str] = None,
    ninja_probe: Optional[dict] = None,
    wrapper_dir: Optional[str] = None,
    wrapper_cap: Optional[str] = None,
    proxy_fd: Optional[int] = None,
    proxy_fifo: Optional[str] = None,
    lto_cap: Optional[str] = None,
    wrapper_dir_override: Optional[str] = None,
    wrapper_mode: Optional[str] = None,
) -> list[str]:
    """The real, complete argv to exec: BuildStream's own bwrap options
    first (unmodified, including its own root-filesystem bind), then the
    injected `--bind`/`--setenv LD_PRELOAD`/`--setenv BST_TRACE_LOG`
    *after* them (so the real root bind can't wipe the injected mount -
    bug 1 above), then BuildStream's own trailing sandboxed command,
    untouched.

    `BST_TRACE_LOG` must be injected explicitly here, not merely set in
    this shim's *own* process environment: BuildStream's own generated
    bwrap argv already contains an exhaustive `--unsetenv` for every var
    bwrap itself was launched with, followed by `--setenv` for only its
    own small curated list (PATH/HOME/TERM/USER/...) - bwrap fully
    reconstructs the sandboxed process's environment from its argv, so a
    var only set in the shim's own environment never reaches the
    sandbox. This was a real bug caught by this design's own first real
    end-to-end run: the hook loaded, found no `BST_TRACE_LOG`, and
    stayed silently inert exactly as designed for the "no tracing
    requested" case - which is indistinguishable from "tracing was
    requested but the env var didn't arrive" without this fix.

    `proxy_fd`/`proxy_fifo` (UX-849): when the `Broker` pre-created this
    element's own proxy, exactly one wins over `jobserver_fd`/
    `jobserver_fifo` outright - `main` already opened the proxy under
    the *same* style the global FIFO resolved to (mirroring UX-841
    exactly; a proxy has no `make --version` of its own to probe).

    `lto_cap` (UX-880): `BST_TRACE_LTO_CAP`, read straight from this
    process's own environment by the caller - the static `-flto=N` cap
    the wrapper-mounted GCC-driver shim rewrites to, same channel as
    `wrapper_cap`.

    `wrapper_dir_override`/`wrapper_mode` (UX-881): `bga capture run
    --wrapper-dir`/`--wrapper-dir-mode`, read the same way - an
    operator's own wrapper directory, mounted alongside (`augment`,
    default) or instead of (`replace`) the shipped one.
    """
    opts, cmd = split_bwrap_args(bst_args)
    injected = [
        "--bind", bind_src, bind_dst,
        "--setenv", "LD_PRELOAD", preload_so,
        "--setenv", "BST_TRACE_LOG", trace_log,
    ]
    element = extract_element_name(opts)
    if element is not None:
        injected += ["--setenv", "BST_TRACE_ELEMENT", element]
    # UX-56: the element tag above is derived from `--dir`, which is the
    # build root - correct under BuildStream's default per-element layout
    # and useless under a project-wide override like freedesktop-sdk's
    # `build-root: /buildstream-build`, where every element collapses to
    # one bucket. This id does not depend on the layout: it is unique per
    # sandbox, so traced processes group exactly per element *build* even
    # when their name is wrong, and a later correlation can relabel the
    # whole group at once. Injected unconditionally, since it costs one
    # setenv and is what makes the group recoverable at all.
    if invocation_id is not None:
        injected += ["--setenv", "BST_TRACE_INVOCATION", str(invocation_id)]
    # UX-46: opened-path recording is opt-in and must be propagated into
    # the sandbox the same way BST_TRACE_LOG is - the hook reads its own
    # environment inside bwrap, where the outer process's env does not
    # reach (the same failure UX-11's own dead-end hit with a hardcoded
    # log path).
    if os.environ.get("BST_TRACE_OPENS"):
        injected += ["--setenv", "BST_TRACE_OPENS", "1"]
    # UX-842: a `notparallel` element's own `-j1` (Direction 20 argument
    # 1) means this sandbox never joins - no MAKEFLAGS auth, no fifo:
    # bind, argv byte for byte as without the mode - a pin can be the
    # workaround for a defect in the native build system, and the mode
    # must not override it.
    decision = jobserver_decision(parse_element_max_jobs(opts), project_max_jobs)
    injected += _jobserver_injection(
        opts, (bind_src, bind_dst), decision,
        pool={"fd": jobserver_fd, "fifo": jobserver_fifo,
             "proxy_fd": proxy_fd, "proxy_fifo": proxy_fifo},
        kind_context={"element_kind": element_kind, "ninja_probe": ninja_probe,
                     "wrappers_dir": wrapper_dir, "wrapper_cap": wrapper_cap,
                     "real_bwrap": real_bwrap, "element": element,
                     "lto_cap": lto_cap,
                     "wrapper_dir_override": wrapper_dir_override,
                     "wrapper_mode": wrapper_mode})
    # UX-106: the ptrace spine, prepended to the sandboxed command so it
    # becomes the parent of everything BuildStream asked to run - which
    # is what makes every descendant its own tracee, and so traceable
    # without any capability under Yama `ptrace_scope=1`.
    #
    # Prepended to `cmd`, not to the bwrap options: it must run *inside*
    # the sandbox, after bwrap has set the namespaces up. Under
    # `--unshare-pid` it therefore becomes pid 1, which is why it carries
    # init duties.
    if spine:
        return [real_bwrap, *opts, *injected, spine, "--", *cmd]
    return [real_bwrap, *opts, *injected, *cmd]


# UX-58: how many invocations are recorded when argv capture is on. A
# real build spawns one bwrap per element task and thousands of them on a
# large project; a handful is enough to identify which option carries the
# element, which is the only question this exists to answer.
DEFAULT_ARGV_RECORD_LIMIT = 32


def record_argv(log_path: str, argv: list[str], limit: int) -> bool:
    """UX-58: append one bwrap argv, as BuildStream generated it, to
    `log_path`. Returns whether a record was written.

    This shim has received BuildStream's complete bwrap command line on
    every capture this project has ever taken, rewritten it, and exec'd
    it without recording it anywhere - so the argv needed to settle
    `UX-56`'s element-identity question has never existed in any
    artifact, and `UX-56` mis-attributed that absence to the capture
    workflow's tarball size limit.

    Bounded by re-reading the file rather than by an in-process counter,
    because each bwrap invocation is a *fresh* shim process with no
    memory of the last. Two concurrent invocations can therefore both
    see room and both write, overshooting `limit` slightly; that is
    accepted deliberately - the alternative is locking on a hot path to
    protect a diagnostic whose only requirement is "a few".

    Never raises. A diagnostic that can fail a real build is worse than
    no diagnostic, so every error path here ends in "record nothing and
    let the build proceed".
    """
    try:
        recorded = 0
        try:
            with open(log_path, encoding="utf-8") as handle:
                recorded = sum(1 for _ in handle)
        except FileNotFoundError:
            pass
        # Checked against a missing file too: a limit of 0 must record
        # nothing rather than record one and then stop.
        if recorded >= limit:
            return False
        # UX-56: the argv turned out to carry the element only via the
        # build root (see UX-58), so the record also captures what the
        # *invoking* process looks like - BuildStream runs each build job
        # in its own forked child, and that child is this shim's parent.
        record = {"pid": os.getpid(), "ppid": os.getppid(), "argv": argv}
        chain, pid = [], os.getppid()
        for _ in range(8):
            try:
                with open(f"/proc/{pid}/cmdline", "rb") as handle:
                    cmd = handle.read().decode("utf-8", "replace").replace("\x00", " ").strip()
                with open(f"/proc/{pid}/stat") as handle:
                    ppid = int(handle.read().rsplit(")", 1)[1].split()[1])
            except (OSError, ValueError, IndexError):
                break
            chain.append({"pid": pid, "cmdline": cmd[:400]})
            if ppid <= 1:
                break
            pid = ppid
        record["parent_chain"] = chain
        line = json.dumps(record, sort_keys=True) + "\n"
        # One write() of one line, appended - the same atomicity argument
        # the trace hook's own single-write rule rests on.
        fd = os.open(log_path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
        try:
            os.write(fd, line.encode("utf-8"))
        finally:
            os.close(fd)
        return True
    except Exception:
        return False


def spine_for_element(policy: Optional[str], census_path: Optional[str],
                      element: Optional[str], spine: Optional[str]) -> Optional[str]:
    """UX-113: whether *this* element's sandbox gets the ptrace spine.

    The spine and the census were built in the same round and never
    introduced. The census knows, before the build starts and per
    element, whether the staged root holds a static executable - i.e.
    whether the hook will be blind there. The spine was all-or-nothing,
    priced for every element, to cover the few where it is the only
    witness; so it stayed opt-in, and therefore mostly off, which
    quietly re-opened the blind spot the whole of Direction 4 closed.

    Three policies. `off` and `on` are what they were. `auto` traces an
    element only where the census says the hook cannot see, and - always
    and deliberately - where the census could not tell:

    - an element the census has no verdict for is traced, because "we
      did not assess it" and "we assessed it and it is clean" are
      different claims and only one of them is safe to skip;
    - an element whose name the shim could not recover is traced, which
      under a build-root override (`UX-56`) is *every* element, so a
      project that collapses its names gets `on` rather than a silently
      empty policy.
    """
    if not spine or policy != "auto":
        return spine
    if element is None:
        return spine                       # name unrecoverable - trace it
    try:
        with open(census_path, encoding="utf-8") as handle:
            verdicts = json.load(handle)
    except (OSError, ValueError, TypeError):
        return spine                       # no census to consult - trace it
    if element not in verdicts:
        return spine                       # unassessed - trace it
    return spine if verdicts[element] else None


def record_invocation(log_path: Optional[str], invocation_id: int,
                      dir_tag: Optional[str], spine_traced: bool = False) -> bool:
    """UX-56: one line per sandbox - `{id, started_at, dir_tag}`.

    `started_at` is `CLOCK_REALTIME` on the host, deliberately not the
    hook's `CLOCK_MONOTONIC`: this record exists to be matched against
    Plane 1's BUILD spans, which are wall-clock, and anchoring here
    avoids needing a monotonic-to-realtime offset at all.

    `dir_tag` is kept even though it is the value that collapses - a
    capture where it happens to be correct is then self-checking, since
    the correlation's answer can be compared against it.

    Unbounded, unlike `record_argv`: there is one bwrap invocation per
    element build, so a 126-element project writes 126 lines. Never
    raises, for the same reason `record_argv` never does.
    """
    if not log_path:
        return False
    try:
        line = json.dumps({
            "invocation_id": invocation_id,
            "started_at": time.time(),
            "dir_tag": dir_tag,
            # UX-113: what the spine policy decided for this sandbox.
            # Recorded rather than inferred from whether spine records
            # appeared: an element that ran no processes and one the
            # policy skipped look identical in the trace, and only one of
            # them is a coverage gap.
            "spine_traced": spine_traced,
        }, sort_keys=True) + "\n"
        fd = os.open(log_path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
        try:
            os.write(fd, line.encode("utf-8"))
        finally:
            os.close(fd)
        return True
    except Exception:
        return False


def record_jobserver_decision(log_path: Optional[str], opts: list[str],
                              element: Optional[str],
                              project_max_jobs: Optional[int],
                              kind_context: Optional[dict] = None) -> bool:
    """UX-842/UX-843: one JSON line per sandbox - `{element, max_jobs,
    decision, kind, policy}` - beside the FIFO in the capture scratch.
    When the shim could not name the element (`extract_element_name`
    found no `--dir`), falls back to the sandbox's own `--chdir`, then
    to the `-j` value itself, and says so with `element_unresolved`.
    `policy` is `None` for a `pinned` decision (the table is never
    consulted). `kind_context` is `_resolve_kind_and_probe`'s
    `{element_kind, ninja_probe, wrappers_dir}` - bundled into one
    optional param to keep this under ruff's argument-count cap. Never
    raises, same contract as `record_diagnostics`."""
    if not log_path:
        return False
    kind_context = kind_context or {}
    element_kind = kind_context.get("element_kind")
    try:
        element_max_jobs = parse_element_max_jobs(opts)
        decision = jobserver_decision(element_max_jobs, project_max_jobs)
        policy = None
        if decision != JOBSERVER_PINNED:
            _pairs, _unsets, policy = kind_job_env(
                element_kind, "--jobserver-auth=0,0",
                kind_context.get("ninja_probe"), kind_context.get("wrappers_dir"),
                jobs_present=_setenv_value(opts, "JOBS") is not None)
        name, unresolved = element, False
        if name is None:
            unresolved = True
            for i, opt in enumerate(opts):
                if opt == "--chdir" and i + 1 < len(opts):
                    name = opts[i + 1]
                    break
            if name is None and element_max_jobs is not None:
                name = f"-j{element_max_jobs}"
        record = {"element": name, "max_jobs": element_max_jobs,
                 "decision": decision, "kind": element_kind, "policy": policy}
        if unresolved:
            record["element_unresolved"] = True
        line = json.dumps(record, sort_keys=True) + "\n"
        fd = os.open(log_path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
        try:
            os.write(fd, line.encode("utf-8"))
        finally:
            os.close(fd)
        return True
    except Exception:
        return False


def record_diagnostics(log_path: Optional[str], received: list[str],
                       exec_argv: list[str], real_bwrap: str,
                       element: Optional[str], spine: Optional[str],
                       injected: bool,
                       stderr_path: Optional[str] = None,
                       jobserver_fifo_host: Optional[str] = None,
                       jobserver_fifo_sandbox: Optional[str] = None) -> bool:
    """UX-146: one line per invocation, holding both argvs.

    A capture that fails tells the user `buildbox-run failed with
    returncode 1` and nothing else, and three unrelated causes produce
    it: the `$PATH` shadow never reaching `buildbox-run` at all, the
    argv rewrite mis-splitting options from the command, or the
    environment. Only the first is visible from outside, and only as an
    absence.

    So: what BuildStream generated, what this shim is about to exec, and
    where the split fell - which is the fragile part, since
    `split_bwrap_args`' arity table was validated against bubblewrap
    0.9.0 and a newer flag it does not know is assumed to take no
    arguments.

    Written *before* the exec, because this process is replaced by the
    real `bwrap` and never runs again. Never raises, for the same reason
    `record_argv` never does: a diagnostic that can fail a real build is
    worse than no diagnostic.
    """
    if not log_path:
        return False
    try:
        opts, cmd = split_bwrap_args(received)
        unknown = unknown_flags(received)
        record = {
            "pid": os.getpid(),
            "ppid": os.getppid(),
            "at": time.time(),
            "real_bwrap": real_bwrap,
            "real_bwrap_executable": os.access(real_bwrap, os.X_OK),
            "element": element,
            "spine": spine,
            "injected": injected,
            "received_argv": list(received),
            "exec_argv": list(exec_argv),
            # Where the parse thinks BuildStream's options end and the
            # sandboxed command begins. A mis-split shows up here as a
            # `command` starting with something that is plainly a flag.
            "option_count": len(opts),
            "command": cmd,
            # UX-151: which option-looking tokens the arity table has no
            # entry for. Non-empty means the split below this line is a
            # guess, and names the flag to add.
            "unknown_flags": unknown,
            # UX-148: where this invocation's stderr was tee'd, when the
            # capture ran under `--diagnose`. `None` on the default path,
            # which still execs and therefore has nowhere to put it.
            "stderr_path": stderr_path,
            # UX-869: fifo style names no host path in `exec_argv` any
            # more (no bind of its own) - both `None` for fd style or
            # nothing active.
            "jobserver_fifo_host": jobserver_fifo_host,
            "jobserver_fifo_sandbox": jobserver_fifo_sandbox,
        }
        line = json.dumps(record, sort_keys=True) + "\n"
        fd = os.open(log_path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
        try:
            os.write(fd, line.encode("utf-8"))
        finally:
            os.close(fd)
        return True
    except Exception:
        return False


def stderr_record_path(diagnostics_path: str, invocation_id: int) -> str:
    """Where one invocation's stderr goes, beside the JSONL record."""
    directory = diagnostics_path + ".stderr"
    os.makedirs(directory, exist_ok=True)
    return os.path.join(directory, f"{invocation_id}.stderr")


def _readable(fd: int, timeout: float = 0.0) -> bool:
    """Is there anything to read on `fd` within `timeout`? (`UX-168`)"""
    try:
        return bool(select.select([fd], [], [], timeout)[0])
    except (OSError, ValueError):
        return False


def _reap(pid: int) -> Optional[int]:
    """The child's wait status if it has exited, else `None`.

    Reaps at most once and hands the status back, because the caller
    needs it: `exit_like` reproduces it, and a status thrown away here
    would break `UX-140`'s contract from a different direction.
    """
    try:
        done, status = os.waitpid(pid, os.WNOHANG)
    except (ChildProcessError, OSError):
        return None
    return status if done == pid else None


def run_teed(real_bwrap: str, argv: list[str], stderr_path: str) -> int:
    """Run the real bwrap as a child, copying its stderr to a file.

    `UX-148`, and the reason this is `--diagnose`-only. The default path
    must keep `exec`-ing: `UX-140` established that the shim *becoming*
    the real bwrap is what makes signals, exit status and process
    identity reach `buildbox-run` unchanged, and a wrapper that changes
    any of those reports on a build that is not the one the user runs.

    Under diagnose the extra process is affordable, but the contract is
    not: this returns the raw `wait` status so the caller can re-raise a
    fatal signal against itself, which is the only way a forked shim can
    still exit `WIFSIGNALED`.

    A real tee, not a redirect - the child's stderr still has to reach
    `buildbox-run`, or a capture run with `--diagnose` would hide the
    very message the user is chasing.
    """
    read_fd, write_fd = os.pipe()
    pid = os.fork()
    if pid == 0:  # pragma: no cover - the child never returns
        try:
            os.close(read_fd)
            os.dup2(write_fd, 2)
            if write_fd > 2:
                os.close(write_fd)
            os.execv(real_bwrap, argv)
        except BaseException as error:
            try:
                os.write(2, f"bga: could not exec {real_bwrap}: {error}\n".encode())
            finally:
                os._exit(127)
    os.close(write_fd)
    status = None
    try:
        with open(stderr_path, "wb") as sink:
            while True:
                if _readable(read_fd, timeout=1.0):
                    chunk = os.read(read_fd, 65536)
                    if not chunk:
                        break
                    sink.write(chunk)
                    # Straight to fd 2: this process's `sys.stderr` may
                    # be buffered, and the ordering buildbox-run sees
                    # should be the child's.
                    os.write(2, chunk)
                    continue
                # UX-168 item 1: the read only ends when *every* holder
                # of the write end closes it, and every descendant of
                # the sandbox holds one - so a process that daemonizes
                # past bwrap's own exit would hang the shim here.
                # Unlikely under `--die-with-parent`, but "unlikely" is
                # not a reason to let a debugging mode wedge a build.
                # Once the child is reaped and the pipe has gone quiet,
                # whatever still holds it is an orphan, not the sandbox.
                if status is None:
                    status = _reap(pid)
                elif not _readable(read_fd):
                    break
    except OSError:
        pass
    finally:
        os.close(read_fd)
    if status is None:
        # The pipe closed first, which is the ordinary case.
        _, status = os.waitpid(pid, 0)
    return status


def exit_like(status: int) -> int:
    """Reproduce a child's wait status as this process's own exit.

    `UX-148`, preserving `UX-140`'s contract through the forked path: a
    sandbox killed by a signal has to reach `bst` as `WIFSIGNALED`, and
    the only way to do that from a parent is to re-raise the same signal
    against itself with the default disposition restored.
    """
    if os.WIFSIGNALED(status):
        signum = os.WTERMSIG(status)
        with contextlib.suppress(ValueError, OSError):
            signal.signal(signum, signal.SIG_DFL)
        os.kill(os.getpid(), signum)
        # Only reached if the signal was blocked or could not be raised.
        return 128 + signum
    return os.WEXITSTATUS(status)


def run_and_mark_done(real_bwrap: str, argv: list[str], done_path: str) -> int:
    """UX-849: run the real bwrap as a forked child - like `run_teed`,
    this shim becomes a genuine parent rather than `execv`-replacing
    itself, only because the broker needs to know, from outside, the
    moment this sandbox is gone. Reproduces `exit_like`'s own exit
    contract; the marker write happens after `waitpid` returns, so a
    signal that kills the sandbox still gets its own `.done` first."""
    pid = os.fork()
    if pid == 0:  # pragma: no cover - the child never returns
        try:
            os.execv(real_bwrap, argv)
        except BaseException as error:
            try:
                os.write(2, f"bga: could not exec {real_bwrap}: {error}\n".encode())
            finally:
                os._exit(127)
    _, status = os.waitpid(pid, 0)
    with contextlib.suppress(OSError):
        open(done_path, "w").close()
    return exit_like(status)


def _open_inheritable_rdwr(path: str) -> int:
    """The one way this module opens a jobserver FIFO for `fd` style -
    read-write so the open cannot block on a second end, inheritable so
    `execv` carries it into the real bwrap (`os.open` marks a new fd
    non-inheritable by default, PEP 446). Shared by `open_jobserver_fd`,
    `_resolve_proxy_auth`, and UX-874's downgrade below."""
    fd = os.open(path, os.O_RDWR)
    os.set_inheritable(fd, True)
    return fd


def open_jobserver_fd() -> tuple[Optional[int], Optional[str]]:
    """The `(fd, fifo_path)` `main` hands `build_shim_argv` - exactly one
    of the pair set, or both `None`.

    UX-679 (spike) / UX-841: only acted on when `run_traced_build` handed
    a FIFO path down. `fd` style (`BST_TRACE_JOBSERVER_AUTH` unset or
    `fd`) opens it read-write here so the open cannot block on a second
    end, and inheritable so `execv` carries the fd into the real `bwrap`
    (Python's `os.open` marks it non-inheritable by default, PEP 446).
    `fifo:` style (GNU Make >= 4.4) opens nothing here - `make` opens the
    bound path itself inside the sandbox - so only the path is returned.
    """
    jobserver_path = os.environ.get("BST_TRACE_JOBSERVER")
    if not jobserver_path:
        return None, None
    if os.environ.get("BST_TRACE_JOBSERVER_AUTH") == "fifo":
        return None, jobserver_path
    return _open_inheritable_rdwr(jobserver_path), None


def _project_max_jobs_env() -> Optional[int]:
    """UX-842: `BST_TRACE_PROJECT_MAX_JOBS`, parsed defensively - unset
    or unparseable both mean "unknown", and every `-jK` then joins."""
    raw = os.environ.get("BST_TRACE_PROJECT_MAX_JOBS")
    try:
        return int(raw) if raw else None
    except ValueError:
        return None


def _element_proxy_paths(element: Optional[str],
                         pinned: bool) -> tuple[Optional[str], Optional[str]]:
    """UX-849: `(proxy_fifo, done_path)` when `BST_TRACE_PROXY_DIR` names
    a proxy the tracer pre-created for this element, else `(None,
    None)` - the shim binds the global FIFO as today. `pinned` (Direction
    20 argument 1): a `notparallel` element never joins anything, proxy
    included, so its sandbox is `execv`'d exactly as before - the fork
    below exists only for a sandbox that actually binds one."""
    if pinned:
        return None, None
    proxy_dir = os.environ.get("BST_TRACE_PROXY_DIR")
    if not proxy_dir or element is None:
        return None, None
    fifo_path = os.path.join(proxy_dir, f"{element}.fifo")
    if not os.path.exists(fifo_path):
        return None, None
    return fifo_path, os.path.join(proxy_dir, f"{element}.done")


def _resolve_proxy_auth(proxy_fifo: Optional[str]) -> tuple[Optional[int], Optional[str]]:
    """`(proxy_fd, proxy_fifo)` for `build_shim_argv` - exactly one set,
    or both `None` when there is no proxy. Mirrors `open_jobserver_fd`'s
    own style read exactly: `BST_TRACE_JOBSERVER_AUTH == "fifo"` binds
    the path unchanged (GNU Make >= 4.4); anything else (including
    unset) opens the proxy itself here, inheritable, the fd style a
    proxy has no `make --version` of its own to have chosen. The
    coordinator's fix: a proxy has to follow the *same* style the
    global FIFO already resolved to, not always `fifo:` - GNU Make 4.3
    (this box, CI) rejects that string outright."""
    if proxy_fifo is None:
        return None, None
    if os.environ.get("BST_TRACE_JOBSERVER_AUTH") == "fifo":
        return None, proxy_fifo
    return _open_inheritable_rdwr(proxy_fifo), None


def _downgrade_fifo_to_fd_if_sandbox_make_rejects_it(
        probe: dict, cache_path: Optional[str], pool: dict) -> dict:
    """UX-874/UX-877: `pool` (`{fd, fifo, proxy_fd, proxy_fifo}`)
    unchanged unless the request is `fifo` (a `fifo` entry present) and
    this element's own sandbox make - probed once, cached at
    `cache_path` (`_make_probe_cache_path`, per element) - is below
    4.4/absent/unparseable, in which case both the global FIFO and
    UX-849's per-element proxy (the same sandbox make consumes either)
    are opened `fd` style instead. Never widens: a request already `fd`
    has no `fifo` entry to act on. `probe` (`{element_kind, real_bwrap,
    opts, ninja_probe, wrappers_dir, jobs_present}`, PLR0913's cap)
    threads its last three straight to `sandbox_make_auth_style` so its
    kind gate matches `kind_job_env`'s own injection.
    """
    if pool.get("fifo") is None and pool.get("proxy_fifo") is None:
        return pool
    if sandbox_make_auth_style(
            probe["element_kind"], probe["real_bwrap"], probe["opts"], cache_path,
            kind_probe=probe) != "fd":
        return pool
    downgraded = dict(pool)
    if pool.get("fifo") is not None:
        downgraded["fd"] = _open_inheritable_rdwr(pool["fifo"])
        downgraded["fifo"] = None
    if pool.get("proxy_fifo") is not None:
        downgraded["proxy_fd"] = _open_inheritable_rdwr(pool["proxy_fifo"])
        downgraded["proxy_fifo"] = None
    return downgraded


def _narrow_jobserver_to_sandbox_make(probe: dict, pinned: bool, pool: dict) -> dict:
    """`main`'s own UX-874/UX-877 wiring, split out to keep its
    statement count under `PLR0915`'s cap and its argument count under
    `PLR0913`'s - `probe` (`{element, element_kind, real_bwrap, opts,
    ninja_probe, wrappers_dir, jobs_present}`) and `pool` (`{fd, fifo,
    proxy_fd, proxy_fifo}`) kept as one param each, the same grouping
    `_jobserver_injection`'s own `binds`/`pool` already use.
    `_make_probe_cache_path` (per element) then
    `_downgrade_fifo_to_fd_if_sandbox_make_rejects_it`. `pool` unchanged
    for a pinned element - nothing is injected for it either way."""
    if pinned:
        return pool
    cache_path = _make_probe_cache_path(
        os.environ.get("BST_TRACE_JOBSERVER"), probe["element"])
    return _downgrade_fifo_to_fd_if_sandbox_make_rejects_it(probe, cache_path, pool)


def _element_kind_env(element: Optional[str]) -> Optional[str]:
    """UX-843: `BST_TRACE_ELEMENT_KINDS`'s map (a JSON `{name: kind}`,
    written once by the tracer from `bst show`), looked up for this
    sandbox's element. `None` on an unset/unreadable file or an element
    the map does not name - both degrade to `unknown_kind`."""
    path = os.environ.get("BST_TRACE_ELEMENT_KINDS")
    if not path or element is None:
        return None
    try:
        with open(path, encoding="utf-8") as handle:
            kinds = json.load(handle)
    except (OSError, ValueError):
        return None
    return kinds.get(element) if isinstance(kinds, dict) else None


def _annotation_style(element: Optional[str]) -> Optional[str]:
    """UX-882: `BST_TRACE_ELEMENT_AUTH_MAP`'s map (a JSON `{name: style}`,
    written once by the tracer from each element's own `public: bga:
    jobserver-auth:` annotation), looked up the same way
    `_element_kind_env` reads `BST_TRACE_ELEMENT_KINDS`. `None` on an
    unset/unreadable file, an element the map does not name, or a
    stored value outside the four override styles - all three degrade
    to "no annotation", the same as `resolve_auth_override`'s own miss."""
    path = os.environ.get("BST_TRACE_ELEMENT_AUTH_MAP")
    if not path or element is None:
        return None
    try:
        with open(path, encoding="utf-8") as handle:
            auth_map = json.load(handle)
    except (OSError, ValueError):
        return None
    if not isinstance(auth_map, dict):
        return None
    style = auth_map.get(element)
    return style if style in _AUTH_OVERRIDE_STYLES else None


def _resolve_kind_and_probe(element, jobserver_fd, jobserver_fifo,
                            project_max_jobs, real_bwrap):
    """UX-843/UX-859: `{element_kind, ninja_probe, wrappers_dir}` for
    `main` - pulled out of it (a dict, not a tuple, so both call sites
    in `main` pass it straight through as one argument) so the mode's
    env-reading and gating (`_element_kind_env`, the ninja probe's own
    gate) don't inflate `main`'s own statement count. The probe runs
    for a cmake/meson element, or any other kind whose own sandbox env
    carries `JOBS` (UX-859: a manual `-G Ninja` recipe is exactly as
    much at risk of the cores+2 regression UX-843 found), whose
    decision would otherwise consult it (mode active, not pinned).
    Cached per capture (UX-855), so this is one `ninja --help` per
    capture even with the gate widened.

    UX-881: `wrapper_dir_override`/`wrapper_mode`
    (`BST_TRACE_WRAPPER_DIR_OVERRIDE`/`BST_TRACE_WRAPPER_MODE`) ride
    along the same way - an operator's own wrapper directory, read
    here so `main`'s single call site stays the only place environment
    is consulted."""
    element_kind = _element_kind_env(element)
    wrappers_dir = os.environ.get("BST_TRACE_WRAPPER_DIR")
    base = {"element_kind": element_kind, "ninja_probe": None,
           "wrappers_dir": wrappers_dir,
           "wrapper_dir_override": os.environ.get("BST_TRACE_WRAPPER_DIR_OVERRIDE"),
           "wrapper_mode": os.environ.get("BST_TRACE_WRAPPER_MODE")}
    active = jobserver_fd is not None or jobserver_fifo is not None
    if not active:
        return base
    opts, _cmd = split_bwrap_args(sys.argv[1:])
    jobs_present = _setenv_value(opts, "JOBS") is not None
    if element_kind not in _NINJA_CAPABLE_KINDS and not jobs_present:
        return base
    decision = jobserver_decision(parse_element_max_jobs(opts), project_max_jobs)
    if decision == JOBSERVER_PINNED:
        return base
    jobserver_path = os.environ.get("BST_TRACE_JOBSERVER")
    cache_path = (os.path.join(os.path.dirname(jobserver_path), "ninja_probe.json")
                 if jobserver_path else None)
    base["ninja_probe"] = probe_ninja(real_bwrap, opts, cache_path)
    return base


SELF_TEST_ARGV = "--bga-shim-self-test"


def main() -> int:
    # UX-147 item 1: the tracer execs the installed shim once, itself,
    # before `bst` runs. The shim is a script materialized under a temp
    # directory, so a noexec mount, an AppArmor denial on executing from
    # /tmp, or a missing interpreter all fail this exec *inside
    # buildbox-run* - which reports `returncode 1` with the stderr
    # swallowed, twenty minutes into a build, while the diagnostics
    # record stays empty and the summary calls the build unmodified.
    if len(sys.argv) > 1 and sys.argv[1] == SELF_TEST_ARGV:
        sys.stdout.write("bga-shim-ok\n")
        return 0

    real_bwrap = os.environ.get("BST_TRACE_REAL_BWRAP", "/usr/bin/bwrap")
    # UX-147 item 4: these were four bare `os.environ[...]` lookups, four
    # lines below the traceback UX-146 fixed. A shim reached without them
    # - the environment sanitized somewhere in the chain, or any other
    # process invoking `bwrap` while the shim directory is on PATH -
    # raised KeyError onto buildbox-run's swallowed stderr and produced
    # the same unexplained `returncode 1`.
    required = ("BST_TRACE_BIND_SRC", "BST_TRACE_BIND_DST",
                "BST_TRACE_PRELOAD_SO", "BST_TRACE_LOG_DST")
    missing = [name for name in required if name not in os.environ]
    if missing:
        sys.stderr.write(
            f"bga: this is bga's bwrap shim, invoked without {missing[0]} - so it "
            f"is not being run by a bga capture. Falling through to the real "
            f"bwrap at {real_bwrap}.\n")
        try:
            os.execv(real_bwrap, [real_bwrap, *sys.argv[1:]])
        except OSError as error:
            sys.stderr.write(f"bga: and could not exec it: {error}\n")
            return 127
        return 1
    bind_src, bind_dst, preload_so, trace_log = (os.environ[name] for name in required)
    # UX-58: opt-in, like --trace-opens, and recorded *before* the
    # rewrite so the file holds what BuildStream actually generated
    # rather than what this shim turned it into.
    argv_log = os.environ.get("BST_TRACE_ARGV_LOG")
    if argv_log:
        try:
            limit = int(os.environ.get("BST_TRACE_ARGV_MAX", DEFAULT_ARGV_RECORD_LIMIT))
        except ValueError:
            limit = DEFAULT_ARGV_RECORD_LIMIT
        record_argv(argv_log, list(sys.argv[1:]), limit)
    # UX-56: the shim's own pid is unique among concurrently-live host
    # processes, which is exactly the scope that matters - it only has to
    # distinguish sandboxes within one build. Recorded with a wall-clock
    # start so the correlation has something to match Plane 1's BUILD
    # spans against; the shim cannot record an *end*, since it execv's.
    invocation_id = os.getpid()
    element = extract_element_name(sys.argv[1:])
    # UX-113: the per-element policy decision, made here because this is
    # the only place that knows which element's sandbox is about to run.
    spine = spine_for_element(
        os.environ.get("BST_TRACE_SPINE_POLICY"),
        os.environ.get("BST_TRACE_SPINE_CENSUS"),
        element,
        os.environ.get("BST_TRACE_SPINE"),
    )
    record_invocation(
        os.environ.get("BST_TRACE_INVOCATION_LOG"), invocation_id, element,
        spine_traced=bool(spine),
    )
    # UX-146: the bisection a user cannot otherwise perform. With this
    # set the shim is still on `$PATH` and still exec'd by
    # `buildbox-run`, but BuildStream's argv reaches the real `bwrap`
    # untouched - so a build that succeeds here and fails without it
    # blames the rewrite, and one that fails both ways blames the
    # shadowing or the exec. It captures nothing, deliberately.
    inject = os.environ.get("BST_TRACE_NO_INJECT") != "1"
    jobserver_fd, jobserver_fifo = open_jobserver_fd()
    project_max_jobs = _project_max_jobs_env()
    # UX-846 (another track): a bind-mounted `PATH` of token-holding
    # wrappers - `_resolve_kind_and_probe` reads only whether it is set,
    # to choose the ninja policy; this shim does not create or size them.
    kind_context = _resolve_kind_and_probe(
        element, jobserver_fd, jobserver_fifo, project_max_jobs, real_bwrap)
    record_jobserver_decision(
        os.environ.get("BST_TRACE_JOBSERVER_DECISIONS"), sys.argv[1:],
        element, project_max_jobs, kind_context=kind_context,
    )
    # UX-849: a plan-active sandbox binds its own proxy and, only then,
    # marks `proxy_done_path` when it exits - a build with no `--plan`
    # never sets `BST_TRACE_PROXY_DIR`, so `proxy_fifo` is always `None`
    # and this whole item costs nothing. The proxy's own auth (fd, or
    # its path rewritten under `bind_dst` - UX-869, no bind of its own)
    # follows `BST_TRACE_JOBSERVER_AUTH`, the coordinator's fix: GNU
    # Make 4.3 (this box, CI) rejects `fifo:` outright.
    opts_now, _cmd_now = split_bwrap_args(sys.argv[1:])
    pinned_now = jobserver_decision(
        parse_element_max_jobs(opts_now), project_max_jobs) == JOBSERVER_PINNED
    proxy_fifo_host, proxy_done_path = _element_proxy_paths(element, pinned_now)
    proxy_fd, proxy_fifo = _resolve_proxy_auth(proxy_fifo_host)
    # UX-874: the host chose `fifo:` from *its own* `make --version`
    # (jobserver_auth_style, UX-841) - narrowed here, per element.
    jobserver_pool = _narrow_jobserver_to_sandbox_make(
        {"element": element, "element_kind": kind_context["element_kind"],
         "real_bwrap": real_bwrap, "opts": opts_now,
         "ninja_probe": kind_context["ninja_probe"],
         "wrappers_dir": kind_context["wrappers_dir"],
         "jobs_present": _setenv_value(opts_now, "JOBS") is not None}, pinned_now,
        pool={"fd": jobserver_fd, "fifo": jobserver_fifo,
             "proxy_fd": proxy_fd, "proxy_fifo": proxy_fifo})
    jobserver_fd, jobserver_fifo = jobserver_pool["fd"], jobserver_pool["fifo"]
    proxy_fd, proxy_fifo = jobserver_pool["proxy_fd"], jobserver_pool["proxy_fifo"]
    if inject:
        argv = build_shim_argv(real_bwrap, sys.argv[1:], bind_src, bind_dst,
                               preload_so, trace_log,
                               invocation_id=invocation_id,
                               # UX-106: the in-sandbox path of the ptrace
                               # spine, or absent. Read from this shim's own
                               # environment, which `run_traced_build` sets -
                               # the same channel `BST_TRACE_PRELOAD_SO`
                               # already uses.
                               spine=spine,
                               jobserver_fd=jobserver_fd,
                               jobserver_fifo=jobserver_fifo,
                               project_max_jobs=project_max_jobs,
                               element_kind=kind_context["element_kind"],
                               ninja_probe=kind_context["ninja_probe"],
                               wrapper_dir=kind_context["wrappers_dir"],
                               wrapper_cap=os.environ.get("BST_TRACE_WRAPPER_CAP"),
                               proxy_fd=proxy_fd,
                               proxy_fifo=proxy_fifo,
                               lto_cap=os.environ.get("BST_TRACE_LTO_CAP"),
                               wrapper_dir_override=kind_context["wrapper_dir_override"],
                               wrapper_mode=kind_context["wrapper_mode"])
    else:
        argv = [real_bwrap, *sys.argv[1:]]
        proxy_done_path = None

    # UX-148: under `--diagnose` only, run the real bwrap as a child so
    # its stderr can be kept. `buildbox-run` reports only a return code
    # on at least one real stack, so whatever the sandbox said when it
    # died was gone - the record proved the rewrite happened and could
    # not say what bwrap objected to.
    diagnostics_path = os.environ.get("BST_TRACE_DIAGNOSTICS")
    stderr_path = None
    if diagnostics_path:
        try:
            stderr_path = stderr_record_path(diagnostics_path, invocation_id)
        except OSError:
            stderr_path = None  # a diagnostic must never fail a build

    fifo_host = _active_jobserver_fifo(
        {"fd": jobserver_fd, "fifo": jobserver_fifo,
         "proxy_fd": proxy_fd, "proxy_fifo": proxy_fifo})
    fifo_sandbox = (_sandbox_fifo_path(bind_src, bind_dst, fifo_host)
                    if fifo_host else None)
    record_diagnostics(diagnostics_path, list(sys.argv[1:]),
                       argv, real_bwrap, element, spine, inject,
                       stderr_path=stderr_path,
                       jobserver_fifo_host=fifo_host,
                       jobserver_fifo_sandbox=fifo_sandbox)

    return _exec_or_run(real_bwrap, argv, stderr_path, proxy_done_path)


def _exec_or_run(real_bwrap: str, argv: list[str], stderr_path: Optional[str],
                 proxy_done_path: Optional[str]) -> int:
    """`main`'s own exec dispatch, split out to keep its branching under
    the baseline's cap: `--diagnose` tees (`run_teed`), a proxy-bound
    sandbox forks so its `.done` marker can be written after it exits
    (`run_and_mark_done`), and the default path still `execv`'s exactly
    as before - unreachable except by returning, since `execv` replaces
    this process outright on success."""
    if stderr_path:
        try:
            status = exit_like(run_teed(real_bwrap, argv, stderr_path))
            if proxy_done_path:
                with contextlib.suppress(OSError):
                    open(proxy_done_path, "w").close()
            return status
        except OSError as error:
            # Falling through to the plain exec is the safe direction: a
            # capture that cannot tee is still a capture.
            sys.stderr.write(
                f"bga: could not tee this sandbox's stderr ({error}); "
                f"running it without the record.\n")

    # UX-849: a proxy-bound sandbox is forked, not `execv`'d, so the
    # `.done` marker below can be written once it actually exits - the
    # only case, beside `--diagnose` above, where this shim outlives the
    # real bwrap rather than becoming it.
    if proxy_done_path:
        return run_and_mark_done(real_bwrap, argv, proxy_done_path)

    try:
        os.execv(real_bwrap, argv)
    except OSError as error:
        # UX-146: this used to be a Python traceback on `buildbox-run`'s
        # stderr, which BuildStream reports as `buildbox-run failed with
        # returncode 1` and buries in an element log. One sentence
        # naming the binary and what the kernel said.
        sys.stderr.write(
            f"bga: could not exec the real bwrap at {real_bwrap}: {error}\n"
            f"bga: set BST_TRACE_REAL_BWRAP if it lives somewhere else.\n")
        return 127
    return 1  # unreachable if execv succeeds


if __name__ == "__main__":
    sys.exit(main())
