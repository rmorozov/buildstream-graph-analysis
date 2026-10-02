# UX-1265: the graph-width finding lost the total element count and "whatever the capacity" from its title

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-163 verification of UX-1248 (2026-10-02) | **Serves:** R1 | **Topic:** analysis | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

The graph-width finding lost the total element count and "whatever the capacity" from its title (UX-1248), and its detail carries only a step whose why_none the text report does not print.

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`.

## Required Fix

The detail carries the total and the capacity clause, and the text report prints it.

## Out of Scope

Other titles (UX-1248).

## Acceptance Test

The text report states the total and the capacity clause for graph-width. Mutation: drop the detail line, and the guard reds.
