# UX-1215: a Back-pushing browser guard runs on a fresh history

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the round-159 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** guards | **Area:** tests | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_a_browser_drive_starts_clean.py`

## Motivation

Page: the round-159 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `31b5971b`, Chromium 1440x900 and 390x844.

Root cause of `c31ada8b`: Chrome caps a tab's session history at 50 entries, and the worker's shared tab carries every earlier test's pushes, so a guard's own pushState entries are pruned and Back lands elsewhere. Two guards now opt in to `fresh_history` (`test_the_rail_tools_and_the_pager_read_as_one_set.py`, `test_a_population_key_is_declared.py`); others that push more than once before Back, e.g. `test_filter_and_back_state_is_kept_and_told.py` and `test_the_rail_takes_a_step.py`, are exposed.

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

Every browser guard that presses Back after more than one push runs on a fresh history, or the shared tab starts each test fresh.

## Out of Scope

Chrome's cap itself.

## Acceptance Test

A census guard names every test file that calls history Back and asserts it uses `fresh_history`; removing the opt-in from one reddens it. Mutation: restore the defect, and the guard reds.

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

**The gap measured** (`tests/unit/test_a_browser_drive_starts_clean.py`, one Chrome, golden): a drive that pushes 60 entries leaves the next drive reading `history.length` 50 (the cap) before; 2 after.

**The close measured:**

```text
$ PYTEST_XDIST= python3 -m pytest tests/unit/test_a_browser_drive_starts_clean.py tests/unit/test_the_rail_tools_and_the_pager_read_as_one_set.py tests/unit/test_a_population_key_is_declared.py -q
34 passed in 87.50s
```

Both `fresh_history=True` call sites are retired. `Browser.measure` keeps `fresh_history=None` as an accepted, ignored keyword so a sibling track's new guard that still passes it does not break; the orchestrator removes it once none do.

| Mutation | Red | Count |
| --- | --- | --- |
| delete `await send("Page.resetNavigationHistory")` from `tests/cdp.mjs` | `test_a_drive_after_sixty_pushes_reads_a_history_of_its_own` (golden, macro_micro), next drive reads 50 | 2 failed |

**Deviation:** the Acceptance Test asked for a census of Back-callers asserting `fresh_history`; the architect's route makes the mistake impossible in the driver instead (every drive resets), so the guard is behavioural, not a census. `tests/tiers.py` is the orchestrator's: the new browser file needs its MEDIUM row.
