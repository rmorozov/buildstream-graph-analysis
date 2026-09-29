# UX-1008: a consumer with no width promise is named, not silently oversubscribing

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-1007 | **Found by:** the census of four BuildStream projects (2026-09-24) - gnome-build-meta's `nvidia-container-toolkit.bst` runs `go build` with no `-p` and no `GOMAXPROCS` of its own | **Serves:** R5 (the report says which sandboxes the pool cannot size) | **Topic:** analysis | **Area:** bga | **Shape:** mechanical | **Reading:** container

**Guard:** tests/unit/test_a_consumer_outside_the_pool_is_named.py

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

## Decision

```text
Route:     threshold is the element's own resolved `max-jobs` (the decision row's `max_jobs`, else the capture's project `max-jobs`). A sandbox that is not joined (`unknown_kind`/`pinned`) whose peak exceeds `max-jobs + 1` gets the verdict `outside the pool`, in UX-1012's verdict column.
Rejected:  host cores as the threshold (go's GOMAXPROCS defaults to the host's cores, so the check could never fire) · a separate section (a second table for the same per-element population).
Files:     bga/correlate.py (UX-1012's function), bga/report/text.py, tests/unit/test_a_consumer_outside_the_pool_is_named.py
Guard:     fixture at max-jobs 4: peak 8 with no promise is named; peak 1 is not; a joined peak 8 is `drew`, not `outside`.
Mutation:  compare against host_cpu_count (peak-8 case stops being named); drop the +1 (a peak-5 case is named when it should not be).
Class:     product
```

## Out of Scope

Making `go` a client of the pool.

## Acceptance Test

A report over a fixture sandbox with peak 8 and no promise names it; one
with peak 1 does not.

## Outcome

Gap measured: before, a sandbox with no decision row or `unknown_kind` read `unknown_kind` at any peak; the report could not tell a peak-1 recipe from a peak-8 `go build`.

Close measured (`python3 -m pytest -n 2 tests/unit/test_a_consumer_outside_the_pool_is_named.py tests/unit/test_the_report_says_which_elements_drew.py`): 11 passed. Fixture at project `max-jobs` 4: peak 8 with no decision row reads `outside the pool`, peak 1 and peak 5 read `unknown_kind`, joined peak 8 reads `drew`, pinned (max-jobs 1) peak 6 reads `outside the pool`. The threshold falls back to the capture's `project_max_jobs` when the decision row has no `max_jobs`. UX-1012's pinned fixture peak moved 3 to 2 (3 > 1+1 is now outside).

| Mutation | Red | Count |
|---|---|---|
| `peak > max_jobs + 1` to `peak > 16` (fixed threshold standing in for host cores) | peak-8 and pinned cases | 2 failed, 4 passed |
| drop the `+ 1` | peak-5 case | 1 failed, 5 passed |
| drop the `project_max_jobs` fallback | peak-8 no-promise case | 1 failed, 5 passed |

Deviation: (orchestrator)
