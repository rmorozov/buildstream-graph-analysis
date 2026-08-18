# P1-09: Criticality "Monte Carlo" ignores perturbed durations

**Priority:** P1 | **Status:** 🟢 Fixed & Verified (2026-08-13) | **Depends on:** none

## What was actually found (re-verification corrected the original diagnosis)

`_compute_perturbed_critical_path` was **not** the `return self.critical_path` no-op the original task description found - by the time this task was picked up, it was already a genuine per-sample longest-path recomputation using the perturbed durations (apparently fixed in an earlier, undocumented round - the same "stale diagnosis" pattern that hit `P2-01`/`P2-02` earlier this session). Confirmed by reading the function in full before starting.

The real, live bug was one layer up, in `compute_criticality_probability`'s aggregation: `critical_counts` is populated with **element UIDs** (`_compute_perturbed_critical_path` operates on the element graph, matching `compute_critical_path`'s own return shape), but the final per-task lookup used the full `task_key` string (`critical_counts.get(task_key, 0)`) - a format mismatch that always missed, silently collapsing every `probability` to exactly `0.0` regardless of what the (correct) resampling actually found. The same mismatch made `observed_critical` always `False` too (`self.critical_path` is also a set of element UIDs, but was checked against `task_key in self.critical_path`).

## What was fixed

Both lookups changed to key by `elem_uid` instead of `task_key`. Verified end-to-end on a diamond fixture (`root -> {a, b} -> merge`, `a`/`b` near-equal length at 50000us/49000us) where `a.bst`/`b.bst`'s criticality now genuinely depends on the ±10% perturbation - `probability` values land strictly between 0 and 1 (previously impossible), sum to exactly 1.0 (exactly one of the two is critical per sample), and `observed_critical` now correctly reflects the real unperturbed critical path (`a.bst`, the longer one, `True`; `b.bst` `False`).

## Spec Reference

Read only: `sed -n '1301,1335p' docs/spec/specification.md` (Part 26 — Criticality Probability).
Key requirements: Monte-Carlo, default 200 samples, duration perturbation ±10%; `criticality_probability = P(element appears on longest path)`, computed by actually resampling; deterministic random seed (same input+seed → same probabilities); advisory only.

## Current Broken Behavior

File: `bga/diagnostics/analyzer.py:577-589`, method `_compute_perturbed_critical_path`.

- Comment admits it: `# Simplified implementation - returns original critical path... Full implementation would re-run DAG longest path algorithm`.
- It **ignores the perturbed durations it's given as an argument** and just `return self.critical_path` (the unperturbed one) every single sample.
- Net effect: every element's `criticality_probability` is deterministically `1.0` (if it happens to be on the one true critical path) or `0.0` (otherwise) — not a genuine sampled distribution at all. This is not incomplete, it's a no-op disguised as a feature.

## Required Fix

1. For each of the (default 200) Monte-Carlo samples, actually apply the ±10% perturbation to task durations (check whether perturbation-generation already exists elsewhere in this file/module — reuse it, don't duplicate) and **re-run the DAG longest-path algorithm** (`bga/graph/edg.py::compute_critical_path`, reuse it, don't reimplement) using the perturbed durations for that sample.
2. Record, for each element, whether it appeared on the resulting critical path for that sample.
3. `criticality_probability(element) = (count of samples where element was on critical path) / (total samples)`.
4. Use a **deterministic seed** for the random perturbation generator (e.g. `random.Random(seed)` with a fixed default seed, overridable) so `same input + same seed → same probabilities` (this is testable and required).
5. Performance note (ties into `P1-16`): per Part 41, Monte-Carlo should reuse graph topology and avoid rebuilding graph structures — only durations/DP values should vary per sample. Don't reconstruct the whole graph object 200 times if `compute_critical_path` allows passing in pre-built adjacency structures with only duration values swapped; check its signature before assuming you need to change it.

## Out of Scope

- Don't touch blast-radius computation (`P1-10`) even though it's in the same file and area.
- Don't optimize beyond "reuse the existing critical-path function and existing graph structures" — a full custom incremental DP is not required here, just genuine per-sample recomputation.

## Acceptance Test

1. Build a fixture with at least one element that is *sometimes* critical depending on duration perturbation (e.g. two near-equal-length parallel paths converging on a shared successor) — this is the key test case, since the old code could never produce a probability strictly between 0 and 1.
2. Assert `0 < criticality_probability(that element) < 1` for that element (proves genuine sampling, not the 0/1 collapse).
3. Assert same-seed determinism: run the analysis twice with the same seed → identical probabilities for every element.
4. Assert bounds: `0 <= P(critical) <= 1` for every element, every run.

Run: whichever test file houses this, plus `PYTHONPATH=. python3 tests/test_e2e.py`.

## Verification Log

```text
$ PYTHONPATH=. python3 -m pytest tests/unit/test_criticality_probability.py -v
4 passed
# test_near_tie_element_has_genuine_intermediate_probability:
#   a.bst=0.6, b.bst=0.4 (sums to 1.0) - strictly between 0 and 1
# test_observed_critical_matches_actual_critical_path: a.bst (longer,
#   50000us) observed_critical=True, b.bst (49000us) False
# test_same_seed_is_deterministic: identical results across two runs
# test_probabilities_are_bounded: 0 <= P <= 1 for every element

$ PYTHONPATH=. python3 -m pytest tests/ -q
80 passed

$ PYTHONPATH=. python3 tests/test_e2e.py
Results: 7 passed, 0 failed
```
