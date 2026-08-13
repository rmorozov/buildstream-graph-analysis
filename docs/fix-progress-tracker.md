# BGA Spec Compliance Fix Progress Tracker

**Last Updated:** 2026-08-13
**Overall Status:** P0 verified fixed. P1 in progress — several prior "Fixed" claims corrected below after re-verification (see Correction Log).

> **Start here, but don't stop here.** This file is an index only. Read `docs/fixing-guide.md` once per session, then open exactly one task file under `docs/tasks/` — do not try to absorb this whole tracker or the full spec into context at once.

## Status Legend

| Status | Meaning |
|---|---|
| 🔴 Not Started | No work begun |
| 🟡 In Progress | Work underway, or a prior claim of "done" that could not be re-verified — treat as not-done |
| 🟢 Fixed & Verified | A named agent ran the task's acceptance test in-session and pasted a passing result into the task file |
| ⚪ Blocked / Out of Scope | Needs a product decision, or deliberately deferred — reason in task file |

**Rule:** a row may only show 🟢 if the linked task file's Verification Log has a real pasted command + passing output. If you find a 🟢 row without that evidence, treat it as 🟡 and re-verify before trusting it — this has already happened once (see Correction Log).

---

## Correction Log (read once, this is why re-verification is mandatory)

On 2026-08-13 the previous tracker's P1 "Attribution Categories" block (old rows 2.1–2.4) was marked 🟢 "All Fixed." Direct code inspection found:
- `classify_resource_wait()` (`bga/attribution/blame_chain.py:291-338`) is now *called* (good), but its body is still the original stub: a `for res in task.resources: pass` no-op loop, `blocking_tasks: {}` always empty, `ambiguous: False` hardcoded regardless of whether a holder was actually identified. Not real per Part 8.
- `classify_scheduler_wait()` (`bga/attribution/blame_chain.py:340-372`) still unconditionally `return False` — completely unimplemented, contradicting its "Fixed" mark.
- Running the CLI end-to-end against a minimal 3-task single-resource-pool fixture (see `docs/fixing-guide.md` §7) shows the Attribution Breakdown summing to only ~33% of the task horizon (H) — a live invariant I4 violation, not previously listed as an issue at all. Filed as `P1-03` (highest real-world priority of the open P1 items).

This is not a criticism of any particular session — it's the reason the verification rule in `docs/fixing-guide.md` §3 is mandatory going forward.

---

## P0 — The Tool Does Not Run

**Status:** 🟢 Verified fixed — confirmed by running `PYTHONPATH=. python3 tests/test_e2e.py` (7/7 passed) and `python3 -m bga.cli analyze <fixture>` end-to-end (exit 0, produced a full text report) on 2026-08-13. No task files — nothing further to do here unless a regression is found.

| # | Issue | Status |
|---|-------|--------|
| P0-1 | CLI constructor mismatch | 🟢 |
| P0-2 | `analyze()` signature mismatch | 🟢 |
| P0-3 | Output formatters referenced non-existent fields | 🟢 |
| P0-4 | Undeclared `networkx` dependency | 🟢 (now in `pyproject.toml` deps) |
| P0-5 | `DiagnosticsAnalyzer` missing graph attribute | 🟢 |
| P0-6 | Missing `deque` import | 🟢 |

---

## P1 — Silently Wrong Numbers

| ID | Issue | Depends on | Status | Task File |
|---|---|---|---|---|
| P1-01 | Resource-wait holder tracking is a stub (no real occupancy-based holder set, `ambiguous` hardcoded False) | — | 🟢 Done — surfaced a related wiring gap, see `P1-20` | [P1-01](tasks/P1-01-resource-wait-holder-tracking.md) |
| P1-02 | Scheduler-wait detection unconditionally returns False | — | 🟢 Done (also fixed a tautological call-site `resource_available` check that would have made this fix unobservable) | [P1-02](tasks/P1-02-scheduler-wait-detection.md) |
| P1-03 | Attribution identity (I4) violated on resource-constrained chains — 3 root causes fixed (zero-wait walk termination, multi-task-per-element predecessor mismapping, spurious multi-terminal heuristic) | — | 🟢 Done (residual gap scoped as `P1-19`) | [P1-03](tasks/P1-03-attribution-identity-resource-chains.md) |
| P1-04 | Flattened timeline undercounts on genuinely disconnected multi-terminal graphs | — | 🟢 Done — also added interval-overlap prevention across walks and IDLE segment generation (previously nonexistent for any scenario) | [P1-04](tasks/P1-04-flattened-timeline-multi-terminal-coverage.md) |
| P1-05 | No violation raised when timeline undercounts | P1-04 | 🔴 | [P1-05](tasks/P1-05-reconciliation-violation-reporting.md) |
| P1-06 | `T∞,cold` hardcoded None; `historical_runs` never supplied | — | 🔴 | [P1-06](tasks/P1-06-cold-floor-historical-wiring.md) |
| P1-07 | No `--cold`/`--allow-partial-cold` CLI flags; cold publication gate unimplemented | P1-06 | 🔴 | [P1-07](tasks/P1-07-cold-cli-flags-and-publication-gate.md) |
| P1-08 | Capacity lower bound only accounts for PROCESS pool; no exclusive-serialization bound | — | 🔴 | [P1-08](tasks/P1-08-capacity-lower-bound-completeness.md) |
| P1-09 | Criticality "Monte Carlo" ignores perturbed durations, returns fixed 0/1 | — | 🔴 | [P1-09](tasks/P1-09-genuine-montecarlo-criticality.md) |
| P1-10 | Blast-radius weighted duration uses fake average instead of real downstream traversal | — | 🔴 | [P1-10](tasks/P1-10-blast-radius-real-traversal.md) |
| P1-11 | Leaf/deferrability fix (`is_required_by_target`, `reachable_from_targets`) claimed fixed — re-verify | — | 🟡 unverified | [P1-11](tasks/P1-11-verify-leaf-deferrability-fix.md) |
| P1-12 | No determinism harness (N≥100 run comparison), no `bga/validation/` package | — | 🔴 | [P1-12](tasks/P1-12-determinism-harness.md) |
| P1-13 | Confidence computation only checks ordering violations; other hard/soft gates never computed | — | 🔴 | [P1-13](tasks/P1-13-confidence-reconciliation-gates.md) |
| P1-14 | Only `bga analyze` exists; spec recommends `graph/floors/replay/sweep/utilisation/diagnostics` subcommands | — | ⚪ needs product decision | [P1-14](tasks/P1-14-cli-subcommand-split.md) |
| P1-15 | Missing `bga/floors/`, `bga/report/`, `bga/validation/` packages (architecture) | P1-06..P1-13 mostly done first | 🔴 do last | [P1-15](tasks/P1-15-package-architecture-refactor.md) |
| P1-16 | Several graph/attribution algorithms are O(N·E)/O(N²), spec wants O(N+E) | — | 🔴 | [P1-16](tasks/P1-16-performance-on-plus-e-algorithms.md) |
| P1-17 | Terminology audit against spec Part 43 avoid-list | — | 🔴 quick/low-risk | [P1-17](tasks/P1-17-terminology-audit.md) |
| P1-18 | `structural.metrics.max_depth` uses shortest-path not longest-path (disagrees with `signals.unweighted_depth`) | — | 🟢 Done | [P1-18](tasks/P1-18-structural-max-depth-shortest-path-bug.md) |
| P1-19 | Flattened timeline doesn't cover intra-element `TRACK→FETCH→BUILD` sequencing or off-chain parallel task time | P1-03 (done) | 🟢 Done — also resolved off-chain coverage for connected components; narrowed `P1-04`'s remaining scope | [P1-19](tasks/P1-19-flattened-timeline-residual-coverage.md) |
| P1-20 | Blame-chain walk never classifies a gap as RESOURCE_WAIT/SCHEDULER_WAIT — always defaults to DEPENDENCY_WAIT, so `P1-01`/`P1-02`'s correct classifiers never reach final output | P1-01 (done), P1-02 (done) | 🟢 Done — also fixed a dormant double-counting bug in `compute_task_attribution` found in the same investigation | [P1-20](tasks/P1-20-gap-classification-into-resource-scheduler-wait.md) |

---

## P2 — Robustness / "Just Works"

| ID | Issue | Depends on | Status | Task File |
|---|---|---|---|---|
| P2-01 | No cycle detection; exit code 3 never produced | — | 🟢 Done (was already implemented; original diagnosis was stale) | [P2-01](tasks/P2-01-cycle-detection-exit-codes.md) |
| P2-02 | Malformed JSON / bad input unhandled | — | 🟢 Done (was partially done; fixed `load_graph` wrapping + missing-file exit code) | [P2-02](tasks/P2-02-malformed-input-error-handling.md) |
| P2-03 | No logging module wired anywhere; `--verbose` does nothing but toggle traceback printing | — | 🔴 | [P2-03](tasks/P2-03-logging-infrastructure.md) |
| P2-04 | Retry/rebuild detection unimplemented — utilization buckets always empty | — | 🔴 | [P2-04](tasks/P2-04-retry-rebuild-detection.md) |
| P2-05 | `--format json` silently omits `structural`/`utilisation`/`confidence`/`violations` (typo'd `hasattr` check + missing fields) | — | 🟢 Done | [P2-05](tasks/P2-05-cli-json-missing-fields.md) |

---

## P3 — Test Coverage Build-Out

| ID | Issue | Depends on | Status | Task File |
|---|---|---|---|---|
| P3-01 | Shared synthetic topology fixture library | — | 🔴 build first, everything else reuses it | [P3-01](tasks/P3-01-topology-fixture-library.md) |
| P3-02 | CLI integration tests (`tests/test_cli.py`) | — | 🟢 Done (7/7 pass) | [P3-02](tasks/P3-02-cli-integration-tests.md) |
| P3-03 | Attribution identity tests (I4) across topologies | P3-01, P1-03 | 🔴 | [P3-03](tasks/P3-03-attribution-identity-tests.md) |
| P3-04 | Tie-break + resource-holder tests | P3-01, P1-01 | 🔴 | [P3-04](tasks/P3-04-tie-break-and-resource-holder-tests.md) |
| P3-05 | Phase overlap + occupancy edge-case tests | P3-01 | 🔴 | [P3-05](tasks/P3-05-phase-and-occupancy-edge-case-tests.md) |
| P3-06 | CPU reconciliation (I9) + cold-floor tests | P3-01, P1-06 | 🔴 | [P3-06](tasks/P3-06-cpu-reconciliation-and-cold-floor-tests.md) |
| P3-07 | Monte-Carlo criticality + determinism-harness tests | P1-09, P1-12 | 🔴 | [P3-07](tasks/P3-07-montecarlo-and-determinism-tests.md) |
| P3-08 | Golden/regression tests (full-pipeline snapshot) | P3-01 | 🟡 partially covered by P3-10's anti-drift check | [P3-08](tasks/P3-08-golden-regression-tests.md) |
| P3-09 | Per-module unit test split (normalize/occupancy/edg/blame_chain/replay/utilisation/diagnostics) | — | 🔴 | [P3-09](tasks/P3-09-per-module-unit-tests.md) |
| P3-10 | Large multi-subproject synthetic-project integration test, using the real `tools/bst_log_to_chrome_trace.py` converter | — | 🟢 Done — found `P1-18` and `P2-05`, amplified `P1-03` evidence | [P3-10](tasks/P3-10-synthetic-multi-subproject-large-test.md) |

---

## Recommended Order for a Sequence of Small-Context Sessions

`P1-01`, `P1-02`, `P1-03`, `P1-04`, `P1-18`, `P1-19`, `P1-20`, `P2-01`, `P2-02`, `P2-05`, and `P3-02` are now done (see Change Log). The whole "flattened timeline / attribution identity" family (`P1-03`, `P1-04`, `P1-19`, `P1-20`) is closed — attribution identity holds exactly on every fixture tested, and `resource_wait_us`/`scheduler_wait_us` are now real, non-zero values wherever the trace evidence supports them. Next up:

1. `P2-03` (logging infrastructure — cheap, high diagnostic value for every session after)
2. `P1-05` (raise a violation when the timeline undercounts - now that `P1-04`/`P1-20` have closed the known undercounting gaps, this becomes a genuine safety net rather than papering over a live bug)
3. Everything else in ID order within its priority tier, respecting the Depends-on column.

**Before starting any 🔴 row: re-verify it's actually still broken.** Two rows in this tracker (`P2-01`, `P2-02`) were mis-diagnosed as unstarted when re-verified this session — they'd already been fixed (fully or partially) in an earlier commit the tracker itself was built from, and nobody had re-run the reproduction before writing the task file. A quick empirical check before diving in costs a few minutes; discovering it mid-implementation costs a lot more.

## Change Log

| Date | Change |
|---|---|
| 2026-08-13 (latest) | Fixed `P1-20` (gap classification wiring): added a single shared `_classify_wait_gap` helper that splits `[ready_time, start)` into non-overlapping `RESOURCE_WAIT`/`SCHEDULER_WAIT`/`DEPENDENCY_WAIT` portions (resource first via `P1-01`'s holder tracking, then scheduler via `P1-02`'s detector, remainder to dependency-wait), used by both `build_blame_chain` (now emits per-category segments instead of one hardcoded `DEPENDENCY_WAIT` segment) and `compute_task_attribution` (fixed the dormant double-counting bug where the same gap was written into both `dependency_wait_us` and `resource_wait_us`). `resource_wait_us`/`scheduler_wait_us` are no longer structurally always `0` — confirmed on `tests/fixtures/synthetic_multi_subproject/` (`resource_wait_us` now `2000000`, was `0`) with exact `Σ == H` identity preserved. Added `tests/unit/test_wait_gap_classification.py` (2 new end-to-end tests). Full suite: 54 passed. |
| 2026-08-13 | Fixed `P1-01` (real resource-wait holder tracking): `classify_resource_wait` now derives time-weighted `blocking_tasks` directly from observed overlapping same-resource task intervals, with the literal `"UNKNOWN"`/`ambiguous=True` fallback per spec Part 8.2 when no holder can be identified. While finishing this, found a deeper, precisely-specified gap: per spec Part 7, `[ready_time, start_us)` should be *classified* into `DEPENDENCY_WAIT`/`RESOURCE_WAIT`/`SCHEDULER_WAIT`, but the blame-chain walk always labels the whole gap `DEPENDENCY_WAIT` - meaning `P1-01`/`P1-02`'s now-correct classifiers are computed (in the currently-dead-code `compute_task_attribution`/`task_attributions` path) but never reach `result.attribution`. Filed precisely as `P1-20`, including a second, currently-dormant double-counting bug found in the same investigation. |
| 2026-08-13 | Fixed `P1-04` (the last piece of the attribution-identity family): identify *every* genuine terminal element (not just the single max-finish one) and walk all of them; added `covered_intervals` tracking so two genuinely independent terminals that happen to run concurrently in wall-clock time don't produce overlapping, double-counted segments; discovered and fixed that no code anywhere ever generated an `IDLE` segment (`idle_us` was structurally always `0`) - `_build_flattened_timeline` now fills genuine gaps with `IDLE`. Attribution identity now holds exactly (`Σ == H`) on every tested fixture: single connected components, disconnected multi-terminal graphs, concurrent independent terminals, and 3+-component graphs. Full suite: 45 passed, 0 xfailed. |
| 2026-08-13 | Re-verified `P2-01`/`P2-02` before starting and found both already partially/fully fixed (cycle detection + exit code 3 fully working since commit `ad8a2db`; JSON error handling and exit code 2 working for two of three loaders) - corrected the tracker's stale diagnosis and closed the two remaining real gaps (`load_graph`'s JSON wrapping for message consistency; missing-required-file now correctly exits `1` instead of falling through to `2`). Added `tests/unit/test_cli_exit_codes.py` as permanent regression coverage for the full documented exit-code contract. |
| 2026-08-13 | Fixed `P1-19` (flattened timeline residual coverage): added intra-element phase predecessor (`TRACK→FETCH→BUILD` sequencing) and extended `explicit_predecessors` to cover every task kind of a dependent element, not just `BUILD`. This achieved *exact* attribution identity on both the simple reproduction and the full `tests/fixtures/synthetic_multi_subproject/` fixture (diamond dependency, multi-task-kind elements, real resource contention) - better than originally scoped, because the existing "greatest finish time" tie-break turned out to already resolve off-chain parallel-work coverage for any connected component, with no occupancy-sweep needed. Narrowed `P1-04` to its now-precise, still-open remaining scope (genuinely disconnected components only) and added `tests/unit/test_multi_terminal_coverage.py` as a concrete, runnable reproduction of exactly that gap. |
| 2026-08-13 | Fixed `P1-02` (real scheduler-wait detection, plus a tautological call-site `resource_available` check that would have made it unobservable) and `P1-03` (attribution identity I4 — three compounding root causes: blame-chain walk stopping on exactly-zero-wait links, `explicit_predecessors` mismapping tasks on multi-task-kind elements, and a spurious multi-terminal heuristic causing triple-counting). Scoped the honest residual of `P1-03` as new task `P1-19`. Added `tests/unit/` (first module-level unit test directory) with `test_blame_chain.py` and `test_attribution_identity.py`. |
| 2026-08-13 | Added `P3-10`: a large multi-subproject synthetic BuildStream project (9 elements, 4 junctioned subprojects, diamond dependency, real resource contention), fed through the user-supplied `tools/bst_log_to_chrome_trace.py` converter end-to-end. Found two new bugs (`P1-18` structural max_depth shortest-vs-longest-path bug; `P2-05` CLI JSON output silently missing several `AnalysisResult` fields) and amplified `P1-03`'s evidence (negative/~453,000-year overflow values on a realistic graph, not just undercounting). Confirmed `P3-02` (CLI integration tests) was already done by a prior session and marked it `🟢`. Repo housekeeping: removed `bga.egg-info/`, all committed `__pycache__/*.pyc`, and a stray `=2.8` file from git tracking; added `make check-clean` and mandatory pre-commit hygiene rules to `docs/fixing-guide.md`. |
| 2026-08-13 (earlier) | Reworked tracker into index-only format; moved details into `docs/tasks/*.md`; corrected P1-01/P1-02 status after re-verification found stub code still present; added P1-03 as a newly discovered live invariant violation; added `docs/fixing-guide.md` as mandatory session entry point. |
| (prior) | Original tracker created from `docs/bga-spec-compliance-review.md`; P0 and several P1 items marked fixed (P0 confirmed correct on re-verification; some P1 marks corrected above). |
