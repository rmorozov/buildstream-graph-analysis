# UX-1283: the pool's seed tokens are handed out before the memory gate has a say

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-1134 | **Found by:** Ruslan's promotion question on round 166 (2026-10-02): what stands between `auto` and arbitrary configurations | **Serves:** R4, R5 | **Topic:** capture | **Area:** tools | **Shape:** judgement | **Reading:** owner:CodSpeed Graviton

**Guard:** none — open, no guard named yet

## Motivation

`bga capture run --jobserver auto --builders B` seeds the pool at
`min(cores - 1, cores - B)` (`bga/cli.py` `_translate_capture_jobserver`).
The tracer writes those tokens into the FIFO at start, and UX-1134's
gate only governs a `+` added after that. On memgiant at 8 builders
the seed is 8, so the giant opened at 9 jobs against `off`'s 8
(run 37031346135: `giant-peak 10`, 26.9 GB of 31 GB). The seed is
sized by cores alone. Two memory-heavy elements starting together
each draw from it unchecked; `pairs`/`cap3` pass no `--builders`, so
their seed is 15 on 16 cores. Unmeasured; inferred from the code.

## Decomposition

Input classes: one memory-heavy element at seed 8; two at once;
`--builders` absent (seed `cores - 1`); a host whose memory fits the
seed. Journey: the `auto` capture's first minute.

## Required Fix

The seed is the gate's first decision rather than a given: with no
plan, the pool opens at what the gate admits from `MemAvailable` and
the build's first measured jobs, or at bst's own max-jobs when it has
no reading yet, and widens from there.

## Out of Scope

Revoking tokens already handed out; the cgroup reading (UX-1282).

## Acceptance Test

A Graviton leg with two memory-bound giants built at once completes
under `auto` where today's seed would take both past memory; the
single memgiant and the win shapes keep their readings within noise.

## Outcome
