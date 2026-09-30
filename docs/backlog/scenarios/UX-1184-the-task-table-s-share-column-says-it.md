# UX-1184: the task table's share column says it is a share, not a duration

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-157 data-exploration review (`/mnt/project-files/view-ui-review/data-exploration/review.md`) of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`, Plane 2 rewritten by heavy.py to 5,849 processes and at most 81 binaries per element) at `cbc739b0`, Chromium 1440x900 and 390x844 | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_a_column_is_named_for_its_field.py`

## Motivation

Finding: 2 of the review.

Screenshot `01-task-share-at-rest.png`. `wall_clock_share_us` ("How much of the run did each task hold?") titles its column "Duration": `toolchain.bst` reads 4.9 min there and 0 ms in the element table; `layer08/mod018` 2.9 s against 14.4 s; `layer00/mod017` 80 ms against 400 ms. Task walk "Which BUILD elements took over 60 s?": the task table's threshold `> 60s` returns 1 row, `toolchain.bst` 4.9 min - the wrong answer; the element table's `> 60s` returns none, correctly (max 14.4 s). Breaks §6e.2 (one concept, one word) and §4b. `UX-391` (closed) relabelled the task key but not its column.

## Decomposition

Input classes: the 1,202-element two-plane page, the heavy-binary page (`UX-1182`'s, heavy.py's until it lands), `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

Rule, "a column named for a quantity is that quantity": a `duration_us` column is titled "Duration" only for an element's or task's own duration; a share of the window reads "Wall-clock share". The column title comes from the declared field, and one lead sentence says share differs from duration and links to the element table. The terminology matrix in `docs/design/styleguide.md` gains the row.

## Decision

Class: product.

Architect (round 158, group B):

```text
Route:     in `mapSectionLabels` (sections.js:484-498) the value head is titled from the field, `title(key, measure)` ("Wall-clock share"), not `title(measure, measure)` ("Duration"); one lead sentence under the head says share is not duration and links `#elements`; styleguide terminology matrix gains the row.
Rejected:  a new `title` in the schema for `wall_clock_share_us` - fixes one map, leaves the rule (title from field) unenforced for the next; renaming the quantity to `share` - it is microseconds, `> 60s` must still parse.
Files:     bga/viewer/sections.js (mapSectionLabels only); docs/design/styleguide.md (§6e.2 matrix row); tests/unit/test_a_column_is_named_for_its_field.py (new); tests/tiers.py (entry).
Guard:     test_a_column_is_named_for_its_field.py - on the 1,202-element page and macro_micro, no two `th` with different `data-column`/source field share a title.
Mutation:  restore `title(measure, measure)` at sections.js:497; the guard reds ("Duration" on both `elements.element_durations` and `wall_clock_share_us.value`).
Class:     product.
Split:     one track; first in track B2 (writes mapSectionLabels before UX-1186 does).
Budgets:   page +~250 B; controls 0; height +~24 px per map section with the lead (one line, 1 section on xl_both); words +~15.
Overlap:   mapSectionLabels is also written by UX-1186 (same track, after) and called into by UX-1191 (one line, track B1).
Question:  none.
```

Taken, three corrections. `title(key, measure)` on every map would retitle `by_binary`'s value "By binary": the value head is titled from the field only where the field names its own quantity (a `TERMS` entry, or a key carrying the unit's suffix), so `wall_clock_share_us` gains `TERMS` "Wall-clock share" and `by_binary` keeps "Count". The guard found a second case, `serial_chains.weighted_duration_us` titled "Duration" (a chain's members summed, not an element's own): retitled "Total" in `bga/schemas.py` - "Summed duration" wrapped `bottleneck` +158 px on `macro_micro`, "Total" +0 px, and the cell renders its unit. The matrix row's rejected-synonym cell is "—": `test_a_reader_never_sees_the_register.py` bans a rejected synonym in every `h2`/`h3`, and "duration" is a heading word elsewhere; the new guard holds the column instead.

## Out of Scope

The share's computation; the element table's own "Duration".

## Acceptance Test

`tests/unit/test_a_column_is_named_for_its_field.py`: on the 1,202-element page and `macro_micro`, no two columns with different source fields share a title. Mutation: retitle the element column "Duration" in the task table's place; the guard reds.

## Outcome

**Gap measured.** The new guard on the base tree (`78d7be67`), `PYTEST_XDIST= python3 -m pytest tests/unit/test_a_column_is_named_for_its_field.py`:

```text
E   AssertionError: macro_micro: one title, several fields: {'Duration': ['duration_us', 'wall_clock_share_us', 'weighted_duration_us']}
E   AssertionError: ('macro_micro', 'Duration')
2 failed
```

**Close measured.** Same command on this commit: `2 passed in 7.63s`. `wall_clock_share_us`'s value head reads "Wall-clock share" on both pages, under a lead linking `#elements`; `serial_chains`' summed duration reads "Total". Budgets, opened at 1440 (`test_the_page_has_a_volume_budget.py`'s `_LOOK`), base -> this:

```text
page half (golden, macro_micro)   144,200 -> 144,384 B   (+184)
golden        height 19,046 -> 19,024   words  7,661 ->  7,661   controls 372 -> 372
macro_micro   height 36,743 -> 36,788   words 12,399 -> 12,414   controls 661 -> 662
xl_both       height 41,834 -> 41,864   words 12,320 -> 12,334   controls 886 -> 887
```

The +1 control is the lead's link.

| mutation | reddened | count |
|---|---|---|
| value head back to `title(measure, measure)` (`sections.js`) | both clauses: "Duration" on `duration_us` and `wall_clock_share_us` | 2 failed |
| no lead (`if (false)`) | `test_the_share_says_it_is_a_share` | 1 failed, 1 passed |
| `weighted_duration_us` titled "Duration" again (`schemas.py`) | `test_no_two_fields_share_a_title` | 1 failed, 1 passed |

Re-based: `test_every_skip_reason_is_declared.py`'s `UNRESOLVABLE` 80 -> 81 (this guard's `NO_BROWSER` skip); `test_the_mapping_is_law.py`'s `wall_clock_share_us` headers `["Task", "Duration"]` -> `["Task", "Wall-clock share"]`; `docs/design/rendered-strings.json` regenerated (`--write`: "Wall-clock share", "Total", two preset options; a stale "Contracts" row the base already no longer rendered dropped).
