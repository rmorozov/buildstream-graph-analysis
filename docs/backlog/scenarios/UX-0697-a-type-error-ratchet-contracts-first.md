# UX-697: a type-error ratchet, contracts first

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-694 (the baseline) | **Serves:** the session editing a schema or a contract, where a wrong key is a `UX-190` bump nobody meant | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

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

**Gap measured.** `pyright bga tools --outputjson`: 118 files, **293**
errors, 10.2 s (`[tool.pyright]` and the pin landed in `cb99d2d8`);
`dev_baseline.py --check` read ruff only — a type error had no gate.

**Close measured.** `pyright_findings` joins `ruff_findings` in
`tools/dev_baseline.py`, sharing `_identity_list` so a pyright
finding's identity is `(tool="pyright", rule, file, collapsed line
text, nth)` exactly like ruff's. `--write --force --reason UX-697` →
`wrote 581 finding(s); 294 authorised by UX-697` (293 pyright + the
producer's own `ruff S603`). `make lint`: 103.9 s before, 130.4 s
after. `make test-touching`: 34 files, 1263 passed, 195 s. A verifier
found `if rule` dropped a severity-error diagnostic with no rule key
(a module-level `return`, which ruff's parser accepts) — `--check`
read clean on a real defect; fixed as `noRule` with its own clause.

| mutation | reddened |
|---|---|
| drop pyright from the producers | 2/3 new clauses |
| treat pyright exit 3 as "no findings" | `test_a_broken_pyright_exits_2_and_writes_nothing` |
| store the row, not the line text, as the identity's line | `TestIdentityIgnoresTheLineNumber`, `TestOccurrenceDisambiguates` |
| restore `if rule` | `test_a_rule_less_pyright_error_is_still_new` |

### Contract surfaces half

**Gap measured** (base `47cfe060`): `pyright bga/schemas.py
bga/contracts.py bga/report` → 12 errors (schemas 4, contracts 0,
report 8: json 3, text 5).

**Close measured.** Same command → 0. `schemas.py`: two `dict = None`
parameters made `Optional[dict]`, `EVIDENCE_QUANTITIES` annotated
`dict[str, dict]`. `report/json.py`, `report/text.py`: `resource_blast`
and `plane2_coverage` declared on `AnalysisResult` as `Optional[dict] =
None` — the fields `cli.py` sets at runtime — and read directly;
`occupancy_stats` stays `getattr`, only a test double carries it.
`text.py:272`'s `(joint or {})` closes a type error, not a bug: the
branch is unreachable with `joint` None (the verifier traced it).
Strict, measured: the three surfaces under `strict` → 1363 errors
(`reportUnknownMemberType` 531, `reportUnknownVariableType` 400,
`reportUnknownArgumentType` 196); reverted, a later burn-down batch.

**Acceptance Test, on the merged tree.** `--shrink` removed the 12
entries the contract half fixed; `def _ux697_probe() -> int: return "x"`
in `bga/report/json.py` → `new: pyright reportReturnType
bga/report/json.py (#1) return "x"`, exit 1; restored, clean.

**Deviation.** The judgement (pin, config, one gate one list, strict
deferred) was the session's; two `implementer` tracks on `sonnet` did
the halves, each read by a `verifier`: the `noRule` hole and the
overstated "real bug" sentence were theirs, fixed before the merge.
`strict` is not listed — 1363 errors is `UX-705`'s burn-down shape,
filed there rather than here. `make lint` carries pyright's 26 s now.
CI's first run reddened on `reportMissingImports` for `from buildstream
import _site`: the runner has no BuildStream, the dev box does, so the
finding existed in one environment only. `reportMissingImports` and
`reportMissingModuleSource` are off in `[tool.pyright]` — an identity
must not move with what is installed.
