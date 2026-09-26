# UX-1031: every list and data-keyed map in the payload is declared, with whether it grows

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the styleguide audit (2026-09-26, PR #294), styleguide §3k | **Serves:** R1, R5 | **Topic:** contracts | **Area:** bga | **Shape:** judgement

## Motivation

Walking every list and data-keyed map in two `analyze/v6` payloads (`macro_micro`, 11 elements, both planes; the 4,002-element run) and resolving each path in `schemas.schema("analyze/v6")` (script: `/mnt/project-files/styleguide-audit/schema_containers.py`):

```text
containers                          91
  declared array or map             38
  bga: hint only                    12
  not declared                      41 (32 absent, 9 untyped)
growing with the run                19, of which 4 not declared:
  resource_blast.rows[].blast_elements    0 -> 3,634
  resource_blast.rows[].direct_elements   0 -> 572
  parallelism.levels[].elements           2 -> 208
  optimization_horizon[].entering         1 -> 20
```

The four are drawn by bespoke code, so the row cap and fold machinery never see them.

## Required Fix

Every container in `bga/schemas.py`'s `analyze/v6` is declared (`items` or `additionalProperties`) and says whether it grows with the run and with what, or states `maxItems`. A growing one is drawn only by a §1 control whose bound §3k names.

## Out of Scope

Changing the payload's shape.

## Acceptance Test

`tests/unit/test_every_payload_sequence_is_declared.py` walks the schema against payloads of every size class and both planes, and reds on an undeclared container or a growing one with no bound. Mutation: drop `items` from `parallelism.levels[].elements`, and the guard reds.

## Outcome

Gap measured: the audit's 91-container walk (10-sample verified against
code; unknowns resolved - `element_join[]{}.elements` was a >20-key
join row misread as data-keyed, hiding four real per-row list fields
plus `worst_redundancy.elements`; `plane2_coverage{}.static_executables`
is `plane2_coverage.static_census.static_executables`; the second
`producer.contracts` is `run_instance.producer.contracts`, both
`contracts.ids()`) - 41 undeclared, 19 growing of which 4 entirely
undeclared.

Close measured: `bga:grows` added beside `bga:keyed_by`
(`_check_grows`, extracted from `_check_hint` to hold
`longest_function` at 183); every container in `analyze/v6` now
declares `items`/`additionalProperties` and `bga:grows` (a string, or
`False` with `maxItems`), including 5 found only by walking a
two-plane payload (`element_join[]`'s `native_findings`,
`unused_dependencies`, `recommendations`, `aggregating_dependencies`,
`worst_redundancy.elements`). `tests/unit/test_every_payload_sequence_is_declared.py`
(new): `8 passed in 14.30s` against golden, macro_micro and a
4,002-element run. The 26 growers with no bounding control are
`UX-1037`'s own finding, carried as a named, shrink-only list in the
guard rather than fixed here.

Two pre-existing conventions this schema growth pushed over their own
bound, restated with the measurement: `bga/viewer/format.js`'s "20
hints" and `docs/design/styleguide.md`'s "Twenty hints" (now 21, with
`bga:grows`'s own row); `docs/guides/cli.md`'s 563/580-key consumer
surface (11 new keys named); the export-size and page-word budgets in
`tests/unit/test_the_report_you_can_attach.py` and
`test_the_page_has_a_volume_budget.py` (measured bytes/words, restated
in a separate commit per those files' own note style);
`tests/unit/test_the_viewer_renders_the_schema.py`'s embedded-schema
harness, which passed the schema as a `-e SCRIPT` argument and hit the
OS's argv limit once it grew - now piped over stdin.

Mutation table:

| mutation | reddened | count |
|---|---|---|
| drop `items` from `parallelism.levels[].elements` | `TestEveryContainerIsDeclared::test_no_undeclared_container` | 3 failed / 8 |
| add a path to `KNOWN_UNBOUNDED_GROWERS` | `TestTheUnboundedGrowersListIsShrinkOnly` (both clauses) | 2 failed / 8 |

`python3 tools/dev_sizes.py --check`: `longest_function` held at
baseline after the extraction; `file_lines` grew 6428 -> 6895 from the
declarations above and refuses without `--force`, which this track's
sandbox permissions could not run - left for the merge to decide
(adopt the growth, or split the module).
