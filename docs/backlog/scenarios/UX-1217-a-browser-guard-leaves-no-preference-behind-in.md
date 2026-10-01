# UX-1217: a browser guard leaves no preference behind in the worker's shared Chrome

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-159 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** guards | **Area:** tests | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_a_browser_drive_starts_clean.py`

## Motivation

Page: the round-159 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `31b5971b`, Chromium 1440x900 and 390x844.

Root cause of `911b36d7`: one Chrome per worker shares localStorage across test files; the task-table guard stored `bga.copy-format=markdown` and `test_copy_takes_every_row_the_fold_holds_and_never_the_stub` then read Markdown as JSON - JSONDecodeError at char 0, red every time the two ran in that order in one process (1 failed, 28 passed).

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

Each browser test starts and ends with the page's localStorage empty of bga keys, checked by a census, not by each guard's care.

## Out of Scope

Session history (`UX-1215`).

## Acceptance Test

A fixture asserts no `bga.` localStorage key survives a test; a guard that sets one and does not remove it reddens the census. Mutation: restore the defect, and the guard reds.

## Decision

Architect, round 160 (rows UX-1215 and UX-1217 share one route and one track):

```text
Route:     mechanism, not census: every drive in tests/cdp.mjs resets the tab's history and clears the page's localStorage before its own document runs - Page.resetNavigationHistory unconditionally, plus a one-shot Page.addScriptToEvaluateOnNewDocument("localStorage.clear()") added before Page.navigate and removed (Page.removeScriptToEvaluateOnNewDocument) after the settle loop, so a journey's own reloads keep their storage.
Rejected:  census of Back-callers asserting fresh_history (UX-1215 AT) - a guard for a mistake the driver can make impossible; fixture asserting no bga. key survives (UX-1217 AT) - same, and a crashed drive skips teardown; fresh tab per drive (/json/new + /json/close, would also close bookkeeping r152's 200-navigations line) - measured 526.0 vs 359.1 ms median drive (+46%, n=10), and storage still leaked (fmt "markdown"); Storage.clearDataForOrigin - origin of a file:// page unproven.
Files:     tests/cdp.mjs (header comment lines 5-9; top-level block at :184 before Page.navigate; after the settle block ~:257; drop freshHistory :53); tests/browser.py Browser.measure (drop fresh_history param + docstring lines); RETIRE: kwarg in tests/unit/test_the_rail_tools_and_the_pager_read_as_one_set.py test_expand_and_collapse_push_one_entry_and_back_drops_the_filter (:275) and test_back_after_the_narrow_rail_s_expand_all_lands_the_reader_s_anchor (:286), tests/unit/test_a_population_key_is_declared.py across() (:414), localStorage.removeItem + comment in tests/unit/test_op_and_duration_meet_on_durations.py _LOOK (:49-50) and tests/unit/test_print_and_find_reach_the_content.py _FOLD (:128-129); new tests/unit/test_a_browser_drive_starts_clean.py.
Guard:     test_a_browser_drive_starts_clean.py - in one worker's shared Chrome, drive 1 sets bga.copy-format and pushes 60 entries; drive 2 reads history.length <= 2 and localStorage.length == 0 (prototype: now 50 / "markdown"; reset 2 / null).
Mutation:  delete the resetNavigationHistory line -> history.length 50, red; delete the one-shot clear -> "markdown", red; survivor check for the retirements: with both removeItem lines gone, run test_op_and_duration_meet_on_durations.py then test_print_and_find_reach_the_content.py in one process (-n0, that order) green, then delete the clear -> JSONDecodeError (911b36d7's red).
Class:     optimization - cuts the catch-up commits these two defects cost round 159 (c31ada8b, 911b36d7: 2 red-then-fix commits); drive cost unchanged, 359.1 vs 359.1 ms median (n=10, scratch/arch160/pdrive.py).
Split:     one track, two commits (UX-1215 then UX-1217), sonnet, mechanical; merges FIRST - UX-1208, UX-1209, UX-1212 guards all Back or touch these files.
Question:  none. Not closed: bookkeeping r152 (Chrome ignores >200 navigations/10 s) - a fresh tab closes it at +167 ms/drive; leave it open.
```

## Outcome

**The gap measured** (`tests/unit/test_a_browser_drive_starts_clean.py`, one Chrome): a drive that stores `bga.copy-format=markdown` leaves `Object.keys(localStorage)` of the next drive `["bga.copy-format"]` before; `[]` after. `911b36d7`'s order reproduced: with both `removeItem` lines gone and the clear deleted, `test_op_and_duration_meet_on_durations.py` then `test_print_and_find_reach_the_content.py` in one process: 1 failed, 28 passed (`JSONDecodeError`, char 0).

**The close measured:**

```text
$ python3 -m pytest -n 4 @browserfiles.txt   (the 124 files naming Browser/find_chrome)
1 failed, 1814 passed, 41 skipped in 393.99s   (the 1: test_every_browser_guard_is_listed, the new file's tiers row, added in this commit)
$ PYTEST_XDIST= python3 -m pytest tests/unit/test_the_tiers_are_a_partition.py -q
17 passed in 3.30s
drive cost, golden, median of 12: 325.0 ms without the clear, 331.0 ms with (+6 ms)
```

Retired: the `localStorage.removeItem("bga.copy-format")` lines in `test_op_and_duration_meet_on_durations.py` `_LOOK` and `test_print_and_find_reach_the_content.py` `_FOLD`. Nothing else in the browser set depended on the leaked state.

| Mutation | Red | Count |
| --- | --- | --- |
| one-shot clear's source replaced by `void 0;` in `tests/cdp.mjs` | `test_a_drive_after_a_stored_preference_reads_an_empty_storage` (golden, macro_micro) | 2 failed |
| same mutation, both `removeItem` lines retired, two files in one process | `test_copy_takes_every_row_the_fold_holds_and_never_the_stub` (`JSONDecodeError`) | 1 failed, 28 passed |

**Deviation:** the Acceptance Test asked for a per-test fixture census of `bga.` keys; the architect's route clears at the driver, so no guard can leave one behind for the next drive and a crashed drive skips no teardown. `fresh_history` stays an accepted, ignored keyword on `Browser.measure` (a sibling track may still pass it); the orchestrator removes it. The `tests/tiers.py` MEDIUM row for the new file is in this commit because the browser-guard partition test is red without it; UX-1215's commit alone lacks it.
