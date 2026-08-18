# `bga` (buildstream-graph-analysis) — Spec Compliance & Quality Review

> **⚠️ Historical snapshot, not current state.** This is the original review that kicked off the multi-round fixing effort tracked in [`docs/backlog/progress-tracker.md`](../backlog/progress-tracker.md) - it accurately describes the tool's state *before that effort began* (CLI completely non-functional, `networkx` undeclared, etc.). None of that is true today: every P0/P1/P2/P3 item below has since been resolved and verified - see the tracker for current status. This file is kept as-is, unedited, as the historical record of what was found and why the tracker's task decomposition looks the way it does.

**Scope:** Review of the implementation in `bga/` against `docs/spec/specification.md` (v9), plus a general correctness/usability/diagnosability pass. Findings below were confirmed by reading the source and by actually running the CLI and test suite, not just by static inspection — every claim has a `file:line` citation.

**Bottom line:** the specification is precise and well-designed, but the implementation currently **cannot run via its own CLI**, and several headline analytical features (resource wait, scheduler wait, cold structural floor, criticality Monte-Carlo, blast radius, the entire M6 structural package) are stub, no-op, or silently wrong code paths. The one test file does not catch any of this, because its assertions check for key *presence*, not correctness, and it never exercises the CLI at all.

---

## Severity Legend

| Level | Meaning |
|---|---|
| **P0** | Tool does not run / is unusable as shipped |
| **P1** | Runs, but produces silently wrong or spec-violating numbers |
| **P2** | Missing structural/spec-mandated pieces (subcommands, packages, gates) |
| **P3** | Polish, performance, documentation |

---

## 1. P0 — The Tool Does Not Run

These block everything else and should be fixed first; nothing downstream can be meaningfully re-tested until they are.

1. **CLI constructor mismatch.** `bga/cli.py:216-222` constructs `BuildEfficiencyAnalyzer(capacity=..., run_replay=..., replay_heuristic=..., run_diagnostics=..., verbose=...)`, but `BuildEfficiencyAnalyzer.__init__` (`bga/analyzer.py:36`) only accepts `run_dir`. **Every invocation of `bga analyze` raises `TypeError` immediately** — confirmed by running it.
2. **`analyze()` signature mismatch.** `cli.py:225` calls `analyzer.analyze(run_dir)`, but the real signature is `analyze(self)` (`bga/analyzer.py:323`) — it takes no argument and nothing in this path ever calls `.load()`/`.load_from_data()` for the CLI-supplied `run_dir`.
3. **Output formatters reference fields that don't exist.** `format_text`/`format_json`/`format_csv` (`bga/cli.py:30-180`) read `result.run_id`, `result.total_duration_us`, `result.critical_path[i].task_key.element_name`. `AnalysisResult`'s real fields are `attribution/occupancy/timeline/floors/signals/utilisation/model/confidence/violations/structural` (`bga/ingest/models.py:224-241`); `TaskKey` has no `element_name` (`bga/ingest/models.py:86`); `signals['critical_path']` is a plain list of UID strings (`bga/graph/edg.py:606`), not task objects.
4. **Undeclared runtime dependency crashes a clean install.** `bga/structural/analyzer.py:38` does `import networkx as nx` inside `build_edg`, but `pyproject.toml:25` declares `dependencies = []`. Structural analysis (M6) is invoked unconditionally on every `.analyze()` call (`bga/analyzer.py:386`), so `pip install -e .` followed by the README's own Quick Start crashes with `ModuleNotFoundError`.

**Net effect:** the CLI, as checked in, cannot successfully analyze a run against the current `BuildEfficiencyAnalyzer`/`AnalysisResult` implementation. It reads as if `cli.py` was written against an older/different API shape that has since diverged. **Fix:** align the CLI → analyzer → result → formatter chain end-to-end, and declare (or remove the dependency on) `networkx`, before anything else is worth re-reviewing.

---

## 2. Spec-Compliance Gaps (P1/P2)

Organized by specification Part. Each item: requirement → current state → what's needed.

### Attribution categories (Part 11, Part 44 promises #3–6)
- **`RESOURCE_WAIT` classifier is dead code.** `classify_resource_wait` (`bga/attribution/blame_chain.py:277-324`) contains a no-op `for res in task.resources: pass` loop and a comment admitting it: *"Simplified: check if resource was at capacity... Full implementation would track exact holders."* It just returns `len(task.resources) > 0`.
- **`SCHEDULER_WAIT` classifier unconditionally returns `False`** (`bga/attribution/blame_chain.py:326-358`, comment: *"Would need more context to determine"*).
- **Neither method is ever called** from `compute_full_attribution`/`compute_task_attribution` — confirmed via grep, zero call sites.
- `RETRY_WAIT`, `IDLE`, `UNTRACKED_HEAD`, `UNTRACKED_TAIL` are hardcoded/always-zero in `_compute_attribution` (`bga/analyzer.py:230-321`, `:312-313`).
- **Consequence:** violates invariant **I4** (Σ attribution == H exactly) any time real elapsed time falls outside the blame-chain-execution / dependency-wait pair, and directly contradicts Part 44 promises 3–6.

### Flattened timeline (Part 12, I10)
- `_build_flattened_timeline` (`bga/attribution/blame_chain.py:581-646`) only emits segments for tasks reachable via the backward blame-chain walk from terminal tasks; per-task attributions computed elsewhere are discarded for reconciliation. `reconcile_attribution` (line 648) sums only from these segments. On graphs with independent branches or multiple terminals, the total will silently undercount H — **no violation or log is raised.**

### Cold structural floor (Part 15, Part 44 #9)
- `T∞,cold` is **hardcoded `None`** always (`bga/analyzer.py:223`, comment: *"Requires historical data (M6)"*). The M6 `analyze_historical_trends` code exists but `historical_runs` is never supplied (`bga/analyzer.py:642` — always `None`). Cold analysis is entirely unreachable, and the CLI has no `--cold`/`--allow-partial-cold` flags at all (spec Part 37.1).

### Capacity lower bound (Part 16)
- `LB` only accounts for a single `PROCESS` resource pool (`bga/analyzer.py:189-199`), with explicit `# TODO: Add DOWNLOAD/UPLOAD work bounds` and `# TODO: Add exclusive serialization bounds`. Spec requires `LB = max(T∞, max_p(W_p/C_p) over all resources, provable exclusive-serialization bounds)`. This is a **correctness violation of the "certified" contract**, not just incompleteness — a certified lower bound that ignores whole resource classes can be wrong, not just weak.

### Criticality probability (Part 26, Part 44 #16)
- `_compute_perturbed_critical_path` (`bga/diagnostics/analyzer.py:577-589`) **ignores the perturbed durations it's given** and returns the unperturbed critical path every sample (comment: *"Simplified implementation... Full implementation would re-run DAG longest path algorithm"*). Every element's `criticality_probability` collapses to a deterministic 0.0 or 1.0 instead of a genuine sampled distribution — this is not Monte Carlo at all.

### Rebuild blast radius (Part 25)
- Weighted duration is `downstream_count × avg_duration` (a fake average over *all* elements), not a real downstream-subgraph traversal (`bga/diagnostics/analyzer.py:474-479`, comment admits the simplification).

### Leaf / deferrability analysis (Part 24)
- `is_required_by_target` is **hardcoded `True`** for every element (`bga/diagnostics/analyzer.py:490-491`, comment: *"Assume all are required unless proven otherwise"*), and `compute_leaf_analysis` force-adds every element to `reachable_from_targets` (lines 648-653). The deferrability signal, as implemented, **can never flag anything as deferrable** — it's structurally incapable of doing the one thing it exists for.

### M6 Structural analysis (`bga/structural/analyzer.py`)
- `build_edg` adds `Element` dataclass objects as networkx nodes while edges use string UIDs from a different construction path (`bga/structural/analyzer.py:44-49`) — this silently creates duplicate/disconnected nodes. **Confirmed empirically:** a 3-element graph reports `num_elements: 6`.
- `_compute_critical_path_nodes` calls `self.edg.compute_critical_path(...)`, a method that doesn't exist on `ElementDependencyGraph` in this module (`bga/structural/analyzer.py:475-482`) — always raises `AttributeError`, caught by a **bare `except Exception: return []`**. Result: `critical_path_length`/`max_depth` are always 0 and `compute_sensitivity` treats every element as non-critical. **Confirmed:** a genuine 3-node linear chain reports `max_depth: 0`.

### Determinism (Part 35, I11)
- No determinism-harness module exists anywhere (spec explicitly calls for an N≥100-repetition run comparing canonical serialized output). No `bga/validation/` package as recommended in Part 39.

### Reconciliation & confidence gates (Part 33)
- `_compute_confidence` (`bga/analyzer.py:397-416`) only checks ordering violations and reduces confidence to a crude binary 1.0/0.5. `critical_path_coverage`, `dominator_coverage`, `blame_chain_coverage`, `task_coverage`, `duration_coverage` — all spec-mandated hard/soft gates — are **never computed or enforced**.

### CLI surface (Part 37)
- Only `bga analyze` exists. Spec's recommended `graph`, `floors`, `replay`, `sweep`, `utilisation`, `diagnostics` subcommands, and the cold-analysis flags, are entirely absent.

### Architecture (Part 39)
- No `bga/floors/`, `bga/report/`, or `bga/validation/` packages exist as the spec recommends — floors logic is inlined in `analyzer.py`, report formatting inlined in `cli.py`. This isn't just a style gap: it makes the invariant/report contracts much harder to unit-test in isolation (see §5 below).

### Performance (Part 41 — "avoid O(N²) for routine diagnostics")
- Several graph algorithms are **O(N·E) instead of the mandated O(N+E)**: `compute_unweighted_depth`, `compute_weighted_depth`, `compute_dominators` all re-scan `graph.dependencies` inside topological-sort loops instead of using precomputed adjacency lists (`bga/graph/edg.py:96-98, 150-152, 360-362`).
- `BlameChainAnalyzer._build_dependency_graph` is **O(N²)** — a nested loop matching finish times across all task pairs, run on every analysis (`bga/attribution/blame_chain.py:187-206`).
- `explicit_predecessors` construction in `_compute_attribution` is **O(tasks²)** and additionally **assumes one task per element** (`bga/analyzer.py:262-280`, comment: *"Simplified: assume one task per element for now"*) — this will silently mis-map dependencies for elements with multiple task kinds/attempts (TRACK/PULL/FETCH/BUILD/PUSH, retries), which directly contradicts the spec's task-key model (`element_uid|task_kind|phase|attempt`, Part 5.2).

### Terminology (Part 43, worth a quick pass)
- Spot-check CLI/report output strings against the spec's explicit "avoid" list ("interval eclipsing", "mathematically optimal schedule", "cold floor as certified bound", "resource blocker as causal predecessor") — not deeply audited here, but easy to check once output is actually reachable (post-P0 fix).

---

## 3. "Just Works" Fixes — Independent of Spec Nuance

These matter even setting the spec aside; they're basic robustness gaps.

- **Cycle detection is entirely absent.** `docs/guides/cli.md:126-131` documents exit code 3 for "graph cycles detected," but no code checks for cycles. Kahn's-algorithm-based depth computation silently defaults unreached (i.e. cyclic) nodes to depth 0 instead of erroring (`bga/graph/edg.py:108-112`).
- **Exit codes are not differentiated.** A single broad `except Exception` in the CLI (`bga/cli.py:246-252`) maps every runtime failure — ingestion or analysis — to the same exit code. Exit code 3 is never produced anywhere, despite being documented.
- **Malformed JSON is unhandled.** `json.JSONDecodeError` isn't caught anywhere in the loader; it propagates as a raw, unfriendly traceback (or a bare one-liner without `--verbose`).
- **`--verbose` doesn't do what it's documented to do.** No logging module is wired up anywhere; `verbose` only toggles whether `cmd_analyze` prints a full traceback vs. one line on failure. `BuildEfficiencyAnalyzer` doesn't even accept a `verbose` kwarg — same root cause as the P0 constructor bug.
- **Retry/rebuild detection is unimplemented.** `retry_tasks=set()`, `rebuild_tasks=set()` are hardcoded (`bga/analyzer.py:472-473`, comments: *"Would need retry/rebuild detection"*), so the `WASTED_RETRY`/`WASTED_REBUILD` utilization buckets can never be populated — utilization numbers are structurally incomplete even before considering spec nuance.

---

## 4. Test Coverage Plan

### Current state
- **One file**, `tests/test_e2e.py`: 7 hand-rolled test functions, all against a single synthetic 3-node linear-chain fixture.
- Assertions check **key presence, not values** — this is precisely why they missed `num_elements: 6` and `max_depth: 0` on a 3-node chain.
- **Zero CLI coverage** — none of the 7 tests invoke `bga.cli`, which is why the P0 constructor/API breakage was never caught.
- The suite **does not run out of the box**: `networkx` is an undeclared dependency (§1.4) and `pytest` itself isn't installed via the package's own `dev` extras in a clean environment.
- No unit tests exist for any module in isolation (normalize, occupancy, graph, attribution, replay, utilisation, diagnostics) — only the one full-pipeline path, on one trivial fixture.

### Recommended layers

| Layer | Purpose | Notes |
|---|---|---|
| **Unit tests per module** (`tests/unit/test_normalize.py`, `test_occupancy.py`, `test_edg.py`, `test_blame_chain.py`, `test_replay.py`, `test_utilisation.py`, `test_diagnostics.py`) | Fast, hermetic, pure-function coverage | No filesystem/network; pytest + `parametrize` |
| **Shared synthetic topology fixtures** (`tests/fixtures/topologies.py`) | Build once, reuse everywhere | linear chain, diamond, fan-in, fan-out, multiple-equal-predecessors, deep-unequal-predecessors, independent branches, terminal tasks, requested vs. non-requested targets |
| **Value-asserting structural tests** | Catch exactly the M6 bugs found here | Replace "key exists" with exact expected values, e.g. `max_depth == 2` for a 3-node chain |
| **Timestamp/ordering tests** | Part 3.3/3.4 | Quantization determinism; negative-gap-absorbed-by-quantization vs. genuine ordering violation; start-clamp preserves finish |
| **Tie-break tests** | Part 7.1/35 | Simultaneous predecessor finishes → assert exact winner by (finish desc, depth desc, key asc); regression test that adding an unrelated graph node doesn't change the result |
| **Resource-holder tests** | Part 8 | Single holder, multiple simultaneous holders (time-weighted split), holder change mid-wait, no identifiable holder → `UNKNOWN`/`ambiguous=true`. **Note:** currently untestable meaningfully since the classifier is dead code — write these *after* the fix, and include an integration/call-count assertion so it can't silently regress back to dead code |
| **Phase overlap tests** | Part 10 | Phase tag must never change underlying causal category, across execution/dependency-wait/resource-wait/idle |
| **Occupancy edge cases** | Part 4/36.7 | Zero-duration tasks, adjacent/nested intervals, gaps, head/tail |
| **Attribution identity tests** | Invariant I4 | Exact integer equality Σ attribution == H, both task-horizon and full-wall-clock variants, across every topology fixture — **this is the invariant most at risk today** |
| **CPU reconciliation tests** | Invariant I9 | Exact match, within-2%, exceeds-2%, missing-accounting cases |
| **Cold-floor tests** | Part 15.3/36.10 | No history→unavailable; cache-key match→used; partial coverage→unavailable by default; `--allow-partial-cold`→`partial=true, confidence=low`. Requires cold-floor wiring to exist first |
| **Criticality Monte-Carlo tests** | Part 26/36 | Seed determinism (same seed → same probabilities); bounds `0<=P<=1`; and — since perturbation is currently a no-op — a test that perturbed durations actually *change* the sampled critical path for at least one sample, to prevent regressing to the current fake implementation |
| **Determinism harness** | Part 35/I11 | Run the same analysis N≥100 times, diff canonical serialized output — currently entirely absent |
| **CLI/integration tests** (`tests/test_cli.py`) | **Highest leverage — would have caught the P0 breakage immediately** | Invoke `bga analyze` via subprocess or `cli.main(argv=[...])` against fixture run dirs; assert exit codes (0/1/2/3) and output shape for `--format text\|json\|csv` |
| **Golden/regression tests** | Catch integration regressions unit tests miss | One or two realistic full traces in `tests/fixtures/golden/` with expected `analysis/v9`-shaped output snapshots, run through the full pipeline |

### Efficiency/approach
1. Build the shared topology fixture library first — it's reused by nearly every other layer.
2. Prefer `pytest.mark.parametrize` over duplicated near-identical test functions.
3. Keep the unit layer hermetic and fast; gate golden/determinism/Monte-Carlo tests behind a `@pytest.mark.slow` marker so day-to-day CI stays quick.
4. Add `pytest`, `pytest-cov`, and `networkx` to installable dev/runtime dependencies so `make test-e2e` / `pytest` actually work from a clean checkout — right now they don't.
5. Write the CLI integration test layer *early* — it's cheap to write and has already proven to be the single test category most likely to catch systemic breakage.

---

## 5. Usability

- **The CLI doesn't work at all (P0)** — by definition the top usability issue; nothing else matters until this is fixed.
- **Missing subcommands.** Spec Part 37 recommends `graph`, `floors`, `replay`, `sweep`, `utilisation`, `diagnostics` as separate subcommands; currently everything is crammed into `analyze` plus flags. Worth explicitly deciding (and documenting) whether to implement the full subcommand split or treat `analyze` + flags as an intentional, documented deviation — this is a product decision, not a pure bug, so it's worth confirming rather than assuming either way.
- **Cold analysis is unreachable from the CLI** — no `--cold`/`--allow-partial-cold` flags exist, even though cold-floor analysis is one of the spec's headline features.
- **Error messages need to be actionable, not tracebacks.** Replace the single broad `except Exception` with typed exceptions mapped to short, human-readable messages by default; `--verbose` reveals the full traceback. Ties directly into §6 below.
- **Fail fast on bad flag combinations.** Validate `--format`/`--output` up front rather than partway through a (currently broken) analysis run.
- **Consider `bga validate RUN`** (or `--validate-only`): run ingestion + hard/soft gate checks only, report pass/fail — a natural, cheap addition given Part 33's gate structure, useful for quickly sanity-checking a trace before committing to a full analysis run.
- **Consider `--strict` mode:** turn soft-gate warnings into hard failures, useful for CI gating vs. the default best-effort/advisory reporting posture.
- **Progress feedback for large traces**, once performance work (§2, Part 41 items) lands — the spec explicitly anticipates large-N graphs.

---

## 6. Error Handling & Logging for Fast Diagnostics

- **Introduce a small custom exception hierarchy**: `BgaError` (base), `IngestionError`, `NormalizationError`, `AnalysisError`, `ValidationError`. Map exception type → documented exit code (1 = bad args/missing files, 2 = ingestion failure, 3 = analysis failure e.g. cycles) in the CLI, replacing today's one-size-fits-all catch — this closes the gap between `docs/guides/cli.md`'s promised contract and reality.
- **Add cycle detection as a first-class `AnalysisError`**, reporting the offending cycle's node list in the message, replacing the silent depth-0 fallback.
- **Wire up Python's `logging` module — currently entirely absent** (zero `import logging` anywhere in the repo). Recommended shape:
  - Module-level logger per package: `ingest`, `normalize`, `occupancy`, `graph`, `attribution`, `replay`, `utilisation`, `diagnostics`, `structural`.
  - `--verbose`/`-v` → `logging.DEBUG`; default → `WARNING`; add `--quiet` → `ERROR`.
  - Log at minimum: ingestion summary (counts loaded per entity type), normalization results (violations found, clamps applied and where), which hard/soft gates passed/failed and why, and — critically — when a classifier or code path that should fire doesn't (this would have surfaced the resource/scheduler-wait classifiers never being called, and the structural bare-except swallowing an `AttributeError`, as *log lines during development*, not just as bugs found by manual review).
  - Replace `bga/structural/analyzer.py:481-482`'s bare `except Exception: return []` with a logged warning plus a corresponding `violations`/`confidence` entry — never silently zero a result.
- **Surface reconciliation failures as structured output, not just logs.** Σattribution != H, CPU buckets not reconciling within 2%, coverage gates failing — the spec already has `violations`/`confidence` fields designed for exactly this (Part 33/44); today most gates simply aren't populated into them.
- **Add `--log-file`** to persist logs separately from the report body — useful for CI post-mortems on why a specific run's numbers look off, without polluting the human-readable report output.

---

## Recommended Fix Order

1. **P0 CLI/API alignment + `networkx` dependency declaration** — nothing else is verifiable until the tool runs.
2. **CLI integration tests** — write these as soon as (1) is fixed, so the fix is locked in and can't silently regress.
3. **Attribution completeness** (resource wait, scheduler wait, flattened-timeline coverage) — this is the invariant (I4) most at risk and most central to the tool's stated purpose.
4. **Custom exceptions + logging** — makes every subsequent fix faster to verify and debug.
5. **M6 structural analysis correctness** (graph construction, critical path) — currently silently wrong, not just incomplete.
6. **Cold floor wiring, LB completeness, criticality Monte-Carlo, blast radius, deferrability** — real analytical fixes, each independently testable once fixture infrastructure (§4) exists.
7. **Missing CLI subcommands, cold flags, performance work, remaining spec-structure gaps (Parts 37/39/41)** — breadth-of-compliance work once correctness is solid.
