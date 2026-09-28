# UX-1092: a scenario declares its guard in one field, backfilled from the inferred column

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-1000 | **Blocks:** — | **Found by:** round 149 — the first weekly retro, `docs/audits/retro-2026-09-28.md`, proposal 3; promotes the r140 `coverage` line on `tools/dev_area_pages.py` | **Serves:** whoever assesses an area's coverage, and every filing the `coverage` class comes from | **Topic:** guards | **Area:** tools | **Shape:** judgement

## Motivation

9 of the week's 15 bookkeeping lines are `coverage`: a guard that
reads nothing. The area pages read covered 366 of 567, 245 of those
inferred from Outcome prose, and every pass over the prose found a new
shape. A guard named in one field at filing makes both exact.

## Required Fix

A task header carries a `Guard:` field naming the test file(s), or
`none` with a reason. `dev_area_pages.py` reads the field and stops
inferring. Closed rows are backfilled from the inferred column, each
backfill checked against the file existing.

## Out of Scope

Judging whether a named guard is strong; a `Guard:` on progress-tracker rows.

## Acceptance Test

`dev_close_task.py --check` refuses a row with no `Guard:` field or one
naming a missing file, and the area pages read 0 inferred. Mutation:
drop one row's field, and the check reds.

## Outcome
