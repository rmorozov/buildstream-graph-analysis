# UX-1264: no fixture has resource_wait as its biggest wait category, so wait-category's step is unexercised

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-163 verification of UX-1256 (2026-10-02) | **Serves:** R1 | **Topic:** guards | **Area:** tests | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

No fixture has resource_wait as its biggest wait category, so wait-category's step equalling the resource-wait hint (`bga sweep`) is unexercised.

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`.

## Required Fix

A fixture whose biggest wait category is resource_wait; the guard reads the step equal to the hint.

## Out of Scope

The step text (UX-1256).

## Acceptance Test

Mutation: change the wait-category step for resource_wait, and the guard reds.
