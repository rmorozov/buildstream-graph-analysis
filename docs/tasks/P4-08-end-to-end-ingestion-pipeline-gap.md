# P4-08: No real end-to-end path from a live BuildStream project to a bga-ready run directory

**Priority:** P4 | **Status:** ⚪ Blocked / Out of Scope — needs a product decision before scoping | **Depends on:** none

## Spec Reference
Part 32 (`run-context/v9`, `graph/v9`, `trace/v9`) defines what `bga` consumes, but the spec is silent on how those three files get produced from a real BuildStream invocation - that's deliberately out of the analysis tool's own spec (Part 32 documents the *contract*, not a producer for it).

## Current State (confirmed)
Nothing in this repository turns a real, live BuildStream project/run into the `run-context.json`/`graph.json`/`trace.json` triple `bga` actually reads:
- `tools/bst_log_to_chrome_trace.py` converts a (currently wrapper-only, see `P4-05`) BuildStream log into Chrome Trace JSON - a `trace`-shaped artifact, not the full triple, and not even trace/v9 shaped directly (Chrome Trace format, a different schema).
- `tests/fixtures/synthetic_multi_subproject/adapter.py` converts Chrome Trace → trace/v9, but it's test-only code (not exposed as a CLI tool, not documented for real use), and it still doesn't produce `graph.json` (the element dependency graph with `cache_key`/`requested_target`) or `run-context.json` (resource capacities, wall clock) - those are entirely hand-built in every fixture in this repo.
- There is no BuildStream-project-introspection code anywhere (reading a `.bst` element tree, extracting real dependency edges and cache keys) to produce a real `graph.json`.

Every example in `README.md`/`docs/cli.md` that references a real BuildStream run directory is therefore aspirational, not something a user can currently follow end-to-end without hand-building `graph.json`/`run-context.json` themselves.

## Why this is Blocked, not just another 🔴 task
Scoping a real fix here requires product/architecture decisions this tracker's usual "read the spec, find the gap, fix it" pattern doesn't resolve on its own:
- Does `bga` want to *own* a BuildStream-log/project-introspection ingestion tool at all, or stay a pure analyzer that expects some other, separately-maintained tool to produce v9-shaped input (the current implicit design)?
- If it should own one: does `graph.json` get derived from BuildStream's project YAML directly (parsing `.bst` element files and their `depends:` blocks), from `bst show`/`bst artifact` command output, from log-scraping (fragile - dependency structure isn't reliably present in build logs), or from some other BuildStream-native introspection surface? This needs someone who knows BuildStream's actual CLI/API surface well, not just this codebase.
- Is wrapper-script log output (the format `tools/bst_log_to_chrome_trace.py` already targets) the intended real-world source at all, or was that convention specific to whatever CI system originally produced the sample logs this repo's fixtures were modeled on?

## Suggested Next Step (not a fix - a scoping step)
Before creating a concrete implementation task here, get a decision from whoever owns the BuildStream-integration side of this project on the questions above. Once scoped, this likely becomes 2-3 separate tasks (graph.json producer, run-context.json producer, and wiring them + `P4-05`'s trace producer into one `bga ingest`-style convenience command) rather than one large one.

## Verification Log
_(not applicable — blocked pending a scoping decision, not yet started)_
