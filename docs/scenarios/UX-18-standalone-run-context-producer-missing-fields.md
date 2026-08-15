# UX-18: `tools/bst_run_context.py` (the standalone producer) doesn't capture `native_max_jobs`/`cpu_budget`/`host_cpu_count`

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** `UX-12`, `UX-15`

## Motivation

Raised by an external review, checking whether `UX-12`/`UX-15`'s new fields are available consistently across `bga`'s documented ingestion paths, not just the one path most recently touched.

`docs/ingestion-pipeline.md` documents three independent "producer pieces" a user can invoke directly: `tools/bst_log_to_chrome_trace.py` (+ `tools/chrome_trace_to_bga_trace.py`) for `trace.json`, `tools/bst_show_to_graph.py` for `graph.json`, and **`tools/bst_run_context.py`** for `run-context.json` - with `tools/bst_extract_run.py` as a convenience coordinator over all three, not the only supported entry point.

Confirmed directly: `tools/bst_run_context.py` has zero references to `native_max_jobs`, `cpu_budget`, or `host_cpu_count` anywhere in the file. It still only produces `resource_capacities`/`max_jobs`/`cpu_accounting` (its original `P4-09` scope). A user following `docs/ingestion-pipeline.md`'s own documented per-tool pipeline (rather than the `bst_extract_run.py` convenience wrapper) gets a `run-context.json` silently missing every field `UX-12`/`UX-15` added - no error, no warning, just absence, indistinguishable from "this run genuinely has no native_max_jobs data" (which is itself a valid, common state) versus "this producer doesn't know how to capture it at all."

This creates two ingestion APIs with silently different capabilities:

```text
tools/bst_extract_run.py   --native-max-jobs N --cpu-budget N   -> full UX-12/15 fields
tools/bst_run_context.py   (no equivalent flags exist)          -> UX-12/15 fields always absent
```

## Required Fix

Pick one, don't leave the divergence unresolved:

1. **Preferred**: extract a single canonical `RunContext`-dict-building function (e.g. `tools/_run_context_builder.py` or similar) that both `tools/bst_run_context.py` and `tools/bst_extract_run.py` call, taking `native_max_jobs`/`cpu_budget` as optional parameters alongside the scheduler-config fields both already handle. `tools/bst_run_context.py` gains `--native-max-jobs`/`--cpu-budget` CLI flags mirroring `bst_extract_run.py`'s own. One implementation, two thin CLI wrappers.
2. **Acceptable fallback** if (1) turns out to need more restructuring than is worth it right now: add the same `--native-max-jobs`/`--cpu-budget` flags directly to `tools/bst_run_context.py` (duplicating the small amount of logic involved - it's just two optional dict keys, not the full extraction pipeline), and add a prominent docstring/comment on both files cross-referencing each other so a future field addition to one isn't silently forgotten on the other again.

Either way, `docs/ingestion-pipeline.md` should state explicitly that both producers now support the same `run-context.json` field set, or explain any remaining, deliberate difference.

## Out of Scope

- Any other divergence between the two files unrelated to `UX-12`/`UX-15`'s specific fields - this task is scoped to closing the one gap found.

## Acceptance Test

1. `tools/bst_run_context.py --native-max-jobs N --cpu-budget N ...` (or equivalent) produces a `run-context.json` with both fields populated, matching what `bst_extract_run.py` would produce for the same inputs.
2. `docs/ingestion-pipeline.md` no longer implies the two producers have silently different field coverage.
3. Full suite green.

## Verification Log
_(append real command + output here once run, before marking 🟢)_
