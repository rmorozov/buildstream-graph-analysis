# UX-1273: "How much work was waiting to start?" excludes work waiting for a builder, so a capacity-bound run reads 1% queued

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-164 view UI re-review on a 2,402-element two-plane page (2026-10-02), finding R4 | **Serves:** R1, R5 | **Topic:** viewer | **Area:** bga, bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_the_ready_queue_asks_what_it_counts.py`

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

## Outcome

The gap measured, at `b35c30e31`, the 2,402-element two-plane page exported, Chromium 1440, `#ready_queue`
textContent: `How much work was waiting to start? ... Nonzero fraction 1.0% The share of the build spent with anything
waiting. High means capacity bound, not graph bound.`

The close measured, same page: `How much ready work waited with a builder free? ... Average depth 0.55x How many
elements were ready with a builder free, averaged over the build. ... Nonzero fraction 1.0% The share of the build
with ready work and a builder free. Work waiting for a full builder is not counted; read resource wait for it.`
The rename default taken; no schema field added. `docs/design/rendered-strings.json`'s two rows of the old heading
read the new one. Guard: 2 passed (25.8 s), at 1440 and 390.

| mutation | reddened | run printed |
|---|---|---|
| restore "How much work was waiting to start?" | `[1440]`, `[390]` | 2 failed |
| restore "High means capacity bound, not graph bound." | `[1440]`, `[390]` | 2 failed |
| reverted | | 2 passed |

Verifier fix: with no `resource_capacities`, `_estimate_ready_count`'s fast path counts every dependency-ready unstarted
task, so the builder-free heading was false there. `ready_queue` publishes `counts` (`builder_free` | `dependency_ready`,
from whether the run recorded capacities); the heading is `How much ready work had not started?` and the `Counts` row
reads `Ready with a builder free` on the 2,402-element page; its gloss: `With builder slots recorded, only work
with a builder free; a full builder's wait is resource wait. Without, every dependency-ready task.` golden with capacities
cleared (`dataclasses.replace(run_context, resource_capacities={})`) publishes `dependency_ready`. golden and
with_timeline regenerated (`dev_refresh_analysis.py --write`): `counts` and `document_shape.leaves` +1 only.
Guard: 3 passed (24.2 s).

| mutation | reddened | run printed |
|---|---|---|
| `counts` always `builder_free` | `test_the_payload_says_which_ready_work_it_counted` | 1 failed |
| heading restored to the builder-free question | `[1440]`, `[390]` | 2 failed, 1 passed |
| `counts` gloss drops the no-capacity sentence | `[1440]`, `[390]` | 2 failed, 1 passed |
| reverted | | 3 passed |
