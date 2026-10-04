# UX-1315: a nested build can run the ninja wrapper

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the owner's LLVM 22.1 build under `--jobserver auto` (2026-10-04) | **Serves:** R1, R2 | **Topic:** capture | **Area:** tools | **Shape:** bounded | **Reading:** container

**Guard:** `tests/unit/test_a_nested_build_can_run_the_ninja_wrapper.py`

## Motivation

> cmake error at cmakelist.txt 46. running '…/wrappers/ninja' '--version' failed with bga: ninja : wrapper re entered itself.

`bga_run_wrapped` exported `BGA_WRAPPER_TOOL=ninja` and refused any process
that inherited it. LLVM's nested configure (runtimes, native tablegen) runs
under the real ninja and probes `CMAKE_MAKE_PROGRAM --version`, which is the
wrapper again: a legitimate nested invocation called a repeat. The guard is
for `UX-846`'s case, the wrapper resolving "real" to itself.

## Decomposition

Input classes: nested wrapper call under the real ninja (via `sh -c` and a child); a rule that execs the wrapper directly (PPID is the exec'd real ninja's PID); the wrapper exec'ing a wrapper copy (same PID); the wrapper forking a copy (`--help`, `--version`, `-j`). Journey: `bga_run_wrapped` guard -> `bga_find_real` -> exec or fork of `$real`. The `flto` shim shares the guard and only execs.

## Required Fix

The guard identifies the recursion, not any inherited invocation.

**Decision:** `BGA_WRAPPER_TOOL=tool:$$` is exported; an exec chain keeps
the PID, so `$$` matching is a repeat. A forked `$real` (`--help`,
`--version`, the `-j`/`--threads` run) gets `BGA_WRAPPER_FORK=tool:$$` on
its own command line only, so `$PPID` matching is a repeat. A single
variable checked against `$PPID` was rejected: the exec'd real ninja's PID
is the recorded one, and a rule shell that execs the wrapper has it as PPID
(`sh -c "ninja ..."`), a false positive. POSIX sh only, no coreutils (`UX-918`).

## Out of Scope

Telling a recursion through an intermediate shell from a nested build: no
marker can, so `BGA_WRAPPER_DEPTH` caps any wrapper chain at 16 instead. The
verifier's trampoline (an unmarked "real" ninja running a wrapper copy via
`sh -c`, no exec) ran unbounded on the two markers alone; the old inherited
name refused it at depth 2.

## Acceptance Test

The guard stages a fake real ninja whose child calls `ninja --version`
through the wrapper (must run), a rule shell exec'ing the wrapper (must run),
and a marker-less wrapper copy reached by exec and by fork (must exit 127
with the message). It reddens under each mutation below.

## Outcome

### The gap, measured

```text
$ (old guard) fake ninja -> sh -> child -> `ninja --version` via the wrapper
bga: ninja: wrapper re-entered itself          exit 127
```

### The close, measured

```text
$ python3 -m pytest -q -p no:xdist tests/unit/test_a_nested_build_can_run_the_ninja_wrapper.py tests/unit/test_a_held_tool_returns_its_tokens.py
15 passed
```

`test_a_held_tool_returns_its_tokens.py`'s isolation case now sets
`BGA_WRAPPER_FORK=ld.lld:<its own pid>`: the old bare tool name no longer
means "inside a wrapper".

### Mutations verified red and reverted (7)

| # | mutation | reddened |
|---|---|---|
| M1 | back to the plain tool-name check | 3 of 15 (nested, direct rule, isolation) |
| M2 | the `$PPID` fork clause dropped | 2 of 15 (fork copy, isolation) |
| M3 | the `$$` clause dropped | 1 of 15 (exec copy) |
| M4 | `$PPID` compared to the tool marker | 2 of 15 (direct rule, isolation) |
| M5 | guard removed (`if false`) | 3 of 15 (exec copy, fork copy, isolation) |
| M6 | the pre-UX-1315 guard, under a jobserver (the owner's forked path) | 1 of 1 |
| M7 | no depth cap, the verifier's trampoline | 1 of 1 (20 s, killed by the test's timeout) |
