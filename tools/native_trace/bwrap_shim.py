#!/usr/bin/env python3
"""A `bwrap` shim placed ahead of the real `/usr/bin/bwrap` in `$PATH` -
the mechanism validated for real in UX-11's Deep Experiment (see
docs/scenarios/UX-11-native-build-system-profiler-tool.md): a naive
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
import os
import sys
from typing import List, Optional, Tuple

# bwrap flags, keyed by how many trailing positional args each consumes -
# from `bwrap --help` (bubblewrap 0.9.0, the version this was validated
# against). Only flags BuildStream's own bwrap invocation is confirmed to
# emit (via real `strace`/argv capture in UX-11's spike) need to be exactly
# right; the rest degrade safely (see _split below).
_TWO_ARG_FLAGS = {"--bind", "--ro-bind", "--dev-bind", "--ro-bind-try", "--dev-bind-try", "--setenv", "--symlink"}
_ONE_ARG_FLAGS = {
    "--unsetenv", "--chdir", "--hostname", "--uid", "--gid", "--dir", "--cap-drop", "--cap-add",
    "--proc", "--dev", "--tmpfs",
}
_ZERO_ARG_FLAGS = {
    "--unshare-pid", "--unshare-net", "--unshare-uts", "--unshare-ipc", "--unshare-user",
    "--unshare-user-try", "--unshare-cgroup", "--unshare-cgroup-try", "--unshare-all",
    "--die-with-parent", "--new-session", "--as-pid-1",
}


def split_bwrap_args(args: List[str]) -> Tuple[List[str], List[str]]:
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
    opts: List[str] = []
    while i < n:
        arg = args[i]
        if arg in _TWO_ARG_FLAGS:
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


def extract_element_name(opts: List[str]) -> Optional[str]:
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
            return opts[i + 1].rstrip("/").rsplit("/", 1)[-1]
    return None


def build_shim_argv(
    real_bwrap: str,
    bst_args: List[str],
    bind_src: str,
    bind_dst: str,
    preload_so: str,
    trace_log: str,
) -> List[str]:
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
    return [real_bwrap, *opts, *injected, *cmd]


def main() -> int:
    real_bwrap = os.environ.get("BST_TRACE_REAL_BWRAP", "/usr/bin/bwrap")
    bind_src = os.environ["BST_TRACE_BIND_SRC"]
    bind_dst = os.environ["BST_TRACE_BIND_DST"]
    preload_so = os.environ["BST_TRACE_PRELOAD_SO"]
    trace_log = os.environ["BST_TRACE_LOG_DST"]
    argv = build_shim_argv(real_bwrap, sys.argv[1:], bind_src, bind_dst, preload_so, trace_log)
    os.execv(real_bwrap, argv)
    return 1  # unreachable if execv succeeds


if __name__ == "__main__":
    sys.exit(main())
