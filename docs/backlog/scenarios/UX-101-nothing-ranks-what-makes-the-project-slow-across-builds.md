# UX-101: nothing ranks what makes the project slow across builds

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-91 (the multi-build log tree), UX-92 (invalidation roots); UX-93 sharpens the cause labels

Direction 3, item 2 — see
[`design/directions.md`](../../design/directions.md).

## Motivation

Every ranking the tool produces is about one build: the critical path
of *that run*, the realizable saving in *that capture*. But the
question a team lead actually has is longitudinal: **which element
costs us the most wall-clock per week?** — and its answer is a
different ranking. An element that is 4th on today's critical path but
rebuilds in 80% of builds (a volatile key near the root, a
frequently-edited component) taxes the team more than today's #1,
which rebuilds once a month.

The data is already on disk. Plane 3's log tree keeps one timestamped
log **per build instance** across history — round 11's tree already
holds the A/B/C experiment's three builds of the same project, and the
capture workflow now publishes fdsdk's tree — and UX-92 knows, for any
pair of runs, *why* each rebuild happened (invalidation root vs churn).

`developer tax(element) = rebuild frequency × mean rebuild cost`,
summed over the log tree's time span.

## Required Fix

A `bga cache-logs` section (and JSON):

1. Per element across the tree: build count, mean and total build
   seconds, and the tax ranking by total seconds over the window. The
   window and build count are printed with the ranking (a 3-build tree
   says so, and says the ranking is weak evidence).
2. **Cause annotation** where consecutive builds' cache keys are
   available in the logs' filenames/headers: how many of an element's
   rebuilds trace to its own key changing vs an upstream root vs
   unchanged-key (the UX-93 retention case). The root that explains the
   most downstream tax is the headline — one volatile key near the root
   *is* the top developer tax, and this is the number that proves it.
3. The standing Plane 3 hedges (one-second resolution, no scheduler
   context, nothing feeds a certified floor) carry over verbatim.

## Out of Scope

- Cross-machine aggregation (one log tree = one machine's history;
  fleet-level tax is a different task with a different data problem).
- Gating (a tax regression gate needs a per-window noise model that
  does not exist yet — same reason UX-92 deferred stage 3).

## Acceptance Test

On this machine's round-11 tree (three builds: cold A, codegen-tweak B,
core-tweak C): `core.bst` tops the tax ranking (rebuilt in all three,
heaviest), the cause annotation shows B's rebuilds rooted at
`codegen.bst` and C's at `core.bst`, and the 3-build window is declared
weak. On the fdsdk published tree: the ranking renders for the rebuild
set and the top entry's cause distribution is printed. Determinism over
the same tree.
