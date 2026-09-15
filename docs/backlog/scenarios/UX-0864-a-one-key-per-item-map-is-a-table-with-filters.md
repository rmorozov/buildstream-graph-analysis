# UX-864: a one-key-per-item map is a table with filters

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-419, UX-526 | **Found by:** round 120, the user (a 16-core, 32 GB host, `--builders 16 --jobserver auto`) | **Serves:** R2 (find one binary or one task among a thousand) | **Topic:** viewer | **Area:** bga-viewer | **Shape:** mechanical

## Motivation

`renderSection` (`bga/viewer/sections.js`) sends every object value
to `renderPairs` without classifying it; `by_binary` and
`wall_clock_share_us` - one key per binary, one per task - render as a
definition list of a thousand rows with a show-all button and no filter
or sort. The styleguide's own row says a one-key-per-element map is a
table, `shapes.js` returns `CONTROLS.MAP_TABLE` for exactly this shape,
and no renderer reads it; `renderStructured` already routes the same
shape to `mapTable` one level down.

## Required Fix

`bga/viewer/sections.js`: the object branch calls `classify()` and
routes `MAP_TABLE` through `mapTable`/`buildTable` with the filter, sort
and top-N tools the blast table has; small keyed objects keep the pairs
pattern per the styleguide's threshold.

## Decomposition

Input classes: a map of 3 keys (pairs), of 40 (table), of 1202 (table,
top-N); the journey it extends is R2 finding one binary in the census.

## Out of Scope

Nested maps; the schema.

## Acceptance Test

`tests/unit/test_the_mapping_is_law.py` gains: `by_binary` and
`wall_clock_share_us` render a table with a filter input and sortable
headers; mutation: route back to `renderPairs` - red.

## Outcome (round 121) — 🟢 Done

### The gap, measured

`renderSection`'s object branch called `renderPairs` unconditionally.
A 41-key `by_binary` map and a 1,202-key `wall_clock_share_us` map,
rendered through the shim (`tests/dom_shim.mjs`): `hasTable: false`,
`hasFilter: false`, `sortable: []` on both - a `<dl>`, any population.

### The close, measured

```text
$ python3 -m pytest tests/unit/test_the_mapping_is_law.py::TestAOneKeyPerItemMapIsATable -v
test_forty_one_binaries_render_a_table_with_filter_and_sort PASSED
test_twelve_hundred_tasks_render_a_table_with_filter_and_sort PASSED
test_a_three_key_object_still_renders_pairs PASSED
test_an_empty_map_renders_without_error PASSED
4 passed in 2.82s
```

`by_binary` (41 keys, past `TABLE_OPENS_BOUNDED_ABOVE=40`): table,
headers `["Binary", "Count"]`, sortable, filtered. `wall_clock_share_us`
(1,202 keys, `bga:keyed_by: task_uid`): headers `["Task", "Duration"]`,
filtered, sortable; row identity survives - first cell "el-1201.bst
BUILD" (element + `renderPairs`'s own qualifier span), `data-key`
"el-1201.bst|BUILD|BUILD|0". A 3-key object still renders a `<dl>`; an
empty map renders without error. Gate: `node?.additionalProperties &&
!node?.properties` - `classify`'s `MAP_TABLE` fires past 4 entries on
any object, but a **record** (`attribution`, eight more) is not "one
key per element"; confirmed against `bga/schemas.py` - only `by_binary`
and `wall_clock_share_us` qualify among `analyze/v6`'s top-level keys.

`make test-touching`: 1743 passed, 9 skipped. `make lint`, `dev_sizes.py
--check`, `dev_baseline.py --check`: clean.

### Mutation table

| Guard | Mutation | Reddened | Count |
|---|---|---|---|
| `TestAOneKeyPerItemMapIsATable` | `isMap` forced `false` (route back to `renderPairs`) | `test_forty_one_binaries_render_a_table_with_filter_and_sort`, `test_twelve_hundred_tasks_render_a_table_with_filter_and_sort` | 2 failed, 2 passed |

Reverted from the pre-mutation copy (`falsify` step 1); re-ran green.

### Deviation from the Required Fix

Undeclared surfaces, both forced by macro_micro's `by_binary`/
`wall_clock_share_us` being 11 keys each - past the 4-key threshold, so
both switch shape on the committed fixture:

- `test_a_task_uid_is_not_a_label.py`'s `TestOnTheRealPage`: `<dt>` ->
  `td[data-column="key"]`; same three assertions - 6 passed.
- `test_the_report_you_can_attach.py`'s size budgets: +1,531 B source
  on both fixtures (measured on identical scratch paths - no content
  moved). `PAGE_BUDGET_B` 325,000→328,000, macro_micro 528,000→531,000,
  golden unchanged (474,000, 4,401 B under) - 32 passed.

Round 2, after the full suite reached four more the touching sweep
did not select (`make test`, fixed on the branch commit `e9977d9b`):

- `test_a_shapeable_population_is_drawn.py`'s `drawn` selector matched
  `columnStrip`'s **annotation**-grade shape too, which every quantity
  column now carries (`distributionStrip`); `RANKED_MAP` says that is
  not a sixth instrument. Narrowed to `data-grade="exhibit"`.
- `structured.js` crossed the 1,500-line ceiling (1,511) with the
  header/noun/`data-key` pass. Moved to `sections.js` as
  `mapSectionLabels`, beside `mapTable`'s only caller; `mapTable`'s own
  body is byte-identical to `ede1ce6f`'s. 1,477 lines.
- `test_the_page_keeps_the_names_it_was_given.py`'s `_LOOK` read
  `dt`/`.pair-key` only. A table's key cell now carries `data-key` too
  (`describedTerm`'s own rule); `_LOOK` gained a third clause reading
  it the same way, first child only.
- `test_a_capped_table_filters_what_it_sorts.py` (§3d): the relabel
  above wiped `interrogable`'s `input.th-filter` on `value` too -
  fixed by detaching it first, relabeling, then reattaching.

Deviation (merge): the verifier passed it and found the gate's record
clause (`!node?.properties`) dead against every shipped section, so
the session added a case at merge (eight named members beside a
catch-all render as pairs; mutation red, 1 of 5); the full suite then
reached the three guards above, fixed by the track in a second round.
