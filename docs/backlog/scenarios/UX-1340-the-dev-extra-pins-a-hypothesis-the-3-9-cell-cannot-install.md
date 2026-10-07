# UX-1340: the dev extra pins a hypothesis the 3.9 cell cannot install, and main has been red since

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the 0.6.0 cut's main-is-green check (2026-10-07) | **Serves:** R8 | **Topic:** guards | **Area:** tests | **Shape:** judgement | **Reading:** container

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
