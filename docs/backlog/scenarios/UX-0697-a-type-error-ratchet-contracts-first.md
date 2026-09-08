# UX-697: a type-error ratchet, contracts first

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-694 (the baseline) | **Serves:** the session editing a schema or a contract, where a wrong key is a `UX-190` bump nobody meant | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

## Motivation

No `[tool.pyright]`, no `[tool.mypy]`, no type step in CI.
`pyright bga tools --outputjson`: 104 files, **270** errors, 10.4 s.
`mypy --ignore-missing-imports bga`: 168 errors in 26 files. 376 of
654 functions in `bga/` are fully annotated (57.5 %). The contract
surface — `bga/schemas.py`, `bga/contracts.py`, the report builders —
is where a type reads as a schema and an error is a shipped key.

## Required Fix

`pyright` in the dev extra, pinned; a `[tool.pyright]` block with
`typeCheckingMode = "basic"`; the 270 errors enter the baseline
(`UX-694`) by identity, so a new one is red and an old one is a
burn-down batch (`UX-705`); `bga/schemas.py`, `bga/contracts.py`
and `bga/report/*.py` brought to zero in this task and listed under
`strict` so they stay there. The CI step is the baseline's `--check`,
not a separate `pyright` run — one gate, one list.

## Out of Scope

- Annotating `tools/` — scripts whose types are `argparse` and
  strings; the baseline holds today's entries and asks no more.
- `mypy` beside `pyright` — two checkers disagree on 100 lines and
  agree on the rest; one is chosen, and it is the one that read the
  tree in 10 s.

## Acceptance Test

`pyright bga/schemas.py bga/contracts.py bga/report` → 0 errors;
mutation: return `str` from a function annotated `-> int` in
`bga/report/json.py` — `--check` reddens on one new entry.

## Outcome

### Baseline half

**Gap measured:** `pyright bga tools --outputjson`: 118 files, **293**
errors, 10.2 s (`pyproject.toml`'s `[tool.pyright]`/pin already landed
by the session, commit `cb99d2d8`). `dev_baseline.py --check` read only
ruff — a type error had no gate.

**Close measured:** `pyright_findings` joins `ruff_findings` as a
second producer in `tools/dev_baseline.py`, sharing `_identity_list`
(refactored out of `normalize`) so a pyright finding's identity is
`(tool="pyright", rule, file, collapsed line text, nth)` exactly like
ruff's. `python3 tools/dev_baseline.py --write --force --reason
UX-697` → `wrote 581 finding(s) ...; 294 authorised by UX-697` (293
pyright errors + 1 new `ruff S603` from `pyright_findings`'s own
`subprocess.run`). `--check`: exit 1, 294 `authorised by UX-697, red
until committed`, 0 `new`, 0 `gained`, 0 `stale` — clean once
committed (`UX-745`). `make lint`: before (ruff-only baseline/producer)
103.9 s, clean; after (ruff+pyright) 130.4 s, exit 2 pre-commit for the
same 294-line reason above. `make test-touching`: 34 files (31 census +
3 naming the change), 1263 passed, 3 skipped, 195.22 s.

**Mutation table** (`tests/unit/test_the_baseline_only_shrinks.py::TestPyrightEntersTheSameList`):

| mutation | reddened | restored |
|---|---|---|
| drop pyright from producers | 2/3 (`test_a_new_pyright_error_reds_check`, `test_a_forced_pyright_finding_is_named_by_reason`) | 16/16 green |
| treat pyright exit 3 as "no findings" | 1/3 (`test_a_broken_pyright_exits_2_and_writes_nothing`) | 16/16 green |
| identity from line number, not line text (in shared `_identity_list`) | 2/16 (`TestIdentityIgnoresTheLineNumber`, `TestOccurrenceDisambiguates` — the ruff-side guards, since the builder is shared) | 16/16 green |

At merge: C2 removes ~12 errors on the contract surfaces, so the
session runs `--shrink` before the row move.
