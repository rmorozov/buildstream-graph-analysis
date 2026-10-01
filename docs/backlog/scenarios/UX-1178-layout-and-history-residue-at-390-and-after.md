# UX-1178: layout and history residue at 390 and after Expand all

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the round-157 walk (2026-09-30) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_the_narrow_page_keeps_its_place.py`

## Motivation

Page: the round-157 walk of the two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14`, 114 elements) and golden/macro_micro at `73af3af3`, Chromium 1440x900 and 390x844.

At 390 a labelled stacked table keeps an 87 px detached header ("Level / Elements here / Which elements", 3 x 29 px, `table-header-group`, not hidden) above rows that print their own `::before` labels (204 px on macro_micro `#serialization_point_risks`; 87 px on `#restructuring`), and the table is 194 px wide in a 342 px container, numeric labels right-aligned over left-aligned names. CODE names break at the hyphen ("lib-f.bst", "lib-e.bst": 2 of 233 on macro_micro at 390; 0 of 356 on the two-plane page). After Expand all the current chapter heading sits 686 px (390) or 456 px (1440) below the top while the hash and rail name it (`#chapter-time`, scroll 11995 at 390). A press on the rail link of the section you are on pushes a history entry (5 to 6, same hash; Back does nothing visible).

Extended by the round-157 data-exploration review (`/mnt/project-files/view-ui-review/data-exploration/review.md`, 1,202-element two-plane page at `cbc739b0`), finding 13 (screenshot `05-binary-cost-390.png`): at 390 `binary_cost`'s CPU values break across lines ("1.5 / s") and the threshold placeholders clip ("> 1(", "> 5(").

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

A labelled stacked table drops its detached header and fills its width; a code name does not break at a hyphen; Expand all keeps the current chapter at the top; a press on the current anchor replaces the entry, not pushes.

Finding 13: a quantity cell does not break inside its value at 390, and a threshold placeholder fits its box.

## Out of Scope

The wide layout's header, which stays for sorting; the Back and Forward landings `UX-1171` fixed.

## Acceptance Test

At 390 no labelled stacked table shows a header block and its width equals its container's; no CODE name breaks inside a token on macro_micro; after Expand all the current chapter's top is within a line of the viewport's top at 390 and 1440; a press on the current anchor leaves `history.length` unchanged. Mutation: restore one defect, and the guard reds.

Finding 13: at 390 no `binary_cost` quantity cell wraps inside a value and no threshold input's placeholder is wider than its box. Mutation: restore one defect, and the guard reds.

## Decision

```text
Route:     CSS: at the compact width a labelled stacked table hides its `thead` and takes its container's width; a code name gets `white-space: nowrap` up to the cell's width and keeps `overflow-wrap: anywhere` past it; a quantity cell is `nowrap`; the rail's Expand all lands the current chapter via `revealAndLand` after the folds settle; a press on the anchor already in the hash calls `replaceState`, not a navigation.
Rejected:  U+2011 non-breaking hyphens in names - copy and find then disagree with the uid; drop the stacked header in JS - the header's absence is a layout fact, and the wide layout keeps it for sorting.
Files:     bga/viewer/style.css (the compact-table block, `main code` 738, the quantity cell rule, `.th-filter` width); bga/viewer/nav.js (`toc`: the Expand all handler ~455); bga/viewer/app.js (`boot`: the capture click handler ~1134-1146, same-hash branch); tests/unit/test_the_narrow_page_keeps_its_place.py (new); tests/tiers.py.
Guard:     test_the_narrow_page_keeps_its_place.py - at 390: no labelled stacked table shows a header box and each equals its container's width; no `code` on macro_micro wraps inside a token; no `binary_cost` quantity cell wraps; no threshold placeholder is wider than its box; after Expand all the chapter top is within one line of the viewport top at 390 and 1440; a press on the current anchor leaves `history.length` unchanged.
Mutation:  remove the compact `thead` rule; the guard reds (second: restore the push on a same-hash press).
Class:     product
Split:     C4, one track, parallel. The placeholder clause retires if UX-1191 (B) folds the per-column thresholds into one filter - then the clause reads that box's placeholder.
Question:  none
```

## Outcome

Gap measured (macro_micro at 390x844, every chapter open, `HEAD` = `8a531cbb`):

```text
stacked table `thead` height        restructuring 87.4 px, serialization_point_risks 204.0 px (table-header-group)
stacked table width / container     327 / 327 (equal since UX-1157; kept as a clause)
code broken inside a token          3: lib-f.bst, dependency-wait, lib-a.bst (heavy 1,202 page: 1)
binary_cost quantity cells wrapped  heavy 1,202 page at 390: 12 ("1.5 s", "59 ms"); macro_micro at 320: 10 ("695 ms")
```

Close measured (same probe, same fixtures): `thead` 0 px on both; 0 code wrapped on macro_micro and the heavy page; 0 quantity cells wrapped (macro_micro 390 and 320, heavy 390). Export `page_bytes` 144,202 -> 144,436 (+234 B); controls 0; height at 1440 0 (every rule is inside `@media (max-width: 60rem)`). The volume budget, the size discipline, the compressed-JS budget, the counted-figure and register guards, and eslint are green. `test_the_narrow_page_keeps_its_place.py`: 12 passed.

| Mutation | Reddened | Count |
|---|---|---|
| delete `table:has(td table) > thead { display: none; }` | `test_a_stacked_table_shows_no_header_and_fills_its_box[macro_micro]` | 1 failed, 11 passed |
| delete the `main code:not(pre code)` inline-block rule | `test_no_code_name_breaks_inside_a_token[golden]`, `[macro_micro]` | 2 failed, 10 passed |
| delete `td.num { white-space: nowrap; }` | `test_no_binary_cost_quantity_wraps[320]` | 1 failed, 11 passed |
| drop `revealAndLand(box)` after Expand all | `test_expand_all_keeps_the_current_chapter_at_the_top` x4 (both fixtures, 390 and 1440) | 4 failed, 8 passed |
| `pushState` on every chapter press | `test_a_press_on_the_current_chapter_adds_no_entry` x2 | 2 failed, 10 passed |

Deviation: (1) the route said `nowrap` up to the cell's width; CSS cannot both forbid wrapping and wrap past a width, so a code name is `display: inline-block` (atomic: moves whole to the next line, wraps with `overflow-wrap: anywhere` only when wider than its line), at compact only. (2) "Labelled stacked table" is `table:has(td table)`; the other tables scroll sideways and keep their header for sorting. (3) The quantity clause is held at 320 as well as 390: macro_micro's cells do not wrap at 390 before the fix, so 390 alone would not redden; the heavy page is not rebuilt in the suite. (4) The threshold-placeholder clause moved to UX-1191 (it removes those inputs); no placeholder rule is written here. (5) `test_focus_keeps_the_reading_position.py` re-based: its probe scrolled to a button straight after Expand all and the new landing pulled it back to 26 px; the probe now waits 600 ms for the landing. (6) The tiers row for the new file is the orchestrator's.
