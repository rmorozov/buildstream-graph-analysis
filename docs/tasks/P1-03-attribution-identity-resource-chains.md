# P1-03: Attribution identity (I4) violated on resource-constrained chains

**Priority:** P1 (highest-value open item — this breaks the tool's core promise) | **Status:** 🔴 Not Started (newly discovered 2026-08-13) | **Depends on:** none, but do after `P1-02` if convenient since that may share root cause

## Spec Reference
Read only: `sed -n '840,868p' docs/specification.md` (Part 13 — Task Horizon and Invariant I1) and `sed -n '1720,1780p' docs/specification.md` (Part 34 — Core Invariants, esp. I4: "for the selected horizon, `Σ attribution_duration == H` exactly").

## Current Broken Behavior — reproduce it yourself first
This was found by actually running the CLI, not by reading code. Reproduce with the fixture in `docs/fixing-guide.md` §7 (a 3-task linear chain, single `PROCESS` resource pool, capacity 1):

```
python3 -m bga.cli analyze /tmp/bga_test_run
```

Observed output (2026-08-13): `Total Duration: 0.5s`, `T∞ (observed critical path): 0.45s`, but the Attribution Breakdown is:
```
Execution On Chain Us  0.15s ( 33.3%)
Dependency Wait Us     0.00s (  0.0%)
Resource Wait Us       0.00s (  0.0%)
Scheduler Wait Us      0.00s (  0.0%)
Idle / Retry / Untracked  all 0.00s
```
Only the *first* task's execution (150000µs) is attributed; the chain's other two tasks (also 150000µs execution each, serialized on the same single-capacity `PROCESS` resource, so genuinely dependency/resource-blocked for 300000µs combined) are missing entirely. **Σ attribution = 150000µs, H = 450000µs — a 66% shortfall.** This directly violates invariant I4.

Note this is *different* from the passing `tests/test_e2e.py::test_invariants` case — that fixture's tasks apparently don't attach `resources` the same way, or don't hit whatever code path drops coverage here. Your first job is root-causing why the two scenarios diverge.

## This is worse than "undercounts" — updated evidence from a larger fixture (2026-08-13)

`tests/test_synthetic_multi_subproject.py` (a 9-element, 24-task graph with real `PROCESS`/`DOWNLOAD` contention across `TRACK`/`FETCH`/`BUILD` phases and diamond dependencies — see `tests/fixtures/synthetic_multi_subproject/`) hits the *same* invariant violation, but the failure mode there is not a simple undercount — it's outright nonsensical:

```
attribution.execution_on_chain_us = -7500000       # negative
attribution.dependency_wait_us    = 14292893059500000   # ~453,000 years, in a 142-second build
```

So on more realistic, multi-branch, resource-contended graphs this bug doesn't just drop coverage (as in the simple 3-task case above) — it can produce **negative durations and multi-order-of-magnitude overflow values**. Whatever the root cause turns out to be, verify the fix against *both* fixtures: the simple linear case here (undercount) and `tests/test_synthetic_multi_subproject.py` (negative/overflow) may or may not share a root cause, but a fix that only makes the simple case sum correctly without also fixing the negative/overflow case on the larger fixture is not done. `tests/test_synthetic_multi_subproject.py::test_attribution_identity_holds` is `xfail`-marked pointing at this task — removing that mark and seeing it pass is part of this task's exit bar, in addition to the acceptance test below.

## Required Fix
1. Instrument/trace `compute_full_attribution` and `_build_flattened_timeline` (`bga/attribution/blame_chain.py:581-646`, and the orchestration in `bga/analyzer.py:230-321`) against the reproduction fixture above to find exactly where coverage is dropped. Likely suspects to check (don't assume — verify): the blame-chain backward walk may be stopping after one hop when a resource-wait or scheduler-wait branch is taken; `explicit_predecessors` construction (`bga/analyzer.py:262-280`, flagged separately as `P1-16` for its O(tasks²)/one-task-per-element assumptions) may be mis-mapping predecessors for this fixture's shape.
2. Fix root cause so the flattened timeline / attribution sum covers every task's full duration, not just the first hop of the blame chain.
3. This task and `P1-04` (multi-terminal timeline coverage) are related but distinct: `P1-04` is about graphs with independent branches / multiple terminals; this task is about a single linear chain still under-attributing. Fix this one first — it's the simpler, more fundamental case.

## Out of Scope
- Don't implement the "raise a violation on undercount" reporting behavior — that's `P1-05`. This task is about making the sum correct in the first place.
- Don't rewrite the O(N²)/O(tasks²) algorithms for performance — that's `P1-16`. If you need to touch that code to fix correctness, keep the algorithmic complexity the same and only fix the logic bug, unless the bug *is* the complexity shortcut (verify before assuming).

## Acceptance Test
1. Re-run the exact reproduction fixture: `python3 -m bga.cli analyze /tmp/bga_test_run` — the Attribution Breakdown must sum to `0.45s` (450000µs = H), matching `T∞ (observed critical path)`.
2. Add a permanent regression test (in `tests/test_e2e.py` or a new `tests/unit/test_attribution_identity.py`) that builds this exact 3-task single-resource-pool scenario programmatically and asserts `sum(attribution values) == H` exactly (integer equality, not approximate).
3. Remove the `@pytest.mark.xfail` from `tests/test_synthetic_multi_subproject.py::test_attribution_identity_holds` and confirm it passes: `PYTHONPATH=. python3 -m pytest tests/test_synthetic_multi_subproject.py::test_attribution_identity_holds -v`. This is the larger, multi-branch, resource-contended fixture where the bug shows up as negative/overflowed values, not just an undercount — both fixtures must pass, not just the simpler one.
4. Re-run `PYTHONPATH=. python3 tests/test_e2e.py` and `PYTHONPATH=. python3 -m pytest tests/ -v` — every existing test must still pass (no regression).

## Verification Log
_(append real command + output here once run, before marking 🟢)_
