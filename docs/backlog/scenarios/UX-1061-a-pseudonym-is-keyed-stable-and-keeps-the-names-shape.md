# UX-1061: a pseudonym is keyed, stable, and keeps the name's shape

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the 2026-09-27 brainstorm with the owner ([`anonymized-bundle.md`](../../design/anonymized-bundle.md)), section 4 | **Serves:** anyone sharing a private capture with an outside reader | **Topic:** store | **Area:** bga | **Shape:** mechanical

## Motivation

The owner must resolve what an outside reader says back to real
elements without hand work, and pseudonyms must name the same element
across captures so comparison classes survive sharing.

## Required Fix

A new `bga/anonymize.py`: `pseudonym = prefix + base32(HMAC-SHA256(key,
class ‖ value))[:k]`, `k` grown on collision; junction separators,
`.bst`, depth, extensions, character class and length band kept; the
result a valid element name. One key per project under `.bga/anon/`,
the map beside it at mode 0600; a key fingerprint for the manifest.

## Out of Scope

Walking a capture (UX-1062); resolving text (UX-1064).

## Acceptance Test

`tests/unit/test_a_pseudonym_is_keyed_stable_and_shaped.py`: same key
and value give the same pseudonym across two runs; a forced collision
grows `k`; the map round-trips; the key and map files are 0600.
Mutation: drop the class from the HMAC input, and an element and a
directory of the same name collide.

## Outcome
