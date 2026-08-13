# P1-11: Leaf/deferrability fix claimed done — needs independent re-verification

**Priority:** P1 | **Status:** 🟡 Unverified (previously marked 🟢 by a prior session; code inspection on 2026-08-13 looks plausible but was not exercised against a real test) | **Depends on:** none

## Spec Reference
Read only: `sed -n '1201,1265p' docs/specification.md` (Part 24 — Leaf and Deferrability Analysis).
Key requirements:
- Required work computed via `reachable_from_any_requested_target` (**reverse** reachability), not `is_required_target` alone.
- `Deferrable = not reachable_from_any_requested_target`.
- Leaf criticality = leaf AND (on blame chain or critical path) AND not reachable from requested targets.
- "No automatic recommendation is made when the leaf is required by the requested target."

## Current State (what a prior session changed, unverified)
File: `bga/diagnostics/analyzer.py`.
- Line 475/728: `reachable_from_targets = set(self.graph_analysis.get('reachable_from_targets', []))` — pulls this from `graph_analysis` instead of the old hardcoded-True approach. **This is only correct if `graph_analysis['reachable_from_targets']` is itself populated correctly upstream** — that upstream computation was not independently checked as part of this review.
- Line 504: `is_required = elem_uid in reachable_from_targets or not reachable_from_targets` — note the `or not reachable_from_targets` clause: if the set is ever empty (e.g. because upstream computation silently returns nothing rather than raising), this **falls back to "everything is required"**, silently reproducing the old bug's effect. This fallback needs scrutiny — is it a deliberate "no targets specified" case (legitimate, per spec: no requested targets means everything is reachable) or could it mask an upstream failure?
- Line 731-732: `if not requested_targets: reachable_from_targets = set(downstream_counts.keys())` — this looks like the deliberate "no targets specified → everything reachable" case, which is legitimate per spec. Confirm the line-504 fallback isn't independently triggering the same effect for a different (buggy) reason.

## Required Fix (verification-first task)
1. Trace where `graph_analysis['reachable_from_targets']` is actually populated (likely in `bga/graph/edg.py::analyze_graph` or similar) and confirm it does a **real reverse-reachability computation** from `requested_target` elements, not another hardcoded/always-full fallback.
2. Write the acceptance test below. If it passes cleanly, update this task's status to 🟢 with the verification log and you're done — no code change needed beyond confirming.
3. If it fails, fix the actual upstream computation (likely in `bga/graph/edg.py`) so reverse reachability is genuine, then re-run the test.

## Out of Scope
- Don't touch blast radius (`P1-10`) or criticality (`P1-09`) even though they're nearby.

## Acceptance Test
Build a fixture with: one `requested_target` element, and a second, unrelated leaf element that is **not** reachable from the requested target (a genuinely deferrable element) plus a third leaf element that **is** reachable from the requested target (should never be flagged deferrable). Assert:
1. The unrelated leaf → `is_required_by_target == False`, appears in deferrable-leaves output.
2. The reachable leaf → `is_required_by_target == True`, does **not** appear in deferrable-leaves output, matching the spec quote "no automatic recommendation is made when the leaf is required by the requested target."

Run: whichever test file houses this, plus `PYTHONPATH=. python3 tests/test_e2e.py`.

## Verification Log
_(append real command + output here once run — this task's whole purpose is to produce this evidence)_
