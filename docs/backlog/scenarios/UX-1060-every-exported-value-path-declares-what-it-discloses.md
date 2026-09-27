# UX-1060: every exported value path declares what it discloses

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the 2026-09-27 brainstorm with the owner ([`anonymized-bundle.md`](../../design/anonymized-bundle.md)), section 3; the owner's review on #298, finding 1 | **Serves:** anyone sharing a private capture with an outside reader | **Topic:** contracts | **Area:** bga | **Shape:** mechanical

## Motivation

An anonymized export needs the class of every value it carries.
`bga/schemas.py` cannot hold it: it pins only the output documents'
top-level keys, sets `additionalProperties` true, and is not the schema
of `graph.json`, `trace.json`, `run-context.json` or the other
captured inputs, so a guard over it passes beside an unclassified field.

## Required Fix

A new `bga/disclosure.py` holds one policy per exported member, keyed by
the member's contract version (`graph/v9`, `trace/v9`,
`run-context/v9`, `plane2/v3`, `sources/v1`, `host-samples/v1`) or,
for an uncontracted member, its layout path. Each policy names every
value path with one of the eight classes of the design's section 3,
including map keys that are data (`per_element.<key>` is class A) and
array items. A walker returns the paths a document holds that the policy
does not name; an unknown contract version returns the whole member.

## Out of Scope

Transforming values - that is UX-1062.

## Acceptance Test

`tests/unit/test_every_exported_value_path_declares_what_it_discloses.py`
walks every member of every fixture under `tests/fixtures/` and reds on
any unnamed path. Mutations: add a key to a fixture's `run-context.json`,
and it reds naming the path; bump a member's contract version, and the
whole member is reported.

## Outcome
