# UX-12: capture real native `--max-jobs` + host CPU core count; flag oversubscription

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** `UX-09` (the joint-optimization finding this directly closes the cheapest part of)

## Motivation

`UX-09` proved, with real evidence, that `--builders` (BuildStream's own element-dispatch concurrency) and native `--max-jobs` (each element's own internal `make -jN`/`ninja` parallelism) both consume the same physical CPU cores, uncoordinated - and that `bga`'s current capacity model has zero visibility into the second axis. Checking exactly how zero: `tools/bst_extract_run.py:325` sets `resource_capacities.PROCESS = scheduler["builders"]`, and run-context/v9's own `max_jobs` field is - confirmed via `tools/bst_log_to_chrome_trace.py:207-224`'s own docstring - a spec-defined synonym for `builders` itself, **not** the real native `--max-jobs` value ("`--max-jobs` is a different, unrelated concept... and is not what run-context/v9's `max_jobs` field means"). So today, no run-context.json anywhere records the real `--max-jobs` a build was actually invoked with, and none records the host's real CPU core count either. `bga` cannot even show a user "you ran builders=8 × max-jobs=8 = 64 potential concurrent processes on a 4-core host" - the input data for that sentence doesn't exist.

This is the cheap, immediately-actionable half of `UX-09`'s implication - distinct from `UX-11`'s much larger intra-sandbox profiler project, which answers a deeper question ("is a single element's own internal parallelism well-used") that this task does not attempt.

## Required Fix

1. **Capture the real `--max-jobs` value.** It isn't visible in BuildStream's own build log the way `--builders`/`--fetchers`/`--pushers` are (confirmed: those three are parsed from real log lines in `bst_log_to_chrome_trace.py:314-320`; `max-jobs` prints nowhere in the log itself). It has to be captured out-of-band - either as an explicit new CLI flag on `tools/bst_extract_run.py`/`tools/bst_run_wrapped.py` (the caller already knows what they passed to `bst --max-jobs N build`), or by querying `bst show --format '%{max-jobs}'` against the project at extraction time (mirrors how `tools/bst_show_to_graph.py` already queries other per-element fields - see `UX-15` below for why a single global value may not be the whole story).
2. **Capture host CPU core count** at extraction time (`os.cpu_count()`, or `len(os.sched_getaffinity(0))` where available - the more correct one under cgroup/container CPU limits, which is exactly the kind of real environment `bga`'s own CI runs in).
3. **Store both as new run-context.json provenance fields** - not reusing the already-taken `max_jobs` name (would silently collide with the existing spec-defined field and corrupt `resource_capacities` math). Something like `native_max_jobs` and `host_cpu_count`, clearly separate from `resource_capacities`.
4. **Surface an oversubscription/undersubscription signal.** When `resource_capacities.PROCESS * native_max_jobs > host_cpu_count` by a meaningful margin, emit a soft violation/caveat in `bga analyze`'s output (report text + JSON) naming the real numbers - directly quantifying, per-run, the exact condition `UX-09` demonstrated causes real slowdown (8×8 on 4 cores was ~11% slower than 4×4). Symmetrically, flag meaningful undersubscription (`builders * max_jobs << host_cpu_count`) as a "you may be leaving cores idle" hint - a distinct, real signal from the existing `RESOURCE_WAIT` category (which measures wait for BuildStream's own dispatch slots, not host-core idle time).

## Out of Scope

- Any change to `LB`/`efficiency_score` math itself - this task only adds visibility (new fields + a caveat message), not a new bound. See `UX-13` for the report-honesty follow-up and `UX-14` for the deeper replay/sweep modeling gap.
- Remote-execution builds - `UX-09` already established the real bottleneck is invisible to the local client in that mode; this task's oversubscription signal is only meaningful for local sandboxes.

## Acceptance Test

1. `tools/bst_extract_run.py` (or a documented wrapper flag) records `native_max_jobs` and `host_cpu_count` in a real run's `run-context.json`.
2. A real re-extraction of `examples/05-cmake-cpp-toolchain`'s `8×8` configuration (the one `UX-09` measured as slower than `4×4`) produces an oversubscription caveat in `bga analyze`'s output naming the real numbers (builders=8, max-jobs=8, host_cpu_count=4).
3. The `4×4` configuration (BuildStream's own real defaults on this host) does not trigger the same caveat.
4. Full suite green.

## Verification Log

Not started. Filed 2026-08-15 following a direct re-check of `UX-09`'s own "Implication for `bga`" section against the real current code (`tools/bst_extract_run.py:325`, `tools/bst_log_to_chrome_trace.py:207-224`), confirming the native `--max-jobs` value and host core count are captured nowhere in the pipeline today.
