# UX-1224: a printed filtered table states its filter

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-160 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_a_printed_filtered_table_states_its_filter.py`

## Motivation

Page: the round-160 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `a69d1d88`, Chromium 1440x900 and 390x844.

Walk P8 (pre-existing): after "+1,160 more" the print medium shows "25 of 1,200 matched", the filter box is hidden, and no filter text reaches paper.

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

A table with a filter prints the filter it is under, beside its badge.

## Out of Scope

The print of a fold (`UX-1196`, closed) and of the chain boxes (`UX-1210`, closed).

## Acceptance Test

In the print medium after "+N more", the table's printed text contains the filter text; a guard in a new `test_a_printed_filtered_table_states_its_filter.py`. Mutation: restore the defect, and the guard reds.

## Decision

Architect, round 161 (2026-10-01):

```text
Route:     refresh() writes the trimmed filter-box value to the badge as `data-filter` (removed when empty); style.css @media print adds `.badge[data-filter]::after { content: " - filter: " attr(data-filter) }`, the `button.fold-more::after` print pattern already there.
Rejected:  printing the input (UX-1154 drops every input on paper); a print-only span with real text (a second text node beside a role=status region hidden in two media).
Files:     bga/viewer/structured.js (refresh, ~:958), bga/viewer/style.css (print block ~:688), tests/unit/test_a_printed_filtered_table_states_its_filter.py
Guard:     under print media, after "+1,160 more" (depends_on:toolchain.bst) on the 1,202 page and its binaries variant at 1440 and 390, the elements badge's ::after computed content contains the filter text; an unfiltered badge has no data-filter.
Mutation:  Delete the data-filter write in refresh: red.
Class:     product
Split:     same track as UX-1223, first.
Question:  none
```

## Outcome

The gap measured, at `e60195184`, the 1,202-element two-plane page (`pages.two_plane_run --layers 20 --width 60`),
Chromium 1440x900, print media, toolchain.bst's card "+1,160 more" pressed (`scratchpad/<worktree>/r1224.js`):

```text
{"more": "+1,160 more", "badge": "25 of 1,200 matched", "filter": null, "after": "none",
 "box": "depends_on:toolchain.bst", "print": true}
```

The close measured, same page and probe: `"filter": "depends_on:toolchain.bst"`, badge `::after` content
`" - filter: depends_on:toolchain.bst"` under print, `none` on screen. The guard: 1,202 page and its `--workload
binaries` variant at 1440 and 390, 1 passed (12.3 s). Golden's page half 159,146 -> 159,261 B (+115). The print
guards, `test_the_viewer_js_ships_compressed.py`, `test_a_status_is_announced.py` and
`test_a_filter_is_a_property_of_a_table.py`: 97 passed.

| mutation | reddened | run printed |
|---|---|---|
| delete the `data-filter` write in `refresh` | `test_a_printed_filtered_table_states_its_filter` (`'filter': None` after the press) | 1 failed |
| reverted | | 1 passed |
