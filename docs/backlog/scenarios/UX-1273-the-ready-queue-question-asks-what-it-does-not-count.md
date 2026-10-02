# UX-1273: "How much work was waiting to start?" excludes work waiting for a builder, so a capacity-bound run reads 1% queued

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-164 view UI re-review on a 2,402-element two-plane page (2026-10-02), finding R4 | **Serves:** R1, R5 | **Topic:** viewer | **Area:** bga, bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 40 --width 60 --workload binaries` (2,402 elements), `bga capture report --json plane2.log --project-dir <d> > plane2.json` in the newest snapshot (39,854 processes, 601 binaries), served by `bga view @last` on main `319539f0`, Chromium 1440x900 and 390x844 (view UI review, round 164, `view-ui-review/round-164/review.md` §R4).

`#ready_queue` reads average depth 0.55x, peak 60, nonzero 1.0%, beside 43.7 min of resource wait. `ReadyQueueMetrics` counts tasks "dependency-ready, resource-ready, but not executing" (`bga/diagnostics/analyzer.py:51`), so a task waiting for a full builder is not in it. The heading asks the question a capacity operator would ask about exactly that backlog.

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`, at 1440 and 390.

## Decision

Route:     rename the question to what the metric counts ("How much ready work waited with a builder free?"), and rewrite ready_queue's description and the nonzero_fraction gloss: drop "had nowhere to run it" and "High means capacity bound"; say that work waiting for a full builder is not counted and point to resource wait.
Rejected:  publishing the dependency-ready backlog. It is cheap (`_estimate_ready_count` with resource_capacities=None already counts it), but it adds a schema field and a golden diff, and the owner named a rename as the alternative. This is the reversal to take if wanted.
Files:     bga/schemas.py (QUESTION at ~5394, ready_queue descriptions at ~3115-3130), bga/diagnostics/analyzer.py (ReadyQueueMetrics docstring line only, if the description is shared), tests/unit/test_the_ready_queue_asks_what_it_counts.py
Guard:     tests/unit/test_the_ready_queue_asks_what_it_counts.py: on the 2,402-element two-plane page at 1440 and 390, #ready_queue's heading and gloss name a free builder, and no ready_queue text reads "capacity bound" or "nowhere to run"
Mutation:  restore "How much work was waiting to start?" (or the "High means capacity bound" gloss): the guard reds
Class:     product
Split:     one track, with UX-1268 (whose acceptance reads this section)
Question:  Default taken; Ruslan may reverse: rename instead of publishing the dependency-ready backlog

## Required Fix

Either the heading names what is counted (ready with a free slot yet not dispatched), or the section also publishes the dependency-ready backlog waiting on a resource, which on a capacity-bound run is the number that matters.

## Out of Scope

The scheduler-wait attribution bucket.

## Acceptance Test

On this page the section's heading or answer no longer reads as the backlog behind full builders, or its backlog figure is nonzero for most of the 43.7 min. Mutation: restore the old heading, and the guard reds.
