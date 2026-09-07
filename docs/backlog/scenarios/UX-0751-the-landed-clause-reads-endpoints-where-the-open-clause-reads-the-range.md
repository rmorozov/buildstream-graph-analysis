# UX-751: the landed clause reads endpoints where the open clause reads the range

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-748 (the open clause), UX-231 (the directions guard) | **Serves:** the reader trusting a Direction's status line | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

## Motivation

`UX-748` gave `test_a_range_called_open_names_no_closed_filing` a
range-expanding helper, `_ids_in()`, so a status calling `A..B` open
reddens when any id inside it has closed. Its sibling,
`test_a_landed_status_names_only_closed_filings`, still reads the two
literal endpoints via `_ITEM` — the narrowness `UX-748` exists to
remove, left in place on the other half of the pair.

It is not hypothetical. Direction 18 read:

```text
**Status:** landed — `UX-685`..`UX-692` all closed.
```

while `UX-689` and `UX-690` were 🔴 Not Started, and the guard passed
because `685` and `692` are both closed. `UX-748`'s verifier confirmed
the mechanism by swapping `_ids_in()` into that clause:

```console
UX-689 is not closed
UX-690 is not closed
```

`UX-748` corrected the sentence — the status now names the six that
landed and the two that did not — but left the clause reading
endpoints, because widening it was outside that row's three named
guards. So the guard would pass on the same shape again tomorrow.

## Required Fix

1. Swap `_ITEM` for `_ids_in()` in
   `test_a_landed_status_names_only_closed_filings`, so a `landed`
   status is checked against every filed id its ranges span.
2. Sweep every `landed` and `partial` status in `directions.md` for the
   sentences the widening reddens, and correct each to what is true —
   the sentence is the defect, not the guard.
3. **The inverse check:** restore `` `UX-685`..`UX-692` all closed `` and
   confirm the widened clause reddens naming `689` and `690`. If it
   does not, the widening is vacuous and the fix is not made.

## Out of Scope

- `_RANGE_OPEN`'s phrasing set. `UX-748` widened it to
  `are|is|remain|remains` with an optional `still`; a further phrasing
  is a new finding and wants its own measurement rather than a guess
  bolted onto this row.
- The `landed as A..B` historical-record shape, which `UX-748`'s own
  comment says is a fixed record and correctly not range-expanded.

## Acceptance Test

`test_a_landed_status_names_only_closed_filings` reads `_ids_in()`,
`make test` is green with every corrected status pasted, and the
mutation above reddens it naming both open ids.

## Outcome

_Not started._
