# UX-1113: the gate runs whichever ruff and pyright are first on PATH, not the locked ones

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Found by:** quality gates audit (`docs/audits/quality-gates-2026-09-29.md`, 2026-09-29) | **Serves:** anyone whose push gate reds on a clean tree | **Topic:** guards | **Area:** tools | **Shape:** mechanical | **Reading:** container

**Guard:** none — named test_the_gate_runs_the_locked_tools.py, absent from tests/

## Motivation

`make lint` calls bare `ruff`, and `dev_baseline.py` a bare `pyright`. In
this container `/root/.local/bin` shadows the lock: `ruff` 0.15.8 against
the locked 0.16.8, `pyright` 1.1.408 against 1.1.414. On `main` at
`e88c2773`, `make push-check` reds with
`new: pyright reportOperatorIssue tools/bst_cache_logs.py (#1)`, a finding
the pinned pyright does not make (round 149 saw the same line). A gate that
reds on a clean tree for a version reason teaches people to force past it.

## Decision

Architect, round 151 (2026-09-29):

```text
Route:     remove the shadow: dev_baseline.py runs `[sys.executable, "-m", "ruff"|"pyright", ...]` (the lock's: 0.16.8, 1.1.414 measured); the Makefile and lint-edited-python.sh call `python3 -m ruff`; `--check` prints both versions and exits 2 when either differs from requirements.lock, read through dev_env_check.py's pinned_version/reported_version/version_ok
Rejected:  PYRIGHT_PYTHON_FORCE_VERSION (downloads another node bundle on a mismatch); PATH reordering (a hook and a direct call would still differ); keeping `ruff_version` in quality_baseline.json (a committed copy of the pin, UX-996)
Files:     tools/dev_baseline.py; Makefile; .claude/hooks/lint-edited-python.sh; tests/quality_baseline.json (drop `ruff_version`, and DOCUMENT_KEYS); tools/dev_env_check.py (retire ruff/pyright TOOLS entries); tests/unit/test_the_env_check_catches_a_repoint.py; tests/unit/test_the_gate_runs_the_locked_tools.py
Guard:     (a) fake `ruff`/`pyright` printing 0.0.1 first on PATH: the version line reads the lock's pins, verdict unchanged; (b) reported version monkeypatched off the lock: `--check` names it and exits 2; (c) no Makefile recipe or hook line starts with bare `ruff`/`pyright`
Mutation:  restore `["ruff", "--version"]` - (a); delete the refusal - (b); bare `ruff check` in the hook - (c)
Class:     bookkeeping (cap lifted) - a false red on a clean main (r149, e88c2773)
Split:     B track, first; before 1112, 1119 and 1118
```

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

## Outcome

**Gap measured.** PATH `ruff --version` 0.15.8, `pyright --version` 1.1.408;
lock 0.16.8 / 1.1.414. `make lint` on `d3ef4bf6` ran the PATH pair.

**Close measured.** `python3 tools/dev_baseline.py --check` prints
`tools: pyright 1.1.414, ruff 0.16.8` (stderr) with the shadowing binaries
still first on PATH; `make lint` needs no `PYRIGHT_PYTHON_FORCE_VERSION`.
Done as decided: `python3 -m ruff|pyright` (`sys.executable`) in
`dev_baseline.py`, Makefile, hook; `ruff_version` dropped from the baseline and
`DOCUMENT_KEYS`; ruff/pyright rows retired from `dev_env_check.TOOLS` (node
stays); the one new S603 is `--force --reason UX-1113`. pyright's version is
not read under `--pyright-from` (UX-802: no pyright spawn). Two guards edited:
`test_the_env_check_catches_a_repoint.py` (population is node),
`test_the_baseline_only_shrinks.py` (broken pyright is a fake `-m` package).
`test_the_selection_is_a_fraction_of_the_suite` reds (median 39 > 38) with or
without this diff.

| Mutation | Reddened | Count |
|---|---|---|
| `[tool, "--version"]` for the `-m` call | (a) version line | 1 failed, 4 passed |
| `if mismatches:` -> `if False:` | (b) main exits 2 | 1 failed, 4 passed |
| bare `ruff check` in the hook | (c) no bare tool | 1 failed, 4 passed |
