# UX-377: the run and the graph disagree about max-jobs, and on a default capture neither has it

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-29 (auto-extract native_max_jobs from the wrapped log), UX-31 (the resolved per-element max-jobs) | **Serves:** anyone who runs `bga snapshot` without extra flags | **Topic:** capture

## Motivation

Native `max-jobs` is what reaches `make -jN` inside a sandbox. It is the
right-hand factor of `UX-116`'s founding question and the input the
whole capacity-guard chain (`UX-12`/`15`/`16`/`17`/`21`) keys off.
BuildStream 2.7.0 gives it three routes, and its own
`data/userconfig.yaml` sets the default:

```yaml
build:
  max-jobs: 0        # 0 means "the host's core count"
```

bga recovers it from exactly one of the three. `NATIVE_MAX_JOBS_RE`
(`bst_log_to_chrome_trace.py:63`) searches the wrapper's `Executing
command:` line for `--max-jobs N`. Measured, three captures of the same
project on a 4-core host:

```text
route                              scheduler.native_max_jobs   graph per-element max_jobs
default (nothing set)                              None                              4
$XDG_CONFIG_HOME/buildstream.conf: 2               None                              2
bst --max-jobs 2 build                                2                              4
```

`bst show` confirms the middle row is a real change and not a fiction —
`%{vars}` reports `max-jobs: 4` with no user config and `max-jobs: 2`
with it.

**Two separate defects, one per column.**

*The run-level value is absent on the two routes people actually use.*
Row 1 is the default `bga snapshot` capture and row 2 is a user config,
and both record `None` — while `graph.json`, in the same snapshot,
records the resolved value for every element. What that costs, read off
`bga analyze --diagnostics` on the 10-element capture:

```text
Capacity: builders 4 x max-jobs unrecorded on 4 core(s): CPU binds first, at 5
Capacity checks (over/under-subscription, memory) did not run for this run
  - missing: native_max_jobs. They are inert here, not passing.
```

The tool's flagship command produces a capture in which its own capacity
chain cannot run, and the missing number is in the file next to it.

*The per-element value is wrong on the route that does record the run.*
Row 3's `4` is not what the build ran at. `bga snapshot` re-derives the
graph with its own `bst show`, which does not replay the build's
options, so a `--max-jobs`-overridden build gets whatever a fresh
resolution says. A cold capture proves it — the raw trace, the Plane 2
report and the run identity all agree, and the graph does not:

```text
what the sandboxes really ran      make -j2   (5 of them, from plane2.log.gz)
plane2 per_element_parallelism     requested_jobs: 2
run_identity.scheduler             native_max_jobs: 2
graph.json per-element max_jobs    4                        <- wrong
```

`serialization_points` compares each element's `max_jobs` against the
run's typical value to find elements pinned below their siblings. On
this capture every element reads 4 against a build that ran at 2, so
the comparison is against a baseline the run never had.

## Required Fix

One resolved value, from the capture that has it.

- **Where the invocation carries no `--max-jobs`, the run-level value
  comes from the graph's own resolved per-element `max-jobs`** — the
  typical value, which `serialization_points` already computes as
  `typical_max_jobs`. `native_max_jobs_source` gains a third value
  saying so, beside `parsed_from_invocation` and the explicit one, so a
  reader can tell a recovered value from a declared one.
- **The graph extraction replays the build's own scheduler options**, or
  the per-element `max_jobs` it writes is labelled as re-derived rather
  than as what ran. Publishing a number the same snapshot contradicts is
  the defect; either ending fixes it.
- **`notparallel` keeps its meaning**: the run-level figure is the
  typical value, not a claim that every element got it, which is exactly
  the distinction `UX-31` drew.

## Falsification

Three captures of one project — default, user config, `--max-jobs` on
the command line — and assert for each that
`run_identity.scheduler.native_max_jobs` is not `None` and that the
graph's per-element values agree with what the raw trace shows the
sandboxes ran (`make -jN`). Today row 1 and row 2 fail the first
assertion and row 3 fails the second.

The other direction: `native_max_jobs_source` still reads
`parsed_from_invocation` when the flag is on the command line, so a
recovered value never silently displaces a declared one.

## Out of Scope

- BuildStream's own resolution order. bga reads what `bst` resolved; it
  does not model the precedence itself.
- `run_context.max_jobs`, which holds `scheduler["builders"]` under a
  name that invites confusion with this one. Renaming a published field
  is its own item with its own compatibility question, and doing it
  inside a change about a missing value would hide one in the other.
