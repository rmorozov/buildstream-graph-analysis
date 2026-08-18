# P4-14: Surface BuildStream's cache-query overhead as a reportable signal

**Priority:** P4 | **Status:** 🟢 Fixed & Verified (2026-08-14) - aggregate pipeline-level signal (Candidate Direction 2); the remote-cache per-element `Cache-query` case (Candidate Direction 1) remains unimplemented, see "What was built" | **Depends on:** `P4-10` (real ingestion pipeline this extends)

## Spec Reference

Not spec-mandated - `docs/spec/specification.md` has zero matches for "CAS", "sandbox", "Query cache", or "cache-query" (confirmed via grep). This is `bga`'s own added heuristic, same non-spec territory as `P4-12`/`P4-13`.

## Background

User's observation: even a build where every element is already cached still has to do *something* to determine that - compute/look up each element's cache key and check the local (and possibly remote) artifact cache - and suspected BuildStream's log hides this time entirely, reporting it as if it took zero seconds, potentially summing to real time on a project with thousands of elements.

Empirically confirmed against a real, installed BuildStream 2.7.0 (`pip install buildstream`, a from-scratch one-element local-source project, `bst build` at **default verbosity - no `--verbose` needed**):

```text
[--:--:--][        ][    main:core activity                 ] START   Build
[--:--:--][        ][    main:core activity                 ] START   Loading elements
[00:00:00][        ][    main:core activity                 ] SUCCESS Loading elements
[--:--:--][        ][    main:core activity                 ] START   Resolving elements
[00:00:00][        ][    main:core activity                 ] SUCCESS Resolving elements
[--:--:--][        ][    main:core activity                 ] START   Initializing remote caches
[00:00:00][        ][    main:core activity                 ] SUCCESS Initializing remote caches
[--:--:--][        ][    main:core activity                 ] START   Query cache
[00:00:00][        ][    main:core activity                 ] SUCCESS Query cache
```

This is BuildStream's own `Stream.query_cache()` (`_stream.py`), which runs over *every* planned element before any FETCH/BUILD/PULL/PUSH queue work begins - loading artifact metadata and checking cache-hit status for each - wrapped in one `messenger.simple_task("Query cache", ...)` (`_messenger.py`). The user's intuition was right that this is real work with a real elapsed cost. But it's logged as one aggregate, non-element-scoped line, not distributed across the elements it actually checked - and `tools/chrome_trace_to_bga_trace.py` already, deliberately, drops it: `action="main"` is not in `ACTION_TO_KIND`, per its own docstring ("BuildStream's own top-level pseudo-activity bracket ... not a real element task and has no `TaskKind` equivalent"). So today `bga` has zero visibility into this cost - not "measured as negligible," but genuinely never measured at all.

A second, more granular case exists for projects with a remote artifact cache configured: `Stream.query_cache()` switches from the single synchronous loop above to a real, parallel scheduler queue, `CacheQueryQueue` (`_scheduler/queues/cachequeryqueue.py`), with its own `action_name = "Cache-query"` and its own resource types (`[ResourceType.PROCESS, ResourceType.CACHE]`) - a genuine per-element job going through the same `ElementJob` START/SUCCESS-with-`elapsed` machinery as FETCH/BUILD/PULL/PUSH (confirmed via `_scheduler/jobs/job.py`: the START/SUCCESS messages fire unconditionally, not gated by `CacheQueryQueue.log_to_file = False` - that flag only suppresses a per-element captured-output logfile, not the terminal status line). **Not yet directly observed in a real log** - this repo's test environment has no remote cache to configure against, so the exact line format for this case (does it produce a normal `[hash][cache-query:element] START/SUCCESS` bracket `bga`'s regex would already syntactically match, just currently unrecognized by `ACTION_TO_KIND`? or something else entirely?) needs direct verification with a real remote-cache fixture before any implementation, not assumed from source reading alone.

Whether either case sums to a *material* fraction of wall-clock time on a large (thousands-of-elements) project is an open, unverified question - this task's job is to make the cost visible and measurable first, not to assert significance up front.

## Candidate Directions

1. **Recognize the per-element `Cache-query` action** (remote-cache case) as a new `TaskKind` (e.g. `CACHE_QUERY`), extending `ACTION_TO_KIND`/`bga/ingest/models.py::TaskKind` the same way other real action words are already recognized. Report it as its own category (or fold into `DOWNLOAD`-adjacent resource accounting, matching `KIND_TO_RESOURCE`'s existing FETCH/PULL grouping) rather than silently absorbing it into `BUILD` or dropping it. Requires the real-log verification above first.
2. **Surface the aggregate "Query cache" pipeline-level cost** (no-remote-cache case) as a single, clearly-labeled report line (e.g. "Query cache: 0.4s, not attributable to individual elements - BuildStream reports this as one pipeline-level operation") rather than forcing it into a per-element task - honest about the real precision limit (one number, not N).
3. **Do nothing beyond documenting the gap**, if a real large-project measurement shows this cost is consistently negligible relative to total build time - this task should include actually measuring it against a real, large (or as large as practically constructible) project before committing to either direction above, not assume significance from first principles alone.

## Required Fix (once a direction is chosen after real measurement)

- At minimum: extract and surface the "Query cache" line's elapsed duration somewhere in the produced run directory/report (even as a single caveat-labeled number) instead of silently discarding it as today.
- If the remote-cache per-element case is confirmed real and log-visible: recognize it as a distinct `TaskKind`, following the existing action-word-recognition pattern.
- Document the real precision limit prominently in both cases: this is a coarse, at-best-single-number signal for the no-remote-cache case, not a per-element breakdown - do not imply more precision than BuildStream's own log actually provides.

## Out of Scope

- Don't invent per-element cache-query durations by estimation/interpolation when the log only provides one aggregate number - that would misrepresent measured data as more precise than it is, against this codebase's "no silent correction" discipline.
- Don't change any existing invariant-bearing computation (attribution identity I4, critical path, LB) - this is purely an additive, presentational signal unless real large-project data shows otherwise and the user decides to escalate it.

## Acceptance Test

- The no-remote-cache "Query cache" log excerpt above, reproduced by a checked-in test fixture (real or realistic).
- A real, large (thousands-of-elements-scale, or as large as practically constructible) project's actual "Query cache" elapsed value measured and reported, to settle whether Candidate Direction 3 (do nothing further) applies.
- If the remote-cache per-element case is pursued: a real log excerpt from an actual remote-cache-configured build showing the `Cache-query` action's real line format, captured before writing any parsing code for it.

## What was built

The real large-project measurement (Acceptance Test item 2) settled the direction: a real, freshly-installed BuildStream 2.7.0, a from-scratch 2001-element project (2000 `kind: import` elements + one `kind: stack` depending on all of them), built once (cold) then rebuilt (fully cached). On the fully-cached rebuild, total wall clock (BuildStream's own "Build" elapsed) was 8s - of that, "Resolving elements" alone was 5s and "Query cache" was 2s, **7 of 8 seconds (87%) of total wall time**, entirely outside any per-element FETCH/BUILD/PULL/PUSH task bga could see. This settled Candidate Direction 3 ("do nothing further") as **not applicable** - the cost is real and material, not negligible. It also showed "Resolving elements" (not "Query cache") was the larger of the two on this fixture, so the fix was scoped to the whole `main:core activity` phase family (Loading elements / Resolving elements / Initializing remote caches / Query cache), not `Query cache` alone, which the original Background section had focused on before this measurement.

Implemented (Candidate Direction 2 - aggregate, per-phase pipeline-level numbers, not a per-element breakdown):

- `tools/bst_log_to_chrome_trace.py`'s `WrapperTraceConverter`: `action == "main"` events are now tracked via a small, separate stack (`_main_activity_stack`) into a new `pipeline_overhead` list (`{"phase": str, "elapsed_us": int}` per completed phase) - deliberately never routed through `active_tasks`/`trace_events` (zero risk to the existing, tested per-element nested-sub-phase collapsing logic). The outer "Build" wrapper is excluded (redundant with the horizon bga computes elsewhere).
- `tools/bst_extract_run.py`: writes `converter.pipeline_overhead` into `run-context.json`'s new `pipeline_overhead` field when non-empty - an additive extension of run-context/v9 (Part 32.1), same precedent as `element_kind`'s addition to graph/v9 (`P4-08`). Confirmed no schema collision (`docs/spec/specification.md` Part 32.1 has no such field).
- `bga/ingest/models.py`: `RunContext.pipeline_overhead` (loaded field) and `AnalysisResult.pipeline_overhead` (computed field: `{"phases": [...], "total_us": int, "fraction_of_horizon": Optional[float], "note": str}`).
- `bga/ingest/loader.py`: reads the new `run-context.json` field.
- `bga/analyzer.py`: `_compute_pipeline_overhead()` - thin pass-through plus a total and a horizon-relative fraction; empty dict (no report section at all) when the log had no pipeline-overhead lines, so every existing fixture/test is byte-identical.
- `bga/report/text.py` / `bga/report/json.py`: a new "Pipeline Overhead (not attributable to individual elements)" block/`pipeline_overhead` key, full-report only (same gating as `structural`/`confidence`), explicitly labeled as not per-element.

Not implemented (Candidate Direction 1, remote-cache per-element `Cache-query` scheduler queue): still not directly observed in a real log - this environment has no remote artifact cache to configure against, so the real line format remains unverified. Left as a documented, deliberate gap rather than guessed at - a future round with remote-cache access can pick this up following the same `TaskKind`-extension pattern already used for `TRACK`/`FETCH`/`PULL`/`BUILD`/`PUSH`.

## Verification Log

Real large-project measurement (BuildStream 2.7.0 in a throwaway venv, 2001-element from-scratch project - see "What was built" above):

```text
$ time bst --log-file cold.log build all.bst   # first build, populates cache
real  0m47.336s
...
Pipeline Summary
    Total:       2001
    Fetch Queue: processed 2001, skipped 0, failed 0
    Build Queue: processed 2001, skipped 0, failed 0

$ time bst --log-file warm.log build all.bst   # rebuild, fully cached
real  0m9.792s
...
    Fetch Queue: processed 0, skipped 2001, failed 0
    Build Queue: processed 0, skipped 2001, failed 0

$ grep -n "Query cache\|Resolving elements\|SUCCESS Build" warm.log
[00:00:00]... SUCCESS Loading elements
[00:00:05]... SUCCESS Resolving elements
[00:00:00]... SUCCESS Initializing remote caches
[00:00:02]... SUCCESS Query cache
[00:00:08]... SUCCESS Build
```

Real end-to-end extraction + `bga analyze` against `warm.log` (the exact scenario the user originally worried about - a fully-cached build where bga's own horizon sees nothing at all):

```text
$ python3 -m tools.bst_extract_run project warm.log rundir --bst-bin bst
Wrote run directory to rundir - targets=['all.bst'], 2001 elements, 2000 dependencies, 0 spans

$ python3 -c "import json; print(json.load(open('rundir/run-context.json'))['pipeline_overhead'])"
[{'phase': 'Loading elements', 'elapsed_us': 0}, {'phase': 'Resolving elements', 'elapsed_us': 5000000},
 {'phase': 'Initializing remote caches', 'elapsed_us': 0}, {'phase': 'Query cache', 'elapsed_us': 2000000}]

$ python3 -m bga.cli analyze rundir
Build Efficiency Report
Total Duration: 0.0s          # <- bga's own horizon: nothing, 0 spans (fully cached)
...
Pipeline Overhead (not attributable to individual elements):
  Loading elements              0.00s
  Resolving elements            5.00s
  Initializing remote caches     0.00s
  Query cache                   2.00s
  Total: 7.00s               # <- the real cost, previously entirely invisible
```

Added `tests/unit/test_pipeline_overhead.py` (11 tests: raw-log extraction against a real captured log excerpt, the "Build" exclusion, no spurious `bst-builder` trace events, nonzero-elapsed arithmetic, defensive handling of an unmatched terminal status, analyzer/report wiring including `fraction_of_horizon` and the both-present/both-absent JSON/text cases). Added `test_pipeline_overhead_extracted_from_a_real_cached_rebuild` to `tests/unit/test_bst_extract_run.py` (builds `tests/fixtures/bst_show_project/` twice - cold then a real cached rebuild - and confirms `Query cache` round-trips through `run-context.json` into the text report; skipped without `bst` on `PATH`, passed for real against the throwaway venv install used for the large-project measurement above).

Full suite: 359 passed with `bst` on `PATH` (354 passed + 5 skipped without it) - was 347/343+4. `make lint` clean. `make check-clean` OK. `tests/test_e2e.py` 7/7.

### Follow-up (2026-08-14): two real bugs found and fixed while researching `P4-15`

While empirically grounding `P4-15`'s "enrich ingest with the real CI flow" (`bst source track`/`bst source checkout`/`bst build`/`bst artifact checkout`), running this converter against real logs from commands *other* than `bst build` surfaced two real bugs in the implementation above - both fixed, both regression-tested. See `docs/spec/ingestion-pipeline.md` fact 12 for the full real-log evidence.

1. **Only `"Build"` was excluded from `pipeline_overhead`, not other commands' own top-level wrappers.** `bst source track` wraps its pipeline-level phases in a `"Track"` bracket instead - before this fix, `Track` would have been miscounted as real, measurable overhead (it spans the entire invocation, exactly like `Build` does). Fixed: `_MAIN_ACTIVITY_WRAPPER_NAMES = {"Build", "Track"}`.
2. **`action="main"` events with a real element hash were being swept into the blank-hash-only `pipeline_overhead` bucket.** `bst source checkout`'s `"Staging sources"` and `bst artifact checkout`'s `"Staging dependencies"`/`"Integrating sandbox"`/`"Checking out files in ..."` are also logged under `action="main"`, but scoped to the checked-out element's own real hash - genuinely per-element work, not pipeline-level. Before this fix, this real per-element data would have been misattributed as "not attributable to individual elements." Fixed: `handle_bst_event` now only routes to the pipeline-level bucket when `hash_val` is blank; a real hash falls through to the normal per-element `active_tasks` path unchanged (preserving exactly the pre-`P4-14` behavior for that case - still dropped downstream by `chrome_trace_to_bga_trace.py` as "not a real element task", just no longer *also* miscounted upstream).

Added regression tests to `tests/unit/test_pipeline_overhead.py` (4 new tests, real captured log excerpts for both cases). See `docs/backlog/tasks/P4-15-stack-consolidation-heuristic.md` for what the now-correctly-routed per-element checkout data is used for (`tools/bst_checkout_cost.py`).
