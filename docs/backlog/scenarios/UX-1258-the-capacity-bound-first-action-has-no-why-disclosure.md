# UX-1258: the capacity-bound first action row has no numbered "Why #1" disclosure

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-163 verification of UX-1244 (2026-10-02) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

The capacity-bound first action row has no element, so it has no numbered "Why #1" disclosure; rows 2-3 build theirs from element facts. Its "why" links to `#finding-capacity-recommendation` and nothing opens in place.

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`.

## Required Fix

The step row opens a disclosure like rows 2-3, built from the finding's own facts rather than element facts.

## Out of Scope

The blast rows' disclosures; the step text (UX-1244).

## Acceptance Test

On the 2,402-element two-plane page the first action row opens a "Why #1" disclosure. Mutation: build none for an element-less row, and the guard reds.
