# UX-18: `tools/bst_run_context.py` (the standalone producer) doesn't capture `native_max_jobs`/`cpu_budget`/`host_cpu_count`

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** `UX-12`, `UX-15`

## Motivation

Raised by an external review, checking whether `UX-12`/`UX-15`'s new fields are available consistently across `bga`'s documented ingestion paths, not just the one path most recently touched.

`docs/spec/ingestion-pipeline.md` documents three independent "producer pieces" a user can invoke directly: `tools/bst_log_to_chrome_trace.py` (+ `tools/chrome_trace_to_bga_trace.py`) for `trace.json`, `tools/bst_show_to_graph.py` for `graph.json`, and **`tools/bst_run_context.py`** for `run-context.json` - with `tools/bst_extract_run.py` as a convenience coordinator over all three, not the only supported entry point.

Confirmed directly: `tools/bst_run_context.py` has zero references to `native_max_jobs`, `cpu_budget`, or `host_cpu_count` anywhere in the file. It still only produces `resource_capacities`/`max_jobs`/`cpu_accounting` (its original `P4-09` scope). A user following `docs/spec/ingestion-pipeline.md`'s own documented per-tool pipeline (rather than the `bst_extract_run.py` convenience wrapper) gets a `run-context.json` silently missing every field `UX-12`/`UX-15` added - no error, no warning, just absence, indistinguishable from "this run genuinely has no native_max_jobs data" (which is itself a valid, common state) versus "this producer doesn't know how to capture it at all."

This creates two ingestion APIs with silently different capabilities:

```text
tools/bst_extract_run.py   --native-max-jobs N --cpu-budget N   -> full UX-12/15 fields
tools/bst_run_context.py   (no equivalent flags exist)          -> UX-12/15 fields always absent
```

## Required Fix

Pick one, don't leave the divergence unresolved:

1. **Preferred**: extract a single canonical `RunContext`-dict-building function (e.g. `tools/_run_context_builder.py` or similar) that both `tools/bst_run_context.py` and `tools/bst_extract_run.py` call, taking `native_max_jobs`/`cpu_budget` as optional parameters alongside the scheduler-config fields both already handle. `tools/bst_run_context.py` gains `--native-max-jobs`/`--cpu-budget` CLI flags mirroring `bst_extract_run.py`'s own. One implementation, two thin CLI wrappers.
2. **Acceptable fallback** if (1) turns out to need more restructuring than is worth it right now: add the same `--native-max-jobs`/`--cpu-budget` flags directly to `tools/bst_run_context.py` (duplicating the small amount of logic involved - it's just two optional dict keys, not the full extraction pipeline), and add a prominent docstring/comment on both files cross-referencing each other so a future field addition to one isn't silently forgotten on the other again.

Either way, `docs/spec/ingestion-pipeline.md` should state explicitly that both producers now support the same `run-context.json` field set, or explain any remaining, deliberate difference.

## Out of Scope

- Any other divergence between the two files unrelated to `UX-12`/`UX-15`'s specific fields - this task is scoped to closing the one gap found.

## Fix Implemented

Took Required Fix option 1 (preferred). New `tools/_run_context_common.py` holds the two pieces that had silently diverged: `host_cpu_count()` (moved verbatim from `bst_extract_run.py`'s own `_host_cpu_count`) and `add_cpu_capacity_fields(run_context, native_max_jobs=None, cpu_budget=None)`, which mutates a `run_context` dict in place adding `native_max_jobs`/`host_cpu_count`/`cpu_budget` with the same `is not None` semantics `UX-16` established (`0` is real, present data, not "missing"). Both `tools/bst_run_context.py`'s `build_run_context()` and `tools/bst_extract_run.py`'s `extract_run()` now call this one function instead of each carrying its own (in one case, entirely absent) copy. `tools/bst_run_context.py` gained matching `--native-max-jobs`/`--cpu-budget` CLI flags, argument-for-argument the same as `bst_extract_run.py`'s own. `docs/spec/ingestion-pipeline.md` gained a new empirically-confirmed-facts entry (#14) naming the divergence and the fix.

## Acceptance Test

1. `tools/bst_run_context.py --native-max-jobs N --cpu-budget N ...` (or equivalent) produces a `run-context.json` with both fields populated, matching what `bst_extract_run.py` would produce for the same inputs.
2. `docs/spec/ingestion-pipeline.md` no longer implies the two producers have silently different field coverage.
3. Full suite green.

## Verification Log

Done for real, 2026-08-16. New `tests/unit/test_run_context_common.py` (4 tests) covers the shared helper directly: `host_cpu_count()` returns a positive int; `add_cpu_capacity_fields` adds all three fields when given; omits `native_max_jobs`/`cpu_budget` (but not `host_cpu_count`, always auto-detected) when not given; distinguishes `0` from absent for both (regression guard against re-introducing `UX-16`'s bug class here). `tests/unit/test_bst_run_context.py` gained 4 new tests: fields captured when given, `host_cpu_count` always captured, fields omitted when not given, and a round-trip test through `bga`'s own `load_run_context` confirming the values reach `RunContext.native_max_jobs`/`cpu_budget`/`host_cpu_count` unchanged.

Full suite green: 514 passed (up from 506 - 8 new tests), same 7 pre-existing environment-only failures as `main` (real `bst`/`bst source track` unavailable in this environment - `test_bst_extract_run.py`, `test_bst_extract_run_strict.py`, `test_bst_checkout_cost.py`). `make lint` clean.

Real CLI re-verification, both producers given the same inputs:

```
$ python -m tools.bst_run_context <(printf '...same log as bst_extract_run would parse...') /tmp/rc-out.json \
    --format raw --start-time 2026-08-14T00:00:00+00:00 --native-max-jobs 4 --cpu-budget 6
Wrote run-context.json to /tmp/rc-out.json
$ cat /tmp/rc-out.json
{
  "trace_epsilon_us": 50000,
  "resource_capacities": {"PROCESS": 3, "DOWNLOAD": 7, "UPLOAD": 2},
  "max_jobs": 3,
  "wall_clock": {"start_us": 1786665600000000, "end_us": 1786665605000000},
  "native_max_jobs": 4,
  "host_cpu_count": 4,
  "cpu_budget": 6
}
```

`native_max_jobs`/`host_cpu_count`/`cpu_budget` all present - matches `bst_extract_run.py`'s own field set for the same inputs (confirmed by the round-trip test above going through the identical `add_cpu_capacity_fields` call both tools now share).
