# UX-1273: "How much work was waiting to start?" excludes work waiting for a builder, so a capacity-bound run reads 1% queued

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-164 view UI re-review on a 2,402-element two-plane page (2026-10-02), finding R4 | **Serves:** R1, R5 | **Topic:** viewer | **Area:** bga, bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 40 --width 60 --workload binaries` (2,402 elements), `bga capture report --json plane2.log --project-dir <d> > plane2.json` in the newest snapshot (39,854 processes, 601 binaries), served by `bga view @last` on main `319539f0`, Chromium 1440x900 and 390x844 (view UI review, round 164, `view-ui-review/round-164/review.md` §R4).

`#ready_queue` reads average depth 0.55x, peak 60, nonzero 1.0%, beside 43.7 min of resource wait. `ReadyQueueMetrics` counts tasks "dependency-ready, resource-ready, but not executing" (`bga/diagnostics/analyzer.py:51`), so a task waiting for a full builder is not in it. The heading asks the question a capacity operator would ask about exactly that backlog.

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

Either the heading names what is counted (ready with a free slot yet not dispatched), or the section also publishes the dependency-ready backlog waiting on a resource, which on a capacity-bound run is the number that matters.

## Out of Scope

The scheduler-wait attribution bucket.

## Acceptance Test

On this page the section's heading or answer no longer reads as the backlog behind full builders, or its backlog figure is nonzero for most of the 43.7 min. Mutation: restore the old heading, and the guard reds.
