# UX-541: the gap sweep is cut and still quadratic, and the reason is a contract

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** `UX-539` (the sweep this is the remainder of), `UX-531` (the round that measured the term) | **Found by:** `UX-539`, measuring its own close | **Serves:** anyone analysing a monorepo | **Topic:** analysis

## Motivation

`UX-539` replaced the per-gap interval sweep with one cursor and cut
the sub-intervals **built** by 2.3x. The sub-intervals actually
**read** did not move:

```text
                        1,202     2,402     4,002    exponent
sub-intervals built    99,781   450,843 1,520,246    n^2.26 -> 44,064 / 215,360 / 655,904
sub-intervals read      (same shape either side)     n^2.26 -> n^2.25
mean slices per call     13.7        —      71.7
```

The leading saturated run itself grows with the run, and
`holder_time_us` has one entry per holder in that run **by
construction**: `_build_holder_info` publishes `blocking_tasks` as the
holder list, so a gap inside a wide saturated window reads a wide list
whatever the sweep does.

So the remaining term is not an algorithm that can be substituted. It
is what the published shape says a gap's blame is, and shrinking it
means changing that shape — a contract, under `UX-190`'s rule.

## Required Fix

Decide, on a measurement rather than on the shape: does a reader of
`blocking_tasks` ever use more than the top few holders? `UX-400`'s
ledgers say which fields reach a reader. If not, `blocking_tasks`
carries a bounded head plus a total, the contract bumps, and the sweep
falls out of `n^2.25` on its own.

If a reader does use the whole list, the number is the reason it
stays, written here.

## Out of Scope

- Re-doing `UX-539`'s cursor — it is the right sweep for the shape it
  is given.

## Acceptance Test

The exponent re-measured the way `UX-531` and `UX-539` measured
theirs — interleaved A/B, min of five, at 1,202 / 2,402 / 4,002, with
the output byte-identical or the contract bumped and the golden
snapshot moved with it.
