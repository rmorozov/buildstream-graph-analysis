# UX-682: change frequency and co-change, from the logs the project already keeps

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-92 (cache effectiveness, blocked at stage 3), UX-479 (weighted blast) | **Serves:** R2 and R3 — split, consolidate, or leave alone, decided on evidence | **Topic:** analysis

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

## Acceptance Test

A kept-log tree where lib-a rebuilds 30 times and codegen twice: the
ranking puts lib-a's expected cost above codegen's despite codegen's
larger blast; two elements that co-rebuild every time are named for
consolidation; mutation: swap frequency for blast count — red.
