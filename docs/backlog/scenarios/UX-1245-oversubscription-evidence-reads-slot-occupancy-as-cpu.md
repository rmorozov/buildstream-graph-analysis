# UX-1245: utilisation calls full builder slots "High CPU use", and its peak concurrency is always 1

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-162 view UI review on a 2,402-element two-plane page (2026-10-01), finding H2 | **Serves:** R5 | **Topic:** analysis | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 40 --width 60 --workload binaries` (2,402 elements), `bga capture report --json plane2.log --project-dir <d> > plane2.json` in the newest snapshot (39,854 processes, 601 binaries), served by `bga view @last` on main `050d9035`, Chromium 1440x900 and 390x844 (view UI review, round 162, `view-ui-review/round-162/review.md` §H2).

`#utilisation` reads "Potential oversubscription: yes", "Oversubscription evidence: High CPU use", "Peak tasks at once: 1". In the same chapter `#occupancy` reads "Peak tasks at once: 4", `#capacity_verdict` "Capacity matched demand: neither over- nor undersubscribed", and Plane 2 measured 0.86 cores busy of 4.

Both are instruments reading a proxy (fixing guide §5):

- `HIGH_CPU_UTILIZATION` fires on useful *slot*-time over capacity at 95% (`bga/utilisation/__init__.py:552`) - builder occupancy, not CPU.
- `max_observed_concurrency` reads `len(interval['concurrent_tasks'])`, which `bga/analyzer.py:2164` always builds as a one-item list, so it is 1 on every run and evidence 2 can never fire.

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

The oversubscription evidence reads CPU where Plane 2 measured it (cores busy against effective CPUs) and says slot occupancy where it did not; peak concurrency is computed from overlapping task intervals, or the field is removed and its label with it.

## Out of Scope

The occupancy section; the capacity recommendation's wording (`UX-1246`).

## Acceptance Test

On this page oversubscription reads no (0.86 of 4 cores) and peak tasks at once 4 in both sections; a two-task overlap fixture reads 2. Mutation: restore the one-item list, and the overlap guard reds.
