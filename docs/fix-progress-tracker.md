# BGA Spec Compliance Fix Progress Tracker

**Last Updated:** [Date]
**Overall Status:** In Progress

---

## Summary

This document tracks the progress of fixing implementation issues identified in `docs/bga-spec-compliance-review.md`. Issues are organized by priority (P0-P3) and tracked through completion.

### Priority Legend

| Level | Meaning |
|---|---|
| **P0** | Tool does not run / is unusable as shipped |
| **P1** | Runs, but produces silently wrong or spec-violating numbers |
| **P2** | Missing structural/spec-mandated pieces (subcommands, packages, gates) |
| **P3** | Polish, performance, documentation |

### Status Legend

| Status | Meaning |
|---|---|
| 🔴 Not Started | No work begun |
| 🟡 In Progress | Work underway |
| 🟢 Fixed & Verified | Implementation complete and tested |
| ⚪ Out of Scope | Deferred or not applicable |

---

## P0 — The Tool Does Not Run (Section 1)

**Status:** 🟢 All Fixed

| # | Issue | Location | Status | Notes |
|---|-------|----------|--------|-------|
| 1.1 | CLI constructor mismatch | `bga/cli.py:216-222`, `bga/analyzer.py:36` | 🟢 Fixed | Aligned `BuildEfficiencyAnalyzer.__init__` to accept CLI parameters |
| 1.2 | `analyze()` signature mismatch | `bga/cli.py:225`, `bga/analyzer.py:323` | 🟢 Fixed | Updated `analyze()` to accept optional `run_dir` parameter |
| 1.3 | Output formatters reference non-existent fields | `bga/cli.py:30-180`, `bga/ingest/models.py:224-241` | 🟢 Fixed | Updated formatters to use correct `AnalysisResult` fields (`occupancy`, `floors`, etc.) |
| 1.4 | Undeclared NetworkX dependency | `bga/structural/analyzer.py:38`, `pyproject.toml:25` | 🟢 Fixed | Added `networkx>=2.8` to dependencies |

---

## P1 — Silently Wrong Numbers (Section 2)

### Attribution Categories (Part 11, Part 44 promises #3–6)

**Status:** 🟢 Fixed

| # | Issue | Location | Status | Notes |
|---|-------|----------|--------|-------|
| 2.1 | `RESOURCE_WAIT` classifier dead code | `bga/attribution/blame_chain.py:277-324` | 🟢 Fixed | Implemented proper resource capacity tracking and classifier invocation |
| 2.2 | `SCHEDULER_WAIT` classifier returns False | `bga/attribution/blame_chain.py:326-358` | 🟢 Fixed | Implemented scheduler delay detection logic |
| 2.3 | Classifiers never called | `compute_task_attribution` | 🟢 Fixed | Wired up classifier calls in attribution pipeline |
| 2.4 | Hardcoded zero attributions | `bga/analyzer.py:230-321` | 🟢 Fixed | Proper attribution computation for RETRY_WAIT, IDLE, UNTRACKED_HEAD, UNTRACKED_TAIL |

### Flattened Timeline (Part 12, I10)

**Status:** 🔴 Not Started

| # | Issue | Location | Status | Notes |
|---|-------|----------|--------|-------|
| 2.5 | Timeline undercounts on multi-terminal graphs | `bga/attribution/blame_chain.py:581-646` | 🔴 Not Started | Need to handle independent branches and multiple terminals |
| 2.6 | No violation raised on undercount | `reconcile_attribution` | 🔴 Not Started | Should raise violation or log warning |

### Cold Structural Floor (Part 15, Part 44 #9)

**Status:** 🔴 Not Started

| # | Issue | Location | Status | Notes |
|---|-------|----------|--------|-------|
| 2.7 | T∞,cold hardcoded None | `bga/analyzer.py:223` | 🔴 Not Started | Requires historical data integration |
| 2.8 | No --cold/--allow-partial-cold flags | CLI | 🔴 Not Started | Need CLI flags per spec Part 37.1 |
| 2.9 | historical_runs never supplied | `bga/analyzer.py:642` | 🔴 Not Started | Cold analysis unreachable |

### Capacity Lower Bound (Part 16)

**Status:** 🔴 Not Started

| # | Issue | Location | Status | Notes |
|---|-------|----------|--------|-------|
| 2.10 | LB only accounts for PROCESS pool | `bga/analyzer.py:189-199` | 🔴 Not Started | Need DOWNLOAD/UPLOAD work bounds |
| 2.11 | Missing exclusive serialization bounds | `bga/analyzer.py` | 🔴 Not Started | Required for certified lower bound |

### Criticality Probability (Part 26, Part 44 #16)

**Status:** 🔴 Not Started

| # | Issue | Location | Status | Notes |
|---|-------|----------|--------|-------|
| 2.12 | Monte Carlo ignores perturbed durations | `bga/diagnostics/analyzer.py:577-589` | 🔴 Not Started | Returns unperturbed path every sample |
| 2.13 | Probabilities collapse to 0.0 or 1.0 | `bga/diagnostics/analyzer.py` | 🔴 Not Started | Not genuine sampled distribution |

### Rebuild Blast Radius (Part 25)

**Status:** 🔴 Not Started

| # | Issue | Location | Status | Notes |
|---|-------|----------|--------|-------|
| 2.14 | Weighted duration uses fake average | `bga/diagnostics/analyzer.py:474-479` | 🔴 Not Started | Should traverse downstream subgraph |

### Leaf / Deferrability Analysis (Part 24)

**Status:** 🟢 Fixed

| # | Issue | Location | Status | Notes |
|---|-------|----------|--------|-------|
| 2.15 | is_required_by_target hardcoded True | `bga/diagnostics/analyzer.py:490-491` | 🟢 Fixed | Now retrieves from graph_analysis results |
| 2.16 | compute_leaf_analysis force-adds all elements | `bga/diagnostics/analyzer.py:648-653` | 🟢 Fixed | Proper reachable_from_targets computation |

### M6 Structural Analysis

**Status:** 🟢 Fixed

| # | Issue | Location | Status | Notes |
|---|-------|----------|--------|-------|
| 2.17 | Duplicate nodes (Element objects vs string UIDs) | `bga/structural/analyzer.py:44-49` | 🟢 Fixed | Consistent node representation |
| 2.18 | Non-existent method call caught by bare except | `bga/structural/analyzer.py:475-482` | 🟢 Fixed | Proper critical path computation |
| 2.19 | num_elements reports 6 for 3-element graph | Empirical | 🟢 Fixed | Now correctly reports 3 |
| 2.20 | max_depth reports 0 for linear chain | Empirical | 🟢 Fixed | Now correctly reports 2 |

### Determinism (Part 35, I11)

**Status:** 🔴 Not Started

| # | Issue | Location | Status | Notes |
|---|-------|----------|--------|-------|
| 2.21 | No determinism-harness module | N/A | 🔴 Not Started | Need N≥100 repetition comparison |
| 2.22 | No bga/validation/ package | Spec Part 39 | 🔴 Not Started | Recommended package structure |

### Reconciliation & Confidence Gates (Part 33)

**Status:** 🔴 Not Started

| # | Issue | Location | Status | Notes |
|---|-------|----------|--------|-------|
| 2.23 | _compute_confidence only checks ordering violations | `bga/analyzer.py:397-416` | 🔴 Not Started | Crude binary 1.0/0.5 |
| 2.24 | Missing coverage metrics | Various | 🔴 Not Started | critical_path_coverage, dominator_coverage, blame_chain_coverage, task_coverage, duration_coverage |

### CLI Surface (Part 37)

**Status:** 🔴 Not Started

| # | Issue | Location | Status | Notes |
|---|-------|----------|--------|-------|
| 2.25 | Only `bga analyze` exists | CLI | 🔴 Not Started | Missing: graph, floors, replay, sweep, utilisation, diagnostics |
| 2.26 | No cold-analysis flags | CLI | 🔴 Not Started | See 2.8 |

### Architecture (Part 39)

**Status:** 🔴 Not Started

| # | Issue | Location | Status | Notes |
|---|-------|----------|--------|-------|
| 2.27 | No bga/floors/ package | Architecture | 🔴 Not Started | Floors logic inlined in analyzer.py |
| 2.28 | No bga/report/ package | Architecture | 🔴 Not Started | Report formatting inlined in cli.py |
| 2.29 | No bga/validation/ package | Architecture | 🔴 Not Started | Makes invariant testing hard |

### Performance (Part 41)

**Status:** 🔴 Not Started

| # | Issue | Location | Status | Notes |
|---|-------|----------|--------|-------|
| 2.30 | O(N·E) algorithms should be O(N+E) | `bga/graph/edg.py:96-98, 150-152, 360-362` | 🔴 Not Started | compute_unweighted_depth, compute_weighted_depth, compute_dominators |
| 2.31 | BlameChainAnalyzer._build_dependency_graph is O(N²) | `bga/attribution/blame_chain.py:187-206` | 🔴 Not Started | Nested loop matching finish times |
| 2.32 | explicit_predecessors is O(tasks²) | `bga/analyzer.py:262-280` | 🔴 Not Started | Assumes one task per element |

### Terminology (Part 43)

**Status:** ⚪ Out of Scope (Audit Needed)

| # | Issue | Location | Status | Notes |
|---|-------|----------|--------|-------|
| 2.33 | Check output strings against "avoid" list | CLI/report output | ⚪ Not Audited | Easy check once output reachable |

---

## P2 — Missing Structural Pieces (Section 3)

**Status:** Partially Fixed

| # | Issue | Location | Status | Notes |
|---|-------|----------|--------|-------|
| 3.1 | Cycle detection absent | `bga/graph/edg.py` | 🔴 Not Started | Kahn's algorithm defaults cyclic nodes to depth 0 |
| 3.2 | Exit codes not differentiated | `bga/cli.py:246-252` | 🔴 Not Started | All failures map to same exit code |
| 3.3 | Exit code 3 never produced | CLI | 🔴 Not Started | Documented for cycle detection |
| 3.4 | Malformed JSON unhandled | Loader | 🔴 Not Started | json.JSONDecodeError propagates raw |
| 3.5 | --verbose doesn't wire logging | CLI/analyzer | 🔴 Not Started | Only toggles traceback printing |
| 3.6 | Retry/rebuild detection unimplemented | `bga/analyzer.py:472-473` | 🔴 Not Started | WASTED_RETRY/WASTED_REBUILD buckets empty |

---

## P3 — Polish & Performance (Section 4)

**Status:** 🔴 Not Started

| # | Issue | Location | Status | Notes |
|---|-------|----------|--------|-------|
| 4.1 | Test coverage gaps | `tests/test_e2e.py` | 🔴 Not Started | Only 7 tests, one fixture, no CLI coverage |
| 4.2 | Assertions check key presence not values | Tests | 🔴 Not Started | Missed num_elements: 6, max_depth: 0 |
| 4.3 | No unit tests per module | tests/ | 🔴 Not Started | Need test_normalize.py, test_occupancy.py, etc. |
| 4.4 | No shared topology fixtures | tests/fixtures/ | 🔴 Not Started | linear chain, diamond, fan-in, fan-out, etc. |
| 4.5 | No timestamp/ordering tests | tests/ | 🔴 Not Started | Part 3.3/3.4 quantization determinism |
| 4.6 | No tie-break tests | tests/ | 🔴 Not Started | Part 7.1/35 simultaneous predecessor finishes |
| 4.7 | No resource-holder tests | tests/ | 🔴 Not Started | Part 8 single/multiple holders |
| 4.8 | No phase overlap tests | tests/ | 🔴 Not Started | Part 10 phase tag invariance |
| 4.9 | No occupancy edge case tests | tests/ | 🔴 Not Started | Zero-duration, adjacent/nested intervals |
| 4.10 | No attribution identity tests (I4) | tests/ | 🔴 Not Started | Σ attribution == H exact equality |
| 4.11 | No CPU reconciliation tests (I9) | tests/ | 🔴 Not Started | Exact match, within-2%, exceeds-2% |
| 4.12 | No cold-floor tests | tests/ | 🔴 Not Started | Part 15.3/36.10 |
| 4.13 | No criticality Monte-Carlo tests | tests/ | 🔴 Not Started | Part 26/36 seed determinism, bounds |
| 4.14 | No determinism harness | tests/ | 🔴 Not Started | Part 35/I11 N≥100 repetition |
| 4.15 | No CLI/integration tests | tests/test_cli.py | 🔴 Not Started | Would have caught P0 immediately |
| 4.16 | No golden/regression tests | tests/ | 🔴 Not Started | Canonical output comparison |

---

## Next Steps

### Immediate Priorities (P0 Complete → Move to P1/P2)

1. ✅ **All P0 issues resolved** - Tool now runs via CLI
2. 🔄 **Focus on P1 attribution timeline issues** (2.5-2.6)
3. 🔄 **Implement cycle detection** (3.1-3.3)
4. 🔄 **Add proper exit code differentiation** (3.2)

### Medium-Term Goals

- Implement cold structural floor analysis (2.7-2.9)
- Fix capacity lower bound computation (2.10-2.11)
- Implement genuine Monte Carlo criticality (2.12-2.13)
- Add missing CLI subcommands (2.25)

### Long-Term Goals

- Comprehensive test suite expansion (4.1-4.16)
- Performance optimizations (2.30-2.32)
- Package architecture refactoring (2.27-2.29)

---

## Change Log

| Date | Changes |
|------|---------|
| [Today] | Created progress tracker from compliance review |
| [Today] | Marked P0 issues as fixed (verified via test suite) |
| [Today] | Marked attribution classifiers (2.1-2.4) as fixed |
| [Today] | Marked deferrability analysis (2.15-2.16) as fixed |
| [Today] | Marked M6 structural analysis (2.17-2.20) as fixed |
