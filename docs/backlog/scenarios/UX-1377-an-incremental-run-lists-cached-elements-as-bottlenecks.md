# UX-1377: an incremental run lists cached elements as bottlenecks

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** walk seed 6 (2026-11-03) | **Serves:** R3, R1 | **Topic:** analysis | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

[`walk-seed-6.md`](../../audits/walk-seed-6.md) finding 5: on
`tests/fixtures/same_build_twice_incremental` (1 rebuilt, 3 cached) the text
report reads "Bottlenecks Identified: 4 - lib0.bst, lib1.bst, lib2.bst,
lib3.bst", while `bga whatif inc --element lib0.bst` answers "Refused: No
measured duration: lib0.bst". The graph owner is pointed at three elements
this run never built.

## Decomposition

Input classes: cold, incremental with some cached, incremental with all
cached (population 0). Journey: extends the walk's seed 6 class.

## Required Fix

A bottleneck is an element this run measured; cached ones are counted
apart ("3 cached, not priced") or left out.

## Out of Scope

Pricing a cached element from an older run.

## Acceptance Test

The incremental fixture's report names lib3.bst alone as a bottleneck; the
mutation that drops the measured-duration filter reddens the guard.

## Outcome
