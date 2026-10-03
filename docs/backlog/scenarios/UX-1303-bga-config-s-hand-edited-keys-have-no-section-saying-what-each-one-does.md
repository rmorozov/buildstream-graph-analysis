# UX-1303: `.bga/config`'s hand-edited keys have no section saying what each one does

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** docs gap audit on `c27ebd68`, UX-1300's thread (2026-10-03) | **Serves:** R1, R8 | **Topic:** docs | **Area:** unassigned | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

`builds_per_day` (`bga/build_rate.py:7`) prices the decision panel's
agent-hours a day, and appears in the guides only as a contract row
(`json-contracts.md:367`); `public_junctions` (`bga/run_store.py:508`)
is in no guide; the sticky `trace_opens`/`trace_spine` are mentioned in
passing (`cli.md:277`, `real-project.md:123`).

```text
$ grep -rln public_junctions docs/guides README.md | wc -l
0
$ grep -rn builds_per_day docs/guides | cut -d: -f1,2
docs/guides/json-contracts.md:367
```

## Required Fix

One `.bga/config` section in cli.md: every key a reader in `bga/`
reads, its default, who writes it and what it changes; real-project.md
links it.

## Out of Scope

Whether `docs/design/roles.md`'s R8 row is stale against `UX-1276`.

## Acceptance Test

A guard collects the keys `bga/` reads from `.bga/config` and reddens
when the section misses one. Reading taken in this container.

## Outcome
