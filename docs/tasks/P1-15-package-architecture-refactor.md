# P1-15: Missing `bga/floors/`, `bga/report/`, `bga/validation/` packages

**Priority:** P1 (do last among P1 items) | **Status:** 🔴 Not Started | **Depends on:** most other P1 items (P1-01 through P1-13) — this is a pure refactor and should happen once the logic it's moving is actually correct, not before

## Spec Reference
Read only: `sed -n '2261,2331p' docs/specification.md` (Part 39 — Implementation Architecture) for the recommended package layout.

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
After each extraction step: `PYTHONPATH=. python3 tests/test_e2e.py` (and the CLI fixture from `docs/fixing-guide.md` §7) must produce **byte-identical output** to before the refactor. Diff the full CLI text/JSON output before and after each step to confirm.

## Verification Log
_(append real command + output here once run, before marking 🟢)_
