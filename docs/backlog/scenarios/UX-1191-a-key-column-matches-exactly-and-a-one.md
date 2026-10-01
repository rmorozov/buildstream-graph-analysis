# UX-1191: a key column matches exactly, and a one-op task table says its op once

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-1182 | **Found by:** the round-157 data-exploration review (`/mnt/project-files/view-ui-review/data-exploration/review.md`) of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`, Plane 2 rewritten by heavy.py to 5,849 processes and at most 81 binaries per element) at `cbc739b0`, Chromium 1440x900 and 390x844 | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** test_a_key_column_matches_exactly.py

## Motivation

Finding: 9 of the review.

1,202 of 1,202 tasks are BUILD, yet the op badge is drawn on every row, where §3d asks for one sentence; there is no op facet. The filter is substring-only: `cc` matches 1,201 rows in `binary_cost`, including `gcc` and `cc1plus`, and `ld` cannot be isolated. Controls: 902 on this page against a 900 bound (909 on the heavy page), so any new input has to replace one.

## Decomposition

Input classes: the 1,202-element two-plane page, the heavy-binary page (`UX-1182`'s, heavy.py's until it lands), `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

Rule, "a key column filters exactly": a declared key column (element, binary, op) offers an exact or prefix match beside the substring box, for example `binary:ld`; a one-value op is stated once. Priced by folding the per-column thresholds into the one filter grammar (`> 5s`), -2 to -3 controls per table, so the page's control count falls.

## Decision

Class: product.

### Architect's section (round 158)

```text
Route:     one filter grammar in the box, parsed by a new `parseQuery` in tables.js: `<column>:<value>` is exact on a declared key column (element, binary, op; the column is found by its `role`/`bga:keyed_by` or its head's text, so it does not wait on UX-1186's code), `<column> > 5s` folds the per-column thresholds in, a bare word stays substring; the `th-filter` inputs (structured.js:896-947) go; a one-value op is said once by a new `statedOp(box)` in sections.js, called at the end of `mapSectionLabels`.
Rejected:  add an exact-match checkbox beside the box - +1 control per table on a page already at 886/900; keep the per-column threshold inputs beside the grammar - two ways to say `> 5s`, and the controls they hold are what pays for UX-1190's buttons.
Files:     bga/viewer/tables.js (parseQuery new, applyFilters line 198 needle test); bga/viewer/structured.js (interrogable: box placeholder/aria, threshold block removed); bga/viewer/sections.js (relabelHead loses the th-filter detach; statedOp new; one call line in mapSectionLabels); bga/viewer/shapes.js (:282 reads `.th-filter`); bga/viewer/viewstate.js (captureView/applyView: thresholds become the box's text); bga/viewer/style.css (drop `th .th-filter` rules 815-822); docs/design/styleguide.md (§3d grammar); tests/unit/test_a_key_column_matches_exactly.py (new); tests/tiers.py; retire tests/unit/test_a_capped_table_filters_what_it_sorts.py (UX-835's "every quantity column carries a th-filter") and rewrite the th-filter drives in test_filter_and_back_state_is_kept_and_told.py, test_tables_you_can_interrogate.py, test_the_tools_scale_with_the_table.py, test_pointer_travel_is_a_budget.py.
Guard:     test_a_key_column_matches_exactly.py - `binary:ld` on UX-1182's page returns the `ld` rows only; `duration > 60s` on the task table equals the old threshold's rows; the one-op task table states its op once; page controls do not rise.
Mutation:  `binary:` matches by substring; the guard reds. Retirement: in the survivor, make `parseQuery` ignore one declared quantity column; the `> 60s` clause reds - covering what UX-835's guard held.
Class:     product.
Split:     last in track B1 (after UX-1190, whose header button shares the `th`); guard waits on UX-1182's page (group A).
Budgets:   page ~-300 B net (grammar +~900, threshold block and its CSS -~1,200); controls: -1 per filtered quantity column, estimate -20 to -30 on xl_both; height: -~30 px per filtered table head (the block input row), estimate -250 to -400 px on xl_both; words: -~25 per one-op task table (the per-row BUILD qualifier).
Overlap:   one line in `mapSectionLabels` (track B2's function): merge B2 first. UX-1187 (group C/A) makes level "a filterable column" - it should use this grammar (`level:3`), so UX-1187 follows UX-1191 or files that half as a follow-up.
```

### Where the route was wrong

```text
1. The th-filter controls it pays with are 9 on xl_both, not 20-30: one per numeric quantity column
   of a table past the row cap, and xl_both has 7 such tables (measured, below).
2. `binary:ld` cannot be the heavy page's clause: heavy_binary_run publishes no `ld` (601 names,
   `make` and `constant-NNN`-style). The guard holds `binary:ld` on macro_micro, and the exact-vs-substring
   discrimination on the heavy page with `binary:constant-29` (0 rows exact; its `*` prefix and a substring match the `constant-29N` rows).
3. `name:value` is exact on any named column, not only the three key roles: `level:3` (UX-1187) needs
   no second grammar. `op:` and `element:` read a task uid's parts.
4. A threshold on a column with no numbers is refused on the page (UX-349's rule survives the
   inputs it was written for); the strip's click writes `>= N` into the box (event `bga:threshold`).
5. Old links: `t.<table>.<column>` folds into the box's text on apply; capture writes `f.` only.
```

## Out of Scope

The key declaration (`UX-1186`); the threshold semantics themselves.

## Acceptance Test

`tests/unit/test_a_key_column_matches_exactly.py`: `binary:ld` on `UX-1182`'s page returns the `ld` rows only, the one-op task table states its op once, and the page's controls do not rise. Mutation: make `binary:` a substring match; the guard reds.

## Outcome

**Gap measured** (`HEAD` 9e9ef410, `tests.pages` builders, Chromium 1440x900, every chapter open;
scratch `measure.py`): header threshold inputs `input.th-filter` and per-row `.task-qualifier`:

```text
page         th-filter  qualifiers  controls  nodes  words   height  page half
golden               0           4       378   2707   7756    19277    148,380
macro_micro          4          11       792   6814  13102    38483    148,380
heavy               12          25       940   8100  13476    41920    148,382
xl_both              9          25      1007   7487  12717    43933    148,382
1,202 (w60)          9          25      1030   7267  12643    42199    148,382
```

`binary:ld` in macro_micro's `binary_cost` box was a substring over the row text; `cc` on the
review page matched every `cc1plus` row. golden's 4 qualifiers are a mixed-op table (3 BUILD, 1 FETCH).

**Close measured** (same instrument, this commit):

```text
page         th-filter  qualifiers  controls  nodes  words   height  page half
golden               0           4       378   2707   7756    19277    149,663
macro_micro          0           0       788   6800  13094    38484    149,663
heavy                0           0       928   8064  13454    41593    149,665
xl_both              0           0       998   7454  12695    43751    149,665
1,202 (w60)          0           0      1021   7234  12621    42017    149,665
```

xl_both: controls -9, nodes -33, words -22, height -182 px; page half +1,283 B. At 390 every table
filter's placeholder fits its box (widest `filter, element:…, > 10`, 149 of 174 px on heavy).
`PYTEST_XDIST= python3 -m pytest tests/unit/test_a_key_column_matches_exactly.py -q`: `7 passed in 7.44s`.
The 82 files naming the touched modules plus the budget/register/guard-line guards, single process:
`2634 passed, 21 skipped` before the four re-bases below, then `63 passed` on those four files.

**Mutation table** (`mutate.py`, each from a pristine copy, `PYTHONDONTWRITEBYTECODE=1`):

| Mutation | Reddened | Run |
|---|---|---|
| `matchesKey`: `got === value` -> `got.includes(value)` | `test_a_key_value_matches_that_column_exactly` | 1 failed, 6 passed |
| `parseQuery` ignores `cpu_us` (UX-835's retired claim) | `test_a_threshold_is_the_box_s_own_grammar` | 1 failed, 6 passed |
| `unread.hidden = true` | `test_an_unreadable_threshold_says_so_and_filters_nothing` | 1 failed, 6 passed |
| `statedOp` never returns an op | `test_a_one_op_task_table_says_its_op_once` | 1 failed, 6 passed |
| placeholder `filter rows by any text, …` | `test_the_placeholder_fits_its_box_at_390` | 1 failed, 6 passed |
| an `input.th-filter` appended to a `th` | `test_no_head_carries_a_filter_of_its_own` | 1 failed, 6 passed |
| restored | - | 7 passed |

**Deviation.** Retired `test_a_capped_table_filters_what_it_sorts.py` (UX-835; its Guard line now
`none — retired by UX-1191`, its tiers row dropped, styleguide §7's §3d row repointed). Re-based:
`test_filter_and_back_state_is_kept_and_told.py` (the unmet threshold typed into the box),
`test_the_shape_before_the_rows.py` (the strip's click lands in the box),
`test_the_tools_scale_with_the_table.py` (the boolean clause reads the box's refusal; the page-level
`TestAThresholdGoesWhereANumberIs` retired, nothing left to enumerate), `test_the_palette_is_validated.py`
(`.table-filter.unparsed`), `test_a_new_control_class_lands_declared.py` (row dropped),
`test_the_mapping_is_law.py` (`el-1201.bst`, no per-row BUILD), `test_pointer_travel_is_a_budget.py`
(J4 loses the column-filter hop and picks a table whose box takes a threshold; all four J4 budgets
lowered, 3 runs, spread 0). UX-1180's unreadable-threshold clause and UX-1178's placeholder clause are
held here. `tests/tiers.py` carries the new file's MEDIUM row (brief).
