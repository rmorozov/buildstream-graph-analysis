# UX-1390: one capacity Note says `--max-jobs` is modelled and missing

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** walk seed 7 (2026-11-27) | **Serves:** R6 | **Topic:** analysis | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

[`walk-seed-7.md`](../../audits/walk-seed-7.md) finding 5: `bga analyze
tests/fixtures/macro_micro/run --format text` (its `plane2.json` beside it), line
91, one Note: "native build-system parallelism (--max-jobs) is modelled for this
capture from its own Plane 2 measurements" and "Capacity checks ... did not run
for this run — missing: the --max-jobs value", while line 116 reads "max-jobs 4".

## Decomposition

Input classes: Plane 2 report beside the run, absent; `--max-jobs` given, not given. Journey: extends the walk's seed 7 class.

## Required Fix

The Note names one source for `--max-jobs`: the capacity checks run on the
modelled value, or the Note says why a modelled value does not count.

## Out of Scope

The capacity checks' own thresholds.

## Acceptance Test

On the fixture above, the text report's Note does not both model and miss
`--max-jobs`; a mutation restoring the two clauses reddens it.
