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
import json
import os
import sys
import time
from typing import List, Optional, Tuple

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


def unknown_flags(args: List[str]) -> List[str]:
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


def build_shim_argv(
    real_bwrap: str,
    bst_args: List[str],
    bind_src: str,
    bind_dst: str,
    preload_so: str,
    trace_log: str,
    invocation_id: Optional[int] = None,
    spine: Optional[str] = None,
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


def record_argv(log_path: str, argv: List[str], limit: int) -> bool:
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
            with open(log_path, "r", encoding="utf-8") as handle:
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
                with open(f"/proc/{pid}/stat", "r") as handle:
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
        with open(census_path, "r", encoding="utf-8") as handle:
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


def record_diagnostics(log_path: Optional[str], received: List[str],
                       exec_argv: List[str], real_bwrap: str,
                       element: Optional[str], spine: Optional[str],
                       injected: bool) -> bool:
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
    bind_src = os.environ["BST_TRACE_BIND_SRC"]
    bind_dst = os.environ["BST_TRACE_BIND_DST"]
    preload_so = os.environ["BST_TRACE_PRELOAD_SO"]
    trace_log = os.environ["BST_TRACE_LOG_DST"]
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
    if inject:
        argv = build_shim_argv(real_bwrap, sys.argv[1:], bind_src, bind_dst,
                               preload_so, trace_log,
                               invocation_id=invocation_id,
                               # UX-106: the in-sandbox path of the ptrace
                               # spine, or absent. Read from this shim's own
                               # environment, which `run_traced_build` sets -
                               # the same channel `BST_TRACE_PRELOAD_SO`
                               # already uses.
                               spine=spine)
    else:
        argv = [real_bwrap, *sys.argv[1:]]

    record_diagnostics(os.environ.get("BST_TRACE_DIAGNOSTICS"), list(sys.argv[1:]),
                       argv, real_bwrap, element, spine, inject)

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
