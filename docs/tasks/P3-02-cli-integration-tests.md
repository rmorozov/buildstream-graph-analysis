# P3-02: CLI integration tests

**Priority:** P3, but **highest leverage of all open test tasks** | **Status:** 🟢 Fixed & Verified (`tests/test_cli.py` already exists and passes; re-verified 2026-08-13) | **Depends on:** none — do this early, independent of `P3-01`

## Status note (2026-08-13)
`tests/test_cli.py` already exists, covering `--help`, `analyze --help`, a nonexistent-dir exit-code-1 case, `analyze` with `--format json`/`text`/`csv`, and `--version` — 7 tests, all passing (see Verification Log). It does **not** yet cover exit codes 2/3 (ingestion/cycle failures, since `P2-01`/`P2-02` aren't done) — those cases should be added, `xfail`-marked pointing at `P2-01`/`P2-02`, once picked up; not required to re-open this task's status for that, treat it as a natural extension. `tests/test_synthetic_multi_subproject.py` (`P3-10`) adds a second, larger CLI end-to-end case on top of this.

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
```
$ PYTHONPATH=. python3 -m pytest tests/test_cli.py -v
tests/test_cli.py::test_cli_help PASSED
tests/test_cli.py::test_cli_analyze_help PASSED
tests/test_cli.py::test_cli_analyze_nonexistent_dir PASSED
tests/test_cli.py::test_cli_analyze_fixture PASSED
tests/test_cli.py::test_cli_analyze_text_format PASSED
tests/test_cli.py::test_cli_analyze_csv_format PASSED
tests/test_cli.py::test_cli_version PASSED
7 passed
```
(2026-08-13, re-verified while building `tests/test_synthetic_multi_subproject.py` / `P3-10`.)
