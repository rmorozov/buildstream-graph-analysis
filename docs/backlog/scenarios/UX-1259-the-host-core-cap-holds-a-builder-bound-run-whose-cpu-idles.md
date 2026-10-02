# UX-1259: UX-861's host-core cap keeps a builder-bound run at 4 builders while the CPU could feed 18

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** Ruslan's decision | **Found by:** the round-163 verification of UX-1244/UX-1246 (2026-10-02) | **Serves:** R1, R5 | **Topic:** analysis | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

UX-861's host-core cap keeps a builder-bound run at 4 builders while Plane 2 measures 0.86 of 4 cores busy and the CPU could feed 18 (the 2,402-element page). The page now says "measure above the cap with bga sweep" (UX-1244, UX-1246); whether the cap should yield to a measured CPU reading is the owner's call.

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`.

## Required Fix

The owner decides whether the cap yields to a measured CPU reading; the row then states the rule and its guard.

## Out of Scope

Reading the cap differently before the owner decides.

## Acceptance Test

The owner's call is recorded in the row; on the 2,402-element page the recommendation follows it. Mutation: restore the cap, and the guard reds.
