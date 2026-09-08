# UX-684: the cached-build verdict — does the graph rebuild the cheapest subgraph?

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-682 (expected rebuild cost), UX-477 (the cold verdict's rule) | **Serves:** R3 showing evidence, R8 reading it | **Topic:** analysis | **Shape:** judgement

## Motivation

The cold build has a verdict — chain-bound / scheduler-bound /
inconclusive (`bga/findings.py:1610-1637`), with the floors and the
sweep behind it. The cached build, which is most builds, has none:
the graph owner cannot say whether the shape lets the likely changes
rebuild little, and the tool's blast findings speak of one resource
at a time.

## Required Fix

A `cached_shape` verdict from `UX-682`'s distribution: the share of
the change history whose rebuild stayed under the p50 weighted blast
("most changes rebuild the cheapest subgraph"), the elements whose
changes dominate the expected cost, and height versus weight stated
separately — stack and other assembling elements add height for
free, a single heavy element adds weight — so "split the tall chain"
and "isolate the heavy element" are two different advices. The
verdict's rule and its denominator are stated the way `UX-477` states
the cold one's.

## Out of Scope

- Simulating a proposed split — `UX-230`'s what-if prices fixes to
  durations; pricing a graph edit is its own model, filed when the
  verdict has a consumer.

## Acceptance Test

Example 06's history: the verdict names the share of changes under
the p50 blast and the dominant element; mutation: weigh by count
instead of duration — red.

## Outcome

**Gap measured:** `git show d3e78b8a:bga/correlate.py | grep -c
cached_shape` → `0`; no `cached_shape` key, function or verdict
constant existed anywhere in the package.

**Close measured:** Example 06 carries no captured kept-log tree
(`find examples/06-macro-micro-optimization -iname '*log*'` names no
Plane 3 history), so this runs against the checked-in capture of the
same project, `tests/fixtures/macro_micro` (`UX-682`'s own tests build
a synthetic history the same way), and a real `bga cache-logs` log
tree built from it. `PYTHONPATH=. python3 -m bga.cli analyze
tests/fixtures/macro_micro/run --format json` carries no `--cache-logs`
flag (`bga analyze` never reads Plane 3), so the verdict is pasted
from `bga correlate`, which does:

```text
$ PYTHONPATH=. python3 -m bga.cli correlate tests/fixtures/macro_micro/run \
    tests/fixtures/macro_micro/plane2.json --cache-logs cache_logs.json --format json
"cached_shape": {
  "verdict": "rebuilds_the_cheapest_subgraph",
  "cheap_share": 0.5833333333333334,
  "cheap_changes": 70, "total_changes": 120,
  "p50_weighted_blast_us": 14150000,
  "dominant": [{"element": "lib-a.bst", "expected_cost_us": 634500000,
    "share_of_expected_cost": 0.625, "height": 7, "weight_us": 21150000,
    "height_rank": 1, "weight_rank": 1, "advice": null,
    "assembling_kind": false}, ...],
  "sentence": "70 of 120 recorded changes (58%) rebuilt at or under the
    graph's own median weighted blast. lib-a.bst dominates the expected
    cost at 63%."
}
```

`python3 -m pytest tests/unit/test_cached_shape_ranks_dominant_by_duration_not_count.py
tests/unit/test_expected_rebuild_cost_ranks_frequency_times_blast.py
tests/unit/test_correlate.py tests/unit/test_granularity.py -q` → `52
passed`. `make test-touching` → `3379 passed, 41 skipped`, one
pre-existing red unrelated to this diff and reproduced identically on
the round's base commit (`test_a_partial_is_not_wholly_made_of_closed_filings`,
Direction 19's review-cadence staleness). `make lint` (ruff +
`dev_baseline.py --check` + `pymarkdown --config .pymarkdown.json`) →
clean.

**Mutation table** (each: copy saved, mutated, `pytest
tests/unit/test_cached_shape_ranks_dominant_by_duration_not_count.py
-q`, restored from the copy, re-run green):

| mutation | reddened | count |
|---|---|---|
| `_dominant_elements` ranks by `rebuilds` instead of `expected_cost_us` | `test_dominant_is_ranked_by_duration_weighted_cost_not_change_count` | 1 failed, 1 passed |
| `cached_shape`'s p50 taken over the recorded-change elements instead of over the whole graph | `test_cheap_share_matches_an_independent_recount` | 1 failed, 1 passed |

Both restored to `2 passed`.
