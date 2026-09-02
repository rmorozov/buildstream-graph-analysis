# UX-535: one fact published twice, drawn twice, listed twice

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-288 (the one-population rule), UX-285 (the grouping that moved without merging) | **Serves:** anyone reading the run's identity, or the rail | **Topic:** viewer

## Motivation

The duplication census over the cold export (35 tables, 338 distinct
text blocks, 12.8 % repeated characters — under §5a's 21 %) found
the repeats that are not citations:

```text
run_instance.producer == producer         True   (analyzer.py:160-162, schemas.py:2494)
rail "Producer"                            2 entries, 2 hrefs
rail "Latent heavies"                      2 entries — a section, and an `elements` preset
graph_summary vs graph_metrics             3 facts, the same sentence, both sections
```

`UX-390` is verified closed (`attribution_hints` has no section).
These three are the remainder: a payload key published under two
paths, and a rail that lists a section and a preset under one label.

## Required Fix

`producer` is published once (`run_instance.producer` stays, the
top-level copy goes — a removal, so the analyze contract bumps under
`UX-190`); `graph_summary`'s three shared facts render in one of the
two sections; rail labels are unique — a preset entry says "preset"
or carries the count.

## Out of Scope

- Selections drawn both as a section and as an `elements` preset —
  `UX-289`/`UX-338`'s design; only the rail label collides.

## Acceptance Test

Payload-level duplicate scan (the census's method) finds zero exact
duplicates; rail labels unique. Mutation: republish `producer` —
the contract guard reds.
