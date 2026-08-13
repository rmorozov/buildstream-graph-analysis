# P2-02: Malformed JSON / bad input unhandled

**Priority:** P2 | **Status:** 🟢 Fixed & Verified (2026-08-13) — was partially already done | **Depends on:** none

## What was already true vs. what was actually fixed
Re-verifying before starting (found while confirming `P2-01`) showed this was **partially** already fixed, not fully unstarted as originally diagnosed:
- `load_run_context` and `load_trace` (`bga/ingest/loader.py`) **already** wrapped `json.JSONDecodeError` and re-raised as `ValueError` with a clear message; `bga/cli.py` **already** caught `json.JSONDecodeError`/`ValueError` and mapped to exit code `2` with a short message (full traceback under `--verbose`).
- `load_graph` did **not** have the same wrapping — a malformed `graph.json` still exited `2` correctly (because `json.JSONDecodeError` is a `ValueError` subclass and the CLI's `except ValueError` catches it too), but with a plain raw exception message instead of the friendlier "Malformed JSON in graph file ..." prefix the other two loaders already had. **Fixed**: added the same `try/except json.JSONDecodeError` wrapping to `load_graph`, for consistency.
- A genuinely **missing** required file (e.g. `graph.json` absent from an existing run directory) raised a raw `FileNotFoundError`, which is *not* a `ValueError` subclass, so it fell through to the generic `except Exception` handler and exited `2` — contradicting `docs/cli.md`'s documented `1` = "bad args/missing files". **Fixed**: `bga/cli.py::cmd_analyze` now has a dedicated `except FileNotFoundError` branch, checked before `ValueError`, mapping to exit code `1` with a clear "Required input file not found" message.

## What was intentionally *not* done
The original task description suggested introducing a typed ingestion exception class (e.g. `class IngestionError(Exception)`), possibly coordinating with `P2-03`'s exception hierarchy. **Not done** - the fix instead extended the existing, already-established pattern (loaders raise plain `ValueError` with a descriptive message; the CLI maps by type/content). Introducing a new exception type now, before `P2-03` (still unstarted) decides on a real hierarchy, would mean redoing this wrapping again later for no benefit in the meantime. If `P2-03` lands a proper hierarchy, revisit whether these `ValueError`s should become a more specific type - not required for this task's own correctness.

## Spec Reference
No spec section — this is a robustness gap, not a spec-compliance one. `docs/cli.md`'s exit-code table: `1` = bad args/missing files, `2` = ingestion failure (e.g. malformed JSON), `3` = analysis failure (cycles, `P2-01`).

## Out of Scope
- General logging infrastructure — that's `P2-03`.
- A formal typed exception hierarchy — see "What was intentionally not done" above.

## Acceptance Test — as executed
1. Malformed `graph.json` → exit code `2`, message `"Malformed JSON in graph file <path>: <detail>"` (not a raw traceback) without `--verbose`.
2. Run directory missing a required file entirely → exit code `1`, message `"Required input file not found - <detail>"`.
3. Nonexistent run directory → exit code `1` (pre-existing, unaffected).
4. Valid fixture → exit code `0`, unaffected.
5. `tests/unit/test_cli_exit_codes.py` (new, shared with `P2-01`) covers all of the above as permanent regression tests.

## Verification Log
```
$ python3 -m bga.cli analyze <malformed graph.json fixture>
Error: Malformed JSON in graph file .../graph.json: Expecting property name enclosed in double quotes: line 1 column 2 (char 1)
exit: 2

$ python3 -m bga.cli analyze <run dir missing run-context.json>
Error: Required input file not found - [Errno 2] No such file or directory: '.../run_context.json'
exit: 1

$ python3 -m bga.cli analyze <nonexistent dir>
exit: 1

$ PYTHONPATH=. python3 -m pytest tests/unit/test_cli_exit_codes.py -v
5 passed

$ PYTHONPATH=. python3 -m pytest tests/ -q
43 passed
```
