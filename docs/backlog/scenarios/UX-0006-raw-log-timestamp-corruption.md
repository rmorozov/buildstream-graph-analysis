# UX-06: `--format raw` corrupts cross-task ordering on real multi-task logs

**Priority:** High | **Status:** 🟢 Done | **Depends on:** none | **Topic:** capture | **Area:** tools

## Motivation

Found while building `examples/04-critical-path-optimization` for UX-05's real optimization walkthrough. `tools/bst_log_to_chrome_trace.py --format raw` (the format `tools/bst_extract_run.py --format raw` and, critically, **all three existing example projects' CI job** (`.github/workflows/ci.yml`'s `bst-examples` job, `examples/01..03`) use to extract a real `bst build` log saved to a file) reconstructs absolute timestamps as:

```python
# tools/bst_log_to_chrome_trace.py, _process_raw_line
ts = self.raw_start_time_us + int(elapsed_s * 1_000_000)
```

where `elapsed_s` comes from BuildStream's own `[HH:MM:SS]` per-line prefix. The module's docstring and comments assume this prefix is "elapsed time since the invocation started" - i.e. a single global session clock. It is not. Confirmed against BuildStream 2.7.0's real installed source (`buildstream/_messenger.py`, `timed_activity`):

```python
@contextmanager
def timed_activity(self, activity_name, *, detail=None, ...):
    with self.timed_suspendable() as timedata:
        ...
        elapsed = datetime.datetime.now() - timedata.start_time
        message = Message(MessageType.SUCCESS, activity_name, elapsed=elapsed, ...)
```

`timedata` is scoped to *that one* `timed_activity` call - the elapsed bracket resets to `[00:00:00]` at the start of **every** task, not once per `bst build` invocation. Directly observed in a real log: `core.bst`'s "Running commands SUCCESS" printed `[00:00:04]` (correct - it ran `sleep 4`), then the very next task, `lib-a.bst`'s "Staging dependencies SUCCESS", printed `[00:00:00]` again despite starting well after core.bst's real 4 seconds had elapsed. `--format raw`'s parser adds each of these per-task-relative elapsed values to the *same* `raw_start_time_us` anchor, so every task's events collapse toward the start of the file regardless of true wall-clock position - corrupting cross-task ordering while leaving each task's own internal START→SUCCESS duration coincidentally correct (the per-task anchor error cancels out within one task's own subtraction).

## Observed Symptoms

Reproduced on two independent real builds (`examples/04-critical-path-optimization`, and a freshly cache-cleared rebuild of `examples/01-resource-contention`) extracted with `--format raw` the same way CI does:

- `bga analyze` reports numerous `ordering_violation`/`clamp_negative_duration` gate failures (tasks excluded from analysis).
- `Confidence: 0.00 (low)`.
- `Total Duration` artificially short vs. BuildStream's own real "Pipeline Summary" (e.g. 4.0s reported vs. real ~11s wall clock for example 04's baseline; 3.0s vs. real ~12s for example 01).
- **`Efficiency Score: 4.00`** for example 01 - outside UX-02's documented `[0.0, 1.0]` range, since `LB` is computed correctly-large from real per-task durations while the corrupted `horizon_us` denominator collapses artificially small.

This means the "real corner-case data" examples 01-03's CI job has been reporting since it was added is very likely carrying corrupted absolute timing - directionally-real category signals (e.g. "RESOURCE_WAIT occurred at all") may still be roughly right by coincidence, but exact numeric claims from that CI job's own historical runs should be treated with suspicion until this is fixed.

## Workaround Used for UX-05

Rather than fix the raw-mode algorithm (see Required Fix - real design work, not a one-line change), UX-05's real example-project numbers were captured with a new, narrow tool, `tools/bst_run_wrapped.py`, which runs a real `bst` command and writes a **wrapped**-format log live (one real UTC timestamp per line, as the command actually runs) instead of saving a raw log to parse after the fact. `--format wrapped`'s parser (`_process_wrapped_line`) never uses BuildStream's own elapsed field - it anchors purely on the wrapper's own absolute timestamp - so it isn't affected by this bug. This is a capture-time workaround, not a fix to `--format raw` itself; `--format raw`/`--format auto` remain broken for saved-log input.

## Fix Implemented

The premise behind both deferred options - "no global time anchor exists in the raw log, so absolute timestamps are unrecoverable" - turned out to be wrong. A global anchor isn't actually needed: what corrupted ordering was a naive *re-anchoring* bug, not a fundamental information gap, and it's fixable by reconstructing timestamps relative to a single monotonically-advancing watermark instead of re-deriving each task's start from its own most recent per-task-relative elapsed value.

**Algorithm** (`tools/bst_log_to_chrome_trace.py`, `_process_raw_line`): a global watermark tracks "the latest reconstructed timestamp seen so far." Every task's outer START is anchored to the *current* watermark (never to its own elapsed, which is meaningless on a START line anyway - BuildStream prints `[--:--:--]` there in practice). When a task's outer terminal event arrives, its real per-task elapsed is applied on top of that task's own anchor (not the watermark), producing its true absolute end time, which then advances the watermark for whatever comes next. The existing `handle_bst_event` depth-collapsing logic (`active_tasks[hash]["depth"]`) already identified exactly which START/terminal pair per task-hash is the "outer" one that should drive span boundaries - nested sub-activity START/terminal pairs (Staging dependencies, Running commands, Caching artifact, etc.) just increment/decrement depth without touching the anchor or watermark. `_process_raw_line` was rewritten to mirror that same depth semantics (hash-keyed depth tracking for per-element tasks, a parallel LIFO stack for `main:core activity` phases), rather than pattern-matching on message text.

**Validation methodology**: real dual-capture ground truth was derived by stripping the `[wrapper][...] INFO: ` prefix from an already-captured `--format wrapped` log (real UTC timestamps, proven correct) of a real `examples/04-critical-path-optimization` build - producing a synthetic raw-format log from the *exact same real build run*, so the reconstruction algorithm could be checked against real per-line ground truth, not just synthetic data. Two iterations:

1. First prototype (naive "anchor = last START seen for this hash"): max error 10.331s / avg error 3.684s. Root cause: BuildStream's final per-task "outer" terminal line (message is an artifact log file path, e.g. `project/element/hash-build.timestamp.log`) has elapsed relative to the *task's overall start*, but the naive algorithm re-anchored on each nested sub-activity's own START, so this line's elapsed got added to the wrong (much later) anchor, corrupting the watermark for every subsequent task.
2. Depth-aware fix (matching `handle_bst_event`'s existing outer-START/outer-terminal semantics): max error 1.058s / avg error 0.931s - within BuildStream's own 1-second reporting granularity, i.e. correct up to the precision the source data itself carries.

**Real re-verification** (2026-08-15, independent of the dual-capture prototype - the actual production code path, run against two independent real projects extracted with `--format raw` exactly as CI does): `examples/01-resource-contention` (freshly cache-cleared rebuild) now reports `Confidence: 1.00 (high)`, zero `ordering_violation`/`clamp_negative_duration` gate exclusions, `Total Duration: 12.0s` (matches the real log's own `main:core activity SUCCESS Build` line, `[00:00:12]`, and its Pipeline Summary), `Efficiency Score: 1.00` (was `4.00`, outside the valid `[0.0, 1.0]` range, before the fix). `examples/04-critical-path-optimization`'s raw-extracted baseline likewise now produces `Confidence: 1.00 (high)` with zero gate exclusions.

No CI/example migration was needed: since `--format raw` is now correct rather than fundamentally unfixable, `.github/workflows/ci.yml`'s existing `bst-examples` job (examples 01-03, `--format raw`) was left as-is - the fix applies transparently to that same code path rather than requiring examples 01-03 to move to `--format wrapped`.

## Out of Scope

- Rewriting `tools/bst_run_wrapped.py` into a `--format raw` replacement inside `bst_log_to_chrome_trace.py` itself - kept as a separate, narrow tool for now.
- Auditing/re-running examples 01-03's specific historical CI numbers - flagged here as suspect, not independently re-verified in this pass.

## Acceptance Test

1. A real multi-task build (`--builders` < fan-out width, so at least 2 tasks overlap) captured to a plain log file, extracted with the fixed `--format raw`, produces a `bga analyze --diagnostics` run with `Confidence` in the high band, zero `ordering_violation`/`clamp_negative_duration` gate exclusions, and `Total Duration` matching BuildStream's own "Pipeline Summary" total within its own reported granularity.
2. `efficiency_score` stays within `[0.0, 1.0]` on that same run.
3. `.github/workflows/ci.yml`'s `bst-examples` job's real `--format raw` extraction path re-verified (locally, against fresh real builds of the same examples) as producing sane `bga analyze` output.
4. Full suite green.

## Verification Log

Real reproduction evidence gathered 2026-08-15 (see Observed Symptoms above) - both example builds' raw logs and `bga analyze` output inspected directly; `_messenger.py` source read from the real installed BuildStream 2.7.0 package.

Fixed and re-verified for real, 2026-08-15. New/updated unit tests in `tests/unit/test_bst_log_converter.py` (`test_downstream_task_does_not_collapse_to_upstreams_own_start`, `test_each_tasks_own_real_duration_is_preserved`, `test_nested_subphases_own_elapsed_does_not_corrupt_the_outer_span`, plus two tests replacing the old, now-incorrect `test_raw_mode_converts_elapsed_to_absolute_microseconds`) exercise the watermark+depth-anchor algorithm directly, including the exact upstream-then-downstream-task-with-reset-elapsed-bracket symptom from the original bug report. `tests/unit/test_pipeline_overhead.py` and `tests/unit/test_bst_checkout_cost.py`'s synthetic fixtures were updated to use realistic `[--:--:--]` START lines (BuildStream never prints a nonzero elapsed on a START) instead of the unrealistic nonzero-elapsed STARTs they'd used before, with all originally-expected totals preserved and re-verified. Real dual-capture validation (see Fix Implemented) against `examples/04-critical-path-optimization` reduced max reconstruction error from 10.331s (naive re-anchoring) to 1.058s (depth-aware fix, matching BuildStream's own 1-second reporting granularity) against real ground truth. Production code re-verified against fresh real `--format raw` extractions of `examples/01-resource-contention` and `examples/04-critical-path-optimization`: `Confidence: 1.00 (high)`, zero `ordering_violation`/`clamp_negative_duration` gate exclusions, `Total Duration`/`Efficiency Score` both sane (`12.0s`/`1.00` for example 01, matching its real Pipeline Summary; was `4.00` efficiency score, outside the valid range, before the fix). Full suite green (`make lint`, `pytest` - 467 passed, same 7 pre-existing environment-only failures as `main` - `bst source track`/missing-`Targets:`-line issues in `test_bst_extract_run.py`/`test_bst_extract_run_strict.py`/`test_bst_checkout_cost.py`'s real-`bst`-invoking tests, unrelated to this change).
