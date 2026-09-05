# UX-712: the size ledger, for what has no finding identity

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-694 (the baseline, whose second half this is), UX-418 (the reference method) | **Found by:** round 95, splitting UX-694 into two tracks | **Serves:** the refactor stream (`UX-695`), which reads the top row of this ledger and today has no ledger to read | **Topic:** guards | **Shape:** bounded

## Motivation

`UX-694` landed the baseline: 299 findings by identity over `bga/`,
`tools/` and the hooks, zero-tolerance for a new one. What has no
finding identity stayed unmeasured — a file's length, a function's
length, a duplicate block — and `UX-695` names those as the refactor
queue. Round 93's readings: `format_text` 548 lines, 15 files over
1,000 lines, `bga/schemas.py` 5,517.

## Required Fix

`tools/dev_baseline.py --sizes` (or `tools/dev_sizes.py`) writes
`tests/quality_reference.json`: per file, the longest function in
lines, the file's lines, and duplicate blocks (`pylint --disable=all
--enable=duplicate-code`, the one pip-installable measure); a guard
fails when any cell grows; `--adopt` rewrites a cell that shrank, in
the same commit (`UX-418`'s pattern). Counts only, never seconds.

## Out of Scope

- A target below today's numbers — the ratchet's direction is the
  policy; the pace is `UX-695`'s.
- Test files — `UX-690`'s shape budget is the suite's ledger.

## Acceptance Test

`--sizes --check` passes on the adopting commit; mutation: add ten
lines to `format_text` — its row grows, red; `--adopt` refuses to move
a cell upward without `--force`.
