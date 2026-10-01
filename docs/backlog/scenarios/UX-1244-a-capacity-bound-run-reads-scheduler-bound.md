# UX-1244: a run whose resource floor is its wall reads "scheduler-bound" and is sent to the blast ranking

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-162 view UI review on a 2,402-element two-plane page (2026-10-01), finding H1 | **Serves:** R1, R5, R8 | **Topic:** analysis | **Area:** bga, bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 40 --width 60 --workload binaries` (2,402 elements), `bga capture report --json plane2.log --project-dir <d> > plane2.json` in the newest snapshot (39,854 processes, 601 binaries), served by `bga view @last` on main `050d9035`, Chromium 1440x900 and 390x844 (view UI review, round 162, `view-ui-review/round-162/review.md` §H1).

`diagnose()` has two arms, chain-bound or scheduler-bound, on `T∞ / time tasks ran` alone (`bga/findings.py:2264`). On this page the chain is 9.8%, so the decision reads "scheduler-bound ... the time is going somewhere other than the chain" with "Scheduling gap 42.5 min", and its three top actions are the blast-radius ranking. The same page says the opposite five times:

```text
#floors      Resource floor LB 47.0 min of 47.2 min wall; Certified headroom 9.9 s
finding      Efficiency score 99.7% - near the certified floor, not the scheduler
#attribution Resource wait 43.7 min - "try --capacity N with a higher N, or bga sweep"
#occupancy   Builders 3.99x of 4
#cpu_time    40.4 min CPU over 47.2 min wall = 0.86 cores of 4
```

The build is bound by its 4 builder slots while the cores idle at 21%. The reader is told to look at the graph, and the one step the run supports - more builders, measured - appears only in the attribution hint.

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`, at 1440 and 390.

## Decision

Architect, round 163 (2026-10-01):

```text
Route:     diagnose() keeps the chain check first; below CHAIN_BOUND_RATIO a third arm `capacity_bound` when floors.lb / wall >= CAPACITY_BOUND_SHARE (0.95) and lb > t_infinity_observed. Sentence names builders and the step; _top_actions puts the capacity-recommendation finding (else the `bga sweep` next step) before the blast ranking. Step comes from the hint source / finding step, not evidence.hint (retired by UX-1256).
Rejected:  task horizon as denominator (ticket and #floors read the wall); Plane 2 cores_busy as the decider (Plane 1-only runs lose the arm); dropping `lb > t∞` (with_timeline lb/wall 0.936 with lb = t∞ is chain-bound).
Files:     bga/findings.py (constant, DIAGNOSES, DIAGNOSIS_SENTENCES, diagnose, _top_actions); bga/provenance.py (_diagnosis_rule); bga/viewer/format.js (READER_LABELS capacity_bound); tests/unit/test_the_diagnosis_follows_the_shape.py.
Guard:     test_the_diagnosis_follows_the_shape.py: constructed result with the page's numbers (t∞ 9.8% of horizon, lb 47.0 of 47.2 min) reads capacity_bound, names builders, first action a builders step; golden and macro_micro stay chain_bound.
Mutation:  delete the capacity arm.
Class:     product
Split:     Track A after UX-1253 (reads its constant).
```

## Required Fix

`diagnose()` gains a third arm, capacity-bound, when the resource floor is within the noise of the wall (LB / wall at or above a named line); its sentence names the binding resource and the step the run supports (the sweep's knee, or the attribution hint), and its top actions come from that step rather than the blast ranking.

## Out of Scope

The capacity policy that caps builders at host cores (`UX-861`); the other findings of the review.

## Acceptance Test

On this page the decision reads capacity-bound, names builders, and its first action is a builders step; golden and macro_micro keep their current diagnosis. Mutation: drop the third arm, and the guard reds on this page only.
