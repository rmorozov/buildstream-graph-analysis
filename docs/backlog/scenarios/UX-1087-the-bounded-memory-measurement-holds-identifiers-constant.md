# UX-1087: the bounded-memory measurement holds identifiers constant

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-1069 | **Found by:** the owner's #298 re-review at 156d7436, finding 4 | **Serves:** anyone sharing a large private capture | **Topic:** store | **Area:** bga | **Shape:** mechanical

## Motivation

`test_the_anonymized_export_runs_in_bounded_memory.py` uses
`ELEMENTS = 8` at both N and 4N, holding distinct identifiers
constant while only the record count scales. `PseudonymMap._forward`,
the originals set and the residue index all grow with *distinct*
identifiers, not with records, so the existing measurement cannot see
that growth; UX-1069's Outcome then states a fixed "~4 MB ceiling"
that does not hold once identifiers scale with the capture.

## Required Fix

Add a scale measurement that varies the number of distinct identifiers
alongside record count, and correct every place UX-1069's "~4 MB
ceiling" claim is published - `docs/backlog/scenarios/UX-1069-the-anonymized-export-runs-in-bounded-memory.md`'s
own Outcome and any doc that repeats it - to state the bound as one
record plus the number of distinct identifiers, not a fixed byte
figure.

## Out of Scope

Any change to the export or residue-scan mechanism itself (UX-1069 is
closed; UX-1085, UX-1086 cover its two open defects).

## Acceptance Test

`tests/unit/test_the_bounded_memory_measurement_varies_identifiers.py`:
a run holding identifiers constant across N/4N and a run scaling
identifiers with N/4N are both measured (tracemalloc), and the second
shows peak growth the first does not; the docs/task-file grep for
"~4 MB" (or the fixed-ceiling wording) finds none outside history.
Mutation: revert the identifier-scaling run to constant identifiers,
and the growth this test exists to show disappears.

## Outcome
