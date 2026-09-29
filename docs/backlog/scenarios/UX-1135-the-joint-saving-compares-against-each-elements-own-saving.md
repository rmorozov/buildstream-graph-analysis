# UX-1135: the joint saving compares against each element's own saving, not the horizon's steps

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-74 | **Found by:** the 0.5.0 release walk, seed 4 (round 152, commit `74aa14f2`) | **Serves:** R1, R2 | **Topic:** analysis | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

On `tests/fixtures/macro_micro` the report says "Together, the top 3
are worth 23.1s (50% of the build) - exactly the sum of their
individual savings, so they are three separate pieces of work that do
not overlap", for core, codegen and lib-b. But
`bga whatif --element codegen.bst` reads `43.200s -> 43.200s (saves
0.000s)`: codegen is worth nothing alone, and only after core is fixed.

`sum_of_individual_us` (`bga/analyzer.py`, the `joint_saving` block)
sums the optimization horizon's *step* savings, each measured after the
steps above it are done. Those telescope, so `joint >= sum` holds by
construction and the sentence claims independence on every run.

## Decomposition

surfaces: `joint_saving` in `bga/analyzer.py`, its sentence in `bga/findings.py`, the golden snapshot
guards: an element worth 0 s alone and more after another is fixed makes the sentence say the set must be worked in order; a set of independent elements still reads as separate
gap: none - `compute_joint_saving(graph, durations, [uid])` already prices one element alone

## Required Fix

`sum_of_individual_us` sums each element's own saving priced alone.
The sentence says the savings add, overlap (joint below the sum), or
compound (joint above the sum: an element is worth more once another
is fixed, so work them in the listed order).

## Out of Scope

The horizon's ordering; the headline table's own set.

## Acceptance Test

`bga analyze tests/fixtures/macro_micro/run` no longer calls the top 3
"separate pieces of work"; it names the order, and its individual sum
matches `bga whatif` per element.

## Outcome

Not started.
