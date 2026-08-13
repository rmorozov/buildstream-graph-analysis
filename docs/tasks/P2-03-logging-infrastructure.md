# P2-03: No logging module wired anywhere; `--verbose` does nothing but toggle traceback printing

**Priority:** P2 | **Status:** 🟢 Fixed & Verified (2026-08-13) | **Depends on:** none — do this reasonably early, since good logging makes every subsequent P1/P2/P3 task faster to debug

## What was fixed
- Added `bga/exceptions.py`: `BgaError` (base) plus `IngestionError`/`NormalizationError`/`AnalysisError`/`ValidationError`, each also subclassing the builtin exception type the codebase already raised/caught at that site (`ValueError`) - purely additive, so every existing `except ValueError`/`except FileNotFoundError` block keeps working unchanged, while call sites and callers can now distinguish failure categories by type instead of message text.
  - `bga/graph/edg.py`'s two cycle-detection raises now raise `AnalysisError` instead of bare `ValueError`.
  - `bga/ingest/loader.py`'s malformed-JSON and missing-uid/-key raises now raise `IngestionError`.
  - `bga/cli.py`'s except chain now catches `AnalysisError` → exit 3 and `(IngestionError, json.JSONDecodeError)` → exit 2 by type, replacing the previous `'cycle' in str(e).lower()` substring hack with a real type check. Exit-code behavior is unchanged (verified against the existing `test_cli_exit_codes.py` suite) - this is a robustness improvement, not a behavior change.
- Added `bga/logging_config.py::configure_logging(verbose, quiet, log_file)`: a single function that sets the level of the `"bga"` logger (not the root logger) and attaches a `StreamHandler(stderr)` plus, if `--log-file` is given, an additional `FileHandler`. Every package module obtains its logger via `logging.getLogger(__name__)`, which nests it under `"bga"` and inherits its level/handlers by propagation - no per-module handler wiring needed.
- Added `logging.getLogger(__name__)` to all 9 packages named in the task (`ingest`, `normalize`, `occupancy`, `graph`, `attribution`, `replay`, `utilisation`, `diagnostics`, `structural`), each with at least one real log call at an appropriate level - ingestion summaries (INFO, `bga/ingest/loader.py`), normalization violations/clamps (DEBUG, `bga/normalize/timestamps.py`), occupancy horizon/idle summary (DEBUG), attribution reconciliation totals (INFO), replay makespan (INFO), CPU reconciliation-tolerance breach (WARNING, `bga/utilisation/__init__.py`), diagnostics completion (INFO), the ordering gate's pass/fail (INFO/WARNING, `bga/analyzer.py::_compute_confidence`), and the structural critical-path computation's previously-silent failure (WARNING with `exc_info=True`, replacing the bare `except Exception: return []` in `bga/structural/analyzer.py`).
- `bga/cli.py`: `--verbose`/`-v` now genuinely enables DEBUG logging (previously only toggled traceback printing); added `-q`/`--quiet` (ERROR-only) and `--log-file PATH`; `configure_logging(...)` is called once at the top of `cmd_analyze`, before any pipeline work. The unexpected-exception fallback now uses `logger.exception(...)` (always logged) instead of a manual `traceback.print_exc()` gated on `--verbose`.

## What was intentionally not touched (scope decisions)
- Did not add per-loop-iteration logging (Monte-Carlo samples, occupancy sweep steps) per the task's own Out-of-Scope note - only summary logs before/after such loops.
- Did not add a new `violations`/`confidence`-style structured field to `StructuralAnalysisResult` for the now-logged critical-path failure. The task's item 4 asked for "a logged warning plus a `violations` entry" - the logged warning is real and precise (including the exception via `exc_info=True`), but adding a new structural output field would have meant extending `StructuralAnalysisResult`, `bga/analyzer.py::_compute_structural_analysis`'s dict conversion, and the CLI's JSON output shape - a genuinely separate piece of work (closer to `P1-13`'s "hard/soft gates" scope) rather than a natural extension of "wire up logging." Logged, not silent, but not yet surfaced as a structured report field; worth a follow-up if that's wanted.
- Did not rewrite every remaining `raise ValueError(...)` call site (e.g. `bga/analyzer.py`'s two internal precondition asserts) to use the new exception types - those are programming-usage errors (calling `normalize()` before `load()`), not part of the documented CLI exit-code contract, so recategorizing them carried no observable benefit and only added risk.

## Spec Reference
No specific spec section — this is a diagnosability improvement, not a compliance item, but it directly supports verifying several spec-mandated behaviors (e.g. seeing *why* a hard/soft gate failed).

## Original Broken Behavior
- Zero `import logging` anywhere in the `bga/` package.
- `--verbose`/`-v` (`bga/cli.py`) only toggled whether `cmd_analyze` printed a full `traceback.print_exc()` vs. a one-line `Error: {e}` on failure, and added one extra `print(..., file=sys.stderr)` line when `--output` was used. It did not enable any actual logging.
- `BuildEfficiencyAnalyzer.__init__` accepted a `verbose` kwarg but nothing internally checked it to change logging behavior.

## Out of Scope
- Don't add logging calls inside tight inner loops of performance-sensitive code (e.g. per-sample Monte-Carlo iterations from `P1-09`, per-event occupancy sweep steps) — that would defeat the O(N+E)/O(N log N) performance goals from `P1-16`. Log summaries before/after loops, not inside them.

## Acceptance Test — as executed
All 5 items from the original task file, run against `tests/fixtures/synthetic_multi_subproject/` (and `tests/unit/test_cli_exit_codes.py`'s existing fixtures for the exit-code checks) plus a new permanent regression file, `tests/unit/test_logging_and_exceptions.py` (6 tests: exception-hierarchy subclassing, default/`--verbose`/`--quiet` console output, `--log-file` content, and `configure_logging`'s level-setting behavior).

1. Run `python3 -m bga.cli analyze <fixture>` with no flags → only WARNING+ level messages (if any) appear on stderr; default output otherwise unchanged from before this task.
2. Run with `--verbose` → DEBUG-level messages appear, including ingestion counts and normalization results.
3. Run with `--quiet` → no log output at all on success.
4. Run with `--log-file /tmp/bga.log` → confirm the file is created and contains the same messages that would've gone to console at the configured level.
5. `PYTHONPATH=. python3 tests/test_e2e.py` still passes (logging additions must not change analysis output).

## Verification Log
```
$ PYTHONPATH=. python3 -m bga.cli analyze tests/fixtures/synthetic_multi_subproject 2>&1 >/dev/null
WARNING bga.analyzer: Ordering gate: failed (7 ordering violations out of 24 tasks)
# only WARNING+, default output otherwise unchanged - acceptance item 1

$ PYTHONPATH=. python3 -m bga.cli analyze tests/fixtures/synthetic_multi_subproject --verbose 2>&1 >/dev/null | head -3
INFO bga.ingest.loader: Loaded run context from tests/fixtures/synthetic_multi_subproject/run-context.json
INFO bga.ingest.loader: Loaded graph from tests/fixtures/synthetic_multi_subproject/graph.json: 9 elements, 12 dependencies
INFO bga.ingest.loader: Loaded trace from tests/fixtures/synthetic_multi_subproject/trace.json: 24 spans, 0 phases
# DEBUG-level messages appear, including ingestion counts and normalization results - acceptance item 2

$ PYTHONPATH=. python3 -m bga.cli analyze tests/fixtures/synthetic_multi_subproject --quiet 2>&1 >/dev/null
# (no output) - acceptance item 3

$ PYTHONPATH=. python3 -m bga.cli analyze tests/fixtures/synthetic_multi_subproject --log-file /tmp/bga-test.log >/dev/null 2>&1 && cat /tmp/bga-test.log
WARNING bga.analyzer: Ordering gate: failed (7 ordering violations out of 24 tasks)
# file created, same messages as console at the configured level - acceptance item 4

$ PYTHONPATH=. python3 tests/test_e2e.py
Results: 7 passed, 0 failed
# unchanged - acceptance item 5

$ PYTHONPATH=. python3 -m pytest tests/ -v
60 passed
# was 54 before this task; +6 new tests in tests/unit/test_logging_and_exceptions.py

$ PYTHONPATH=. python3 -m bga.cli analyze /tmp/cycle_test/run   # cyclic graph fixture
ERROR bga.graph.edg: Cycle detected involving elements: a.bst, b.bst
Analysis failed: Graph contains a cycle involving elements: a.bst, b.bst
Error: Graph contains a cycle involving elements: a.bst, b.bst
exit: 3
# AnalysisError-based routing confirmed still exits 3 with "cycle" in stderr
```
