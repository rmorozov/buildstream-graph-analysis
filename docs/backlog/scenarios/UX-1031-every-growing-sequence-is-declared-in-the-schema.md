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

Not started.
