# UX-1060: every schema leaf declares what it discloses

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the 2026-09-27 brainstorm with the owner ([`anonymized-bundle.md`](../../design/anonymized-bundle.md)), section 3 | **Serves:** anyone sharing a private capture with an outside reader | **Topic:** contracts | **Area:** bga | **Shape:** judgement

## Motivation

An anonymized export needs to know, per value, whether it names the
project, is public vocabulary, a measurement, a host fact, a hash, free
text, a secret or a time. Classified per file, a name embedded in a
string or a field added next round leaks; a denylist fails open.

## Required Fix

Each leaf of the published schemas in `bga/schemas.py` carries a
`disclosure` word from the eight classes of the design's section 3
(`sensitivity` is taken by an `analyze` section). Each
`CAPTURE_LAYOUT` row in `bga/run_store.py` names keep, transform or
drop.

## Out of Scope

Acting on the class - that is UX-1062.

## Acceptance Test

`tests/unit/test_every_schema_leaf_declares_what_it_discloses.py` walks
every published schema and every layout row and reds on one with no
class. Mutation: delete one leaf's `disclosure`, and it reds naming it.

## Outcome
