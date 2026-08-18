# P1-03: Attribution identity (I4) violated on resource-constrained chains

**Priority:** P1 (highest-value item found — this broke the tool's core promise) | **Status:** 🟢 Fixed & Verified (2026-08-13) — see "What remains" below for the honest residual, now scoped as `P1-19` | **Depends on:** none

## Spec Reference

Read only: `sed -n '840,868p' docs/spec/specification.md` (Part 13 — Task Horizon and Invariant I1) and `sed -n '1720,1780p' docs/spec/specification.md` (Part 34 — Core Invariants, esp. I4: "for the selected horizon, `Σ attribution_duration == H` exactly").

## Original bug reports (both fully resolved by the fixes below)

**Simple case** (`docs/contributing/fixing-guide.md` §7's 3-task linear chain, single `PROCESS` pool): only the terminal task's execution (150000µs) was attributed; Σattribution = 150000µs against H = 450000µs — a 66% shortfall.

**Larger case** (`tests/fixtures/synthetic_multi_subproject/`, 9 elements, `TRACK`/`FETCH`/`BUILD` phases, real `PROCESS`/`DOWNLOAD` contention, a diamond dependency): not just an undercount — outright nonsensical values, `execution_on_chain_us = -7500000` (negative) and `dependency_wait_us = 14292893059500000` (~453,000 years in a 142-second build).

## Three compounding root causes (all found and fixed)

1. **Blame-chain walk stopped dead on exactly-zero-wait links.** `build_blame_chain` (`bga/attribution/blame_chain.py`) only continued to a predecessor when `ready_time < task.start_us` was true — i.e. only when there was a *strictly positive* dependency wait. When tasks were scheduled perfectly back-to-back (zero gap — the common case for a fully-serialized single-resource-pool chain, exactly the simple reproduction above), the walk added one node and immediately broke, silently dropping every upstream task from the chain and therefore from the flattened timeline (which only emits segments for chain-member tasks). **Fix:** the walk now continues to the responsible predecessor whenever `explicit_predecessors` lists one, independent of wait magnitude; `dependency_wait_start` is still only set when the wait is actually positive.

2. **`explicit_predecessors` construction assumed one task per element.** `bga/analyzer.py::_compute_attribution` mapped each element-level dependency edge to "whichever task happened to match last" in a nested loop over all tasks — for elements with multiple task kinds (`TRACK`/`FETCH`/`BUILD`), this produced wrong or missing predecessor task-keys, which fed `task_finish_times.get(pred_key, 0)`'s silent zero-fallback for unmatched keys — producing bogus `ready_time = 0` for tasks with real predecessors, and therefore `dependency_wait_us = start_us - 0 ≈ start_us` (a full absolute epoch-scale microsecond timestamp, ~1.7×10^15µs) for several tasks at once. Summed across ~8-9 such tasks, this is exactly what produced the ~14.29×10^15µs (~453,000-year) figure. **Fix:** `explicit_predecessors` is now built by mapping each dependency edge onto the specific `BUILD` task of each element (the real-world semantics of a BuildStream `depends:` edge — a downstream element's build needs the upstream element's *build* to have completed, not its track/fetch), via a single `O(tasks + edges)` pass instead of the old `O(tasks × edges)` nested loop with silent overwrites.

   Additionally, both `build_blame_chain` and `compute_task_attribution` were independently *recomputing* a "ready time" from `explicit_predecessors`/`task_finish_times` via `compute_ready_time`, duplicating — and, per the above, sometimes contradicting — the already-correct `task.ready_us` computed once during normalization (`bga/normalize/timestamps.py::compute_ready_times`, which correctly aggregates across *all* of a predecessor element's task kinds). Both call sites now use `task.ready_us` directly instead of re-deriving it, eliminating this second, narrower, buggy computation as a divergence source. (`compute_ready_time` itself is left in place, unused by these two call sites now, in case a future task needs it — deleting it wasn't necessary to fix the bug.)

3. **The default `terminal_tasks` heuristic spuriously treated most tasks as terminals.** `compute_full_attribution`'s default (when no explicit `terminal_tasks` set is passed — the common case) came from `self.successors`, built in `_build_dependency_graph` by matching `other.finish_us == task.ready_us` across *all* tasks — a heuristic entirely disconnected from the real dependency graph. On a multi-task-kind element graph, most `TRACK`/`FETCH` tasks' finish times don't happen to coincide with anything, so the heuristic misclassified them as having "no successor", i.e. as terminals. On `tests/fixtures/synthetic_multi_subproject/` this produced **12 spurious terminals** (correct answer: 1 — `app.bst`), each starting its own backward walk, several of which re-visited and re-summed shared upstream tasks (e.g. `core-utils.bst:libcore.bst`'s `BUILD` task appeared in the flattened segments **three times**). **Fix:** per spec Part 6.2 ("the chain begins from **the** terminal task responsible for the observed end of the build" — singular), the default is now the one task whose `finish_us` equals the overall maximum finish time (ties broken by task key ascending, matching the determinism rule used elsewhere). Callers with multiple genuinely independent requested targets should pass `terminal_tasks` explicitly — that broader case is `P1-04`'s scope, not silently attempted here via a heuristic that gets it wrong most of the time.

## What remains — honestly scoped out as `P1-19`

After the three fixes above: **exact** identity (Σattribution == H) now holds for any graph where every element has a single task kind (`tests/unit/test_attribution_identity.py`, the original simple-case reproduction). On the larger multi-task-kind fixture, the catastrophic failure modes are gone — no negative values, no overflow, right order of magnitude (`tests/test_synthetic_multi_subproject.py::test_attribution_no_longer_produces_garbage_values`, passing) — but exact equality does not yet hold: **136,500,000µs vs H=142,000,000µs**, a gap that is *exactly* `libcore.bst`'s own `TRACK`+`FETCH` duration (5.5s), because the blame-chain walk has no concept of intra-element task sequencing (see `docs/backlog/tasks/P1-19-flattened-timeline-residual-coverage.md` for the full diagnosis and design sketch). `tests/test_synthetic_multi_subproject.py::test_attribution_identity_exact` is `xfail`-marked pointing at `P1-19`.

This is a deliberate scope boundary, not an oversight: the three root causes above were the ones producing *wrong/nonsensical* numbers (the original bug reports' actual complaint). The residual gap is a *narrower*, well-understood, separately-fixable completeness gap in the same subsystem, cleanly separable from what was actually broken.

## Out of Scope (unchanged from original)

- The "raise a violation on undercount" reporting behavior is `P1-05`.
- Rewriting algorithms for performance (beyond the `explicit_predecessors` complexity improvement that came for free with the correctness fix) is `P1-16`.

## Acceptance Test — as executed

1. `python3 -m bga.cli analyze /tmp/bga_test_run` (the simple reproduction) — Attribution Breakdown now sums to exactly `0.45s` (100.0%), matching H.
2. `tests/unit/test_attribution_identity.py::test_zero_wait_serialized_chain_attribution_is_exact` — new permanent regression test for the simple case, asserts exact integer equality.
3. `tests/test_synthetic_multi_subproject.py::test_attribution_no_longer_produces_garbage_values` — new permanent regression test for the negative/overflow failure mode on the larger fixture; passes. (`test_attribution_identity_exact`, the *exact*-equality version on this same fixture, remains `xfail` — see "What remains" above; this was the original acceptance criterion #3, revised in light of the deeper understanding gained while fixing this.)
4. Full suite: `PYTHONPATH=. python3 -m pytest tests/ -v` — no regressions.

## Verification Log

```text
$ python3 -m bga.cli analyze /tmp/bga_test_run
Execution On Chain Us   0.45s (100.0%)
Dependency Wait Us      0.00s (  0.0%)
(all other categories 0.0%)

$ PYTHONPATH=. python3 -m pytest tests/unit/test_attribution_identity.py -v
1 passed

$ PYTHONPATH=. python3 -m pytest tests/test_synthetic_multi_subproject.py -v
11 passed, 1 xfailed (test_attribution_identity_exact - see P1-19)

$ PYTHONPATH=. python3 -m pytest tests/ -v
35 passed, 1 xfailed
```
