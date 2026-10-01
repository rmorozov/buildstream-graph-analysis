# UX-1211: Copy follows the order on screen

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the round-159 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_copy_follows_the_order_on_screen.py`

## Motivation

Page: the round-159 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `31b5971b`, Chromium 1440x900 and 390x844.

Walk P2 (pre-existing): task table sorted Duration ascending shows toolchain, all.bst, mod017, mod014, mod013 (400 ms), mod050 (450 ms); Copy gives payload order with all.bst last. Elements sorted by depth shows all.bst first; Copy puts it last.

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

Copy writes the rows in the order the table shows them, sort included.

## Out of Scope

Which rows Copy takes (`UX-1189`, closed).

## Acceptance Test

After a sort on the task and elements tables, Copy's row keys equal the shown rows' keys in order; a guard in a new `test_copy_follows_the_order_on_screen.py`. Mutation: restore the defect, and the guard reds.

## Decision

Round 160's architect (group A, track T-B), pasted. As built: the sort `applyFilters` ran on `kept` - the header's
or, with none, the Top-N column's - now runs on `rows`, the held order, before the filter loop; `kept` is built from
it in order and `showOnly` records it, so `ownRows` and Copy read the order on screen. The Top-N comparator moved
unchanged (unknown values last).

```text
Route:     the order the table shows is the one order it holds: applyFilters ranks every row (header sort, or the Top-N column) before filtering and hands that order to showOnly, so HELD.order - which ownRows, shownRows and Copy read - is the order on screen; today it keeps the payload order while the shown rows are appended sorted.
Rejected:  Copy re-sorting its rows with byColumn (a second sort that can disagree with the first); Copy reading DOM order (misses the fold's held middle, UX-1196).
Files:     bga/viewer/tables.js applyFilters (sort `rows`, not `kept`; pass the ordered list to showOnly); tests/unit/test_copy_follows_the_order_on_screen.py (new).
Guard:     on walk: task table sorted Duration ascending and elements sorted Unweighted depth, unfiltered and with a filter: Copy JSON keys == the shown rows' data-raw keys, in order.
Mutation:  pass `rows` to showOnly again -> all.bst last in Copy, red.
Class:     product
Split:     T-B first commit.
Question:  none
```

Budget: 0 at rest. Code half +172 B. The new guard sets `bga.copy-format` only if it reads Markdown; it removes it (UX-1217's census).

## Outcome

The gap measured, at `ffa8bcb1`, the 1,202-element two-plane page (`pages.two_plane_run --layers 20 --width
60`), Chromium 1440x900, each sortable table bounded to its first Rows-shown option and one head pressed
(`scratchpad/<worktree>/gap1211.py`, the guard's probe): 5 of 9 tables copy rows in an order the screen does not show.

```text
wall_clock_share_us duration_us ascending   shown toolchain, all.bst, mod017, mod014   copied toolchain, mod017, mod014, mod050
elements unweighted_depth descending        shown all.bst, mod040, mod028, mod059      copied mod040, mod028, mod059, mod022
critical_path_detail, binary_cost, levels   DIFFER;  element_deltas, serial_chains, consolidation, provenance   equal
```

The close measured, same page and probe: 9 of 9 equal (`wall_clock_share_us` copies toolchain, all.bst, mod017,
mod014 as shown). Page half on the walk run 157,669 -> 157,669 B (0: the comparator moved, the code did not
grow). Volume at rest unmoved (the change acts on a sort or a bound). The 25 existing test files naming
`tables.js` or Copy, with `test_the_page_has_a_volume_budget.py`: 501 passed, 5 skipped.

| mutation | reddened | run printed |
|---|---|---|
| `tables.js` at `ffa8bcb1` (sort `kept`, hold the payload order) | `..._in_their_order[macro_micro]`, `[big]` | 2 failed, 3 passed |
| reverted | | 5 passed |

golden does not discriminate: its sortable tables are 3 and 13 rows, unbounded, so `sortable` reorders the
held order itself. The filtered case does not either - `state.kept` was already sorted - and stays as coverage.
