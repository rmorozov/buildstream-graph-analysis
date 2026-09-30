# UX-1189: Copy exports the filtered population, not the page

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-157 data-exploration review (`/mnt/project-files/view-ui-review/data-exploration/review.md`) of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`, Plane 2 rewritten by heavy.py to 5,849 processes and at most 81 binaries per element) at `cbc739b0`, Chromium 1440x900 and 390x844 | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_copy_takes_the_matched_population.py`

## Motivation

Finding: 7 of the review.

Filtering the elements table to `layer1` matches 600 rows; the label reads "Copy 25 rows" and the clipboard gets 25. JSON copy writes `is_leaf: "false"` as a string. Controls that differ from their label: `button.copy-rows` after a filter reads "Copy 25 rows" with 600 matched and 25 copied. Breaks §4c.

## Decomposition

Input classes: the 1,202-element two-plane page, the heavy-binary page (`UX-1182`'s, heavy.py's until it lands), `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

Rule, "copy states and copies the population it names": copy takes every matched row up to a ceiling the label states ("Copy 600 matched rows"), and booleans stay booleans in JSON.

## Decision

Class: product.

Owner (Ruslan, 2026-09-30 19:26, on the controls-budget card, option
"Consolidate + raise"): every table's own "as Markdown" checkbox
becomes one page-wide control, carried inside this row since it is the
copy format; the xl_both controls bound is raised by the measured
remainder, once, by the integrator on the merge - not in this commit.

Architect (round 158):

```text
Route:     `copyRows` copies `state.kept` (the matched population `applyFilters` already writes, tables.js:256) up to `ALL_ROWS_CEILING` (200), and `label()` says it: "Copy 600 matched rows" / "Copy first 200 of 600 matched rows"; `rowJson` (tables.js:421) emits `true`/`false` as JSON booleans.
Rejected:  copy the mounted page (today) - the defect; copy unbounded - a 4,848-row clipboard write with no ceiling breaks §3k's "every step is bounded"; a new ceiling constant - `ALL_ROWS_CEILING` is the page's one "whole population" bound already.
Files:     bga/viewer/structured.js (interrogable: shownRows -> matchedRows, label, copyRows click); bga/viewer/tables.js (rowJson, rowsMarkdown takes the same rows); tests/unit/test_copy_takes_the_matched_population.py (new); tests/tiers.py; docs/backlog/bookkeeping.md (sweep the r152 "10 of 71" line).
Guard:     test_copy_takes_the_matched_population.py - after a filter the clipboard's row count equals min(matched, 200) and the label states both; a boolean column copies as a JSON boolean.
Mutation:  copy `shownRows()` again; the guard reds. Second: `rowJson` drops the boolean branch; the boolean clause reds.
Class:     product.
Split:     third in track B1, after UX-1185 (both write `label`).
Budgets:   page +~400 B; controls 0 (optional -28: see Question); height 0; words +~1 per filtered table, 0 at rest.
Overlap:   none outside B1.
```

Track B1, where the route moved: copy takes the matched population
only while a filter or threshold is set; unfiltered it takes the rows
shown, which is `UX-1185`'s label ("the Copy label follows the mounted
rows") and this row's Out of Scope. The one box is
`label.copy-as > input.copy-markdown` ("Copy tables as Markdown") in
the rail beside "Copy link to this view", built by `copyFormatBox` in
`viewstate.js`; it dispatches `bga:copy-format` on the document, which
every table's copy label hears. `readCopyFormat` holds the box's own
choice in memory first, so a page with no storage still copies what
its titles promise. The `r152` "10 of 71" bookkeeping line is the
closer's sweep, not this commit's.

## Out of Scope

The copy label after paging (`UX-1185`); the Markdown copy's layout.

## Acceptance Test

`tests/unit/test_copy_takes_the_matched_population.py`: after a filter the clipboard's row count equals the matched count up to the stated ceiling, and a boolean column copies as a JSON boolean. Mutation: copy `visibleRows`; the guard reds.

## Outcome

**Gap measured** - the guard against the UX-1190 commit's `structured.js`, `tables.js`, `viewstate.js` and `app.js` (swapped in, `mutate.py --head`), the 1,202-element page `two_plane_run(--layers 20 --width 60)`, `golden`, `macro_micro`, Chromium 1440x900:

```text
elements, filter "layer19"   badge "25 of 60 matched, of 1,202", label "Copy 25 rows", 25 copied
elements, filter "layer1"    badge "25 of 600 matched, of 1,202", label "Copy 25 rows", 25 copied
is_leaf, observed_critical   copied as "false" / "true" strings
Markdown boxes               one per table, in each table's tools
guard                        4 failed, 1 passed
```

**Close measured** - the same guard, and `measure.py` (`_LOOK` of the volume budget, opened), UX-1190 -> this commit:

```text
guard            test_copy_takes_the_matched_population.py 5 passed in 8.48s
"layer19"        "Copy 60 matched rows", 60 copied (25 mounted); "layer1" "Copy first 200 of 600 matched rows", 200
golden           19,047 -> 18,965 px   7,661 -> 7,633 words   374 -> 361 controls
macro_micro      38,231 -> 38,052 px   12,433 -> 12,373 words   684 -> 655 controls
xl_both          43,241 -> 43,074 px   12,353 -> 12,307 words   917 -> 895 controls
page bytes       +92 B (1,202 page, 739,159 -> 739,251 B)
touching files   78 files naming the four modules + budget + resting look + ids: 1 red (§4c row), fixed
```

**Mutation table** - `test_copy_takes_the_matched_population.py` (5 tests), each alone, restored from its copy, `PYTHONDONTWRITEBYTECODE=1`:

| mutation | reddened | run |
|---|---|---|
| copy takes `shownRows()` again | filter copies what it matched; past the ceiling | 2 failed, 3 passed |
| no `ALL_ROWS_CEILING` slice | past the ceiling the label states it | 1 failed, 4 passed |
| the label ignores the filter | filter copies what it matched; past the ceiling | 2 failed, 3 passed |
| `rowJson` drops the boolean branch | a boolean copies as a boolean | 1 failed, 4 passed |
| the box dispatches no `bga:copy-format` | one page-wide box sets every table's format | 1 failed, 4 passed |
| all reverted | - | 5 passed |

Re-based: `test_a_control_acts_on_what_it_names.py` (one box, every copy promises Markdown),
`test_a_control_says_what_it_does.py` (no table carries its own box),
`test_filter_and_back_state_is_kept_and_told.py` (`copy-as` is no longer in a table's tools); styleguide §4c.
Track B1 net over base `8a531cbb`: xl_both controls 886 -> 895 (+9, under 900), height 42,037 -> 43,074, page +1,167 B.
