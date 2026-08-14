# P1-28: Monte-Carlo criticality rebuilt graph topology on every sample instead of once

**Priority:** P1 (spec-text deviation; not asymptotically wrong, so lower urgency than P1-27, but still a direct violation of an explicit spec instruction) | **Status:** 🟢 Fixed & Verified (2026-08-13) | **Depends on:** none

## Spec Reference
Part 41.2: Monte-Carlo criticality (200 samples) "should reuse the graph topology and avoid rebuilding graph structures. Only durations and dynamic programming values vary."

## How this was found
Same independent re-audit that found `P1-27`. Confirmed by reading `bga/diagnostics/analyzer.py::_compute_perturbed_critical_path` (called once per sample) and finding `build_element_graph(self.graph)`/`compute_in_out_degree(self.graph)` called fresh inside it, not hoisted above the sampling loop.

## Current Broken Behavior (before this fix)
`DiagnosticsAnalyzer.compute_criticality_probability` calls `_compute_perturbed_critical_path` once per Monte-Carlo sample (default `DEFAULT_MC_SAMPLES = 200`). That function rebuilt `predecessors`/`successors` (`build_element_graph`) and `in_degree` (`compute_in_out_degree`) from `self.graph` on every single call - identical work 200 times over, since only the perturbed `elem_durations` actually differs per sample, not the graph's static topology. Each rebuild is still `O(N+E)` (not asymptotically quadratic, so this doesn't breach Part 41's big-O ceiling), but it's a direct, literal deviation from Part 41.2's explicit instruction and wastes ~200x the necessary graph-construction work on every `--diagnostics` run.

## What was fixed
Hoisted `build_element_graph`/`compute_in_out_degree` out of `_compute_perturbed_critical_path` and into `compute_criticality_probability`, computed once before the sampling loop and passed in as parameters. `_compute_perturbed_critical_path`'s signature now takes `predecessors`/`successors`/`in_degree` explicitly instead of deriving them from `self.graph` itself. Verified the topology dicts are never mutated across samples (the per-sample `temp_in_degree = dict(in_degree)` inside the function already makes its own working copy), so sharing them across all 200 calls is safe.

## Out of Scope
- Did not change the Monte-Carlo sampling logic itself (duration perturbation, seeded RNG, per-sample longest-path computation) - already verified correct and genuinely-resampling by `P1-09`/`P3-07`. This is purely a redundant-work elimination.

## Acceptance Test
`PYTHONPATH=. python3 -m pytest tests/unit/test_criticality_probability.py -v` - new call-count regression test asserts `build_element_graph`/`compute_in_out_degree` are each called exactly once per `analyze()` run (not once per sample), and every existing criticality-probability value stays identical (pure refactor, no behavior change).

## Verification Log
```
$ PYTHONPATH=. python3 -m pytest tests/unit/test_criticality_probability.py -v
5 passed
# test_graph_topology_built_once_not_per_sample: monkeypatched
# build_element_graph/compute_in_out_degree, confirmed each called
# exactly 1 time (not num_samples=200) across a full analyze() run
# with run_diagnostics=True.

$ PYTHONPATH=. python3 -m pytest tests/ -q
241 passed   # cumulative with P1-27/P1-29's regression tests

$ PYTHONPATH=. python3 tests/test_e2e.py
Results: 7 passed, 0 failed

$ make check-clean
OK: no ignored files are tracked
```
