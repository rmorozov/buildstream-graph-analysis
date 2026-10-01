# UX-1195: the filter grammar matches what the page shows: a constant column, the displayed word, the column's name

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the round-158 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** test_a_key_column_matches_exactly.py

## Motivation

Page: the round-158 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `43397b70`, Chromium 1440x900 and 390x844.

binary_cost says "Every row: Binary cc, Calls 1, Share of CPU 100.0%."; `binary:cc`, `cc` and `calls = 1` each give "none of 1,202 match" (1,202 rows qualify). On elements, `is_leaf:yes` and `observed:yes` match nothing (cells read yes/no, raw values are true/false; `leaf:true` gives 150); `level = 12` returns none where the page says Level; `duration > 5s` returns none where the column is element_durations (`durations > 5s` gives 576). `share > 50%` prints "'> 50%' is not a threshold this table can read, so it is not applied" and still empties the table. Verifier: `binary: make`, with a space, gives none with no hint; the badge reads "25 of 112 matched, of 4,057" (walk N6, VERIFY-2).

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

A clause matches a constant column the page states, the word a cell displays, and the column's displayed name or its singular; a clause not applied leaves the rows unfiltered; a key with a space after the colon is read or hinted; the badge states one population.

## Decision

Class: product.

### Architect's section (round 159)

```text
Route:     the grammar resolves over every column the table had, the stated-once ones included: `statedOnce` stashes each
           removed constant column's raw and shown value on the table, and `matchesKey`/thresholds/the word fall back to it;
           a key clause matches raw OR the displayed word; names add each word's singular; a word naming no column before a
           threshold is unread (said, nothing applied, no substring residue); `key: value` with a space reads; the badge
           states one population.
Rejected:  keep the constant columns in the DOM (hidden) - UX-349/UX-1151 removed them for width and the cells cost nodes
           (binary_cost on the walk page: 1,202 rows x 3 cells held); a `level` alias for unweighted_depth - levels are
           computed on the gating graph and depth on the whole graph (edg.py compute_unweighted_depth vs structural
           _compute_level_decomposition), so the alias could disagree; `level = 12` reads unread, naming the columns.
Files:     bga/viewer/tables.js (`columnNames`: singulars; `parseQuery`: `key:\s*value`, unread words, bare threshold skips
           `data-share` columns [UX-1194's line]; `matchesKey`: raw or shown, stated fallback; `applyFilters`: stated
           fallback for thresholds and the word; `badgeText`: `25 of 112 matched` - one population); bga/viewer/structured.js
           (`statedOnce`: stash; `interrogable` input handler: hand the stash and the th labels to parseQuery, the unread
           sentence names the word).
Guard:     tests/unit/test_a_key_column_matches_exactly.py, one case per quoted query, on the walk page and its binaries
           variant: binary:cc, cc, calls = 1 keep 1,202; is_leaf:yes and observed:yes keep the rows whose cells read yes;
           duration > 5s equals durations > 5s (576); share > 50% and level = 12 leave 1,202 rows and say why; `binary: make`
           equals `binary:make`; no badge carries two denominators.
Mutation:  stop the stash in statedOnce - binary:cc reads "none of 1,202", red; drop the singular - duration > 5s none, red.
Class:     product.
Split:     T1, first.
Budget:    volume-neutral (an unread sentence shows only on a bad clause); page half ~+0.8 KB (~40 lines).
Question:  none. The badge change reverses UX-1170's two-denominator form; record it.
```

### Where the track went further

```text
1. `name:value` whose name is no column is unread too, not a substring: `binary: make` on the elements table
   gave "none of 1,202" with no hint; it now applies nothing and names the columns, as the threshold clause does.
2. The stash is a `STATED` WeakMap in tables.js, read by `applyFilters` itself, so no caller threads it through.
3. The binaries variant is the guard's existing `heavy_binary_run` page (112 elements), not a second 1,202 build.
```

## Out of Scope

Op on the elements table (`UX-1194`).

## Acceptance Test

Each quoted query above returns the rows the page shows for it; a guard in `test_a_key_column_matches_exactly.py`, one case per query. Mutation: restore the defect, and the guard reds.

## Outcome

**Gap measured** (`27f21d10`, the 1,202-element page and its `--workload binaries` variant built by
`tests.pages.two_plane_run`, Chromium 1440x900, each query typed into the table's box; badge | rows mounted):

```text
elements     is_leaf:yes          none of 1,202 match | 0      (leaf:true: 25 of 150 matched, of 1,202)
elements     observed:yes         none of 1,202 match | 0
elements     duration > 5s        none of 1,202 match | 0      (durations > 5s: 25 of 576 matched, of 1,202)
elements     level = 12           none of 1,202 match | 0
elements     share > 50%          none of 1,202 match | 0      + "'> 50%' is not a threshold this table can read"
binary_cost  binary:cc / cc / calls = 1 / binary: cc   none of 1,202 match | 0   ("Every row: Binary cc, Calls 1, ...")
walkbin binary_cost  binary: make none of 11,683 match | 0     (binary:make: 1,200 matched)
```

**Close measured** (same pages, this commit):

```text
elements     is_leaf:yes          25 of 150 matched           elements  observed:yes   22 of 1,202
elements     duration > 5s        25 of 576 matched           elements  durations > 5s 25 of 576 matched
elements     level = 12           25 of 1,202 | "“level = 12”: no column here is called “level” (Element, ...), so it is not applied."
elements     share > 50%          25 of 1,202 | "“share > 50%”: no column here is called “share” (...)"
binary_cost  binary:cc, cc, calls = 1, binary: cc   1,202 matched (Copy first 200 of 1,202 matched rows)
walkbin binary_cost  binary: make 25 of 1,200 matched = binary:make
volume (measure.py, the guard's _LOOK, opened)   before -> after
  golden       19,277 px  7,744 w  378 ctl  2,708 nodes   unchanged
  macro_micro  38,484 px 13,060 w  788 ctl  6,801 nodes   unchanged
  xl_both      43,751 px 12,739 w  998 ctl  7,455 nodes   unchanged
  page half    151,905 -> 152,461 B (+556)
```

`test_a_key_column_matches_exactly.py` 12 passed; the 41 files naming tables.js/structured.js or the filter box:
663 passed, 2 skipped.

**Mutation table** (`mutate.py`, each restored from a copy; `test_a_key_column_matches_exactly.py`, 12 cases):

| mutation | reddened | run |
|---|---|---|
| `statedOnce` stops `STATED.set` | `test_a_column_stated_once_still_answers_the_box` | 1 failed, 11 passed |
| no singular in `columnNames` | `test_a_column_answers_to_its_singular` | 1 failed, 11 passed |
| `matchesKey` reads raw only, not the shown word | `test_a_key_clause_reads_the_word_the_cell_shows` | 1 failed, 11 passed |
| an unknown word before a threshold stays a substring | `test_a_word_naming_no_column_applies_nothing_and_says_so` | 1 failed, 11 passed |
| badge `K of N matched, of M` back | `test_the_badge_states_one_population` | 1 failed, 11 passed |
| `name:\s*value` back to `name:value` | `test_a_key_value_matches_that_column_exactly` (`binary: make`) | 1 failed, 11 passed |

Re-based guards (the badge's second denominator is gone): `test_filter_and_back_state_is_kept_and_told.py`,
`test_a_filter_is_a_property_of_a_table.py`, `test_copy_takes_the_matched_population.py` (two asserts). This reverses
`UX-1170`'s `K of N matched, of M`. The bare-threshold `data-share` skip (`UX-1194`'s line) has no guard here: nothing
marks a share head until `UX-1194` lands.
