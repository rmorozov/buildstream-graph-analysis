# UX-25: `critical_path_coverage`/`dominator_coverage` hard-gate failures report a bare ratio, no diagnostic detail

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — (independent)

## Motivation

Found during a real hands-on walkthrough of the current CLI against a fresh real capture of `examples/05-cmake-cpp-toolchain` (`bst --builders 4 build all.bst`, extracted via `tools/bst_run_wrapped.py` + `tools/bst_extract_run.py`, analyzed via `bga analyze`) - not hypothetical. Real output included:

```
Confidence:
  Overall: 0.73 (medium)
  Failed Hard Gates: critical_path_coverage_full

Violations (1):
  - hard gate failed: critical_path_coverage = 0.8
```

Checked against `bga/validation/invariants.py:144-148`: the violation entry is literally `{'type': 'hard_gate_failed', 'gate': 'critical_path_coverage', 'value': critical_path_coverage}` - a bare ratio, no indication of *which* critical-path element has no matching task, or *why*. The same real report's own critical-path ranking, a few lines earlier in the exact same output, already had the answer: `3. all.bst (100% probability of being on critical path) [structural: stack, may not reflect real compute work]` - `all.bst` is a `kind: stack` element with no build/fetch task of its own (5 elements on the real critical path, 4/5 = 0.8, matching exactly). **The tool already computes and displays the fact that explains this violation, in a different section of the same report - it just never connects the two.** A user seeing only the Violations line has no way to know this without manually cross-referencing the critical-path list themselves and recognizing the stack-element caveat as the explanation.

`dominator_coverage` (`bga/validation/invariants.py:132`, same file) is checked via a structurally identical gate and almost certainly has the same gap - not separately reproduced here, but worth checking when this is picked up.

## Required Fix

Real, scoped: attach a `detail` field to each `hard_gate_failed` violation naming the specific element(s) responsible and, where already known (e.g. `element_kind`'s existing `stack` heuristic from `P4-12`), the real reason - not a generic re-statement of the ratio. For `critical_path_coverage`, this means identifying which `critical_path` UIDs are missing from `elements_with_tasks` (`bga/validation/invariants.py:78`, already computed - just not surfaced) and, for each, checking whether it's a `kind: stack`/similar structural element (already known elsewhere in the codebase, per `P4-12`'s `element_kind` heuristics) versus a genuine coverage gap worth investigating.

## Out of Scope

- Changing the hard-gate pass/fail threshold or semantics themselves - this is a reporting-detail fix only, not a behavior change.
- Reproducing/confirming the `dominator_coverage` case with real evidence - flagged as likely-same-shape but not independently verified in this filing.

## Acceptance Test

1. A real run reproducing this doc's own `all.bst`/`critical_path_coverage=0.8` case reports a `hard_gate_failed` violation whose detail names `all.bst` and its structural-stack reason, without the user needing to cross-reference the critical-path list manually.
2. A real run with a genuine (non-structural) coverage gap still reports something useful (at minimum, the specific missing element UID(s)), not silently suppressed just because it isn't the stack case.
3. Full suite green.

## Verification Log

Filed 2026-08-16, from a real `bga analyze` run against a freshly captured `examples/05-cmake-cpp-toolchain` build (`--builders 4 build all.bst`) - not implemented.
