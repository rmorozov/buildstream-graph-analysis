# P1-15: Missing `bga/floors/`, `bga/report/`, `bga/validation/` packages

**Priority:** P1 (do last among P1 items) | **Status:** 🟢 Fixed & Verified (2026-08-13) | **Depends on:** most other P1 items (P1-01 through P1-13) — this is a pure refactor and should happen once the logic it's moving is actually correct, not before

## What was done

Done incrementally, one package per commit, exactly as required:

1. **`bga/floors/`** (`observed.py`, `capacity.py`, `serialization.py`, `cold.py`): extracted `T∞,observed`, the capacity lower bound (`P1-08`), the exclusive-serialization bound (`P1-08`), and the cold structural floor (`P1-06`/`P1-07`, `_compute_cold_floor`'s entire body moved verbatim). `bga/analyzer.py::_compute_floors` is now the orchestrator. Computing the non-exclusive and exclusive LB terms as two separate function calls and combining via `max()` is mathematically identical to the original single running-max loop (max is associative/commutative). Replay's `default_caps` now reuses the same `compute_default_capacities` helper the LB computation uses, instead of a separate `getattr(run_context, 'fetchers'/'pushers', 2)` lookup - that was dead code (`RunContext`, a frozen dataclass, has no such fields, so it always evaluated to the literal `2` anyway), so this is the same effective values computed once instead of twice with different-looking (but behaviorally identical) code.
2. **`bga/report/`** (`text.py`, `json.py`, plus a small `_shared.py` for the `SECTIONS`/`GRAPH_SIGNAL_KEYS` constants both formatters need): `format_text`/`format_json`/`format_csv`/`format_sweep_text` moved verbatim out of `bga/cli.py`, which now just imports and calls them.
3. **`bga/validation/invariants.py`**: `_compute_confidence`'s full Part 33 hard/soft-gate and confidence-formula computation (`P1-13`), alongside `determinism.py` (`P1-12`) in the same package. The original method had one side effect - appending hard-gate-failure entries to `self.violations` - which would make a directly-extracted version impure. Redesigned to return `(confidence_dict, new_violations)`, with `bga/analyzer.py::_compute_confidence` (now a thin orchestrator) doing `self.violations.extend(new_violations)` at the call site - preserves the exact same violations list contents in the exact same order while keeping the extracted function a genuine pure function of its inputs.

Not attempted: the spec's much more granular Part 39 architecture for packages *other* than the three this task named (e.g. splitting `bga/graph/edg.py` into `reachability.py`/`depth.py`/`dominators.py`/`critical_path.py`/`slack.py`/`criticality.py`, or `bga/attribution/blame_chain.py` into 6 files) - out of this task's stated scope (`bga/floors/`, `bga/report/`, `bga/validation/` only, per its own Current State section).

## Verification Log

```text
# After EACH of the 3 extraction steps: full suite + byte-identical CLI
# output diff (via `git stash push -u` to capture the pre-extraction
# baseline, then `git stash pop` and re-run for comparison).

$ PYTHONPATH=. python3 -m pytest tests/ -q   # after every step
100 passed

$ PYTHONPATH=. python3 tests/test_e2e.py   # after every step
Results: 7 passed, 0 failed

# Step 1 (bga/floors/): diffed `analyze --format json`, `analyze` text,
# `floors --format json`, `floors --cold --history-dir <hist>
# --format json`, and `replay --format json` - all IDENTICAL.
# Step 2 (bga/report/): diffed `analyze --format json`, `analyze` text,
# `analyze --format csv`, `graph --format json`, and `sweep` text -
# all IDENTICAL.
# Step 3 (bga/validation/): diffed `analyze --format json` (including
# the violations array) and `analyze` text - IDENTICAL.

$ make check-clean
OK: no ignored files are tracked
```

## Spec Reference

Read only: `sed -n '2261,2331p' docs/spec/specification.md` (Part 39 — Implementation Architecture) for the recommended package layout.

## Current State

- Floors logic (`T∞,observed`, LB, certified headroom, cold floor) lives inline in `bga/analyzer.py` instead of a dedicated `bga/floors/` package (`observed.py`, `capacity.py`, `serialization.py`, `cold.py`).
- Report formatting lives inline in `bga/cli.py` instead of `bga/report/` (`text.py`, `json.py`).
- `bga/validation/` (partially created by `P1-12` for the determinism harness) doesn't yet hold the invariant-checking logic that's currently scattered in `bga/analyzer.py::_compute_confidence`.

## Required Fix

**This is a pure refactor — behavior must not change.** Before starting, confirm every fix in `P1-01` through `P1-13` that touches these areas is done and verified (check the tracker), so you're moving correct code, not baking in bugs at a new location.

1. Extract floors computation from `bga/analyzer.py` into `bga/floors/observed.py` (T∞,observed), `bga/floors/capacity.py` (LB), `bga/floors/serialization.py` (exclusive-serialization bounds, from `P1-08`), `bga/floors/cold.py` (from `P1-06`/`P1-07`). Keep `bga/analyzer.py` as the orchestrator that calls into these, per the existing pattern already used for `bga/graph/`, `bga/attribution/`, etc.
2. Extract `format_text`/`format_json`/`format_csv` from `bga/cli.py` into `bga/report/text.py`/`bga/report/json.py`; `cli.py` should just call into these.
3. Extract invariant-checking logic (hard/soft gates from `P1-13`) into `bga/validation/invariants.py`, alongside the `determinism.py` module from `P1-12`.
4. After each extraction step, re-run the full test suite before moving to the next — do this incrementally, one package at a time, one commit per package, not as one giant commit.

## Out of Scope

- Do not change any computed value or output format as part of this refactor. If you find a bug while moving code, log it as a new tracker row and fix it in a separate follow-up commit/task — don't mix refactor and behavior change in the same commit.

## Acceptance Test

After each extraction step: `PYTHONPATH=. python3 tests/test_e2e.py` (and the CLI fixture from `docs/contributing/fixing-guide.md` §7) must produce **byte-identical output** to before the refactor. Diff the full CLI text/JSON output before and after each step to confirm.

## Verification Log

_(append real command + output here once run, before marking 🟢)_
