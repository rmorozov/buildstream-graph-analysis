# UX-1306: no guide says the run store grows, or how to prune it

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** docs gap audit on `c27ebd68`, UX-1300's thread (2026-10-03) | **Serves:** R1, R5 | **Topic:** docs | **Area:** unassigned | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

`bga snapshot --prune`, `--older-than`, `--keep` and `--max-store` are
in cli.md only (`cli.md:316-351`); README, real-project.md and pilot.md
(which keeps 30 bundles a class) never mention `.bga/runs` growth.

```text
$ grep -rln -- '--prune\|--max-store' docs/guides README.md
docs/guides/cli.md
```

## Required Fix

A "disk" paragraph in real-project.md with the store's measured size
per run and the prune commands, and a README pointer.

## Out of Scope

Changing prune defaults.

## Acceptance Test

The paragraph names a measured bytes-per-run figure and the commands;
the link guard holds the pointer. Reading taken in this container.

## Outcome
