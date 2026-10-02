# UX-1277: findings do not say whether they are new, still open or gone since the run before

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-164 view UI re-review on a 2,402-element two-plane page (2026-10-02), brainstorm B4 | **Serves:** R4, R8, R1 | **Topic:** analysis | **Area:** bga, bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 40 --width 60 --workload binaries` (2,402 elements), `bga capture report --json plane2.log --project-dir <d> > plane2.json` in the newest snapshot (39,854 processes, 601 binaries), served by `bga view @last` on main `319539f0`, Chromium 1440x900 and 390x844 (view UI review, round 164, `view-ui-review/round-164/review.md` §B4).

The compare chapter now leads with "-0.1% (2.5 s faster) than the run before, inside the noise band", and the store holds two snapshots, yet each of the 15 findings reads as if seen for the first time. For a continuous improvement process the useful split is new since the baseline, still open, and gone (the last is invisible today because a fixed finding is simply absent). `bga/compare.py` compares durations and verdicts, not findings.

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

`bga compare` publishes the findings diff by finding id and subject (new, persisting with its age in snapshots, resolved); the page marks each finding's status and lists resolved ones in one line under the findings.

## Out of Scope

Cross-host comparison (the comparison class rule); the noise band.

## Acceptance Test

On a store where @prev has a finding @last lacks and the reverse, the page marks one new, lists one resolved, and marks the shared ones persisting. Mutation: drop the resolved list, and the guard reds.
