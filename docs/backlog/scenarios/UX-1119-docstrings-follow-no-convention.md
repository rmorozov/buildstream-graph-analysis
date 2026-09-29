# UX-1119: docstrings follow no convention a tool can read

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** — | **Found by:** quality gates audit (`docs/audits/quality-gates-2026-09-29.md`, 2026-09-29); Ruslan took it on the audit thread (2026-09-29 06:09) | **Serves:** the reader of `bga/` | **Topic:** guards | **Area:** tools | **Shape:** mechanical | **Reading:** container

**Guard:** none — named test_docstrings_follow_one_convention.py, absent from tests/

## Motivation

No docstring convention is named in `REVIEW.md`, `rules.md` or
`pyproject.toml`; `ruff --select D` finds D205 5,115 and D209 4,311 over
`bga tools tests`. The one docstring rule held today is the 25-line register
cap, by a custom AST test.

## Decision

Architect, round 151 (2026-09-29):

```text
Route:     `[tool.ruff.lint.pydocstyle] convention = "google"`; dev_baseline.py FAMILIES gains D2, D3, D4 with IGNORED = (D205, D209, D212) passed as `--ignore` (1,226 layout hits that conflict with the house register); 22 real findings absorbed (D301 9, D403 5, D415 4, D417 3, D200 1) against 575 (+4%); tests/ stays out; REVIEW.md names the convention in one line
Rejected:  the full D2-D4 set (1,248 entries, baseline 128 KB -> ~400 KB); pep257 (1,637, 492 of them D401); `ruff --fix` of D209/D212 (a tree-wide rewrite colliding with 1118)
Files:     pyproject.toml ([tool.ruff.lint.pydocstyle]); tools/dev_baseline.py; tests/quality_baseline.json (+22, `--write --force --reason UX-1119`); REVIEW.md; tests/unit/test_docstrings_follow_one_convention.py
Guard:     pyproject names google, FAMILIES carries D2/D3/D4, and a scratch file under a copied tree turns `--check` red
Mutation:  the row's numpy-section mutation does NOT redden (measured); a bga/ function whose `Args:` omits a parameter (D417) reddens; removing D4 from FAMILIES turns it green
Class:     bookkeeping (cap lifted)
Split:     B track, after 1113
```

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

## Outcome

**Gap measured.** `python3 -m ruff check --select D bga tools tests` on
`d3ef4bf6` (Decision's reading): D205 5,115, D209 4,311; no convention named.

**Close measured.** `pyproject.toml` `[tool.ruff.lint.pydocstyle]
convention = "google"`; `dev_baseline.py` FAMILIES gain D2/D3/D4, `IGNORED =
(D205, D209, D212)` passed as `--ignore`; baseline 576 -> 598 (22 forced by
`--reason UX-1119`: D301 9, D403 5, D415 4, D417 3, D200 1); `REVIEW.md` names
the convention in one line. `tests/` stays out (`DEFAULT_PATHS`). The
guard's scratch tree carries only the real `[tool.ruff.lint.pydocstyle]`
section, not the whole pyproject (the suppression census reads a copied one).
UX-1112's own S603 (`tools/dev_lint_docs.py`) was forced under `UX-1112` in
that commit.

| Mutation | Reddened | Count |
|---|---|---|
| `D4` out of FAMILIES | families test, D417 scratch case | 2 failed, 3 passed |
| `convention = "numpy"` | names-google test, D417 scratch case | 2 failed, 3 passed |
