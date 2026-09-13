# UX-827: the distribution twin draws five of sixteen published marks, and no mean

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-598 (the distributions published), UX-343 (their quantities) | **Found by:** round 115, the design review | **Serves:** R3 reading a graph's shape; the owner asking for deciles | **Topic:** analysis | **Area:** bga | **Shape:** judgement

## Motivation

`analyzer.distribution()` publishes `n, min, max, deciles p10..p90, p95,
p99, is_flat` — sixteen marks. The page's twin table draws five:

```text
scale export · blast_radius_distribution
  sentence   "0 → 1201, median 30, p95 575 — n=1202."
  twin       min 0 · median 30 · p95 575 · max 1201 · n 1202        (5 rows)
  payload    deciles p10 0, p20 1, p30 4, p40 10, p50 30, p60 66, p70 157, p80 …, p90 …, p95 575, p99 …
```

The deciles and p99 reach a reader only through the JSON door; a mean
is not published at all — the one figure a reader with a spreadsheet
asks for first, and the one a heavy tail makes least honest.

## Required Fix

`distribution()` adds `mean` (declared, with a sentence); the twin
table is one row per published mark in order — min, p10 … p90, p95,
p99, max, mean, n — and the sentence stays on median and p95 (§2f,
landed this round). A flat population keeps its one line.

## Decomposition

Input classes: a population with a shape (1,202), one too small
(`MIN_ELEMENTS_FOR_DISTRIBUTION`, "too few to have a shape"), and a flat
one (`is_flat`); the journey is R3's graph-shape question in the answer
key.

## Out of Scope

- A `std`/MAD — no reader has asked; refused until one does.
- The percentile *step* as a control — the deciles are the step; a 5% step is a second table and a second scale.

## Acceptance Test

On the scale export every `*_distribution` twin has 17 rows; `mean`
declared in `schemas.py`; mutation: drop a decile row — the §2f guard
reds.
