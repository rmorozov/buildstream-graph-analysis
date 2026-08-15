# UX-06: `--format raw` corrupts cross-task ordering on real multi-task logs

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** none

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

## Required Fix (deferred - real design work, not attempted here)

`--format raw` fundamentally cannot reconstruct correct absolute timestamps from a saved log file after the fact, because BuildStream's own log gives no global time anchor at all (only per-task-relative elapsed). Two real options, both non-trivial:
1. Deprecate `--format raw` for saved-log input entirely; steer users toward `tools/bst_run_wrapped.py`-style live capture (wrapped format) as the only supported path for real builds. Simplest, but a behavior/workflow change with a doc/migration cost across `docs/ingestion-pipeline.md` and all three existing example projects' CI wiring.
2. Make `--format raw` do live/streaming capture itself (tag each line with `datetime.now()` as it's read from a pipe, not after the fact from a static file) - closes the gap for the "invoke and extract in one step" case but does nothing for genuinely already-saved historical logs, which have no recoverable absolute anchor by construction.

Either option needs: migrating `.github/workflows/ci.yml`'s `bst-examples` job (examples 01-03) off `--format raw`, re-validating those three examples' CI-reported numbers are sane afterward, and updating `docs/ingestion-pipeline.md`'s format description.

## Out of Scope

- Rewriting `tools/bst_run_wrapped.py` into a `--format raw` replacement inside `bst_log_to_chrome_trace.py` itself - kept as a separate, narrow tool for now.
- Auditing/re-running examples 01-03's specific historical CI numbers - flagged here as suspect, not independently re-verified in this pass.

## Acceptance Test

1. A real multi-task build (`--builders` < fan-out width, so at least 2 tasks overlap) captured to a plain log file, extracted with the fixed `--format raw`, produces a `bga analyze --diagnostics` run with `Confidence` in the high band, zero `ordering_violation`/`clamp_negative_duration` gate exclusions, and `Total Duration` matching BuildStream's own "Pipeline Summary" total within its own reported granularity.
2. `efficiency_score` stays within `[0.0, 1.0]` on that same run.
3. `.github/workflows/ci.yml`'s `bst-examples` job re-run for real, all three examples' `bga analyze` output re-inspected and sane.
4. Full suite green.

## Verification Log

Real reproduction evidence gathered 2026-08-15 (see Observed Symptoms above) - both example builds' raw logs and `bga analyze` output inspected directly; `_messenger.py` source read from the real installed BuildStream 2.7.0 package. Not yet fixed - filed as backlog per this session's scope (UX-05's real optimization-walkthrough experiment), worked around via `tools/bst_run_wrapped.py` instead.
