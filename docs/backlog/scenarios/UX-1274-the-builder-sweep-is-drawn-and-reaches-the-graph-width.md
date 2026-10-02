# UX-1274: "the graph allows 8" is where the sweep stopped, and the page never shows what more builders would buy

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-164 view UI re-review on a 2,402-element two-plane page (2026-10-02), brainstorm B1 | **Serves:** R1, R5, R8 | **Topic:** analysis | **Area:** bga, bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 40 --width 60 --workload binaries` (2,402 elements), `bga capture report --json plane2.log --project-dir <d> > plane2.json` in the newest snapshot (39,854 processes, 601 binaries), served by `bga view @last` on main `319539f0`, Chromium 1440x900 and 390x844 (view UI review, round 164, `view-ui-review/round-164/review.md` §B1).

The capacity recommendation and `#agent_sizing` read "the graph allows 8", and the constraint row explains "the sweep's knee is at 8 builders, the top of the range swept". The range is builders x `_RECOMMENDATION_SWEEP_HEADROOM` (2), capped at 32 (`bga/correlate.py:1150`), so 8 is the sweep's edge, not a knee; `graph-width` says 60 can build at once. The sweep's points (builders to replay makespan) are computed but not published, so the capacity-bound decision can only say "measure with bga sweep" where it could say what 6, 8 or 16 builders replay to.

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

The sweep runs to the graph's widest stage (or the cap) and publishes its curve; the page draws it as a series under the capacity recommendation, a knee at the range's edge is said as "no knee within N", and the capacity-bound decision quotes the replayed wall at the knee with the replay's caveat.

## Out of Scope

UX-861's policy (UX-1259); trying configurations on a real host.

## Acceptance Test

On this page the sweep reaches at least 16 builders, its curve is drawn with one mark per point, no sentence calls the range's top a knee, and the decision names a replayed wall for a builder count above 4. Mutation: restore the 2x range, and the guard reds.
