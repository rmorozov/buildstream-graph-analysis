# UX-1037: 26 payload containers grow with the run and no §1 control bounds them

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-1031 | **Found by:** UX-1031's own declaration pass | **Serves:** R1, R5 | **Topic:** viewer | **Area:** bga | **Shape:** judgement

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

## Decomposition

Input classes: each of the 26 paths at the 4,002-element run, drawn and not drawn. The journey extends reading a section into reaching the end of its longest list.

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

**Gap measured.** The census page (`gen-synthetic --seed 1 --layers 20
--width 200`) carries 9 of the 26 paths, 17 empty - so the page read is
the 4,002-element `--store --runs 2` snapshot with `macro_micro`'s
Plane 2 containers grafted on and each path filled to 300 marker names
per instance, exported, every fold open, every reveal pressed 10 times;
names found per path by text node (base `e0af222d`):

```text
drawn through a §1 control already        18  17 reveal (6+3 at rest), serialization_point_risks[].pinned_elements table (25 rows)
drawn unbounded                            4  element_join[].native_findings, .unused_dependencies: 300 <code> in one element section
                                              element_join[].recommendations: 300 p.advice in one element section
                                              optimization_horizon[].entering: 1,500 links in horizon, 300 names per element section
only in the section's JSON door            2  findings[].evidence.steps[].entering, restructuring[].elements
not drawn anywhere                         2  element_join[].aggregating_dependencies, .worst_redundancy.elements
```

**Close measured.** `app.js`'s `bounded` hands a list past
`TABLE_OPENS_BOUNDED_ABOVE` to `renderStructured` (§1's folded list, or
table for objects); `element.js` takes it as an option (no new import
edge). Same page after: the four are a reveal (6 + 3, window 60, last
page 51) and a 40-row table. §3k names all 26 in a table the census
now reads; `KNOWN_UNBOUNDED_GROWERS` 26 -> 0, ratchet 26 -> 0.

```text
$ pytest -n 1 -q tests/unit/test_every_step_past_a_bound_is_bounded.py \
    tests/unit/test_the_report_you_can_attach.py tests/unit/test_the_page_has_a_volume_budget.py
76 passed, 2 skipped in 97.56s
$ pytest -n 1 -q <declared guard, styleguide ledger, 6 element/horizon neighbours>
109 passed, 2 skipped in 39.71s
page (bytes - embedded)   339,335 -> 340,188 B   PAGE_BUDGET_B 341,000
```

**Mutation table** (each restored from a scratch copy):

| mutation | reddened | count |
|---|---|---|
| `bounded` never fires (`> 1e9`) | `test_no_instance_mounts_past_the_bound` (the 4, 300 each), `test_each_path_lands_only_in_its_named_control` (the 4, `bare`) | 2 of 4 |
| §3k: `aggregating_dependencies` -> reveal, `restructuring[].elements` -> not drawn, `longest_serial_chain` -> table | `test_the_table_names_paths_and_the_page_draws_them`, `test_each_path_lands_only_in_its_named_control` (both other rows) | 2 of 4 |
| re-list `optimization_horizon[].entering` | `test_a_named_path_has_left_the_unbounded_list`, `test_the_list_has_not_grown` | 2 of 3 |

Deviation: `sections.js`'s `DRAWN_ELSEWHERE` says every `element_join`
field reaches the elements table or an element section; the two
not-drawn paths do not (a drift, not fixed here). `data-raw` and
`data-entering` attributes still carry whole lists - attributes, not
drawn. The census builds a second page: +43 s in its tier.
