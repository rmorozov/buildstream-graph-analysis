# UX-141: the guard list names a site that is gone and misses the one that runs most

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-128, UX-130 (done — this is their seam)

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

- The SEIZE-unavailable path (UX-140) and group-stop detach (UX-143 — this line said UX-142, which is `bga doctor`'s hardcoded target; corrected by `UX-154`).

## Acceptance Test

`FAIL_CONT_AT=attach` in a real sandbox: build completes untraced-
equivalent, degradation names `attach`, nothing in state `T`;
`FAIL_CONT_AT=initial` is rejected as an unknown site rather than
silently inert; the mutation run (attach guard removed → timeout) is
pasted; tier pin matches collection.


---

## What was built

`CONT_SITES = ["exec", "exit", "fork", "signal", "attach"]`, once, in the
test module — and the spine now **rejects a name that is not one of
them** rather than ignoring it:

```text
$ BST_TRACE_SPINE_FAIL_CONT_AT=initial spine -- /bin/sh -c "exit 7"
spine: BST_TRACE_SPINE_FAIL_CONT_AT=initial names no restart site.
Known sites: exec exit fork signal attach
rc=2
```

That is the part that stops this recurring: a stale list now fails
loudly instead of testing nothing. Both `[initial]` runs had been passing
while injecting nothing, one of them inside the pinned bst tier.

### The falsification, at the `attach` site specifically

`attach` is the restart that runs once per auto-attached descendant —
more often than every other site combined. With the guard removed (the
pre-`UX-128` discard):

```text
guard removed:  rc=124   # timeout(1) at 25s - the hang UX-128 exists to prevent
guard restored: rc=7     # the command's own exit status
```

Tier pin moved 37 → **39**, and the delta is not from this item: the
`initial`→`attach` swap is net zero (five sites before, five after).
Both new bst tests come from `UX-142`. Collection confirms 39.
