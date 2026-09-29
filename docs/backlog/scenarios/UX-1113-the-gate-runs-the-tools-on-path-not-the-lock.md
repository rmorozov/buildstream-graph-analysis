# UX-1113: the gate runs whichever ruff and pyright are first on PATH, not the locked ones

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** quality gates audit (`docs/audits/quality-gates-2026-09-29.md`, 2026-09-29) | **Serves:** anyone whose push gate reds on a clean tree | **Topic:** guards | **Area:** tools | **Shape:** judgement | **Reading:** container

**Guard:** none — named test_the_gate_runs_the_locked_tools.py, absent from tests/

## Motivation

`make lint` calls bare `ruff`, and `dev_baseline.py` a bare `pyright`. In
this container `/root/.local/bin` shadows the lock: `ruff` 0.15.8 against
the locked 0.16.8, `pyright` 1.1.408 against 1.1.414. On `main` at
`e88c2773`, `make push-check` reds with
`new: pyright reportOperatorIssue tools/bst_cache_logs.py (#1)`, a finding
the pinned pyright does not make (round 149 saw the same line). A gate that
reds on a clean tree for a version reason teaches people to force past it.

## Required Fix

The Makefile, `dev_baseline.py` and `.claude/hooks/lint-edited-python.sh`
invoke `python3 -m ruff` and the pinned pyright
(`PYRIGHT_PYTHON_FORCE_VERSION` from the lock); `dev_baseline.py --check`
prints the tool versions it ran and refuses to judge when they differ from
`requirements.lock`.

## Out of Scope

Pinning tools outside the dev extra.

## Acceptance Test

`tests/unit/test_the_gate_runs_the_locked_tools.py`: with a fake `ruff`
earlier on PATH printing another version, `dev_baseline.py --check` names
the mismatch and exits non-zero, and the Makefile's lint recipe contains no
bare `ruff`. Mutation: restore the bare call; it reddens.
