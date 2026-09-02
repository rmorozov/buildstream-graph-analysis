# UX-539: the two superlinear terms `UX-531` measured and did not take

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** `UX-531` (the three it did take, and the profile) | **Serves:** anyone opening a run of a few thousand elements | **Topic:** analysis

## Motivation

`UX-531` turned three per-gap scans into index lookups and cut
`bga analyze` at 4,002 elements from **44.01 s to 23.33 s** — `n^1.80`
to `n^1.69`. It stopped there because what is left is not a lookup
that was missed; it is two algorithms:

```text
                                        calls          cumulative
descendants / ancestors, once per node  4,001 + 4,002      16.2 s
_resource_saturation_intervals          per gap            28.2 s
```

`descendants`/`ancestors` walk the graph from each node in turn, which
is `O(n(V+E))` and is the shape `UX-042` named a "30x" for when the
term it measured was one of several. `_resource_saturation_intervals`
sweeps the interval list per gap, where a single sweep with a running
count would answer every gap at once.

Neither is a rewrite of the analysis. Both are the same substitution:
compute once over the whole run, read per node or per gap.

## Required Fix

- Replace the per-node reachability with one pass — a transitive
  closure over the reverse topological order, or the bitset the graph
  is small enough for at 4,002 — and keep `descendants(x)` as its
  reader, so no call site changes.
- Replace the per-gap interval sweep with one sorted sweep that
  carries the running count, and index it by time.
- The exponent, measured the way `UX-531` measured it: interleaved
  A/B, min of three, at 1,202 / 2,402 / 4,002, with the output
  **byte-identical** at each size. A faster analysis that answers
  differently is a different analysis.
- The guard is the **bound**, not the seconds: `UX-531` counts whole-run
  walks (9 at 40 tasks and 9 at 80); this extends that count to the two
  terms above, so the next round cannot reintroduce a per-node pass
  without reddening.

## Out of Scope

- The seconds as an assertion, declined for `UX-531`'s reason: a 23 s
  guard needs a tier row it cannot pay for, and a second measured on a
  machine running three tracks is a second of noise (`UX-538`).
- Caching the analysis, which is `bga snapshot`'s job and already done
  — this is the path `bga view` takes on a run with no published
  analysis.

## Acceptance Test

The exponent at 1,202 / 2,402 / 4,002 before and after, both pasted,
and `bga analyze --format json` byte-identical at each size. Mutation:
put one of the two terms back per node — the walk-count bound must
redden, on the fixture and not on a clock.

## Outcome

_Not started._
