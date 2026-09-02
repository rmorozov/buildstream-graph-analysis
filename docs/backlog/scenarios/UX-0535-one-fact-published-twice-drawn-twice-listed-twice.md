# UX-535: one fact published twice, drawn twice, listed twice

**Priority:** Medium | **Status:** 🟡 In Progress | **Depends on:** UX-288 (the one-population rule), UX-285 (the grouping that moved without merging) | **Serves:** anyone reading the run's identity, or the rail | **Topic:** viewer

## Motivation

The duplication census over the cold export (35 tables, 338 distinct
text blocks, 12.8 % repeated characters — under §5a's 21 %) found
the repeats that are not citations:

```text
run_instance.producer == producer         True   (analyzer.py:160-162, schemas.py:2494)
rail "Producer"                            2 entries, 2 hrefs
rail "Latent heavies"                      2 entries — a section, and an `elements` preset
graph_summary vs graph_metrics             3 facts, the same sentence, both sections
```

`UX-390` is verified closed (`attribution_hints` has no section).
These three are the remainder: a payload key published under two
paths, and a rail that lists a section and a preset under one label.

## Required Fix

`producer` is published once (`run_instance.producer` stays, the
top-level copy goes — a removal, so the analyze contract bumps under
`UX-190`); `graph_summary`'s three shared facts render in one of the
two sections; rail labels are unique — a preset entry says "preset"
or carries the count.

## Out of Scope

- Selections drawn both as a section and as an `elements` preset —
  `UX-289`/`UX-338`'s design; only the rail label collides.

## Acceptance Test

Payload-level duplicate scan (the census's method) finds zero exact
duplicates; rail labels unique. Mutation: republish `producer` —
the contract guard reds.

## Outcome (round 80, 2026-09-02) — 🟢 Done; one of the three was not a duplicate

### The rail (batch 1)

`viewEntries` labels a preset entry with the option's own text, which
carries the count: `Latent heavies (1)` against the section's `Latent
heavies`. Zero collisions of 59 and 83 entries, both fixtures.

### `graph_summary` — three facts removed, `analyze/v5`

Not "the same sentence" but the same **object**: the summary was
assigned from the `StructuralMetrics` instance `graph_metrics`
publishes, so the two agreed by construction, not by luck.

```text
bga/structural/analyzer.py:632  'total_elements':       metrics.num_elements
                         633    'critical_path_length': metrics.critical_path_length
                         634    'max_parallelism':      metrics.max_parallelism

fixture         graph_summary.total_elements   graph_metrics.num_elements
golden                     4                            4
with_timeline             11                           11
```

They are read from `graph_metrics` now; `graph_summary` keeps the three
that are its own — `bottleneck_count`, `deferrable_leaves`,
`best_case_speedup`. One reader moved: `chapters.js`'s elements-chapter
answer. Three removals, so **`analyze/v4` → `analyze/v5`** (`UX-190`),
v4 joining `SUPERSEDED`. Both fixtures regenerated with
`dev_refresh_analysis.py --write`; the semantic diff is those keys, the
version stamps, and `document_shape` leaves 699 → 697 on golden —
−3 keys +1 contract id, exactly.

### `producer` — the Required Fix names a duplicate that is not one

The census read `run_instance.producer == producer` as one fact twice.
They are **two facts that coincide when one build does both jobs**. A
run captured by an older build and analyzed by this one:

```text
top-level producer      0.3.0   ← the build that ANALYZED
run_instance.producer   0.1.0   ← the build that CAPTURED   EQUAL: False
```

Removing `run_instance.producer` as written takes `UX-250`'s
contract-movement refusal with it: `bga compare` hands `run_instance` to
`comparison_movement`, and both documents' top-level stamps are the
analyzing build, so the top-level copy cannot stand in — measured, the
refusal fires on the capture pair and is silent on the top-level pair.
Batch 1 reached the same refusal from the opposite direction and
concluded the *reverse* removal; both directions lose a fact. Neither
copy goes, and `TestTheTwoProducerStampsAreTwoFacts` pins the
difference so the next census does not re-file it.

### Mutations verified red and reverted (8)

| # | mutation | reddened |
|---|---|---|
| P1 | `link.textContent = name` restored | `…no_label_points_two_ways`, 2 |
| P2 | the drive reports `entries: 0` | `…rail_was_actually_read`, 2 |
| M1 | the three re-added to `summary` | `…share_no_key` 2, `…second_name` 2, `…quotes_no_metric` 2 |
| M2 | `ANALYZE` back to `analyze/v4` | `…removal_bumped_the_contract`, 2 |
| M3 | `_document` returns `{}` | `…scan_read_two_populated_sections` 2, `…second_name` 2 |
| M4 | `run_instance['producer']` unset (the Fix as written) | `…two_stamps_differ`, 1 |
| M5 | `comparison_movement` returns `[]` | `…refusal_reads_the_capture_stamp`, 1 |
| M6 | the `old[name] != new[name]` filter dropped | `…top_level_stamp_cannot_stand_in`, 1 |

### Deviation

The three went to `graph_metrics`, not the reverse: `num_elements` sits
beside `num_edges` there, and the summary's remaining keys are
consequences rather than measurements.
`test_the_summary_repeats_the_metrics_it_quotes` asserted the two copies
agreed; it is now `test_the_summary_quotes_no_metric_at_all` — the same
claim made structural instead of checked after the fact.
