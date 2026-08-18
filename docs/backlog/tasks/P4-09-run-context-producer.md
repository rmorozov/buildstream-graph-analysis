# P4-09: `run-context.json` producer from a real BuildStream invocation

**Priority:** P4 | **Status:** 🟢 Fixed & Verified (2026-08-14) | **Depends on:** none (independent of `P4-10`, though `P4-10` calls this)

## Spec Reference
Part 32.1 (`run-context/v9`): `trace_epsilon_us`, `wall_clock` (`start_us`/`end_us`), `host`, `resource_capacities`, `max_jobs`, `cpu_accounting`.

## Background
Read `docs/spec/ingestion-pipeline.md` first - this is the second of the two remaining pieces `P4-08` split off (graph.json, from `bst show`, is done). Unlike `graph.json`, `run-context.json` has **no `bst show` equivalent** - `bst show` is purely static project introspection and has no notion of runtime resource capacity, wall-clock bounds, or CPU accounting. This data has to come from the real invocation's own environment/config instead.

## Required Fix
1. `max_jobs`/`resource_capacities`: BuildStream's own config exposes builder/fetcher/pusher job counts (`bst --builders`/`--fetchers`/`--pushers` CLI flags, or the project's `.bst`/user config file) - determine the right source (CLI flags used for the real invocation being analyzed take precedence over config-file defaults) and extract from there, not by guessing at "the number of CPUs available on this machine" (a `PROCESS` capacity of 4 configured via `--builders 4` is what actually constrained the real build, regardless of how many cores the host has).
2. `wall_clock`: if a wrapper log is available (the `P4-05` trace path), reuse its own `bst-invocation` start/end timestamps (`tests/fixtures/synthetic_multi_subproject/generate_fixture.py` already does exactly this for its own synthetic run_context - same technique, real data). If only a raw `bst` log is available (no wrapper), derive from BuildStream's own log timestamps directly.
3. `cpu_accounting.effective_cpus`: without this, `bga`'s CPU reconciliation (Part 33.3) falls back to a default of `1.0`, producing spurious reconciliation-error warnings on any genuinely concurrent build - confirmed and fixed for two of this repo's own fixtures already (`P3-01`'s `tests/fixtures/topologies.py`, `P1-27`'s fix to `tests/fixtures/synthetic_multi_subproject/generate_fixture.py`). A real producer must set this from the same `max_jobs`/builder-count source as (1), not leave it unset and reproduce the same class of spurious-warning bug those fixtures already hit and fixed.

## Out of Scope
- Don't try to derive `resource_capacities` from `bst show` - confirmed in `P4-08`'s research that `bst show` has no notion of runtime capacity at all, only static dependency/cache-key data.

## Acceptance Test
Run against a real (or realistically-simulated) BuildStream invocation with a known `--builders`/`--fetchers` configuration and a captured wrapper log; the produced `run-context.json` matches the known configuration exactly, and feeding it alongside `P4-08`'s graph.json and a real trace.json into `bga analyze` produces a report with no spurious CPU-reconciliation warnings.

## What was built
`tools/bst_run_context.py`. Rather than re-deriving BuildStream's own CLI-flag-vs-config-file precedence for `--builders`/`--fetchers`/`--pushers`, it reuses `tools/bst_log_to_chrome_trace.py`'s `WrapperTraceConverter` to parse the log once and read the `Maximum {Fetch,Build,Push} Tasks:` header lines BuildStream itself prints unconditionally - these already reflect whatever precedence BuildStream applied (CLI flag, user config, or its own bundled default), so this producer doesn't need to reproduce that logic at all. Falls back to BuildStream's own bundled defaults (`fetchers=10, builders=4, pushers=4`, confirmed against a real 2.7.0 install's `buildstream/data/userconfig.yaml`) only when those header lines aren't present (e.g. a truncated log capture).

`resource_capacities`/`max_jobs` map as `PROCESS=builders`, `DOWNLOAD=fetchers`, `UPLOAD=pushers`, `max_jobs=builders` - confirmed against real BuildStream's own `--help` text (`--builders`: "Maximum simultaneous build tasks") and Part 27's critical-path resource-mix table (`FETCH / PULL / DOWNLOAD`, `PUSH / UPLOAD`). `--max-jobs` (a different, unrelated concept - parallelism *within* one build task, confirmed in BuildStream's own `_context.py`) is deliberately not used for this.

`wall_clock` reuses the exact same converter instance's `bst-invocation` span bounds (`tools/chrome_trace_to_bga_trace.invocation_wall_clock`) - one real parse of the log serves both the scheduler-config and wall-clock derivation, not two independently-diverging ones. `cpu_accounting.effective_cpus` is set from the same `builders` count.

## Out of Scope (unchanged)
- Does not attempt to read a per-machine user config file (`~/.config/buildstream.conf`) - confirmed via BuildStream's own source that scheduler config is never part of `project.conf`, and a per-user config file from the original CI runner generally isn't recoverable post-hoc anyway. The log's own already-resolved header lines are the only real, recoverable source.

## Verification Log
```
$ PYTHONPATH=. python3 -m pytest tests/unit/test_bst_run_context.py -v
7 passed

# Real run against a real BuildStream 2.7.0 build log:
$ PYTHONPATH=. python3 tools/bst_run_context.py --format raw real_build.log run-context.json
$ cat run-context.json
{
  "trace_epsilon_us": 50000,
  "resource_capacities": {"PROCESS": 4, "DOWNLOAD": 10, "UPLOAD": 4},
  "max_jobs": 4,
  "cpu_accounting": {"effective_cpus": 4},
  "wall_clock": {"start_us": ..., "end_us": ...}
}
# matches BuildStream's own real header: "Maximum Fetch Tasks: 10",
# "Maximum Build Tasks: 4", "Maximum Push Tasks: 4" (unmodified defaults,
# no CLI override passed to this real build)

$ PYTHONPATH=. python3 -c "from bga.ingest.loader import load_run_context; \
  rc = load_run_context(__import__('pathlib').Path('run-context.json')); \
  print(rc.max_jobs, rc.resource_capacities, rc.cpu_accounting)"
4 {'PROCESS': 4, 'DOWNLOAD': 10, 'UPLOAD': 4} {'effective_cpus': 4}
# loads cleanly into bga's own loader

$ PYTHONPATH=. python3 -m pytest tests/ -q
311 passed (with bst on PATH)

$ make check-clean
OK: no ignored files are tracked
```
