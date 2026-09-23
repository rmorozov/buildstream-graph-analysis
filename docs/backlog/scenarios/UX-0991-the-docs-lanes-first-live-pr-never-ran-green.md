# UX-991: UX-956's docs lane never ran green on its first live PR

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-956 | **Blocks:** — | **Found by:** round 139 — PR #277, CI job 107184948186 on `2fb11985` | **Serves:** every docs-only pull request the lane is meant to spare the full matrix | **Topic:** guards | **Area:** tools | **Shape:** judgement

## Motivation

`UX-956` built a light `docs-lane` job. Its first live PR (#277) never
ran it green, two independent defects:

(a) `tools/dev_docs_lane.py --run` called `pytest.main()` **in-process**.
`sys.path[0]` for a script invoked as `python3 tools/dev_docs_lane.py`
is the script's own directory, `tools/`, not the repo root - so
`tests/unit/test_a_behaviour_claim_names_the_bst_it_was_read_on.py`
(always in the lane, via `tiers.CENSUS`), whose own `from
tests.unit.test_the_pinned_bst_is_the_documented_one import pinned`
needs the repo root importable as a package, errored:

```text
$ echo docs/audits/round-138.md | python3 tools/dev_docs_lane.py --run
...
2592 passed, 4 skipped, 1 error
```

reproduced on `origin/main` `2dac36ec`, and matching CI job
`107184948186` on `2fb11985`. `make test` runs `python -m pytest`,
which puts the repo root at `sys.path[0]` instead - the reason the
full matrix never saw this.

(b) `ci.yml`'s `changes` job diffs `github.event.pull_request.base.sha`
against the checked-out merge ref. `base.sha` is the event's own
snapshot from push time; when main moves before the run starts - CI's
own adopt commits do this constantly - it is stale and main's own new
commits appear in the diff, flipping `docs_only` to `false` on an
actually-docs-only PR. Measured on run `35862765977` (PR #277, HEAD
`420b9acc`): `base.sha` was `9ffa0b6b` while the merge ref `8907b1f3`
was built on `2dac36ec` (a `flake_ledger.json` adopt committed
12:47:19, run created 12:47:50):

```text
$ git diff --name-only 9ffa0b6b 8907b1f3   # base.sha -> merge ref
... includes tests/flake_ledger.json -> docs_only=false
$ git diff --name-only 2dac36ec 8907b1f3   # HEAD^1 -> merge ref
... -> docs_only=true
```

## Required Fix

(a) Keep `pytest.main()` in-process. Before `import pytest`, put REPO
first on `sys.path` and prepend it to `os.environ["PYTHONPATH"]`, so
`-n auto`'s own worker interpreters - separate processes, spawned from
the environment, not this process's `sys.path` - inherit it too.

(b) On a `pull_request` event, diff `HEAD^1` (the merge ref's own
first parent - the base it was actually built on) against `HEAD`,
in both the `changes` job's step and the `docs-lane` job's `git diff`
step. Keep the non-PR fallback (`HEAD`) as it is.

## Out of Scope

- Pinning `base.sha` some other way (a second checkout, a stored ref) -
  `HEAD^1` reads what the runner already checked out, no extra fetch.
- The `pytest.main()` in-process convenience elsewhere in the repo
  (`dev_docs_only.py`'s own `main()` takes no pytest dependency at all,
  and no other tool here shells to pytest): not measured to share this
  defect.

## Acceptance Test

`echo docs/audits/round-138.md | python3 tools/dev_docs_lane.py --run`
exits clean, no `ModuleNotFoundError`, no `error` outcome. A guard
proves a census file importing `tests.unit....` collects under a real,
unmocked `run_pytest()` call, `-n auto` included; mutating away the
`sys.path`/`PYTHONPATH` insertion reds it. A guard over `ci.yml`
proves the diff base is `HEAD^1` on a `pull_request`, not `base.sha`;
mutating back to `base.sha` reds it.

## Outcome

**Round 139, 2026-09-23**

**Gap measured** (both defects, pasted above under Motivation) -
(a) on `origin/main` `2dac36ec`: `2592 passed, 4 skipped, 1 error`;
(b) on PR #277's run `35862765977`: `base.sha` (`9ffa0b6b`) misses a
`flake_ledger.json` adopt commit the merge ref (`8907b1f3`) already
carries, so `git diff base.sha merge-ref` wrongly includes it while
`git diff HEAD^1 merge-ref` does not.

**Close measured.** (a) `tools/dev_docs_lane.py`'s new `run_pytest()`
inserts REPO at `sys.path[0]` and prepends it to `PYTHONPATH` before
`import pytest`; `main()` calls it and returns its int. Re-run after
the fix, real `-n auto` workers included:

```text
$ echo docs/audits/round-138.md | python3 tools/dev_docs_lane.py --run
78 test file(s) in the docs lane
2627 passed, 4 skipped in 58.80s
```

(b) `ci.yml`'s `changes` and `docs-lane` steps both now diff
`"${{ github.event_name == 'pull_request' && 'HEAD^1' || 'HEAD' }}"`;
neither names `base.sha` any more.

**Mutation table** (`tests/unit/test_a_docs_only_diff_runs_its_guards.py`,
32 tests; scratchpad snapshot/revert, never `git checkout --`):

| mutation | reddened | count |
|---|---|---|
| (a) drop the `sys.path`/`PYTHONPATH` insertion | `test_a_census_file_that_imports_another_test_module_collects` - the real `ModuleNotFoundError` this task opened with, in 0.46s inside a fresh subprocess | 1/32 |
| (b) `changes` step's diff reverted to `base.sha` | `test_the_diff_base_is_the_merge_refs_first_parent_not_base_sha` | 1/32 |
| (b) `docs-lane` step's diff reverted to `base.sha` | same test, second `assert` | 1/32 |

The census-collection guard runs `run_pytest()` for real (unmocked),
as a same-directory sibling script under `tools/` - a `python -c`
witness would not discriminate: `-c`'s own `sys.path[0]` is `''` (the
process cwd), which `cwd=REPO` already satisfies regardless of the fix
under test, the "guard whose setup already excludes" shape (`CLAUDE.md`).
A plain file run from `tools/` reproduces the real script's own
`sys.path[0]`. Every mutation reverted; suite back to 32/32 and files
byte-identical to the snapshot each time.

**Deviation:** the Required Fix originally shelled to
`[sys.executable, "-m", "pytest", ...]` as a subprocess - `make test`'s
own shape, avoiding `sys.path` entirely. That needed a new, forced
`tests/quality_baseline.json` entry (ruff S603 on the new
`subprocess.run` call - this repo's own convention for every such
call, ~30 existing forced entries). `dev_baseline.py --write --force
--reason UX-991` was refused twice by the session's own permission
classifier ("Security Test Removal", then "CI Bypass") as a false
positive on routine baseline maintenance. Per instructions, not routed
around (no hand-edited baseline, no `noqa` - `UX-705` counts a
suppression as a finding too, same wall). Reworked to the in-process
`sys.path`/`PYTHONPATH` shape instead, which needs no new subprocess
call and so no baseline entry; `make lint` is clean under it.
