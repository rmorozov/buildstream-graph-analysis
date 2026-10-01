# UX-1194: op: and a duration threshold meet on the table that holds durations

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-158 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_op_and_duration_meet_on_durations.py`

## Motivation

Page: the round-158 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `43397b70`, Chromium 1440x900 and 390x844.

The review's task 2, "BUILD elements over 60 s": the only table that accepts `op:` is the task-share table, and `op:BUILD > 60s` there returns 1 row, toolchain.bst "4.9 min", which is its share of the window (element duration 0 ms). The elements table, which holds durations, has no op column: `op:BUILD > 5s` gives none of 1,202; `> 60s` gives 0 rows, the true answer. Task walk: 3 actions, answer WRONG (walk158-findings.md, N7).

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

A reader asking for elements of an op over a duration reaches one table where both clauses meet on element durations; a duration threshold on a share column is refused, not read as a duration.

## Decision

Class: product.

Architect (round 159, group A, track T2):

```text
Route:     publish each task's own duration as `task_durations_us` (task-uid keyed, an analyze/v6 permitted addition) and draw it
           as the Duration column of the task table, ahead of the share, so the reader types `op:BUILD > 60s` in that table's box
           and the bare threshold reads Duration; the share column's header is marked and a bare threshold never reads it.
Rejected:  op on the element table - `element_durations` is the element's LONGEST task (bga/graph/edg.py
           compute_element_durations), so `op:BUILD > 60s` there admits an element whose FETCH took 61 s and BUILD 5 s, and an
           element has many ops, not one;
           a viewer join of share keys to element durations - the same max-task error, plus a derivation on the page;
           refusal alone - honest but never answers the review's task 2.
Files:     bga/analyzer.py (signals block beside `wall_clock_share_us`, ~l.2335: `{str(t.task_key): t.dur_us for t in
           self.normalized_tasks}`); bga/schemas.py (the type map l.317, the key list l.1097, a `task_durations_us`
           definition beside l.2736 with KEYED_BY task_uid, QUANTITY duration_us, GROWS tasks, the rail/question table
           l.5290); bga/viewer/pairs.js (new `taskSignalTable`, the task-keyed sibling of `elementSignalTable`);
           bga/viewer/sections.js (`renderSection`: wall_clock_share_us drawn through it when task_durations_us is present;
           `DRAWN_ELSEWHERE` gains task_durations_us; `mapSectionLabels`: the "A share of the active window, not a
           duration" lead and its link retire where a Duration column stands beside, and the share th gets `data-share`);
           bga/viewer/chapters.js (the chapter list at l.149 names task_durations_us beside wall_clock_share_us);
           docs/guides/cli.md (the contract section names `task_durations_us` - test_the_documents_keep_up_with_the_contracts
           reddens without it). The parseQuery line "a bare threshold skips a th[data-share] column" rides UX-1195 (T1).
Guard:     tests/unit/test_op_and_duration_meet_on_durations.py (new) on the walk page: `op:BUILD > 60s` in the task table
           keeps exactly the payload's BUILD tasks over 60e6 us (0) and never toolchain.bst; `op:BUILD > 5s` keeps the count
           derived from the payload (non-zero, so the 0 is not vacuous); on a BUILD-only run each task_durations_us equals
           its element's element_durations (a cross-check against a second published field); with the key deleted from the
           payload, bare `> 60s` is unread and the rows stay whole.
Mutation:  put the share column first (or drop the data-share mark) - toolchain.bst at 4.9 min returns, red.
Class:     product.
Split:     one track, T2, first in it; runs beside T1, merges after T1 (needs its parseQuery line).
Budget:    measured by prototype (Duration th+button and a td per shown row): xl_both +27 nodes (7,482 of 7,500 alone),
           +25 words, +1 control; macro_micro +13 nodes, +11 words, +1 control; retiring the share lead's link takes the
           control back (-1). Payload: +10.7 KB gzipped on xl_both. Page half ~+0.9 KB (~45 JS lines).
Question:  none. Deviation to record: the Required Fix says "element durations"; the clause meets on the BUILD task's own
           duration, which is what "BUILD elements over 60 s" asks and equals the element's on a BUILD-only run.
```

Taken, with three changes. The column's key is `duration_us`, not `duration`: `UX-1184`'s guard holds one title per field, and every other "Duration" column is `duration_us`. `UX-1192`'s outlier strip read the task table's first quantity, which is now Duration (no outlier on this run), so its guard reads the share strip off the same page with `task_durations_us` removed - the older-payload rendering this row keeps. The "with the key deleted, bare `> 60s` is unread" clause needs `UX-1195`'s `data-share` skip in `parseQuery` (T1); this guard asserts what this commit owns there - the old two-column table and its lead come back.

## Out of Scope

The task-share table's share semantics (`UX-1184`); the filter grammar's other words (`UX-1195`).

## Acceptance Test

On the 1,202-element page, `op:BUILD > 60s` returns the elements whose BUILD duration exceeds 60 s (0 here) and never toolchain.bst at its share; a guard in a new `test_op_and_duration_meet_on_durations.py`. Mutation: restore the defect, and the guard reds.

## Outcome

### The gap, measured

```text
two_plane_run --layers 20 --width 60 (1,202 elements, all BUILD), Chromium 1440x900; the page with
task_durations_us removed from its payload, which renders as 27f21d10 did:
  heads ["Task", "Wall-clock share"]
  op:BUILD > 60s  "1 of 1,202"  toolchain.bst 4.9 min   (its share; task_durations_us 0)
  op:BUILD > 5s   "1 of 1,202"  toolchain.bst 4.9 min
```

### The close, measured

```text
same page, this commit:
  heads ["Task", "Duration", "Wall-clock share"]  (share th data-share)
  op:BUILD > 60s  "none of 1,202 match"           analyze: BUILD tasks over 60e6 us = 0
  op:BUILD > 5s   "25 of 576 matched, of 1,202"   analyze: BUILD tasks over 5e6 us = 576
  task_durations_us == element_durations on all 1,202 (one task per element)
$ PYTEST_XDIST= python3 -m pytest tests/unit/test_op_and_duration_meet_on_durations.py -q
7 passed in 6.87s
volume, opened, 1440x900 (27f21d10 -> this commit):
  xl_both      height 43,548 -> 43,503, words 12,739 -> 12,743, controls 998 -> 997, nodes 7,455 -> 7,481
  macro_micro  height 38,308 -> 38,263, words 13,060 -> 13,057, controls 788 -> 788, nodes 6,801 -> 6,813
  page half 151,905 -> 152,253 B; bga/schemas.py 6,998 lines (descriptions joined to fit)
```

### Mutations verified red and reverted (4)

| # | mutation | reddened |
|---|---|---|
| M1 | `structured.js` `mapTable`: `...beside` after the value column (share first) | 5 of 7, `op:BUILD > 60s` among them (toolchain.bst back) |
| M2 | `analyzer.py`: drop the `task_durations_us` line | 6 of 7 |
| M3 | `sections.js`: `data-share` -> `data-shown` | 3 of 7 (`the_duration_column_stands_before_the_marked_share[*]`) |
| M4 | `sections.js`: `else if (false && named ...)` (no lead without the key) | `test_without_the_key_the_share_table_is_as_it_was`, 1 failed |

Reverted from the saved copy each time: 7 passed.

Re-based in this commit: `test_a_column_is_named_for_its_field.py` (the lead and its link retire beside a Duration column; the share is marked), `test_a_key_column_matches_exactly.py` (a bare `> 1s` in the task table counts `task_durations_us`), `test_a_mark_says_its_value.py` (the outlier strip read on the share-only payload), `test_a_shapeable_population_is_drawn.py` (`task_durations_us` answered as the task table's column), `docs/guides/cli.md` 606 -> 607 keys.

**Deviation (round 159 walk, N4).** toolchain.bst read Duration 0 ms beside a 4.9 min share: an analyzer bug, not a real share. The sweep sorts ends before starts, so a zero-length task's end preceded its own start and it stayed active to the run's end. Such a task now enters no events (Part 20: share is the integral over its own execution).
Shares over their own duration: walk 1 (toolchain.bst 0 us, share 291,775,000) -> 0; macro_micro 1 (20,433,333) -> 0; the sum is unchanged (1,447,950,000; 43,200,000). The 60 s premise goes; `op:BUILD > 5s` holds the non-vacuity (share count differs).
`test_a_mark_says_its_value.py` re-based: its outlier was this defect, so the fixture plants 291,775,000 and the rest's spread is read against the cut (p95 at x 40, bound 10 x 100 x cut/max = 16.5).
Mutation: the zero-length filter keeping every event gives `test_no_task_holds_more_of_the_window_than_it_ran[walk, macro_micro]` 2 failed, 11 passed.

**Deviation (round 159 verification, older payload).** The share was marked `data-share` only beside Duration, so without `task_durations_us` a bare `> 60s` and `op:BUILD > 60s` read the share (toolchain.bst at 4.9 min, the gap above) and `parseQuery`'s share skip never ran. The share is marked always; the lead stays where Duration is absent.
Stripped walk page, this commit: `> 60s` and `op:BUILD > 60s` say "“> 60s” is not a threshold this table can read, so it is not applied." and keep all 1,202 rows; heads `[key, value(data-share)]`.
Mutations: marking only beside Duration gives 2 failed, 11 passed (`..._share_table_is_as_it_was`, `..._a_bare_threshold_reads_no_share`); `!spec.share` dropped from `parseQuery`'s primary gives 1 failed, 12 passed.
