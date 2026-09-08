# UX-682: change frequency and co-change, from the logs the project already keeps

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-92 (cache effectiveness, blocked at stage 3), UX-479 (weighted blast) | **Serves:** R2 and R3 — split, consolidate, or leave alone, decided on evidence | **Topic:** analysis | **Shape:** judgement

## Motivation

The advice "keep your blast radius under a threshold" leads to a
mesh of trivial elements; the quantity that decides split-or-
consolidate is **expected rebuild cost** — how often an element
changes times what its change rebuilds — and its second factor
exists while its first does not:

```text
blast weight        blast_count / building_count / assembling_count / measured_us   bga/blast.py:311-320 — exists
change frequency    grep frequency|churn|rebuild_frequency (with blast) → 0 hits   — absent
Plane 3             bst_cache_logs: configure tax, developer tax, pairwise churn (one run vs its predecessor)
UX-92 stage 3       blocked on pinned capture refs — cache *variation*, which this does not need
```

Plane 3's kept logs record every element build the project ran; a
per-element rebuild count over that history is change frequency,
and the pairwise co-rebuild count is the co-change matrix. Neither
needs the ref variation `UX-92` was blocked on.

## Required Fix

From `bga cache-logs` over the kept history: per element, rebuild
count and the share of those rebuilds with an unchanged key; per pair,
co-rebuild count. Then `expected_rebuild_cost = frequency ×
weighted blast` per element, ranked; and the two advices as findings:
**split** where an element's consumers split into groups that never
co-change with each other; **consolidate** where two elements
co-change in ≥ p90 of their rebuilds and neither is consumed alone.
Every sentence names the counts it came from.

## Out of Scope

- Predicting future changes — frequency is history, and the finding
  says over how many builds.

## Contract (join)

In `bga/correlate.py`: `expected_rebuild_cost(analysis, cache_logs) ->
list[dict]`, one row per element present in both
`analysis['elements']['blast_radius']` (`weighted_duration_us` the
weighted blast, `downstream_count` the unweighted) and the Plane 3
`elements` list: `{'element', 'rebuilds', 'weighted_blast_us',
'expected_cost_us': rebuilds * weighted_blast_us, 'blast_count'}`,
ranked by `expected_cost_us` desc. Returned from `correlate()` under
`"expected_rebuild_cost"`, absent (not `[]`) when the Plane 3 payload
lacks `change_frequency` — `_scale_of`'s rule. Two new
`find_granularity_findings` ids: `'consolidate-by-co-change'` (a
`co_change` pair with `min(share_of_a, share_of_b) >= 0.9` and
`co_rebuilds >= 3`, where the two elements' consumer sets in
`dependencies` are identical) and `'split-by-co-change'` (an element
whose direct consumers form ≥ 2 connected components under "has a
co_change row with `co_rebuilds > 0`", each component's members having
`rebuilds >= 3`). Every sentence names the counts and says `over at
least N builds` from `builds_lower_bound`.

## Acceptance Test

A kept-log tree where lib-a rebuilds 30 times and codegen twice: the
ranking puts lib-a's expected cost above codegen's despite codegen's
larger blast; two elements that co-rebuild every time are named for
consolidation; mutation: swap frequency for blast count — red.

## Outcome

### Join half

**Gap measured:** `grep -rn "expected_rebuild_cost\|consolidate-by-co-change\|split-by-co-change" bga/correlate.py`
before this change: 0 hits — the join half of `expected rebuild cost`
and its two findings did not exist.

**Close measured:** `python -m pytest
tests/unit/test_expected_rebuild_cost_ranks_frequency_times_blast.py
tests/unit/test_granularity.py tests/unit/test_correlate.py -q` — 49
passed. Acceptance fixture (lib-a: blast 4/weighted 40s/30 rebuilds;
codegen: blast 20/weighted 400s/2 rebuilds): lib-a's
`expected_cost_us` is 1,200,000,000 (1200s), codegen's is 800,000,000
(800s) — lib-a ranks first despite codegen's 5x larger blast.

**Mutation table:**

| mutation | reddened | count |
|---|---|---|
| `expected_cost_us` uses `blast_count` instead of `rebuilds` | ranking + exact-value tests | 2 of 7 failed |
| drop the "neither is consumed alone" consumer-set check | the pair-x-alone-consumer negative test | 1 of 7 failed |
| `expected_rebuild_cost` key returned unconditionally (`[]` instead of omitted) | the key-absent-without-`change_frequency` test | 1 of 7 failed |

All three reverted from the pre-mutation copy; suite green after each revert.
