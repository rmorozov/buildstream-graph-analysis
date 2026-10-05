# UX-1335: the dev extra pins a hypothesis the Python floor cannot install

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the merge steward reading main's matrix on `19f1fd73` (2026-10-03) | **Serves:** R5 | **Topic:** guards | **Area:** unassigned | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_every_dev_pin_installs_on_the_python_floor.py`

## Motivation

`pyproject.toml` declares `requires-python = ">=3.9"`; UX-1117 pinned
`hypothesis==6.168.3`, whose metadata says `Requires-Python: >=3.10`.
Main's `test (3.9)` cell has failed at install on every first-parent merge
from `057bc920` (#301) to `19f1fd73` (#315); `e88c2773` before it passed.
PR CI runs 3.12 alone (UX-995), so no pull request saw it:

```text
ERROR: Could not find a version that satisfies the requirement hypothesis==6.168.3; extra == "dev"
ERROR: No matching distribution found for hypothesis==6.168.3; extra == "dev"
```

Ruslan's call, 2026-10-03: keep 3.9.

## Required Fix

Pin hypothesis per Python with a marker: `6.168.3` from 3.10, `6.141.1`
(the newest whose wheel resolves for 3.9) below. A guard reds an exact dev
pin whose installed release's Requires-Python excludes the floor. Whatever
else the floor's suite then shows is fixed in the same commit.

## Out of Scope

Running 3.9 on pull requests; the other cells' install pins, which are
ranges pip resolves per Python.

## Acceptance Test

`pip install -e ".[dev]"` and `make test` on a 3.9 interpreter in this
container; the guard reds with the unmarked pin restored.

## Outcome

## Outcome (round 171, 2026-10-03) — 🟢 Done

**Premise:** held — the floor's cell failed at install, and behind the
install the suite itself no longer ran on 3.9.

### The gap, measured

```text
$ uv python install 3.9; python3.9 -m venv v39; v39/bin/pip install -e ".[dev]"   # main 19f1fd73
ERROR: No matching distribution found for hypothesis==6.168.3; extra == "dev"
$ make test   # v39 on PATH, pin split only
3 failed, 12300 passed, 216 skipped, 26 errors
    27 x TypeError: zip() takes no keyword arguments
```

Past the pin, `zip(strict=True)` (3.10+) in three test files errored 26
browser tests and failed one; the other two failures were this row's own
unfiled row and undeclared skip reason.

### After

```text
$ make test   # v39 on PATH
12330 passed, 216 skipped in 866.32s
$ python3 -m pytest tests/unit/test_every_dev_pin_installs_on_the_python_floor.py \
    tests/unit/test_the_package_runs_on_the_python_it_claims.py      # 3.11
7 passed
```

### Mutations verified red and reverted (3)

| # | mutation | reddened |
|---|---|---|
| A1 | `pyproject.toml` back to the unmarked `hypothesis==6.168.3` | 1 of 2 (`requires Python >=3.10`) |
| A2 | the marker evaluation dropped from `offenders()` | 2 of 2 |
| A3 | `strict=True` restored in `test_back_after_a_reveal_re_folds.py:123` | `test_no_zip_takes_strict_below_3_10`, 1 |

### Deviation from the Required Fix

The `zip(strict=)` clause joins UX-539's floor guard and scans `tests/`
too, since the floor's cell runs the suite, not only the package.

