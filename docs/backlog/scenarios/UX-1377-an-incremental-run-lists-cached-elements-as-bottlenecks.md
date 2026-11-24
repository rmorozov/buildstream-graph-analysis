# UX-1377: an incremental run lists cached elements as bottlenecks

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** walk seed 6 (2026-11-03) | **Serves:** R3, R1 | **Topic:** analysis | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_a_cached_element_is_not_a_bottleneck.py`

## Motivation

[`walk-seed-6.md`](../../audits/walk-seed-6.md) finding 5: on
`tests/fixtures/same_build_twice_incremental` (1 rebuilt, 3 cached) the text
report reads "Bottlenecks Identified: 4 - lib0.bst, lib1.bst, lib2.bst,
lib3.bst", while `bga whatif inc --element lib0.bst` answers "Refused: No
measured duration: lib0.bst". The graph owner is pointed at three elements
this run never built.

## Decomposition

Input classes: cold, incremental with some cached, incremental with all
cached (population 0). Journey: extends the walk's seed 6 class.

## Required Fix

A bottleneck is an element this run measured; cached ones are counted
apart ("3 cached, not priced") or left out.

## Out of Scope

Pricing a cached element from an older run.

## Acceptance Test

The incremental fixture's report names lib3.bst alone as a bottleneck; the
mutation that drops the measured-duration filter reddens the guard.

## Decision

A bottleneck is named only if this run measured it (a build duration this run); choke points with no measured duration (cached or pulled) are counted apart. One source of truth: the analysis publishes the split, every consumer reads it.

- `bga/structural/analyzer.py`, `models.py`: `BottleneckAnalysis.unpriced_choke_points` - the choke points whose element duration (`_durations()`, the map the structural analysis already prices with) is 0 or absent.
- `bga/analyzer.py`, `bga/schemas.py`: `bottleneck.unpriced_choke_points`, an additive key beside `choke_points` (the structural list stays the graph's waists, so the page's "Choke points" table and `bottleneck_count` are unchanged); no schema bump. `schemas.measured_bottlenecks()` is the one reader: `(named, unpriced)`; a document without the key names all.
- `bga/report/text.py`: `Bottlenecks Identified: 1 - lib3.bst (3 cached, not priced)`; with none measured, `Bottlenecks Identified: 0 (N cached, not priced)`. A cold run reads as before. Only the text report names choke points as bottlenecks (`choke_point_uids` has no other caller; `viewer/tables.js` reads the list as the choke-point table).
- All-cached (population 0): `_compute_structural_analysis` returns `{}` with no tasks, so no line is printed and no element is named; the count is the cache line's "4 cached, 0 rebuilt".
- `docs/guides/json-contracts.md`: the key named, the surface figure 645 to 646.
- No golden snapshot moved: the goldens carry no cached choke point and the suite's golden readers are green.

Guard: `tests/unit/test_a_cached_element_is_not_a_bottleneck.py`.

## Outcome

**Gap measured** - `python3 -m bga.cli analyze tests/fixtures/same_build_twice_incremental/run | grep Bottlenecks`, before (the filter off):

```text
  Bottlenecks Identified: 4 - lib0.bst, lib1.bst, lib2.bst, lib3.bst
```

and `bga whatif <run> --element lib0.bst`: `Refused: No measured duration: lib0.bst.`

**Close measured** - same command, after; the cold fixture (`same_build_twice_cold/run`) unchanged:

```text
  Bottlenecks Identified: 1 - lib3.bst (3 cached, not priced)
  Bottlenecks Identified: 4 - lib0.bst, lib1.bst, lib2.bst, lib3.bst     (cold)
```

All cached (the incremental topology with no spans): no Bottlenecks line, `100.0% cache hit ratio (4 cached, 0 rebuilt)`.
`python3 -m pytest tests/unit/test_a_cached_element_is_not_a_bottleneck.py -q`: `5 passed`.
No golden snapshot moved. `dev_touching.py --base origin/main` selection (245 files): 5226 passed, 46 failed; 3 were this change (a hyphen in the new schema description, the key unnamed in `json-contracts.md`, its surface figure) and fixed; the 36 remaining on `--lf` need `tests/ci_reference.json`, `flake_ledger.json`, `touch_map.json`, which the worktree has not fetched.

**Mutations**

| mutation | reddened | count |
|---|---|---|
| `structural/analyzer.py`: `if not durations.get(node)` -> `if False` (filter dropped) | `test_an_incremental_run_names_only_what_it_rebuilt`, `test_the_json_publishes_the_split_beside_the_choke_points` | 2 failed, 3 passed |
| `schemas.measured_bottlenecks`: `unpriced = set()` (reader ignores the split) | `test_an_incremental_run_names_only_what_it_rebuilt`, `test_a_document_whose_choke_points_are_all_unpriced_names_none` | 2 failed, 3 passed |

Not discriminating: `test_an_all_cached_run_names_no_element_and_states_the_cached_count` and `test_a_cold_run_is_unchanged` stay green under both - an all-cached run has no structural block at all, so nothing reaches the filter; they hold the input classes, not the filter.

**Deviation** - none.
