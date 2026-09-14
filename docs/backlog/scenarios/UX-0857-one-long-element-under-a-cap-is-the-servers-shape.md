# UX-857: one long element under a cap is the server's shape

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-848, UX-856 | **Found by:** round 119, the user | **Serves:** R4 (an llvm-sized element alone on the critical path takes the whole machine) | **Topic:** capture | **Area:** examples | **Shape:** judgement

## Motivation

BuildStream caps an element's `max-jobs` at 8 by default. On a 40-core
server an element the size of llvm, alone on the critical path while
half the graph waits on it, builds at `-j8` with 32 cores idle; under
the mode it takes every token the pool has. `examples/10` cannot show it
- four elements at `-j4` on four cores are saturated at `off`, and the
mode read slower at every stage - but a four-core box models the server
faithfully: one long element under a `max-jobs` below the core count.

## Required Fix

`examples/11-serial-giant/`: one cmake element compiling 256 generated
C files into one binary (the giant), three small elements that depend
on it, `max-jobs: 2` in `project.conf` (the server's 8 of 40, scaled),
`all.bst` on top; the `bst-examples` job captures it twice from a cold
cache (`bga snapshot --jobserver off`, then `--jobserver auto`, the
switch from `UX-856`) and `bga compare` prints both walls; the README
carries this box's two numbers, dated, with the expected ratio (the
giant at 2 jobs against 4 tokens) beside the measured one.

## Out of Scope

A real llvm build; a machine with more cores than this box.

## Acceptance Test

`tests/unit/test_the_examples_build.py` gains the CI step's assertion
for 11 (a wall for each run, `auto` under `off`); mutation: point the
second capture at the first's snapshot - the compare refuses (red). The
two walls from this box pasted in the Outcome.
