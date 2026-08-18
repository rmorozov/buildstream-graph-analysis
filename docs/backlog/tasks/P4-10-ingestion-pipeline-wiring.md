# P4-10: Wire trace + graph + run-context extraction into one convenience flow

**Priority:** P4 | **Status:** 🟢 Fixed & Verified (2026-08-14) | **Depends on:** `P4-05` (raw-log support for the trace converter, done), `P4-09` (run-context producer, done) — `P4-08` (graph producer) was already done

## Spec Reference
Part 32 (the full `run-context/v9` + `graph/v9` + `trace/v9` triple `bga analyze` expects as one directory).

## Background
Read `docs/spec/ingestion-pipeline.md` first. The three producer pieces (`tools/bst_log_to_chrome_trace.py` for trace, `tools/bst_show_to_graph.py` for graph, `P4-09`'s new tool for run-context) are each independent, single-purpose scripts by design (see that doc's "Target architecture" section) - this task is specifically about coordinating them into one real user-facing flow, not merging them into one script.

## Required Fix
1. A convenience command or script (e.g. `tools/bst_extract_run.sh`, or a small Python coordinator - match whichever fits the existing `tools/` scripts' style better) that takes a wrapper log (or raw log, once `P4-05` lands) plus the BuildStream project directory, and produces a complete `run-context.json`/`graph.json`/`trace.json` triple in one output directory, ready for `bga analyze` directly.
2. **Derive the target element list from the real invocation itself** (the wrapper log's own `Executing command: ... bst build <targets>` line, already parsed by `tools/bst_log_to_chrome_trace.py`'s `EXEC_CMD_RE`) and pass that same list to `bst_show_to_graph.py`'s `requested_target` marking - not a hardcoded umbrella-target convention like `all.bst`. This was flagged as the top scenario risk when this design was discussed: a mismatch between "what graph.json declares as requested" and "what the trace shows was actually built" would silently corrupt leaf/deferrability analysis (Part 24) and terminal-task selection (Part 6.2) with no error raised.
3. Ensure graph extraction runs against the **same checkout/commit** the trace's build ran against (see `docs/spec/ingestion-pipeline.md`'s "time-of-extraction consistency" note) - fail loudly (or at least warn) if the tool can detect a mismatch (e.g. comparing a git commit hash captured at trace-build time against the current checkout), rather than silently producing a graph.json whose cache keys don't match what was really built.
4. Improve `bga`'s own error message for the specific "graph.json present, trace.json missing" case (confirmed today: a generic `Required input file not found`, exit 1 - functionally correct but not as actionable as it could be) to hint at running this new extraction flow, per the original "bga can hint the user to run a local build" request.

## Out of Scope
- Don't build a full "bga manages your BuildStream builds for you" orchestration layer - this only coordinates *extraction* from a build that already happened (or is happening), it doesn't invoke `bst build` itself.

## Acceptance Test
A single command, given a real (or realistic synthetic) wrapper log + project directory, produces a complete run directory that `bga analyze` consumes with zero manual editing - and using a *different* target list on two separate real builds produces two different, each-individually-correct `requested_target` sets (proving target derivation isn't hardcoded).

## What was built
`tools/bst_extract_run.py extract_run(project_dir, log_path, output_dir, ...)`, coordinating (not merging) the three independent producer tools:
1. Parses `log_path` once via `WrapperTraceConverter` (auto-detecting wrapped/raw per line, same as `bst_log_to_chrome_trace.py`) to get Chrome Trace events, the real scheduler config, and the real target list.
2. **Target derivation**: reads BuildStream's own `Targets:` summary-header line (confirmed real and present in both wrapped and raw logs, printed unconditionally by BuildStream itself - see `docs/spec/ingestion-pipeline.md`) - not a hardcoded umbrella-target convention, and not a wrapper-specific shell-command parse (`EXEC_CMD_RE`), which would only work for wrapped logs. **Fails loudly** (`RuntimeError`, refuses to guess) if no `Targets:` line is found, per the acceptance test's "don't hardcode a convention" requirement.
3. `tools/chrome_trace_to_bga_trace.chrome_events_to_bga_spans` converts those events into trace/v9 spans.
4. `tools/bst_show_to_graph.extract_graph(project_dir, targets)` produces graph.json, using the *real* derived target list from step 2 (not a separate guess) - this is exactly the "keep `requested_target` honest relative to what was really built" property the task file's original design note called out as the top scenario risk.
5. The same converter instance's scheduler config + invocation wall-clock bounds produce run-context.json (`P4-09`'s logic, inlined here to avoid a second, separate log parse).
6. **Time-of-extraction consistency check**: if `project_dir` is a git repository, warns (does not fail) when the working tree is dirty (`git status --porcelain`) - see `docs/spec/ingestion-pipeline.md`'s "time-of-extraction consistency" note for the honest limitation (a clean-but-wrong-commit tree isn't detectable this way).
7. Also writes `chrome_trace.json` alongside the three bga-ready files - not part of `bga`'s input contract, but the same artifact the user's own real personal workflow (visualizing a build timeline in `ui.perfetto.dev`) already uses, produced for free by the same extraction run.

Also improved `bga`'s own CLI error message (`bga/cli.py::_print_missing_input_hint`) for the "some but not all of run-context.json/graph.json/trace.json present" case: now hints at the specific missing file(s) and the tool that produces each, plus `tools/bst_extract_run.py` for the one-step path - only fires when at least one real input file is already present (a genuinely empty/unrelated directory gets the original, generic message).

## Verification Log
```
$ PYTHONPATH=. python3 -m pytest tests/unit/test_bst_extract_run.py -v
8 passed   # including 2 real end-to-end tests against a real bst build

$ PYTHONPATH=. python3 -m pytest tests/unit/test_cli_exit_codes.py -v
7 passed   # including the new missing-file hint tests

# Real, complete, zero-manual-editing run against a real BuildStream 2.7.0 build:
$ bst -C tests/fixtures/bst_show_project --no-colors build app.bst > real_build.log 2>&1
$ PYTHONPATH=. python3 tools/bst_extract_run.py tests/fixtures/bst_show_project real_build.log /tmp/extracted_run
Wrote run directory to /tmp/extracted_run - targets=['app.bst'], 4 elements, 3 dependencies, 9 spans
Warning: project directory '...' has uncommitted changes - ...

$ PYTHONPATH=. python3 -m bga.cli analyze /tmp/extracted_run
============================================================
Build Efficiency Report
============================================================
...
Structural Analysis:
  Elements: 4, Edges: 3, Max Depth: 1
============================================================
# full report produced, zero manual editing of any file

# Acceptance test's "different target lists produce different
# requested_target sets" - confirmed by test_different_target_lists_produce_different_requested_targets
# (real: bst build base.bst -> requested={'base.bst'}; bst build base2.bst
# -> requested={'base2.bst'}, each independently correct)

$ PYTHONPATH=. python3 -m pytest tests/ -q
311 passed (with bst on PATH) / 307 passed, 4 skipped (without)   # was 261/2

$ PYTHONPATH=. python3 tests/test_e2e.py
Results: 7 passed, 0 failed

$ make check-clean
OK: no ignored files are tracked
```
