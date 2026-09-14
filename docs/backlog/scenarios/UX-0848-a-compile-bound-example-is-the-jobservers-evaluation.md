# UX-848: a compile-bound example is the jobserver's evaluation

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-843, UX-846 | **Found by:** round 117, Direction 20 | **Serves:** R4 (the number round 112 asked for) | **Topic:** capture | **Area:** tools | **Shape:** judgement

## Motivation

Round 112 declined the mode because examples/06's wall did not move
(30.25 s → 30.46 s) while its under-utilised share fell fourfold: that
project's bound is a six-deep chain, and no jobserver shortens a chain.
The mode is supported when a compile-bound capture's wall moves, and
no example in the tree is compile-bound.

## Required Fix

`examples/07-jobserver/`: four independent autotools and cmake
elements, each compiling 64 generated C files and linking one binary,
behind one `all.bst`, small enough for CI's examples job; the job
captures it twice (static `max-jobs`, then `--jobserver auto`) and
`bga compare` prints the envelope and the wall side by side; the
README of the example carries the two numbers from the machine that
wrote it, dated. The mode's `Status` in Direction 20 is decided on
that row.

## Decomposition

Input classes: cold cache both ways (the artifact keys equal per
`UX-844`, so the second capture must be run with the cache cleared);
the journey it extends is R4's first capture with the mode on.

## Out of Scope

A project with a real link-bound tail - `UX-846`'s fixture; remote
execution (`UX-680`).

## Acceptance Test

`bst-examples` in CI builds 07 both ways and `tests/unit/test_the_examples_build.py`
(or the job's own step) asserts `bga compare` prints a wall for each;
mutation: point the second capture at the first's run - the compare
refuses two identical runs (red).
