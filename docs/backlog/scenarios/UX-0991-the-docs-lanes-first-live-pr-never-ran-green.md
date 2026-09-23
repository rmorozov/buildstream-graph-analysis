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

(a) Run `[sys.executable, "-m", "pytest", ...]` as a subprocess with
`cwd=REPO` - the Makefile's own invocation shape - returning its exit
code, instead of calling `pytest.main()` in the current process.

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
proves a census file importing `tests.unit....` collects under the
real `--run` invocation; mutating back to in-process `pytest.main()`
reds it. A guard over `ci.yml` proves the diff base is `HEAD^1` on a
`pull_request`, not `base.sha`; mutating back to `base.sha` reds it.

## Outcome

**Round 139, 2026-09-23**

**Gap measured** (both defects, pasted above under Motivation) -
(a) on `origin/main` `2dac36ec`: `2592 passed, 4 skipped, 1 error`;
(b) on PR #277's run `35862765977`: `base.sha` (`9ffa0b6b`) misses a
`flake_ledger.json` adopt commit the merge ref (`8907b1f3`) already
carries, so `git diff base.sha merge-ref` wrongly includes it while
`git diff HEAD^1 merge-ref` does not.

**Close measured.** (a) `tools/dev_docs_lane.py`'s `run_command()`
builds `[sys.executable, "-m", "pytest", *files, "-q", "-n", "auto",
*rest]`; `main()` runs it via `subprocess.run(..., cwd=REPO)` and
returns `.returncode`. Re-run after the fix:

```text
$ echo docs/audits/round-138.md | python3 tools/dev_docs_lane.py --run
78 test file(s) in the docs lane
2628 passed, 4 skipped in 62.90s (0:01:02)
```

(b) `ci.yml`'s `changes` and `docs-lane` steps both now diff
`"${{ github.event_name == 'pull_request' && 'HEAD^1' || 'HEAD' }}"`;
neither names `base.sha` any more.

**Mutation table** (`tests/unit/test_a_docs_only_diff_runs_its_guards.py`,
33 tests; scratchpad snapshot/revert, never `git checkout --`):

| mutation | reddened | count |
|---|---|---|
| (a) `main()` reverted to in-process `pytest.main()` | `test_run_hands_pytest_the_lane` (`code == 0` -> stub's `99`) | 1/33 |
| (b) `changes` step's diff reverted to `base.sha` | `test_the_diff_base_is_the_merge_refs_first_parent_not_base_sha` | 1/33 |
| (b) `docs-lane` step's diff reverted to `base.sha` | same test, second `assert` | 1/33 |

`test_run_is_a_python_dash_m_pytest_subprocess_not_in_process` and
`test_a_census_file_that_imports_another_test_module_collects` (which
runs `run_command()`'s real argv, unmocked, against the actual census
file) stayed green under (a)'s mutation - they test `run_command()`
directly, not `main()`'s dispatch; `test_run_hands_pytest_the_lane`
is the one that catches a `main()`-level reversion. Every mutation
reverted; suite back to 33/33 and files byte-identical to the
snapshot each time.

**Deviation:** the first cut of the census-collection guard used
`--collect-only` on the CLI's own full `--run` (the whole 78-file
census), which tripped `test_the_selector_carries_the_census.py`'s own
`SUBPROCESS_POPULATION_MARKERS` detector (`--collect-only` is itself a
population marker) and would have needed a new `tiers.py` CENSUS entry
for this guard file. Narrowed to `run_command()`'s own argv against a
single named file instead - faster (11s vs 27s for the file), no
census growth, and still an unmocked, real subprocess.
