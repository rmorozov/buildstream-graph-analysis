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
| P1-01 | Resource-wait holder tracking is a stub (no real occupancy-based holder set, `ambiguous` hardcoded False) | — | 🟡 corrected from 🟢 | [P1-01](tasks/P1-01-resource-wait-holder-tracking.md) |
| P1-02 | Scheduler-wait detection unconditionally returns False | — | 🔴 corrected from 🟢 | [P1-02](tasks/P1-02-scheduler-wait-detection.md) |
| P1-03 | **Attribution identity (I4) violated on resource-constrained chains** — new finding, live bug | P1-01, P1-02 likely related | 🔴 NEW | [P1-03](tasks/P1-03-attribution-identity-resource-chains.md) |
| P1-04 | Flattened timeline undercounts on multi-terminal / independent-branch graphs | — | 🔴 | [P1-04](tasks/P1-04-flattened-timeline-multi-terminal-coverage.md) |
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
| P1-18 | `structural.metrics.max_depth` uses shortest-path not longest-path (disagrees with `signals.unweighted_depth`) | — | 🔴 NEW, root cause found | [P1-18](tasks/P1-18-structural-max-depth-shortest-path-bug.md) |

---

## P2 — Robustness / "Just Works"

| ID | Issue | Depends on | Status | Task File |
|---|---|---|---|---|
| P2-01 | No cycle detection; exit code 3 never produced | — | 🔴 | [P2-01](tasks/P2-01-cycle-detection-exit-codes.md) |
| P2-02 | Malformed JSON / bad input unhandled | — | 🔴 | [P2-02](tasks/P2-02-malformed-input-error-handling.md) |
| P2-03 | No logging module wired anywhere; `--verbose` does nothing but toggle traceback printing | — | 🔴 | [P2-03](tasks/P2-03-logging-infrastructure.md) |
| P2-04 | Retry/rebuild detection unimplemented — utilization buckets always empty | — | 🔴 | [P2-04](tasks/P2-04-retry-rebuild-detection.md) |
| P2-05 | `--format json` silently omits `structural`/`utilisation`/`confidence`/`violations` (typo'd `hasattr` check + missing fields) | — | 🔴 NEW, root cause found | [P2-05](tasks/P2-05-cli-json-missing-fields.md) |

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

1. `P1-02` (scheduler wait — small, self-contained, high spec-fidelity value)
2. `P1-03` (attribution identity — the most consequential live bug found; a build tool whose headline numbers don't sum correctly is not trustworthy)
3. `P3-02` (CLI integration tests — locks in P0 and prevents this whole class of regression from recurring silently)
4. `P1-01` (real resource-holder tracking — likely related to P1-03's root cause, do after P1-03 lands so there's a passing baseline to diff against)
5. `P2-01`, `P2-03` (cycle detection + logging — cheap, high diagnostic value for every session after)
6. Everything else in ID order within its priority tier, respecting the Depends-on column.

## Change Log

| Date | Change |
|---|---|
| 2026-08-13 | Added `P3-10`: a large multi-subproject synthetic BuildStream project (9 elements, 4 junctioned subprojects, diamond dependency, real resource contention), fed through the user-supplied `tools/bst_log_to_chrome_trace.py` converter end-to-end. Found two new bugs (`P1-18` structural max_depth shortest-vs-longest-path bug; `P2-05` CLI JSON output silently missing several `AnalysisResult` fields) and amplified `P1-03`'s evidence (negative/~453,000-year overflow values on a realistic graph, not just undercounting). Confirmed `P3-02` (CLI integration tests) was already done by a prior session and marked it `🟢`. Repo housekeeping: removed `bga.egg-info/`, all committed `__pycache__/*.pyc`, and a stray `=2.8` file from git tracking; added `make check-clean` and mandatory pre-commit hygiene rules to `docs/fixing-guide.md`. |
| 2026-08-13 (earlier) | Reworked tracker into index-only format; moved details into `docs/tasks/*.md`; corrected P1-01/P1-02 status after re-verification found stub code still present; added P1-03 as a newly discovered live invariant violation; added `docs/fixing-guide.md` as mandatory session entry point. |
| (prior) | Original tracker created from `docs/bga-spec-compliance-review.md`; P0 and several P1 items marked fixed (P0 confirmed correct on re-verification; some P1 marks corrected above). |
