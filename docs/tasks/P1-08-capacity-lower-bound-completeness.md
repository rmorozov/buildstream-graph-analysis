# P1-08: Capacity lower bound only accounts for PROCESS pool

**Priority:** P1 | **Status:** 🟢 Fixed & Verified (2026-08-13) | **Depends on:** none

## What was fixed
- `bga/analyzer.py::_compute_floors` now sums observed work (`W_p`) per resource over every resource actually used by any task (not just a hardcoded `PROCESS`), and takes `LB = max(T∞,observed, max_p(W_p/C_p), exclusive-serialization bounds)`.
- Added `exclusive_resources: List[str]` to `RunContext` (Part 31.3), wired through `bga/ingest/loader.py::load_run_context`. For any resource named there, the bound is the full summed work (`W_p`, not `W_p/C_p`) - exclusive resources can't overlap at all regardless of declared capacity.
- **Newly-found, previously-latent bug fixed alongside this**: `bga/replay/scheduler.py::ReplayScheduler._get_task_resources` was hardcoded to always return `{'PROCESS': 1}` regardless of a task's actual resources. This was invisible before, because LB's own PROCESS-only under-approximation could never exceed T_C's (also PROCESS-only) makespan. Once LB correctly reflects a real DOWNLOAD/UPLOAD/CACHE bottleneck, it can exceed T_C's stubbed schedule, violating I2 (`LB <= T_C`) - confirmed empirically before the fix (`LB=400000 > T_C=150000` on the DOWNLOAD-bottleneck fixture below). Fixed `_get_task_resources` to derive requirements from the task's own `resources` (falling back to `primary_resource`, then `PROCESS` only if a task declares no resources at all). This changes only the resource-requirement *lookup*, not replay's scheduling algorithm/heuristics/tie-breaks - judged in-scope as necessary to keep I1/I2 true, since leaving it broken would mean this task's own fix produced an invariant-violating result.

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
```
$ PYTHONPATH=. python3 -m pytest tests/unit/test_capacity_lower_bound.py -v
3 passed
# test_lb_reflects_download_bottleneck_not_just_process: LB=400000 (DOWNLOAD
#   bound), not the PROCESS-only 12500; H=450000>=LB; LB<=T_C=400000 (I1/I2)
# test_exclusive_resource_forces_full_serialization_floor: LB=200000 (full
#   serialization), not 100000 (naive work_us//capacity)
# test_single_process_fixture_unchanged: LB=100000, matches old formula exactly

# Before the replay/_get_task_resources fix, on the DOWNLOAD-bottleneck
# fixture:
#   lb: 400000  t_c: 150000  LB <= T_C: False   <- I2 violated
# After:
#   lb: 400000  t_c: 400000  LB <= T_C: True

$ PYTHONPATH=. python3 -m pytest tests/ -q
67 passed

$ PYTHONPATH=. python3 tests/test_e2e.py
Results: 7 passed, 0 failed
```
