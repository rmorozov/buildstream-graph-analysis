# UX-872: a junctioned example builds under the mode in CI

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-869, UX-871, UX-856 | **Found by:** round 121, the user (a real project under a junction, GNU Make 4.4 on the host) | **Serves:** R4 (the snapshot entry point with the jobserver on runs in CI, on a junction) | **Topic:** capture | **Area:** tools | **Shape:** judgement

## Motivation

Every jobserver-on CI step runs `bga capture run` or the tracer
directly on a project with no junction; `bga snapshot --jobserver`
(`UX-856`) has never run in CI, and no example has a junction, so the
two defects the user hit on the first day (`UX-869`, `UX-871`) had no
step to fail on.

## Required Fix

`examples/12-junctioned/`: a small project whose elements come through
a local junction (a sub-project inside it holding one cmake element and
a stack), built by the `bst-examples` job with `bga snapshot
--jobserver auto -- bst build all.bst`, asserting the junctioned cmake
element's decision reads `joined` with a kind, not `unknown_kind`, and
the build exits 0; the README carries this box's reading, dated.

## Decomposition

Input classes: a junctioned cmake element, the junction element itself
(never joins), the stack on top; the journey it extends is the user's
`bga snapshot --jobserver auto` on a junctioned project.

## Out of Scope

A remote junction; a second example under fifo-style auth (CI's make
is 4.3 - name the class as CI-only in the README).

## Acceptance Test

`tests/unit/test_the_examples_build.py` gains the step's assertions
(the exit, the joined decision on the junctioned element); mutation:
point the assertion at an unjunctioned element - red. The live reading
from this box pasted in the Outcome.
