# UX-1128: the weekly lock check reds on any upstream release, so the audit never runs

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-698 | **Found by:** Ruslan, `Quality` run 36426449685 and PR #302 | **Serves:** anyone reading the weekly shelf for a vulnerable pin | **Topic:** guards | **Area:** tools | **Shape:** mechanical | **Reading:** container

**Guard:** test_the_gate_only_shelf_is_on_github.py

## Motivation

`quality.yml`'s `pip-audit` job compiles the dev extra into an empty
`/tmp/requirements.lock`, so uv resolves every package to its newest
release and the diff against the committed lock reds whenever anything
upstream ships. The scheduled run on `39d89d47` failed on `isort 9.0.1 ->
9.0.2` and `platformdirs 4.12.0 -> 4.12.1`, neither named by
`pyproject.toml`, and `pip-audit` itself never ran. The `sizes` job
installs `.[dev]` plus an unpinned `pylint`, while R0801's count moves with
the pylint that reads it (`UX-1126`).

## Required Fix

The lock check copies `requirements.lock` to its output path before
compiling, so uv keeps every pin the extra still admits and only a pin
`pyproject.toml` no longer admits moves. `sizes` installs
`requirements.lock`, then the package with `--no-deps`.

## Out of Scope

Freshness, which Dependabot's pip group owns; the Python the shelf runs.

## Acceptance Test

The step seeds the file it compiles into; `sizes` has exactly the two lock
installs. Seeded, the scheduled run's sha passes and PR #302's
pyproject-only bump reds on `ruff`.

## Outcome (PR #302, 2026-09-29) — 🟢 Done

**Premise:** held — an empty output path resolves every package fresh.

### The gap, measured

```text
$ gh run 36426449685, job pip-audit, sha 39d89d47 (schedule)
25c25 < isort==9.0.1 --- > isort==9.0.2
41c41 < platformdirs==4.12.0 --- > platformdirs==4.12.1
requirements.lock is stale: run make lock
```

Two transitive pins moved upstream, no `pyproject.toml` line changed, and
the job exited 1 before `pip-audit` read anything.

### After

```text
$ cp <lock> t.lock; uv pip compile pyproject.toml --extra dev -o t.lock -q; diff   # uv 0.12.20
39d89d47's lock and pyproject:       pass
#302's pyproject, main's lock:       RED  < ruff==0.16.8  > ruff==0.16.9
#302's pyproject, regenerated lock:  pass
```

Seeded, the check reds only on a pin the extra no longer admits.

### Mutations verified red and reverted (3)

| # | mutation | reddened |
|---|---|---|
| A1 | the `cp requirements.lock` line deleted | `test_the_lock_check_is_seeded_from_the_committed_lock`, 1 failed / 9 |
| A2 | the seed copied to `/tmp/seed.lock`, not the compile's output | same clause, 1 failed / 9 |
| A3 | `sizes` back to `pip install -e '.[dev]' pylint` | `test_the_sizes_job_installs_the_lock`, 1 failed / 9 |

Deviation: none from the Required Fix.
