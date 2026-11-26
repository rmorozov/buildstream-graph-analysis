# UX-1383: a dependabot pip pull request arrives with its lock

**Priority:** Medium | **Status:** 🟡 In Progress | **Depends on:** — | **Found by:** `retro-2026-10-26.md` proposal 1, repeated in `retro-2026-11-02.md`; Ruslan filed it on the decision card, 2026-11-05 19:54 UTC | **Serves:** every dependabot pip bump, and the owner's time per bump | **Topic:** guards | **Area:** unassigned | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_a_dependabot_pip_pr_arrives_with_its_lock.py`

## Motivation

Four of four dependabot pip pull requests (`#302`, `#322`, `#332`,
`#334`) went red on `pip-audit`'s lock check, `bst-tests`' lint and
`test (3.12)` until a hand `requirements.lock` commit landed, and waited
0, 5, 9 and 1 days for it. Dependabot edits `pyproject.toml` only.

## Required Fix

A dependabot pip pull request carries a lock that `quality.yml`'s check
accepts without a hand commit: a job on `dependabot/pip/*` that runs
`make lock` and pushes it, or an ecosystem that writes the lock itself.

## Out of Scope

Auto-merging dependabot pull requests.

## Acceptance Test

The next dependabot pip pull request is green on its first CI run with
no commit but dependabot's and the lock job's.

## Decision

`.github/workflows/dependabot-lock.yml`: on a `pull_request` whose actor is
`dependabot[bot]` and whose head is `dependabot/pip/*`, run `make lock-sync`
(`UX-1384`'s `LOCK_COMPILE`, seeded, no `--upgrade` - the check's compile)
and commit `requirements.lock` alone to that branch. Dependabot-triggered
runs get a read-only token unless `permissions:` raises it, and a push
made with `GITHUB_TOKEN` starts no workflow, so the checkout takes the
`DEPENDABOT_LOCK_TOKEN` Dependabot secret (a fine-grained token, contents:
write, this repository - the owner's to create) and falls back to
`GITHUB_TOKEN` with a warning. Not `pull_request_target`: no base-branch
token is needed, and none is handed to the PR's tree.
`test_no_workflow_pushes_to_the_default_branch.py` admits
`refs/heads/dependabot/pip/` literally. Once someone else commits,
Dependabot stops rebasing the PR on its own - as with every hand lock so far.

## Outcome

Gap, PR #349 (`01465455`, hypothesis 6.170.14 -> .17, ruff 0.17.3 -> .6),
merged with `UX-1384` in a scratch worktree: `make lock-check` -> rc 2;
its four reds on GitHub: `pip-audit`, `test (3.12)`, both `bst-tests`.
Same tree, `make lock-sync` -> `requirements.lock` moves exactly
`hypothesis==6.170.17` and `ruff==0.17.6`; `make lock-check` -> rc 0.

Close: `python3 -m pytest -q -p no:xdist tests/unit/test_a_dependabot_pip_pr_arrives_with_its_lock.py` -> 5 passed
(the push step's own shell against a bare remote: a moved lock is
committed alone with a tracked stray edit present; an agreeing lock pushes nothing).

| mutation | count |
|---|---|
| D1 the `dependabot/pip/` condition dropped | 1 failed, 4 passed |
| D2 `lock-sync` with `--upgrade` | 1 failed, 4 passed |
| D3 `git commit -a` instead of the lock alone | 1 failed, 4 passed |
| D4 the push removed | 1 failed, 4 passed |
| D5 the agree test inverted | 2 failed, 3 passed |
| D6 the checkout token is `github.token` alone | 1 failed, 4 passed |
| reverted | 5 passed |

Owner review of #352: the token reached the job that runs `make lock-sync` on
Dependabot's tree. Now `generate` checks out the event's head sha with
`persist-credentials: false`, no secret and `contents: read`, and uploads the lock;
`publish` holds the token, runs no project code, fetches the branch, leaves it alone
if it moved past that sha, and commits the downloaded lock alone. 7 passed:

| mutation | count |
|---|---|
| D7 `persist-credentials: false` dropped | 1 failed, 6 passed |
| D8 `generate` checks out `github.head_ref` | 1 failed, 6 passed |
| D9 the secret passed to `generate`'s checkout | 1 failed, 6 passed |
| D10 `publish` runs `make lock-sync` | 1 failed, 6 passed |
| D11 the head check removed | 1 failed, 6 passed |
| D12 `git commit -a` | 1 failed, 6 passed |
| reverted | 7 passed |

The Acceptance Test is the runner's: the next dependabot pip PR green on
its first run, which needs the secret; the row stays open until then.

