# UX-1158: filter and back-navigation state is not kept or told

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the round-154 walk, item 6 (2026-09-30) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_filter_and_back_state_is_kept_and_told.py`

## Motivation

Page: the round-154 walk of the two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14`, 114 elements; `bga_view --export`, Chromium 1440x900 and 390x844; screenshots in `round-154/`).

A no-match filter shows "0 of 114" and an empty table with no message; the drawing caption "across all 114 rows" ignores the filter; the rail's "Sections · N" toggles and the chapter open state are not restored on the third Back; the URL hash carries raw keys (`~v.elements=All+elements&n.binary_cost=25:cpu_us`).

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

A no-match filter says so and the caption counts the filtered rows; Back restores rail and chapter state; the hash reads as labels or is opaque on purpose.

## Decision

- **No match:** `badgeText(0, M)` reads `none of M match` (`tables.js`), beside the box that emptied the table.
- **Caption:** the strip redraws over the filter's rows on each `refresh` and says `across K of M rows`, `across all M rows` unfiltered (`shapes.js`, `structured.js`).
- **Back:** a rail chapter press is navigation, so the `UX-1056` capture listener (`app.js`) snapshots the entry it leaves and pushes `#chapter-<id>`; measured before: three presses, one Back leaves the page.
- **Hash: opaque on purpose.** The state after `~` is written as one unpadded base64 token; a query holding `=` is read as before, so every old hash and the rail's view links keep loading (`viewstate.js`). A view or Top-N control at its opening value writes nothing, so an untouched page's hash is its anchor alone.
- **Guard:** `tests/unit/test_filter_and_back_state_is_kept_and_told.py`, Chromium on `golden`, `macro_micro` and the two-plane page. Mutations: each part reverted in turn.
- **Bytes:** part paid for by two dead branches in code touched here - the strip click's shim fallback (`shapes.js`, it only re-ran what the `input` event had run) and the jump box's `location.hash =` (`app.js`).

## Out of Scope

The analysis behind the values; the other findings of the round-154 walk.

## Acceptance Test

On the two-plane page a no-match filter draws a message, and three Backs restore the rail and chapters. Mutation: restore the defect, and the new guard reds.

## Outcome

**Gap measured** - the two-plane review page (`gen-synthetic --seed 1 --store --layers 8 --width 14`, 114 elements), `bga_view --export`, Playwright Chromium 1440x900, HEAD `54d61bb9`:

```text
one rail press, nothing else   hash 121 chars: #~v.elements=All+elements&n.wall_clock_share_us=25:value&n.binary_cost=25:cpu_us&n.elements=25:element_durations&c=
filter "layer07"               badge 14 of 114   strip "Element durations across all 114 rows" (drawn from 114)
filter "zzzqqq"                badge 0 of 114    strip "across all 114 rows", table empty, no message
3 rail presses, then Back      history.length 2 -> 2 -> 2; the first Back left the page
```

**Close measured** - same page, same script:

```text
one rail press, nothing else   hash 13 chars: #chapter-time
filter "layer07"               badge 14 of 114   strip "Element durations across 14 of 114 rows" / "1.1 s -> 8.7 s across 14 rows"
filter "zzzqqq"                badge none of 114 match   strip gone; hash #chapter-time~Zi5lbGVtZW50cz16enpxcXEmYz0
3 rail presses, then Back x3   open decide,time,machine / decide,time / decide; rail machine / time / decide; y 12351 / 6056 / 0
export page half               149,151 -> 149,307 B (+156, budget 150,000)
```

**Mutation table** - `tests/unit/test_filter_and_back_state_is_kept_and_told.py` (7 tests; `golden` has no filterable table with a strip, so the filter tests read `macro_micro` and the two-plane page):

| mutation | reddened | run |
|---|---|---|
| badge back to `0 of M` | `test_a_no_match_filter_says_so` | 1 failed, 6 passed |
| strip not redrawn in `refresh` | `test_the_strip_counts_the_filtered_rows` | 1 failed, 6 passed |
| rail press pushes no entry | `test_three_backs_restore_rail_and_chapters`, `test_an_untouched_page_writes_only_its_anchor` | 2 failed, 5 passed |
| rail press pushes, no snapshot | `test_three_backs_restore_rail_and_chapters` | 1 failed, 6 passed |
| `joinHash` writes the readable query | `test_the_state_is_one_token` | 1 failed, 6 passed |
| opening Top-N written to the hash | `test_an_untouched_page_writes_only_its_anchor` | 1 failed, 6 passed |
| `splitHash` decodes every query as a token | `test_a_readable_hash_from_before_still_loads` | 1 failed, 6 passed |
| all reverted | - | 7 passed |

Re-based, the hash now a token: `test_a_fold_stays_open_in_the_link`, `test_a_link_that_shows_what_i_was_looking_at`, `test_a_rail_click_reaches_the_writer`, `test_the_fragment_keeps_up_with_the_fold`, `test_the_page_has_a_reader`, `test_the_fold_says_how_deep_it_goes` read it through `pages.view_query`; `test_the_rail_and_the_jump_box_write_the_anchor` reads the anchor alone (an untouched view writes no state).
