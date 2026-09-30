# UX-1165: filter and link state residue after UX-1158

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the round-155 walk (2026-09-30) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_filter_and_back_state_is_kept_and_told.py`

## Motivation

Page: the round-155 walk of the two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14`, 114 elements; `bga_view --export`, Chromium 1440x900 and 390x844) at `8b7e3d3b`.

No-match filter on `#binary_cost`: the sentence "All 114 rows: …" stays over an empty table and "Copy 0 rows" stays; the strip caption reads "across 14 rows", not "across K of M rows", and no-match removes the strip; the chapter "Sections · N" button writes no hash and no history, so reload and Copy link lose it; "All rows" on a bounded table is never written to the link; Back after rail presses measured at 1440 only; `applyTopN` in `tables.js` is dead in production (one test uses it).

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

An empty filter result says so and offers no copy, the caption says K of M, every button that changes the view writes the link, and Back is measured at 390.

## Decision

- **Empty result:** at zero shown rows `Copy N rows`, its `as Markdown` box and the `All M rows: …` note hide (`structured.js`); the badge's `none of M match` is the one sentence.
- **Caption:** `columnStrip` takes `of`, so the strip's sentence reads `across K of M rows` while filtered; its label stays the column (`UX-1156`); no match still draws no strip (`drawings.js`, `shapes.js`).
- **Link:** the open chapters are written as `ch` when they differ from what the page opens itself (the first chapter and the anchor's own), and applied through `applyFolds`; `All rows` on a bounded table writes `n.<key>=` (`viewstate.js`). The fold stays `replaceState` - only the rail press is navigation.
- **Back at 390:** the rail journey runs at 390x844 as well as 1440x900.
- **Dead code:** `applyTopN` goes (`tables.js`); its one test reads `applyFilters` with `top`.
- **Guard:** `tests/unit/test_filter_and_back_state_is_kept_and_told.py`, extended. Mutations: each part reverted in turn.

## Out of Scope

The hash's encoding (an owner default of `UX-1158`).

## Acceptance Test

On the two-plane page a filter with no match leaves no table sentence and no "Copy 0 rows"; the "Sections · N" press and "All rows" survive a reload; Back at 390 returns each rail step. Mutation: restore one defect, and the guard reds.

## Outcome

**Gap measured** - the two-plane review page (`pages.two_plane_run(shape=REVIEW_SHAPE)`, 114 elements), Chromium 1440x900 unless named, base `3e6feb45`; the guard's own scripts, run by a scratch `measure.py`:

```text
filter before   badge 25 of 114          "68 ms → 1.1 s across 114 rows."    offered copy-rows, uniform-columns, copy-as
filter "layer01/mod002.bst"  badge 1 of 114  "1 row — too few to have a shape."
filter none     badge none of 114 match  strip gone                          offered copy-rows, uniform-columns, copy-as
fold press      open decide,run  hash ""   -> reload: open decide
All rows        wall_clock_share_us  hash ""   -> reload: top 25:value
back 1440       press3, back x3: open/rail/y  ...time|time|8509 / ...compare|compare|8050 / decide,change|change|5924 / decide|decide|0
back 390        press3, back x3: open/rail/y  ...time|time|13141 / ...compare|compare|12440 / decide,change|change|8978 / decide|decide|0
macro_micro     filter "core.bst": badge 8 of 71, strip "1 → 32 across 8 rows."
```

Back at 390 already walked the rail at base; it is now measured, not fixed.

**Close measured** - same page, same script:

```text
filter "layer01/mod002.bst"  badge 1 of 114  "1 of 114 rows — too few to have a shape."
filter none     badge none of 114 match  strip gone                          offered (none)
fold press      open decide,run  hash #~Y2g9ZGVjaWRlJTJDcnVuJmM9   -> reload: open decide,run
All rows        wall_clock_share_us  hash #~bi53YWxsX2Nsb2NrX3NoYXJlX3VzPSZjaD1kZWNpZGUlMkNydW4mYz0  -> reload: top "" (All rows)
back 1440/390   unchanged from the gap, three Backs restore each step
macro_micro     filter "core.bst": strip "1 → 32 across 8 of 71 rows.", label "Calls" at both widths
page half       golden 149,744 -> 149,932 B (+188); with_timeline 150,176 B, over 150,000 until UX-1167's 160,000
```

**Mutation table** - `tests/unit/test_filter_and_back_state_is_kept_and_told.py` (10 tests, 7 before), each mutation applied alone and the file restored from its copy:

| mutation | reddened | run |
|---|---|---|
| strip gets no `of` (`shapes.js`) | `test_the_strip_counts_the_filtered_rows` | 1 failed, 9 passed |
| copy and note stay at zero rows (`structured.js`) | `test_an_empty_result_offers_no_copy_and_no_sentence` | 1 failed, 9 passed |
| open chapters not captured | `test_a_chapter_fold_survives_a_reload` | 1 failed, 9 passed |
| open chapters not applied | `test_a_chapter_fold_survives_a_reload`, `test_three_backs_restore_rail_and_chapters` | 2 failed, 8 passed |
| `All rows` not captured | `test_all_rows_survives_a_reload` | 1 failed, 9 passed |
| empty `n.` not applied | `test_all_rows_survives_a_reload` | 1 failed, 9 passed |
| anchor's chapter counted as state | `test_an_untouched_page_writes_only_its_anchor`, `test_three_backs_restore_rail_and_chapters` | 2 failed, 8 passed |
| all reverted | - | 10 passed |

Re-based: the UX-1158 strip test's filtered-sentence claim now reads `K of M rows` (the label claim, `UX-1156`'s, is unchanged); `_FILTER` prefers the table holding a stated-once note (`binary_cost` on the two-plane page) and opens its chapter first, so visibility is readable. `test_the_top_n_preset_narrows_without_lying_about_the_total` reads `applyFilters` with `top` now that `applyTopN` is gone.
