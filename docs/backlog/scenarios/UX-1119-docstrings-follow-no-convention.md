# UX-1119: docstrings follow no convention a tool can read

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** quality gates audit (`docs/audits/quality-gates-2026-09-29.md`, 2026-09-29); Ruslan took it on the audit thread (2026-09-29 06:09) | **Serves:** the reader of `bga/` | **Topic:** guards | **Area:** tools | **Shape:** judgement | **Reading:** container

**Guard:** none — named test_docstrings_follow_one_convention.py, absent from tests/

## Motivation

No docstring convention is named in `REVIEW.md`, `rules.md` or
`pyproject.toml`; `ruff --select D` finds D205 5,115 and D209 4,311 over
`bga tools tests`. The one docstring rule held today is the 25-line register
cap, by a custom AST test.

## Required Fix

`[tool.ruff.lint.pydocstyle] convention = "google"`; the `D` family joins
the baselined families (`UX-694`'s ratchet) over `bga/` and `tools/`, with
`D1xx` (missing docstrings) off and `tests/` exempt. `REVIEW.md` names the
convention in one line.

## Out of Scope

Writing missing docstrings; the register cap.

## Acceptance Test

`tests/unit/test_docstrings_follow_one_convention.py` asserts the config
names `google` and that `dev_baseline.py --check` reads the `D` family.
Mutation: a new function in `bga/` with an Args section in another style
reds the baseline check.
