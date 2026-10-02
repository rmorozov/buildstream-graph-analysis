# UX-1276: every saving is in build seconds, and the lead asks what it is worth to the team

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-164 view UI re-review on a 2,402-element two-plane page (2026-10-02), brainstorm B3 | **Serves:** R8, R5 | **Topic:** viewer | **Area:** bga, bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 40 --width 60 --workload binaries` (2,402 elements), `bga capture report --json plane2.log --project-dir <d> > plane2.json` in the newest snapshot (39,854 processes, 601 binaries), served by `bga view @last` on main `319539f0`, Chromium 1440x900 and 390x844 (view UI review, round 164, `view-ui-review/round-164/review.md` §B3).

The decision, horizon and what-if price fixes in seconds of one build (certified headroom 9.9 s, scheduling gap 42.5 min). `roles.md` scores R8 Partial for exactly this: "nothing ... converts to anything a budget speaks". The store knows how many snapshots it holds and when they were taken; the owner's own build rate is several hundred review builds a day. Neither reaches the page.

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

With a build rate (from the store's snapshot timestamps, or declared), the page converts a saving and a capacity change into agent-hours per day beside the seconds, says where the rate came from, and omits the line when there is none.

## Out of Scope

Money; cross-project aggregation.

## Acceptance Test

On a store with a declared rate the decision's saving shows agent-hours per day equal to seconds x rate / 3600 and names its source; with no rate the line is absent. Mutation: drop the rate source, and the guard reds.
