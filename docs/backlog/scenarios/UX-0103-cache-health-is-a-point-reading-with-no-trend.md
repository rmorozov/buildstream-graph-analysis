# UX-103: cache health is a point reading with no trend

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-92 (per-run accounting), UX-96 (the baseline/refs fetch helper), UX-93 (honest churn labels first)

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
