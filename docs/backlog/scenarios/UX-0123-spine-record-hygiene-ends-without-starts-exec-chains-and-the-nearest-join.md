# UX-123: spine record hygiene — ENDs without STARTs, exec chains, and the nearest join

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-106, UX-107 (done — these are their S4/S5/S6)

## Motivation

Three record-level defects from round 12's `spine.c`/parser review,
none build-breaking, each quietly distorting the data:

1. **ENDs for processes that never exec'd.** `PTRACE_EVENT_EXIT` fires
   for every tracee including fork-without-exec children, whose
   "cmdline" is the parent's; the parser discards these ENDs, but the
   discard is **uncounted** — a whole record class neither reported nor
   summarized.
2. **Exec chains bill the first image.** `sh -c "gcc …"` execs in
   place, producing N STARTs and one END; FIFO pairing lands CPU, peak
   RSS and exit status on the *pre-exec* image and counts the surplus
   START as "no observed exit". The shell/compiler chain is the common
   case, and it plausibly accounts for part of fdsdk's 8,135
   unobserved exits.
3. **The stream join takes the first hook record within its 1.0s
   tolerance, not the nearest** — and the repo's own tests assert that
   `--unshare-pid` namespaces reuse small pids quickly, so a stale
   unmatched hook record can capture a later spine record for a reused
   pid.

## Required Fix

1. Do not emit an exit record for a pid with no exec START (or emit a
   distinct record type), and publish the drop/fork-only count in the
   report's coverage block.
2. Decide the exec-chain billing (last image is what a profiler means
   by "the process") and implement it in pairing for both streams; the
   unobserved-exits count should then drop measurably on the fdsdk
   capture, which is the check.
3. Nearest-within-tolerance for the stream join.

## Out of Scope

- The hang paths (UX-117/118) and signal model (UX-119).
- hook.c's own pre-existing exec-chain shape beyond what shared
  pairing code fixes.

## Acceptance Test

A fixture build with a fork-no-exec child and an exec chain: no
phantom END rows, the chain's CPU/RSS/exit billed to the final image,
the fork-only count published. On the retained fdsdk spine capture,
re-parsed: unobserved-exit count reported lower with the delta
explained, and no join pairs a reused pid across a gap larger than the
nearest candidate's.
