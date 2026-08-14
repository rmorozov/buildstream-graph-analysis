# P4-10: Wire trace + graph + run-context extraction into one convenience flow

**Priority:** P4 | **Status:** 🔴 Not Started | **Depends on:** `P4-05` (raw-log support for the trace converter), `P4-09` (run-context producer) — `P4-08` (graph producer) is already done

## Spec Reference
Part 32 (the full `run-context/v9` + `graph/v9` + `trace/v9` triple `bga analyze` expects as one directory).

## Background
Read `docs/ingestion-pipeline.md` first. The three producer pieces (`tools/bst_log_to_chrome_trace.py` for trace, `tools/bst_show_to_graph.py` for graph, `P4-09`'s new tool for run-context) are each independent, single-purpose scripts by design (see that doc's "Target architecture" section) - this task is specifically about coordinating them into one real user-facing flow, not merging them into one script.

## Required Fix
1. A convenience command or script (e.g. `tools/bst_extract_run.sh`, or a small Python coordinator - match whichever fits the existing `tools/` scripts' style better) that takes a wrapper log (or raw log, once `P4-05` lands) plus the BuildStream project directory, and produces a complete `run-context.json`/`graph.json`/`trace.json` triple in one output directory, ready for `bga analyze` directly.
2. **Derive the target element list from the real invocation itself** (the wrapper log's own `Executing command: ... bst build <targets>` line, already parsed by `tools/bst_log_to_chrome_trace.py`'s `EXEC_CMD_RE`) and pass that same list to `bst_show_to_graph.py`'s `requested_target` marking - not a hardcoded umbrella-target convention like `all.bst`. This was flagged as the top scenario risk when this design was discussed: a mismatch between "what graph.json declares as requested" and "what the trace shows was actually built" would silently corrupt leaf/deferrability analysis (Part 24) and terminal-task selection (Part 6.2) with no error raised.
3. Ensure graph extraction runs against the **same checkout/commit** the trace's build ran against (see `docs/ingestion-pipeline.md`'s "time-of-extraction consistency" note) - fail loudly (or at least warn) if the tool can detect a mismatch (e.g. comparing a git commit hash captured at trace-build time against the current checkout), rather than silently producing a graph.json whose cache keys don't match what was really built.
4. Improve `bga`'s own error message for the specific "graph.json present, trace.json missing" case (confirmed today: a generic `Required input file not found`, exit 1 - functionally correct but not as actionable as it could be) to hint at running this new extraction flow, per the original "bga can hint the user to run a local build" request.

## Out of Scope
- Don't build a full "bga manages your BuildStream builds for you" orchestration layer - this only coordinates *extraction* from a build that already happened (or is happening), it doesn't invoke `bst build` itself.

## Acceptance Test
A single command, given a real (or realistic synthetic) wrapper log + project directory, produces a complete run directory that `bga analyze` consumes with zero manual editing - and using a *different* target list on two separate real builds produces two different, each-individually-correct `requested_target` sets (proving target derivation isn't hardcoded).

## Verification Log
_(append real command + output here once run, before marking 🟢)_
