# UX-571: the ingestion facts were confirmed on a BuildStream this machine no longer has

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-88 (the last correction to this document) | **Serves:** whoever meets a `bst` output line the parser does not | **Topic:** docs

## Motivation

`docs/spec/ingestion-pipeline.md` is a 2026-08-14 log of "empirically
confirmed facts against real `bst` 2.7.0" — thirteen mentions of
that version. This machine runs 2.8.0 (`bst --version`), the
extract guard gates on `which bst` and passed here, and no document
records that the facts were exercised on 2.8.0 at all. Two facts are
also wrong on their own terms:

```text
F9   "%{kind} … not read by any analysis consumer yet"
     grep -rl element_kind bga/ → analyzer.py blast.py findings.py floors/cold.py cache_effectiveness.py sources.py
F11  "Query cache … currently dropped entirely"
     the document's own §546: "P4-14 is done … Pipeline Overhead block"; test_pipeline_overhead.py exists
```

Eighteen test files cite this document as provenance; none reads it.

## Required Fix

The version the facts were last exercised against comes from the
guard, not the prose: `test_bst_extract_run.py` prints the `bst`
version it ran under and the document's header cites "last exercised
on" that output, dated. F9 and F11 corrected in place, the way `UX-88`
corrected F5 (the old sentence kept, one line naming what changed).

## Out of Scope

- Re-deriving every fact on 2.8.0 by hand — the extract guards are
  the derivation; the item records which version they ran under.

## Acceptance Test

The header carries the version and date the guard printed; mutation:
restore "not read by any analysis consumer" — a grep-backed clause
(the six consumers, derived) reds.
