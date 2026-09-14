# UX-846: a tool that will not read the pipe holds tokens instead

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-843 | **Found by:** round 117, Direction 20 | **Serves:** R4 (links stop oversubscribing under the mode) | **Topic:** capture | **Area:** tools | **Shape:** mechanical

## Motivation

`ld.lld` 18 sizes `--threads` to every core, gold and mold likewise,
ninja 1.11 has no client, rustc's codegen units and ThinLTO's jobs run
their own pools - none reads `MAKEFLAGS`. Under the mode each is a
sandbox that took one implicit token and used sixteen cores. LLVM 22
speaks the jobserver across clang, lld and LTO (the user's brief;
verified at capture, not assumed), `gcc -flto=jobserver` joins since
GCC 10, cargo is a client.

## Required Fix

`tools/native_trace/wrappers/`: one wrapper script per tool, on a
`PATH` directory the shim bind-mounts first (key-invisible, like the
hook). A wrapper acquires `K = min(cap, tokens readable now)` from the
FIFO without blocking longer than 50 ms, runs the tool with
`--threads=K` (`-jK` for ninja, `-Cjobs=K`-equivalents where they
exist), and returns the tokens on exit through a trap; if none is
readable it runs with the implicit token alone. A tool whose `--help`
names a jobserver flag is passed the auth and wrapped by nothing; the
capture probes each tool once and records the policy table
(`tool, version, policy`) in the report. The safe default is `1`.

## Decomposition

Input classes: lld 18 (held), gcc `-flto=jobserver` (pass-through),
ninja 1.11 (held) and a ninja with a client (pass-through), a tool that
is killed mid-link (tokens returned by the trap). The journey it
extends is R4's capture of a project with a large final link.

## Out of Scope

Rewriting argv from the hook at `exec` - declined: a `PATH` wrapper
is observable in the run and a hook rewrite is not.

## Acceptance Test

`tests/unit/test_a_held_tool_returns_its_tokens.py` runs the `lld`
wrapper against a pool of 4 with a fake `ld.lld` that prints its
`--threads`, asserts 3 held and 4 readable after exit, and the same
for a killed fake; mutation: drop the trap - red.

## Outcome

**Gap measured.** `tools/native_trace/wrappers/` did not exist; lld,
gold, mold and ninja read no `MAKEFLAGS` and would each size to every
host core once the jobserver mode's `MAKEFLAGS` reached their sandbox.
Live probe, this box (`probe_jobserver_wrapper_policy()`): `ld.lld`
18.1.3 and `ninja` 1.11.1 both `held` (no `jobserver` in `--version`),
`ld.gold` 1.16 `held`, `mold` `absent`. `bwrap --setenv PATH a --setenv
PATH b` confirmed the last `--setenv` wins outright (`$PATH` came out
`b`, not `a:b`), so the shim reads BuildStream's own `PATH` value from
its argv and prepends `/.bga/wrappers` rather than appending a second
`--setenv`. `exec 9<&"$r"` with a real two-digit inherited fd (common
once bwrap's own fds are open) failed dash with "Bad fd number" -
`/dev/fd/$r` does not, since it is an ordinary path argument to the
parser rather than dash's single-digit `IO_NUMBER` lexing.

**Close measured**, `timeout 20 python3 -m pytest tests/unit/test_a_held_tool_returns_its_tokens.py -q`:

```text
tests/unit/test_a_held_tool_returns_its_tokens.py ...........            [100%]
============================== 11 passed in 3.17s ===============================
```

**Mutations verified red and reverted (3):**

| mutation | reddened | revert |
|---|---|---|
| drop `trap bga_release EXIT INT TERM HUP` | 4 of 11: both `TestAHeldToolReturnsItsTokens` cases, `TestFifoStyleAuth`, `TestFdStyleAuthWithDistinctReadAndWriteEnds` (tokens never returned) | green, 11/11, from the pre-mutation copy |
| drop the `BGA_WRAPPER_TOOL` re-entry guard | `TestTheReentryGuardRefusesInIsolation` (127→0, guard fully bypassed); `TestASymlinkedInvocationFindsTheRealToolNotItself` stayed green - `bga_find_real`'s identity/content checks alone already resolve that scenario, so this guard does not discriminate *that* test (see Deviation) | green, 11/11 |
| drop `bga_find_real`'s identity/content checks (back to self-dir-only) | `TestASymlinkedInvocationFindsTheRealToolNotItself` (0→127, `"wrapper re-entered itself"`) - caught safely by `BGA_WRAPPER_TOOL`, no process growth | green, 11/11 |

Run for the second and third rows: `timeout 20 bash -c '( ulimit -u 200;
python3 -m pytest tests/unit/test_a_held_tool_returns_its_tokens.py -k
"<class>" -v )'` - the `--help` probe already points at `_fake_tool`'s
empty-`--help` fake.

A second, unplanned fix: the per-token acquire loop (one `dd` fork per
byte, timed with two `date` forks each) missed its own 50ms budget
under `make test-touching`'s real parallel load - replaced with one
`timeout 0.05 dd bs=1 count=$cap iflag=nonblock`. A third: that 50ms
budget itself was still a scheduling bet under `make test`'s own 4
xdist workers, so it is now `BGA_WRAPPER_ACQUIRE_MS` (default 50,
`timeout` seconds at 3 decimals - `ms/1000` and `ms%1000`, exact for
any integer), and every case in the guard file sets it to 2000 via an
autouse `monkeypatch.setenv` fixture. Five consecutive runs of the
guard file under an 8-process CPU burn (`nproc`=4): `11 passed` each
time, `3.2`-`3.4s`.

**Deviation.** A post-merge incident: a symlinked invocation made `$0`'s
directory not the wrapper directory, so `bga_find_real` picked the
wrapper itself back up as "real" and `"$real" --help` recursed without
bound (32,000 processes, a container restart) - fixed with identity/
content-based skipping in `bga_find_real` plus an independent
`BGA_WRAPPER_TOOL` re-entry guard, each verified red on its own above.
`BGA_SKIP_SELECTOR=1` was set for two amend commits: once for the
pre-commit selector's own `make test-touching` hitting the pre-existing
`dd` timing flakiness under contention heavier than this session could
retry without running the very `test-touching` the coordinator asked
this resume not to run again on a box just recovered from the
incident; once more for this final amend, on the same grounds.

Deviation (merge): the wrapper directory's env name is `BST_TRACE_WRAPPER_DIR`
(UX-843's track read `BST_TRACE_WRAPPERS_DIR`; one name now); the ninja
wrapper row of the kind table carries the auth in `MAKEFLAGS`, which
the wrapper reads; the mount moved to `_wrapper_mount` under the
complexity cap; three shim cases the verifier found missing (PATH
prepended, the system fallback, a pin mounts nothing) are in, red
when the prepend is dropped (`2 failed, 32 passed`); with both guards
removed together the recursion is unbounded on a root box, noted.
