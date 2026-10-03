# UX-1305: a capture that recorded zero processes has no troubleshooting guide

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** docs gap audit on `c27ebd68`, UX-1300's thread (2026-10-03) | **Serves:** R1 | **Topic:** docs | **Area:** unassigned | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

The pilot's most likely failure, a shim that never ran, is answered
by `--diagnose`/`--no-inject` and `BST_TRACE_REAL_BWRAP`, and those live
only in cli.md's catch-all list or nowhere: `bwrap_shim.py:2065` tells
the user to set `BST_TRACE_REAL_BWRAP`, which no doc names.

```text
$ grep -rlw BST_TRACE_REAL_BWRAP docs/guides README.md | wc -l
0
$ grep -rl -- '--diagnose' docs/guides README.md
docs/guides/cli.md
```

## Required Fix

A troubleshooting section in real-project.md (linked from pilot.md):
zero processes, the shim's exec failing, `bga doctor`, `--diagnose`,
`--no-inject`, `BST_TRACE_REAL_BWRAP`; the env var joins cli.md's
inventory with `BST_TRACE_ARGV_MAX`.

## Out of Scope

`bga doctor`'s own checks.

## Acceptance Test

`grep` reads the section's names in real-project.md; the env inventory
guard covers both variables. Reading taken in this container.

## Outcome
