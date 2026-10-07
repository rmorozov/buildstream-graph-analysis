# UX-1342: the headline's "top 3" and the work order name two different triples

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** walk seed 5 (2026-10-07), finding 3 | **Serves:** R1 | **Topic:** analysis | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** none yet

## Motivation

On `tests/fixtures/macro_micro` at `3e3657a7`, `bga analyze` text: the
headline table's top 3 is core/lib-b/lib-d (12.1 + 4.0 + 4.0 s), the order
reads "core.bst (31.1 s) -> codegen.bst (24.1 s, pays off after the step
before) -> lib-b.bst", and one line below "codegen.bst (7.0 s) - ... worth
nothing to fix today". `bga whatif --element codegen.bst`: "43.200s ->
43.200s (saves 0.000s)". `UX-1135` made the joint figure honest (23.1 s,
matching `whatif` on core+codegen+lib-b); the two triples remain.

## Decomposition

Input classes: a run whose top savings are independent; one where a saving
pays only after another (codegen after core); one with fewer than three
elements worth fixing. Journey: `macro_micro`, example 06.

## Required Fix

Open: one triple across the headline and the order, or a sentence naming
why they differ (codegen pays only after core).

## Out of Scope

The joint-saving arithmetic (`UX-1135`).

## Acceptance Test

On `macro_micro`, every "top 3" the text names is the same three elements,
or the text says why not.
