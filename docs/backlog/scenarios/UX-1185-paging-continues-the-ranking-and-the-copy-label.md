# UX-1185: paging continues the ranking, and the copy label follows the page

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-157 data-exploration review (`/mnt/project-files/view-ui-review/data-exploration/review.md`) of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`, Plane 2 rewritten by heavy.py to 5,849 processes and at most 81 binaries per element) at `cbc739b0`, Chromium 1440x900 and 390x844 | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Finding: 3 of the review.

Screenshot `02-task-share-after-next.png`. At rest `wall_clock_share_us` shows Top 25 by share; Next shows payload rows 41-80, alphabetical, and ranks 26-40 cannot be reached by paging. The Top-N select goes blank. There are 31 pages at 1,202 rows and 122 at 4,848 (heavy `binary_cost`). The offset is not in the fragment, so a reload returns to Top 25. Controls that differ from their label: `button.copy-rows` after Next reads "Copy 25 rows" with 40 rows mounted; `button.page-next` from Top 25 reads "Next ›" and jumps to payload rows 41-80, dropping the ranking. Breaks §3k and §4c; amends `UX-1028`'s pager (closed).

Unroll threshold, priced at `UNROLL_AT = 80`: on the committed pages only `macro_micro`'s `binary_cost` (71 rows) changes, +46 rows at 32.25 px = +1,484 px, so the small class's opened height goes from 36,859 to about 38,343 px against a 38,200 bound (over by about 143 px); the Top-N select stays, so controls are unchanged; about 100 B of page code against 15,798 B of headroom. At 40 nothing changes; at 120 heavy `by_binary` gains 56 rows (42,309 to about 44,115 px against 43,500 on the 4,100 class: over).

## Decomposition

Input classes: the 1,202-element two-plane page, the heavy-binary page (`UX-1182`'s, heavy.py's until it lands), `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

Rule, "a pager continues the view": in `bga/viewer/structured.js`, `state.top` keeps `opening.top.column` in `step`, so the pager steps the order and the bound the table opened on; `openingBound` and the page size become one number; the Copy label follows the mounted rows; the offset travels in the view state and the fragment.

Per D1, a table of at most 80 rows (two pages) opens whole, and past that it opens bounded with the filter as its first tool. The small class's opened-height bound in `tests/unit/test_the_page_has_a_volume_budget.py` moves 38,200 -> about 38,400 px, with this row and the +1,484 px measurement as its reason.

## Decision

Owner (Ruslan, 2026-09-30 19:04 ("your defaults looks good to try")), D1: unroll a paged view at 80 rows (two pages) or fewer; where that pushes the small page's opened-height bound over, raise it about 200 px with the reason filed. D4: the pager walks the opening ranking, not payload order. Class: product.

## Out of Scope

What the ranking ranks by (each section's own opening sort); the filter's grammar (`UX-1191`).

## Acceptance Test

`tests/unit/test_a_pager_continues_the_view.py`: on all three 1,202-row tables the first row after Next is rank 26 of the opening sort (or 41 after a 40-row opening), the copy label equals the mounted row count, a reload with the fragment restores the position, and `macro_micro`'s 71-row `binary_cost` opens whole. Mutation: `step()` sets `column: null`; the guard reds.

## Outcome

Open.
