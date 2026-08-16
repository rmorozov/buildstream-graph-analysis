# UX-24: Chrome Trace export for Plane 2, and a combined two-plane view in perfetto.dev

**Priority:** Medium | **Status:** 🔴 Not Started (design brainstorm only) | **Depends on:** `UX-11` (done), `UX-23` (element tagging - needed for the combined mode, not the standalone mode)

## Motivation

Plane 1 already has a real, working Chrome Trace export path (`tools/bst_log_to_chrome_trace.py`, confirmed real and in active use for the user's own `ui.perfetto.dev` visualization workflow - see `docs/ingestion-pipeline.md`'s own note that this output shape "must keep working exactly as before"). Plane 2 (`tools/bst_native_build_tracer.py`) currently only emits its own custom JSON report shape (`by_binary`/`max_concurrency`/`processes` - see `bst_native_build_tracer.py`'s `summarize`) - real, useful data, but not viewable in the same tool the user already uses for Plane 1.

Two real, concrete opportunities, not competing - both worth having:

1. **Standalone Plane 2 Chrome Trace export.** Every traced process already has real `start_ts`/`end_ts`/`pid`/`ppid`/`cmd` (`pair_events`'s output) - directly convertible to a real Chrome Trace B/E pair per process, with the traced process's own real `pid` becoming the Chrome Trace `tid` (one row per real OS process - a natural fit for Chrome Trace's thread-per-row model, and a much more literal, granular timeline than Plane 1's synthetic per-element/per-task rows). Doesn't need `UX-23` - works from the trace data that already exists today.
2. **Combined two-plane view.** Confirmed via `tools/bst_log_to_chrome_trace.py:253-272`: Plane 1's own export already uses a fixed sentinel `pid: 1` ("the BuildStream invocation") with one Chrome Trace `tid` per element/task. A combined export could instead give each *element* its own real Chrome Trace `pid` (not `tid`) - Plane 1's own element-level B/E pair as the top row, and, nested under that same synthetic `pid`, Plane 2's own real per-process rows (`tid` = real OS pid) for whatever was traced *inside* that element's sandbox. One file, opened once in `perfetto.dev`: expand any element's row to see its own real native-build-system process tree, exactly the "full detailed picture... ready for standalone analysis" the user asked for. This mode needs `UX-23`'s element-tagging first - without it, Plane 2's trace has no way to know which element each process's row belongs to.

## Design sketch (not implemented)

- New tool, `tools/native_trace_to_chrome_trace.py` (mirrors `tools/chrome_trace_to_bga_trace.py`'s naming convention - a second, separate converter, not folded into the tracer itself, matching this repo's existing "small single-purpose tools" discipline) - standalone mode: one B/E pair per traced process, `cat: "native-process"` to keep it visually distinct from Plane 1's own `bst-builder`/`bst-invocation` categories if merged later.
- Combined mode: takes both a Plane 1 Chrome Trace JSON (from `bst_log_to_chrome_trace.py`) and a Plane 2 element-tagged raw trace (`UX-23`) for the *same real run*, and merges them - real, nontrivial part of the design: Plane 1's own timestamps are wall-clock-anchored (`_resolve_start_time_us`), Plane 2's are `CLOCK_MONOTONIC`-anchored (arbitrary epoch, per `hook.c`'s own header) - the two clocks need one real, explicit correlation point (e.g. the element's own Plane-1-recorded "Running commands" B event timestamp, matched to Plane 2's own earliest traced process for that element) before merging, not just concatenated as-is. This correlation step is the real design risk worth scoping carefully before implementation, not assumed away.

## Out of Scope

- Any implementation - design brainstorm only, per this task's own scope.
- Solving the clock-correlation problem in this doc - flagged as the real open design risk, not resolved here.
- Changing `tools/bst_log_to_chrome_trace.py`'s own existing output shape - the user's own established `perfetto.dev` workflow for Plane 1 alone must keep working unchanged (same constraint `docs/ingestion-pipeline.md` already states).

## Acceptance Test

1. Standalone Plane 2 export: a real captured native trace (e.g. `examples/05-cmake-cpp-toolchain`'s own real run) converts to a valid Chrome Trace JSON, opens cleanly in `perfetto.dev`, and shows real per-process rows with real, non-zero durations for matched processes.
2. Combined mode: a real captured run of the same project, both planes traced together, produces one Chrome Trace JSON where expanding any cmake element's row reveals its own real traced sub-processes, with timestamps that are visibly, correctly co-located on one shared timeline (not two disjoint clusters from clock-anchoring mismatch).
3. Full suite green.

## Verification Log

Filed 2026-08-16. Design brainstorm only, grounded in real inspection of `tools/bst_log_to_chrome_trace.py`'s own real pid/tid conventions (lines 253-272) and Plane 2's own real, already-confirmed `CLOCK_MONOTONIC` timestamp semantics (`UX-11`'s own doc) - not implemented.
