# UX-103: cache health is a point reading with no trend

**Priority:** Medium | **Status:** 🟢 Done — with one deviation from the acceptance's arithmetic, recorded below | **Depends on:** UX-92 (per-run accounting), UX-96 (the baseline/refs fetch helper), UX-93 (honest churn labels first)

Direction 3, item 4 — and the trend stage UX-92 explicitly deferred.
See [`design/directions.md`](../../design/directions.md).

## Motivation

UX-92 gave one run a cache report card: hit ratio, transfer cost,
churn. A report card once is a diagnosis; the CI question is a trend:
**is the cache getting worse?** A remote that slows from 40MB/s to
5MB/s, a hit ratio eroding as a volatile key spreads, transfer time
quietly overtaking rebuild time — each of these degrades every build in
the organization, none is visible in any single run, and all are
computable from data the per-run capture refs (UX-81) now retain
weekly. This is the highest blast-radius-per-hour item in Direction 3:
one degrading cache server slows more people than any element ever
will.

The infrastructure prerequisites all exist as of round 11: retained
same-config history, a scheduled cadence, per-run `run/` directories
with pull/push task durations, and the UX-92 signals.

## Required Fix

1. A `bga cache-trend <run-dir>...` command (chronological run
   directories — in CI, supplied by UX-96's fetch helper): per run,
   hit ratio, churn count/seconds (with UX-93's honest labels),
   pull/push total seconds and per-artifact mean, rebuild-vs-pull
   balance. Rendered as one row per run plus a delta verdict on the
   newest against the trailing window (same scaled-MAD shape as the
   UX-59 band — reuse it, do not invent a second noise model).
2. A finding (id, severity) when the newest run's reading sits outside
   the window band: "pull time per artifact 3.2x the trailing median -
   the cache remote is degrading, before any element gets slower".
3. Wire into the capture workflow as a post-publish step once ≥3
   same-config refs exist, so the weekly schedule accumulates the
   trend without a human.

Bytes-per-second needs artifact sizes, which Plane 1 does not carry —
ship seconds-based first, and note size capture as the follow-on
(same posture as UX-100's size axis).

## Out of Scope

- A hard CI gate on the trend (needs more history than three runs; the
  finding is the deliverable, the gate is a later, evidenced decision —
  UX-92 stage 3's deferral reasoning stands).
- Cache-server-side metrics (this reads only what the build saw).

## Acceptance Test

Over the three retained incremental fdsdk refs (fetched via the UX-96
helper): the trend table renders three rows with real numbers and no
finding (same-commit runs, stable cache). Synthesize a degraded fourth
run (pull durations scaled up in a copy) and the transfer finding fires
naming the metric and the band. Two runs only → the command says the
window is insufficient rather than trending two points.

---

## Fix Implemented

`bga cache-trend RUN...` (`bga/cache_trend.py`), reading a chronological
series and judging only its newest member.

```text
run                             hit  built  cached     xfer  /artifact   churn
02-32064333551/run              72%     25      65        -          -       -
01-32113933158/run              72%     25      65        -          -   0+25r
00-32122941503/run              72%     25      65        -          -   0+25r
```

That is the three real retained fdsdk refs, fetched by `UX-96`'s helper.
Three facts in it are worth naming: the hit ratio is stable at 72%, the
churn column reads `0+25r` — zero waste, 25 rebuilt in *both* runs,
which is `UX-93`'s retention label surviving into the series — and
transfer is `-` rather than `0`, because every published capture is
taken with remotes ignored, by design, so there is no transfer to
measure.

### Three decisions, each of which had a cheaper wrong answer

**The noise model is `bga.compare`'s, imported.** `compute_band` and
`MIN_BASELINE_RUNS`, not a second implementation. The evidence for that
shape — seven repeated builds of one unchanged commit, and what a single
contaminated baseline does to a mean ± σ band — is in its docstring and
applies here unchanged.

**Churn is pairwise and keeps `UX-93`'s labels.** A run has no churn on
its own; churn is a fact about a run against its predecessor. Each row
computes it through the same `compute_cache_churn` the `compare` path
uses, so a run whose predecessor was caches-off reports no churn verdict
rather than a fabricated one.

**The band is widened to the fixed rule when the measured one is
narrower**, exactly as `bga compare` does. Found by running it: three
runs whose rebuild seconds differed by 0.03% produced a band 2.2s wide
on a 4740s median, and a 6% rise read as a regression. A band tighter
than quantization noise fires on everything.

### A real definition bug, caught by the synthetic run

Exercising the transfer trend meant adding synthetic PULL spans to a
copy of a real capture — and the *rebuild* seconds moved too. Cause:
`rebuild_us` was reading `signals.element_durations`, which is the
longest task per element **whatever its kind** (`UX-53`'s single
definition, correct for path computations and wrong here), so a 6.4s
pull outlasted a short build and became that element's duration. A trend
that sets rebuild time against transfer time cannot have transfer time
inside both sides of the comparison. `rebuild_us` now sums BUILD tasks
directly.

The false finding it produced — *"rebuild seconds is 1.1x the trailing
median"* on a run that rebuilt nothing new — is exactly the class of
thing `UX-93` was filed for, arriving in new code the same day.

### The acceptance, run

**A degraded fourth run.** Three real captures with synthetic pulls at
1.90s/2.00s/2.10s per artifact, then a fourth at 6.40s:

```text
[high] cache-trend-regression: transfer seconds is 3.2x the trailing median
(416.0s against 130.0s over 3 run(s), band 101.1s..158.9s) - the cache remote
is degrading, before any element gets slower
[high] cache-trend-regression: transfer seconds per artifact is 3.2x the
trailing median (6.4s against 2.0s over 3 run(s), band 1.6s..2.4s) - the cache
remote is degrading, before any element gets slower
```

**Two runs.** *"2 run(s) supplied; a band needs 3 trailing runs plus the
one being judged, so 4. The rows above are real readings with no verdict
attached."*

**Wired into the capture workflow**, after the publish so that the
capture just taken is the newest row and the run being judged. The step
is `continue-on-error`: a degrading cache is a finding to read, not a
reason to fail the job that produced the data. The exact step was run
by hand against the real refs before being committed.

### Deviation from the acceptance, recorded

The acceptance says *"over the three retained incremental fdsdk refs …
the trend table renders three rows with real numbers and no finding"*.
It renders three rows with real numbers and **no verdict at all**: three
runs is a trailing window of two, and `MIN_BASELINE_RUNS` is three.

Both readings of "no finding" are satisfied — nothing fires — but they
are not the same statement, and this repository's whole discipline is
that "we did not check" must not look like "we checked and found
nothing". Meeting the acceptance's arithmetic literally would have meant
either putting the judged run inside its own baseline population or
lowering the floor for this one caller, and both weaken the noise model
to fit a sentence. The command says which it is.

Four refs is what closes the gap, and the weekly schedule produces the
fourth on its own.

Tests: 9 new in `tests/unit/test_cache_trend.py`. Suite: 1283 → 1292.

## Verification Log

Done 2026-08-18. The three-row table, the two-run refusal and the CI
step are real runs against the three published fdsdk refs; the degraded
fourth run is those same captures with pull spans synthesized into a
copy, which is what the acceptance asks for.
