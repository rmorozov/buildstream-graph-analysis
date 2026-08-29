# UX-377: the run and the graph disagree about max-jobs, and on a default capture neither has it

**Priority:** High | **Status:** 🟢 Done Done | **Depends on:** UX-29 (auto-extract native_max_jobs from the wrapped log), UX-31 (the resolved per-element max-jobs) | **Serves:** anyone who runs `bga snapshot` without extra flags | **Topic:** capture

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

## Outcome

Round 61. Both columns, and the three routes now agree with each other
and with what the sandboxes ran:

```text
route              run   source                     graph   sandboxes ran
default              4   resolved_from_graph          [4]   make -j4
user config: 2       2   resolved_from_graph          [2]   make -j2
bst --max-jobs 2     2   parsed_from_invocation       [2]   make -j2
```

against, before:

```text
default           None   —                            [4]
user config: 2    None   —                            [2]
bst --max-jobs 2     2   parsed_from_invocation       [4]   <- ran -j2
```

**The run-level value has a third source.**
`NATIVE_MAX_JOBS_RESOLVED_FROM_GRAPH`, last of three, so a flag on the
command line still wins and `native_max_jobs_source` keeps saying which
route the published number took. `typical_resolved_max_jobs` is the
**maximum** of the graph's resolved per-element values — the same rule
`serialization_points.typical_max_jobs` uses, deliberately, because
they are the same quantity and having the run level disagree with the
per-element comparison would be the defect. An element carrying
`notparallel` reads 1 and does not lower the run: it is a finding
*against* that figure.

What it bought, on a default capture:

```text
before  Capacity: builders 4 x max-jobs unrecorded on 4 core(s)
        Capacity checks did not run for this run - missing: native_max_jobs
after   Capacity: builders 4 x max-jobs 2 on 4 core(s): memory binds at 1,
        below the 4 configured - more builders contend rather than overlap
```

**The graph is extracted with the build's own options.** `--max-jobs`
is a *top-level* `bst` option — `bst show --max-jobs 2` is `No such
option`, which is worth knowing and is what the argv clause holds — so
it goes before the subcommand. Without it, the one route that recorded
the run published a graph describing a fresh resolution: five sandboxes
at `make -j2` under a graph saying 4.

Reading the scheduler config moved above the graph extraction, which it
could always have been: it only inspects what the converter already
parsed.

### Falsification run

Seven mutations against the committed tree. All seven caught:

| # | Mutation | Caught by |
| --- | --- | --- |
| M1 | the graph tier is removed — the defect | `test_the_graph_answers_when_nothing_else_does` |
| M2 | the graph tier outranks the invocation | `test_the_invocation_beats_the_graph` |
| M3 | the typical value is the minimum | `test_a_notparallel_element_does_not_lower_the_run` |
| M4 | an empty graph guesses 1 | `test_a_graph_with_no_resolved_value_says_nothing` |
| M5 | the options land after the subcommand | `test_run_bst_show_puts_the_options_before_the_subcommand` |
| M6 | the graph is extracted without the build's options | `test_the_extraction_replays_what_the_invocation_carried` |
| M7 | the run context is not offered the graph's value | `test_the_run_context_is_offered_the_graphs_value` |

M5 is the one a reader would not guess: the placement is the whole
content of that claim, and a clause that only checked the option was
*present* would stay green while every extraction failed.

### Verification Log

```text
$ python3 -m pytest tests/unit/test_one_resolved_max_jobs.py -q
12 passed in 0.22s

$ # three captures of one project, reading run-context, graph and the
$ # `make -jN` the raw trace shows
default              run=4  src=resolved_from_graph     graph=[4]  ran=[4]
user config max-jobs 2  run=2  src=resolved_from_graph  graph=[2]  ran=[2]
bst --max-jobs 2     run=2  src=parsed_from_invocation  graph=[2]  ran=[2]

$ bga analyze <default capture>/run --diagnostics | grep Capacity
  Capacity: builders 4 x max-jobs 2 on 4 core(s): memory binds at 1 ...
```

Tiered small on landing at 0.22s.

## Out of Scope (added on closing)

- `run_context.max_jobs`, which holds `scheduler["builders"]`. Renaming
  a published field is its own item with its own compatibility
  question, and it stayed out as the filing said.
