# UX-128: three more unguarded CONT sites reopen the hang, one branch over

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-117 (done — this is its perimeter, not its regression)

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
