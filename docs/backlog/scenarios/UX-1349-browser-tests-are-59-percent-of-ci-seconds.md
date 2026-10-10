# UX-1349: browser tests are 59% of CI's test seconds, against UX-690's 40%

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** main's first clean push run after UX-1348, run 37943350480 attempt 2 on `216fcc30` (2026-10-09) | **Serves:** R8 | **Topic:** guards | **Area:** tests | **Shape:** judgement | **Reading:** runner:test

**Guard:** `tests/unit/test_the_suite_holds_its_shape_budget.py::test_the_browser_row_holds_the_ledger`

## Motivation

The CI reference adopts only from a push run whose every cell is clean,
and the 3.9 cell was red 2026-09-29..10-09 (UX-1340), so the reference
sat still for ten days. Its first refresh, `records` `3f75d927`:

```text
$ python3 tools/dev_shape_budget.py      # reference 2d88ac2f -> 3f75d927
browser   642 s -> 1862 s of 3142 s total
browser budget: 59.3% measured, 40% the Required Fix states, 51.2% the ledger holds
```

The growth is new browser files, led by
`test_the_narrow_page_keeps_its_place.py` (131 s),
`test_an_element_view_answers_whole.py` (52 s),
`test_the_builder_sweep_is_drawn.py` (51 s). The owner adopted 59.3% on
2026-10-10 to turn main green, and asked for this row to cut it back.

## Required Fix

Bring the browser share back toward 40% without dropping a claim: share
one page build per fixture across browser files, or move a geometry check
that needs no layout to the DOM shim. Re-adopt the ledger at the new share.

## Out of Scope

Skipping, quarantining or deleting a browser test; changing the 40% target.

## Acceptance Test

`python3 tools/dev_shape_budget.py` on a CI reference adopted after the fix
reads the browser share at or under 45%, with every browser test still run.
