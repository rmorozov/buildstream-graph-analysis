# UX-678: memory joins the sweep and the queue model

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-613 (capacity-model/v1), UX-30 (the sweep), UX-116 (memory envelope) | **Serves:** R5 sizing a builder, R4 reading the sweep | **Topic:** analysis

## Motivation

```text
bga/ingest/models.py:38-43     Resource = PROCESS / DOWNLOAD / UPLOAD / CACHE — no MEMORY
bga/replay/scheduler.py        the sweep varies PROCESS capacity only
bga/capacity_model.py:1-75     inputs: builder count, arrival rate, service-time distribution — memory absent
bga/findings.py:810-989        memory_envelope / capacity_recommendation: static peak arithmetic, separate from both
```

The sweep will happily say "eight builders buy 40 %" on a machine
whose RAM fits four of these elements at once; the envelope knows
that and the sweep does not read it.

## Required Fix

Memory as a replay resource: each element's measured peak RSS is its
demand, host RAM (from `host-samples`) the capacity; the sweep's knee
and the queue model's utilization are reported under both
constraints, and the recommendation names which one bound first.

## Out of Scope

- Storage as a resource — the same shape, filed when a capture
  measures per-element disk (it does not yet).

## Acceptance Test

A synthetic run whose elements' peaks sum past host RAM at six
builders: the sweep's knee moves to the memory-bound builder count
and says so; mutation: remove the constraint — the knee guard reds.
