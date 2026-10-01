# UX-1227: the palette's first ArrowDown lands on its first row

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** — | **Found by:** verifier A, the round-160 verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_the_palette_arrows_start_at_the_ends.py`

## Motivation

`UX-1212`'s Deviation: the palette's ArrowDown path lands on row 1 first; `bga/viewer/app.js:359` reads `active = (active + step + rows.length + (active < 0 ? 1 : 0)) % rows.length`, so from -1 a step of 1 gives 1. Noticed, not changed.

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

From no active row, ArrowDown lands on row 0 and ArrowUp on the last row.

## Out of Scope

The palette's result order.

## Acceptance Test

Open the palette, one ArrowDown: row 0 active; one ArrowUp from none: the last row; a guard in a new `test_the_palette_arrows_start_at_the_ends.py`. Mutation: restore the defect, and the guard reds.

## Decision

Architect, round 161 (2026-10-01):

```text
Route:     app.js:359 becomes `active = active < 0 ? (step > 0 ? 0 : rows.length - 1) : (active + step + rows.length) % rows.length;`.
Rejected:  starting `active` at 0 on render (a highlighted row before any key press is a new state).
Files:     bga/viewer/app.js, tests/unit/test_the_palette_arrows_start_at_the_ends.py
Guard:     golden export's jump box in Chromium (harness of test_jump_finds_what_the_rail_lists.py): ArrowDown once -> row 0; ArrowUp once -> last row.
Mutation:  Restore `+ (active < 0 ? 1 : 0)`: ArrowDown reads row 1, red.
Class:     product
Split:     with UX-1225.
Question:  none
```

## Outcome

The gap measured, at `e60195184`, golden's export in Chromium 1440x900, the jump box typed "bst" (10 rows), one
key from no active row (the guard's probe): `{'down': {'active': 1, 'rows': 10}, 'up': {'active': 9, 'rows': 10}}`:
ArrowDown skipped row 0; ArrowUp already reached the last row.

The close measured, same probe: down active 0, up active 9; 1 passed (1.2 s). Golden's page half 159,345 ->
159,357 B (+12). With the jump, rail-anchor, heading, compression and seam guards: 78 passed.

| mutation | reddened | run printed |
|---|---|---|
| restore `+ (active < 0 ? 1 : 0)` | `test_the_palette_arrows_start_at_the_ends` (down active 1) | 1 failed |
| reverted | | 1 passed |

The ArrowUp assertion does not discriminate under that mutation (the old formula also gave the last row from
-1); it stays as coverage of the Required Fix's second clause.
