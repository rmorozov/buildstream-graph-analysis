# P1-19: Flattened timeline residual coverage (intra-element + off-chain time)

**Priority:** P1 | **Status:** 🟢 Fixed & Verified (2026-08-13) | **Depends on:** `P1-03` (done)

## Spec Reference
Read only: `sed -n '466,534p' docs/specification.md` (Part 6, esp. 6.2: "It proceeds backward until `wall_start` or until an attribution boundary is reached. The remaining time is represented as a **measured residual** rather than artificially forcing it through the dependency graph.") and `sed -n '788,839p' docs/specification.md` (Part 12, esp. `Σ segment_duration == H` exactly).

## Where this came from
`P1-03` fixed three compounding bugs producing outright garbage attribution values. After those fixes, attribution identity (I4) held exactly for single-task-kind graphs, but on `tests/fixtures/synthetic_multi_subproject/` (multi-task-kind elements, diamond dependency, real resource contention) there was a 5,500,000µs gap out of H=142,000,000µs, exactly matching `libcore.bst`'s own `TRACK`+`FETCH` duration.

## Two fixes — turned out simpler than the original design sketch predicted

The original design sketch (below, kept for reference) assumed this needed two separate pieces of work: (1) intra-element sequencing, straightforward, and (2) off-chain parallel-work coverage, expected to need a full occupancy-sweep-based reconciliation to avoid double-counting overlapping wall-clock time. In practice, **one coherent fix covered both**, because of how `select_dependency_blame`'s tie-break already works:

1. **Intra-element phase predecessor.** New `BlameChainAnalyzer._intra_element_predecessor()` (`bga/attribution/blame_chain.py`) finds, for a task with no intra-element predecessor searched yet, the immediately-preceding same-element task in `TRACK → FETCH/PULL → BUILD → PUSH` order (a new `_PHASE_ORDER` mapping). `build_blame_chain` now adds this candidate to the predecessor pool alongside `explicit_predecessors`, with `ready_time = max(inter-element ready_us, intra-element predecessor's finish_us)`.
2. **`explicit_predecessors` extended to every task kind, not just `BUILD`.** `bga/analyzer.py::_compute_attribution` previously only mapped dependency edges onto the successor element's `BUILD` task. Extended so *every* task of the downstream element gets an edge to the upstream element's `BUILD` task — matching `bga/normalize/timestamps.py::compute_ready_times`, which already (correctly) gates every task kind of a dependent element on its predecessors' finish, not just `BUILD`. Without this, a `TRACK`/`FETCH` task's real cross-element wait had no predecessor entry for the walk to continue into.

**Why this also solved "off-chain parallel work" without an occupancy sweep:** `select_dependency_blame`'s tie-break already picks whichever predecessor candidate has the *latest* finish time — the true bottleneck. With the predecessor pool now complete (inter-element, every task kind, plus intra-element phase order), the walk at every step follows the objectively slowest path back through the graph. That is, by construction, the graph's actual (weighted) critical path — and a connected graph's critical path spans exactly `[min_start, max_finish)` of everything reachable from it, because nothing on that critical path can start before the path's own earliest predecessor finishes, and nothing off the critical path (by definition of "critical") extends past what the critical path already accounts for in time. So "off-chain but transitively connected" work turned out not to need separate coverage at all — it's implicitly bounded by (nested within, or feeding into) the critical path's own span.

**What this does *not* solve** (confirmed empirically, not assumed): genuinely **disconnected** components — two elements with no dependency relationship to each other at all, each an independent "terminal" — are a different situation, since `compute_full_attribution` only walks from the single task with the overall maximum finish time (`P1-03`'s fix for the old broken multi-terminal heuristic). If an independent second component starts and finishes at times not nested within the first terminal's own span, its entire execution is dropped. This is confirmed as **`P1-04`'s distinct, still-open scope** — see `tests/unit/test_multi_terminal_coverage.py`, added as a permanent regression/documentation test for exactly this gap.

## Original design sketch (superseded by the above — kept for context)
<details>
<summary>What I originally thought this would require</summary>

1. Intra-element sequencing: extend `build_blame_chain` to check for an earlier same-element task and continue the walk into it. (This part matched what was actually needed.)
2. Off-chain parallel work: expected to need "an occupancy-sweep-based reconciliation ... that, for any horizon time not covered by the chain, determines from the full task set what best explains that interval." **This turned out to be unnecessary** for the connected-component case — see above for why.
</details>

## Out of Scope (as executed)
- Did not touch `P1-01` (resource-holder tracking) or `P1-02` (scheduler-wait, already done) - orthogonal to which tasks get a flattened-timeline segment.
- Did not attempt disconnected multi-terminal support - that's confirmed as `P1-04`'s scope, now precisely bounded and testable rather than an open question.

## Acceptance Test — as executed
1. `tests/test_synthetic_multi_subproject.py::test_attribution_identity_exact` - `xfail` mark removed, now a plain passing assertion.
2. `tests/test_synthetic_multi_subproject.py::test_attribution_no_longer_produces_garbage_values` and `tests/unit/test_attribution_identity.py` - still pass, no regression.
3. `tests/unit/test_multi_terminal_coverage.py` (new) - documents and locks in exactly what remains open for `P1-04`, so that task now has a concrete, runnable reproduction instead of a design question.
4. Full suite green.

## Verification Log
```
$ python3 -c "... attribution on tests/fixtures/synthetic_multi_subproject ..."
H: 142000000  total: 142000000  gap: 0  exact match: True

$ python3 -c "... attribution on /tmp/bga_test_run (simple 3-task chain) ..."
H: 450000  total: 450000  match: True

$ PYTHONPATH=. python3 -m pytest tests/ -v
38 passed, 0 xfailed
```
