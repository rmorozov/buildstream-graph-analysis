# UX-1379: bga supports Python 3.11 again, on push to main

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-1348 | **Found by:** Ruslan, a field report needs 3.11 for now (2026-11-05) | **Serves:** R8 | **Topic:** guards | **Area:** tests | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_a_pull_request_runs_the_newest_python_only.py`, `tests/unit/test_the_python_floor_is_a_guard.py`, `tests/unit/test_no_records_writer_runs_on_a_red_suite.py`

## Motivation

`UX-1348` raised `requires-python` to `>=3.12`, so `pip install` refuses
bga on 3.11, which a field user still runs. Nothing in the package needs
3.12: `requirements.lock` installs on 3.11.0 here, rc 0.

## Required Fix

`requires-python = ">=3.11"`, a 3.11 classifier, and CI's push matrix
`["3.11","3.12","3.13","3.14"]` with a `clean_311` output the records
writers wait on. The pull request keeps 3.12 alone, the primary cell
(Ruslan's choice, 2026-11-05: a 3.11-only break reds main alone). The
guards that read the floor and the cells follow, and the documents that
say "the floor Python alone" and "all three" say 3.12 and all four.

## Out of Scope

A 3.11 pull-request cell; moving the primary off 3.12; ruff and
pyright's `target-version`, which stay at 3.9.

## Acceptance Test

The full suite on 3.11 in a fresh venv off `requirements.lock` is red
only where 3.12 is red at the base; the floor clause reddens when the
push matrix drops 3.11 or `requires-python` returns to 3.12.

## Outcome (round 176, 2026-11-05) — 🟢 Done

**Premise:** held - nothing in the package or its lock needs 3.12.

### The gap, measured

```text
$ v311/bin/pip install -r requirements.lock                     # rc 0, 3.11 at 276b4df5
$ v311/bin/python -m pytest -q -n 4                             # at 276b4df5
= 2 failed, 12869 passed, 215 skipped, 5 warnings, 4 errors in 699.39s =
```

All six read the 3.12 floor: four wheel fixtures and the clang stamp test
fail in `pip wheel` ("requires a different Python"), and
`test_the_floor_is_the_one_pyproject_declares` reads `(3, 12) <= (3, 11)`.

### After

```text
$ v311/bin/python -m pytest -q <those three files + the four floor/cell guards>
======================== 57 passed, 1 skipped in 22.00s ========================
```

`uv pip compile` seeded from the lock at `--python-version 3.12`, CI's
lock check, leaves `requirements.lock` unchanged.

### Mutations verified red and reverted (2)

| # | mutation | reddened |
|---|---|---|
| A1 | push matrix without `"3.11"` | `test_the_push_matrix_starts_at_the_floor`, `..._equals_pyprojects_classifiers` |
| A2 | `requires-python = ">=3.12"` | `test_the_push_matrix_starts_at_the_floor` |

