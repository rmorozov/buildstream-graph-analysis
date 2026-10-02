# UX-1274: "the graph allows 8" is where the sweep stopped, and the page never shows what more builders would buy

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-164 view UI re-review on a 2,402-element two-plane page (2026-10-02), brainstorm B1 | **Serves:** R1, R5, R8 | **Topic:** analysis | **Area:** bga, bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_the_builder_sweep_is_drawn.py` (the 2,402-element two-plane page, built by `pages.two_plane_run`; Chromium 1440x900 and 390x844; node probe of `sizingCard`)

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 40 --width 60 --workload binaries` (2,402 elements), `bga capture report --json plane2.log --project-dir <d> > plane2.json` in the newest snapshot (39,854 processes, 601 binaries), served by `bga view @last` on main `319539f0`, Chromium 1440x900 and 390x844 (view UI review, round 164, `view-ui-review/round-164/review.md` §B1).

The capacity recommendation and `#agent_sizing` read "the graph allows 8", and the constraint row explains "the sweep's knee is at 8 builders, the top of the range swept". The range is builders x `_RECOMMENDATION_SWEEP_HEADROOM` (2), capped at 32 (`bga/correlate.py:1150`), so 8 is the sweep's edge, not a knee; `graph-width` says 60 can build at once. The sweep's points (builders to replay makespan) are computed but not published, so the capacity-bound decision can only say "measure with bga sweep" where it could say what 6, 8 or 16 builders replay to.

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`, at 1440 and 390.

## Decision

Route:     the sweep top becomes min(max(builders x 2, host_cores x 2, graph width), 32); publish capacity_recommendation.sweep [{builders, replayed_wall_us}] under the existing `bga:series` hint (no new JS drawing); at the range's top the reason and the sizing card read "no knee within N"; _capacity_step appends "the replay puts K builders at W (replayed, no contention)" in every binding branch, the host_cores cap kept as it stands.
Rejected:  sweeping to the graph's full width of 60 past the 32 cap (more replays than the acceptance's 16 needs; analyze wall time is unmeasured); a new drawings.js primitive (bga:series already draws ≥3 points); changing the recommended number (UX-1259's policy)
Files:     bga/cli.py (~442 range), bga/correlate.py (reason, curve), bga/sweep_curve.py (new: curve rows, knee-or-edge wording), bga/findings.py (_capacity_step), bga/schemas.py (sweep + SERIES, graph_ceiling description), bga/viewer/sections.js (sizingCard builders row), tests/unit/test_capacity_recommendation.py, tests/unit/test_the_builder_sweep_is_drawn.py
Guard:     tests/unit/test_the_builder_sweep_is_drawn.py: on the 2,402-element two-plane page the sweep reaches ≥16, the curve has one mark per point, no text calls the range's top a knee, and the decision names a replayed wall for >4 builders
Mutation:  restore `max(builders, host_cores) * _RECOMMENDATION_SWEEP_HEADROOM` as the top: the guard reds
Class:     product
Split:     one track; UX-1276 follows it (it prices the replayed-wall delta this publishes); UX-1272 shares sizingCard and compute_agent_sizing, so put it in this track
Question:  Default taken; Ruslan may reverse: the sweep stops at the existing 32 cap rather than the graph width of 60; analyze's added replay time is measured in the Outcome

## Required Fix

The sweep runs to the graph's widest stage (or the cap) and publishes its curve; the page draws it as a series under the capacity recommendation, a knee at the range's edge is said as "no knee within N", and the capacity-bound decision quotes the replayed wall at the knee with the replay's caveat.

## Out of Scope

UX-861's policy (UX-1259); trying configurations on a real host.

## Acceptance Test

On this page the sweep reaches at least 16 builders, its curve is drawn with one mark per point, no sentence calls the range's top a knee, and the decision names a replayed wall for a builder count above 4. Mutation: restore the 2x range, and the guard reds.

## Outcome

Gap measured (base `b35c30e31`; the Motivation's page rebuilt: `gen-synthetic --store --seed 1 --layers 40 --width 60
--workload binaries`, `capture report --json` on the newest snapshot, `analyze <run> --plane2 plane2.json --format json`):

```text
                         before                                      after
sweep range              1..8 (max(4 builders, 4 cores) x 2)         1..32 (min(max(8, 8, widest stage 60), 32))
graph constraint         allows 8, "the sweep's knee is at 8          allows 30, "the sweep's knee is at 30 builders"
                         builders, the top of the range swept"
capacity_recommendation  no curve                                    sweep: 32 replayed walls, 187.9 min at 1 .. 6.2 min at 32
decision's first step    "Measure builders above the host's          "...with bga sweep; the replay puts 30 builders at
                         4-core cap with bga sweep"                  6.4 min (replayed, no contention)"
macro_micro              graph allows 2, swept 1..8                  unchanged: allows 2, sweep 8 points, decision row 1 is core.bst
```

Close measured: analyze's added replay time on that page, `time_sweep.py` (one subprocess per run, old range patched in,
3 alternating reps):

```text
old 3.83 4.00 4.99 median 4.00s
new 5.32 4.65 4.92 median 4.92s
added 0.92s
```

`test_the_builder_sweep_is_drawn.py`: 8 passed in 31.4s (the page built once per module, one browser for both widths).

| Mutation | Reddened | Count |
|---|---|---|
| `sweep_top` back to `min(max(builders, host_cores) * 2, 32)` | `test_the_sweep_reaches_past_the_host_to_sixteen` | 1 failed, 7 passed |
| `knee_reason`'s edge branch off (`if False:`) + card's `"the graph allows #"` unconditional | `test_a_knee_at_the_range_top_is_no_knee`, `test_the_sizing_card_says_no_knee_at_the_top[8]` | 2 failed, 2 passed |
| `_capacity_step`'s replayed tail dropped | decision step (payload), the curve test at 1440 and 390 (step text), the unit step test | 4 failed, 4 passed |
