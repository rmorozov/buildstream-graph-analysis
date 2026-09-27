# UX-1065: a declared public junction keeps its public names

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-1062 | **Found by:** the 2026-09-27 brainstorm with the owner ([`anonymized-bundle.md`](../../design/anonymized-bundle.md)), section 5 | **Serves:** anyone sharing a private capture with an outside reader | **Topic:** store | **Area:** bga | **Shape:** judgement

## Motivation

Knowing an element is freedesktop-sdk's `gcc.bst` is worth more than
hiding a public name, but `bga` offline cannot tell a public junction
from an internal fork of one.

## Required Fix

The store's config names public junctions; a name list is built from a
public checkout on disk at a named tag; a name passes through only when
it is under a declared junction **and** in that list. Nothing declared,
nothing passes. The export says which junctions passed.

## Out of Scope

Guessing publicness from a source URL.

## Acceptance Test

`tests/unit/test_a_public_junction_keeps_only_public_names.py`: a
fixture with a declared junction and one element added "in a fork" -
the public element keeps its name, the added one is pseudonymized.
Mutation: drop the list intersection, and the fork's element leaks.

## Outcome
