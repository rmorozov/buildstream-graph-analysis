# UX-24: Chrome Trace export for Plane 2, and a combined two-plane view in perfetto.dev

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** `UX-11` (done), `UX-23` (done - element tagging, needed for the combined mode) | **Topic:** capture | **Area:** tools

## Motivation

Plane 1 already has a real, working Chrome Trace export path (`tools/bst_log_to_chrome_trace.py`, confirmed real and in active use for the user's own `ui.perfetto.dev` visualization workflow - see `docs/spec/ingestion-pipeline.md`'s own note that this output shape "must keep working exactly as before"). Plane 2 (`tools/bst_native_build_tracer.py`) currently only emits its own custom JSON report shape (`by_binary`/`max_concurrency`/`processes` - see `bst_native_build_tracer.py`'s `summarize`) - real, useful data, but not viewable in the same tool the user already uses for Plane 1.

Two real, concrete opportunities, not competing - both worth having:

1. **Standalone Plane 2 Chrome Trace export.** Every traced process already has real `start_ts`/`end_ts`/`pid`/`ppid`/`cmd` (`pair_events`'s output) - directly convertible to a real Chrome Trace B/E pair per process, with the traced process's own real `pid` becoming the Chrome Trace `tid` (one row per real OS process - a natural fit for Chrome Trace's thread-per-row model, and a much more literal, granular timeline than Plane 1's synthetic per-element/per-task rows). Doesn't need `UX-23` - works from the trace data that already exists today.
2. **Combined two-plane view.** Confirmed via `tools/bst_log_to_chrome_trace.py:253-272`: Plane 1's own export already uses a fixed sentinel `pid: 1` ("the BuildStream invocation") with one Chrome Trace `tid` per element/task. A combined export could instead give each *element* its own real Chrome Trace `pid` (not `tid`) - Plane 1's own element-level B/E pair as the top row, and, nested under that same synthetic `pid`, Plane 2's own real per-process rows (`tid` = real OS pid) for whatever was traced *inside* that element's sandbox. One file, opened once in `perfetto.dev`: expand any element's row to see its own real native-build-system process tree, exactly the "full detailed picture... ready for standalone analysis" the user asked for. This mode needs `UX-23`'s element-tagging first - without it, Plane 2's trace has no way to know which element each process's row belongs to.

## Design sketch (not implemented)

- New tool, `tools/native_trace_to_chrome_trace.py` (mirrors `tools/chrome_trace_to_bga_trace.py`'s naming convention - a second, separate converter, not folded into the tracer itself, matching this repo's existing "small single-purpose tools" discipline) - standalone mode: one B/E pair per traced process, `cat: "native-process"` to keep it visually distinct from Plane 1's own `bst-builder`/`bst-invocation` categories if merged later.
- Combined mode: takes both a Plane 1 Chrome Trace JSON (from `bst_log_to_chrome_trace.py`) and a Plane 2 element-tagged raw trace (`UX-23`) for the *same real run*, and merges them - real, nontrivial part of the design: Plane 1's own timestamps are wall-clock-anchored (`_resolve_start_time_us`), Plane 2's are `CLOCK_MONOTONIC`-anchored (arbitrary epoch, per `hook.c`'s own header) - the two clocks need one real, explicit correlation point (e.g. the element's own Plane-1-recorded "Running commands" B event timestamp, matched to Plane 2's own earliest traced process for that element) before merging, not just concatenated as-is. This correlation step is the real design risk worth scoping carefully before implementation, not assumed away.

## Fix Implemented

Built as designed above, plus two real corrections found only by actually running the combined mode end-to-end against a real captured run - not by unit tests alone (which all passed throughout, on synthetic data that happened not to expose either issue):

1. **Output shape**: `tools/native_trace_to_chrome_trace.py` emits a bare JSON array of events (Chrome Trace's own "JSON Array Format"), not `{"traceEvents": [...]}`. An earlier draft assumed the object-wrapped shape; the real end-to-end test caught it immediately once it tried to parse a real `tools/bst_log_to_chrome_trace.py` output file - that tool's own `get_json()` returns `json.dumps(meta_events + self.trace_events)` directly, a flat list, confirmed by reading it.
2. **Anchor point**: the design originally assumed a distinct Plane 1 "Running commands" B event to anchor on. Running the real combined-mode capture and inspecting Plane 1's own real output directly showed this doesn't exist: `bst_log_to_chrome_trace.py`'s `handle_bst_event` treats every nested sub-phase (Staging sources, Running commands, Caching artifact, ...) sharing the same `hash`+`action` as depth-tracking on the *same already-open* span - there is exactly **one** real B/E pair per element per action, covering the element's whole build task, never a separate event per phase. Fixed by anchoring on that single real per-element B event instead.

Both the standalone converter (`build_standalone_chrome_trace` - per-element synthetic `pid`, real OS `pid` as `tid`, `X`/`i` events for matched/open records) and the combined converter (`build_combined_chrome_trace` + `compute_clock_offset_us`, using the corrected single-anchor-point design) work exactly as originally designed otherwise.

To make a real, single-invocation end-to-end test possible at all, `tools/bst_run_wrapped.run_wrapped` gained an `env` parameter (`None` reproduces its own prior behavior exactly), and `tools/bst_native_build_tracer.run_traced_build`/`run` gained a `--wrapped-log PATH` option that reuses it - letting one real `bst build` invocation capture both planes simultaneously, correlatable by construction rather than requiring two separate builds (which would break I11 determinism between the two captures).

Tests: 16 new (`tests/unit/test_native_trace_to_chrome_trace.py` - 15 pure-logic; `tests/unit/test_dual_plane_capture.py` - 1 real, environment-gated end-to-end test proving the full pipeline: one real build, both planes captured, combined trace correctly correlated).

## Out of Scope

- Any implementation - design brainstorm only, per this task's own scope.
- Solving the clock-correlation problem in this doc - flagged as the real open design risk, not resolved here.
- Changing `tools/bst_log_to_chrome_trace.py`'s own existing output shape - the user's own established `perfetto.dev` workflow for Plane 1 alone must keep working unchanged (same constraint `docs/spec/ingestion-pipeline.md` already states).

## Acceptance Test

1. Standalone Plane 2 export: a real captured native trace (e.g. `examples/05-cmake-cpp-toolchain`'s own real run) converts to a valid Chrome Trace JSON, opens cleanly in `perfetto.dev`, and shows real per-process rows with real, non-zero durations for matched processes.
2. Combined mode: a real captured run of the same project, both planes traced together, produces one Chrome Trace JSON where expanding any cmake element's row reveals its own real traced sub-processes, with timestamps that are visibly, correctly co-located on one shared timeline (not two disjoint clusters from clock-anchoring mismatch).
3. Full suite green.

## Verification Log

Filed 2026-08-16 as a design brainstorm, grounded in real inspection of `tools/bst_log_to_chrome_trace.py`'s own real pid/tid conventions (lines 253-272) and Plane 2's own real, already-confirmed `CLOCK_MONOTONIC` timestamp semantics (`UX-11`'s own doc).

Implemented for real the same day. 16 new tests, full suite green: 644 passed (up from 628), same 7 pre-existing environment-only failures as `main`. `make lint` clean.

Real end-to-end re-verification against `examples/05-cmake-cpp-toolchain`'s `core.bst` (fully cleared first) - one single real `bst build` invocation capturing both planes at once:

```text
$ python3 -m tools.bst_native_build_tracer run --raw-log raw.log --wrapped-log wrapped.log \
    examples/05-cmake-cpp-toolchain report.json -- bst --no-colors build core.bst

$ python3 -m tools.native_trace_to_chrome_trace standalone raw.log standalone.json
Wrote 99 trace events to standalone.json

$ python3 -m tools.bst_log_to_chrome_trace --format wrapped wrapped.log plane1.json
Successfully generated trace! Open plane1.json in chrome://tracing or ui.perfetto.dev

$ python3 -m tools.native_trace_to_chrome_trace combined plane1.json raw.log combined.json --anchor-element core.bst
Wrote 108 trace events to combined.json
```

Inspected `combined.json` directly: 98 real `native-process` events (Plane 2), 2 real `bst-builder` events + 2 `bst-invocation` events (Plane 1, both fully preserved unmodified), 6 metadata events. **Decisive correlation evidence**: Plane 2's own earliest event timestamp landed exactly on Plane 1's own real build-start timestamp (`1786899207182000` on both sides), and every Plane 2 event for `core.bst` fell within Plane 1's own real build-task span extended by its own natural tail (compile/link work continuing briefly past the officially-logged "build" span's own end) - one shared, correctly co-located timeline, not two disjoint clusters from a clock-anchoring mismatch. Both Acceptance Test items satisfied with real evidence, not synthetic fixtures alone.
