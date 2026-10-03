# UX-1308: the graph owner has no end-to-end guide

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** docs gap audit on `c27ebd68`, UX-1300's thread (2026-10-03) | **Serves:** R3 | **Topic:** docs | **Area:** unassigned | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

R3's tools - `junction-cost`, `cache-trend`, floors, blast, what-if -
are in cli.md; real-project.md covers blast, what-if and sweep, and no
guide walks a graph owner from a capture to a structural decision.

```text
$ grep -rl 'bga junction-cost\|bga cache-trend' docs/guides README.md
docs/guides/cli.md
```

## Required Fix

A section (or `graph-owner.md`) walking one example project through
the graph-only and duration findings, in the shape of `jobserver.md`.

## Out of Scope

New findings.

## Acceptance Test

The guide's commands run on a committed example (the pasted-block
guard holds them). Reading taken in this container.

## Outcome
