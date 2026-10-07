# UX-1340: the dev extra pins a hypothesis the 3.9 cell cannot install, and main has been red since

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the 0.6.0 cut's main-is-green check (2026-10-07) | **Serves:** R8 | **Topic:** guards | **Area:** tests | **Shape:** judgement | **Reading:** container

**Guard:** none — the install is CI's `test (3.9)` cell on push to `main`, which caught it; `UX-1343` brings it to the pull request

## Motivation

`UX-1117` pinned `"hypothesis==6.168.3"` in the `dev` extra. Hypothesis
6.142 on declares `Requires-Python >=3.10`, and `requires-python` here is
`>=3.9`. CI run 37651114659 on `3e3657a7`, job `test (3.9)`:

```text
ERROR: Could not find a version that satisfies the requirement hypothesis==6.168.3; extra == "dev"
ERROR: No matching distribution found for hypothesis==6.168.3; extra == "dev"
```

The pull-request lane runs 3.12 alone (`UX-995`), so the cell is red only
on push to `main`: every push run from `057bc920` (2026-09-29) to
`3e3657a7` failed on `test (3.9)`, 20 of 20, `0.5.0`'s own merge among them.

## Required Fix

Pin the 3.9 cell to the newest hypothesis it can install, by environment
marker, and leave the lock (resolved above 3.9) where it is.

## Out of Scope

Making the pull-request lane see a floor-only install break (`UX-1343`).

## Acceptance Test

`uv pip install -e ".[dev]"` into a 3.9 venv succeeds and the property
tests pass there; `uv pip compile` seeded from the lock leaves it unchanged.

## Outcome (round 172, 2026-10-07) — 🟢 Done

**Premise:** held — the pin, not the runner, reds the 3.9 cell.

### The gap, measured

```text
$ uv venv -p 3.9 m39 && uv pip install -p m39/bin/python -e ".[dev]"   # pyproject at 3e3657a7
      And because bga[dev]==0.5.0 depends on hypothesis==6.168.3, we can
      conclude that bga[dev]==0.5.0 cannot be used.
```

The same refusal CI run 37651114659 prints on `test (3.9)`; pip lists
6.141.1 as the newest hypothesis with no `Requires-Python >=3.10`.

### After

```text
$ uv pip install -p v39/bin/python -e ".[dev]" && v39/bin/python -c "import hypothesis,sys; ..."
3.9.25 6.141.1
$ v39/bin/python -m pytest -q -p no:xdist tests/unit/test_the_log_reader_holds_its_properties.py \
    tests/unit/test_the_minutes_inside_analyze.py tests/unit/test_capacity_recommendation.py
57 passed, 1 skipped
$ uv pip compile pyproject.toml --extra dev -o <copy of requirements.lock> --python-version 3.12
(no diff against requirements.lock)
```

The 3.9 cell installs 6.141.1 and runs the property tests; 3.10 and up keep
6.168.3, so the lock does not move.

### Mutations verified red and reverted (1)

| # | mutation | reddened |
|---|---|---|
| A1 | the `python_version < '3.10'` line dropped, the unmarked pin restored | the 3.9 install, "requirements are unsatisfiable" |

Deviation: no `tests/unit` guard; an install on the floor is CI's 3.9 cell, which only push to `main` runs (`UX-1343`).
