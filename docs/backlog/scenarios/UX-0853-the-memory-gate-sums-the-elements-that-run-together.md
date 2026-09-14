# UX-853: the memory gate sums the elements that run together

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-850 | **Found by:** round 118, UX-850's verifier | **Serves:** R5 (two elements each under the bound do not jointly exceed the host) | **Topic:** capture | **Area:** tools | **Shape:** mechanical

## Motivation

`UX-850`'s gate reads `MemAvailable` once per tick and compares it
against one element's planned peak times the tokens it would hold. Two
running elements each pass on their own; together they exceed the host.
An element on its implicit token alone never reaches the gate, so N such
elements co-reside unchecked. The verifier named it.

## Required Fix

`tools/bst_native_build_tracer.py`: `Broker._memory_gate` reserves,
per tick, the sum over every running element of `peak_rss * (1 + tokens
held)` before granting; a grant is withheld when `MemAvailable` minus
that sum, minus the candidate's own increment, goes under zero; a
running element with no planned peak counts as the plan's median peak.
The `memory_withheld` row gains `reserved` (the sum). Nothing else in
the broker moves.

## Decomposition

Input classes: one running element, two whose peaks each fit and whose
sum does not, an element on its implicit token only, an unplanned
element at the median; the journey it extends is R5's "does this
machine fit this build" under the mode.

## Out of Scope

Reading memory from the hook per process (a live RSS rather than the
plan's peak) - a later row, `UX-682`'s shape.

## Acceptance Test

`tests/unit/test_the_pool_withholds_for_memory.py` gains a case with
two running elements each under the bound whose sum is over it: the
second grant is withheld and its row carries the sum; mutation: reserve
only the candidate's own peak - red.
