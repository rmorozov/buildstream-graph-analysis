# UX-904: nothing prices N separate CI builds against one junctioned invocation

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-903 (the variants that make N), P4-15 / `bst_checkout_cost.py` (the precedent) | **Found by:** the 2026-09-20 rollout thread — the owner names this as one of the questions bga should answer: do the variants need separate CI builds, or are they worth embedding in one BuildStream invocation through junctions | **Serves:** R5 (the fleet that runs N of them), R3 (whose graph the junction changes), R4 and R6 (the latency of a verdict) | **Topic:** analysis | **Area:** bga | **Shape:** judgement

## Motivation

A pipeline that builds four variants runs four BuildStream invocations,
each paying the pipeline's own cost — loading elements, resolving them,
querying the cache — before any element builds, and each scheduling its
graph alone on its agent. One junctioned invocation pays that once and
schedules every variant's elements together, which is more parallelism
to find and a larger cache-hit surface, against a longer critical path
and a blast radius that now spans variants.

The tool has both halves of this arithmetic already and joins neither:
`pipeline_overhead` is a published per-invocation cost
(`bga/analyzer.py`, `analyze/v6`), `tools/bst_checkout_cost.py` is the
existing precedent for exactly this shape of question — N separate
invocations against one grouping element, measured rather than
speculated — and `examples/12-junctioned` is a committed project with a
real junction in it. What is missing is the answer, and the owner asks
for it directly.

## Required Fix

Price the two arrangements from captures the pipeline already produces:
given N runs of the same tree under different variants, what one
junctioned invocation would cost, and what it would win. The honest
shape is a projection with its assumptions stated, the way
`bga whatif` already is:

| term | where it comes from |
|---|---|
| pipeline cost paid N times | `pipeline_overhead`, per run |
| the union graph's floor | the N graphs joined at their shared elements, T∞ over the union |
| what is actually shared | elements identical across variants — the cache already knows |
| what the junction costs | staging the subproject, measured on `examples/12-junctioned` |

And the refusal that keeps it honest: where the N runs are not
comparable (`UX-898`, `UX-903`), say so rather than joining them.

A re-capture is still the ground truth, and the finding says so.

## Decomposition

surfaces: a new analysis module beside `bga/whatif.py`, the CLI entry point, `analyze/v6`'s projection namespace or a document of its own, and `examples/12-junctioned` as the fixture with a real junction
guards: two variant runs sharing most elements (a projected saving), two sharing nothing (no saving, and it says so), runs of different types (refused), and a single run (nothing to compare)
gap: whether "the same element in two variants" is decidable from cache keys alone — different variants may key differently for the same source, which is the whole question and needs a real pair to settle
track: session's own — the arithmetic is a modelling decision, not a mechanical one
gate: after `UX-903`, whose class makes "the same tree, different variant" nameable

## Out of Scope

Restructuring anyone's pipeline; the row publishes the number, not the
migration. Junction semantics themselves, which BuildStream owns.

## Acceptance Test

On two synthetic runs of one tree under two variants with a known
overlap, the projection names the shared element set, the pipeline cost
saved, the union floor, and a bound on what one invocation would cost —
each figure carrying its assumption. On two runs with no overlap it
reports no saving. On runs of different declared types it refuses.
Mutations: double the pipeline overhead (the saving grows by exactly
that), remove an element from the overlap (the shared set and the saving
both fall), make the two runs different types (refused rather than
joined).

## Outcome
