# UX-541: the gap sweep is cut and still quadratic, and the reason is a contract

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** `UX-539` (the sweep this is the remainder of), `UX-531` (the round that measured the term) | **Found by:** `UX-539`, measuring its own close | **Serves:** anyone analysing a monorepo | **Topic:** analysis

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

## Outcome (round 81, 2026-09-02) — 🟢 Done

The decision the item asked for, and the premise is half wrong.

### The scale family, which was not on record

Only 4,002 had a pasted recipe. All three:

```text
gen-synthetic --layers 12 --width 100 --seed 1   ->  1,202   (the default)
gen-synthetic --layers 12 --width 200 --seed 1   ->  2,402
gen-synthetic --layers 20 --width 200 --seed 1   ->  4,002
```

### The gap, measured — the exponent is in breadth, not in n

Instrumented `_iter_saturation_intervals` and `_build_holder_info` over
a whole `analyze_run`. Holding width at 200 so only the element count
grows:

```text
  1202  sub-intervals read  180,930   blocking_tasks width  mean  95.83  max 396
  2402  sub-intervals read  383,680                         mean 103.89  max 383
  4002  sub-intervals read  655,904                         mean  92.87  max 420
exponent in n: ln(655904/180930)/ln(4002/1202) = 1.07    width: FLAT
```

Against the canonical family, where width doubles between the first two
points: 85,112 -> 383,680 reads, x4.51 for x2.00 elements, exponent
**2.18**. So `n^2.25` is real but is not an exponent in `n` — the
holder list tracks the run's parallel breadth, and the two only grow
together when the fixture is widened. The item's "the leading saturated
run itself grows with the run" holds only for wider runs, not larger
ones.

### The reader question, answered

No reader reads it. `blocking_tasks` appears nowhere in `bga/` outside
its own producer; `bga/validation/invariants.py:327` reads only
`ambiguous`; it is in no `bga/schemas.py` contract. Emptying the field
outright leaves the published document **byte-identical** at all three
sizes — so the whole term is worth at most:

1,202 noise · 2,402 -16.3% · 4,002 -7.8%, digests identical.

### What was taken instead

`_classify_wait_gap` returns the **first** segment's holder_info and
drops every later one, so those were accumulated and sorted for
nothing: **40.5%** of the builds at 1,202, 47.5% at 4,002. Gated on
`resource_wait_holder_info is None`. Interleaved A/B, min of three,
four arms in one worktree (`base` = `ca825c3`; adjacent runs of one
arm swing 15%, hence interleaving):

```text
     n       base     UX-541     UX-542       both
  1202     1.561s     1.459s     1.495s     1.476s     UX-541 x0.935
  2402     4.218s     3.796s     4.030s     3.628s     UX-541 x0.900
  4002    10.439s     9.491s     9.826s     8.406s     UX-541 x0.909
```

Output byte-identical at all three (sha256 of the document less
`run_instance`/`producer`: `52d1e446dc33e8cf`, `217b3924ceaea175`,
`0cb454b75b589195`, before and after). A constant-factor win: the
exponent moves 1.50 -> 1.49, not a complexity change.

### Mutations verified red and reverted (1)

| # | mutation | reddened |
|---|---|---|
| M1 | `wants_holders` forced True — build every segment again | both clauses of `TestTheHolderMapIsBuiltOnlyForTheSegmentThatIsKept` — 2 failed, 12 passed |

### Deviation from the Required Fix

**Yes, deliberately.** The fix named "a bounded head plus a total,
the contract bumps"; neither half was taken. No published contract
carries `blocking_tasks` to bump, and a bounded head serves no reader
either — none exists. It buys at most 7.8% at 4,002, against a
spec-mandated shape (Part 8.2), so it was not worth a spec deviation.
The mandated-but-unread field is filed as `UX-553`.
