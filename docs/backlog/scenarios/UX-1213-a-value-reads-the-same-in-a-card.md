# UX-1213: a value reads the same in a card, a table, a badge and a sentence

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-159 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_a_value_is_what_it_names.py` (`TestAValueReadsTheSameEverywhere`)

## Motivation

Page: the round-159 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `31b5971b`, Chromium 1440x900 and 390x844.

Walk, pre-existing: P5 the on-demand card reads "Is a leaf false", "Observed critical false" where the table reads "no". P6 badge "10 of 1,202" for a filter matching 10 is the same text as an unfiltered Top 10 window; "matched" appears only when the matches exceed the window (binary_cost focus "8 of 11,683"). P7 density sentence "across 1202 rows" beside the badge's "1,202".

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Decision

```text
Route:     three one-place fixes: the card's `shown` prints a non-number through plainValue (yes/no, as the tables do); badgeText says "matched" whenever matched < total (shown == matched reads "10 matched"); columnStrip's sentence counts through a separated count.
Rejected:  a per-site toLocaleString (the count would have three formatters again, UX-412).
Files:     bga/viewer/element.js `shown`; bga/viewer/tables.js badgeText; bga/viewer/drawings.js columnStrip; tests/unit/test_a_value_is_what_it_names.py.
Guard:     on walk: an on-demand card (layer10/mod010.bst) has no /\b(true|false)\b/ text and does print "Is a leaf no"; a filter matching n <= 10 under Top 10 badges "matched"; no visible text /\b\d{4,} rows/ on the three pages.
Mutation:  `String(row.value)` back -> "false", red; badgeText's `shown < matched` back -> "10 of 1,202", red; `${n}` back -> "1202 rows", red.
Class:     product
Split:     one track, T-D, parallel.
Question:  none
```

Budget: 0 (same word counts; no booleans in any card at rest on the three pages). Code half: architect +176 B, measured +88 B.

Changed from the architect's route: (1) `columnStrip` has no `plural` (tables.js imports drawings.js), so it keeps a local `count`; the `n === 1` plural test stays on the number. (2) The "1094 rows" in the walk is not the strip: it is `depthSentence`'s own local `plural` in shapes.js, which printed no separator - fixed there. (3) The toolchain card has no booleans on the generated page; the on-demand card the guard reads is `layer10/mod010.bst` (Is a leaf no, Observed critical no). Two guards in test_a_filter_is_a_property_of_a_table.py asserted the old `12 of 1,202` for a filter keeping 12 and are re-based to `12 matched`.

## Required Fix

Cards print booleans as the tables do; a filtered badge says matched whatever the window; counts carry a thousands separator.

## Out of Scope

The filter grammar (`UX-1206`).

## Acceptance Test

No card text matches /\b(true|false)\b/; a filter matching 10 under Top 10 reads "matched"; no visible text matches /\b\d{4,}\b rows/; a guard in `test_a_value_is_what_it_names.py`. Mutation: restore the defect, and the guard reds.

## Outcome

Gap measured (big page, `two_plane_run --layers 20 --width 60`, Chromium 1440x900, pre-change):
a filter keeping 10 under Top 10 read `10 of 1,202`, the unfiltered window's text; card
`Is a leaf false`; density sentence `across 1202 rows`; `1 level, 1094 rows`.

Close measured (same page, `test_a_value_is_what_it_names.py`, 9 passed in 23 s): window
`10 of 1,202`; `layer08/mod01` reads `10 matched`, a uid reads `1 matched`; card
`Is a leaf no`; no text node on big, golden or macro_micro matches `\b\d{4,}\b rows`.
Page half: viewer module gzip+base64 120,176 -> 120,264 B (+88 B; architect's bound +176).
Volume budget test passes unchanged. eslint bga/viewer clean.

| Mutation | Red | Count |
|---|---|---|
| element.js `plainValue(row.value)` -> `String(row.value)` | the booleans guard | 1 failed, 2 passed |
| tables.js `matched < total` -> `shown < matched && matched < total` | the matched guard | 1 failed, 2 passed |
| tables.js drop the `shown === matched` arm | the matched guard | 1 failed, 2 passed |
| drawings.js `${said}` -> `${n}` in the sentence | the comma guard | 1 failed, 2 passed |
| shapes.js drop `toLocaleString` in `depthSentence` | the comma guard | 1 failed, 2 passed |

Deviation: re-based two guards in `test_a_filter_is_a_property_of_a_table.py`
(`12 of 1,202` -> `12 matched`, `1 of 1,202` -> `1 matched`); shapes.js touched beyond the
declared files; the styleguide's §3 badge row gains the `10 matched` form. Hand-built fold
summaries (`decision.js` 97/326, `element.js` 704, `sections.js` 111, `views.js` 911) still print
an unseparated count and are left to a row of their own.
Follow-up 1 (`tally` in format.js, the one count formatter, routes quantity "count", plural, badgeText, sentences;
finding prose takes `:,`; two resource_blast count hints in schemas.py): bare 4+-digit text nodes 55 on big + 2 on
macro_micro -> 0 (`test_no_visible_count_reads_four_bare_digits`; reverting the count case, `_downstream`, the status
line or a hint: 1 failed). Page half +23 B. Re-based `test_all_rows_means_all_rows.py`'s caption to `all 1,202`.
Follow-up 2: `bst` on the elements table under Top 10 read `10 of 1,202`, the unfiltered text; badgeText takes
`narrowed` from the table's state and reads `10 of 1,202 matched` (`all N matched` unbounded), styleguide §3 amended.
`test_a_filter_matching_every_row_still_says_matched`: `hit` back to `matched < total`, or the caller passing
`narrowed: false`, reds it (1 failed each). Page half 158,220 -> 158,276 B.
