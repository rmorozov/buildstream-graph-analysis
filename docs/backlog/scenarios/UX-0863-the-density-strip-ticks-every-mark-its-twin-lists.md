# UX-863: the density strip ticks every mark its twin lists

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-195 | **Found by:** round 120, the user (a 16-core, 32 GB host, `--builders 16 --jobserver auto`) | **Serves:** R1 (the strip and the table under it say the same percentiles) | **Topic:** viewer | **Area:** bga-viewer | **Shape:** mechanical

## Motivation

The distribution shape publishes nine deciles, p95, p99, min, max
and mean, and the twin table lists all of them; `stripSvg`
(`bga/viewer/drawings.js`) draws a min-to-max bar with ticks at p50 and
p95 only, hardcoded, and the sentence under it names the same four. A
reader who opens the twin sees p10, p90 and p99 the strip never marked.

## Required Fix

`bga/viewer/drawings.js`: `stripSvg` ticks every mark the twin lists
(the deciles, p95, p99), the outer ones lighter, labels at p10, p50, p90
and p99; the sentence under the strip names the same set.

## Decomposition

Input classes: a flat distribution, one with p99 far from p95, n of
1; the journey it extends is R1 reading a distribution's spread.

## Out of Scope

A histogram; changing the published shape.

## Acceptance Test

`tests/unit/test_a_drawing_is_graded.py`: the strip's tick count
equals the twin's mark rows; mutation: keep p50 and p95 only - red.
