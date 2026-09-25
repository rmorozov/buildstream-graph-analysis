# UX-1013: admission ranks from BuildStream's own cached build logs when bga never captured the project

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-1005 | **Found by:** Ruslan on the Graviton thread (2026-09-25), on ranking admission with no previous capture | **Serves:** R4, R5 | **Topic:** capture | **Area:** tools | **Shape:** judgement

## Motivation

UX-1005 track C ranks waiting sandboxes by slack from a `--plan`, or,
with none, from graph structure: level from the bottom, ties broken by
declared width. Structure cannot see duration: on `13-mixed-graph` the
giant and its 24 narrow siblings share one level. A machine that built
the project before keeps each element's build log in BuildStream's
local cache (`bst artifact log`), so per-element durations may exist
where bga never ran.

## Decomposition

surfaces: the tracer's ranking source (`plan` / `structural` today)
guards: an element whose cached log reads the longest build ranks first at equal level; a log with no timing falls back to structural and says so
gap: whether `bst artifact log` carries start and end times reliably, per BuildStream version, and for a key that changed since
track: after UX-1005

## Required Fix

A third ranking source, `cached-logs`, between `plan` and
`structural`, named in the report.

## Out of Scope

Remote caches' logs.

## Acceptance Test

On a project built once without bga, the capture's report names
`cached-logs` as the ranking source and ranks the longest element first.

## Outcome

Not started.
