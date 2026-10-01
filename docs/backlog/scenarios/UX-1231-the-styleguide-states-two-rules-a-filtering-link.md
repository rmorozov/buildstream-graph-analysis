# UX-1231: the styleguide states two rules: a filtering link moves focus to its filter, an entry naming no View is at the opening View

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-160 residue pass, track W3 (2026-10-01) | **Serves:** R1 | **Topic:** docs | **Area:** unassigned | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Track W3 (`UX-1214` follow-up 2) found two candidate rules: "a link that filters a table moves focus to its filter" and "an entry naming no View is at the opening View" (popstate sets the View as it clears a filter; the real defect was Forward).

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

The styleguide states both rules, each naming the guard that holds it.

## Out of Scope

The behaviour (`UX-1214`, closed).

## Acceptance Test

`test_the_styleguide_names_its_guards.py` passes with both rules stated and each guard named; deleting a rule's guard reds it. Mutation: restore the defect, and the guard reds.

## Outcome

Open.
