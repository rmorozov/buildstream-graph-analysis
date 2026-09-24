# UX-1008: a consumer with no width promise is named, not silently oversubscribing

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-1007 | **Found by:** the census of four BuildStream projects (2026-09-24) - gnome-build-meta's `nvidia-container-toolkit.bst` runs `go build` with no `-p` and no `GOMAXPROCS` of its own | **Serves:** R5 (the report says which sandboxes the pool cannot size) | **Topic:** analysis | **Area:** bga | **Shape:** judgement

## Motivation

`go build` takes every CPU whatever `max-jobs` says, and a pool cannot
lend it tokens it never reads. Today such a sandbox reads
`unknown_kind`, the same line as a serial recipe, so a report cannot tell
a one-core element from one that took the whole host.

## Decomposition

surfaces: the jobserver decision record and its line in the report
guards: a sandbox whose Plane 2 peak exceeds its promised width by more than one core is named as outside the pool
gap: whether the threshold is the capture's own `max-jobs` or the host's cores
track: session's own
gate: its own

## Required Fix

Name the sandboxes whose measured concurrency exceeds any width they
were promised, so oversubscription outside the pool is visible.

## Out of Scope

Making `go` a client of the pool.

## Acceptance Test

A report over a fixture sandbox with peak 8 and no promise names it; one
with peak 1 does not.
