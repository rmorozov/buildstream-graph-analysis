# UX-697: a type-error ratchet, contracts first

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-694 (the ledger's column) | **Serves:** the session editing a schema or a contract, where a wrong key is a `UX-190` bump nobody meant | **Topic:** guards

## Motivation

No `[tool.pyright]`, no `[tool.mypy]`, no type step in CI.
`pyright bga tools --outputjson`: 104 files, **270** errors, 10.4 s.
`mypy --ignore-missing-imports bga`: 168 errors in 26 files. 376 of
654 functions in `bga/` are fully annotated (57.5 %). The contract
surface — `bga/schemas.py`, `bga/contracts.py`, the report builders —
is where a type reads as a schema and an error is a shipped key.

## Required Fix

`pyright` in the dev extra, pinned; a `[tool.pyright]` block with
`typeCheckingMode = "basic"`; the per-file error count a ledger column
(`UX-694`) so it may not grow; `bga/schemas.py`, `bga/contracts.py`
and `bga/report/*.py` brought to zero in this task and listed under
`strict` so they stay there. The CI step is the ledger's guard, not a
separate `pyright` run — one gate, one reference.

## Out of Scope

- Annotating `tools/` — scripts whose types are `argparse` and
  strings; the ratchet holds them at today's count and asks no more.
- `mypy` beside `pyright` — two checkers disagree on 100 lines and
  agree on the rest; one is chosen, and it is the one that read the
  tree in 10 s.

## Acceptance Test

`pyright bga/schemas.py bga/contracts.py bga/report` → 0 errors;
mutation: return `str` from a function annotated `-> int` in
`bga/report/json.py` — the ledger guard reddens on that file's row.
