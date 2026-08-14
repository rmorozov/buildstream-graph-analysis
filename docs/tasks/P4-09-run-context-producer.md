# P4-09: `run-context.json` producer from a real BuildStream invocation

**Priority:** P4 | **Status:** 🔴 Not Started | **Depends on:** none (independent of `P4-10`, though `P4-10` will call this)

## Spec Reference
Part 32.1 (`run-context/v9`): `trace_epsilon_us`, `wall_clock` (`start_us`/`end_us`), `host`, `resource_capacities`, `max_jobs`, `cpu_accounting`.

## Background
Read `docs/ingestion-pipeline.md` first - this is the second of the two remaining pieces `P4-08` split off (graph.json, from `bst show`, is done). Unlike `graph.json`, `run-context.json` has **no `bst show` equivalent** - `bst show` is purely static project introspection and has no notion of runtime resource capacity, wall-clock bounds, or CPU accounting. This data has to come from the real invocation's own environment/config instead.

## Required Fix
1. `max_jobs`/`resource_capacities`: BuildStream's own config exposes builder/fetcher/pusher job counts (`bst --builders`/`--fetchers`/`--pushers` CLI flags, or the project's `.bst`/user config file) - determine the right source (CLI flags used for the real invocation being analyzed take precedence over config-file defaults) and extract from there, not by guessing at "the number of CPUs available on this machine" (a `PROCESS` capacity of 4 configured via `--builders 4` is what actually constrained the real build, regardless of how many cores the host has).
2. `wall_clock`: if a wrapper log is available (the `P4-05` trace path), reuse its own `bst-invocation` start/end timestamps (`tests/fixtures/synthetic_multi_subproject/generate_fixture.py` already does exactly this for its own synthetic run_context - same technique, real data). If only a raw `bst` log is available (no wrapper), derive from BuildStream's own log timestamps directly.
3. `cpu_accounting.effective_cpus`: without this, `bga`'s CPU reconciliation (Part 33.3) falls back to a default of `1.0`, producing spurious reconciliation-error warnings on any genuinely concurrent build - confirmed and fixed for two of this repo's own fixtures already (`P3-01`'s `tests/fixtures/topologies.py`, `P1-27`'s fix to `tests/fixtures/synthetic_multi_subproject/generate_fixture.py`). A real producer must set this from the same `max_jobs`/builder-count source as (1), not leave it unset and reproduce the same class of spurious-warning bug those fixtures already hit and fixed.

## Out of Scope
- Don't try to derive `resource_capacities` from `bst show` - confirmed in `P4-08`'s research that `bst show` has no notion of runtime capacity at all, only static dependency/cache-key data.

## Acceptance Test
Run against a real (or realistically-simulated) BuildStream invocation with a known `--builders`/`--fetchers` configuration and a captured wrapper log; the produced `run-context.json` matches the known configuration exactly, and feeding it alongside `P4-08`'s graph.json and a real trace.json into `bga analyze` produces a report with no spurious CPU-reconciliation warnings.

## Verification Log
_(append real command + output here once run, before marking 🟢)_
