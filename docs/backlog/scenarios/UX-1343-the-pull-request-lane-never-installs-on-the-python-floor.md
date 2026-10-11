# UX-1343: the pull-request lane never installs on the Python floor, so a 3.9-only break reds main alone

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-1340 | **Found by:** UX-1340 (2026-10-07) | **Serves:** R8 | **Topic:** guards | **Area:** tests | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_a_pull_request_runs_the_newest_python_only.py`

## Motivation

`UX-995` moved the pull request to the newest Python alone. `UX-1340`'s
pin then reded `test (3.9)` on 20 consecutive pushes to `main`
(`057bc920`..`3e3657a7`, 2026-09-29 to 2026-10-07) with every pull request
green, and nothing in the project noticed until a release looked.

## Required Fix

Open. Candidates: a `pip install --dry-run -e ".[dev]"` step on 3.9 in the
pull-request lane (seconds, no suite); or a red push run on `main` that
files or pings a row.

## Out of Scope

Running the whole suite on four Pythons per pull request.

## Acceptance Test

A pull request that pins a dev dependency 3.9 cannot install reds before
merge.

## Outcome (2026-10-08) — 🟢 Done

**Premise:** held; closed by `UX-1348`, which made the pull request's one
cell, the primary `3.12`, the `requires-python` floor - so its `pip
install -e ".[dev]"` is an install on the floor, with no new step.

### The gap, measured

At `5d25bb79`: `requires-python = ">=3.9"`, pull request `["3.12"]`.

### After

```text
$ venv3.13/bin/python -m pytest -q tests/unit/test_a_pull_request_runs_the_newest_python_only.py
5 passed
```

### Mutations verified red and reverted (1)

| # | mutation | reddened |
|---|---|---|
| M3 | `requires-python = ">=3.13"`, PR lane left on 3.12 | `test_the_pull_request_matrix_is_the_primary_cell_and_the_floor_alone` |
