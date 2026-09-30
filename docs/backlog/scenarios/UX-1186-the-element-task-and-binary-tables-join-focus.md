# UX-1186: the element, task and binary tables join Focus, Inspect and the jump box

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-1182 | **Found by:** the round-157 data-exploration review (`/mnt/project-files/view-ui-review/data-exploration/review.md`) of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`, Plane 2 rewritten by heavy.py to 5,849 processes and at most 81 binaries per element) at `cbc739b0`, Chromium 1440x900 and 390x844 | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_a_population_key_is_declared.py`

## Motivation

Finding: 4 of the review.

The elements table (1,202 rows), the task table, `binary_cost` and `by_binary` carry 0 `a.inspect` and 0 `tr[data-element]`; the page's 96 keyed rows are all in 6 small sections (headline 3, critical path 22, horizon 5, bottleneck 51, sensitivity 5, batch 10). Focus on `layer12/mod030` leaves 4 sections undimmed and collapses the elements table. The jump box answers "Nothing matches" for `gperf`, `python3` and `cc`. A card's "Also in" names 3 sections and never the element, task or binary tables. Breaks `UX-208`'s rule that a declared element column earns every row a generic Inspect. No `dl` on the page exceeds 19 pairs (`confidence`), and every population map already renders as a two-column table; what they lack is a declared key.

## Decomposition

Input classes: the 1,202-element two-plane page, the heavy-binary page (`UX-1182`'s, heavy.py's until it lands), `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

Rule, "a population's key column is declared": a table keyed by element, task or binary declares that column (`bga:keyed_by`), so every row carries `data-element` or `data-binary`, an Inspect link, Focus membership and a jump-box entry. Declare the key in `bga/viewer/pairs.js` and `elementSignalTable`; map a task to its element for `KEYED_BY_TASK_UID`; add a `binary` kind to `jumpTargets`; Focus dims such a table's other rows rather than collapsing it. Per D2, a `dl` stays for at most 40 (`TABLE_OPENS_BOUNDED_ABOVE`) scalar pairs about one subject; a map keyed by a population is a table with a declared, linked key column whatever its length, and never unrolls into a `dl`. The rule lands in `docs/design/styleguide.md` §1 and §3k.

## Decision

Owner (Ruslan, 2026-09-30 19:04 ("your defaults looks good to try")), D2: a `dl` stays for up to 40 scalar pairs about one subject. Any population map becomes a table with a declared, linked key column, whatever its length. There is no unrolling into a `dl`. Class: product.

Architect (round 158, group B):

```text
Route:     reuse `role: "element"` (the mechanism `buildTable` already reads, structured.js:691-705) and add `role: "binary"`: `elementSignalTable`'s `element` column gets `role: "element"` (pairs.js:123); `mapSectionLabels` maps a `KEYED_BY_TASK_UID` row to `data-element = taskUid(raw).element` with the Inspect link, and a map declaring `bga:keyed_by: "binary"` (by_binary, binary_cost in bga/schemas.py) sets `data-binary`; `jumpTargets` (nav.js:897) adds a `binary` kind read from the payload's binary-keyed maps, not the DOM (the DOM holds 25 of 1,202 rows); `applyFocus` (focus.js:33) dims a keyed table's other rows and never sets `data-unfocused` on its section. D2's rule (a `dl` for at most 40 scalar pairs about one subject; a population map is a table with a linked key) lands in styleguide §1 and §3k.
Rejected:  a new `bga:keyed_by` column-level hint beside `role` - two declarations for one fact; `jumpTargets` from `[data-element]` in the DOM only - misses every row past the bound.
Files:     bga/viewer/structured.js (buildTable key block 691-705: `role` element|binary); bga/viewer/pairs.js (elementSignalTable hint only); bga/viewer/sections.js (mapSectionLabels key loop); bga/viewer/nav.js (jumpTargets); bga/viewer/focus.js (applyFocus); bga/viewer/style.css (a dimmed row in a focused table); bga/schemas.py (`bga:keyed_by: "binary"` on by_binary and binary_cost); bga/schema_hints.py if the keyed_by vocabulary is enumerated there; docs/design/styleguide.md (§1, §3k); tests/unit/test_a_population_key_is_declared.py (new); tests/tiers.py.
Guard:     test_a_population_key_is_declared.py - per table declaring a key, mounted rows with the data attribute == mounted rows; Focus never collapses such a table; the jump box finds a binary on UX-1182's page.
Mutation:  drop `role: "element"` from `elementSignalTable`'s element column; the guard reds.
Class:     product.
Split:     second in track B2, after UX-1184 (same function, mapSectionLabels). Depends on UX-1182 (guard page).
Budgets:   page +~1,500 B; controls +1 `a.inspect` per mounted keyed row: ~+25 each on elements, wall_clock_share_us, binary_cost, by_binary on xl_both = +75 to +100, and on macro_micro +71 on binary_cost once UX-1185 unrolls it - neither fits (see Question); height 0; words +1 per row if the glyph counts as a word (+~100 on macro_micro).
Overlap:   UX-1183 (group A) edits binary_cost's schema node (adds `wall_us`) - same dict in bga/schemas.py, merge UX-1183 first; UX-1187 edits `_ELEMENT_PRESETS`/the elements table's columns (pairs.js presetTable, schemas.py) - not elementSignalTable, but the same table: UX-1187 keeps `role: "element"`. UX-1188's new element_deltas table should declare `role: "element"` itself.
```

Taken, four corrections. (1) One declaration per population table, `bga:keyed_by`: a map names what its keys are (`task_uid`, `binary`), a list names its key columns; `buildTable` turns either into the column's existing `role`, and the table carries `data-keyed-by`, which Focus reads. So `elementSignalTable` declares `KEYED_BY_ELEMENT` in its hint, not `role` on its column, and the `role: "element"` tables (critical path, horizon) keep folding under Focus as before. (2) `binary_cost` takes one line, `KEYED_BY: [KEYED_BY_ELEMENT, KEYED_BY_BINARY]` after `RAIL`, clear of the `COLUMNS`/`items` that `UX-1183` edits. (3) A binary row carries `data-binary` and no Inspect link: no binary card exists to inspect, and a link to nowhere breaks `UX-194`; the jump box lands a binary on its row, or on its section when no row is mounted. (4) A keyed map is always a table (`renderSection`): `golden`'s `wall_clock_share_us` (4 tasks) and the 1,202-element page's `by_binary` (1 binary) were `dl`s. `style.css` is untouched: `[data-dimmed]` is already styled. The card's "Also in" (Motivation) is not in the Required Fix and is left.

## Out of Scope

The pager (`UX-1185`); the binary membership itself (`UX-1183`).

## Acceptance Test

`tests/unit/test_a_population_key_is_declared.py`: for every table whose schema declares `bga:keyed_by`, mounted rows with the data attribute equal mounted rows, Focus never collapses such a table, and on `UX-1182`'s page the jump box finds a binary. Mutation: drop the declaration on `elements`; the guard reds.

## Outcome

**Gap measured.** The new guard on the base tree (`78d7be67`, `UX-1182`'s page), `PYTEST_XDIST= python3 -m pytest tests/unit/test_a_population_key_is_declared.py`:

```text
E   AssertionError: ('golden', [])                                  no table declares a key
E   AssertionError: ('golden', [['wall_clock_share_us', 1]])        a task map drawn as a dl
E   AssertionError: {'tables': [], ...}  assert None == 'BINARY'     jump box: no binary
3 failed, 2 passed    (the row and Focus clauses pass vacuously: no keyed table to read)
```

**Close measured.** Same command on this commit: `5 passed in 5.21s`. Keyed rows / mounted rows, each table: `golden` `wall_clock_share_us` 4/4, `elements` 4/4; `macro_micro` 11/11, `binary_cost` 25/25 (element and binary), `by_binary` 11/11, `elements` 11/11; heavy page 25/25 each. Focus on an element no mounted `elements` row holds folds none of them; the jump box offers `exponential-032` (1 call, not mounted) under BINARY and lands on `#by_binary`. A card's "Also in" gains the three tables (`element-core-bst`: +25 words). Budgets, opened at 1440, `UX-1184`'s commit -> this:

```text
page half (golden, macro_micro)   144,384 -> 145,048 B   (+664; track +848 over 78d7be67)
golden        height 19,024 -> 19,248   words  7,661 ->  7,671   controls 372 -> 390
macro_micro   height 36,788 -> 37,172   words 12,414 -> 12,673   controls 662 -> 740
xl_both       height 41,864 -> 42,005   words 12,334 -> 12,348   controls 887 -> 965
```

xl_both's 965 controls is over the 4,100 class's 900: `test_the_page_has_a_volume_budget.py::test_the_whole_page_is_bounded_too[xl_both]` is red on this commit. The bound is not touched (owner, 19:26: raised once at the merge by the measured need); the need is +78 here, +79 over `78d7be67`.

| mutation | reddened | count |
|---|---|---|
| drop `[KEYED_BY]: KEYED_BY_ELEMENT` from `elementSignalTable` (`pairs.js`) | `test_the_populations_declare_their_key` | 1 failed, 4 passed |
| Focus drops the `table[data-keyed-by]` clause (`focus.js`) | `test_focus_dims_a_keyed_table_and_never_folds_it` | 1 failed, 4 passed |
| `jumpTargets` skips every keyed table (`nav.js`) | `test_the_jump_box_finds_a_binary_off_the_page` | 1 failed, 4 passed |
| a keyed map classified by size again (`sections.js`) | `declare_their_key`, `a_keyed_map_is_never_a_dl` | 2 failed, 3 passed |
| the task relabel drops the Inspect link (`sections.js`) | `test_every_mounted_row_carries_its_key` | 1 failed, 4 passed |
| no `data-binary` on a row (`structured.js`) | `test_every_mounted_row_carries_its_key` | 1 failed, 4 passed |

Re-based: `test_the_jump_box_offers_what_it_knows.py`'s empty palette gains `binaries: []`; `test_the_mapping_is_law.py`'s task key label strips the trailing Inspect glyph and asserts the row's `data-element`; `test_every_skip_reason_is_declared.py`'s `UNRESOLVABLE` 81 -> 82 (this guard's `NO_BROWSER` skip).
