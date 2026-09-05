# UX-676: the utilization envelope, and the intervals that violate it

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-675 (the cores series), UX-377 (resolved max-jobs), UX-48 (idle split) | **Serves:** R4 first, R2 and R3 through the elements each interval names | **Topic:** analysis | **Shape:** judgement

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

## Outcome

**The gap, measured.** `UtilizationResult` computed two window lists
and published neither, in the wrong unit:

```text
$ grep -rn "idle_periods" bga/analyzer.py bga/schemas.py
(no output - computed since M4, read by nothing outside its own module)
$ sed -n '430,435p' bga/utilisation/__init__.py   # before
    utilization = active_count / self.effective_cpus
```

Active *tasks* over cpus is slots, not cores - the proxy `UX-675`
exists to replace. Both lists are deleted, which is the branch of the
Required Fix's third bullet that keeps one answer to one question.

**The close, measured**, on `tests/fixtures/host_cpu` - a real
two-plane capture taken for this item, and the only committed run with
a CPU series:

```text
cores 4 · builders 4 x max-jobs 4 = 16 configured · capacity 4
busy p50/p95     1.884 / 3.255          underutilized_share 0.917
verdict          not_binding            overcommitted_share 0.0

underutilized_intervals[0]
  busy_cores 1.069 of 4 · lost_core_seconds 5.865
  building [{element: core.bst, max_jobs: 1}]
```

`core.bst` is `notparallel` in the example's own element file, so it
builds at one job while three cores idle. That is the Acceptance
Test's top row, and it arrived because the build does it.

**The mutation table.** Seven, each reddening a named clause in
`test_the_cores_were_or_were_not_binding.py`.

| mutation | clause that reds |
|---|---|
| capacity is the configured 16, not the smaller 4 | `..._less_than_one_idle_core_is_not_enough` |
| the idle floor halved to 0.5 cores | same |
| an idle core alone is a violation | same |
| swap ignored in the overcommit test | `..._overcommit_beats_under_use_in_the_verdict` |
| under-use beats overcommit in the verdict | same |
| the cap keeps the first rows, not the worst | `..._the_ranking_is_by_lost_core_seconds` |
| bounds published in microseconds | `..._points_at_a_library_query_and_its_own_window` |

**Four deviations.**

*The under-utilization rule is wider than the filing's.* "While work
was ready" found **zero** intervals on the capture: BuildStream
dispatches immediately here, so the idle was parallelism-bound, not
scheduling-bound, and the rule would have missed `core.bst` - the
Acceptance Test's own row. It is now one whole core idle while Plane 1
says there was work, building *or* ready; the row's two columns say
which, leaving *why* to `UX-677` as the Out of Scope requires.

*No Plane 2 process count.* `plane2/v3` is folded and carries no
per-process time ranges; the only file that does is `plane2.log.gz`,
which `analyze` never opens by design (`UX-300`). Each row carries
`trace_query` plus `trace_bounds` instead, so the count is one click
away in the trace - which is what the handoff is for.

*No per-builder column.* `trace/v9` records which spans overlap a
window, not which builder ran them; there is no lane id to group by.
The column is the concurrent set against `builders`.

*A second substitution token.* `{element}` was "the one substitution".
`{window}` is the second and renders to nothing without bounds, so
every un-bounded query is byte-identical to before.
**One thing the first draft got wrong.** `envelope.percentile` was a
copy of `store_aggregate`'s, with a guard holding the two equal - two
rules and an instrument to keep them the same. The touching-map guard
reddened on the import that clause needed; it is one import now.

The export bounds move to 438,000 and 489,000 (+5,633 / +5,632: 533 B
source, ~5,100 B contract). Earlier task files carrying 482,000 are
history, which §3.6 names rather than this item rewriting them.
