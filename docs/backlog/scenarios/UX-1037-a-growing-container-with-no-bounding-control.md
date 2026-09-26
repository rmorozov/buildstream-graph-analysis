# UX-1037: 26 payload containers grow with the run and no §1 control bounds them

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-1031 | **Found by:** UX-1031's own declaration pass | **Serves:** R1, R5 | **Topic:** viewer | **Area:** bga | **Shape:** judgement

## Motivation

`UX-1031` required every container in `analyze/v6` to declare whether it
grows with the run, and closed with every one declared. Declaring
`bga:grows` on a container did not give it a bound: 26 of them grow
with the run and are drawn by bespoke code the row cap and fold
machinery never see, so nothing in the payload or the page's own
controls caps their size:

```text
capacity_recommendation.pinned_elements
plane2_coverage.static_census.elements_at_risk
plane2_coverage.static_census.static_executables
findings[].evidence.steps[].entering
optimization_horizon[].entering
cache.target_closure.targets
bottleneck.longest_serial_chain
bottleneck.serial_chains[].members
parallelism.levels[].elements
serialization_point_risks[].pinned_elements
deferrability.recommended_deferrals
confidence.critical_path_cached
timestamp_agreement.shorter_than_bst
element_join[].worst_redundancy.elements
element_join_coverage.plane1_only_with_impact
element_join_coverage.undeclared_plane2_elements
resource_blast.rows[].direct_elements
resource_blast.rows[].blast_elements
resource_blast.rows[].staged_at
duration_resolution.elements
duration_resolution.tasks
restructuring[].elements
element_join[].native_findings
element_join[].unused_dependencies
element_join[].recommendations
element_join[].aggregating_dependencies
```

Some already sit inside a table `structured.js`/`app.js` cap on the page
(`TABLE_OPENS_BOUNDED_ABOVE` and its kin); others (the `[].elements`
subsets, `static_executables`, `recommended_deferrals`) are a bare list
of uids on a card or a `<dd>`, with nothing capping it at all - a
40,000-element run can put every one of an element's dependents in one
cell.

## Required Fix

Each path above is drawn only by a §1 control whose bound §3k names -
either the page's existing table cap already reaches it (name which
one, in §3k), or it needs one (a cap, a "show more", or a fold) that
§3k then names.

## Out of Scope

Re-deriving the list: it is `UX-1031`'s own measurement, carried in
`tests/unit/test_every_payload_sequence_is_declared.py`'s
`KNOWN_UNBOUNDED_GROWERS`. Changing the payload's shape.

## Acceptance Test

For each path above, either `structured.js`/`app.js` already draws it
through a control `test_every_drawing_has_a_name_and_a_data_route.py`
(or a sibling table/list guard) can name, or a new control is added and
that guard extended to cover it. Once a path is bounded,
`test_every_payload_sequence_is_declared.py`'s
`test_every_named_path_is_still_unbound` reds until it is removed from
`KNOWN_UNBOUNDED_GROWERS` - the shrink the list exists to force.

## Outcome

Not started.
