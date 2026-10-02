# UX-1261: #binary_cost's answer sentence names `make` over a pair table whose first page does not show make

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-163 verification of UX-1247 (2026-10-02) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

The #binary_cost answer sentence names `make` over a pair table whose first page does not show make; the per-binary table is the separate #by_binary section.

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`.

## Required Fix

The sentence links to #by_binary, or the table's first page shows the binary the sentence names.

## Out of Scope

The by_binary table (UX-1247).

## Acceptance Test

On the 2,402-element page the binary the answer names is reachable from it in one click. Mutation: drop the link, and the guard reds.
