# UX-539: the two superlinear terms `UX-531` measured and did not take

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** `UX-531` (the three it did take, and the profile) | **Serves:** anyone opening a run of a few thousand elements | **Topic:** analysis

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

## Outcome (round 80, 2026-09-02) — 🟢 Done

### The gap, measured

Both terms live in `bga/structural/analyzer.py` and
`bga/attribution/blame_chain.py`. The sweep built 1,520,246
sub-intervals at 4,002 and its two callers read 651,649 — both break at
the end of the leading saturated run.

### After

Reachability is one bitset closure over the topological order
(`_reachability_counts`); only the counts are wanted, so no set is
materialised. The gap sweep is a generator whose slice cursor advances
with the boundaries instead of being re-found by binary search, and
`_resource_saturation_intervals` is `list()` of it — what `UX-42`'s
oracle still holds. cProfile, seeded 4,002 run:

```text
                             before                after
total calls              98,792,092           43,133,696   -56%
analyze_bottlenecks     22.131s cum          0.209s cum  (closure 0.160s)
  nx descendants/ancestors  4002 + 4002 calls, 21.831s ->  0 calls
the gap sweep           26.102s cum          5.316s cum
```

**The bound, load-independent, over a whole `bga analyze`:**

```text
                       1,202     2,402     4,002
whole-graph walks     2,404     4,804     8,004   ->  0 (one closure)
sub-intervals built  99,781   450,843 1,520,246   ->  44,064 / 215,360 / 655,904
```

Wall and child CPU, **interleaved before/after, min of five** — three
tracks share this machine and adjacent wall figures swing 2x:

```text
 1,202   before   5.03s   after   3.92s   x1.28    CPU  3.09 ->  2.48
 2,402   before  15.82s   after  12.24s   x1.29    CPU  9.86 ->  6.89
 4,002   before  35.84s   after  26.41s   x1.36    CPU 25.63 -> 17.67  x1.45
```

Output **byte-identical** at all three. Exponent: wall `n^1.63 ->
n^1.59`, CPU `n^1.75 -> n^1.62`.

### Mutations verified red and reverted (4)

| # | mutation | reddened |
|---|---|---|
| M1 | `_reachability_counts` becomes the per-node `nx` walk again | the query budget at all three sizes and the doubling clause — 4 failed, 17 passed (3,743 queries for a budget of 423 at 20 diamonds) |
| M2 | the closure ORs `bit[j]` only, dropping transitivity | the oracle on 2 of 4 shapes and the non-vacuity clause — 3 failed, 18 passed |
| M3 | `classify_resource_wait` reads the eager list again | both bound clauses — 2 failed, 19 passed (12 slices vs 402) |
| M4 | the slice cursor stops advancing | all three gap clauses **and** `UX-42`'s oracle — 6 failed, 15 passed |

M4 is the pair that matters: the bound alone accepts a sweep that reads
one slice and answers wrongly; the oracle stops it.

### Deviation

The gap sweep is **not** de-superlinearised, only cut 2.3x: the
sub-intervals *read* were already `n^2.26` and stay `n^2.25`, because the
leading saturated run grows with the run (mean 13.7 slices at 1,202,
71.7 at 4,002) and its `holder_time_us` has that many entries by
construction. Shrinking it changes what `_build_holder_info` publishes —
a contract, not an algorithm. **A row is owed** for that, and for what
now leads the profile untouched: `compute_criticality_probability`
(14.5s) and `_compute_perturbed_critical_path` (12.2s, 200 calls) in
`bga/diagnostics/`.

```text
$ make lint            ruff + PyMarkdown, All checks passed!
$ make test-touching   1 failed, 508 passed, 3 skipped in 63.53s - the failure
   is test_diagnostics_performance's 10s wall budget, 14.43s under three
   parallel tracks; alone it is 4 passed in 3.83s. Load, not this (UX-538).
```
