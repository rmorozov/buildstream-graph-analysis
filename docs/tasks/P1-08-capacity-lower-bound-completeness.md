# P1-08: Capacity lower bound only accounts for PROCESS pool

**Priority:** P1 | **Status:** 🔴 Not Started | **Depends on:** none

## Spec Reference
Read only: `sed -n '976,1016p' docs/specification.md` (Part 16 — Capacity Lower Bound, and Part 17 — Certified Headroom).
Key requirement (quoted): `LB = max(T∞,observed, max_p(W_p / C_p), provable exclusive-serialization bounds)` where `W_p` = observed work for resource `p`, `C_p` = available capacity for `p`. "Only observed durations participate."

## Current Broken Behavior
File: `bga/analyzer.py:189-199`.
- Only computes `max_p(W_p/C_p)` for a single hardcoded `PROCESS` resource pool.
- Explicit `# TODO: Add DOWNLOAD/UPLOAD work bounds` and `# TODO: Add exclusive serialization bounds` comments mark the gap.
- This means `LB` is an **under-approximation** whenever `DOWNLOAD`/`UPLOAD` (or other) resources are actually the bottleneck, or when exclusive resources force serialization beyond what the PROCESS-only bound captures — a correctness bug in a value the spec calls "certified," not just a missing feature.

## Required Fix
1. Generalize the `W_p/C_p` computation to iterate over **all** resource types present in the trace/run-context (`PROCESS`, `DOWNLOAD`, `UPLOAD`, `CACHE`, `OTHER` — see Part 31.2, `sed -n '1476,1512p' docs/specification.md`), not just `PROCESS`. `W_p` = sum of observed task durations requiring resource `p`; `C_p` = capacity for `p` from `run_context.resource_capacities`.
2. Add the exclusive-serialization bound: for resources marked `exclusive` (see run-context/graph config, Part 31.3), the lower bound must additionally account for the fact that exclusive-resource tasks cannot overlap at all — sum their durations as a hard serialization floor for that resource.
3. `LB = max(T∞,observed, max over all p of W_p/C_p, exclusive-serialization bounds)`.
4. Keep this strictly based on **observed** durations only — do not let this task's changes pull in any cold/estimated duration.

## Out of Scope
- Don't touch `T∞,observed` computation itself (that's already correct, in `bga/graph/edg.py`).
- Don't touch the replay/capacity-sweep counterfactual model (`bga/replay/scheduler.py`) — that's a separate, explicitly-non-certified model per Part 18-19.

## Acceptance Test
Construct a fixture where `DOWNLOAD` work, not `PROCESS` work, is the actual bottleneck (e.g. few PROCESS-heavy tasks but many large FETCH/PULL tasks sharing a small `DOWNLOAD` capacity). Assert:
1. `LB` reflects the `DOWNLOAD` bound, not just the `PROCESS` bound (i.e. `LB > W_PROCESS/C_PROCESS` in this fixture, and `LB == W_DOWNLOAD/C_DOWNLOAD` or the exclusive-serialization bound if that's larger).
2. `LB <= T_C` (replay makespan) and `H >= LB` still hold (invariants I1/I2) — run the existing invariant checks against this new fixture too.
3. `PYTHONPATH=. python3 tests/test_e2e.py` still passes (no regression on the existing single-PROCESS fixture, where the new general formula should reduce to the same answer as before).

## Verification Log
_(append real command + output here once run, before marking 🟢)_
