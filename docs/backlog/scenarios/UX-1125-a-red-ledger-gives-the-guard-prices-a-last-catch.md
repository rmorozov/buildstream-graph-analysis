# UX-1125: a red ledger gives `dev_guard_prices` a last-catch source

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-1122 | **Found by:** UX-1122 T2 (round 151, 2026-09-29) | **Serves:** Ruslan, who decides what the per-PR path costs | **Topic:** guards | **Area:** tools | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_the_red_ledger_is_appended_on_push.py`

## Motivation

`tools/dev_guard_prices.py` (`UX-1122`) reads each file's last catch as
None, "unrecorded", because no source records which test files went red
on a pull request. Until a source exists the retro cannot retire a guard
on its last true catch.

## Required Fix

On push to main, `.github/workflows/ci.yml` collects the failing test
files from the merged PR's red runs' junit and appends
`{file, sha, round}` to `tests/red_ledger.json` on `refs/heads/records`,
a 5th `RECORD_PATHS` entry; `tools/dev_guard_prices.py` reads it. Until
10 rounds exist the retro proposes only "needs owner" and "confirm
inferred".

## Decision

```text
Route:     tools/dev_red_ledger.py, two parts: pure `failing_files(junit)` plus `append(ledger, files, sha, round)` (round from dev_guard_prices.current_round); and `--from-pr SHA`, which finds the merged PR's red ci.yml runs and downloads their `junit-*` artifacts through the API with GITHUB_TOKEN. dev_guard_prices reads tests/red_ledger.json as last_catch; an absent file still reads "unrecorded".
Rejected:  appending on the PR run (unmerged heads would write records) · inferring from the push run (rarely red, the PR gates it).
Files:     T1: tools/dev_red_ledger.py, tools/dev_guard_prices.py, tools/dev_records.py (RECORD_PATHS 5th entry + its docstring count), .gitignore (+tests/red_ledger.json), tests/unit/test_the_red_ledger_is_appended_on_push.py. T2: .github/workflows/ci.yml (a `red-ledger-adopt` job chained after flake-ledger-adopt, `actions: read`, `contents: write`, `concurrency: records`), tests/unit/test_the_records_writers_are_one_chain.py (4→5)
Guard:     test_the_red_ledger_is_appended_on_push.py: a junit with one failing file appends one entry; a green junit appends none.
Mutation:  `failing_files` returns every testcase's file; the green case reds.
Class:     bookkeeping
Split:     T1 lands alone and green (fetch skips a missing record path). T2 in the same commit if ci.yml can be edited; if the edit is refused, paste the job YAML into the task file for the owner to apply.
```

## Out of Scope

Moving any file to a scheduled lane; that is a row the retro proposes.

## Acceptance Test

`tests/unit/test_the_red_ledger_is_appended_on_push.py`: a junit with one
failing file appends one `{file, sha, round}` entry; a green junit
appends none. Mutation: append on a green junit; the test reddens.

## Outcome

**Gap measured:** `python3 tools/dev_guard_prices.py` read every last catch as
"unrecorded": no record of red test files existed.

**Close measured:** `tools/dev_red_ledger.py` (`failing_files`, `append`,
`last_catch`, `--from-pr SHA` via urllib and `GITHUB_TOKEN`, no `gh`);
`tests/red_ledger.json` is the 5th `RECORD_PATHS` entry, gitignored;
`dev_guard_prices` reads it, an absent file reads `{}`; `ci.yml` gains
`red-ledger-adopt` (after `area-pages-publish`, `actions: read`,
`contents: write`, `concurrency: records`, gated on `test` success and on push
to main). `python3 -m pytest -n 2 -q` on the new guard, the writers-chain
guard (4 to 5) and the area-pages guard: 14 passed. The network part is
tested only through injected `get`/`download` fakes; never run live.

| Mutation | Reddened | Run |
|---|---|---|
| `failing_files` counts every testcase (`if True:`) | red-junit, green-junit | 2 failed, 4 passed |
| `append` drops its `(file, sha)` dedup | repeat-sha test | 1 failed, 5 passed |

Reverted from a copy; 10 passed on the guard plus the chain guard.

**Deviation:** `make lint` exits 1 on `still forced by UX-1114/1119`
lines for files this track does not touch; `ruff check`/`format --check` are
clean on the touched files.
