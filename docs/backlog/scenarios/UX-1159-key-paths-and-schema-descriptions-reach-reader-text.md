# UX-1159: key paths and schema descriptions reach reader text

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-154 walk, items 8, 9 and 10; the UX-1141 and UX-1144 residue (2026-09-30) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_a_key_path_stays_where_it_is_copied.py`

## Motivation

Page: the round-154 walk of the two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14`, 114 elements; `bga_view --export`, Chromium 1440x900 and 390x844; screenshots in `round-154/`).

Key paths in `<code>` serve as reader labels ("Threshold headline.chain_share < 0.9", evidence "headline.chain_share 42.4%", "Paths resolve against analyze/v6"), pinned by `test_why_bga_believes_what_it_believes` and `test_the_provenance_names_its_rule`; long schema descriptions name `host_cpu_count`, `native_max_jobs`, `cpu_budget`, `avg_fanin`, `avg_fanout`, `ru_maxrss`, `max_concurrency` and no guard sees a description absent from the fixtures; "Records embedded no"; `format.js` quantity/duration/bytes and `views.js` history rows draw a dash for null; 146 " - " dashes in prose. Whether `T∞`, `LB`, `T_C` should carry plain-language names is a question, not a defect (UX-1144 decided the symbols).

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390.

## Decision

- **Choice.** A key path is reader text only inside a copy surface (`pre`, a command line, a Perfetto query's tables, `[data-copy]`, the JSON door, the schema drawing). The provenance fold labels each path by the schema's title (`pathLabel` in `format.js`), keeps the path on `data-path`/`data-observed`/`data-document`/`data-unpublished`, and drops the "Paths resolve against" line to its attribute. Schema descriptions and the producer sentences the page prints (`analyzer.py` capacity note, `provenance.py` rule sentences, two Perfetto notes) name a field by its words.
- **Symbols (default taken, open to the owner).** Keep T∞, LB, T_C; the §6e.2.1 word carries its plain name beside it ("Chain floor T∞", "Resource floor LB", "Replay makespan T_C"), so every label - the first use included - names it; sentences keep the bare symbol.
- **Files.** `bga/viewer/{decision,format,questions,element}.js` (a Plane 2 flag reads through `READER_LABELS`), `bga/{schemas,analyzer,provenance,cli}.py`, the tracer's two notes, the styleguide §6e.2.1 table and §4g, the committed analyses.
- **Guard.** `tests/unit/test_a_key_path_stays_where_it_is_copied.py`: walks every `description` of every `schemas.schema(name)` for a `snake_case`/`UPPER_CASE` key or a dotted key path, and boots `golden`/`macro_micro` with every door open for a visible text node holding one outside a copy surface.
- **Mutation.** Restore `<code>${path}</code>` in the evidence `dt`, and restore one description's `avg_fanin`; each reds its test.

## Required Fix

A key path stays where a reader copies it, not where one reads it; a schema-walking check sees every description; the symbol question is put to the session.

## Out of Scope

The analysis behind the values; the other findings of the round-154 walk.

## Acceptance Test

A guard that walks `schemas.schema(name)` finds no snake_case key in a description, and no reader-text node is a key path outside a copy control. Mutation: restore the defect, and the new guard reds.

## Outcome

**Gap measured** - the guard's own regexes on the base (`54d61bb9`), every door open, 1440 px; the two-plane page is `gen-synthetic --seed 1 --store --layers 8 --width 14` plus its Plane 2 report:

```text
schema descriptions walked 1173, naming a key 110 (91 distinct keys)
golden       key tokens in reader text  64   (provenance 42, capacity_verdict 5, decision 3, headline 3, ...)
macro_micro  key tokens in reader text  99   (provenance 69, floors 5, decision 3, headline 3, ...)
two_plane    key tokens in reader text  67 at 1440, 67 at 390 (provenance 46, floors 4, headline 3, ...)
```

**Close measured** - the same instrument on this commit:

```text
schema descriptions walked 1173, naming a key 0
golden 0 · macro_micro 0 · two_plane 0 at 1440, 0 at 390
schema description bytes (analyze/v6)   64,297 -> 64,024 B
page with its data removed (golden)    149,133 -> 149,253 B  (+120)
opened words  golden 8,025 -> 8,084 · macro_micro 13,109 -> 13,172 (budget 13,200)
```

**Mutation table** - each reverted from a copy, then green (55 passed across the three files):

| mutation | reddened | the run printed |
|---|---|---|
| evidence `dt` prints `ref.path` again | `test_no_reader_text_holds_a_key_path[golden,macro_micro]` - 38 and 57 tokens | 2 failed, 1 passed |
| `avg_fanout`'s description says `avg_fanin` again | `test_no_schema_description_names_a_key` - `graph_metrics/avg_fanout` | 1 failed |
| "Paths resolve against `analyze/v6`" restored | `test_every_string_it_shows_comes_from_the_record` | 1 failed |
| the `dt`'s `title` (the path on the hover) dropped | `test_no_field_is_withheld[golden,macro_micro]` - `evidence[].path` 21 and 32 | 2 failed, 2 passed |
| `TERMS.lb` back to "LB" | `test_each_concept_carries_its_one_word[golden,macro_micro]` | 2 failed |

**Deviation.** Re-based, claims kept: `test_why_bga_believes_what_it_believes` admits a path's label and no longer "Paths resolve against"; `test_the_provenance_names_its_rule` reads the observed field by its row's label and each path on the hover (`title`), `document` and `evidence[].quantity` behind the door (the latter read as reached only as a substring of the printed paths); `test_a_reader_sees_labels_not_keys` loses its `T_C` exemption; `test_one_element_one_record` finds "downstream count" and "observed-critical" in the join's descriptions; the skipped-input and plane-2 note pins in `test_a_boolean_is_a_verdict`, `test_the_cpu_floor_divides_by_cores`, `test_every_plane2_block_has_a_destination` follow the new words. `macro_micro/plane2.json`'s two notes edited as the tracer now writes them (`UX-1142`'s precedent). The null dashes and " - " prose in the Motivation are not this Required Fix and are untouched.
