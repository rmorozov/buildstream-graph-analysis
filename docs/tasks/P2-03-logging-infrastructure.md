# P2-03: No logging module wired anywhere; `--verbose` does nothing but toggle traceback printing

**Priority:** P2 | **Status:** 🔴 Not Started | **Depends on:** none — do this reasonably early, since good logging makes every subsequent P1/P2/P3 task faster to debug

## Spec Reference
No specific spec section — this is a diagnosability improvement, not a compliance item, but it directly supports verifying several spec-mandated behaviors (e.g. seeing *why* a hard/soft gate failed).

## Current Broken Behavior
- Zero `import logging` anywhere in the `bga/` package — confirm with `grep -rn "^import logging\|logging\." bga/` before starting (should return nothing).
- `--verbose`/`-v` (`bga/cli.py`) only toggles whether `cmd_analyze` prints a full `traceback.print_exc()` vs. a one-line `Error: {e}` on failure, and adds one extra `print(..., file=sys.stderr)` line when `--output` is used. It does not enable any actual logging.
- `BuildEfficiencyAnalyzer.__init__` accepts a `verbose` kwarg (confirmed present after the P0 fix) but nothing internally checks it to change logging behavior.

## Required Fix
1. Add a small custom exception hierarchy if not already added by `P2-01`/`P2-02` (coordinate — check the tracker/task files first): `BgaError` (base), `IngestionError`, `NormalizationError`, `AnalysisError`, `ValidationError`. Map each to the documented exit codes in `bga/cli.py` (1/2/3 per `docs/cli.md`).
2. Add module-level `logging.getLogger(__name__)` loggers to each package: `bga.ingest`, `bga.normalize`, `bga.occupancy`, `bga.graph`, `bga.attribution`, `bga.replay`, `bga.utilisation`, `bga.diagnostics`, `bga.structural`.
3. Wire `--verbose`/`-v` → `logging.DEBUG`, default (no flag) → `logging.WARNING`. Add a new `--quiet`/`-q` flag → `logging.ERROR`.
4. Log at minimum, at appropriate levels:
   - INFO: ingestion summary (counts loaded per entity type).
   - DEBUG: normalization results (violations found, clamps applied and where).
   - INFO/WARNING: which hard/soft gates passed/failed and why (once `P1-13` lands; if not yet landed, log whatever gate-like checks currently exist, e.g. ordering violations).
   - WARNING: any place a code path silently used to swallow an error — specifically replace `bga/structural/analyzer.py`'s bare `except Exception: return []` (if not already fixed by a P1 task) with a logged warning plus a `violations` entry, never silent.
5. Add a `--log-file PATH` option to persist logs separately from the report body (use a `logging.FileHandler` in addition to the console handler, not instead of).

## Out of Scope
- Don't add logging calls inside tight inner loops of performance-sensitive code (e.g. per-sample Monte-Carlo iterations from `P1-09`, per-event occupancy sweep steps) — that would defeat the O(N+E)/O(N log N) performance goals from `P1-16`. Log summaries before/after loops, not inside them.

## Acceptance Test
1. Run `python3 -m bga.cli analyze <fixture>` with no flags → only WARNING+ level messages (if any) appear on stderr; default output otherwise unchanged from before this task.
2. Run with `--verbose` → DEBUG-level messages appear, including ingestion counts and normalization results.
3. Run with `--quiet` → no log output at all on success.
4. Run with `--log-file /tmp/bga.log` → confirm the file is created and contains the same messages that would've gone to console at the configured level.
5. `PYTHONPATH=. python3 tests/test_e2e.py` still passes (logging additions must not change analysis output).

## Verification Log
_(append real command + output here once run, before marking 🟢)_
