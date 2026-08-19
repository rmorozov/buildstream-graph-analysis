# UX-141: the guard list names a site that is gone and misses the one that runs most

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-128, UX-130 (done — this is their seam)

## Motivation

UX-130 deleted UX-128's `initial` restart site (SEIZE has no
post-SETOPTIONS CONT) and added `attach` (once per auto-attached
descendant — ~2,000 times on the storm, ~127k on fdsdk). Nothing
downstream moved:

- both failure-injection parametrize lists still include `"initial"`;
  `resume()` matches by `strcmp`, so `FAIL_CONT_AT=initial` injects
  nothing and **both `[initial]` tests pass vacuously** — one of them
  in the bst tier, inflating the pinned count by one;
- the **`attach` site has no failure-injection coverage in either
  tier** — the single most-executed restart in a real capture, and
  the exact "one of N copies of a guard is missing" defect UX-128 was
  filed for;
- `spine.c`'s seam comment still documents the old five-site list —
  the one place a reader would learn how to write the missing test;
- the naming test covers four sites, so nothing catches any of this.

## Required Fix

Parametrize lists and the naming test become
`["exec","exit","fork","signal","attach"]`; the seam comment updated;
the CI tier pin moved deliberately by the resulting delta; and
UX-128's falsification (guard removed → hang) re-run at the `attach`
site specifically. Annotate UX-128's five-site verification table per
the UX-132 convention while touching it.

## Out of Scope

- The SEIZE-unavailable path (UX-140) and group-stop detach (UX-142).

## Acceptance Test

`FAIL_CONT_AT=attach` in a real sandbox: build completes untraced-
equivalent, degradation names `attach`, nothing in state `T`;
`FAIL_CONT_AT=initial` is rejected as an unknown site rather than
silently inert; the mutation run (attach guard removed → timeout) is
pasted; tier pin matches collection.
