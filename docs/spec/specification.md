# BuildStream Build Efficiency Analyzer (`bga`)

## Specification and Implementation Plan — Version 9

> **For "what does `bga` do today," start at [`docs/design/architecture.md`](../design/architecture.md) instead.** This document remains authoritative for the original design intent and full-length invariant/data-contract text, but it predates every real extension built since (the second intra-element analysis plane, `bga compare`, the capacity/CPU-budget work, and more) - `architecture.md` names each one and points back here for whatever hasn't changed.

---

# Part 0 — Executive Summary

`bga` analyzes one concrete BuildStream CI run and separates three fundamentally different kinds of statements:

1. **Measurement** — what actually happened in the trace.
2. **Certification** — what cannot be beaten given observed durations, dependencies, and resource constraints.
3. **Estimation / counterfactual modeling** — what might happen under different capacities, cold-cache assumptions, or duration distributions.

The governing principle is:

> **Measure what happened. Certify what cannot be improved. Label what is estimated. Never mix the three.**

The v9 architecture makes one important structural distinction:

```text
                    ┌──────────────────────────────┐
                    │          Raw trace            │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │   Normalized task intervals  │
                    │   + integer-µs timestamps     │
                    └──────────────┬───────────────┘
                                   │
                 ┌─────────────────┴──────────────────┐
                 │                                    │
                 ▼                                    ▼
       ┌────────────────────┐              ┌─────────────────────┐
       │ Occupancy step      │              │ Static dependency   │
       │ function            │              │ graph / EDG         │
       └─────────┬──────────┘              └──────────┬──────────┘
                 │                                    │
                 │                                    ▼
                 │                         ┌─────────────────────┐
                 │                         │ Structural models   │
                 │                         │ T∞ / LB / critical  │
                 │                         │ paths / reachability│
                 │                         └──────────┬──────────┘
                 │                                    │
                 └────────────────┬───────────────────┘
                                  ▼
                       ┌─────────────────────┐
                       │ Dependency-causal   │
                       │ blame-chain walk    │
                       └──────────┬──────────┘
                                  │
                                  ▼
                       ┌─────────────────────┐
                       │ Gap classification  │
                       │ + annotations       │
                       └──────────┬──────────┘
                                  │
                                  ▼
                       ┌─────────────────────┐
                       │ Flattened measured  │
                       │ attribution view    │
                       └─────────────────────┘
```

The important change from v8 is that **the blame chain does not hop through resource blockers** and **PHASE does not compete with causal categories**.

---

# Part 1 — Product Definition

## 1.1 Purpose

`bga` answers:

1. **Where did the wall clock actually go?**

   * measured task execution;
   * dependency waiting;
   * resource waiting;
   * scheduler waiting;
   * retry effects;
   * genuine idle;
   * trace head/tail.

2. **How much of the elapsed time was structurally unavoidable?**

   * observed critical-path floor;
   * capacity/resource-area lower bounds;
   * provable serialization bounds.

3. **Where is the build structurally fragile?**

   * critical-path elements;
   * near-critical elements;
   * high downstream blast radius;
   * leaf/terminal work;
   * high wait-to-execution tasks;
   * high criticality probability.

4. **Was the available capacity used effectively?**

   * task occupancy;
   * resource occupancy;
   * CPU utilization;
   * oversubscription evidence.

5. **What would happen under different capacities?**

   * deterministic replay;
   * capacity sweep;
   * knee detection.

6. **What would happen without cache hits?**

   * advisory `T∞,cold`;
   * never used as a certified bound.

---

## 1.2 Non-Goals

`bga` does not claim to calculate:

* the mathematically optimal real scheduler;
* exact counterfactual runtime under changed capacity;
* a universally correct single cause for every wait;
* exact CPU cost from task durations alone;
* a trustworthy cold runtime when historical evidence is unavailable.

---

# Part 2 — Three Semantic Layers

Every result belongs to one of three layers.

## 2.1 Measured Layer

Derived directly from the run:

```text
trace intervals
task durations
occupancy
ready times
observed waits
resource holders
wall clock
CPU accounting
```

Measured results may be exact relative to the supplied trace.

---

## 2.2 Certified Layer

Results that are mathematically valid under explicit assumptions.

Examples:

```text
T∞,observed
LB
certified_headroom
observed critical path
graph reachability
resource-area lower bounds
```

Certified results use observed durations unless explicitly stated otherwise.

---

## 2.3 Advisory / Counterfactual Layer

Examples:

```text
T∞,cold
T_C
capacity sweeps
knee estimates
Monte-Carlo criticality probability
heuristic scheduler replay
```

These must never silently appear as measured or certified quantities.

---

# Part 3 — Time Representation and Trace Normalization

## 3.1 Integer Microseconds

All internal timestamps and durations use:

```text
int64 microseconds
```

Chrome traces already use microsecond-resolution timestamps, making integer microseconds the preferred canonical representation.

This gives:

```text
sum(category_duration) == horizon
```

as exact integer equality.

No floating-point arithmetic is used for timeline accounting.

Floating-point seconds are created only at the reporting boundary.

---

## 3.2 Timestamp Quantization

A configurable trace epsilon is converted once into integer microseconds.

Example:

```yaml
trace_epsilon_us: 50000
```

Default:

```text
50 ms
```

All timestamps are quantized to the epsilon grid during ingestion.

Conceptually:

```text
quantized_ts = round(ts / epsilon) * epsilon
```

The implementation must use a documented deterministic rounding rule.

After quantization, timestamps within epsilon become exact equality.

This avoids the non-transitive relation:

```text
A ~ B
B ~ C
A != C
```

that would occur if epsilon were repeatedly applied pairwise.

---

## 3.3 Ordering Validation

For a dependency edge:

```text
predecessor -> task
```

the expected relationship is:

```text
finish(predecessor) <= start(task)
```

after normalization.

If raw timestamps produce a small negative gap that disappears through quantization, the normalized trace is accepted.

If a genuine negative ordering remains after normalization:

```text
start(task) < finish(predecessor)
```

the trace contains an ordering violation.

No hidden runtime correction is performed.

---

## 3.4 Immutable Finish Time

When a normalization operation has to clamp a task start to its ready time:

```text
start' = ready
```

the task's finish timestamp remains immutable.

Therefore:

```text
duration' = finish - start'
```

Duration absorbs the correction.

The analyzer never moves a finish timestamp merely to preserve the original duration.

---

# Part 4 — Primary Trace Model

## 4.1 Occupancy Step Function

The primitive trace representation is an occupancy step function.

For every recognized task:

```text
[start_us, finish_us)
```

creates an interval event:

```text
START(task)
FINISH(task)
```

For every resource:

```text
resource occupancy(t)
```

is represented similarly.

The sweep-line produces a sequence:

```text
[t0, t1) -> active task set
[t1, t2) -> active task set
...
```

This is the core architectural primitive.

It supports:

* active task count;
* resource occupancy;
* wall-clock activity;
* idle detection;
* head/tail analysis;
* push tail;
* exclusive-resource stalls;
* concurrency;
* wall-clock task share;
* ready-queue depth;
* overlap analysis.

No blame-chain semantics are required to construct the occupancy model.

---

## 4.2 Occupancy Invariants

For every consecutive sweep interval:

```text
active_tasks(t)
```

is deterministic and complete with respect to recognized task spans.

Intervals are:

* ordered;
* contiguous;
* non-overlapping;
* half-open.

---

## 4.3 Wall Clock

Preferred:

```text
wall_clock = run_context.wall_end - run_context.wall_start
```

Fallback:

```text
trace_horizon =
    max(recognized finish)
    - min(recognized start)
```

The fallback is explicitly marked as reduced provenance.

---

# Part 5 — Static Dependency Graph

## 5.1 Element Dependency Graph

`bga` constructs an Element Dependency Graph:

```text
EDG
```

using the dependency closure BuildStream actually schedules and stages.

Dependency scope is explicit:

```text
build
runtime
```

The graph must not invent dependencies that were not present in the supplied BuildStream model.

---

## 5.2 Task Graph

Tasks are identified as:

```text
element_uid|task_kind|phase|attempt
```

Task kinds:

```text
TRACK
PULL
FETCH
BUILD
PUSH
OTHER
```

---

## 5.3 Structural Metrics

The graph engine computes:

```text
in_degree
out_degree
unweighted_depth
weighted_depth
reachable_downstream_count
dominators
critical path
slack
```

---

# Part 6 — Blame-Chain Model

## 6.1 Fundamental Definition

The blame chain is **not a flattened timeline**.

It is a causal backward walk through dependency relationships.

At task `t`:

```text
execution(t):
    [start(t), finish(t))

dependency wait:
    [ready(t), start(t))
```

The chain follows:

```text
task execution
    ↓
dependency wait
    ↓
predecessor responsible for readiness
    ↓
predecessor execution
    ↓
its dependency wait
    ↓
...
```

Every chain interval is contiguous with the next chain interval.

There is therefore no overlap problem inside the chain itself.

---

## 6.2 Chain Horizon

The chain begins from the terminal task responsible for the observed end of the build.

It proceeds backward until:

```text
wall_start
```

or until an attribution boundary is reached.

The remaining time is represented as a measured residual rather than artificially forcing it through the dependency graph.

---

## 6.3 Dependency Hop Only

A critical rule:

> **The blame chain hops only through dependency causality.**

It does not hop from a task to an arbitrary resource holder.

Resource contention is measured separately.

---

# Part 7 — Dependency Gate

For task `t`:

```text
ready_time(t) =
    max(finish(p))
    for p in predecessors(t)
```

If:

```text
start(t) == ready_time(t)
```

then the task was dependency-ready exactly when it started.

If:

```text
start(t) > ready_time(t)
```

the interval is classified according to what happened during that gap.

---

## 7.1 Dependency Blame Selection

When several predecessors finish at effectively the same time, select deterministically.

Tie-breaking:

```text
1. greatest normalized finish time
2. greatest longest-path-to-source depth
3. smallest task key
```

This replaces v8's out-degree rule.

Rationale:

* depth represents causal history;
* depth is stable against unrelated graph additions;
* ascending task key provides deterministic final ordering.

Out-degree is never used as a causal tie-breaker.

---

# Part 8 — Resource Wait Model

## 8.1 Resource Wait Does Not Alter the Chain

If a task is dependency-ready but cannot start because a resource is unavailable:

```text
category = RESOURCE_WAIT
```

The blame chain remains attached to the waiting task.

It does **not** hop to one resource-holder task.

---

## 8.2 Resource Holder Set

For every resource-wait interval:

```text
blocking_tasks =
    set of tasks holding the required resource
```

The set is time-weighted.

Example:

```text
RESOURCE_WAIT / PROCESS

00:10 - 00:15
    holder A: 70%
    holder B: 30%
```

If no holder can be established:

```text
blocking_tasks = UNKNOWN
ambiguous = true
```

This is preferable to inventing a single causal winner.

---

## 8.3 Resource Attribution

For each resource:

```text
resource_wait_duration
holder_time_distribution
peak_occupancy
average_occupancy
exclusive_stall_time
```

are independently measured.

---

# Part 9 — Scheduler Wait

A task is:

```text
dependency-ready
resource-available
not-running
```

during an interval.

That interval is:

```text
SCHEDULER_WAIT
```

provided the trace contains sufficient evidence to establish this state.

The analyzer does not infer scheduler failure merely because a task did not run.

---

# Part 10 — Phase Model

## 10.1 PHASE Is an Annotation

Phases such as:

```text
load
resolve
cache cleanup
metadata processing
```

are not causal categories competing for wall-clock ownership.

They annotate intervals.

For example:

```text
IDLE
    phase=cache_cleanup
```

or:

```text
SCHEDULER_WAIT
    phase=load
```

The phase is therefore metadata attached to the underlying measured category.

---

## 10.2 Phase Overlap

If a background phase overlaps execution:

```text
EXECUTION_ON_CHAIN
    phase=cache_cleanup
```

The execution remains execution.

No eclipsing subsystem is required.

The analyzer may report:

```text
phase_overlap:
    cache_cleanup: 12.4s
```

but this does not alter the causal attribution.

---

# Part 11 — Measured Attribution Categories

The canonical categories are:

```text
EXECUTION_ON_CHAIN
DEPENDENCY_WAIT
RESOURCE_WAIT
SCHEDULER_WAIT
IDLE
RETRY_WAIT
UNTRACKED_HEAD
UNTRACKED_TAIL
```

`PHASE` is not a category.

---

## 11.1 Category Semantics

### EXECUTION_ON_CHAIN

Execution interval belonging to a task on the measured dependency blame chain.

### DEPENDENCY_WAIT

Time attributable to waiting for dependency completion.

### RESOURCE_WAIT

Time where dependencies are satisfied but required resources are unavailable.

### SCHEDULER_WAIT

Time where a task is ready and resources are available, but dispatch does not occur.

### IDLE

No recognized work explains the interval.

### RETRY_WAIT

Delay caused by retry sequencing.

### UNTRACKED_HEAD

Time before the first recognized build activity.

### UNTRACKED_TAIL

Time after the last recognized build activity.

---

# Part 12 — Flattened Timeline

## 12.1 Purpose

The flattened timeline is a **presentation and reconciliation view**, not the causal model.

It is constructed after measured categories and annotations are established.

Its contract is:

```text
segments are ordered
segments do not overlap
segments cover the selected horizon
```

For the task horizon:

```text
Σ segment_duration == H
```

exactly.

For the full wall-clock horizon:

```text
UNTRACKED_HEAD
+
task-horizon attribution
+
UNTRACKED_TAIL
==
wall_clock
```

exactly.

---

## 12.2 No Interval Eclipsing

There is no generic interval-eclipsing engine.

No category is allowed to "win" over another category merely because its priority is higher.

Overlapping source intervals remain separately represented in the source model.

Only the final attribution view is one-dimensional.

---

# Part 13 — Task Horizon and Invariant I1

Define:

```text
H =
    max(finish(recognized tasks))
    -
    min(start(recognized tasks))
```

The certified lower bound must satisfy:

```text
H >= LB
```

This is the meaningful hard check.

Separately:

```text
wall_clock >= H
```

is a provenance / containment relationship and should not be confused with the lower-bound invariant.

---

# Part 14 — Structural Floors

## 14.1 Observed Structural Floor

```text
T∞,observed =
    weighted longest path using observed durations
```

This is certified for the observed run.

Interpretation:

> Given these dependencies and these observed task durations, no schedule with unlimited relevant capacity can complete faster than this value.

---

## 14.2 Unweighted Structural Depth

Compute:

```text
unweighted_depth
```

independently of duration.

This is useful for:

* cross-run structural comparison;
* cache-independent graph analysis;
* identifying deep dependency chains.

---

# Part 15 — Cold Structural Floor

## 15.1 Definition

```text
T∞,cold =
    weighted longest path using estimated cold durations
```

It is advisory only.

---

## 15.2 Duration Source Hierarchy

For a task:

```text
1. same cache_key historical execution
2. same element_uid + task_kind + phase historical execution
3. cohort median / p75
4. declared metadata estimate
5. unavailable
```

Never use:

```text
cache-hit duration
zero
arbitrary constant
```

as an implicit cold duration.

---

## 15.3 Cold Publication Gate

By default:

```text
if any task on cold critical path has unavailable duration:
    T∞,cold = unavailable
```

Optional:

```text
--allow-partial-cold
```

produces an explicitly:

```text
partial=true
confidence=low
```

value.

Cold analysis never affects:

```text
LB
certified_headroom
primary confidence
measured attribution
```

---

# Part 16 — Capacity Lower Bound

```text
LB = max(
    T∞,observed,
    max_p(W_p / C_p),
    provable exclusive-serialization bounds
)
```

where:

```text
W_p = observed work for resource p
C_p = available capacity for resource p
```

Only observed durations participate.

---

# Part 17 — Certified Headroom

```text
certified_headroom =
    H - LB
```

where `H` is the recognized task horizon.

The report also provides:

```text
wall_clock_headroom =
    wall_clock - LB
```

but the certified task-horizon comparison is the primary invariant.

---

# Part 18 — Heuristic Replay

`T_C` is a deterministic feasible replay.

It is used for:

* scheduler comparison;
* capacity sweep;
* model slack;
* what-if analysis.

It is not used for primary attribution.

```text
model_slack = T_C - LB
```

A large model slack indicates the replay model itself is leaving opportunity on the table.

It does not prove the real BuildStream scheduler did so.

---

# Part 19 — Capacity Sweep

Sweep:

```text
PROCESS / builders
DOWNLOAD / fetchers
UPLOAD / pushers
```

Report:

```text
capacity
predicted T_C
normalized improvement
knee
```

The result is presented as a **shape**, not an exact runtime prediction.

---

# Part 20 — Wall-Clock Share

For every recognized task:

```text
share(t) =
    ∫ execution(t) 1 / n(τ) dτ
```

where:

```text
n(τ) = number of concurrently executing recognized tasks
```

This represents the task's marginal share of active wall time.

Properties:

```text
task running alone:
    receives full wall-clock credit

task running alongside 15 others:
    receives 1/16 credit
```

Across all tasks:

```text
Σ share(t) = active_task_wall_time
```

This metric requires no graph.

It is therefore a core M0 diagnostic.

---

# Part 21 — Ready Queue Depth

For each instant:

```text
ready_queue_depth(t)
```

is the number of tasks that are:

```text
dependency-ready
resource-ready
not currently executing
```

The timeline is reported as:

```text
average ready queue depth
peak ready queue depth
time with non-zero queue
```

This helps distinguish:

```text
nothing was ready
```

from:

```text
work was ready but not dispatched
```

and therefore makes `SCHEDULER_WAIT` evidence-based.

---

# Part 22 — Concurrency

## 22.1 Average Task Concurrency

```text
average_task_concurrency =
    Σ task_execution_duration / H
```

This is the time-average number of simultaneously executing recognized tasks.

---

## 22.2 Resource Occupancy

For resource `p`:

```text
average_occupancy(p) =
    Σ duration(tasks requiring p) / H
```

Also report:

```text
peak_occupancy(p)
capacity(p)
```

---

# Part 23 — Wait-to-Execution Ranking

The primary ranking metric is bounded:

```text
wait_share(t) =
    wait(t) / (wait(t) + execution(t))
```

with:

```text
0 <= wait_share < 1
```

This avoids pathological rankings for cached or near-zero-duration tasks.

The raw ratio is also available:

```text
raw_wait_to_execution =
    wait / max(execution, epsilon)
```

but is secondary.

---

# Part 24 — Leaf and Deferrability Analysis

## 24.1 Element Leaf

A leaf is defined on the **element graph**, not the task graph.

Terminal task kinds are excluded.

A task is potentially terminal only when its corresponding element is terminal in the relevant element dependency graph.

---

## 24.2 Requested Target Reachability

Do not define required work using:

```text
is_required_target
```

alone.

Instead compute:

```text
reachable_from_any_requested_target
```

using reverse reachability.

An element is potentially deferrable when:

```text
not reachable_from_any_requested_target
```

subject to the selected dependency scope.

---

## 24.3 Leaf Criticality

Report tasks/elements that are:

```text
leaf
AND
on observed blame chain or critical path
AND
not reachable from requested targets
```

These are candidates for:

```text
deferral
decoupling
post-build testing
separate pipeline
```

No automatic recommendation is made when the leaf is required by the requested target.

---

# Part 25 — Rebuild Blast Radius

For each element:

```text
reachable_downstream_count
```

is computed using reverse reachability.

Report:

```text
element
downstream count
downstream weighted duration
```

Example interpretation:

```text
core/libc.bst
    downstream elements: 1847
```

Historical extension:

```text
blast_radius × churn_rate
```

provides a prioritization signal for stabilization work.

---

# Part 26 — Criticality Probability

A single critical path can be unstable under small duration changes.

Run Monte-Carlo simulations:

```text
default:
    200 samples
    duration perturbation:
        ±10%
```

For every element:

```text
criticality_probability =
    P(element appears on longest path)
```

Report:

```text
element
P(critical)
observed slack
observed critical-path membership
```

This is advisory.

It is particularly useful for near-critical paths.

---

# Part 27 — Critical Path Resource Mix

Classify critical-path execution by:

```text
COMPUTE
NETWORK
CACHE_IO
OTHER
```

Default classification:

| Task/resource pattern   | Category |
| ----------------------- | -------- |
| FETCH / PULL / DOWNLOAD | NETWORK  |
| PUSH / UPLOAD           | NETWORK  |
| BUILD + PROCESS         | COMPUTE  |
| TRACK + PROCESS         | COMPUTE  |
| CACHE without PROCESS   | CACHE_IO |
| otherwise               | OTHER    |

Report:

```text
observed critical path
blame-chain execution
```

separately.

---

# Part 28 — Fetch / Build Overlap

Measure:

```text
FETCH interval
BUILD interval
```

overlap.

Report:

```text
fetch-only prefix
fetch/build overlap
build-only interval
```

A large fetch-only prefix indicates potentially avoidable startup latency.

This diagnostic is trace-only.

---

# Part 29 — Duration Variability

Across historical runs compute:

```text
mean
median
p50
p75
p95
coefficient_of_variation
```

for important task classes.

High coefficient of variation is a **trustworthiness warning** for derived rankings.

If duration variability is high:

```text
confidence in deterministic task ranking decreases
```

but the individual run's measured trace remains valid.

---

# Part 30 — Utilisation Axis

The utilization axis is independent from makespan attribution.

## 30.1 CPU Capacity

```text
capacity_cpu_s =
    effective_cpus × wall_clock
```

when CPU accounting is available.

---

## 30.2 Buckets

```text
useful
idle_no_tasks
idle_underparallel
wasted_retry
wasted_rebuild
untracked
```

---

## 30.3 Oversubscription

Potential oversubscription:

```text
builders × max_jobs > effective_cpus
```

is only a warning.

Evidence requires at least one of:

```text
high observed CPU utilization
duration degradation with concurrency
native build-job saturation
```

Otherwise:

```text
potential_oversubscription = true
evidence = LOW
```

---

# Part 31 — Task and Resource Model

## 31.1 Task Kinds

```text
TRACK
PULL
FETCH
BUILD
PUSH
OTHER
```

## 31.2 Resources

```text
PROCESS
DOWNLOAD
UPLOAD
CACHE
OTHER
```

## 31.3 Exclusive Resources

Example:

```yaml
resources:
  - CACHE

exclusive:
  - CACHE
```

---

# Part 32 — Data Contracts

Schemas:

```text
run-context/v9      graph/v9      trace/v9      analysis/v9   (inputs, and the analysis shape)
analyze/v5          compare/v2    blast/v2      correlate/v2  (published outputs - 32.5)
store/v1            store-aggregate/v1          whatif/v1     (published outputs - 32.5)
sweep/v1                                                      (what capacity buys - 32.5)
host/v2                                                       (the measuring machine - UX-186)
sources/v1                                                    (the source inventory - UX-171)
capture-layout/v1                                             (the capture directory - UX-381)
host-samples/v1                                               (the host while it built - UX-378)
bundle-manifest/v1                                            (a capture you can carry - UX-520)
plane2/v3           plane2/v2     plane2/v1                   (the Plane 2 report - UX-384)
analyze/v4          analyze/v3    analyze/v2                  (read, never written - UX-535)
compare/v1          blast/v1      correlate/v1                  (read, never written - UX-341)
host/v1                                                       (read, normalised in - UX-341)
```

---

## 32.1 run-context/v9

```json
{
  "trace_epsilon_us": 50000,
  "wall_clock": {},
  "host": {},
  "resource_capacities": {},
  "max_jobs": {},
  "cpu_accounting": {}
}
```

---

## 32.2 graph/v9

```json
{
  "elements": [
    {
      "uid": "core/libc.bst",
      "cache_key": "sha256:...",
      "requested_target": false
    }
  ]
}
```

Derived:

```text
in_degree
out_degree
unweighted_depth
reachable_downstream_count
leaf_status
dominator_status
```

---

## 32.3 trace/v9

```json
{
  "spans": [
    {
      "task_key": "core/libc.bst|BUILD|BUILD|0",
      "ts_us": 1000000,
      "dur_us": 42000000,
      "resources": ["PROCESS", "CACHE"],
      "primary_resource": "PROCESS"
    }
  ],
  "phases": [
    {
      "name": "load",
      "ts_us": 0,
      "dur_us": 92000
    }
  ]
}
```

Phases remain independent source intervals.

---

## 32.4 analysis/v9

```json
{
  "attribution": {},
  "occupancy": {},
  "timeline": {},
  "floors": {
    "t_infinity_observed": 1092000000,
    "t_infinity_cold": null,
    "lb": 1264000000,
    "certified_headroom": 647000000
  },
  "signals": {
    "wall_clock_share": {},
    "leaf_critical_tasks": [],
    "wait_to_execution_top": [],
    "criticality_probability": {},
    "blast_radius": [],
    "critical_path_resource_mix": {},
    "ready_queue": {},
    "concurrency": {},
    "fetch_build_overlap": {},
    "duration_variability": {}
  },
  "utilisation": {},
  "model": {},
  "confidence": {},
  "violations": []
}
```

## 32.5 The published output schemas (`UX-190`)

`analysis/v9` above is the *shape of the analysis*, which the spec
defines. What `bga` actually writes to stdout under `--format json` is
a document built from it, and until `UX-190` that document declared no
version at all - so a consumer had nothing to pin, and a field rename
in a published payload (`runs_outside_band` → `edges_outside_band`,
round 19) reached them silently.

Every published output now self-declares, with `schema` as its first
key:

| output | schema | printed by |
|---|---|---|
| `bga analyze --format json` (and every section subcommand) | `analyze/v5` | `bga analyze --schema` |
| `bga compare --format json` | `compare/v2` | `bga compare --schema` |
| `bga blast --format json` | `blast/v2` | `bga blast --schema` |
| `bga correlate --format json` | `correlate/v2` | `bga correlate --schema` |
| `bga snapshot --list --format json` | `store/v1` | `bga analyze --schema` lists every id |
| `bga snapshot --aggregate --format json` | `store-aggregate/v1` | as above |
| `bga whatif --format json` | `whatif/v1` | as above |
| `bga sweep --format json` | `sweep/v1` | as above |
| the host manifest inside `run-context.json` | `host/v2` | `bga.hostinfo.collect` |
| the source inventory at `sources.json` in a run directory | `sources/v1` | `bga.sources.build_inventory` |
| the Plane 2 report at `plane2.json` beside a run | `plane2/v3` | `bga.plane2` |
| the capture directory `.bga/` itself - every path, what writes it, what reads it, and what an absence means (32.6) | `capture-layout/v1` | `bga.run_store` |
| the host's memory and swap while the build ran, at `host-samples.jsonl` beside a run | `host-samples/v1` | `bga.run_store` names it (`OWNED`); `tools/bst_native_build_tracer.py` writes it |
| the manifest inside a run bundle: each member's path, presence and contract version, and the `bga` that packed it, so the receiving side recognises and refuses a bundle it cannot read in full (`UX-520`) | `bundle-manifest/v1` | `bga.bundle` |
| the Plane 2 report a capture before `UX-384` wrote - read, never written | `plane2/v2` | `bga.plane2.SUPERSEDED` |
| the Plane 2 report a capture before `UX-297` wrote - read, never written | `plane2/v1` | `bga.plane2.SUPERSEDED` |
| what `analyze`, `compare`, `blast` and `correlate` wrote before `UX-341` unified the units, what `analyze` wrote before `UX-344` lifted its two namespaces, and what it wrote before `UX-535` published the graph's shape once - read, never written | `analyze/v4`, `analyze/v3`, `analyze/v2`, `compare/v1`, `blast/v1`, `correlate/v1` | `bga.schemas.SUPERSEDED` |
| the host manifest with `memory_mb` where `host/v2` has `memory_bytes` - read and normalised, never written | `host/v1` | `bga.hostinfo.SUPERSEDED` |

The six above the retired rows are **written but not printable**: they
are on-disk shapes a run directory carries, not documents a subcommand
emits, so `--schema` does not know them. `bga.contracts.unprintable()`
less `superseded()` names that difference rather than leaving a reader
to discover it at a refusal.

`plane2/v1` is a fifth kind again: **read and never written**
(`UX-297`), and `UX-341` added five more of it - the four documents
whose units it renamed, and the host manifest, which is converted on
the way in so an old baseline still compares rather than reading as a
different machine. Every capture taken before that item embedded its whole
per-process record list in the report - 99.9% of the document on a
200,000-process trace, and read by nothing - and those stores still
analyze. `bga.contracts.superseded()` names the shapes a release still
opens, because what a release *supports* and what it *emits* are
different facts a consumer needs separately.

**The inputs are a third kind** (`UX-540`). `run-context/v9`,
`graph/v9` and `trace/v9` are stamped by whatever produced the capture
and read by `bga.ingest`, so they are in neither set above - they are
what a release *accepts*, and `bga analyze` refuses without all three:

| input | schema | read by |
|---|---|---|
| the run's identity, host manifest and scheduler configuration (32.1) | `run-context/v9` | `bga.ingest.READS` |
| the declared element graph, from `bst show` (32.2) | `graph/v9` | as above |
| the scheduler's own spans and phases (32.3) | `trace/v9` | as above |

`bga.contracts.reads()` names those three and `ids()` does not, because
what a release accepts and what it emits are two questions. `analysis/v9`
(32.4) is not a fourth input: it is the analyzer's in-memory result shape
(`bga.ingest.models.AnalysisResult`), stamped on no artifact, parsed
from none, and reaching a consumer only as `analyze/v5`.

The list is not maintained by hand alone: a guard asserts that every id
in `bga.contracts.ids()` appears here and in `docs/design/architecture.md`'s
contract inventory, so a new payload cannot ship undocumented. The
inventory is derived from the package rather than from a list, because
`UX-248` measured what a list costs: `sources/v1` was written to every
run directory for nine rounds while appearing in no registry, no guard
and no document.

**The versioning rule**: a field *rename or removal* bumps the version;
an *addition* does not. So `additionalProperties` is true in all three,
and a consumer that pins `analyze/v5` keeps working while the tool
grows.

The schemas live in one place, `bga/schemas.py`, which the renderers
are built against and `--schema` prints from - they cannot be a
hand-written copy drifting from the payload. A round-trip guard
validates the golden run's real output against them
(`tests/unit/test_output_schemas.py`).

They pin the top level only: the always-present keys, their types, and
the `schema` key. Enumerating every nested object would be a second
implementation of the renderer, drifting from the first.

---

## 32.6 The capture directory (`capture-layout/v1`, `UX-381`)

32.5 says what every *document* answers for. This says what the
*directory* they live in answers for — the thing a user pastes into an
issue, tars up, and hands to CI.

Every published `bga` command line names a path inside `.bga/`, and the
tool prints them itself at the end of every capture. `@last` and
`@prev` resolve by listing `runs/`; `bga view` reads `run/`; `bga
correlate` finds `plane2.json` as a sibling; `bga timeline` reads
`plane2.log.gz` and `build.log`; the store aggregator walks the lot.
The layout was load-bearing in a dozen places and stated in none — the
registry above named one of its twenty paths, and the only file-layout
table in the documentation described a **different** directory (the CI
field-capture bundle, `docs/design/capture-workflow.md`, which now says
so).

**Presence has three values, not two.** "Not there" means three
different things here, and a consumer that cannot tell them apart
cannot tell a broken capture from a cheap one:

| presence | what an absence means |
|---|---|
| `required` | the capture is unusable, and the tool refuses rather than reporting an empty result |
| `conditional` | that option was off, or that stage did not run. Every consumer of the path says so rather than substituting a zero |
| `derived` | nothing. It is a cache or a convenience and is rebuilt on demand |

| path | presence | contract | what it is |
|---|---|---|---|
| `.bga/` | required | — | the project-local store `UX-126` introduced. Everything below is relative to it; `bga` creates it on the first capture. |
| `.bga/.gitignore` | derived | — | written once so a clone does not ship the capture archive (`UX-189`). Absent only in a store made before that item; the next capture writes it. |
| `.bga/config` | conditional | — | the store's own settings, written when one is set. Absent means every setting is at its default. |
| `.bga/tmp/` | derived | — | `bga`'s scratch: the `$PATH` shim, the compiled hook and spine, and unnamed intermediates (`UX-155`). Never read across captures; safe to delete. |
| `.bga/runs/` | required | — | one directory per capture, named by UTC stamp. `@last` and `@prev` resolve by listing it, so its ordering is part of the contract: the names sort chronologically as strings. |
| `.bga/runs/<stamp>/` | required | — | one capture: the snapshot `bga snapshot --list` enumerates and `@last` names. The stamp is UTC and sorts chronologically as a string, which is what makes the listing an ordering. |
| `.bga/runs/<stamp>/run/` | required | — | the run directory - the unit every published command line takes a path to. Absent on a build that failed before any element completed (`UX-156`), which is a capture with nothing to analyse rather than a corrupt one. |
| `.bga/runs/<stamp>/run/graph.json` | required | `graph/v9` | the declared element graph, from `bst show`. |
| `.bga/runs/<stamp>/run/trace.json` | required | `trace/v9` | the scheduler's own spans and phases - Plane 1. |
| `.bga/runs/<stamp>/run/run-context.json` | required | `run-context/v9` | what the run was: identity, host manifest (`host/v2` inside it), scheduler configuration, and the resolved `native_max_jobs` (`UX-377`). |
| `.bga/runs/<stamp>/run/chrome_trace.json` | derived | — | the Plane 1 trace in the legacy Chrome JSON shape. Present only on a capture taken before `UX-452`: the extraction wrote it for a person to drag into perfetto.dev, `UX-437`'s census measured that no reader opens it, and `bga timeline --format chrome` renders the same shape on demand from `trace.json`. Safe to delete; nothing rewrites it. |
| `.bga/runs/<stamp>/run/sources.json` | conditional | `sources/v1` | the source inventory (`UX-171`), read by `bga blast`. Absent means the capture could not resolve the project's sources, and `blast` says so rather than reporting an empty inventory. |
| `.bga/runs/<stamp>/plane2.json` | conditional | `plane2/v3` | the Plane 2 report - what ran inside the sandboxes. Absent on a capture taken without Plane 2, and every Plane 2 section of every output is then absent rather than empty. |
| `.bga/runs/<stamp>/plane2.log.gz` | conditional | — | the raw per-process trace the report was folded from, gzipped. `bga timeline` renders from this; absent means no timeline, which is a different absence from no report (`UX-329`). |
| `.bga/runs/<stamp>/plane2-resource.json` | conditional | — | the two capacity scalars, beside the report so the aggregator never opens the big file for them (`UX-296`). Absent where the report is. |
| `.bga/runs/<stamp>/host-samples.jsonl` | conditional | `host-samples/v1` | the host's memory and swap while the build ran, one JSON object per line (`UX-378`). Absent on a capture taken before that item or with sampling unavailable. |
| `.bga/runs/<stamp>/analyze.json` | conditional | `analyze/v5` | the analysis this capture published, so `bga view` renders rather than re-deriving (`UX-296`). Absent means the viewer parses the run itself, and the trace carries no graph structure (`UX-380`). |
| `.bga/runs/<stamp>/build.log` | conditional | — | the wrapped BuildStream log, kept because its first line records the real invocation (`UX-29`). `bga timeline` needs it and refuses without it. |
| `.bga/runs/<stamp>/element-slice.json` | conditional | — | which elements the capture was asked for, where it was asked for a slice rather than the whole project. |
| `.bga/runs/<stamp>/capture-context.txt` | conditional | — | what the capture did and why, in prose - the diagnostics `UX-146` writes. Never parsed. |
| `.bga/runs/<stamp>/.size` | derived | — | a cached size for this snapshot, so `--list` does not walk every run. Rebuilt when the tree signature changes; safe to delete. |

The names are values in `bga/run_store.py` and the statement is
`run_store.CAPTURE_LAYOUT` beside them, so the constants and this table
are one declaration rather than two.
`tests/unit/test_the_capture_directory_is_a_contract.py` walks a real
capture and holds the three equal: every path on disk is named here,
every `required` path is present, and this table matches the module.

---

## 32.7 Decisions the registry records

The Parts outside this one are read-only for a round, so a Part the
tool never built, a state the code cannot reach, or a figure that has
dated cannot be corrected where it is written. It is decided here
instead, and a reader meets the answer beside the claim rather than
filing it a second time. Every row below is held by a guard.

### 32.7.1 Part 8.2's `ambiguous` holder state is retired (`UX-563`)

Part 8.2 and Part 42's "Holder set + `UNKNOWN`" row require an
unidentifiable resource holder to be reported as `blocking_tasks =
UNKNOWN, ambiguous = true`. **The occupancy-based holder model has no
such outcome.** `classify_resource_wait` reports a microsecond as
resource wait only where occupancy reached capacity, and capacity is at
least 1, so at least one real overlapping task is identified for every
microsecond it reports - "saturated but unexplained" is a state the old
time-overlap model had and this one cannot enter.

| what | where | value |
|---|---|---|
| the holder record's flag | `bga/attribution/blame_chain.py` | `'ambiguous': False`, the only value any code path writes |
| Part 33.4's `ambiguous_wait_time` term | `bga/validation/invariants.py` | a constant 0, and the attribution score is the other two terms |

So the hard rule stands unchanged - **never invent a holder** - but it
is enforced by the model rather than by a flag: there is no case in
which a plausible-looking blocker could be substituted, because a
blocker is only ever named from an occupancy count that already
contains it. `UNKNOWN` remains reserved; nothing writes it.

Reinstating the state would be a change to the holder model, not to the
flag. `tests/unit/test_a_retired_state_is_declared.py` holds the three:
no code path writes `True`, the confidence term is 0 on a real run, and
this note says so.

---

# Part 33 — Reconciliation and Confidence

## 33.1 Hard Gates

```text
ordering_violations == 0
critical_path_coverage == 1.0
dominator_coverage == 1.0
```

The blame-chain headline additionally requires:

```text
blame_chain_coverage == 1.0
```

---

## 33.2 Soft Gates

Default:

```text
task_coverage >= 0.95
duration_coverage >= 0.98
```

---

## 33.3 Utilization Reconciliation

When CPU accounting is available:

```text
sum(reported_cpu_buckets)
```

must be within:

```text
2%
```

of:

```text
capacity_cpu_s
```

The difference is explicitly reported as:

```text
unaccounted_cpu_s
```

rather than silently forcing categories to sum.

---

## 33.4 Confidence

Primary confidence:

```text
confidence =
    min(
        provenance_score,
        coverage_score,
        model_score,
        attribution_score
    )
```

Attribution score considers:

```text
untracked_time
ambiguous_wait_time
violation_time
```

but does not penalize legitimate phase overlap.

Cold confidence is independent:

```text
cold_confidence
```

---

# Part 34 — Core Invariants

## I1 — Certified Lower Bound

```text
H >= LB
```

where:

```text
H =
    max(finish(recognized tasks))
    -
    min(start(recognized tasks))
```

---

## I2 — Replay

```text
T_C >= LB
```

---

## I3 — Structural Path

```text
T∞,observed >= max(observed task duration)
```

---

## I4 — Attribution Identity

For the selected horizon:

```text
Σ attribution_duration == H
```

exactly.

---

## I5 — Non-Negativity

```text
all attribution durations >= 0
```

---

## I6 — Occupancy Capacity

Observed resource occupancy may not exceed declared capacity unless:

```text
capacity violation is explicitly explained
```

---

## I7 — Blame Coverage

The primary blame-chain headline requires:

```text
blame_chain_coverage == 1.0
```

---

## I8 — Run Identity

All analysis inputs must belong to the same run identity.

---

## I9 — CPU Reconciliation

When CPU accounting is available:

```text
abs(
    sum(cpu_buckets) - capacity_cpu_s
)
<=
0.02 × capacity_cpu_s
```

and:

```text
unaccounted_cpu_s
```

is explicitly reported.

---

## I10 — Timeline Integrity

The final flattened timeline is:

```text
ordered
contiguous
non-overlapping
```

---

## I11 — Determinism

Repeated analysis of the same normalized input produces:

```text
identical graph metrics
identical attribution
identical blame chain
identical diagnostics
```

---

## I12 — Cold Isolation

`T∞,cold` never participates in:

```text
LB
certified_headroom
primary confidence
measured attribution
```

---

## I13 — Cold Publication

`T∞,cold` is not published unless:

```text
cold_critical_path_coverage == 1.0
```

or the user explicitly enables partial estimation.

---

# Part 35 — Determinism Contract

All ordering operations must define a total ordering.

The primary dependency-hop ordering is:

```text
1. normalized finish timestamp DESC
2. unweighted / weighted graph depth DESC
3. task key ASC
```

The resource-holder set is sorted by:

```text
task key ASC
```

No Python hash iteration order, dictionary order, filesystem order, or concurrency-dependent ordering may influence results.

A determinism harness runs the same analysis:

```text
N >= 100 times
```

and compares canonical serialized output.

---

# Part 36 — Testing Strategy

## 36.1 Synthetic Graph Tests

Cover:

```text
linear chain
diamond
fan-in
fan-out
multiple equal predecessors
deep unequal predecessors
independent branches
terminal tasks
requested/non-requested targets
```

---

## 36.2 Timestamp Tests

### Quantization

Input:

```text
100.00
100.04
100.08
epsilon = 0.05
```

Expected:

```text
deterministic quantized values
transitive equality
```

### Negative dependency offset

Small normalized negative gap:

```text
accepted
```

Large negative gap:

```text
ordering violation
```

---

## 36.3 Clamp Test

When:

```text
start < ready
```

after permitted normalization:

```text
start := ready
finish unchanged
duration := finish - start
```

---

## 36.4 Tie-Break Tests

Two predecessors:

```text
same finish
different depth
```

Expected:

```text
greater depth wins
```

Same depth:

```text
smallest task key wins
```

Adding an unrelated graph node must not change the result.

---

## 36.5 Resource Holder Tests

Test:

```text
one holder
multiple simultaneous holders
holder changes during wait
no identifiable holder
```

Expected output is a time-weighted holder set.

No resource-holder hop occurs in the dependency chain.

---

## 36.6 Phase Tests

Test:

```text
phase overlaps execution
phase overlaps dependency wait
phase overlaps resource wait
phase overlaps idle
multiple overlapping phases
```

Expected:

```text
underlying causal category remains unchanged
phase appears only as annotation
```

---

## 36.7 Occupancy Tests

Test:

```text
single task
overlapping tasks
nested intervals
zero-duration tasks
adjacent intervals
gaps
head
tail
```

Verify exact sweep invariants.

---

## 36.8 Attribution Tests

Verify:

```text
Σ attribution == H
```

with integer equality.

---

## 36.9 CPU Reconciliation Tests

Test:

```text
exact reconciliation
<2% unaccounted
>2% unaccounted
missing CPU accounting
```

---

## 36.10 Cold Floor Tests

### No history

```text
T∞,cold = unavailable
```

### Same cache-key history

```text
historical duration used
```

### Partial coverage

```text
unavailable by default
```

### Explicit override

```text
partial=true
confidence=low
```

---

## 36.11 Criticality Monte-Carlo Tests

Use a deterministic random seed.

Verify:

```text
same input + same seed
=
same probabilities
```

Also verify probability bounds:

```text
0 <= P(critical) <= 1
```

---

# Part 37 — CLI

Recommended command structure:

```text
bga analyze RUN
bga graph RUN
bga floors RUN
bga replay RUN
bga sweep RUN
bga utilisation RUN
bga diagnostics RUN
```

---

## 37.1 Cold Analysis

Default:

```text
bga floors RUN
```

reports:

```text
T∞,observed
```

Optional:

```text
bga floors RUN --cold
```

enables trustworthy historical cold analysis.

Optional:

```text
bga floors RUN \
    --cold \
    --allow-partial-cold
```

enables explicitly heuristic partial estimation.

---

# Part 38 — Report Structure

Recommended report:

```text
BGA BUILD EFFICIENCY REPORT

RUN SUMMARY
    Wall clock
    Task horizon
    Recognized tasks
    Coverage

MEASURED WALL-CLOCK ATTRIBUTION
    Execution
    Dependency wait
    Resource wait
    Scheduler wait
    Retry wait
    Idle
    Untracked head
    Untracked tail

TASK-LEVEL SIGNALS
    Wall-clock share
    Wait-to-execution
    Leaf criticality
    Ready queue

STRUCTURAL ANALYSIS
    T∞ observed
    Unweighted depth
    Critical path
    Slack
    Criticality probability

RESOURCE ANALYSIS
    Critical-path resource mix
    Resource occupancy
    Exclusive stalls

REBUILD LEVERAGE
    Blast radius
    Churn × blast radius

REFERENCE FLOORS
    T∞ observed
    T∞ cold
    LB
    Certified headroom

COUNTERFACTUAL MODEL
    T_C
    Model slack
    Capacity sweep
    Knee

CPU UTILISATION
    Useful
    Idle
    Retry
    Rebuild
    Untracked
    Unaccounted

TRACE QUALITY
    Coverage
    Ordering violations
    Duration variability
    Confidence

RECOMMENDATIONS
```

Recommendations must be generated from measured signals and clearly distinguish evidence from interpretation.

---

# Part 39 — Implementation Architecture

Recommended Python package:

```text
bga/
    ingest/
        run_context.py
        trace.py
        graph.py

    normalize/
        timestamps.py
        intervals.py

    occupancy/
        sweep.py
        tasks.py
        resources.py
        ready_queue.py

    graph/
        edg.py
        reachability.py
        depth.py
        dominators.py
        critical_path.py
        slack.py
        criticality.py

    attribution/
        blame_chain.py
        dependency_gate.py
        resource_wait.py
        scheduler_wait.py
        retry.py
        timeline.py

    floors/
        observed.py
        capacity.py
        serialization.py
        cold.py

    replay/
        scheduler.py
        sweep.py

    utilisation/
        cpu.py
        oversubscription.py

    diagnostics/
        wall_share.py
        wait_ratio.py
        blast_radius.py
        resource_mix.py
        fetch_build.py
        variability.py

    report/
        text.py
        json.py

    validation/
        invariants.py
        determinism.py
```

---

# Part 40 — Milestone Plan

## M0 — Trace Normalization and Occupancy Core

### Goal

Build the architectural core from which all trace-only measurements derive.

### Deliverables

* `trace/v9` ingestion;
* integer-microsecond timestamps;
* deterministic quantization;
* interval normalization;
* sweep-line occupancy engine;
* active task sets;
* resource occupancy;
* wall-clock horizon;
* task horizon;
* head/tail;
* idle integral;
* push tail;
* exclusive-resource stalls;
* duration histogram;
* retry cost;
* basic phase annotations;
* average concurrency;
* wall-clock share;
* ready-queue depth;
* fetch/build overlap;
* text and JSON output.

### Exit Criteria

For golden traces:

```text
occupancy reconstruction is deterministic
all intervals are normalized
all trace-only metrics reconcile exactly
```

M0 does **not** implement:

```text
blame chain
dependency attribution
interval eclipsing
```

---

# M1 — Graph Model and Structural Analysis

### Goal

Build the static dependency model.

### Deliverables

* `graph/v9` ingestion;
* dependency scopes;
* EDG;
* task-key normalization;
* element graph;
* unweighted depth;
* weighted depth;
* reachability;
* downstream blast radius;
* requested-target reverse reachability;
* leaf classification;
* dominators;
* critical path;
* slack spectrum;
* `T∞,observed`;
* critical-path resource mix.

### Exit Criteria

Synthetic graphs produce expected:

```text
reachability
depth
dominators
critical paths
T∞
```

Adding unrelated graph nodes does not change causal tie-breaking.

---

# M2 — Dependency Blame Chain

### Goal

Implement the measured causal model.

### Deliverables

* backward dependency walk;
* ready-time calculation;
* dependency gate;
* deterministic dependency selection;
* execution attribution;
* dependency waits;
* retry gate;
* scheduler gate;
* resource-wait classification;
* holder-set annotation;
* phase annotations;
* blame-chain coverage;
* attribution reconciliation.

### Exit Criteria

For synthetic and golden real traces:

```text
Σ attribution == H
```

exactly.

Repeated analyses produce identical chains.

---

# M3 — Certified Floors and Replay

### Goal

Implement reference scheduling models.

### Deliverables

* resource-area bounds;
* exclusive serialization bounds;
* `LB`;
* certified headroom;
* deterministic replay;
* resource sets;
* exclusive resources;
* `T_C`;
* model slack;
* capacity sweep;
* knee detection.

### Exit Criteria

```text
H >= LB
T_C >= LB
```

and replay is deterministic.

Sweep results are monotonic where theoretically expected.

---

# M4 — CPU Utilisation

Can proceed in parallel with M1–M3 when CPU accounting is available.

### Deliverables

* effective CPU calculation;
* cgroup quota handling;
* CPU buckets;
* unaccounted bucket;
* 2% reconciliation tolerance;
* oversubscription evidence;
* concurrency/degradation regression where historical data permits.

### Exit Criteria

The analyzer distinguishes:

```text
potential oversubscription
observed saturation
insufficient evidence
```

without treating configuration alone as proof.

---

# M5 — Advanced Diagnostics

### Goal

Add high-value structural diagnostics that rely on already-established primitives.

### Deliverables

* wall-clock share;
* ready queue depth refinements;
* blast radius;
* churn × blast radius;
* criticality probability;
* fetch/build overlap;
* duration coefficient of variation;
* advanced leaf analysis;
* historical baseline comparison.

### Exit Criteria

The diagnostics are deterministic, covered by fixtures, and do not alter primary attribution.

---

# M6 — Cold Structural Analysis

### Goal

Add advisory cold-cache modeling.

### Deliverables

* historical duration store;
* cache-key history;
* element/task cohort history;
* cold source hierarchy;
* `T∞,cold`;
* cold coverage;
* cold confidence;
* explicit partial estimation.

### Exit Criteria

Cold analysis never changes:

```text
LB
certified_headroom
primary confidence
measured attribution
```

---

# Part 41 — Performance Requirements

`bga` is expected to operate on large BuildStream graphs.

Target characteristics:

```text
N = number of tasks
E = dependency edges
S = trace spans
```

Expected dominant complexity:

```text
trace normalization: O(S log S)
occupancy sweep:     O(S log S)
graph construction:  O(N + E)
reachability:        O(N + E) where DAG-specific traversal permits
critical path:       O(N + E)
blast radius:        O(N + E) with reverse traversal / memoization
```

Avoid:

```text
O(N²)
```

for routine diagnostics.

---

## 41.1 Memory

Do not retain every sweep interval as a Python object when a compact event representation is sufficient.

Prefer:

```text
sorted events
active-set IDs
compact segment arrays
```

for large traces.

---

## 41.2 Critical Path Monte-Carlo

The default:

```text
200 samples
```

should reuse the graph topology and avoid rebuilding graph structures.

Only durations and dynamic programming values vary.

---

## 41.3 Historical Data

Historical duration lookup must be indexed by:

```text
cache_key
element_uid + task_kind + phase
cohort
```

to avoid scanning historical runs per task.

---

# Part 42 — Risks and Mitigations

| Risk                                               | Impact                         | Mitigation                                                     |
| -------------------------------------------------- | ------------------------------ | -------------------------------------------------------------- |
| Timestamp epsilon hides real ordering problems     | False confidence               | Quantize once; report normalization; keep epsilon configurable |
| Clock skew exceeds epsilon                         | Invalid ordering               | Capture-layer normalization; fail loudly                       |
| Blame chain has ambiguous dependency gate          | Reduced attribution confidence | Deterministic depth/key selection; mark ambiguity              |
| Resource blocker is not identifiable               | Incorrect causal claim         | Holder set + `UNKNOWN`; never invent a blocker                 |
| Scheduler wait is ambiguous                        | Misleading scheduler diagnosis | Ready queue + occupancy evidence                               |
| Background phase overlaps task work                | Double counting                | Phase is annotation, never a competing category                |
| Cached tasks collapse observed critical path       | Cross-run volatility           | Report observed floor + unweighted depth + advisory cold floor |
| Cold estimate lacks evidence                       | False structural conclusion    | Default unavailable                                            |
| CPU accounting has residuals                       | False exactness                | Explicit `unaccounted` bucket and 2% tolerance                 |
| Large graph causes quadratic analysis              | Slow analyzer                  | DAG traversals, memoization, compact representations           |
| Critical path changes under small perturbation     | Fragile recommendation         | Monte-Carlo criticality probability                            |
| High task duration variance                        | Unstable rankings              | CV trustworthiness warning                                     |
| Adding unrelated graph nodes changes attribution   | Non-reproducibility            | Depth + task-key tie-breaking                                  |
| Resource wait is mistaken for dependency causality | Wrong optimization target      | Resource holders remain annotations                            |

---

# Part 43 — Terminology

## Preferred

```text
Measured blame-chain attribution
Occupancy step function
Dependency-causal chain
Flattened timeline
Trace epsilon
Observed structural floor
Advisory cold structural floor
Certified headroom
Model slack
Leaf critical task
Wait share
Wall-clock share
Ready queue depth
Resource holder set
Criticality probability
Rebuild blast radius
Critical-path resource mix
```

## Avoid

```text
Interval eclipsing
Absolute graph time
Pure configuration overhead
Mathematically optimal schedule
Exact runtime inefficiency
True minimum build time
Cold floor as certified bound
Resource blocker as causal predecessor
```

---

# Part 44 — Final Semantic Contract

`bga` v9 promises:

1. **Trace measurements are based on normalized integer-microsecond intervals.**
2. **Occupancy is the primitive trace-analysis object.**
3. **The blame chain follows dependency causality only.**
4. **Resource waits expose holder sets instead of inventing a single causal blocker.**
5. **PHASE is an annotation on measured gaps, not a competing wall-clock category.**
6. **The final attribution timeline is contiguous, non-overlapping, and exactly reconcilable.**
7. **Observed structural floors use observed durations only.**
8. **Certified headroom is based only on certified observed bounds.**
9. **Cold structural analysis is advisory and never silently invented.**
10. **Replay and capacity sweeps are counterfactual models, not measurements.**
11. **CPU utilization is a separate axis from makespan attribution.**
12. **Deterministic tie-breaking is causal and stable under unrelated graph growth.**
13. **Ready-queue depth distinguishes scheduler starvation from lack of ready work.**
14. **Wall-clock share provides a graph-independent marginal-sensitivity ranking.**
15. **Blast radius identifies structurally expensive elements to change.**
16. **Criticality probability identifies robustly critical and near-critical elements.**
17. **Duration variability is treated as a trustworthiness signal.**
18. **All hard invariants use exact integer arithmetic wherever possible.**

Final principle:

> **Measure what happened. Certify what cannot be improved. Model what might happen. Never confuse the three.**
