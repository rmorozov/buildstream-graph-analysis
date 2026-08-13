# P2-02: Malformed JSON / bad input unhandled

**Priority:** P2 | **Status:** 🔴 Not Started | **Depends on:** none (pairs well with `P2-01`/`P2-03` since all three touch the CLI's error path, but each is independently completable)

## Spec Reference
No spec section — this is a robustness gap, not a spec-compliance one. Reference `docs/cli.md`'s exit-code table for the target behavior (`1` = bad args/missing files, `2` = ingestion failure).

## Current Broken Behavior
- `json.JSONDecodeError` is not caught anywhere in `bga/ingest/loader.py` — a malformed `run-context.json`/`graph.json`/`trace.json` propagates as a raw, unfriendly traceback (or a bare one-liner without `--verbose`, per the current CLI catch-all).
- Missing required fields raise `ValueError` in a few spots (`bga/ingest/models.py:99` `TaskKey.from_string`, `bga/ingest/loader.py:220`) but these aren't consistently caught/mapped to exit code 2 either — confirm current behavior by testing before assuming it's fully broken vs. partially handled.
- The pytest/dev environment itself isn't fully set up out of the box (`pytest`/`pytest-cov` declared as `dev` extras in `pyproject.toml` but not installed by default) — while installing this is an environment issue, not a code bug, if you hit it while working this task, run `pip install -e ".[dev]"` (or `pip install pytest pytest-cov`) locally rather than treating it as a code defect to fix.

## Required Fix
1. In `bga/ingest/loader.py`, wrap JSON parsing calls in a `try/except json.JSONDecodeError` that re-raises as a typed ingestion error with a clear message (file path + line/col from the original exception, don't lose that detail) — coordinate with `P2-03` on the exception hierarchy name if it's landed; otherwise use a local `class IngestionError(Exception)` for now.
2. Ensure all `ValueError`s raised during ingestion (missing fields, malformed task keys, etc.) are consistently wrapped/mapped the same way, so every ingestion-time failure — JSON syntax or schema — reaches the CLI as the same error category.
3. In `bga/cli.py`, catch this category specifically and exit with code `2`, with a short, actionable message by default (not a raw traceback) — full traceback still available under `--verbose`.
4. Missing files (e.g. `run-context.json` doesn't exist at all) should map to exit code `1` per the docs — confirm this is already the case or fix it as part of this task.

## Out of Scope
- Don't build the general logging infrastructure — that's `P2-03`. This task only needs the exception types and CLI exit-code mapping, not full log wiring.

## Acceptance Test
1. Run the CLI against a run directory with intentionally malformed JSON (e.g. truncated `graph.json`) → exit code `2`, one-line actionable error message (not a raw traceback) without `--verbose`; full traceback with `--verbose`.
2. Run against a run directory missing `trace.json` entirely → exit code `1`.
3. Run against a valid fixture → exit code `0`, unaffected by this change.
4. `PYTHONPATH=. python3 tests/test_e2e.py` still passes.

## Verification Log
_(append real command + output here once run, before marking 🟢)_
