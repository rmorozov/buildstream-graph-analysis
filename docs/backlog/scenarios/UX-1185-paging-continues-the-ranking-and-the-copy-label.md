# UX-1185: paging continues the ranking, and the copy label follows the page

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the round-157 data-exploration review (`/mnt/project-files/view-ui-review/data-exploration/review.md`) of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`, Plane 2 rewritten by heavy.py to 5,849 processes and at most 81 binaries per element) at `cbc739b0`, Chromium 1440x900 and 390x844 | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_a_pager_continues_the_view.py`

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

Architect (round 158):

```text
Route:     `interrogable`'s pager (structured.js:993-1046) steps `state.top = {n: opening.top.n, column: <current sort column>, offset}` - the page size is the opening bound (25), one number, and `openingBound` (tables.js:292) returns null at `total <= UNROLL_AT = 80`; `label()` reruns from `refresh`, not only on input/change; the offset and the sort ride `captureView`/`applyView`.
Rejected:  keep the pager at 40 over payload order and drop the preset on Next (today's shape) - D4 rejects it; a separate paging state beside `state.top` - two sources for one window is what Review #295 fixed; unroll at 120 - over 43,500 on heavy by ~615 px (task file).
Files:     bga/viewer/structured.js (interrogable: pagerRefresh, step, prev/next handlers, preset change, refresh calls label); bga/viewer/tables.js (openingBound, new UNROLL_AT); bga/viewer/viewstate.js (captureView, applyView: offset key); tests/unit/test_a_pager_continues_the_view.py (new); tests/unit/test_the_page_has_a_volume_budget.py (50-class row, line 379: 38,200 -> 38,400 px with UX-1185's +1,484 px reason); tests/unit/test_all_rows_means_all_rows.py and test_every_step_past_a_bound_is_bounded.py (window size 40 -> opening n, only where they assert it); tests/tiers.py.
Guard:     test_a_pager_continues_the_view.py - on the three 1,202-row tables row 1 after Next is rank 26 of the opening sort; copy label == mounted rows; fragment reload restores the offset; macro_micro `binary_cost` (71) opens whole.
Mutation:  `step()` sets `column: null` (structured.js:1029); the guard reds on rank 26.
Class:     product.
Split:     first in track B1.
Budgets:   page +~700 B; controls 0 (the select stays); height: macro_micro opened +1,484 px (bound raised per D1), xl_both 0 (no table of 41-80 rows on the committed pages, per the task file); words macro_micro +~140 (46 binary rows x ~3).
Overlap:   UX-1190 and UX-1189 rewrite the same state and `label` - same track, after it.
Question:  none (D1, D4 recorded).
```

Track B1, where the route moved: the offset travels as `p.<table>` and
is put back through a `bga:page` event on the pager, not by clicking
Next N times (47 clicks for the last page of 1,202). Next steps from
the end of what is shown (`Top 10` then Next is rows 11-35), and the
last page is aligned (rows 1,201-1,202), not clamped full: the old
clamp re-showed 23 rows on the last page, 1,225 rows walked for 1,202,
which is the ranking not continuing. The page-size-40 assertions the
architect expected in `test_all_rows_means_all_rows.py` and
`test_every_step_past_a_bound_is_bounded.py` do not exist; neither
moved.

## Out of Scope

What the ranking ranks by (each section's own opening sort); the filter's grammar (`UX-1191`).

## Acceptance Test

`tests/unit/test_a_pager_continues_the_view.py`: on all three 1,202-row tables the first row after Next is rank 26 of the opening sort (or 41 after a 40-row opening), the copy label equals the mounted row count, a reload with the fragment restores the position, and `macro_micro`'s 71-row `binary_cost` opens whole. Mutation: `step()` sets `column: null`; the guard reds.

## Outcome

**Gap measured** - the guard against base `8a531cbb`'s `structured.js`, `tables.js` and `viewstate.js` (swapped in, `mutate.py --head`), 1,202-element page `two_plane_run(--layers 20 --width 60)`, Chromium 1440x900:

```text
wall_clock_share_us, binary_cost, elements   Next -> "rows 41-80 of 1,202", payload order
                                             (share: 1,740,000 / 1,800,000 / 150,000), 40 mounted
copy label after Next                        "Copy 25 rows" with 40 mounted
fragment after two Nexts                     no offset; reload opens Top 25
macro_micro binary_cost                      25 of 71 mounted
guard                                        4 failed, 1 passed
```

**Close measured** - the same guard and `measure.py` (`_LOOK` of the volume budget, opened), base -> this commit:

```text
guard            test_a_pager_continues_the_view.py 5 passed in 9.60s
walk             1,202 rows on 49 pages per table, non-increasing, page 2 row 1 = rank 26
golden           19,046 px  7,661 words  372 controls  2,642 nodes   (unmoved)
macro_micro      36,743 -> 38,226 px   12,399 -> 12,433 words   661 controls   5,606 -> 5,974 nodes
xl_both          42,037 -> 43,166 px   12,320 -> 12,353 words   886 -> 885 controls   6,847 -> 7,019 nodes
page bytes       +272 B (1,202 page, 738,084 -> 738,356 B)
touching files   47 files naming structured/tables/viewstate + budget + compressed: 9 red, rebased below
```

**Mutation table** - `test_a_pager_continues_the_view.py` (5 tests), each alone, restored from its copy, `PYTHONDONTWRITEBYTECODE=1`:

| mutation | reddened | run |
|---|---|---|
| `step()` sets `column: null` | page 2 is rank 26, pages walk the ranking | 1 failed, 4 passed |
| `captureView` drops `p.` | a reload with the fragment keeps the page | 1 failed, 4 passed |
| `relabel = label` removed | the copy label counts the mounted rows (last page, 2 rows) | 1 failed, 4 passed |
| `UNROLL_AT = 40` | eighty rows or fewer open whole | 1 failed, 4 passed |
| all reverted | - | 5 passed |
| (round-158 residue) the filter's `rewind?.()` call removed | a filter edit returns the pager to its first rows | 1 failed, 5 passed |
| (round-158 residue) `data-offset` written at offset 0 | a filter edit returns the pager to its first rows (`p.` in the link) | 1 failed, 5 passed |

Re-based: the small class's opened bound 38,200 -> 38,400 (D1, styleguide §3e);
`test_the_max_jobs_advice_is_one_level.py` 45 -> 85 rows and
`test_all_rows_means_all_rows.py` 60 -> 100 resources (past `UNROLL_AT`);
`test_filter_and_back_state_is_kept_and_told.py` reads a whole table's `71 rows`
badge and no longer needs macro_micro to open bounded;
`test_a_filter_is_a_property_of_a_table.py` Top 10 then Next is `rows 11-35`;
`test_the_report_has_two_panes.py` reads the new `openingBound` line.
xl_both is not 0 px as the architect priced: `consolidation_candidates`
(75 rows) unrolls, +1,129 px, 334 px of the 43,500 left.

**Residue (round 158, walk N3).** A filter edit kept the pager offset. Against `1901e8a7` the new clause reads `rows 26-50 of 60` after `layer1`, Next, `layer12/` on the 1,202 page's `elements` (`1 failed, 5 passed`); on the heavy 1,202 page `binary:lognormal*`, Next, `binary:lognormal-308` read `rows 26-31 of 31`, `6 of 31 matched`, and clearing read `rows 26-50 of 11,683` with `p.binary_cost=25`. Any input on the box now rewinds the pager to offset 0, and offset 0 writes no `p.`: `rows 1-25 of 31`, first row `lognormal-308`; cleared, `rows 1-25 of 11,683`; neither link holds `p.`. Paging stays on, so `test_a_filter_is_a_property_of_a_table.py`'s `rows 1-1 of 1` and its disabled Next hold. `6 passed`, and the two files together `17 passed in 21.94s`.
