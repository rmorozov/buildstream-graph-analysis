# UX-821: the adopt jobs run a tool on a bare interpreter

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-698 (the defusedxml import), UX-503 / UX-524 / UX-691 (the three adopt jobs) | **Found by:** round 114, main's own CI after PR #222 | **Serves:** the default branch, whose tier reference, touching map and flake ledger stopped adopting on 2026-09-08 | **Topic:** guards | **Area:** tools | **Shape:** judgement

## Motivation

`UX-698` made `tools/dev_tier_drift.py` and `tools/dev_junit_tail.py`
parse junit with `defusedxml`, a `dev` extra. The three adopt jobs
(`tier-reference-adopt`, `touch-map-adopt`, `flake-ledger-adopt`) run
only on a push to the default branch, on `actions/setup-python` with
no install step, so every one of them has been red since that merge —
and the gate is on pull requests, where they never run:

```text
$ # main at d190935e, run 34691397514, job flake-ledger-adopt
  File ".../tools/dev_tier_drift.py", line 37, in <module>
    import defusedxml.ElementTree as ET
ModuleNotFoundError: No module named 'defusedxml'
##[error]Process completed with exit code 1.
$ # touch-map-adopt, the same run: dev_touch_map -> dev_tier_drift -> defusedxml
$ git log -1 --format='%h %ad' --date=short -S defusedxml -- tools/dev_tier_drift.py
bf5043e9 2026-09-08
```

No guard reads a job's install steps against what its tool imports.

## Required Fix

Each adopt job installs `-e ".[dev]"` after `setup-python`, as the
test job does. A guard reads `ci.yml`: every `python tools/<x>.py`
step whose tool imports a third-party module — following the tool's
own `tools/` imports — sits after a `pip install` step in its job.

## Out of Scope

- Whether the adopt jobs should install less than `[dev]` — the test
  job's step, measured at 11 s on the 3.9 lane, is what they copy.
- The rows the three jobs failed to adopt from 2026-09-08 to 2026-09-12
  — the next push to main adopts what that run measures.

## Acceptance Test

`tests/unit/test_a_ci_job_installs_what_its_tool_imports.py` green;
red with one adopt job's install step removed, and red with the
import walk stopped at the first file.

## Outcome

**Gap measured.** Three adopt jobs, each red on the same line at every
push to main from `bf5043e9` (2026-09-08) to `a20f87a8` (2026-09-12):

```text
$ python3 -c "import tests.unit.test_a_ci_job_installs_what_its_tool_imports as t; print(sorted(t.third_party_imports('dev_touch_map')))"
['defusedxml']
```

**Close measured.** One step in each of the three jobs; the guard:

```text
$ python3 -m pytest -q -p no:xdist tests/unit/test_a_ci_job_installs_what_its_tool_imports.py
3 passed in 0.29s
```

| mutation | result |
|---|---|
| the install step removed from `flake-ledger-adopt` | 1 failed, 2 passed |
| the walk stops at the first file (`found \|= …` → `pass`) | 1 failed, 2 passed — `dev_touch_map reaches defusedxml through dev_tier_drift` |
| `ci.yml` as at `a20f87a8`, the fix absent | 1 failed, 2 passed |

**Deviation.** The three jobs cannot be run here; the close is the
guard and the next push to main, which the round document names.
