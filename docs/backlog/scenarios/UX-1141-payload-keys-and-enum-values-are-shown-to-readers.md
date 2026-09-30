# UX-1141: payload keys and enum values are shown to readers as the label

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the view UI review on a two-plane page (2026-09-29), findings H2, M13 | **Serves:** R1, R2, R5 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_a_reader_sees_labels_not_keys.py`

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14` (114 elements), `bga capture report --json plane2.log` in the newest snapshot, then `python3 -m tools.bga_view <snapshot>/run --export page.html`, booted in Chromium 1440x900 and 390x844 (view UI review, 2026-09-29, `view-ui-review.md` §H2, M13).

Visible on the page: the term "resource_wait_us"; "Diagnosis scheduler_bound"; `#utilisation` rows "idle_no_tasks", "wasted_rebuild" and "INSUFFICIENT_EVIDENCE"; `#confidence`'s one-column "Hard gates" table of six gate ids; "CHAIN_BOUND_RATIO ... in bga/findings.py" in the decision panel; sort pickers "Top 10 by cpu_us". 29 nodes. The wait-category card labels both `category` and `category_us` "Category".

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390. The journey extends a first-time reader's pass over the page.

## Decision

- One map, `READER_LABELS` in `bga/viewer/format.js` (beside `title()`): every enum value and gate id the payload publishes as a *value* (diagnosis, `chain_share_of`, both cores sources, oversubscription evidence, utilisation buckets, the six hard gates, attribution categories, skipped capacity inputs) to a sentence-case phrase; `TERM_LABELS` beside it for the keys whose trimmed title collides with a sibling (`category_us` "Time waiting", `deeper_than_three_share`, `started_at_us`).
- Applied at the choke points, not per section: `renderText` (every string `dd`/`td`, so a map table's key column too), an inline list's items, `title()` for terms; a declared record member in a map table's key column reads `title()`; a Top-N option reads its column's header, not its key.
- `renderProvenance` drops `rule.name` and `rule.module` from the text; both stay on `data-rule`/`data-module` and in the section's JSON door.
- Exempt: `<code>` (a path or command, §4g's existing exception), the published run name, and `T_C` (a floor label - `UX-1144`'s row).
- Guard: `tests/unit/test_a_reader_sees_labels_not_keys.py` - golden, macro_micro and the two-plane 8x14 page, every door open: zero visible text nodes that are a bare `snake_case`/`UPPER_CASE` token, zero Top-N options naming a key, no `dl` with two identical terms. Mutation: `readerLabel` returns its input unmapped.

## Required Fix

An enum value and a gate id render as a sentence-case phrase from one label map; a source constant and file path move behind the JSON door; `category_us` reads as time waiting.

## Out of Scope

The analysis behind the values; other findings of the same review.

## Acceptance Test

Booted in the container: no visible text node is a bare `snake_case` or `UPPER_CASE` token and no `dl` holds two identical terms, booted on the two-plane page. Mutation: restore the finding's shape, and the guard reds.

## Outcome

### The gap, measured

Every door open (`tests.pages.OPEN_EVERY_DOOR_JS`), visible text nodes
that are a bare `snake_case`/`UPPER_CASE` token, outside `<code>`, the
run name and `T_C`; `dl`s with a repeated term; at 1440x900:

```text
page                     bare-token nodes   repeated dt
two-plane 8x14 (114 el)  20                 Category, Deeper than three
golden                   17                 Category, Deeper than three
macro_micro              31                 Category, Deeper than three, Started at
```

Two-plane: `CHAIN_BOUND_RATIO` x3, `OPPORTUNITY_FLOOR_PCT`,
`resource_wait_us`, `scheduler_bound`, `task_horizon`, 4 buckets,
`detected_host_cpu_count`, `INSUFFICIENT_EVIDENCE`, `host_cpu_count`,
6 gate ids. macro_micro adds record keys in map tables (`cpu_model`,
`hit_share`, `projected_us`, ...) and `native_max_jobs`.

### The close, measured

```text
$ PYTEST_XDIST= python3 -m pytest tests/unit/test_a_reader_sees_labels_not_keys.py -q
9 passed in 4.33s
```

Same probe after: 0 / 0 / 0 bare-token nodes, no repeated term. Hard
gates read "Ordering: no violations" ...; the rule line reads
"Threshold `headline.chain_share < 0.9`"; Top-N reads "Top 10 by Wall
clock share".

### Mutations verified red and reverted (3)

| # | mutation | reddened |
|---|---|---|
| A1 | `readerLabel` returns its input unmapped | `test_no_visible_text_node_is_a_bare_key` [golden, macro_micro, two_plane], 3 failed |
| A2 | Top-N option back to `${column}`; `title()` skips `TERM_LABELS` | `test_no_top_n_option_names_a_key` [macro_micro, two_plane], `test_no_list_repeats_a_term` [x3], 5 failed |
| A3 | `renderProvenance` prints `rule.name` again | bare-key [x3] and `test_each_block_names_its_rule_and_where_it_lives` [x2], 5 failed |


Re-based guards: `test_the_provenance_names_its_rule.py` (rule name and
module on `data-rule`/`data-module`, and absent from the text),
`test_why_bga_believes_what_it_believes.py` (the rule line's layout
strings), `test_a_filter_is_a_property_of_a_table.py` (the Top-10
option found by value, not by the key in its label).

Residue fix (round 154): `Resource.PROCESS/DOWNLOAD/UPLOAD`, `useful`, `untracked` and kebab-case finding ids (`blast-radius-ranking`) go through `readerLabel`; "Reasoning in ..." / inline pairs read labels; prose `binary_cost`, `host-samples.jsonl`, `element_join[].cores_busy`, `findings[].evidence.change`, `recommended_builders minus builders`, `debug.cpu_us`, `debug.max_rss_kb` reworded; the unpublished-input paths sit in `<code>`; the guard gains a key-path/enum/`.jsonl`/finding-id scan (5 of 6 mutations red; the schema-description one is invisible on the three fixtures). Open: paths in `<code>` (`headline.chain_share`, `analyze/v6`) stay, `test_why_bga_believes_what_it_believes` and `test_the_provenance_names_its_rule` pin them; snake_case keys inside longer descriptions (`host_cpu_count`, `native_max_jobs`, `avg_fanin`, `ru_maxrss`) remain.
