# UX-130: seize, don't TRACEME — the attach-stop should be identifiable, not guessed

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-118 (done — this is what its fix revealed)

## Motivation

UX-118 fixed the re-injected attach-SIGSTOP by *guessing* which SIGSTOP
is the attach one (first per pid, tracked in an 8192-slot table).
Round 13's review found the guess wrong at both ends:

- **The direct child's own SIGSTOP is eaten.** The child's attach-stop
  is consumed by the pre-loop `waitpid` and never enters the seen-set,
  so the first genuine SIGSTOP the loop sees for it is classified as
  the attach-stop and zeroed — contradicting the code's own "suppressed
  exactly once per pid" comment. The test written to prove pass-through
  (`kill -STOP $$` + delayed `kill -CONT`) **passes either way**: it
  asserts exit 0 and a marker file, both of which hold whether the stop
  was honored or swallowed.
- **`forget_pid` zeroes instead of tombstoning.** In open addressing a
  zeroed slot breaks the probe chain; the hash is a bijection below pid
  8192, so collisions begin exactly at fdsdk's 127k-pid scale — where a
  broken chain swallows a genuine SIGSTOP and leaks slots toward the
  table-full fallback.
- **Classic ptrace cannot distinguish a group-stop from a
  signal-delivery stop at all** (both are `WSTOPSIG==SIGSTOP`,
  `event==0`), so a genuinely group-stopped tracee ping-pongs instead
  of staying stopped — falsifying the "behaves exactly as untraced"
  comment. The primitive that fixes this (`PTRACE_LISTEN`) requires
  `PTRACE_SEIZE`.

One mechanism change removes all three: **`PTRACE_SEIZE` +
`PTRACE_INTERRUPT`/`PTRACE_EVENT_STOP`** makes the attach-stop exactly
identifiable (no first-SIGSTOP heuristic, no pid table at all) and
group-stops properly observable.

## Required Fix

1. Move the spine from `PTRACE_TRACEME`+`SETOPTIONS` to
   `PTRACE_SEIZE` on the direct child + inherited auto-attach; handle
   `PTRACE_EVENT_STOP` (attach and group-stop cases) per ptrace(2),
   with `PTRACE_LISTEN` for group-stops. Delete `g_seen`/`forget_pid`.
2. The pass-through test made falsifiable: assert the stop was real
   (wall-clock ≥ the CONT delay, or `/proc/<pid>/stat` state `T`
   observed) — on the direct child specifically.
3. A tracee that group-stops under the spine stays stopped until CONT'd
   externally, exactly as untraced — pinned by test.
4. If SEIZE proves unavailable in some sandbox configuration, the
   TRACEME path may remain as a fallback — with the seen-set defects
   (child seeding, tombstones) fixed there, since a fallback carries
   the same correctness bar.

## Out of Scope

- The CONT guards (UX-128) — land those first; this rebuilds the attach
  layer they guard.

## Acceptance Test

The falsifiable pass-through test passes on the direct child and a
grandchild; a `kill -STOP` aimed at a traced process leaves it in state
`T` under the spine (verified via `/proc`), resumable by `kill -CONT`;
UX-118's kill-the-tracer clause still passes 3/3 in the bst tier; and
fdsdk-scale pid churn is exercised by a synthetic 10k-fork fixture with
zero swallowed stops (the storm extended, or a dedicated one).
