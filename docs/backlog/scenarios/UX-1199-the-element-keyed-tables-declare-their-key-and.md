# UX-1199: the element-keyed tables declare their key, and by_binary, binary_cost and serial_chains rank and name their quantity

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the round-158 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer, bga/schemas | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_a_population_key_is_declared.py` (`TestAListKeyedTableAndARankAreDeclared`)

## Motivation

Page: the round-158 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `43397b70`, Chromium 1440x900 and 390x844.

leaf_analysis.leaves_detail: 40 rows of element uids, key header "Key", 0 a.inspect, 0 data-element, not declared keyed, under "Each leaf, keyed by its element uid."; consolidation_candidates (27) and parallelism levels likewise: Focus does not dim them, Jump does not index them. by_binary's "Count" is calls (lognormal-308 = 71; binary_cost has 31 element rows), it opens "Top 25 by By binary" and "By binary 13 to 1200", and has no element link. binary_cost opens "Top 25 by Calls" tied at 3, in payload order, not CPU. serial_chains offers Rank as a quantity, so Top 10 shows ranks 40-31 (walk N12, N11, N15, VERIFY-1).

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

leaves_detail, consolidation and levels declare their element key; by_binary names its count Calls, titles its rank by it and links a binary to its elements; binary_cost opens by CPU; Rank is not a Top-N quantity.

## Decision

Class: product.

Architect (round 159, group A, track T2):

```text
Route:     leaves_detail stops being a table of its own: its two fields join the element table's Leaves view (keyed by
           construction; the element card already shows both, element.js l.297); consolidation and levels declare their
           element-list column keyed, which marks each row `data-elements` (an attribute, no anchor) and Focus reads it;
           by_binary's value is titled Calls from the schema and each binary that binary_cost holds links to its rows
           there; binary_cost's columns put CPU first, so it opens ranked by CPU; serial_chains' rank declares no quantity.
Rejected:  key leaves_detail in place - measured +40 controls / +40 nodes on xl_both (1,038 of 1,020 controls), over;
           an Inspect link per element in a list cell - consolidation alone is 75 rows of 2-3 uids on xl_both;
           a `bga:rank` hint for binary_cost - the column order is already the opening rule, so data, not a hint.
Files:     bga/schemas.py (`_ELEMENT_PRESETS` "Leaves": + is_potentially_deferrable, deferral_risk; consolidation_candidates
           l.2566 and parallelism.levels items: KEYED_BY element on `elements`; serial_chains rank l.2290 drops "quantity";
           binary_cost COLUMNS l.4834: cpu_us, cpu_share before calls; by_binary l.4825 additionalProperties title "Calls");
           bga/viewer/pairs.js (`elementSignalTable`/`renderPairs`: join leaf_analysis.leaves_detail like element_join);
           bga/viewer/sections.js (`FIELDS_DRAWN_ELSEWHERE`: leaf_analysis.leaves_detail, with one line naming the Leaves
           view; `mapSectionLabels`: the value head reads the schema title; by_binary's key cell links to binary_cost
           through `filterSection`, only where the payload's binary_cost has the binary); bga/viewer/structured.js
           (`mapTable`: the value spec takes additionalProperties.title, so the Top-N label and the strip say Calls;
           `buildTable`: a keyed list column writes `data-elements`); bga/viewer/focus.js (`applyFocus`: dims a row whose
           `data-elements` lacks the uid). Re-point tests/unit/test_every_table_has_its_own_state_key.py (it pads
           leaves_detail as its nested table) and check tests/unit/test_one_table_many_views.py l.366.
Guard:     tests/unit/test_a_population_key_is_declared.py: on the walk page Focus dims consolidation and levels rows and
           the Leaves view rows; by_binary's head reads Calls; heavy's binary_cost first row is its CPU maximum (derived
           from the payload); serial_chains' Top 10 holds ranks 1-10; no leaves_detail table is drawn.
Mutation:  drop KEYED_BY from consolidation_candidates - Focus leaves its rows undimmed, red; put calls back first - row 1
           is payload order, red.
Class:     product.
Split:     T2, second (after UX-1194 in mapSectionLabels and schemas.py).
Budget:    measured: by_binary links +9 controls on macro_micro (collect2, uname have no binary_cost rows), +25 on heavy, +1
           on xl_both; the leaves trade -10 controls / -383 nodes on xl_both, -1 / -19 on macro_micro. Page half ~+0.5 KB.
Question:  none. Deviation: leaves_detail answers "keyed" as the element table's Leaves view, not as a keyed table of its own.
```

Taken, with four changes. by_binary's value is titled "Calls in run", not "Calls": `UX-1184`'s guard holds one title per field and binary_cost's per-element `calls` is already "Calls". A list column keys its row through a new `bga:keyed_by` value, `elements` (`KEYED_BY_ELEMENTS`, the column's own name, as `UX-1186` reads a list's key); `buildTable` writes `data-elements` from the row's list. serial_chains' Total moves ahead of Length, so with Rank no longer a quantity the opening and Top 10 rank by Total, which is the order Rank states; Rank enters `test_every_number_says_what_it_is.py`'s `UNDECLARABLE` as an ordinal. "Jump indexes" needed no change: the jump box already lists every element uid from the payload (`UX-1179`). The guard extends `test_a_population_key_is_declared.py`, the file the Acceptance Test names.

## Out of Scope

The keyed tables `UX-1186` declared.

## Acceptance Test

Each named table is keyed (Focus dims, Jump indexes), by_binary's header reads Calls, binary_cost's first row is its CPU maximum, serial_chains' Top 10 is ranks 1-10; a guard in `test_a_population_key_is_declared.py`. Mutation: restore the defect, and the guard reds.

## Outcome

### The gap, measured

```text
1481cb27 (UX-1194), Chromium 1440x900; walk = two_plane_run --layers 20 --width 60 (1,202), heavy = heavy_binary_run (114):
  leaf_analysis draws table leaf_analysis.leaves_detail (walk 150 rows, heavy 13), key head "Key"
  consolidation_candidates keyed-by null, rows with data-elements 0 of 27 (walk) / 0 of 2 (heavy)
  levels keyed-by null, data-elements 0 of 22 (walk) / 0 of 10 (heavy)
  by_binary heads ["Binary", "Count"], "Top 25 by By binary", key links 0 of 25 (heavy)
  binary_cost (heavy) "Top 25 by Calls", row 1 exponential-397 3 calls 455 ms CPU
  serial_chains options "Top 10 by Rank", "Top 25 by Rank", ...
```

### The close, measured

```text
this commit, same pages:
  no leaves_detail table; Leaves view heads end "Is potentially deferrable", "Deferral risk"
  consolidation keyed-by "elements", data-elements 27 of 27 / 2 of 2; levels 22 of 22 / 10 of 10
  Focus on consolidation row 1's first element: the rows that lack it dimmed, the rows that hold it not
  by_binary heads ["Binary", "Calls in run"], "Top 25 by Calls in run", links 25 of 25 (heavy), 9 of 11 (macro_micro)
  binary_cost (heavy) "Top 25 by CPU", row 1 lognormal-323 2.2 s = max cpu_us
  serial_chains options "Top 10 by Total", ...; Top 10 holds ranks 1-10 (walk, heavy)
$ PYTEST_XDIST= python3 -m pytest tests/unit/test_a_population_key_is_declared.py -q
10 passed in 12.64s
volume, opened, 1440x900 (1481cb27 -> this commit):
  xl_both      height 43,503 -> 43,467, words 12,743 -> 12,718, controls 997 -> 988, nodes 7,481 -> 7,087
  macro_micro  height 38,263 -> 38,234, words 13,057 -> 13,049, controls 788 -> 796, nodes 6,813 -> 6,784
  page half 152,253 -> 152,677 B; bga/schemas.py 6,996 lines
```

### Mutations verified red and reverted (8)

| # | mutation | reddened (1 failed, 9 passed each, 12.6-13.0s) |
|---|---|---|
| M1 | `schemas.py`: drop consolidation's `KEYED_BY` | `test_focus_dims_the_list_keyed_rows_that_lack_the_element` |
| M2 | `schemas.py`: `calls` back ahead of `cpu_us` in binary_cost | `test_binary_cost_opens_on_its_cpu_maximum` |
| M3 | `schemas.py`: rank declares `"quantity": "count"` again | `test_rank_is_not_a_top_n_quantity` |
| M4 | `schemas.py`: by_binary value without `title` | `test_by_binary_counts_calls_and_links_what_binary_cost_holds` |
| M5 | `sections.js`: `FIELDS_DRAWN_ELSEWHERE` loses `leaf_analysis` | `test_the_leaves_are_the_element_table_s_leaves_view` |
| M6 | `focus.js`: Focus reads `[data-elements-off]` | `test_focus_dims_the_list_keyed_rows_that_lack_the_element` |
| M7 | `pairs.js`: no leaves_detail join | `test_the_leaves_are_the_element_table_s_leaves_view` |
| M8 | `sections.js`: by_binary links nothing | `test_by_binary_counts_calls_and_links_what_binary_cost_holds` |

Reverted from the saved copy each time: 10 passed.

Re-based in this commit: `test_every_table_has_its_own_state_key.py` pads `utilisation.buckets` (leaves_detail is no longer a table), `test_the_mapping_is_law.py` reads by_binary's head as "Calls in run", `test_every_number_says_what_it_is.py` names `bottleneck.serial_chains.[].rank` in `UNDECLARABLE`.
