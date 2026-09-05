# UX-128: three more unguarded CONT sites reopen the hang, one branch over

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-117 (done — this is its perimeter, not its regression) | **Topic:** capture | **Area:** tools/native_trace

## Motivation

UX-117 guarded the generic signal-delivery restart
(`spine.c:624`: CONT failure → `degrade("cont-failed")`) and then wrote
*"no tracee is ever left stopped by any other path, so there is no
third case for a set to cover"* (`spine.c:572-576`). There are three —
the exec-stop (`:588`), exit-stop (`:596`) and fork/clone-stop (`:605`)
restarts all **discard the `PTRACE_CONT` return value** (as does the
initial post-SETOPTIONS CONT at `:508`, issued even on the detach
path). A CONT failure at any of them leaves that tracee stopped
forever; `waitpid(-1)` never reaches `ECHILD`; the build hangs — the
identical failure mode UX-117 was filed for.

Two of UX-117's own acceptance clauses also never landed as written:
the "nothing left stopped" assertion via `/proc/<pid>/stat` state is
not asserted anywhere, and the test runs as a plain subprocess, not in
the bst-gated sandbox the acceptance names — the same real-sandbox gap
UX-118 and UX-119's item 2 share (UX-119's SIGTERM test kills the
*command*, not the spine, and never varies tracee count).

> **Partly superseded by `UX-130` (2026-08-19).** The `initial` site
> named below — the post-`SETOPTIONS` restart — no longer exists:
> `PTRACE_SEIZE` sets its options at attach and has no such CONT, so the
> five guarded sites are now four plus `attach`, the restart that runs
> once per auto-attached descendant. The verification table's `initial`
> row therefore describes a call site that is gone; its four others
> stand. `UX-141` moved the test lists to match and made an unknown site
> name a hard error, because for one round both `[initial]` runs passed
> while injecting nothing.

## Required Fix

1. Route all four CONT sites through the same failure guard as `:624`.
2. UX-117's missing assertions: `/proc/<pid>/stat` state checked before
   reaping in the degrade test; the degrade and kill-the-tracer tests
   (and UX-119's SIGTERM-at-the-spine, aimed at the spine's pid, at two
   tracee counts) run `bst`-gated inside a real bwrap sandbox, with the
   tier pin bumped.
3. The `:572-576` comment updated to describe the guard that now
   actually exists.

## Out of Scope

- The SIGSTOP/seize mechanism questions (UX-130).

## Acceptance Test

Force a CONT failure at each of the four sites in turn (the existing
`BST_TRACE_SPINE_DEGRADE_AFTER`-style seam, extended per site): the
build completes with its untraced exit status every time, nothing is
left in state `T`, and the degradation record names the site. All
spine failure-path tests report as `bst`-tier tests in CI's pinned
count.

## Fix Implemented

### One guard, because the defect was that the repetition diverged

Every `PTRACE_CONT` in `spine.c` now goes through `resume(pid, sig,
site)`. There is exactly one left in the file, inside that function.
On failure it degrades — naming the site, so `reason=cont-failed-exec`
says *which* restart broke — and detaches, which resumes the tracee;
`ESRCH` stays ordinary, and the pending signal goes to the detach so a
tracee stopped for a real signal still receives it.

`UX-117` wrote three lines at one site and a comment asserting the other
paths could not strand a tracee. Making it a function is the fix for the
comment as much as for the code: five copies of a guard is five chances
for four of them to be missing.

**One latent bug found while wiring it.** The initial restart was issued
unconditionally, including on the `setoptions-failed` path that had just
detached the child one line above — a `PTRACE_CONT` at a pid no longer
ours. It is now in the `else` branch.

### The `:572-576` comment

The reasoning it carried is sound and stays; the sentence *"no tracee is
ever left stopped by any other path"* is gone, replaced by what is now
true — the invariant that branch relies on is **enforced** by `resume()`
rather than asserted about four sites that did not do it.

### The tests UX-117 named and did not land

- `/proc/<pid>/stat` state is now read directly
  (`test_a_degrade_leaves_nothing_in_state_T`). An exit code cannot see a
  stranded tracee: the build completes around it, which is precisely why
  the original clause mattered and why asserting the exit status was not
  it.
- The failure paths run **inside a real bwrap sandbox**, `bst`-gated:
  five sites × `--unshare-pid`, the degrade path, and `UX-119`'s SIGTERM
  clause corrected twice — aimed at the *spine's* pid rather than the
  command's, at 1 and at 8 tracees, asserted against bare bwrap rather
  than against the number 143.

Tier pin 26 → **34**.

## Verification Log

Done 2026-08-19.

### Every site, forced to fail

```text
$ python -m pytest tests/unit/test_process_spine.py -q
33 passed in 23.12s

$ python -m pytest tests/unit/test_process_spine.py -m bst -q
14 passed, 27 deselected in 20.51s
```

### Falsified, which is the part that matters

With `resume()` returning before its error check — exactly the
pre-`UX-128` behaviour of discarding the `PTRACE_CONT` result — every one
of the five sites hangs until the test's own timeout:

```text
E   subprocess.TimeoutExpired: Command '[.../spine', '--', '/bin/sh', '-c',
    'for i in 1 2 3; do (sleep 0.3; true) & done; wait; ... exit 7']'
    timed out after 30 seconds
FAILED …test_a_cont_failure_at_any_site_still_completes_the_build[initial]
FAILED …test_a_cont_failure_at_any_site_still_completes_the_build[exec]
FAILED …test_a_cont_failure_at_any_site_still_completes_the_build[exit]
FAILED …test_a_cont_failure_at_any_site_still_completes_the_build[fork]
FAILED …test_a_cont_failure_at_any_site_still_completes_the_build[signal]
5 failed in 150.80s
```

Five sites, five hangs, five 30-second timeouts — and all five pass with
the guard. That is the hang `UX-117` was filed for, reproduced at each of
the four places its fix did not reach.

### Deviation, recorded

The acceptance says "the existing `BST_TRACE_SPINE_DEGRADE_AFTER`-style
seam, extended per site". It is a **second** seam
(`BST_TRACE_SPINE_FAIL_CONT_AT=<site>`) rather than an extension of the
first, because the two force different things: the existing one trips the
degrade *decision* after N events, and this one makes a *specific
restart* fail. Extending the counter would have made the site a function
of event ordering, which is exactly the kind of test that passes for the
wrong reason. Both are read once at startup and neither is in the fixed
`BST_TRACE_*` list `bwrap_shim.py` passes through, so neither can reach a
real capture — asserted by `test_the_seam_is_off_unless_asked_for`.
