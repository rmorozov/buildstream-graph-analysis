# UX-1087: the bounded-memory measurement holds identifiers constant

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-1069 | **Found by:** the owner's #298 re-review at 156d7436, finding 4 | **Serves:** anyone sharing a large private capture | **Topic:** store | **Area:** bga | **Shape:** mechanical

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

**Gap measured** at `e5075375` with `/tmp/<track>/measure_axes.py`
(`ELEMENTS`/`N` monkeypatched onto the UX-1069 test module, small
chunks, one warm run to pay first-call caches), two axes:

```text
== records vary, ELEMENTS=8 fixed ==
ELEMENTS=8 N=1000: bytes=90477  peak=358764  (outcome=exported)
ELEMENTS=8 N=4000: bytes=362292 peak=388605  (outcome=exported)
== ELEMENTS vary, N=1000 fixed ==
ELEMENTS=8    N=1000: bytes=90477  peak=358075
ELEMENTS=800  N=1000: bytes=178009 peak=1369809
ELEMENTS=8000 N=1000: bytes=998409 peak=10811093
```

Records at fixed identifiers barely move the peak (+29841 B over 4x the
records); identifiers at fixed records do not: 1277.4 B/identifier from
8->800, 1311.3 B/identifier from 800->8000 - one record's transient
copy plus the distinct identifiers' `PseudonymMap._forward`, `originals`
and residue-index entries, confirming UX-1069's "~4 MB ceiling" held
only because its own guard kept identifiers fixed at 8.

**Close measured.** New
`tests/unit/test_the_bounded_memory_measurement_varies_identifiers.py`
adds two guards at unit-tier scale (4 KiB chunks, one warm run):
records N=1000/4000 at ELEMENTS=8 stays under the existing 0.25x-of-
bytes-gained bound; ELEMENTS 8/608 at N=100 must grow by over 100 KB
(so the guard is live) and by at most `PER_IDENTIFIER_BOUND=2600`
B/identifier, roughly double the 1311 B/identifier measured above.
`pytest tests/unit/test_the_bounded_memory_measurement_varies_identifiers.py
tests/unit/test_the_anonymized_export_runs_in_bounded_memory.py -q`:
`20 passed in 7.68s`. UX-1069's Outcome and the closed-row summary's
"~4 MB ceiling" wording is corrected to state the bound as one record
plus the distinct identifiers' map, originals and residue index (the
closed.md row is the orchestrator's).

**Mutation** (`bga/bundle.py`, `_Anonymizer.collect`'s `leaf()`
closure, restored from `/tmp/bundle.py.orig`, `PYTHONDONTWRITEBYTECODE=1`):
adding `self.pmap.originals.add(f"record:{pattern}:{value}")` per leaf,
a per-record copy into the originals set, grows it with every
`by_cpu` record regardless of distinct identifiers.

| mutation | reddened | count |
|---|---|---|
| per-record copy into `pmap.originals` in `collect()`'s leaf closure | `test_records_vary_at_fixed_identifiers_stays_flat` (grew 6358731 >= 0.25 x 271815) | 1 failed, 1 passed |

Reverted from the copy; `pytest .../test_the_bounded_memory_measurement_varies_identifiers.py -q`: `2 passed in ...s`.
