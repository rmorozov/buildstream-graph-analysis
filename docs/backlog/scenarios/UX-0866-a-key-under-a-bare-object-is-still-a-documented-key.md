# UX-866: a key under a bare object is still a documented key

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-858, UX-838 | **Found by:** round 120, review 24 | **Serves:** R4 (the guide names every flag and key the capture writes) | **Topic:** docs | **Area:** bga | **Shape:** mechanical

## Motivation

`UX-858` added `--jobserver-seed N` to `bga capture run` and `seed` to
`run_instance.jobserver`; `docs/guides/cli.md`'s jobserver flag list
names every sibling flag and not this one, and its `run_instance.
jobserver` row lists four keys where the schema hint has five. The
coverage guard (`test_the_documents_keep_up_with_the_contracts.py`)
never sees it: the real schema types `run_instance` as a bare `object`,
so `_consumer_surface()` never descends into it - `UX-838`'s shape one
level up the schema.

## Required Fix

`docs/guides/cli.md`: a `--jobserver-seed N` line in the jobserver
flag list and `seed` in the `run_instance.jobserver` row; the coverage
walk (`_consumer_surface()` or the guard's own reader) also reads the
keys `_RUN_INSTANCE_HINT` declares under `run_instance`, so a key added
there with no guide row reds the guard.

## Decomposition

Input classes: a key under a typed object, a key under a bare object
with a hint, a key with no hint at all; the journey it extends is
review 24's read of the guide against the tree.

## Out of Scope

Typing `run_instance` with `properties` in the published schema (a
contract change, its own row).

## Acceptance Test

`tests/unit/test_the_documents_keep_up_with_the_contracts.py`: the
walk counts `run_instance.jobserver.seed` and the guide names it;
mutation: drop the hint's keys from the walk - the count falls and the
guide's stated reach reds.
