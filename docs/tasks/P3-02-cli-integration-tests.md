# P3-02: CLI integration tests

**Priority:** P3, but **highest leverage of all open test tasks** | **Status:** 🔴 Not Started | **Depends on:** none — do this early, independent of `P3-01`

## Why this matters most
The original P0 breakage (CLI constructor mismatch, broken output formatters) went completely undetected by the existing test suite because **zero existing tests invoke `bga.cli` at all** — every test calls into `bga.analyzer`/other modules directly. A single integration test that runs `bga analyze` end-to-end would have caught the entire P0 class of bug immediately. This task closes that gap permanently.

## Spec Reference
`sed -n '2133,2260p' docs/specification.md` (Part 37 CLI, Part 38 Report Structure) for what output shape to expect. Also `docs/cli.md` for the documented exit-code contract.

## Required Fix
Create `tests/test_cli.py`:
1. Invoke the CLI via `bga.cli.main(argv=[...])` (preferred — faster, in-process) or `subprocess.run(["python3", "-m", "bga.cli", ...])` (use if `main()` isn't structured to be called with a custom `argv` and return an exit code cleanly — check its signature first) against fixture run directories (reuse `P3-01`'s topology library once it exists, or build a minimal fixture inline if this lands first).
2. Test each documented exit code: `0` (success), `1` (bad args/missing files), `2` (ingestion failure — pairs with `P2-02`), `3` (analysis failure/cycle — pairs with `P2-01`). If `P2-01`/`P2-02` haven't landed yet, write these test cases anyway and mark them `@pytest.mark.xfail` with a comment pointing at the blocking task ID, so they start passing automatically once those land.
3. Test each `--format` value (`text`, `json`, `csv` — confirm the exact set from `create_parser()`) produces well-formed, parseable output (e.g. `json.loads()` the JSON output and assert key fields are present and correctly typed — ints where the spec requires integer microseconds, no stray `TypeError`/`AttributeError` from the formatter).
4. Test `--output PATH` writes to a file correctly.
5. Test `--replay`/`--diagnostics`/`--capacity`/`--heuristic`/`--verbose` flags each work without crashing (don't need to assert deep correctness of their output here — that's covered by unit tests elsewhere — just that the CLI plumbing doesn't break).

## Out of Scope
- Don't test deep numeric correctness of the analysis itself here (that's what `P3-03` and friends are for) — this task is specifically about the CLI plumbing (argv → analyzer → formatter → stdout/exit code) not breaking, which is exactly the layer that broke silently before.

## Acceptance Test
`PYTHONPATH=. python3 -m pytest tests/test_cli.py -v` — all cases pass (or are `xfail` with a clear reason pointing at the blocking task). This test file itself, once created, becomes part of the standard regression check every other task's Verification Log should reference alongside `tests/test_e2e.py`.

## Verification Log
_(append real command + output here once run, before marking 🟢)_
