# UX-676: the utilization envelope, and the intervals that violate it

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-675 (the cores series), UX-377 (resolved max-jobs), UX-48 (idle split) | **Serves:** R4 first, R2 and R3 through the elements each interval names | **Topic:** analysis | **Shape:** judgement

## Motivation

The CI owner's question has a short answer and a long one, and the
tool has neither. It computes the long one's raw material and throws
it away:

```text
bga/utilisation/__init__.py:118-119   UtilizationResult.idle_periods / high_utilization_periods
bga/utilisation/__init__.py:403-435   _analyze_idle_periods: <10 % / ≥80 % windows
grep idle_periods bga/analyzer.py bga/schemas.py → 0 hits            computed, never published, no element lists
published instead                      idle_no_tasks vs idle_underparallel — two totals (UX-48), no windows
```

And the raw material is the wrong unit (processes, `UX-675`). What the
role needs is the **envelope** — cores busy against the capacity the
scheduler configured (`builders × max-jobs`, `UX-377`) and the cores
the host has, subject to memory headroom — and its two kinds of
violation as intervals: under-utilization (busy well below both
caps while work was ready — `idle_underparallel` says the work was
there) and overcommit (load above cores, or swap above zero).

## Required Fix

- A `utilization_envelope` section: the series summarised (p50/p95
  busy cores against capacity and cores; the share of the build
  under- and over-committed) and the **headline sentence** the CI
  owner asked for: whether cores were the binding resource without
  overcommitting memory, in one line, with the numbers.
- An `underutilized_intervals` table (and its mirror
  `overcommitted_intervals`): interval · cores busy of capacity ·
  the elements building in it *per builder* with each one's native
  `max-jobs` · Plane 2 process count in the interval · the
  predecessors that had just finished and the successors waiting —
  one row per interval, bounded by the 40-row rule, ranked by lost
  core-seconds. Each row carries the canned Perfetto query scoped to
  its time range (`UX-368`'s per-finding query, with `ts` bounds
  substituted), so the pivot per interval is one click away.
- `idle_periods` re-based on the cores series and published, or
  deleted — computed-and-unread is the class `UX-401` filed.

## Out of Scope

- Deciding *why* an interval is under-utilized — the table names the
  elements and their `max-jobs`; `UX-677` prices the remedy.

## Acceptance Test

On a two-plane capture of example 06 (core.bst pinned to `-j1`) the
table's top row names core.bst's interval with `max-jobs 1` and the
cores busy under capacity; the headline says cores were not the
binding resource; mutation: read processes instead of cores — the
section's unit guard reds.
