# UX-629: a required set grew under an unchanged id

**Priority:** Medium | **Status:** 🔴 Open | **Depends on:** UX-343 (one contract version), UX-610 (which grew it) | **Found by:** architecture review 15 | **Serves:** a consumer validating a document it wrote yesterday | **Topic:** contracts

## Motivation

`UX-610` took `_COMPARE_REQUIRED` from 13 keys to 14, so
`schema('compare/v2')['required']` is 15 entries where it was 14 at
`147a49c`. The id did not move.

A `compare/v2` document a consumer wrote before this window no longer
validates against `compare/v2` after it. That is a breaking change by
any reading a consumer would recognise, and the rule does not call it
one:

- §3.7 names **rename** and **removal** as breaking, and is silent on
  a required set growing;
- `additionalProperties: true` protects extra keys, not missing ones;
- `test_output_schemas.py` catches a removal.

The window's `bga/schemas.py` diff is 87 insertions and one deletion,
and the deletion is a `description` string — so by the rule as written
this window is additions and no bump, which is true and insufficient.

## Required Fix

Either §3.7 gains a third clause — a key entering `required` under a
live id is a bump — or the addition lands as permitted-and-always-
written, declared optional in the schema and guaranteed by the
emitter, with a guard that says which was chosen.

Argued, not picked: the second shape keeps old documents valid and
costs a reader the certainty that the key is there.

## Out of Scope

- `UX-628`, the prose those keys lack.
- `UX-610` itself, which is closed and right about what it published.

## Acceptance Test

A key added to a live schema's `required` list, reddening a guard that
names the choice §3.7 made.
